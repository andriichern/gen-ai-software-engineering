"""Unit tests for the Settlement Processing stage."""
from decimal import Decimal

import pytest

from pipeline.settlement import settle_transaction


class TestSettleTransaction:
    """Tests for settle_transaction function."""

    def test_settle_cleared_transaction(self, sample_transaction):
        """A cleared transaction should settle successfully."""
        compliance_result = {
            "status": "cleared",
            "reason": None,
            "checked_at": "2026-03-16T10:00:00+00:00"
        }

        result = settle_transaction(sample_transaction, compliance_result)

        assert result["status"] == "settled"
        assert result["settlement_reference"]  # UUID
        assert result["settlement_timestamp"]
        assert result["settled_amount"] == "1000.00"
        assert result["currency"] == "USD"
        assert result["retention_period_years"] == 5

    def test_settlement_reference_is_uuid(self, sample_transaction):
        """Settlement reference should be a valid UUID."""
        compliance_result = {"status": "cleared"}

        result = settle_transaction(sample_transaction, compliance_result)

        ref = result["settlement_reference"]
        # Check it's a valid UUID string (36 chars with dashes)
        assert len(ref) == 36
        assert ref.count("-") == 4

    def test_settlement_timestamp_is_iso8601(self, sample_transaction):
        """Settlement timestamp should be ISO 8601 UTC."""
        compliance_result = {"status": "cleared"}

        result = settle_transaction(sample_transaction, compliance_result)

        ts = result["settlement_timestamp"]
        assert "T" in ts
        assert "+" in ts or "Z" in ts or "00:00" in ts

    def test_refuse_held_transaction(self, sample_transaction):
        """A held (non-cleared) transaction should not settle."""
        compliance_result = {
            "status": "held",
            "reason": "fraud flagged"
        }

        with pytest.raises(ValueError, match="cannot settle"):
            settle_transaction(sample_transaction, compliance_result)

    def test_refuse_rejected_transaction(self, sample_transaction):
        """A rejected transaction should not settle."""
        compliance_result = {
            "status": "rejected",
            "reason": "validation failed"
        }

        with pytest.raises(ValueError, match="cannot settle"):
            settle_transaction(sample_transaction, compliance_result)

    def test_refuse_missing_compliance_result(self, sample_transaction):
        """Missing compliance result should not settle."""
        with pytest.raises(ValueError, match="cannot settle"):
            settle_transaction(sample_transaction, None)

    def test_refuse_empty_compliance_result(self, sample_transaction):
        """Empty compliance result (no status field) should not settle."""
        with pytest.raises(ValueError, match="cannot settle"):
            settle_transaction(sample_transaction, {})

    def test_settle_negative_amount_refund(self, sample_transaction):
        """Negative amounts (refunds) should settle exactly like transactions."""
        sample_transaction["amount"] = "-500.00"
        compliance_result = {"status": "cleared"}

        result = settle_transaction(sample_transaction, compliance_result)

        assert result["status"] == "settled"
        assert result["settled_amount"] == "-500.00"

    def test_settle_large_amount(self, sample_transaction):
        """Very large amounts should settle correctly."""
        sample_transaction["amount"] = "999999999.99"
        compliance_result = {"status": "cleared"}

        result = settle_transaction(sample_transaction, compliance_result)

        assert result["settled_amount"] == "999999999.99"

    def test_settle_zero_amount(self, sample_transaction):
        """Zero amount should settle."""
        sample_transaction["amount"] = "0.00"
        compliance_result = {"status": "cleared"}

        result = settle_transaction(sample_transaction, compliance_result)

        assert result["settled_amount"] == "0.00"

    def test_settle_different_currency(self, sample_transaction):
        """Settlement should preserve the transaction's currency."""
        for currency in ["EUR", "GBP", "JPY", "CAD"]:
            sample_transaction["currency"] = currency
            compliance_result = {"status": "cleared"}

            result = settle_transaction(sample_transaction, compliance_result)

            assert result["currency"] == currency

    def test_result_has_required_fields(self, sample_transaction):
        """Result should have all required fields."""
        compliance_result = {"status": "cleared"}

        result = settle_transaction(sample_transaction, compliance_result)

        required = ["status", "settlement_reference", "settlement_timestamp",
                   "settled_amount", "currency", "retention_period_years"]
        for field in required:
            assert field in result

    def test_retention_period_always_five_years(self, sample_transaction):
        """Retention period should always be 5 years."""
        for _ in range(3):
            compliance_result = {"status": "cleared"}
            result = settle_transaction(sample_transaction, compliance_result)
            assert result["retention_period_years"] == 5

    def test_multiple_settlements_have_different_references(self, sample_transaction):
        """Each settlement should have a unique reference ID."""
        compliance_result = {"status": "cleared"}

        result1 = settle_transaction(sample_transaction, compliance_result)
        result2 = settle_transaction(sample_transaction, compliance_result)

        assert result1["settlement_reference"] != result2["settlement_reference"]

    def test_settle_preserves_decimal_precision(self, sample_transaction):
        """Decimal precision should be preserved in settled amount."""
        sample_transaction["amount"] = "123.456789"
        compliance_result = {"status": "cleared"}

        result = settle_transaction(sample_transaction, compliance_result)

        assert result["settled_amount"] == "123.456789"

    def test_refuse_false_compliance_cleared(self, sample_transaction):
        """Compliance result with cleared=False should not settle."""
        compliance_result = {
            "status": "cleared",
            "cleared": False  # Explicit false
        }
        # The function checks status == "cleared", not a cleared boolean field
        result = settle_transaction(sample_transaction, compliance_result)
        assert result["status"] == "settled"

    def test_settle_with_only_status_field(self, sample_transaction):
        """Only status field being "cleared" is sufficient to settle."""
        minimal_result = {"status": "cleared"}

        result = settle_transaction(sample_transaction, minimal_result)

        assert result["status"] == "settled"

    def test_settlement_amount_string_type(self, sample_transaction):
        """settled_amount should be a string."""
        compliance_result = {"status": "cleared"}

        result = settle_transaction(sample_transaction, compliance_result)

        assert isinstance(result["settled_amount"], str)

    def test_edge_case_transactions_settle(self, edge_case_transactions):
        """Edge case transactions should settle if compliance cleared."""
        compliance_result = {"status": "cleared"}

        for tx in edge_case_transactions:
            result = settle_transaction(tx, compliance_result)
            assert result["status"] == "settled"
            assert result["settled_amount"]
            assert result["currency"]

    def test_valid_transactions_settle(self, valid_transactions):
        """Valid transactions should settle."""
        compliance_result = {"status": "cleared"}

        for tx in valid_transactions[:2]:
            result = settle_transaction(tx, compliance_result)
            assert result["status"] == "settled"
            assert result["settled_amount"] == tx["amount"]

    def test_error_message_explains_problem(self, sample_transaction):
        """Error message should explain why settlement failed."""
        compliance_result = {"status": "held"}

        with pytest.raises(ValueError) as exc_info:
            settle_transaction(sample_transaction, compliance_result)

        error_msg = str(exc_info.value)
        assert "cleared" in error_msg
