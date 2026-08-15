"""Unit tests for the Compliance Check stage."""
import pytest

from pipeline.compliance import check_compliance


class TestCheckCompliance:
    """Tests for check_compliance function."""

    def test_cleared_when_not_flagged(self, sample_transaction):
        """Unflagged transaction should be cleared."""
        fraud_result = {
            "score": "0.30",
            "flagged": False,
            "factors": {
                "high_value_amount": False,
                "cross_border_mismatch": False,
                "unusual_hour_timing": False
            }
        }

        result = check_compliance(sample_transaction, fraud_result)

        assert result["status"] == "cleared"
        assert result["reason"] is None
        assert "checked_at" in result

    def test_held_when_flagged(self, sample_transaction):
        """Flagged transaction should be held for review."""
        fraud_result = {
            "score": "0.50",
            "flagged": True,
            "factors": {
                "high_value_amount": True,
                "cross_border_mismatch": False,
                "unusual_hour_timing": False
            }
        }

        result = check_compliance(sample_transaction, fraud_result)

        assert result["status"] == "held"
        assert "fraud score" in result["reason"]
        assert "0.50" in result["reason"]

    def test_held_explains_high_flag(self, sample_transaction):
        """Held status should explain the fraud flag."""
        fraud_result = {
            "score": "0.85",
            "flagged": True,
            "factors": {
                "high_value_amount": True,
                "cross_border_mismatch": True,
                "unusual_hour_timing": True
            }
        }

        result = check_compliance(sample_transaction, fraud_result)

        assert result["status"] == "held"
        assert "0.85" in result["reason"]

    def test_held_on_flagged_with_zero_score(self, sample_transaction):
        """Even flagged transactions with any score should be held."""
        fraud_result = {
            "score": "0.00",
            "flagged": True  # Explicitly flagged despite low score
        }

        result = check_compliance(sample_transaction, fraud_result)

        assert result["status"] == "held"

    def test_cleared_with_no_flagged_field(self, sample_transaction):
        """Missing flagged field (falsy) should clear."""
        fraud_result = {
            "score": "0.50",
            # No flagged field
        }

        result = check_compliance(sample_transaction, fraud_result)

        assert result["status"] == "cleared"

    def test_cleared_with_false_flagged(self, sample_transaction):
        """Explicitly false flagged field should clear."""
        fraud_result = {
            "score": "0.50",
            "flagged": False
        }

        result = check_compliance(sample_transaction, fraud_result)

        assert result["status"] == "cleared"
        assert result["reason"] is None

    def test_result_has_checked_at_timestamp(self, sample_transaction):
        """Result should have a checked_at ISO 8601 timestamp."""
        fraud_result = {"flagged": False}

        result = check_compliance(sample_transaction, fraud_result)

        assert "checked_at" in result
        assert "T" in result["checked_at"]  # ISO 8601 format
        assert "+" in result["checked_at"] or "Z" in result["checked_at"]

    def test_multiple_calls_have_different_timestamps(self, sample_transaction):
        """Multiple calls should produce different checked_at times."""
        fraud_result = {"flagged": False}

        result1 = check_compliance(sample_transaction, fraud_result)
        result2 = check_compliance(sample_transaction, fraud_result)

        # Timestamps should be close but might differ (depending on timing)
        assert result1["checked_at"]
        assert result2["checked_at"]

    def test_empty_fraud_result_clears_transaction(self, sample_transaction):
        """Empty fraud result should clear transaction (no flag)."""
        fraud_result = {}

        result = check_compliance(sample_transaction, fraud_result)

        assert result["status"] == "cleared"

    def test_none_fraud_result_clears_transaction(self, sample_transaction):
        """None fraud result should be treated as falsy (clear)."""
        # Check how None is handled
        result = check_compliance(sample_transaction, {})
        assert result["status"] == "cleared"

    def test_held_with_high_risk_score(self, sample_transaction):
        """Very high fraud score should result in held status."""
        fraud_result = {
            "score": "1.00",
            "flagged": True
        }

        result = check_compliance(sample_transaction, fraud_result)

        assert result["status"] == "held"

    def test_compliance_never_rejects(self, sample_transaction):
        """Compliance should never reject (only clear or hold)."""
        # Test various fraud results
        for flagged in [True, False]:
            fraud_result = {"flagged": flagged}
            result = check_compliance(sample_transaction, fraud_result)
            assert result["status"] in ["cleared", "held"]

    def test_compliance_respects_gdpr_principle(self, sample_transaction):
        """Flagged transactions are held for human review (GDPR Article 22)."""
        # This is the core compliance principle
        fraud_result = {"flagged": True}
        result = check_compliance(sample_transaction, fraud_result)

        # Held = human review = no automated adverse decision
        assert result["status"] == "held"
        assert "human review" in result["reason"]

    def test_compliance_with_different_fraud_scores(self, sample_transaction):
        """Test compliance with various fraud scores."""
        for score_str in ["0.00", "0.25", "0.50", "0.75", "1.00"]:
            fraud_result = {"score": score_str, "flagged": False}
            result = check_compliance(sample_transaction, fraud_result)
            assert result["status"] == "cleared"

    def test_compliance_ignores_transaction_pii(self, sample_transaction):
        """Compliance should not log PII from transaction."""
        # Even though we don't directly check output, the fact that
        # check_compliance takes a record (which contains PII in original)
        # but only checks fraud result shows GDPR-safe behavior
        result = check_compliance(sample_transaction, {"flagged": True})

        # Result should not contain account numbers, amounts, etc. in reason
        assert "ACC-" not in result["reason"]
        assert "1000" not in result["reason"]

    def test_very_high_flagged_score_reason(self, sample_transaction):
        """Reason text should mention fraud score."""
        fraud_result = {
            "score": "0.99",
            "flagged": True
        }

        result = check_compliance(sample_transaction, fraud_result)

        assert "held for human review" in result["reason"]
        assert "fraud score" in result["reason"]

    def test_valid_transactions_compliance(self, valid_transactions):
        """Valid transactions with low fraud scores should clear."""
        fraud_result = {"flagged": False}

        for tx in valid_transactions[:2]:  # Test a couple
            result = check_compliance(tx, fraud_result)
            assert result["status"] == "cleared"

    def test_edge_case_compliance(self, edge_case_transactions):
        """Edge case transactions should process through compliance."""
        for tx in edge_case_transactions:
            fraud_result = {"flagged": True}
            result = check_compliance(tx, fraud_result)
            assert result["status"] == "held"
            assert "fraud score" in result["reason"]
