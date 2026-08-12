"""Validation stage.

Checks each input transaction for well-formedness and required fields.
Validation rules depend only on the record itself, never on prior-stage
results, so this stage always produces a definite pass/fail outcome and
never records a rule as not-applicable.

Also exposes a standalone, read-only "--check" CLI mode that validates a
transaction dataset directly (never shared/input/) without touching
shared/ at all.
"""
from __future__ import annotations

import argparse
import json
from datetime import datetime
from decimal import Decimal, InvalidOperation
from pathlib import Path

import pycountry

from lib.dataset import load_transactions
from lib.models import StageContext, Transaction, ValidationResult
from lib.stage_runner import run_first_stage

REQUIRED_FIELDS = [
    "transaction_id",
    "timestamp",
    "source_account",
    "destination_account",
    "amount",
    "currency",
    "transaction_type",
]


def _is_valid_decimal(value) -> bool:
    if not isinstance(value, str):
        return False
    try:
        Decimal(value)
    except InvalidOperation:
        return False
    return True


def _is_valid_iso4217(code) -> bool:
    if not isinstance(code, str) or len(code) != 3:
        return False
    return pycountry.currencies.get(alpha_3=code.upper()) is not None


def _is_valid_iso8601_utc(value) -> bool:
    if not isinstance(value, str):
        return False
    text = value.strip()
    if text.endswith("Z"):
        text = text[:-1] + "+00:00"
    try:
        parsed = datetime.fromisoformat(text)
    except ValueError:
        return False
    return parsed.tzinfo is not None


def validate_transaction(record: Transaction, context: StageContext) -> ValidationResult:
    """validate_transaction(record, context) -> ValidationResult

    context is accepted for signature/contract uniformity with the other
    stages but is never consulted: validation depends only on the record.
    """
    data = record.to_dict() if isinstance(record, Transaction) else dict(record)
    errors: list[str] = []

    for field_name in REQUIRED_FIELDS:
        if data.get(field_name) in (None, ""):
            errors.append(f"missing required field: {field_name}")

    if data.get("amount") not in (None, "") and not _is_valid_decimal(data["amount"]):
        errors.append("amount is not a valid decimal string")

    if data.get("currency") not in (None, "") and not _is_valid_iso4217(data["currency"]):
        errors.append(f"currency '{data['currency']}' is not a valid ISO 4217 code")

    if data.get("timestamp") not in (None, "") and not _is_valid_iso8601_utc(data["timestamp"]):
        errors.append("timestamp is not a valid ISO 8601 UTC datetime")

    passed = not errors
    reason = None if passed else "; ".join(errors)
    return ValidationResult(passed=passed, reason=reason, errors=errors)


def run_standalone_check(source: str) -> dict:
    """Read-only report mode: validates every record in `source` (a dataset
    file or directory, never shared/input/) and returns a structured,
    machine-readable report. Writes nothing anywhere."""
    records = load_transactions(source)
    entries = []
    valid = 0
    invalid = 0
    for raw in records:
        txn = Transaction.from_dict(raw)
        result = validate_transaction(txn, StageContext())
        if result.passed:
            valid += 1
        else:
            invalid += 1
        entries.append(
            {
                "transaction_id": txn.transaction_id,
                "passed": result.passed,
                "reason": result.reason,
            }
        )
    return {
        "total": len(records),
        "valid": valid,
        "invalid": invalid,
        "results": entries,
    }


def _is_pass(result: ValidationResult) -> bool:
    return result.passed


def main() -> None:
    parser = argparse.ArgumentParser(
        prog="validation",
        description=(
            "Validation stage for the transaction processing pipeline. "
            "In normal (mutating) mode it reads shared/input/, annotates every "
            "record with a validation_result, and writes shared/output/."
        ),
    )
    parser.add_argument(
        "--input-dir",
        default="shared/input",
        help="Directory of raw transaction records to validate (mutating mode only).",
    )
    parser.add_argument(
        "--output-dir",
        default="shared/output",
        help="Directory to write annotated messages to (mutating mode only).",
    )
    parser.add_argument(
        "--check",
        action="store_true",
        help=(
            "Standalone, read-only mode: validate the dataset given by --source "
            "and print a JSON report (per-record pass/fail plus total/valid/invalid "
            "counts) to stdout. Writes nothing to shared/ or anywhere else. "
            "Has no effect unless this flag is set."
        ),
    )
    parser.add_argument(
        "--source",
        default="sample-transactions.json",
        help="Transaction dataset (file or directory) to validate. Only used with --check.",
    )
    args = parser.parse_args()

    if args.check:
        report = run_standalone_check(args.source)
        print(json.dumps(report, indent=2))
        return

    tally = run_first_stage(
        stage_name="validation",
        next_stage="fraud_detection",
        result_key="validation_result",
        compute_fn=validate_transaction,
        raw_input_dir=Path(args.input_dir),
        processing_dir=Path(args.output_dir).parent / "processing",
        output_dir=Path(args.output_dir),
        is_pass=_is_pass,
    )
    print(f"[validation] done: {tally}")


if __name__ == "__main__":
    main()
