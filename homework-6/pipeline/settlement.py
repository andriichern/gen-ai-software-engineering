"""Settlement Processing stage.

Settles each transaction that passed Compliance Check via an internal
simulated ledger — no external network calls. Held or rejected transactions
are marked not-settled with the reason. If Compliance's outcome is absent
from context, settlement is recorded not-settled, naming that the compliance
annotation was missing (never inventing a compliance outcome).

Audit/settlement records containing account or PII data are retained for 5
years under GDPR's legal-obligation basis, then purged or anonymized; this
stage does not implement retention/purge scheduling itself (out of scope for
a single processing run) but records the retention basis in its outcome.
"""
from __future__ import annotations

import argparse
import uuid
from pathlib import Path

from lib.message_io import now_iso
from lib.models import SettlementResult, StageContext, Transaction
from lib.stage_runner import run_downstream_stage

RETENTION_NOTE = "retained 5 years under GDPR legal-obligation basis, then purged or anonymized"


def settle_transaction(record: Transaction, context: StageContext) -> SettlementResult:
    if context.compliance_result is None:
        return SettlementResult(
            status="not_settled",
            reason="compliance status unknown: compliance annotation missing",
        )

    if context.compliance_result.status == "held":
        return SettlementResult(
            status="not_settled",
            reason=f"held by compliance: {context.compliance_result.reason}",
        )

    if context.compliance_result.status == "rejected":
        return SettlementResult(
            status="not_settled",
            reason=f"rejected by compliance: {context.compliance_result.reason}",
        )

    if context.compliance_result.status != "passed":
        return SettlementResult(
            status="not_settled",
            reason=f"compliance outcome unclear: {context.compliance_result.status}",
        )

    return SettlementResult(
        status="settled",
        settlement_reference=str(uuid.uuid4()),
        settlement_timestamp=now_iso(),
        reason=RETENTION_NOTE,
    )


def _is_pass(result: SettlementResult) -> bool:
    return result.status == "settled"


def main() -> None:
    parser = argparse.ArgumentParser(
        prog="settlement",
        description="Settlement Processing stage for the transaction processing pipeline.",
    )
    parser.add_argument("--input-dir", default="shared/output", help="Directory of upstream messages to read.")
    parser.add_argument("--output-dir", default="shared/output", help="Directory to write annotated messages to.")
    parser.add_argument(
        "--original-dir",
        default="shared/input",
        help="Directory holding original transaction records.",
    )
    args = parser.parse_args()

    tally = run_downstream_stage(
        stage_name="settlement",
        next_stage="reporting",
        result_key="settlement_result",
        compute_fn=settle_transaction,
        source_dir=Path(args.input_dir),
        processing_dir=Path(args.output_dir).parent / "processing",
        output_dir=Path(args.output_dir),
        input_dir=Path(args.original_dir),
        is_pass=_is_pass,
    )
    print(f"[settlement] done: {tally}")


if __name__ == "__main__":
    main()
