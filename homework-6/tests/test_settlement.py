"""Unit tests for pipeline/settlement.py."""
from __future__ import annotations

import uuid

from lib.models import StageContext, Transaction
from pipeline.settlement import settle_transaction


def _settle(data: dict, context: StageContext):
    return settle_transaction(Transaction.from_dict(data), context)


COMPLIANCE_PASSED = {"status": "passed", "reason": None, "rule_outcomes": {}}
COMPLIANCE_HELD = {"status": "held", "reason": "flagged by fraud detection", "rule_outcomes": {}}
COMPLIANCE_REJECTED = {"status": "rejected", "reason": "sanctions match", "rule_outcomes": {}}


# ---------------------------------------------------------------------------
# Happy path
# ---------------------------------------------------------------------------


def test_passed_compliance_settles_transaction(sample_transaction):
    context = StageContext.from_dict({"compliance_result": COMPLIANCE_PASSED})
    result = _settle(sample_transaction, context)
    assert result.status == "settled"
    assert result.settlement_reference is not None
    uuid.UUID(result.settlement_reference)  # a genuine settlement reference
    assert result.settlement_timestamp is not None


def test_settlement_reference_is_unique_per_call(sample_transaction):
    context = StageContext.from_dict({"compliance_result": COMPLIANCE_PASSED})
    r1 = _settle(sample_transaction, context)
    r2 = _settle(sample_transaction, context)
    assert r1.settlement_reference != r2.settlement_reference


# ---------------------------------------------------------------------------
# Held/rejected -> never settled
# ---------------------------------------------------------------------------


def test_held_transaction_is_not_settled(sample_transaction):
    context = StageContext.from_dict({"compliance_result": COMPLIANCE_HELD})
    result = _settle(sample_transaction, context)
    assert result.status == "not_settled"
    assert "held" in result.reason
    assert result.settlement_reference is None


def test_rejected_transaction_is_not_settled(sample_transaction):
    context = StageContext.from_dict({"compliance_result": COMPLIANCE_REJECTED})
    result = _settle(sample_transaction, context)
    assert result.status == "not_settled"
    assert "rejected" in result.reason
    assert result.settlement_reference is None


def test_unknown_compliance_status_is_not_settled(sample_transaction):
    context = StageContext.from_dict(
        {"compliance_result": {"status": "pending_review", "reason": None, "rule_outcomes": {}}}
    )
    result = _settle(sample_transaction, context)
    assert result.status == "not_settled"
    assert "unclear" in result.reason


# ---------------------------------------------------------------------------
# Edge cases: extreme amounts still settle the same way (settlement does not
# gate on amount, only on compliance outcome)
# ---------------------------------------------------------------------------


def test_very_high_amount_settles_normally(sample_transaction):
    sample_transaction["amount"] = "999999999.99"
    context = StageContext.from_dict({"compliance_result": COMPLIANCE_PASSED})
    result = _settle(sample_transaction, context)
    assert result.status == "settled"


def test_negative_refund_amount_settles_normally(sample_transaction):
    sample_transaction["amount"] = "-50000.00"
    context = StageContext.from_dict({"compliance_result": COMPLIANCE_PASSED})
    result = _settle(sample_transaction, context)
    assert result.status == "settled"


# ---------------------------------------------------------------------------
# Absent-annotation cases: settlement depends on compliance's outcome. A
# missing compliance annotation must be recorded not_settled, naming the
# missing annotation - never raise, never default to settled.
# ---------------------------------------------------------------------------


def test_empty_context_is_not_settled_naming_compliance(sample_transaction):
    result = _settle(sample_transaction, StageContext())
    assert result.status == "not_settled"
    assert "compliance" in result.reason
    assert result.settlement_reference is None


def test_partial_context_missing_compliance_only(sample_transaction):
    other = StageContext.from_dict(
        {"fraud_result": {"score": "0.1", "flagged": False, "factors": {}, "missing": []}}
    )
    result = _settle(sample_transaction, other)
    assert result.status == "not_settled"
    assert "compliance" in result.reason


def test_absent_compliance_never_raises(sample_transaction):
    _settle(sample_transaction, StageContext())  # must not raise


def test_absent_compliance_never_defaults_to_settled(sample_transaction):
    result_missing = _settle(sample_transaction, StageContext())
    result_passed = _settle(sample_transaction, StageContext.from_dict({"compliance_result": COMPLIANCE_PASSED}))
    assert result_missing.status == "not_settled"
    assert result_passed.status == "settled"


# ---------------------------------------------------------------------------
# Non-termination
# ---------------------------------------------------------------------------


def test_settlement_never_terminates_the_flow(sample_transaction, edge_case_transactions):
    for txn in [sample_transaction] + edge_case_transactions:
        for ctx_data in ({}, {"compliance_result": COMPLIANCE_HELD}, {"compliance_result": COMPLIANCE_PASSED}):
            result = _settle(txn, StageContext.from_dict(ctx_data))
            assert result is not None
            assert result.status in ("settled", "not_settled")
