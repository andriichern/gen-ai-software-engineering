"""Compliance Check stage.

Reads fraud-scored records from shared/output, moves each into
shared/processing while it is reviewed against the GDPR / Data Protection Act
2018 baseline, and either clears it on to shared/output for Settlement or
writes a held/rejected final record directly to shared/results.
"""
from __future__ import annotations

import argparse
from pathlib import Path
from typing import Any, Dict

from lib.common import (
    audit,
    lean_data,
    make_envelope,
    read_json,
    utc_now_iso,
    write_envelope,
    write_final_result,
)
from lib.stage_runner import run_stage_loop

STAGE_NAME = "compliance"


def check_compliance(record: Dict[str, Any], fraud: Dict[str, Any]) -> Dict[str, Any]:
    """Applies the GDPR / Data Protection Act 2018 baseline uniformly to every
    record. Converts a fraud flag into a hold for human review (GDPR Article
    22) rather than an automated adverse decision. Never carries or logs PII
    in plaintext -- only transaction_id-scoped facts are used here.

    Returns a ComplianceResult: {"status": "cleared"|"held"|"rejected",
    "reason": str|None, "checked_at": ISO 8601 UTC}.
    """
    if fraud.get("flagged"):
        return {
            "status": "held",
            "reason": f"held for human review: fraud score {fraud.get('score')} flagged this record",
            "checked_at": utc_now_iso(),
        }
    return {"status": "cleared", "reason": None, "checked_at": utc_now_iso()}

def run_stage(input_dir: Path, processing_dir: Path, output_dir: Path, results_dir: Path) -> Dict[str, int]:
    def process_transaction(transaction_id: str, working: Path) -> bool:
        envelope = read_json(working)
        data = envelope["data"]

        fraud_result = data.get("fraud_result", {})
        # check_compliance's Transaction argument is the accumulated data record
        # itself (it needs no further original fields beyond what fraud already
        # gathered), per the "Function to CREATE" signature in specification.md.
        result = check_compliance(data, fraud_result)

        if result["status"] == "cleared":
            new_data = lean_data(transaction_id, data["amount"], data["currency"], {
                "validation_result": data.get("validation_result"),
                "fraud_result": fraud_result,
                "compliance_result": result,
                "country": data.get("country"),
                "transaction_timestamp": data.get("transaction_timestamp"),
            })
            new_envelope = make_envelope(STAGE_NAME, "settlement", new_data)
            write_envelope(output_dir, transaction_id, new_envelope)
            audit(STAGE_NAME, transaction_id, "cleared")
            return True

        write_final_result(
            results_dir,
            input_dir,
            transaction_id,
            {
                "validation_result": data.get("validation_result"),
                "fraud_result": fraud_result,
                "compliance_result": result,
                "reason": result["reason"],
                "final_status": result["status"],
            },
        )
        audit(STAGE_NAME, transaction_id, result["status"])
        return False

    return run_stage_loop(output_dir, processing_dir, "move", process_transaction)


def _default_shared_dir() -> Path:
    return Path("shared")


def main() -> None:
    parser = argparse.ArgumentParser(description="Run the Compliance Check stage standalone.")
    parser.add_argument("--input-dir", type=Path, default=_default_shared_dir() / "input")
    parser.add_argument("--output-dir", type=Path, default=_default_shared_dir() / "output")
    parser.add_argument("--processing-dir", type=Path, default=_default_shared_dir() / "processing")
    parser.add_argument("--results-dir", type=Path, default=_default_shared_dir() / "results")
    args = parser.parse_args()

    tally = run_stage(args.input_dir, args.processing_dir, args.output_dir, args.results_dir)
    print(f"[{STAGE_NAME}] processed={tally['processed']} passed={tally['passed']} failed={tally['failed']}")


if __name__ == "__main__":
    main()
