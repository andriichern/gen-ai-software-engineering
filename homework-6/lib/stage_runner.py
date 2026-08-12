"""Generic file-based stage execution over shared/, reused by both the
orchestrator and every stage's standalone CLI entry point so the two never
disagree about how a stage reads its source directory, stages work in
processing/, and writes its output.
"""
from __future__ import annotations

from pathlib import Path
from typing import Callable

from lib.message_io import build_envelope, context_from_envelope_data, read_json, write_json
from lib.models import Transaction


def run_first_stage(
    *,
    stage_name: str,
    next_stage: str,
    result_key: str,
    compute_fn: Callable,
    raw_input_dir: Path,
    processing_dir: Path,
    output_dir: Path,
    is_pass: Callable[[object], bool],
) -> dict:
    """Validation-shaped stage: reads raw transaction records (not envelopes)
    from raw_input_dir, stages them through processing_dir, and writes the
    first envelope (with an empty starting context) to output_dir.
    raw_input_dir is never modified."""
    processing_dir.mkdir(parents=True, exist_ok=True)
    output_dir.mkdir(parents=True, exist_ok=True)

    record_files = sorted(raw_input_dir.glob("*.json"))
    staged: list[Path] = []
    for record_path in record_files:
        record_data = read_json(record_path)
        proc_path = processing_dir / record_path.name
        write_json(proc_path, record_data)
        staged.append(proc_path)

    processed = 0
    passed = 0
    failed = 0

    for proc_path in staged:
        record_data = read_json(proc_path)
        record = Transaction.from_dict(record_data)

        from lib.models import StageContext

        result = compute_fn(record, StageContext())

        lean_data = {
            "transaction_id": record.transaction_id,
            "amount": record.amount,
            "currency": record.currency,
            result_key: result.to_dict(),
        }
        envelope = build_envelope(stage_name, next_stage, lean_data)
        write_json(output_dir / proc_path.name, envelope)
        proc_path.unlink()

        processed += 1
        outcome = is_pass(result)
        passed += 1 if outcome else 0
        failed += 0 if outcome else 1
        print(f"[{stage_name}] {record.transaction_id}: {'pass' if outcome else 'fail'}")

    return {"processed": processed, "passed": passed, "failed": failed}


def run_downstream_stage(
    *,
    stage_name: str,
    next_stage: str,
    result_key: str,
    compute_fn: Callable,
    source_dir: Path,
    processing_dir: Path,
    output_dir: Path,
    input_dir: Path,
    is_pass: Callable[[object], bool],
    extra_kwargs: dict | None = None,
) -> dict:
    """Fraud/Compliance/Settlement-shaped stage: drains envelope messages
    from source_dir (normally shared/output/, reused for every stage) into
    processing_dir, computes this stage's result using the accumulated
    context plus the fresh original record from input_dir, then writes the
    updated envelope back to output_dir."""
    extra_kwargs = extra_kwargs or {}
    processing_dir.mkdir(parents=True, exist_ok=True)
    output_dir.mkdir(parents=True, exist_ok=True)

    source_files = sorted(source_dir.glob("*.json"))
    staged: list[Path] = []
    for src_path in source_files:
        envelope = read_json(src_path)
        proc_path = processing_dir / src_path.name
        write_json(proc_path, envelope)
        src_path.unlink()
        staged.append(proc_path)

    processed = 0
    passed = 0
    failed = 0

    for proc_path in staged:
        envelope = read_json(proc_path)
        data = envelope["data"]
        transaction_id = data["transaction_id"]

        original = read_json(input_dir / f"{transaction_id}.json")
        record = Transaction.from_dict(original)
        context = context_from_envelope_data(data)

        result = compute_fn(record, context, **extra_kwargs)

        data[result_key] = result.to_dict()
        new_envelope = build_envelope(stage_name, next_stage, data)
        write_json(output_dir / proc_path.name, new_envelope)
        proc_path.unlink()

        processed += 1
        outcome = is_pass(result)
        passed += 1 if outcome else 0
        failed += 0 if outcome else 1
        print(f"[{stage_name}] {transaction_id}: {'pass' if outcome else 'fail'}")

    return {"processed": processed, "passed": passed, "failed": failed}
