"""Reporting stage.

Reads the finished (settled) messages from shared/output, combines them with
the already-terminal records (rejected/held) already sitting in
shared/results, builds the aggregate run summary at shared/report.json, then
writes each settled transaction's final record to shared/results -- joining
the fresh original from shared/input with the results gathered at every
stage it reached. Leaves shared/output and shared/processing holding no
files, without removing the directories themselves.
"""
from __future__ import annotations

import argparse
from collections import defaultdict
from decimal import Decimal
from pathlib import Path
from typing import Any, Dict, List

from lib.common import (
    audit,
    clear_processing_file,
    list_json_files,
    read_json,
    read_original_record,
    utc_now_iso,
    write_json,
)
from lib.stage_runner import run_stage_loop

STAGE_NAME = "reporting"

SCORE_BUCKETS = (
    ("0.00-0.19", Decimal("0.00"), Decimal("0.19")),
    ("0.20-0.49", Decimal("0.20"), Decimal("0.49")),
    ("0.50-0.79", Decimal("0.50"), Decimal("0.79")),
    ("0.80-1.00", Decimal("0.80"), Decimal("1.00")),
)


def build_report(records: List[Dict[str, Any]]) -> Dict[str, Any]:
    """Computes the aggregate run summary from every processed transaction's
    accumulated results, whatever stage it finally reached. Counts
    transactions only -- never the summary record itself. Every monetary
    aggregate is computed with Decimal.
    """
    total = len(records)
    validated = rejected = flagged = held = settled = 0
    score_distribution = {label: 0 for label, _, _ in SCORE_BUCKETS}
    settled_value_by_currency: Dict[str, Decimal] = defaultdict(lambda: Decimal("0"))

    for record in records:
        validation_result = record.get("validation_result") or {}
        if validation_result.get("status") == "passed":
            validated += 1

        final_status = record.get("final_status")
        if final_status == "rejected":
            rejected += 1
        elif final_status == "held":
            held += 1
        elif final_status == "settled":
            settled += 1

        fraud_result = record.get("fraud_result") or {}
        if fraud_result.get("flagged"):
            flagged += 1
        score_raw = fraud_result.get("score")
        if score_raw is not None:
            score = Decimal(str(score_raw))
            for label, low, high in SCORE_BUCKETS:
                if low <= score <= high:
                    score_distribution[label] += 1
                    break

        settlement_result = record.get("settlement_result")
        if settlement_result and settlement_result.get("status") == "settled":
            currency = settlement_result.get("currency")
            amount = Decimal(str(settlement_result.get("settled_amount", "0")))
            settled_value_by_currency[currency] += amount

    return {
        "generated_at": utc_now_iso(),
        "total_records": total,
        "counts": {
            "validated": validated,
            "rejected": rejected,
            "flagged": flagged,
            "held": held,
            "settled": settled,
        },
        "risk_score_distribution": score_distribution,
        "total_settled_value_by_currency": {c: str(v) for c, v in settled_value_by_currency.items()},
    }

def run_stage(input_dir: Path, processing_dir: Path, output_dir: Path, results_dir: Path) -> Dict[str, int]:
    report_path = results_dir.parent / "report.json"

    def process_transaction(transaction_id: str, working: Path) -> bool:
        envelope = read_json(working)
        data = envelope["data"]

        original = read_original_record(input_dir, transaction_id)
        final_record = dict(original)
        final_record.update(
            {
                "validation_result": data.get("validation_result"),
                "fraud_result": data.get("fraud_result"),
                "compliance_result": data.get("compliance_result"),
                "settlement_result": data.get("settlement_result"),
                "final_status": "settled",
            }
        )
        settled_finals.append((transaction_id, final_record, working))
        return True

    # Records already terminated earlier in the run (validation-rejected,
    # compliance-held/rejected) already sit in shared/results.
    terminal_records = [read_json(f) for f in list_json_files(results_dir)]

    # Deferred: the report needs every settled_finals entry gathered before any
    # of them can be written, so process() only builds and collects each final
    # record here; the actual results/ writes (and processing/ clearing) happen
    # in the second pass below, once build_report has run over the full set.
    settled_finals: List[tuple] = []

    tally = run_stage_loop(output_dir, processing_dir, "move", process_transaction, clear_processing=False)

    all_records = terminal_records + [f[1] for f in settled_finals]
    report = build_report(all_records)
    write_json(report_path, report)

    for transaction_id, final_record, working in settled_finals:
        results_dir.mkdir(parents=True, exist_ok=True)
        write_json(results_dir / f"{transaction_id}.json", final_record)
        audit(STAGE_NAME, transaction_id, "settled")
        clear_processing_file(working)

    return tally


def _default_shared_dir() -> Path:
    return Path("shared")


def main() -> None:
    parser = argparse.ArgumentParser(description="Run the Reporting stage standalone.")
    parser.add_argument("--input-dir", type=Path, default=_default_shared_dir() / "input")
    parser.add_argument("--output-dir", type=Path, default=_default_shared_dir() / "output")
    parser.add_argument("--processing-dir", type=Path, default=_default_shared_dir() / "processing")
    parser.add_argument("--results-dir", type=Path, default=_default_shared_dir() / "results")
    args = parser.parse_args()

    tally = run_stage(args.input_dir, args.processing_dir, args.output_dir, args.results_dir)
    print(f"[{STAGE_NAME}] processed={tally['processed']} passed={tally['passed']} failed={tally['failed']}")


if __name__ == "__main__":
    main()
