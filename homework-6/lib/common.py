"""Shared internal types and utilities reused across every pipeline stage.

Kept deliberately small: JSON I/O helpers, decimal-safe (de)serialization,
UTC timestamp / UUID helpers, the audit-trail emitter, and the lean
inter-stage message envelope used by every stage.
"""
from __future__ import annotations

import json
import shutil
import uuid
from datetime import datetime, timezone
from decimal import Decimal, InvalidOperation
from pathlib import Path
from typing import Any, Dict, List, Optional

# ---------------------------------------------------------------------------
# Time / identity helpers
# ---------------------------------------------------------------------------


def utc_now_iso() -> str:
    """Current UTC time as an ISO 8601 string."""
    return datetime.now(timezone.utc).isoformat()


def new_id() -> str:
    """A random UUID4 string, used for message IDs and settlement references."""
    return str(uuid.uuid4())


def parse_iso8601(value: str) -> datetime:
    """Parse an ISO 8601 timestamp (accepting a trailing 'Z') into an aware UTC datetime."""
    normalized = value.replace("Z", "+00:00")
    dt = datetime.fromisoformat(normalized)
    if dt.tzinfo is None:
        dt = dt.replace(tzinfo=timezone.utc)
    return dt.astimezone(timezone.utc)


# ---------------------------------------------------------------------------
# Decimal-safe JSON I/O
# ---------------------------------------------------------------------------


class _DecimalEncoder(json.JSONEncoder):
    def default(self, o: Any) -> Any:
        if isinstance(o, Decimal):
            return str(o)
        return super().default(o)


def read_json(path: Path) -> Dict[str, Any]:
    with path.open("r", encoding="utf-8") as fh:
        return json.load(fh)


def write_json(path: Path, obj: Dict[str, Any]) -> None:
    path.parent.mkdir(parents=True, exist_ok=True)
    with path.open("w", encoding="utf-8") as fh:
        json.dump(obj, fh, indent=2, cls=_DecimalEncoder)


def parse_decimal(amount: str) -> Decimal:
    """Parse a string amount into a Decimal, never routing through float."""
    try:
        return Decimal(amount)
    except InvalidOperation as exc:
        raise ValueError(f"amount is not a well-formed decimal string: {amount!r}") from exc


# ---------------------------------------------------------------------------
# Audit trail (console only -- never persisted, per specification.md)
# ---------------------------------------------------------------------------


def audit(stage: str, transaction_id: str, outcome: str) -> None:
    """Emit one audit-trail entry: ISO 8601 UTC timestamp, stage, transaction_id, outcome.

    Identifies the record by transaction_id alone -- no PII is ever included.
    """
    print(f"[AUDIT] timestamp={utc_now_iso()} stage={stage} transaction_id={transaction_id} outcome={outcome}")


# ---------------------------------------------------------------------------
# Directory / file helpers
# ---------------------------------------------------------------------------


def list_json_files(directory: Path) -> List[Path]:
    """All *.json files in a directory, sorted by name for a deterministic order."""
    if not directory.exists():
        return []
    return sorted(p for p in directory.iterdir() if p.is_file() and p.suffix == ".json")


def move_into_processing(src: Path, processing_dir: Path) -> Path:
    """Move a source-stage message file into processing/ (true move -- source is transient)."""
    processing_dir.mkdir(parents=True, exist_ok=True)
    dest = processing_dir / src.name
    shutil.move(str(src), str(dest))
    return dest


def copy_into_processing(src: Path, processing_dir: Path) -> Path:
    """Copy (never move) a file into processing/. Used only by Validation, since the
    original in shared/input/ must remain read-only and available for every later
    stage to re-read original fields from.
    """
    processing_dir.mkdir(parents=True, exist_ok=True)
    dest = processing_dir / src.name
    shutil.copy2(str(src), str(dest))
    return dest


def clear_processing_file(path: Path) -> None:
    """Remove a working file from processing/ once a stage has finished with it,
    so processing/ holds no files at rest.
    """
    if path.exists():
        path.unlink()


def read_original_record(input_dir: Path, transaction_id: str) -> Dict[str, Any]:
    """Read a transaction's original record from shared/input/ (read-only)."""
    return read_json(input_dir / f"{transaction_id}.json")


# ---------------------------------------------------------------------------
# Inter-stage message envelope (lean -- never the full original record)
# ---------------------------------------------------------------------------


def make_envelope(source_stage: str, target_stage: str, data: Dict[str, Any]) -> Dict[str, Any]:
    return {
        "message_id": new_id(),
        "timestamp": utc_now_iso(),
        "source_stage": source_stage,
        "target_stage": target_stage,
        "message_type": "transaction",
        "data": data,
    }


def write_envelope(output_dir: Path, transaction_id: str, envelope: Dict[str, Any]) -> None:
    output_dir.mkdir(parents=True, exist_ok=True)
    write_json(output_dir / f"{transaction_id}.json", envelope)


def lean_data(
    transaction_id: str,
    amount: str,
    currency: str,
    accumulated: Optional[Dict[str, Any]] = None,
) -> Dict[str, Any]:
    """Build the lean `data` payload of a message: transaction_id/amount/currency
    plus whatever <stage>_result keys have accumulated so far. Never the full
    original record.
    """
    data: Dict[str, Any] = {
        "transaction_id": transaction_id,
        "amount": amount,
        "currency": currency,
    }
    if accumulated:
        data.update(accumulated)
    return data


def write_final_result(
    results_dir: Path,
    input_dir: Path,
    transaction_id: str,
    accumulated: Dict[str, Any],
) -> None:
    """Write the final shared/results/{transaction_id}.json record: the fresh
    original transaction (read from shared/input/) joined with every
    <stage>_result gathered so far, plus any top-level fields (reason,
    final_status) passed in `accumulated`.
    """
    original = read_original_record(input_dir, transaction_id)
    final_record = dict(original)
    final_record.update(accumulated)
    results_dir.mkdir(parents=True, exist_ok=True)
    write_json(results_dir / f"{transaction_id}.json", final_record)
