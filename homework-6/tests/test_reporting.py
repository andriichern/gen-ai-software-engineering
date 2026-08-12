"""Unit tests for pipeline/reporting.py's pure build_report() function."""
from __future__ import annotations

from lib.models import ProcessedTransaction, StageContext


VALID_PASSED = {"passed": True, "reason": None, "errors": []}
VALID_FAILED = {"passed": False, "reason": "bad amount", "errors": ["bad amount"]}
FRAUD_CLEAR = {"score": "0.10", "flagged": False, "factors": {}, "missing": []}
FRAUD_FLAGGED = {"score": "0.80", "flagged": True, "factors": {}, "missing": []}
COMPLIANCE_PASSED = {"status": "passed", "reason": None, "rule_outcomes": {}}
COMPLIANCE_HELD = {"status": "held", "reason": "flagged", "rule_outcomes": {}}
COMPLIANCE_REJECTED = {"status": "rejected", "reason": "sanctions", "rule_outcomes": {}}
SETTLEMENT_SETTLED = {
    "status": "settled",
    "settlement_reference": "ref-1",
    "settlement_timestamp": "2026-03-16T10:00:00+00:00",
    "reason": "ok",
}
SETTLEMENT_NOT_SETTLED = {
    "status": "not_settled",
    "settlement_reference": None,
    "settlement_timestamp": None,
    "reason": "held",
}


def _processed(transaction_id: str, context_data: dict, amount="100.00", currency="USD") -> ProcessedTransaction:
    return ProcessedTransaction(
        transaction_id=transaction_id,
        amount=amount,
        currency=currency,
        context=StageContext.from_dict(context_data),
    )


def _import_build_report():
    from pipeline.reporting import build_report

    return build_report


# ---------------------------------------------------------------------------
# Happy path / verdict precedence
# ---------------------------------------------------------------------------


def test_fully_settled_transaction_gets_settled_verdict():
    build_report = _import_build_report()
    record = _processed(
        "T1",
        {
            "validation_result": VALID_PASSED,
            "fraud_result": FRAUD_CLEAR,
            "compliance_result": COMPLIANCE_PASSED,
            "settlement_result": SETTLEMENT_SETTLED,
        },
    )
    report = build_report([record])
    assert report.verdicts[0].verdict == "SETTLED"
    assert report.settled == 1
    assert report.total == 1


def test_failed_validation_outranks_compliance_rejected():
    build_report = _import_build_report()
    record = _processed(
        "T2",
        {
            "validation_result": VALID_FAILED,
            "fraud_result": FRAUD_CLEAR,
            "compliance_result": COMPLIANCE_REJECTED,
            "settlement_result": SETTLEMENT_NOT_SETTLED,
        },
    )
    report = build_report([record])
    verdict = report.verdicts[0]
    assert verdict.verdict == "REJECTED"
    assert "validation" in verdict.reason


def test_compliance_rejected_outranks_held():
    """Even if validation passed, a rejected compliance status must not be
    overridden by a downstream held-style condition (rejected always wins
    over held in the precedence table)."""
    build_report = _import_build_report()
    record = _processed(
        "T3",
        {
            "validation_result": VALID_PASSED,
            "fraud_result": FRAUD_FLAGGED,
            "compliance_result": COMPLIANCE_REJECTED,
            "settlement_result": SETTLEMENT_NOT_SETTLED,
        },
    )
    report = build_report([record])
    verdict = report.verdicts[0]
    assert verdict.verdict == "REJECTED"
    assert "compliance" in verdict.reason


def test_compliance_held_outranks_settled():
    build_report = _import_build_report()
    record = _processed(
        "T4",
        {
            "validation_result": VALID_PASSED,
            "fraud_result": FRAUD_FLAGGED,
            "compliance_result": COMPLIANCE_HELD,
            "settlement_result": SETTLEMENT_NOT_SETTLED,
        },
    )
    report = build_report([record])
    verdict = report.verdicts[0]
    assert verdict.verdict == "HELD"
    assert "compliance" in verdict.reason


def test_a_stage_that_did_not_run_yields_incomplete_and_outranks_everything():
    build_report = _import_build_report()
    # Validation passed, fraud clear, compliance passed - but settlement
    # never ran (missing annotation). INCOMPLETE must still win.
    record = _processed(
        "T5",
        {
            "validation_result": VALID_PASSED,
            "fraud_result": FRAUD_CLEAR,
            "compliance_result": COMPLIANCE_PASSED,
        },
    )
    report = build_report([record])
    verdict = report.verdicts[0]
    assert verdict.verdict == "INCOMPLETE"
    assert "settlement" in verdict.reason


