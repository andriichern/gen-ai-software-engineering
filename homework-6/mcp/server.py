"""Custom FastMCP server that makes the transaction-processing pipeline queryable.

Exposes the pipeline's outcomes over MCP without running or mutating anything:

    tool      get_transaction_status(transaction_id)  -> status of one transaction
    tool      list_pipeline_results()                 -> summary of every transaction
    resource  pipeline://summary                      -> latest run summary, as text

Read-only by construction. The server never writes to shared/, never imports
pipeline code, and depends on nothing beyond the standard library and fastmcp,
so it stays a leaf that cannot perturb a run it is reporting on.

Two constraints shape the implementation:

* Under stdio transport, stdout carries the JSON-RPC protocol stream. Anything
  printed there corrupts the connection, so every diagnostic goes to stderr.
* The working directory of an MCP client is not guaranteed, so shared/ is
  anchored to this file's location rather than to cwd. PIPELINE_SHARED_DIR
  overrides it.

Run:  uv run --no-project --with fastmcp mcp/server.py
"""
from __future__ import annotations

import json
import os
import sys
from pathlib import Path
from typing import Any, Dict, List, Optional

from fastmcp import FastMCP

# ---------------------------------------------------------------------------
# Locations
# ---------------------------------------------------------------------------

_DEFAULT_SHARED_DIR = Path(__file__).resolve().parent.parent / "shared"
SHARED_DIR = Path(os.environ.get("PIPELINE_SHARED_DIR") or _DEFAULT_SHARED_DIR)
RESULTS_DIR = SHARED_DIR / "results"
REPORT_PATH = SHARED_DIR / "report.json"
STATUS_PATH = SHARED_DIR / "status.json"

# Ordered so every rendering of outcome counts agrees, including outcomes that
# a given run happened to produce none of.
FINAL_STATUSES = ("settled", "held", "rejected")

STAGE_ORDER = ("validation", "fraud_detection", "compliance", "settlement", "reporting")

mcp = FastMCP("pipeline-status")


# ---------------------------------------------------------------------------
# Reading pipeline artifacts
# ---------------------------------------------------------------------------


def _warn(message: str) -> None:
    """Emit a diagnostic on stderr -- never stdout, which carries the protocol."""
    print(f"[pipeline-status] {message}", file=sys.stderr)


def _read_json(path: Path) -> Optional[Dict[str, Any]]:
    """Read a JSON object, or None if it is missing or unreadable.

    A partially written artifact from an interrupted run is a normal state for
    this server to encounter, not an error worth failing a request over.
    """
    try:
        with path.open("r", encoding="utf-8") as fh:
            loaded = json.load(fh)
    except FileNotFoundError:
        return None
    except (OSError, json.JSONDecodeError) as exc:
        _warn(f"could not read {path}: {exc}")
        return None
    return loaded if isinstance(loaded, dict) else None


def _result_paths() -> List[Path]:
    """Every result file, name-sorted for a deterministic response order."""
    if not RESULTS_DIR.is_dir():
        return []
    return sorted(p for p in RESULTS_DIR.iterdir() if p.is_file() and p.suffix == ".json")


def _safe_result_path(transaction_id: str) -> Optional[Path]:
    """Resolve a transaction id to its result file, or None if the id is unsafe.

    The id arrives from the caller and is interpolated into a filename, so ids
    bearing path separators are refused outright rather than normalized -- a
    legitimate transaction id never contains one.
    """
    if not transaction_id or any(ch in transaction_id for ch in ("/", "\\", "\x00")) or ".." in transaction_id:
        return None
    return RESULTS_DIR / f"{transaction_id}.json"


# ---------------------------------------------------------------------------
# Shaping a record for an LLM caller
# ---------------------------------------------------------------------------


