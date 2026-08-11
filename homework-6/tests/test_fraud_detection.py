"""Unit tests for the Fraud Detection stage."""
from decimal import Decimal

import pytest

from pipeline.fraud_detection import _usd_equivalent, score_transaction


class TestUsdEquivalent:
    """Tests for _usd_equivalent helper function."""

    def test_usd_currency_returns_same_amount(self, sample_exchange_rates):
        """USD amounts should return the same value."""
        result = _usd_equivalent(Decimal("1000"), "USD", sample_exchange_rates)
        assert result == Decimal("1000")

    def test_convert_eur_to_usd(self, sample_exchange_rates):
        """EUR to USD conversion should work."""
        eur_amount = Decimal("1000")
        result = _usd_equivalent(eur_amount, "EUR", sample_exchange_rates)
        # 1000 EUR / 0.92 = 1086.957...
        assert result == eur_amount / Decimal("0.92")

    def test_convert_gbp_to_usd(self, sample_exchange_rates):
        """GBP to USD conversion should work."""
        gbp_amount = Decimal("500")
        result = _usd_equivalent(gbp_amount, "GBP", sample_exchange_rates)
        # 500 GBP / 0.79
        assert result == gbp_amount / Decimal("0.79")

    def test_missing_exchange_rate_raises_error(self, sample_exchange_rates):
        """Missing exchange rate should raise ValueError."""
        with pytest.raises(ValueError, match="no exchange rate available"):
            _usd_equivalent(Decimal("1000"), "AUD", sample_exchange_rates)

    def test_zero_amount_returns_zero(self, sample_exchange_rates):
        """Zero amount should return zero."""
        result = _usd_equivalent(Decimal("0"), "EUR", sample_exchange_rates)
        assert result == Decimal("0")

    def test_very_large_amount(self, sample_exchange_rates):
        """Very large amounts should convert correctly."""
        large = Decimal("999999999.99")
        result = _usd_equivalent(large, "EUR", sample_exchange_rates)
        assert result == large / Decimal("0.92")