def test_incomplete_outranks_a_would_be_rejected_verdict():
    """Even a record that would otherwise resolve to REJECTED must report
    INCOMPLETE if a stage never ran, because the verdict cannot be trusted
    without every annotation."""
    build_report = _import_build_report()
    record = _processed(
        "T6",
        {
            "validation_result": VALID_FAILED,
            "fraud_result": FRAUD_CLEAR,
            "compliance_result": COMPLIANCE_REJECTED,
            # settlement missing
        },
    )
    report = build_report([record])
    verdict = report.verdicts[0]
    assert verdict.verdict == "INCOMPLETE"


def test_fraud_flag_alone_never_produces_its_own_verdict():
    """A fraud flag is an attribute of whichever verdict applies - it never
    becomes a verdict by itself."""
    build_report = _import_build_report()
    record = _processed(
        "T7",
        {
            "validation_result": VALID_PASSED,
            "fraud_result": FRAUD_FLAGGED,
            "compliance_result": COMPLIANCE_PASSED,
            "settlement_result": SETTLEMENT_SETTLED,
        },
    )
    report = build_report([record])
    verdict = report.verdicts[0]
    assert verdict.verdict == "SETTLED"
    assert verdict.fraud_flagged is True
    assert verdict.verdict not in ("FRAUD", "FLAGGED")


def test_no_final_verdict_leaves_fraud_flagged_false_when_no_fraud_result():
    build_report = _import_build_report()
    record = _processed("T8", {})
    report = build_report([record])
    assert report.verdicts[0].fraud_flagged is False


# ---------------------------------------------------------------------------
# Aggregate counts
# ---------------------------------------------------------------------------


def test_aggregate_counts_across_multiple_records():
    build_report = _import_build_report()
    records = [
        _processed("A", {
            "validation_result": VALID_PASSED, "fraud_result": FRAUD_CLEAR,
            "compliance_result": COMPLIANCE_PASSED, "settlement_result": SETTLEMENT_SETTLED,
        }),
        _processed("B", {
            "validation_result": VALID_PASSED, "fraud_result": FRAUD_FLAGGED,
            "compliance_result": COMPLIANCE_HELD, "settlement_result": SETTLEMENT_NOT_SETTLED,
        }),
        _processed("C", {
            "validation_result": VALID_FAILED, "fraud_result": FRAUD_CLEAR,
            "compliance_result": COMPLIANCE_REJECTED, "settlement_result": SETTLEMENT_NOT_SETTLED,
        }),
        _processed("D", {}),
    ]
    report = build_report(records)
    assert report.total == 4
    assert report.settled == 1
    assert report.held == 1
    assert report.rejected == 1
    assert report.incomplete == 1
    assert report.fraud_flagged == 1
    assert report.compliance_held == 1
    assert "4 transaction(s)" in report.summary


def test_empty_batch_yields_zeroed_report():
    build_report = _import_build_report()
    report = build_report([])
    assert report.total == 0
    assert report.settled == 0
    assert report.verdicts == []


# ---------------------------------------------------------------------------
# Every transaction gets exactly one verdict record
# ---------------------------------------------------------------------------


def test_one_verdict_per_input_record():
    build_report = _import_build_report()
    records = [_processed(f"TXN{i}", {}) for i in range(5)]
    report = build_report(records)
    assert len(report.verdicts) == 5
    assert {v.transaction_id for v in report.verdicts} == {f"TXN{i}" for i in range(5)}


def test_build_report_never_raises_for_any_context_shape():
    build_report = _import_build_report()
    shapes = [
        {},
        {"validation_result": VALID_PASSED},
        {"validation_result": VALID_PASSED, "fraud_result": FRAUD_FLAGGED},
        {"validation_result": VALID_PASSED, "fraud_result": FRAUD_FLAGGED, "compliance_result": COMPLIANCE_HELD},
        {
            "validation_result": VALID_PASSED, "fraud_result": FRAUD_FLAGGED,
            "compliance_result": COMPLIANCE_HELD, "settlement_result": SETTLEMENT_NOT_SETTLED,
        },
    ]
    records = [_processed(f"S{i}", shape) for i, shape in enumerate(shapes)]
    report = build_report(records)
    assert report.total == len(shapes)
    for verdict in report.verdicts:
        assert verdict.verdict in ("SETTLED", "REJECTED", "HELD", "INCOMPLETE")
