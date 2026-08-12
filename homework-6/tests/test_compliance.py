"""Unit tests for pipeline/compliance.py."""
from __future__ import annotations

from lib.models import StageContext, Transaction
from pipeline.compliance import check_compliance


def _check(data: dict, context: StageContext):
    return check_compliance(Transaction.from_dict(data), context)


FRAUD_FLAGGED = {"score": "0.90", "flagged": True, "factors": {}, "missing": []}
FRAUD_CLEAR = {"score": "0.10", "flagged": False, "factors": {}, "missing": []}
VALID_PASSED = {"passed": True, "reason": None, "errors": []}
VALID_FAILED = {"passed": False, "reason": "missing required field: amount", "errors": ["missing required field: amount"]}


# ---------------------------------------------------------------------------
# Happy path
# ---------------------------------------------------------------------------


def test_clean_transaction_passes(sample_transaction):
    context = StageContext.from_dict({"fraud_result": FRAUD_CLEAR, "validation_result": VALID_PASSED})
    result = _check(sample_transaction, context)
    assert result.status == "passed"
    assert result.reason is None


def test_fraud_flagged_transaction_is_held_not_rejected(sample_transaction):
    """Per GDPR Art. 22, compliance never auto-rejects: it holds for human
    review instead."""
    context = StageContext.from_dict({"fraud_result": FRAUD_FLAGGED, "validation_result": VALID_PASSED})
    result = _check(sample_transaction, context)
    assert result.status == "held"
    assert result.reason is not None
    assert result.status != "rejected"


def test_compliance_never_produces_rejected_status(sample_transaction, edge_case_transactions):
    """check_compliance's only two outcomes are 'passed' and 'held' -
    rejection is never one of its statuses (Art. 22 automated-decision ban)."""
    for txn in [sample_transaction] + edge_case_transactions:
        for fraud in (FRAUD_FLAGGED, FRAUD_CLEAR, None):
            ctx_data = {"validation_result": VALID_PASSED}
            if fraud is not None:
                ctx_data["fraud_result"] = fraud
            result = _check(txn, StageContext.from_dict(ctx_data))
            assert result.status in ("passed", "held")


# ---------------------------------------------------------------------------
# Rule outcomes structure
# ---------------------------------------------------------------------------


def test_rule_outcomes_include_both_rules(sample_transaction):
    context = StageContext.from_dict({"fraud_result": FRAUD_CLEAR, "validation_result": VALID_PASSED})
    result = _check(sample_transaction, context)
    assert set(result.rule_outcomes) == {"fraud_conditional_hold", "validation_conditional_audit_completeness"}


def test_failed_validation_marks_incomplete_audit(sample_transaction):
    context = StageContext.from_dict({"fraud_result": FRAUD_CLEAR, "validation_result": VALID_FAILED})
    result = _check(sample_transaction, context)
    assert result.rule_outcomes["validation_conditional_audit_completeness"]["outcome"] == "incomplete_audit"
    # Failing validation does not itself cause a hold - only fraud does.
    assert result.status == "passed"


# ---------------------------------------------------------------------------
# Absent-annotation cases: each rule depends on one specific stage's
# annotation. Missing that annotation must yield an explicit not-applicable
# outcome naming it, never a raise, a default, or a fabricated clean pass.
# ---------------------------------------------------------------------------


def test_empty_context_both_rules_not_applicable(sample_transaction):
    result = _check(sample_transaction, StageContext())
    assert result.rule_outcomes["fraud_conditional_hold"]["outcome"] == "not_applicable"
    assert "fraud_detection" in result.rule_outcomes["fraud_conditional_hold"]["note"]
    assert result.rule_outcomes["validation_conditional_audit_completeness"]["outcome"] == "not_applicable"
    assert "validation" in result.rule_outcomes["validation_conditional_audit_completeness"]["note"]
    # Absence is never silently treated as a clean pass verdict overall -
    # status still resolves, but every rule that could not run says so.
    assert result.status == "passed"  # no hold rule triggered = passed overall


def test_partial_context_missing_fraud_only(sample_transaction):
    context = StageContext.from_dict({"validation_result": VALID_PASSED})
    result = _check(sample_transaction, context)
    assert result.rule_outcomes["fraud_conditional_hold"]["outcome"] == "not_applicable"
    assert result.rule_outcomes["validation_conditional_audit_completeness"]["outcome"] == "compliant"


def test_partial_context_missing_validation_only(sample_transaction):
    context = StageContext.from_dict({"fraud_result": FRAUD_CLEAR})
    result = _check(sample_transaction, context)
    assert result.rule_outcomes["fraud_conditional_hold"]["outcome"] == "clear"
    assert result.rule_outcomes["validation_conditional_audit_completeness"]["outcome"] == "not_applicable"


def test_absent_fraud_annotation_never_raises(sample_transaction):
    _check(sample_transaction, StageContext())  # must not raise


def test_absent_annotation_never_substitutes_a_default_flag(sample_transaction):
    """A missing fraud_result must never be treated as 'not flagged' (a
    silently assumed default) - it must be recorded not_applicable."""
    result_missing = _check(sample_transaction, StageContext())
    result_explicit_clear = _check(
        sample_transaction, StageContext.from_dict({"fraud_result": FRAUD_CLEAR})
    )
    assert result_missing.rule_outcomes["fraud_conditional_hold"]["outcome"] == "not_applicable"
    assert result_explicit_clear.rule_outcomes["fraud_conditional_hold"]["outcome"] == "clear"
    assert result_missing.rule_outcomes["fraud_conditional_hold"] != result_explicit_clear.rule_outcomes["fraud_conditional_hold"]


# ---------------------------------------------------------------------------
# Non-termination
# ---------------------------------------------------------------------------


def test_compliance_never_terminates_the_flow(sample_transaction, edge_case_transactions):
    for txn in [sample_transaction] + edge_case_transactions:
        result = _check(txn, StageContext())
        assert result is not None
        assert result.status in ("passed", "held")
