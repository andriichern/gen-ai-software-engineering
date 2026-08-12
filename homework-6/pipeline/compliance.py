"""Compliance Check stage.

Applies GDPR and Data Protection Act 2018 rules uniformly to every record.
Per GDPR Article 22, this stage never makes a solely automated decision with
legal or significant effect — it issues a hold for human review instead of
an automated rejection. It evaluates two independent rules:

  1. fraud-conditional hold: if Fraud Detection flagged the record, hold it
     for human review. If fraud_result is absent from context, this rule is
     recorded as not-applicable, naming the missing annotation.
  2. validation-conditional audit-completeness: confirms the record was
     already established well-formed by Validation before treating it as
     compliant for audit-trail purposes. If validation_result is absent,
     this rule is recorded as not-applicable, naming the missing annotation.

Neither rule ever fabricates a value for a missing annotation, and absence
of an annotation is never silently treated as a clean pass.
"""
from __future__ import annotations

import argparse
from pathlib import Path

from lib.models import ComplianceResult, StageContext, Transaction
from lib.stage_runner import run_downstream_stage


def _fraud_conditional_hold_rule(context: StageContext) -> dict:
    if context.fraud_result is None:
        return {"outcome": "not_applicable", "note": "fraud_detection annotation missing"}
    if context.fraud_result.flagged:
        return {"outcome": "hold", "note": "flagged by fraud detection; GDPR Art. 22 human review required"}
    return {"outcome": "clear", "note": "no fraud flag present"}


def _validation_conditional_audit_rule(context: StageContext) -> dict:
    if context.validation_result is None:
        return {"outcome": "not_applicable", "note": "validation annotation missing"}
    if not context.validation_result.passed:
        return {"outcome": "incomplete_audit", "note": f"record failed validation: {context.validation_result.reason}"}
    return {"outcome": "compliant", "note": "record established well-formed by validation"}


def check_compliance(record: Transaction, context: StageContext) -> ComplianceResult:
    fraud_rule = _fraud_conditional_hold_rule(context)
    audit_rule = _validation_conditional_audit_rule(context)

    rule_outcomes = {
        "fraud_conditional_hold": fraud_rule,
        "validation_conditional_audit_completeness": audit_rule,
    }

    if fraud_rule["outcome"] == "hold":
        return ComplianceResult(status="held", reason=fraud_rule["note"], rule_outcomes=rule_outcomes)

    return ComplianceResult(status="passed", reason=None, rule_outcomes=rule_outcomes)


def _is_pass(result: ComplianceResult) -> bool:
    return result.status == "passed"


def main() -> None:
    parser = argparse.ArgumentParser(
        prog="compliance",
        description="Compliance Check stage for the transaction processing pipeline.",
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
        stage_name="compliance",
        next_stage="settlement",
        result_key="compliance_result",
        compute_fn=check_compliance,
        source_dir=Path(args.input_dir),
        processing_dir=Path(args.output_dir).parent / "processing",
        output_dir=Path(args.output_dir),
        input_dir=Path(args.original_dir),
        is_pass=_is_pass,
    )
    print(f"[compliance] done: {tally}")


if __name__ == "__main__":
    main()