def _blocking_reason(record: Dict[str, Any]) -> Optional[str]:
    """Why this transaction did not settle, or None if nothing blocked it."""
    for key in ("validation_result", "compliance_result", "settlement_result"):
        block = record.get(key)
        if isinstance(block, dict) and block.get("reason"):
            return str(block["reason"])
    return None


def _fraud_digest(record: Dict[str, Any]) -> Optional[str]:
    block = record.get("fraud_result")
    if not isinstance(block, dict):
        return None
    score = block.get("score")
    verdict = "flagged" if block.get("flagged") else "not flagged"
    return f"score {score}, {verdict}" if score is not None else verdict


def _stage_status(record: Dict[str, Any], key: str) -> Optional[str]:
    block = record.get(key)
    if not isinstance(block, dict):
        return None
    status = block.get("status")
    return str(status) if status is not None else None


def _summarize(record: Dict[str, Any]) -> Dict[str, Any]:
    """Trim a full result record down to what a caller asking about status needs.

    The stored record carries account numbers, descriptions and per-stage
    timestamps that answer no status question; omitting them keeps responses
    small and keeps incidental account data out of the transcript.
    """
    return {
        "transaction_id": record.get("transaction_id"),
        "final_status": record.get("final_status"),
        "amount": record.get("amount"),
        "currency": record.get("currency"),
        "stages": {
            "validation": _stage_status(record, "validation_result"),
            "fraud": _fraud_digest(record),
            "compliance": _stage_status(record, "compliance_result"),
            "settlement": _stage_status(record, "settlement_result"),
        },
        "reason": _blocking_reason(record),
    }


def _load_all_results() -> List[Dict[str, Any]]:
    records = []
    for path in _result_paths():
        record = _read_json(path)
        if record is not None:
            records.append(record)
    return records


def _count_by_final_status(records: List[Dict[str, Any]]) -> Dict[str, int]:
    counts = {status: 0 for status in FINAL_STATUSES}
    for record in records:
        status = str(record.get("final_status") or "unknown")
        counts[status] = counts.get(status, 0) + 1
    return counts


# ---------------------------------------------------------------------------
# Tools
# ---------------------------------------------------------------------------


@mcp.tool
def get_transaction_status(transaction_id: str) -> Dict[str, Any]:
    """Get the current pipeline status of a single transaction by its id.

    Returns how far the transaction travelled through the pipeline, its final
    status, and -- when it did not settle -- the reason that stopped it. An id
    with no result on disk returns found=false rather than raising, so asking
    about an unknown transaction is an answer, not a failure.
    """
    path = _safe_result_path(transaction_id)
    if path is None:
        return {
            "found": False,
            "transaction_id": transaction_id,
            "message": "invalid transaction_id: must not be empty or contain path separators",
        }

    record = _read_json(path)
    if record is None:
        return {
            "found": False,
            "transaction_id": transaction_id,
            "message": (
                f"no result recorded for {transaction_id!r}. The pipeline may not have run, "
                "or this transaction was not part of the last run."
            ),
        }

    summary = _summarize(record)
    summary["found"] = True
    return summary


@mcp.tool
def list_pipeline_results() -> Dict[str, Any]:
    """Summarize every transaction processed by the most recent pipeline run.

    Returns the total count, a breakdown by final status, and one compact entry
    per transaction including the reason any of them failed to settle.
    """
    records = _load_all_results()
    if not records:
        return {
            "total": 0,
            "counts": {status: 0 for status in FINAL_STATUSES},
            "transactions": [],
            "message": "no pipeline results found -- the pipeline has not produced results yet",
        }

    return {
        "total": len(records),
        "counts": _count_by_final_status(records),
        "transactions": [_summarize(record) for record in records],
    }


# ---------------------------------------------------------------------------
# Resource: pipeline://summary
# ---------------------------------------------------------------------------


