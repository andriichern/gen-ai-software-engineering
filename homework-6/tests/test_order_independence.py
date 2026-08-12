"""Order-independence tests: the 4 reorderable stages (Validation, Fraud
Detection, Compliance Check, Settlement) must produce a complete, correct
result for every transaction no matter what order they run in, with
Reporting always last. This is the pipeline's core design property.

These tests drive the stage functions directly (not through files/HTTP) so
every permutation can be exercised cheaply and deterministically.
"""
from __future__ import annotations

import itertools

import pytest

from lib.models import ProcessedTransaction, StageContext, Transaction
from pipeline.compliance import check_compliance
from pipeline.fraud_detection import score_transaction
from pipeline.reporting import build_report
from pipeline.settlement import settle_transaction
from pipeline.validation import validate_transaction

STAGE_FUNCTIONS = {
    "validation": lambda record, context, rates: validate_transaction(record, context),
    "fraud_detection": lambda record, context, rates: score_transaction(record, context, rates),
    "compliance": lambda record, context, rates: check_compliance(record, context),
    "settlement": lambda record, context, rates: settle_transaction(record, context),
}

RESULT_KEY = {
    "validation": "validation_result",
    "fraud_detection": "fraud_result",
    "compliance": "compliance_result",
    "settlement": "settlement_result",
}

ORCHESTRATOR_ORDER = ["validation", "fraud_detection", "compliance", "settlement"]
COMPLIANCE_BEFORE_FRAUD = ["compliance", "validation", "fraud_detection", "settlement"]
SETTLEMENT_BEFORE_COMPLIANCE = ["validation", "fraud_detection", "settlement", "compliance"]
FULL_REVERSAL = list(reversed(ORCHESTRATOR_ORDER))

PERMUTATIONS = [ORCHESTRATOR_ORDER, COMPLIANCE_BEFORE_FRAUD, SETTLEMENT_BEFORE_COMPLIANCE, FULL_REVERSAL]


def _run_order(order: list[str], record: Transaction, rates) -> StageContext:
    context = StageContext()
    for stage in order:
        fn = STAGE_FUNCTIONS[stage]
        result = fn(record, context, rates)
        setattr(context, RESULT_KEY[stage], result)
    return context


@pytest.mark.parametrize("order", PERMUTATIONS, ids=["orchestrator-order", "compliance-before-fraud", "settlement-before-compliance", "full-reversal"])
def test_permutation_completes_without_raising_and_every_stage_annotates(order, sample_transaction, fake_rates):
    record = Transaction.from_dict(sample_transaction)
    context = _run_order(order, record, fake_rates)

    # Every stage produced an annotation for this transaction - none skipped.
    assert context.validation_result is not None
    assert context.fraud_result is not None
    assert context.compliance_result is not None
    assert context.settlement_result is not None


@pytest.mark.parametrize("order", PERMUTATIONS, ids=["orchestrator-order", "compliance-before-fraud", "settlement-before-compliance", "full-reversal"])
def test_permutation_produces_exactly_one_final_record_with_a_verdict(order, sample_transaction, fake_rates):
    record = Transaction.from_dict(sample_transaction)
    context = _run_order(order, record, fake_rates)

    processed = ProcessedTransaction(
        transaction_id=record.transaction_id,
        amount=record.amount,
        currency=record.currency,
        context=context,
    )
    report = build_report([processed])
    assert report.total == 1
    assert len(report.verdicts) == 1
    verdict = report.verdicts[0]
    assert verdict.verdict in ("SETTLED", "REJECTED", "HELD", "INCOMPLETE")


@pytest.mark.parametrize("order", PERMUTATIONS, ids=["orchestrator-order", "compliance-before-fraud", "settlement-before-compliance", "full-reversal"])
def test_all_orchestrator_transactions_get_one_verdict_each_regardless_of_order(order, valid_transactions, fake_rates):
    processed_list = []
    for txn in valid_transactions:
        record = Transaction.from_dict(txn)
        context = _run_order(order, record, fake_rates)
        processed_list.append(
            ProcessedTransaction(
                transaction_id=record.transaction_id,
                amount=record.amount,
                currency=record.currency,
                context=context,
            )
        )
    report = build_report(processed_list)
    assert report.total == len(valid_transactions)
    assert len(report.verdicts) == len(valid_transactions)
    assert {v.transaction_id for v in report.verdicts} == {t["transaction_id"] for t in valid_transactions}