class TestScoreTransaction:
    """Tests for score_transaction function."""

    def test_low_value_domestic_normal_hours(self, sample_transaction, sample_exchange_rates):
        """Low value, domestic, normal hours should have low fraud score."""
        sample_transaction["amount"] = "1000.00"
        sample_transaction["timestamp"] = "2026-03-16T12:00:00Z"
        sample_transaction["metadata"]["country"] = "GB"

        result = score_transaction(sample_transaction, sample_exchange_rates)

        assert "score" in result
        score = Decimal(result["score"])
        assert score < Decimal("0.50")
        assert not result["factors"]["high_value_amount"]
        assert not result["factors"]["cross_border_mismatch"]
        assert not result["factors"]["unusual_hour_timing"]

    def test_high_value_adds_score(self, sample_transaction, sample_exchange_rates):
        """High value transaction should add HIGH_VALUE_WEIGHT to score."""
        sample_transaction["amount"] = "20000.00"
        sample_transaction["timestamp"] = "2026-03-16T12:00:00Z"
        sample_transaction["metadata"]["country"] = "GB"

        result = score_transaction(sample_transaction, sample_exchange_rates)

        assert result["factors"]["high_value_amount"]
        score = Decimal(result["score"])
        assert score >= Decimal("0.50")

    def test_cross_border_adds_score(self, sample_transaction, sample_exchange_rates):
        """Cross-border transaction should add CROSS_BORDER_WEIGHT to score."""
        sample_transaction["amount"] = "1000.00"
        sample_transaction["timestamp"] = "2026-03-16T12:00:00Z"
        sample_transaction["metadata"]["country"] = "FR"

        result = score_transaction(sample_transaction, sample_exchange_rates)

        assert result["factors"]["cross_border_mismatch"]
        score = Decimal(result["score"])
        assert score >= Decimal("0.30")

    def test_unusual_hour_adds_score(self, sample_transaction, sample_exchange_rates):
        """Transaction outside 6am-10pm UTC should add UNUSUAL_HOUR_WEIGHT."""
        sample_transaction["amount"] = "1000.00"
        sample_transaction["timestamp"] = "2026-03-16T03:00:00Z"  # 3am UTC
        sample_transaction["metadata"]["country"] = "GB"

        result = score_transaction(sample_transaction, sample_exchange_rates)

        assert result["factors"]["unusual_hour_timing"]
        score = Decimal(result["score"])
        assert score >= Decimal("0.20")

    def test_multiple_risk_factors_accumulate(self, sample_transaction, sample_exchange_rates):
        """Multiple risk factors should accumulate in score."""
        sample_transaction["amount"] = "25000.00"  # high value
        sample_transaction["timestamp"] = "2026-03-16T05:00:00Z"  # unusual hour
        sample_transaction["metadata"]["country"] = "DE"  # cross-border

        result = score_transaction(sample_transaction, sample_exchange_rates)

        assert result["factors"]["high_value_amount"]
        assert result["factors"]["cross_border_mismatch"]
        assert result["factors"]["unusual_hour_timing"]

        score = Decimal(result["score"])
        # 0.50 + 0.30 + 0.20 = 1.00 (capped)
        assert score == Decimal("1.00")

    def test_score_capped_at_one(self, sample_transaction, sample_exchange_rates):
        """Score should never exceed 1.00."""
        sample_transaction["amount"] = "999999999.99"
        sample_transaction["timestamp"] = "2026-03-16T03:00:00Z"
        sample_transaction["metadata"]["country"] = "FR"

        result = score_transaction(sample_transaction, sample_exchange_rates)

        score = Decimal(result["score"])
        assert score <= Decimal("1.00")

    def test_flagged_when_score_above_threshold(self, sample_transaction, sample_exchange_rates):
        """Transaction should be flagged when score >= 0.50."""
        sample_transaction["amount"] = "25000.00"
        sample_transaction["timestamp"] = "2026-03-16T12:00:00Z"
        sample_transaction["metadata"]["country"] = "GB"

        result = score_transaction(sample_transaction, sample_exchange_rates)

        assert result["flagged"] is True

    def test_not_flagged_when_score_below_threshold(self, sample_transaction, sample_exchange_rates):
        """Transaction should not be flagged when score < 0.50."""
        sample_transaction["amount"] = "1000.00"
        sample_transaction["timestamp"] = "2026-03-16T12:00:00Z"
        sample_transaction["metadata"]["country"] = "GB"

        result = score_transaction(sample_transaction, sample_exchange_rates)

        assert result["flagged"] is False

    def test_negative_amount_treated_as_positive_for_scoring(self, sample_transaction, sample_exchange_rates):
        """Negative amounts (refunds) should be scored on absolute value."""
        sample_transaction["amount"] = "-25000.00"
        sample_transaction["timestamp"] = "2026-03-16T12:00:00Z"
        sample_transaction["metadata"]["country"] = "GB"

        result = score_transaction(sample_transaction, sample_exchange_rates)

        assert result["factors"]["high_value_amount"]

    def test_missing_country_not_cross_border(self, sample_transaction, sample_exchange_rates):
        """Missing country in metadata should not be treated as cross-border."""
        sample_transaction["amount"] = "1000.00"
        sample_transaction["timestamp"] = "2026-03-16T12:00:00Z"
        sample_transaction["metadata"]["country"] = None

        result = score_transaction(sample_transaction, sample_exchange_rates)

        assert not result["factors"]["cross_border_mismatch"]

    def test_result_has_required_fields(self, sample_transaction, sample_exchange_rates):
        """Result should have all required fields."""
        result = score_transaction(sample_transaction, sample_exchange_rates)

        assert "score" in result
        assert "factors" in result
        assert "flagged" in result
        assert "scored_at" in result
        assert isinstance(result["score"], str)
        assert isinstance(result["flagged"], bool)

    def test_eur_transaction_scored_correctly(self, sample_exchange_rates):
        """EUR transaction should be converted to USD equivalent for scoring."""
        tx = {
            "transaction_id": "EUR_TEST",
            "timestamp": "2026-03-16T12:00:00Z",
            "source_account": "ACC-001",
            "destination_account": "ACC-002",
            "amount": "10000.00",  # EUR, converts to ~10870 USD
            "currency": "EUR",
            "transaction_type": "transfer",
            "description": "Test",
            "metadata": {"channel": "online", "country": "DE"}
        }

        result = score_transaction(tx, sample_exchange_rates)

        # Should be flagged as high value when converted
        assert result["factors"]["high_value_amount"]

    def test_boundary_high_value_threshold(self, sample_transaction, sample_exchange_rates):
        """Test boundary at HIGH_VALUE_USD_THRESHOLD (10000)."""
        # Just below threshold
        sample_transaction["amount"] = "9999.99"
        sample_transaction["metadata"]["country"] = "GB"
        result = score_transaction(sample_transaction, sample_exchange_rates)
        assert not result["factors"]["high_value_amount"]

        # Just above threshold
        sample_transaction["amount"] = "10000.01"
        result = score_transaction(sample_transaction, sample_exchange_rates)
        assert result["factors"]["high_value_amount"]

    def test_boundary_unusual_hour_start(self, sample_transaction, sample_exchange_rates):
        """Test boundary at unusual hour start (6am UTC)."""
        # At 5:59am (unusual)
        sample_transaction["timestamp"] = "2026-03-16T05:59:00Z"
        result = score_transaction(sample_transaction, sample_exchange_rates)
        assert result["factors"]["unusual_hour_timing"]

        # At 6:00am (normal)
        sample_transaction["timestamp"] = "2026-03-16T06:00:00Z"
        result = score_transaction(sample_transaction, sample_exchange_rates)
        assert not result["factors"]["unusual_hour_timing"]

    def test_boundary_unusual_hour_end(self, sample_transaction, sample_exchange_rates):
        """Test boundary at unusual hour end (10pm UTC)."""
        # At 9:59pm (normal)
        sample_transaction["timestamp"] = "2026-03-16T21:59:00Z"
        result = score_transaction(sample_transaction, sample_exchange_rates)
        assert not result["factors"]["unusual_hour_timing"]

        # At 10:00pm (unusual)
        sample_transaction["timestamp"] = "2026-03-16T22:00:00Z"
        result = score_transaction(sample_transaction, sample_exchange_rates)
        assert result["factors"]["unusual_hour_timing"]

    def test_edge_case_transactions(self, edge_case_transactions, sample_exchange_rates):
        """Edge case transactions should be scored without errors."""
        for tx in edge_case_transactions:
            result = score_transaction(tx, sample_exchange_rates)
            assert "score" in result
            assert "flagged" in result
            score = Decimal(result["score"])
            assert Decimal("0") <= score <= Decimal("1.00")
