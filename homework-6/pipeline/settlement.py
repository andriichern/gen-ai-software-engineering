"""Settlement Processing stage.

Reads compliance-cleared records from shared/output, moves each into
shared/processing while settling it against an internal simulated ledger (no
external/network call), and writes the settled record back to shared/output
for Reporting.
"""
from __future__ import annotations

import argparse
from decimal import Decimal
from pathlib import Path
from typing import Any, Dict

from lib.common import (
    audit,
    lean_data,
    make_envelope,
    new_id,
    parse_decimal,
    read_json,
    utc_now_iso,
    write_envelope,
    write_final_result,
)
from lib.stage_runner import run_stage_loop

STAGE_NAME = "settlement"
RETENTION_PERIOD_YEARS = 5


def settle_transaction(record: Dict[str, Any], compliance: Dict[str, Any]) -> Dict[str, Any]:
    """Settles a cleared record against the internal simulated ledger. Refuses
    to settle anything whose compliance result is absent or not cleared.
    Negative amounts (refunds) settle exactly as legitimate transactions do.

    Returns a SettlementResult: {"status": "settled", "settlement_reference":
    uuid4, "settlement_timestamp": ISO 8601 UTC, "settled_amount": decimal
    string, "currency": str, "retention_period_years": 5}.
    """
    if not compliance or compliance.get("status") != "cleared":
        raise ValueError("cannot settle a record whose compliance result is absent or not cleared")

    amount: Decimal = parse_decimal(record["amount"])

    return {
        "status": "settled",
        "settlement_reference": new_id(),
        "settlement_timestamp": utc_now_iso(),
        "settled_amount": str(amount),
        "currency": record["currency"],
        "retention_period_years": RETENTION_PERIOD_YEARS,
    }

def run_stage(input_dir: Path, processing_dir: Path, output_dir: Path, results_dir: Path) -> Dict[str, int]:
    def process_transaction(transaction_id: str, working: Path) -> bool:
        envelope = read_json(working)
        data = envelope["data"]

        compliance_result = data.get("compliance_result", {})
        try:
            result = settle_transaction(data, compliance_result)
        except ValueError as exc:
            write_final_result(
                results_dir,
                input_dir,
                transaction_id,
                {
                    "validation_result": data.get("validation_result"),
                    "fraud_result": data.get("fraud_result"),
                    "compliance_result": compliance_result,
                    "reason": str(exc),
                    "final_status": "settlement_refused",
                },
            )
            audit(STAGE_NAME, transaction_id, f"refused: {exc}")
            return False

        new_data = lean_data(transaction_id, data["amount"], data["currency"], {
            "validation_result": data.get("validation_result"),
            "fraud_result": data.get("fraud_result"),
            "compliance_result": compliance_result,
            "settlement_result": result,
            "country": data.get("country"),
            "transaction_timestamp": data.get("transaction_timestamp"),
        })
        new_envelope = make_envelope(STAGE_NAME, "reporting", new_data)
        write_envelope(output_dir, transaction_id, new_envelope)
        audit(STAGE_NAME, transaction_id, "settled")
        return True

    return run_stage_loop(output_dir, processing_dir, "move", process_transaction)


def _default_shared_dir() -> Path:
    return Path("shared")


def main() -> None:
    parser = argparse.ArgumentParser(description="Run the Settlement Processing stage standalone.")
    parser.add_argument("--input-dir", type=Path, default=_default_shared_dir() / "input")
    parser.add_argument("--output-dir", type=Path, default=_default_shared_dir() / "output")
    parser.add_argument("--processing-dir", type=Path, default=_default_shared_dir() / "processing")
    parser.add_argument("--results-dir", type=Path, default=_default_shared_dir() / "results")
    args = parser.parse_args()

    tally = run_stage(args.input_dir, args.processing_dir, args.output_dir, args.results_dir)
    print(f"[{STAGE_NAME}] processed={tally['processed']} passed={tally['passed']} failed={tally['failed']}")


if __name__ == "__main__":
    main()