def _render_from_artifacts(report: Dict[str, Any], status: Dict[str, Any]) -> str:
    """Render the summary from the artifacts the reporting stage certified."""
    lines = [
        "Pipeline Run Summary",
        "====================",
        f"Run started:   {status.get('run_started_at', 'unknown')}",
        f"Run completed: {status.get('run_completed_at') or 'still running / interrupted'}",
        f"Report generated: {report.get('generated_at', 'unknown')}",
        "",
        f"Transactions ingested: {report.get('total_records', 'unknown')}",
        "",
        "Outcome counts",
    ]

    counts = report.get("counts")
    if isinstance(counts, dict) and counts:
        width = max(len(str(k)) for k in counts)
        for key, value in counts.items():
            lines.append(f"  {str(key).ljust(width)}  {value}")
    else:
        lines.append("  (none recorded)")

    stages = status.get("stages")
    if isinstance(stages, dict) and stages:
        lines += ["", "Per-stage tallies", f"  {'stage'.ljust(16)}{'proc':>6}{'pass':>6}{'fail':>6}"]
        ordered = [s for s in STAGE_ORDER if s in stages] + [s for s in stages if s not in STAGE_ORDER]
        for name in ordered:
            tally = stages.get(name)
            if not isinstance(tally, dict):
                continue
            processed = tally.get("processed", "-")
            passed = tally.get("passed", "-")
            failed = tally.get("failed", "-")
            lines.append(f"  {str(name).ljust(16)}{processed:>6}{passed:>6}{failed:>6}")

    distribution = report.get("risk_score_distribution")
    if isinstance(distribution, dict) and distribution:
        lines += ["", "Risk score distribution"]
        for bucket, count in distribution.items():
            lines.append(f"  {bucket}  {count}")

    settled_value = report.get("total_settled_value_by_currency")
    if isinstance(settled_value, dict) and settled_value:
        lines += ["", "Total settled value by currency"]
        for currency, total in settled_value.items():
            lines.append(f"  {currency}  {total}")

    lines += ["", "source: shared/report.json + shared/status.json"]
    return "\n".join(lines)


def _render_from_results(records: List[Dict[str, Any]]) -> str:
    """Fall back to aggregating the result files directly.

    Used when report.json or status.json is missing or unreadable -- typically
    an interrupted run. Per-stage tallies and run timings cannot be recovered
    this way, so the text says so instead of implying the run finished.
    """
    counts = _count_by_final_status(records)
    lines = [
        "Pipeline Run Summary",
        "====================",
        "Run timings unavailable -- summarized directly from shared/results/.",
        "",
        f"Transactions with results: {len(records)}",
        "",
        "Outcome counts",
    ]
    width = max(len(k) for k in counts)
    for key, value in counts.items():
        lines.append(f"  {key.ljust(width)}  {value}")

    unsettled = [r for r in records if r.get("final_status") != "settled"]
    if unsettled:
        lines += ["", "Did not settle"]
        for record in unsettled:
            reason = _blocking_reason(record) or "no reason recorded"
            lines.append(f"  {record.get('transaction_id')}  [{record.get('final_status')}]  {reason}")

    lines += ["", "source: shared/results/ (report.json or status.json unavailable -- run may be incomplete)"]
    return "\n".join(lines)


@mcp.resource("pipeline://summary", mime_type="text/plain")
def pipeline_summary() -> str:
    """The latest pipeline run summary as human-readable text.

    Prefers the artifacts the reporting stage wrote, since per-stage tallies and
    run timings exist nowhere else, and falls back to aggregating the individual
    result files when those artifacts are missing.
    """
    report = _read_json(REPORT_PATH)
    status = _read_json(STATUS_PATH)
    if report is not None and status is not None:
        return _render_from_artifacts(report, status)

    records = _load_all_results()
    if records:
        return _render_from_results(records)

    return (
        "Pipeline Run Summary\n"
        "====================\n"
        "No pipeline run found. Neither shared/report.json nor shared/results/ "
        f"holds any data under {SHARED_DIR}."
    )


if __name__ == "__main__":
    mcp.run()
