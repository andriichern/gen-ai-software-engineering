"""Reporting stage.

Always invoked last. The sole owner of shared/results/. Computes each
transaction's final verdict from its accumulated stage outcomes using the
spec's pinned precedence table, then writes:

  - shared/results/{transaction_id}.json  - one file per transaction, joining
    the original record (read fresh from shared/input/) with accumulated
    stage results, verdict, fraud_flagged, and reason.
  - shared/report.json - aggregate run summary.

build_report() itself is a pure function with no I/O, per the stage
contract; the CLI/orchestrator glue below performs the file I/O around it.
"""
from __future__ import annotations

import argparse
from pathlib import Path

from lib.message_io import context_from_envelope_data, now_iso, read_json, write_json
from lib.models import ProcessedTransaction, RunReport, StageContext, VerdictRecord


def _compute_verdict(context: StageContext) -> tuple[str, str | None]:
    v, f, c, s = (
        context.validation_result,
        context.fraud_result,
        context.compliance_result,
        context.settlement_result,
    )

    missing = [
        name
        for name, val in (
            ("validation", v),
            ("fraud_detection", f),
            ("compliance", c),
            ("settlement", s),
        )
        if val is None
    ]
    if missing:
        return "INCOMPLETE", f"stage(s) did not run: {', '.join(missing)}"

    if not v.passed:
        return "REJECTED", f"validation: {v.reason}"

    if c.status == "rejected":
        return "REJECTED", f"compliance: {c.reason}"

    if c.status == "held":
        return "HELD", f"compliance: {c.reason}"

    if s.status == "settled":
        return "SETTLED", None

    return "INCOMPLETE", "no settlement outcome recorded"


def build_report(records: list[ProcessedTransaction]) -> RunReport:
    """build_report(records) -> RunReport. Pure: performs no I/O."""
    verdicts: list[VerdictRecord] = []
    settled = rejected = held = incomplete = fraud_flagged_count = compliance_held_count = 0

    for processed in records:
        verdict, reason = _compute_verdict(processed.context)
        fraud_flagged = bool(processed.context.fraud_result and processed.context.fraud_result.flagged)

        if verdict == "SETTLED":
            settled += 1
        elif verdict == "REJECTED":
            rejected += 1
        elif verdict == "HELD":
            held += 1
        else:
            incomplete += 1

        if fraud_flagged:
            fraud_flagged_count += 1
        if processed.context.compliance_result and processed.context.compliance_result.status == "held":
            compliance_held_count += 1

        verdicts.append(
            VerdictRecord(
                transaction_id=processed.transaction_id,
                verdict=verdict,
                fraud_flagged=fraud_flagged,
                reason=reason,
                stage_outcomes=processed.context.to_dict(),
            )
        )

    total = len(records)
    summary = (
        f"{total} transaction(s) processed: {settled} settled, {rejected} rejected, "
        f"{held} held, {incomplete} incomplete; {fraud_flagged_count} fraud-flagged."
    )

    return RunReport(
        total=total,
        settled=settled,
        rejected=rejected,
        held=held,
        incomplete=incomplete,
        fraud_flagged=fraud_flagged_count,
        compliance_held=compliance_held_count,
        summary=summary,
        generated_at=now_iso(),
        verdicts=verdicts,
    )


def run_reporting(output_dir: Path, input_dir: Path, results_dir: Path, report_path: Path) -> RunReport:
    """CLI/orchestrator glue: reads finished messages from output_dir, builds
    the batch of ProcessedTransaction, computes the report, writes one file
    per transaction into results_dir (joining the fresh original record),
    and writes report.json. Leaves output_dir empty of files afterward."""
    results_dir.mkdir(parents=True, exist_ok=True)

    source_files = sorted(output_dir.glob("*.json"))
    processed_list: list[ProcessedTransaction] = []
    envelopes_by_id: dict[str, Path] = {}

    for src_path in source_files:
        envelope = read_json(src_path)
        data = envelope["data"]
        transaction_id = data["transaction_id"]
        context = context_from_envelope_data(data)
        processed_list.append(
            ProcessedTransaction(
                transaction_id=transaction_id,
                amount=data.get("amount"),
                currency=data.get("currency"),
                context=context,
            )
        )
        envelopes_by_id[transaction_id] = src_path

    report = build_report(processed_list)

    for verdict_record in report.verdicts:
        original = read_json(input_dir / f"{verdict_record.transaction_id}.json")
        final_record = dict(original)
        final_record.update(
            {
                "transaction_id": verdict_record.transaction_id,
                "verdict": verdict_record.verdict,
                "fraud_flagged": verdict_record.fraud_flagged,
                "reason": verdict_record.reason,
                "stage_outcomes": verdict_record.stage_outcomes,
            }
        )
        write_json(results_dir / f"{verdict_record.transaction_id}.json", final_record)
        envelopes_by_id[verdict_record.transaction_id].unlink()

    write_json(report_path, report.to_dict())

    return report


def main() -> None:
    parser = argparse.ArgumentParser(
        prog="reporting",
        description="Reporting stage for the transaction processing pipeline (terminal stage).",
    )
    parser.add_argument("--input-dir", default="shared/output", help="Directory of finished messages to read.")
    parser.add_argument("--original-dir", default="shared/input", help="Directory holding original records.")
    parser.add_argument("--results-dir", default="shared/results", help="Directory to write final records to.")
    parser.add_argument("--report-path", default="shared/report.json", help="Path to write the aggregate report.")
    args = parser.parse_args()

    report = run_reporting(
        output_dir=Path(args.input_dir),
        input_dir=Path(args.original_dir),
        results_dir=Path(args.results_dir),
        report_path=Path(args.report_path),
    )
    print(f"[reporting] done: {report.to_dict()}")


if __name__ == "__main__":
    main()
