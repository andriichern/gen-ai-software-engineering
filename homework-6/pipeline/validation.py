"""Validation stage.

Reads each transaction record from shared/input, moves a working copy into
shared/processing while checking it against the canonical schema, and either
forwards it (annotated) to shared/output or writes a rejection directly to
shared/results.
"""
from __future__ import annotations

import argparse
import json
from pathlib import Path
from typing import Any, Dict

import pycountry

from lib.common import (
    audit,
    lean_data,
    make_envelope,
    parse_decimal,
    parse_iso8601,
    read_json,
    utc_now_iso,
    write_envelope,
    write_final_result,
)
from lib.stage_runner import run_stage_loop

STAGE_NAME = "validation"
DEFAULT_DATASET = "sample-transactions.json"
REQUIRED_TOP_LEVEL_FIELDS = (
    "transaction_id",
    "timestamp",
    "source_account",
    "destination_account",
    "amount",
    "currency",
    "transaction_type",
    "description",
    "metadata",
)


def _iso4217_valid(code: Any) -> bool:
    if not isinstance(code, str) or not code:
        return False
    return pycountry.currencies.get(alpha_3=code.upper()) is not None


def validate_transaction(record: Dict[str, Any]) -> Dict[str, Any]:
    """Confirms presence/type of every canonical field and returns a ValidationResult:
    {"status": "passed"|"failed", "reason": str|None, "checked_at": ISO 8601 UTC}.
    """
    for field in REQUIRED_TOP_LEVEL_FIELDS:
        if field not in record or record[field] in (None, ""):
            return {
                "status": "failed",
                "reason": f"missing required field: {field}",
                "checked_at": utc_now_iso(),
            }

    if not isinstance(record["transaction_id"], str):
        return {"status": "failed", "reason": "transaction_id must be a string", "checked_at": utc_now_iso()}

    try:
        parse_iso8601(record["timestamp"])
    except (ValueError, TypeError):
        return {
            "status": "failed",
            "reason": f"invalid timestamp: {record.get('timestamp')!r}",
            "checked_at": utc_now_iso(),
        }

    if not isinstance(record["source_account"], str):
        return {"status": "failed", "reason": "source_account must be a string", "checked_at": utc_now_iso()}
    if not isinstance(record["destination_account"], str):
        return {"status": "failed", "reason": "destination_account must be a string", "checked_at": utc_now_iso()}

    amount_raw = record["amount"]
    if not isinstance(amount_raw, str):
        return {
            "status": "failed",
            "reason": f"amount must be a decimal string, got {type(amount_raw).__name__}",
            "checked_at": utc_now_iso(),
        }
    try:
        parse_decimal(amount_raw)
    except ValueError as exc:
        return {"status": "failed", "reason": str(exc), "checked_at": utc_now_iso()}

    currency = record["currency"]
    if not _iso4217_valid(currency):
        return {
            "status": "failed",
            "reason": f"invalid currency code: {currency}",
            "checked_at": utc_now_iso(),
        }

    if not isinstance(record["transaction_type"], str):
        return {"status": "failed", "reason": "transaction_type must be a string", "checked_at": utc_now_iso()}

    if not isinstance(record["description"], str):
        return {"status": "failed", "reason": "description must be a string", "checked_at": utc_now_iso()}

    metadata = record["metadata"]
    if not isinstance(metadata, dict):
        return {"status": "failed", "reason": "metadata must be an object", "checked_at": utc_now_iso()}
    channel = metadata.get("channel")
    country = metadata.get("country")
    if not isinstance(channel, str) or not channel:
        return {"status": "failed", "reason": "missing required field: metadata.channel", "checked_at": utc_now_iso()}
    if not isinstance(country, str) or not country:
        return {"status": "failed", "reason": "missing required field: metadata.country", "checked_at": utc_now_iso()}

    return {"status": "passed", "reason": None, "checked_at": utc_now_iso()}

def run_stage(input_dir: Path, processing_dir: Path, output_dir: Path, results_dir: Path) -> Dict[str, int]:
    def process_transaction(transaction_id: str, working: Path) -> bool:
        record = read_json(working)
        result = validate_transaction(record)

        if result["status"] == "passed":
            data = lean_data(transaction_id, record["amount"], record["currency"], {"validation_result": result})
            envelope = make_envelope(STAGE_NAME, "fraud_detection", data)
            write_envelope(output_dir, transaction_id, envelope)
            audit(STAGE_NAME, transaction_id, "passed")
            return True

        write_final_result(
            results_dir,
            input_dir,
            transaction_id,
            {
                "validation_result": result,
                "reason": result["reason"],
                "final_status": "rejected",
            },
        )
        audit(STAGE_NAME, transaction_id, f"failed: {result['reason']}")
        return False

    return run_stage_loop(input_dir, processing_dir, "copy", process_transaction)


def dry_run(dataset: Path) -> Dict[str, Any]:
    """Validates every record in `dataset` and reports the outcome without
    writing anything: no shared directory is read, created, or modified, and
    no record is altered. Reuses `validate_transaction` unchanged, so a
    dry run and a real run always agree on whether a record is valid.

    Returns {"dataset", "total", "valid", "invalid", "results"}, where each
    entry of "results" is {"transaction_id", "status", "reason"}.
    """
    records = read_json(dataset)
    if not isinstance(records, list):
        raise ValueError(f"dataset must be a JSON array of transaction records: {dataset}")

    results = []
    for record in records:
        result = validate_transaction(record)
        results.append(
            {
                "transaction_id": record.get("transaction_id"),
                "status": result["status"],
                "reason": result["reason"],
            }
        )

    valid = sum(1 for r in results if r["status"] == "passed")
    return {
        "dataset": str(dataset),
        "total": len(results),
        "valid": valid,
        "invalid": len(results) - valid,
        "results": results,
    }


def _default_shared_dir() -> Path:
    return Path("shared")


def main() -> None:
    parser = argparse.ArgumentParser(description="Run the Validation stage standalone.")
    parser.add_argument("--input-dir", type=Path, default=_default_shared_dir() / "input")
    parser.add_argument("--output-dir", type=Path, default=_default_shared_dir() / "output")
    parser.add_argument("--processing-dir", type=Path, default=_default_shared_dir() / "processing")
    parser.add_argument("--results-dir", type=Path, default=_default_shared_dir() / "results")
    parser.add_argument(
        "--dry-run",
        action="store_true",
        help=(
            "Validate every record in the dataset and print a JSON report to stdout "
            "WITHOUT writing anything: no shared directory is read, created, or "
            "modified, and no record is altered. Use --dataset to pick the input file."
        ),
    )
    parser.add_argument(
        "--dataset",
        type=Path,
        default=Path(DEFAULT_DATASET),
        help=f"Dataset validated by --dry-run (default: {DEFAULT_DATASET}). Ignored without --dry-run.",
    )
    args = parser.parse_args()

    if args.dry_run:
        print(json.dumps(dry_run(args.dataset), indent=2))
        return

    tally = run_stage(args.input_dir, args.processing_dir, args.output_dir, args.results_dir)
    print(f"[{STAGE_NAME}] processed={tally['processed']} passed={tally['passed']} failed={tally['failed']}")


if __name__ == "__main__":
    main()
