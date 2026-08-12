#!/usr/bin/env python3
"""Orchestrator for the transaction processing pipeline.

Runs the 5 stages in the fixed order Validation -> Fraud Detection ->
Compliance Check -> Settlement Processing -> Reporting, entirely in-process
by importing each stage's core function directly (never as a subprocess,
never via HTTP). This order is hardcoded here: it is never read from any
config file (including gateway/'s), never overridable by a flag or
environment variable, and the orchestrator has no knowledge that
services/ or gateway/ exist.

Run from the homework-6 root: `python3 orchestrator.py [--source PATH]`.
"""
from __future__ import annotations

import argparse
import shutil
from pathlib import Path

from lib.dataset import load_transactions
from lib.exchange_rates import fetch_exchange_rates
from lib.message_io import now_iso, write_json
from lib.stage_runner import run_downstream_stage, run_first_stage
from pipeline.compliance import check_compliance
from pipeline.fraud_detection import score_transaction
from pipeline.reporting import run_reporting
from pipeline.settlement import settle_transaction
from pipeline.validation import validate_transaction

ROOT = Path(__file__).resolve().parent
SHARED = ROOT / "shared"

STAGE_NAMES = ["validation", "fraud_detection", "compliance", "settlement", "reporting"]


def _reset_shared_tree() -> Path:
    if SHARED.exists():
        shutil.rmtree(SHARED)
    for sub in ("input", "processing", "output", "results"):
        (SHARED / sub).mkdir(parents=True, exist_ok=True)
    return SHARED


def _copy_input_dataset(source: str, input_dir: Path) -> list[dict]:
    records = load_transactions(source)
    for record in records:
        write_json(input_dir / f"{record['transaction_id']}.json", record)
    return records


def _new_status() -> dict:
    return {
        "run_started_at": now_iso(),
        "run_completed_at": None,
        "stages": {
            name: {"started_at": None, "completed_at": None, "processed": 0, "passed": 0, "failed": 0}
            for name in STAGE_NAMES
        },
    }


def _mark_stage_started(status: dict, status_path: Path, stage: str) -> None:
    status["stages"][stage]["started_at"] = now_iso()
    write_json(status_path, status)


def _mark_stage_completed(status: dict, status_path: Path, stage: str, tally: dict) -> None:
    status["stages"][stage].update(
        {
            "completed_at": now_iso(),
            "processed": tally["processed"],
            "passed": tally["passed"],
            "failed": tally["failed"],
        }
    )
    write_json(status_path, status)


def run_pipeline(source: str) -> None:
    shared = _reset_shared_tree()
    status_path = shared / "status.json"
    report_path = shared / "report.json"
    input_dir = shared / "input"
    processing_dir = shared / "processing"
    output_dir = shared / "output"
    results_dir = shared / "results"

    status = _new_status()
    write_json(status_path, status)

    records = _copy_input_dataset(source, input_dir)
    print(f"[orchestrator] copied {len(records)} transaction(s) into shared/input/")

    currencies = sorted({r["currency"] for r in records if r.get("currency")})
    print(f"[orchestrator] fetching live exchange rates for currencies present in input: {currencies}")
    rates = fetch_exchange_rates(retries=3, delay_seconds=3.0)

    # --- Stage 1: Validation ---
    _mark_stage_started(status, status_path, "validation")
    tally = run_first_stage(
        stage_name="validation",
        next_stage="fraud_detection",
        result_key="validation_result",
        compute_fn=validate_transaction,
        raw_input_dir=input_dir,
        processing_dir=processing_dir,
        output_dir=output_dir,
        is_pass=lambda r: r.passed,
    )
    _mark_stage_completed(status, status_path, "validation", tally)

    # --- Stage 2: Fraud Detection ---
    _mark_stage_started(status, status_path, "fraud_detection")
    tally = run_downstream_stage(
        stage_name="fraud_detection",
        next_stage="compliance",
        result_key="fraud_result",
        compute_fn=score_transaction,
        source_dir=output_dir,
        processing_dir=processing_dir,
        output_dir=output_dir,
        input_dir=input_dir,
        is_pass=lambda r: not r.flagged,
        extra_kwargs={"rates": rates},
    )
    _mark_stage_completed(status, status_path, "fraud_detection", tally)

    # --- Stage 3: Compliance Check ---
    _mark_stage_started(status, status_path, "compliance")
    tally = run_downstream_stage(
        stage_name="compliance",
        next_stage="settlement",
        result_key="compliance_result",
        compute_fn=check_compliance,
        source_dir=output_dir,
        processing_dir=processing_dir,
        output_dir=output_dir,
        input_dir=input_dir,
        is_pass=lambda r: r.status == "passed",
    )
    _mark_stage_completed(status, status_path, "compliance", tally)

    # --- Stage 4: Settlement Processing ---
    _mark_stage_started(status, status_path, "settlement")
    tally = run_downstream_stage(
        stage_name="settlement",
        next_stage="reporting",
        result_key="settlement_result",
        compute_fn=settle_transaction,
        source_dir=output_dir,
        processing_dir=processing_dir,
        output_dir=output_dir,
        input_dir=input_dir,
        is_pass=lambda r: r.status == "settled",
    )
    _mark_stage_completed(status, status_path, "settlement", tally)

    # --- Stage 5: Reporting (terminal; sole writer of results/) ---
    _mark_stage_started(status, status_path, "reporting")
    report = run_reporting(
        output_dir=output_dir,
        input_dir=input_dir,
        results_dir=results_dir,
        report_path=report_path,
    )
    _mark_stage_completed(
        status,
        status_path,
        "reporting",
        {"processed": report.total, "passed": report.settled, "failed": report.total - report.settled},
    )

    status["run_completed_at"] = now_iso()
    write_json(status_path, status)

    # shared/input/ is read-only for the duration of the run (every stage
    # reads fresh original fields from it); only now that nothing is left to
    # read it does the orchestrator empty it, per the Ending Context.
    for f in input_dir.glob("*.json"):
        f.unlink()

    print(f"[orchestrator] run complete: {report.summary}")


def main() -> None:
    parser = argparse.ArgumentParser(
        prog="orchestrator",
        description="Runs the full 5-stage transaction processing pipeline against shared/.",
    )
    parser.add_argument(
        "--source",
        default="sample-transactions.json",
        help="Transaction dataset to process (file or directory). Defaults to sample-transactions.json.",
    )
    args = parser.parse_args()
    run_pipeline(args.source)


if __name__ == "__main__":
    main()
