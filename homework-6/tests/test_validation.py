"""Unit tests for pipeline/validation.py."""
from __future__ import annotations

import json

import pytest

from lib.models import StageContext, Transaction
from pipeline.validation import run_standalone_check, validate_transaction


def _validate(data: dict, context: StageContext | None = None):
    return validate_transaction(Transaction.from_dict(data), context or StageContext())


# ---------------------------------------------------------------------------
# Happy path
# ---------------------------------------------------------------------------


def test_valid_transaction_passes(sample_transaction):
    result = _validate(sample_transaction)
    assert result.passed is True
    assert result.reason is None
    assert result.errors == []


def test_valid_transactions_fixture_all_pass(valid_transactions):
    for txn in valid_transactions:
        result = _validate(txn)
        assert result.passed is True, f"{txn['transaction_id']} unexpectedly failed: {result.reason}"


# ---------------------------------------------------------------------------
# Error cases: missing fields, wrong types, invalid values
# ---------------------------------------------------------------------------


def test_missing_amount_fails(sample_transaction):
    del sample_transaction["amount"]
    result = _validate(sample_transaction)
    assert result.passed is False
    assert any("amount" in e for e in result.errors)


@pytest.mark.parametrize(
    "field",
    ["transaction_id", "timestamp", "source_account", "destination_account", "amount", "currency", "transaction_type"],
)
def test_each_required_field_missing_fails(sample_transaction, field):
    sample_transaction[field] = ""
    result = _validate(sample_transaction)
    assert result.passed is False
    assert any(field in e for e in result.errors)


def test_amount_as_number_not_string_fails(sample_transaction):
    sample_transaction["amount"] = 1500.00
    result = _validate(sample_transaction)
    assert result.passed is False
    assert any("decimal" in e for e in result.errors)


def test_invalid_decimal_amount_fails(sample_transaction):
    sample_transaction["amount"] = "not-a-number"
    result = _validate(sample_transaction)
    assert result.passed is False


def test_invalid_currency_code_fails(sample_transaction):
    sample_transaction["currency"] = "XYZ"
    result = _validate(sample_transaction)
    assert result.passed is False
    assert any("currency" in e for e in result.errors)


def test_invalid_timestamp_fails(sample_transaction):
    sample_transaction["timestamp"] = "not-a-valid-timestamp"
    result = _validate(sample_transaction)
    assert result.passed is False
    assert any("timestamp" in e for e in result.errors)


def test_timestamp_without_timezone_fails(sample_transaction):
    sample_transaction["timestamp"] = "2026-03-16T10:00:00"  # no offset/Z
    result = _validate(sample_transaction)
    assert result.passed is False


def test_invalid_transactions_fixture_all_fail_except_type_flexible_fields(invalid_transactions):
    for txn in invalid_transactions:
        result = _validate(txn)
        # Every entry in the invalid fixture is deliberately malformed in at
        # least one required-field/type/format way, except metadata-only
        # issues (metadata is not itself a required field).
        if txn["transaction_id"] in ("INVALID_006", "INVALID_007"):
            continue
        assert result.passed is False, f"{txn['transaction_id']} unexpectedly passed"


# ---------------------------------------------------------------------------
# Edge cases
# ---------------------------------------------------------------------------


def test_edge_case_transactions_are_well_formed(edge_case_transactions):
    """The edge-case fixture varies amount/timing/currency extremes, not
    well-formedness, so validation should still pass for all of them."""
    for txn in edge_case_transactions:
        result = _validate(txn)
        assert result.passed is True, f"{txn['transaction_id']}: {result.reason}"


def test_very_high_amount_is_a_valid_decimal(sample_transaction):
    sample_transaction["amount"] = "999999999.99"
    result = _validate(sample_transaction)
    assert result.passed is True


def test_negative_amount_refund_is_valid(sample_transaction):
    sample_transaction["amount"] = "-50000.00"
    result = _validate(sample_transaction)
    assert result.passed is True


def test_null_currency_fails(sample_transaction):
    sample_transaction["currency"] = None
    result = _validate(sample_transaction)
    assert result.passed is False


# ---------------------------------------------------------------------------
# Absent-annotation cases: validation depends only on the record, so an
# empty or partial context must never change the outcome, never raise, and
# never be consulted.
# ---------------------------------------------------------------------------


def test_empty_context_does_not_affect_result(sample_transaction):
    result_empty = _validate(sample_transaction, StageContext())
    result_default = _validate(sample_transaction)
    assert result_empty.to_dict() == result_default.to_dict()


def test_partial_context_does_not_affect_result(sample_transaction):
    partial = StageContext.from_dict({"fraud_result": {"score": "0.9", "flagged": True}})
    result = _validate(sample_transaction, partial)
    assert result.passed is True
    # Never recomputes another stage's result: no fraud/compliance fields on
    # ValidationResult.
    assert not hasattr(result, "fraud_result")
    assert not hasattr(result, "score")


def test_context_never_raises_for_validation(sample_transaction):
    # Passing any context shape must never raise - validation is
    # context-independent by contract.
    _validate(sample_transaction, StageContext())


# ---------------------------------------------------------------------------
# Non-termination: validate_transaction never signals the record should
# leave the flow - it always returns a ValidationResult, pass or fail.
# ---------------------------------------------------------------------------


def test_validation_never_terminates_the_flow(invalid_transactions):
    for txn in invalid_transactions:
        result = _validate(txn)
        assert result is not None
        assert isinstance(result.passed, bool)


# ---------------------------------------------------------------------------
# run_standalone_check (--check CLI mode)
# ---------------------------------------------------------------------------


def test_run_standalone_check_reports_totals(tmp_path, valid_transactions, invalid_transactions):
    dataset = valid_transactions + [t for t in invalid_transactions if t["transaction_id"] not in ("INVALID_006", "INVALID_007")]
    source = tmp_path / "dataset.json"
    source.write_text(json.dumps(dataset))

    report = run_standalone_check(str(source))
    assert report["total"] == len(dataset)
    assert report["valid"] == len(valid_transactions)
    assert report["invalid"] == len(dataset) - len(valid_transactions)
    assert len(report["results"]) == len(dataset)


def test_run_standalone_check_is_read_only(tmp_path, valid_transactions):
    source = tmp_path / "dataset.json"
    source.write_text(json.dumps(valid_transactions))
    before = source.read_text()

    run_standalone_check(str(source))

    assert source.read_text() == before


def test_run_standalone_check_missing_source_raises(tmp_path):
    with pytest.raises(FileNotFoundError):
        run_standalone_check(str(tmp_path / "does-not-exist.json"))