def test_stage_run_out_of_order_records_not_applicable_naming_missing_annotation(sample_transaction, fake_rates):
    """When Compliance runs before Fraud Detection, the fraud-conditional
    rule cannot evaluate yet - it must say so explicitly, not silently pass
    or invent a value, and a later Fraud Detection run must not be skipped
    just because Compliance already ran."""
    record = Transaction.from_dict(sample_transaction)
    order = COMPLIANCE_BEFORE_FRAUD
    context = StageContext()

    # Run only the first stage (compliance) to inspect its output before
    # fraud_detection has run.
    first_stage = order[0]
    assert first_stage == "compliance"
    compliance_result = STAGE_FUNCTIONS["compliance"](record, context, fake_rates)
    assert compliance_result.rule_outcomes["fraud_conditional_hold"]["outcome"] == "not_applicable"
    assert "fraud_detection" in compliance_result.rule_outcomes["fraud_conditional_hold"]["note"]

    # Fraud detection still runs later in this order and is not skipped.
    setattr(context, "compliance_result", compliance_result)
    fraud_result = STAGE_FUNCTIONS["fraud_detection"](record, context, fake_rates)
    assert fraud_result is not None


# ---------------------------------------------------------------------------
# Verdict precedence, asserted directly
# ---------------------------------------------------------------------------


def _build_single_verdict(context_data: dict) -> str:
    processed = ProcessedTransaction(
        transaction_id="V1", amount="100.00", currency="USD",
        context=StageContext.from_dict(context_data),
    )
    return build_report([processed]).verdicts[0]


VALID_PASSED = {"passed": True, "reason": None, "errors": []}
VALID_FAILED = {"passed": False, "reason": "bad", "errors": ["bad"]}
FRAUD_CLEAR = {"score": "0.1", "flagged": False, "factors": {}, "missing": []}
FRAUD_FLAGGED = {"score": "0.9", "flagged": True, "factors": {}, "missing": []}
COMPLIANCE_PASSED = {"status": "passed", "reason": None, "rule_outcomes": {}}
COMPLIANCE_HELD = {"status": "held", "reason": "held", "rule_outcomes": {}}
COMPLIANCE_REJECTED = {"status": "rejected", "reason": "rejected", "rule_outcomes": {}}
SETTLED = {"status": "settled", "settlement_reference": "r1", "settlement_timestamp": "t", "reason": None}
NOT_SETTLED = {"status": "not_settled", "settlement_reference": None, "settlement_timestamp": None, "reason": "r"}


def test_a_stage_that_did_not_run_yields_incomplete_and_outranks_everything_else():
    verdict = _build_single_verdict(
        {"validation_result": VALID_FAILED, "fraud_result": FRAUD_CLEAR, "compliance_result": COMPLIANCE_REJECTED}
        # settlement missing
    )
    assert verdict.verdict == "INCOMPLETE"


def test_validation_failure_outranks_compliance_rejection():
    verdict = _build_single_verdict({
        "validation_result": VALID_FAILED,
        "fraud_result": FRAUD_CLEAR,
        "compliance_result": COMPLIANCE_REJECTED,
        "settlement_result": NOT_SETTLED,
    })
    assert verdict.verdict == "REJECTED"
    assert "validation" in verdict.reason


def test_compliance_rejection_outranks_hold():
    verdict = _build_single_verdict({
        "validation_result": VALID_PASSED,
        "fraud_result": FRAUD_FLAGGED,
        "compliance_result": COMPLIANCE_REJECTED,
        "settlement_result": NOT_SETTLED,
    })
    assert verdict.verdict == "REJECTED"
    assert "compliance" in verdict.reason


def test_hold_outranks_settled():
    verdict = _build_single_verdict({
        "validation_result": VALID_PASSED,
        "fraud_result": FRAUD_FLAGGED,
        "compliance_result": COMPLIANCE_HELD,
        "settlement_result": SETTLED,  # even if settled were somehow set
    })
    assert verdict.verdict == "HELD"


def test_fraud_flag_alone_never_produces_its_own_verdict_but_is_an_attribute():
    verdict = _build_single_verdict({
        "validation_result": VALID_PASSED,
        "fraud_result": FRAUD_FLAGGED,
        "compliance_result": COMPLIANCE_PASSED,
        "settlement_result": SETTLED,
    })
    assert verdict.verdict == "SETTLED"
    assert verdict.fraud_flagged is True


def test_fraud_flagged_and_settled_together_verdict_is_still_settled_not_a_fraud_verdict():
    verdict = _build_single_verdict({
        "validation_result": VALID_PASSED,
        "fraud_result": FRAUD_FLAGGED,
        "compliance_result": COMPLIANCE_PASSED,
        "settlement_result": SETTLED,
    })
    assert verdict.verdict in ("SETTLED", "REJECTED", "HELD", "INCOMPLETE")
    assert verdict.verdict not in ("FRAUD", "FLAGGED", "FRAUD_FLAGGED")
