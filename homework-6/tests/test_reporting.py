"""Unit tests for the Reporting stage."""
from decimal import Decimal

import pytest

from pipeline.reporting import build_report


class TestBuildReport:
    """Tests for build_report function."""

    def test_empty_records_generates_zero_report(self):
        """Empty record list should generate a report with all zeros."""
        result = build_report([])

        assert result["total_records"] == 0
        assert result["counts"]["validated"] == 0
        assert result["counts"]["rejected"] == 0
        assert result["counts"]["flagged"] == 0
        assert result["counts"]["held"] == 0
        assert result["counts"]["settled"] == 0

    def test_single_valid_settled_transaction(self):
        """A single validated and settled transaction should be counted."""
        records = [
            {
                "validation_result": {"status": "passed"},
                "fraud_result": {"flagged": False, "score": "0.20"},
                "compliance_result": {"status": "cleared"},
                "settlement_result": {"status": "settled", "settled_amount": "1000.00", "currency": "USD"},
                "final_status": "settled"
            }
        ]

        result = build_report(records)

        assert result["total_records"] == 1
        assert result["counts"]["validated"] == 1
        assert result["counts"]["settled"] == 1
        assert result["counts"]["flagged"] == 0
        assert result["counts"]["rejected"] == 0
        assert result["counts"]["held"] == 0

    def test_rejected_transaction_counted(self):
        """Rejected transactions should be counted."""
        records = [
            {
                "validation_result": {"status": "failed"},
                "final_status": "rejected"
            }
        ]

        result = build_report(records)

        assert result["total_records"] == 1
        assert result["counts"]["rejected"] == 1
        assert result["counts"]["validated"] == 0

    def test_held_transaction_counted(self):
        """Held transactions should be counted."""
        records = [
            {
                "validation_result": {"status": "passed"},
                "fraud_result": {"flagged": True, "score": "0.75"},
                "compliance_result": {"status": "held"},
                "final_status": "held"
            }
        ]

        result = build_report(records)

        assert result["total_records"] == 1
        assert result["counts"]["held"] == 1
        assert result["counts"]["flagged"] == 1

    def test_flagged_transaction_counted_separately(self):
        """Flagged transactions should be counted even if held."""
        records = [
            {
                "fraud_result": {"flagged": True, "score": "0.60"},
                "final_status": "held"
            }
        ]

        result = build_report(records)

        assert result["counts"]["flagged"] == 1

    def test_fraud_score_distribution_bucketing(self):
        """Fraud scores should be bucketed correctly."""
        records = [
            {"fraud_result": {"score": "0.10"}},  # 0.00-0.19
            {"fraud_result": {"score": "0.25"}},  # 0.20-0.49
            {"fraud_result": {"score": "0.50"}},  # 0.50-0.79
            {"fraud_result": {"score": "0.95"}},  # 0.80-1.00
        ]

        result = build_report(records)

        assert result["risk_score_distribution"]["0.00-0.19"] == 1
        assert result["risk_score_distribution"]["0.20-0.49"] == 1
        assert result["risk_score_distribution"]["0.50-0.79"] == 1
        assert result["risk_score_distribution"]["0.80-1.00"] == 1

    def test_fraud_score_distribution_boundaries(self):
        """Test score distribution at bucket boundaries."""
        records = [
            {"fraud_result": {"score": "0.19"}},  # Should be in first bucket
            {"fraud_result": {"score": "0.20"}},  # Should be in second bucket
            {"fraud_result": {"score": "0.49"}},  # Should be in second bucket
            {"fraud_result": {"score": "0.50"}},  # Should be in third bucket
            {"fraud_result": {"score": "0.79"}},  # Should be in third bucket
            {"fraud_result": {"score": "0.80"}},  # Should be in fourth bucket
            {"fraud_result": {"score": "1.00"}},  # Should be in fourth bucket
        ]

        result = build_report(records)

        assert result["risk_score_distribution"]["0.00-0.19"] == 1
        assert result["risk_score_distribution"]["0.20-0.49"] == 2
        assert result["risk_score_distribution"]["0.50-0.79"] == 2
        assert result["risk_score_distribution"]["0.80-1.00"] == 2

    def test_settled_value_by_currency_single(self):
        """Settled values should be aggregated by currency."""
        records = [
            {
                "settlement_result": {
                    "status": "settled",
                    "settled_amount": "1000.00",
                    "currency": "USD"
                },
                "final_status": "settled"
            }
        ]

        result = build_report(records)

        assert result["total_settled_value_by_currency"]["USD"] == "1000.00"

    def test_settled_value_by_currency_multiple(self):
        """Multiple currencies should aggregate separately."""
        records = [
            {
                "settlement_result": {
                    "status": "settled",
                    "settled_amount": "1000.00",
                    "currency": "USD"
                },
                "final_status": "settled"
            },
            {
                "settlement_result": {
                    "status": "settled",
                    "settled_amount": "500.00",
                    "currency": "EUR"
                },
                "final_status": "settled"
            },
            {
                "settlement_result": {
                    "status": "settled",
                    "settled_amount": "200.00",
                    "currency": "USD"
                },
                "final_status": "settled"
            }
        ]

        result = build_report(records)

        assert result["total_settled_value_by_currency"]["USD"] == "1200.00"
        assert result["total_settled_value_by_currency"]["EUR"] == "500.00"

    def test_settled_value_with_negative_amounts(self):
        """Negative amounts (refunds) should be aggregated correctly."""
        records = [
            {
                "settlement_result": {
                    "status": "settled",
                    "settled_amount": "1000.00",
                    "currency": "USD"
                },
                "final_status": "settled"
            },
            {
                "settlement_result": {
                    "status": "settled",
                    "settled_amount": "-250.00",
                    "currency": "USD"
                },
                "final_status": "settled"
            }
        ]

        result = build_report(records)

        assert result["total_settled_value_by_currency"]["USD"] == "750.00"

    def test_report_excludes_unsettled_from_value(self):
        """Held/rejected transactions should not be in settled values."""
        records = [
            {
                "settlement_result": {
                    "status": "settled",
                    "settled_amount": "1000.00",
                    "currency": "USD"
                },
                "final_status": "settled"
            },
            {
                "final_status": "held"  # No settlement
            },
            {
                "final_status": "rejected"  # No settlement
            }
        ]

        result = build_report(records)

        assert "USD" in result["total_settled_value_by_currency"]
        assert result["total_settled_value_by_currency"]["USD"] == "1000.00"

    def test_report_includes_generated_at_timestamp(self):
        """Report should include generated_at timestamp."""
        result = build_report([])

        assert "generated_at" in result
        assert "T" in result["generated_at"]

    def test_report_structure(self):
        """Report should have complete required structure."""
        result = build_report([])

        assert "generated_at" in result
        assert "total_records" in result
        assert "counts" in result
        assert "risk_score_distribution" in result
        assert "total_settled_value_by_currency" in result

        assert "validated" in result["counts"]
        assert "rejected" in result["counts"]
        assert "flagged" in result["counts"]
        assert "held" in result["counts"]
        assert "settled" in result["counts"]

    def test_mixed_transaction_flow(self):
        """Complex mix of transactions should report correctly."""
        records = [
            {
                "validation_result": {"status": "passed"},
                "fraud_result": {"flagged": False, "score": "0.10"},
                "final_status": "settled",
                "settlement_result": {
                    "status": "settled",
                    "settled_amount": "1500.00",
                    "currency": "USD"
                }
            },
            {
                "validation_result": {"status": "passed"},
                "fraud_result": {"flagged": True, "score": "0.75"},
                "final_status": "held"
            },
            {
                "validation_result": {"status": "failed"},
                "final_status": "rejected"
            },
            {
                "validation_result": {"status": "passed"},
                "fraud_result": {"flagged": False, "score": "0.30"},
                "final_status": "settled",
                "settlement_result": {
                    "status": "settled",
                    "settled_amount": "2000.00",
                    "currency": "EUR"
                }
            }
        ]

        result = build_report(records)

        assert result["total_records"] == 4
        assert result["counts"]["validated"] == 3
        assert result["counts"]["rejected"] == 1
        assert result["counts"]["flagged"] == 1
        assert result["counts"]["held"] == 1
        assert result["counts"]["settled"] == 2
        assert result["total_settled_value_by_currency"]["USD"] == "1500.00"
        assert result["total_settled_value_by_currency"]["EUR"] == "2000.00"

    def test_settled_values_use_decimal_arithmetic(self):
        """Settled values should use Decimal for precision."""
        records = [
            {
                "settlement_result": {
                    "status": "settled",
                    "settled_amount": "0.01",
                    "currency": "USD"
                },
                "final_status": "settled"
            },
            {
                "settlement_result": {
                    "status": "settled",
                    "settled_amount": "0.02",
                    "currency": "USD"
                },
                "final_status": "settled"
            }
        ]

        result = build_report(records)

        # Should be "0.03", not "0.030000000000000001"
        assert result["total_settled_value_by_currency"]["USD"] == "0.03"

    def test_transaction_without_validation_result(self):
        """Transactions without validation_result should not affect validated count."""
        records = [
            {
                "final_status": "settled",
                "settlement_result": {
                    "status": "settled",
                    "settled_amount": "1000.00",
                    "currency": "USD"
                }
            }
        ]

        result = build_report(records)

        assert result["counts"]["validated"] == 0
        assert result["counts"]["settled"] == 1

    def test_transaction_without_fraud_result(self):
        """Transactions without fraud_result should not be flagged."""
        records = [
            {
                "final_status": "settled"
            }
        ]

        result = build_report(records)

        assert result["counts"]["flagged"] == 0

    def test_missing_settlement_currency_ignored(self):
        """Missing currency in settlement should be handled gracefully."""
        records = [
            {
                "settlement_result": {
                    "status": "settled",
                    "settled_amount": "1000.00"
                    # No currency field
                },
                "final_status": "settled"
            }
        ]

        result = build_report(records)

        # Should handle gracefully, None key might be created
        assert result["total_records"] == 1

    def test_edge_case_very_large_settlement_value(self):
        """Very large settled amounts should sum correctly."""
        records = [
            {
                "settlement_result": {
                    "status": "settled",
                    "settled_amount": "999999999.99",
                    "currency": "USD"
                },
                "final_status": "settled"
            }
        ]

        result = build_report(records)

        assert result["total_settled_value_by_currency"]["USD"] == "999999999.99"
