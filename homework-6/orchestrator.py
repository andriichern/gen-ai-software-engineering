"""Standalone orchestrator for the transaction-processing pipeline.

Wipes and recreates shared/, copies the input dataset into shared/input/,
fetches live exchange rates once for whichever currencies appear in the
input, then runs the five pipeline stages in fixed sequence -- Validation,
Fraud Detection, Compliance Check, Settlement Processing, Reporting --
each stage's core function called in-process (never as a subprocess), so
real per-stage counts are available for shared/status.json.

Runnable any time, with no coupling to any code-generation session:
    python3 orchestrator.py [--input sample-transactions.json]
"""
from __future__ import annotations

import argparse
import shutil
import sys
from pathlib import Path
from typing import Any, Dict

import pycountry

from lib.common import clear_processing_file, list_json_files, read_json, utc_now_iso, write_json
from lib.exchange_rates import ExchangeRateError, fetch_exchange_rates
from pipeline import compliance, fraud_detection, reporting, settlement, validation

STAGE_ORDER = ("validation", "fraud_detection", "compliance", "settlement", "reporting")
DEFAULT_INPUT = "sample-transactions.json"


def _iso4217_valid(code: Any) -> bool:
    return isinstance(code, str) and bool(code) and pycountry.currencies.get(alpha_3=code.upper()) is not None


def _wipe_and_create_shared_tree(shared_dir: Path) -> Dict[str, Path]:
    if shared_dir.exists():
        shutil.rmtree(shared_dir)
    dirs = {
        "input": shared_dir / "input",
        "processing": shared_dir / "processing",
        "output": shared_dir / "output",
        "results": shared_dir / "results",
    }
    for d in dirs.values():
        d.mkdir(parents=True, exist_ok=True)
    return dirs


def _copy_input_dataset(source: Path, input_dir: Path) -> list:
    if not source.exists():
        raise FileNotFoundError(f"input dataset not found: {source}")
    records = read_json(source) if source.suffix == ".json" else None
    if not isinstance(records, list):
        raise ValueError(f"input dataset must be a JSON array of transaction records: {source}")
    for record in records:
        transaction_id = record.get("transaction_id")
        if not transaction_id:
            raise ValueError(f"a record in {source} is missing transaction_id: {record!r}")
        write_json(input_dir / f"{transaction_id}.json", record)
    return records


class StatusPublisher:
    """Writes shared/status.json live, twice per stage (start, then completion)."""

    def __init__(self, path: Path):
        self.path = path
        self.state: Dict[str, Any] = {"run_started_at": utc_now_iso(), "stages": {}}
        self._flush()

    def _flush(self) -> None:
        write_json(self.path, self.state)

    def start_stage(self, stage: str) -> None:
        self.state["stages"][stage] = {"start": utc_now_iso()}
        self._flush()

    def complete_stage(self, stage: str, tally: Dict[str, int]) -> None:
        self.state["stages"][stage].update(
            {
                "end": utc_now_iso(),
                "processed": tally["processed"],
                "passed": tally["passed"],
                "failed": tally["failed"],
            }
        )
        self._flush()

    def complete_run(self) -> None:
        self.state["run_completed_at"] = utc_now_iso()
        self._flush()


def run(input_source: Path, shared_dir: Path) -> None:
    print(f"Wiping and recreating {shared_dir}/ ...")
    dirs = _wipe_and_create_shared_tree(shared_dir)

    STAGES = {
        "validation": lambda: validation.run_stage(dirs["input"], dirs["processing"], dirs["output"], dirs["results"]),
        "fraud_detection": lambda: fraud_detection.run_stage(dirs["input"], dirs["processing"], dirs["output"], rates),
        "compliance": lambda: compliance.run_stage(dirs["input"], dirs["processing"], dirs["output"], dirs["results"]),
        "settlement": lambda: settlement.run_stage(dirs["input"], dirs["processing"], dirs["output"], dirs["results"]),
        "reporting": lambda: reporting.run_stage(dirs["input"], dirs["processing"], dirs["output"], dirs["results"]),
    }

    status_path = shared_dir / "status.json"
    status = StatusPublisher(status_path)

    print(f"Copying input dataset from {input_source} into {dirs['input']}/ ...")
    records = _copy_input_dataset(input_source, dirs["input"])
    print(f"Ingested {len(records)} transaction record(s).")

    currencies = sorted({r.get("currency") for r in records if _iso4217_valid(r.get("currency"))})
    print(f"Fetching live exchange rates for currencies: {currencies or '(none -- USD only)'} ...")
    try:
        rates = fetch_exchange_rates(currencies)
    except ExchangeRateError as exc:
        print(f"ERROR: {exc}", file=sys.stderr)
        raise SystemExit(1) from exc
    print(f"Exchange rates fetched: { {k: str(v) for k, v in rates.items()} }")

    for name, stage_fn in STAGES.items():
        print(f"\n=== Stage: {name} ===")
        status.start_stage(name)
        tally = stage_fn()
        status.complete_stage(name, tally)
        print(f"{name}: processed={tally['processed']} passed={tally['passed']} failed={tally['failed']}")

    status.complete_run()

    # The run has now fully finished successfully -- shared/input/ has served
    # its purpose (every stage that needed original fields has already read
    # them) and is emptied of files, matching how output/ and processing/ are
    # already left: the directory itself stays, only its files are removed.
    print(f"Clearing {dirs['input']}/ ...")
    for f in list_json_files(dirs["input"]):
        clear_processing_file(f)

    print(f"\nRun complete. Results in {dirs['results']}/, summary at {shared_dir / 'report.json'}.")


def main() -> None:
    parser = argparse.ArgumentParser(description="Run the transaction-processing pipeline end to end.")
    parser.add_argument(
        "--input",
        type=Path,
        default=Path(DEFAULT_INPUT),
        help=f"Path to the input transaction dataset (default: {DEFAULT_INPUT})",
    )
    parser.add_argument("--shared-dir", type=Path, default=Path("shared"), help="Path to the shared/ working tree")
    args = parser.parse_args()

    run(args.input, args.shared_dir)


if __name__ == "__main__":
    main()
