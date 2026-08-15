"""Integration tests for the transaction processing pipeline.

Note: Full end-to-end orchestrator testing requires CLI invocation with actual files.
These tests verify that pipeline modules work together correctly.
"""
from decimal import Decimal
from pathlib import Path

import pytest

from lib.common import lean_data, make_envelope, write_json, read_json
from pipeline.validation import validate_transaction
from pipeline.fraud_detection import score_transaction
from pipeline.compliance import check_compliance
from pipeline.settlement import settle_transaction
from pipeline.reporting import build_report


class TestPipelineModuleIntegration:
    """Test pipeline modules working together in sequence."""

    def test_validation_to_fraud_detection_flow(self, sample_transaction, sample_exchange_rates):
        """Validated transaction should flow to fraud detection."""
        # Validation
        validation_result = validate_transaction(sample_transaction)
        assert validation_result["status"] == "passed"

        # Fraud Detection
        fraud_result = score_transaction(sample_transaction, sample_exchange_rates)
        assert "score" in fraud_result
        assert "flagged" in fraud_result

    def test_fraud_to_compliance_flow(self, sample_transaction, sample_exchange_rates):
        """Fraud scored transaction should flow to compliance."""
        # Fraud Detection
        fraud_result = score_transaction(sample_transaction, sample_exchange_rates)

        # Compliance
        compliance_result = check_compliance(sample_transaction, fraud_result)
        assert compliance_result["status"] in ["cleared", "held"]

    def test_compliance_to_settlement_flow(self, sample_transaction, sample_exchange_rates):
        """Compliance cleared transaction should settle."""
        # Compliance
        compliance_result = {"status": "cleared"}

        # Settlement
        settlement_result = settle_transaction(sample_transaction, compliance_result)
        assert settlement_result["status"] == "settled"

    def test_settlement_to_reporting_flow(self, sample_transaction, sample_exchange_rates):
        """Settled transaction should appear in report."""
        # Create a final result record
        final_record = {
            "transaction_id": sample_transaction["transaction_id"],
            "validation_result": {"status": "passed"},
            "fraud_result": {"score": "0.30", "flagged": False},
            "compliance_result": {"status": "cleared"},
            "settlement_result": {
                "status": "settled",
                "settled_amount": sample_transaction["amount"],
                "currency": sample_transaction["currency"]
            },
            "final_status": "settled"
        }

        # Reporting
        report = build_report([final_record])
        assert report["total_records"] == 1
        assert report["counts"]["validated"] == 1
        assert report["counts"]["settled"] == 1

    def test_complete_pipeline_flow(self, sample_transaction, sample_exchange_rates):
        """Complete flow from validation to reporting."""
        # Step 1: Validation
        validation_result = validate_transaction(sample_transaction)
        assert validation_result["status"] == "passed"

        # Step 2: Fraud Detection
        fraud_result = score_transaction(sample_transaction, sample_exchange_rates)
        assert "score" in fraud_result

        # Step 3: Compliance
        compliance_result = check_compliance(sample_transaction, fraud_result)
        assert compliance_result["status"] in ["cleared", "held"]

        # Step 4: Settlement (only if cleared)
        if compliance_result["status"] == "cleared":
            settlement_result = settle_transaction(sample_transaction, compliance_result)
            assert settlement_result["status"] == "settled"

            # Step 5: Reporting
            final_record = {
                "transaction_id": sample_transaction["transaction_id"],
                "validation_result": validation_result,
                "fraud_result": fraud_result,
                "compliance_result": compliance_result,
                "settlement_result": settlement_result,
                "final_status": "settled"
            }
            report = build_report([final_record])
            assert report["total_records"] == 1
            assert report["counts"]["settled"] == 1

    def test_invalid_transaction_fails_validation(self, invalid_transactions):
        """Invalid transactions should fail validation."""
        for tx in invalid_transactions[:2]:
            result = validate_transaction(tx)
            assert result["status"] == "failed"

    def test_message_envelope_carries_data(self, sample_transaction):
        """Message envelopes should properly carry transaction data."""
        data = lean_data(
            sample_transaction["transaction_id"],
            sample_transaction["amount"],
            sample_transaction["currency"],
            {"validation_result": {"status": "passed"}}
        )

        envelope = make_envelope("validation", "fraud_detection", data)

        assert envelope["source_stage"] == "validation"
        assert envelope["target_stage"] == "fraud_detection"
        assert envelope["data"]["transaction_id"] == sample_transaction["transaction_id"]
        assert envelope["data"]["validation_result"]["status"] == "passed"

    def test_multiple_transactions_in_report(self):
        """Report should handle multiple transactions."""
        records = [
            {
                "validation_result": {"status": "passed"},
                "fraud_result": {"flagged": False, "score": "0.10"},
                "final_status": "settled",
                "settlement_result": {
                    "status": "settled",
                    "settled_amount": "1000.00",
                    "currency": "USD"
                }
            },
            {
                "validation_result": {"status": "failed"},
                "final_status": "rejected"
            },
            {
                "fraud_result": {"flagged": True, "score": "0.75"},
                "final_status": "held"
            }
        ]

        report = build_report(records)

        assert report["total_records"] == 3
        assert report["counts"]["validated"] == 1
        assert report["counts"]["rejected"] == 1
        assert report["counts"]["held"] == 1
        assert report["counts"]["settled"] == 1

    def test_high_value_cross_border_unusual_hour_flow(self, sample_exchange_rates):
        """High-risk transaction flow through pipeline."""
        tx = {
            "transaction_id": "RISK_001",
            "timestamp": "2026-03-16T03:00:00Z",  # unusual hour
            "source_account": "ACC-001",
            "destination_account": "ACC-002",
            "amount": "50000.00",  # high value
            "currency": "EUR",  # cross-border
            "transaction_type": "transfer",
            "description": "Test",
            "metadata": {"channel": "online", "country": "FR"}  # different from GB baseline
        }

        # Validation
        val_result = validate_transaction(tx)
        assert val_result["status"] == "passed"

        # Fraud Detection (should flag)
        fraud_result = score_transaction(tx, sample_exchange_rates)
        assert fraud_result["flagged"] is True

        # Compliance (should hold due to flag)
        comp_result = check_compliance(tx, fraud_result)
        assert comp_result["status"] == "held"

        # Settlement should refuse
        from pipeline.settlement import settle_transaction
        with pytest.raises(ValueError):
            settle_transaction(tx, comp_result)

    def test_refund_processing_flow(self, sample_exchange_rates):
        """Negative amount (refund) should flow through pipeline."""
        refund_tx = {
            "transaction_id": "REFUND_001",
            "timestamp": "2026-03-16T10:00:00Z",
            "source_account": "ACC-001",
            "destination_account": "ACC-002",
            "amount": "-500.00",
            "currency": "USD",
            "transaction_type": "refund",
            "description": "Refund",
            "metadata": {"channel": "online", "country": "US"}
        }

        # Validation
        val_result = validate_transaction(refund_tx)
        assert val_result["status"] == "passed"

        # Fraud Detection
        fraud_result = score_transaction(refund_tx, sample_exchange_rates)
        assert "score" in fraud_result

        # Compliance
        comp_result = check_compliance(refund_tx, fraud_result)
        assert comp_result["status"] in ["cleared", "held"]

        # Settlement if cleared
        if comp_result["status"] == "cleared":
            settlement_result = settle_transaction(refund_tx, comp_result)
            assert settlement_result["status"] == "settled"
            assert settlement_result["settled_amount"] == "-500.00"

    def test_multi_currency_flow(self, sample_exchange_rates):
        """Multiple currencies should flow through pipeline correctly."""
        for currency in ["USD", "EUR", "GBP"]:
            tx = {
                "transaction_id": f"MULTI_{currency}",
                "timestamp": "2026-03-16T10:00:00Z",
                "source_account": "ACC-001",
                "destination_account": "ACC-002",
                "amount": "1000.00",
                "currency": currency,
                "transaction_type": "transfer",
                "description": f"Test {currency}",
                "metadata": {"channel": "online", "country": "US"}
            }

            # Full flow
            val_result = validate_transaction(tx)
            assert val_result["status"] == "passed"

            fraud_result = score_transaction(tx, sample_exchange_rates)
            assert fraud_result["score"]

            comp_result = check_compliance(tx, fraud_result)
            assert comp_result["status"] in ["cleared", "held"]

    def test_edge_case_very_large_amount_flow(self, sample_exchange_rates):
        """Very large amounts should flow correctly."""
        tx = {
            "transaction_id": "LARGE_001",
            "timestamp": "2026-03-16T10:00:00Z",
            "source_account": "ACC-001",
            "destination_account": "ACC-002",
            "amount": "999999999.99",
            "currency": "USD",
            "transaction_type": "wire_transfer",
            "description": "Large transfer",
            "metadata": {"channel": "branch", "country": "US"}
        }

        val_result = validate_transaction(tx)
        assert val_result["status"] == "passed"

        fraud_result = score_transaction(tx, sample_exchange_rates)
        assert fraud_result["flagged"] is True  # Should be flagged as high value

        comp_result = check_compliance(tx, fraud_result)
        assert comp_result["status"] == "held"

    def test_valid_fixtures_flow_through_pipeline(self, valid_transactions, sample_exchange_rates):
        """Valid fixture transactions should flow through pipeline."""
        for tx in valid_transactions[:2]:
            # Validation
            val_result = validate_transaction(tx)
            assert val_result["status"] == "passed", f"{tx['transaction_id']} should pass validation"

            # Should proceed through fraud and compliance
            fraud_result = score_transaction(tx, sample_exchange_rates)
            assert "score" in fraud_result
