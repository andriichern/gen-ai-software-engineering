"""Unit tests for pipeline/fraud_detection.py."""
from __future__ import annotations

from decimal import Decimal

import pytest

from lib.exchange_rates import ExchangeRates
from lib.models import StageContext, Transaction
from pipeline.fraud_detection import score_transaction


def _score(data: dict, rates: ExchangeRates, context: StageContext | None = None):
    return score_transaction(Transaction.from_dict(data), context or StageContext(), rates)


# ---------------------------------------------------------------------------
# Happy path
# ---------------------------------------------------------------------------


def test_low_value_domestic_daytime_is_not_flagged(fake_rates, sample_transaction):
    sample_transaction["amount"] = "50.00"
    sample_transaction["metadata"]["country"] = "GB"
    sample_transaction["timestamp"] = "2026-03-16T12:00:00Z"
    result = _score(sample_transaction, fake_rates)
    assert result.flagged is False
    assert Decimal(result.score) < Decimal("0.50")


def test_all_three_factors_triggered_flags_transaction(fake_rates, sample_transaction):
    sample_transaction["amount"] = "20000.00"  # well above 10k USD threshold
    sample_transaction["currency"] = "USD"
    sample_transaction["metadata"]["country"] = "FR"  # cross-border vs GB baseline
    sample_transaction["timestamp"] = "2026-03-16T02:00:00Z"  # outside 06:00-22:00 window
    result = _score(sample_transaction, fake_rates)
    assert result.flagged is True
    assert Decimal(result.score) == Decimal("1.00")
    assert result.factors["high_value_amount"]["triggered"] is True
    assert result.factors["cross_border_mismatch"]["triggered"] is True
    assert result.factors["unusual_hour_timing"]["triggered"] is True


def test_score_is_capped_at_one(fake_rates, sample_transaction):
    sample_transaction["amount"] = "999999999.99"
    sample_transaction["metadata"]["country"] = "FR"
    sample_transaction["timestamp"] = "2026-03-16T02:00:00Z"
    result = _score(sample_transaction, fake_rates)
    assert Decimal(result.score) <= Decimal("1.00")


def test_score_never_rejects_only_flags(fake_rates, sample_transaction):
    """Fraud Detection only flags for review; it never signals rejection."""
    result = _score(sample_transaction, fake_rates)
    assert not hasattr(result, "status")
    assert isinstance(result.flagged, bool)


# ---------------------------------------------------------------------------
# Error / edge cases: not-applicable factors, not raised exceptions
# ---------------------------------------------------------------------------


def test_invalid_amount_marks_high_value_factor_not_applicable(fake_rates, sample_transaction):
    sample_transaction["amount"] = "not-a-number"
    result = _score(sample_transaction, fake_rates)
    assert result.factors["high_value_amount"]["applicable"] is False
    assert "high_value_amount" in " ".join(result.missing)


def test_unknown_currency_marks_high_value_factor_not_applicable(fake_rates, sample_transaction):
    sample_transaction["currency"] = "JPY"  # not in fake_rates
    result = _score(sample_transaction, fake_rates)
    assert result.factors["high_value_amount"]["applicable"] is False


def test_missing_country_marks_cross_border_factor_not_applicable(fake_rates, sample_transaction):
    del sample_transaction["metadata"]["country"]
    result = _score(sample_transaction, fake_rates)
    assert result.factors["cross_border_mismatch"]["applicable"] is False
    assert "cross_border_mismatch" in " ".join(result.missing)


def test_invalid_timestamp_marks_unusual_hour_factor_not_applicable(fake_rates, sample_transaction):
    sample_transaction["timestamp"] = "not-a-timestamp"
    result = _score(sample_transaction, fake_rates)
    assert result.factors["unusual_hour_timing"]["applicable"] is False
    assert "unusual_hour_timing" in " ".join(result.missing)


def test_all_factors_not_applicable_yields_zero_score_not_flagged(fake_rates, sample_transaction):
    sample_transaction["amount"] = "bad"
    sample_transaction["timestamp"] = "bad"
    del sample_transaction["metadata"]["country"]
    result = _score(sample_transaction, fake_rates)
    assert result.score == "0"
    assert result.flagged is False
    assert len(result.missing) == 3


def test_extreme_negative_amount_uses_absolute_value(fake_rates, sample_transaction):
    sample_transaction["amount"] = "-50000.00"
    sample_transaction["currency"] = "USD"
    result = _score(sample_transaction, fake_rates)
    assert result.factors["high_value_amount"]["applicable"] is True
    assert result.factors["high_value_amount"]["triggered"] is True


# ---------------------------------------------------------------------------
# Boundary: exactly at the high-value threshold
# ---------------------------------------------------------------------------


def test_exactly_at_high_value_threshold_triggers(fake_rates, sample_transaction):
    sample_transaction["amount"] = "10000.00"
    sample_transaction["currency"] = "USD"
    result = _score(sample_transaction, fake_rates)
    assert result.factors["high_value_amount"]["triggered"] is True


def test_just_below_high_value_threshold_does_not_trigger(fake_rates, sample_transaction):
    sample_transaction["amount"] = "9999.99"
    sample_transaction["currency"] = "USD"
    result = _score(sample_transaction, fake_rates)
    assert result.factors["high_value_amount"]["triggered"] is False


def test_hour_window_boundary_start_is_within_window(fake_rates, sample_transaction):
    sample_transaction["timestamp"] = "2026-03-16T06:00:00Z"
    result = _score(sample_transaction, fake_rates)
    assert result.factors["unusual_hour_timing"]["triggered"] is False


def test_hour_window_boundary_end_is_within_window(fake_rates, sample_transaction):
    sample_transaction["timestamp"] = "2026-03-16T22:00:00Z"
    result = _score(sample_transaction, fake_rates)
    assert result.factors["unusual_hour_timing"]["triggered"] is False


def test_just_after_window_end_is_unusual(fake_rates, sample_transaction):
    sample_transaction["timestamp"] = "2026-03-16T22:00:01Z"
    result = _score(sample_transaction, fake_rates)
    assert result.factors["unusual_hour_timing"]["triggered"] is True


# ---------------------------------------------------------------------------
# Absent-annotation: fraud detection does not depend on any prior stage, so
# any context (empty or partial) must produce the same, well-defined result
# and never raise.
# ---------------------------------------------------------------------------


def test_empty_context_never_raises_and_scores_normally(fake_rates, sample_transaction):
    result_empty = _score(sample_transaction, fake_rates, StageContext())
    result_default = _score(sample_transaction, fake_rates)
    assert result_empty.to_dict() == result_default.to_dict()


def test_partial_context_with_unrelated_annotation_does_not_affect_result(fake_rates, sample_transaction):
    partial = StageContext.from_dict({"validation_result": {"passed": True, "reason": None, "errors": []}})
    result = _score(sample_transaction, fake_rates, partial)
    direct = _score(sample_transaction, fake_rates)
    assert result.to_dict() == direct.to_dict()


# ---------------------------------------------------------------------------
# Non-termination
# ---------------------------------------------------------------------------


def test_fraud_detection_never_terminates_the_flow(fake_rates, edge_case_transactions):
    for txn in edge_case_transactions:
        result = _score(txn, fake_rates)
        assert result is not None
        assert isinstance(result.flagged, bool)
