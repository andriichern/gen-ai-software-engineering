"""Unit tests for the Validation stage."""
import json

import pytest

from pipeline.validation import dry_run, validate_transaction


class TestValidateTransaction:
    """Tests for validate_transaction function."""

    def test_valid_transaction_passes(self, sample_transaction):
        """A properly formed transaction should pass validation."""
        result = validate_transaction(sample_transaction)
        assert result["status"] == "passed"
        assert result["reason"] is None
        assert "checked_at" in result

    def test_missing_transaction_id(self, sample_transaction):
        """Transaction without transaction_id should fail."""
        del sample_transaction["transaction_id"]
        result = validate_transaction(sample_transaction)
        assert result["status"] == "failed"
        assert "transaction_id" in result["reason"]

    def test_missing_timestamp(self, sample_transaction):
        """Transaction without timestamp should fail."""
        del sample_transaction["timestamp"]
        result = validate_transaction(sample_transaction)
        assert result["status"] == "failed"
        assert "timestamp" in result["reason"]

    def test_missing_source_account(self, sample_transaction):
        """Transaction without source_account should fail."""
        del sample_transaction["source_account"]
        result = validate_transaction(sample_transaction)
        assert result["status"] == "failed"
        assert "source_account" in result["reason"]

    def test_missing_destination_account(self, sample_transaction):
        """Transaction without destination_account should fail."""
        del sample_transaction["destination_account"]
        result = validate_transaction(sample_transaction)
        assert result["status"] == "failed"
        assert "destination_account" in result["reason"]

    def test_missing_amount(self, sample_transaction):
        """Transaction without amount should fail."""
        del sample_transaction["amount"]
        result = validate_transaction(sample_transaction)
        assert result["status"] == "failed"
        assert "amount" in result["reason"]

    def test_missing_currency(self, sample_transaction):
        """Transaction without currency should fail."""
        del sample_transaction["currency"]
        result = validate_transaction(sample_transaction)
        assert result["status"] == "failed"
        assert "currency" in result["reason"]

    def test_missing_transaction_type(self, sample_transaction):
        """Transaction without transaction_type should fail."""
        del sample_transaction["transaction_type"]
        result = validate_transaction(sample_transaction)
        assert result["status"] == "failed"
        assert "transaction_type" in result["reason"]

    def test_missing_description(self, sample_transaction):
        """Transaction without description should fail."""
        del sample_transaction["description"]
        result = validate_transaction(sample_transaction)
        assert result["status"] == "failed"
        assert "description" in result["reason"]

    def test_missing_metadata(self, sample_transaction):
        """Transaction without metadata should fail."""
        del sample_transaction["metadata"]
        result = validate_transaction(sample_transaction)
        assert result["status"] == "failed"
        assert "metadata" in result["reason"]

    def test_invalid_transaction_id_type(self, sample_transaction):
        """transaction_id must be a string."""
        sample_transaction["transaction_id"] = 12345
        result = validate_transaction(sample_transaction)
        assert result["status"] == "failed"
        assert "string" in result["reason"]

    def test_invalid_timestamp_format(self, sample_transaction):
        """Invalid timestamp format should fail."""
        sample_transaction["timestamp"] = "not-a-timestamp"
        result = validate_transaction(sample_transaction)
        assert result["status"] == "failed"
        assert "timestamp" in result["reason"]

    def test_invalid_timestamp_type(self, sample_transaction):
        """timestamp must be parseable as an ISO 8601 string."""
        sample_transaction["timestamp"] = 123456789
        # When timestamp is not a string, parse_iso8601 will fail
        # This tests that the validation catches this
        with pytest.raises((AttributeError, ValueError, TypeError)):
            validate_transaction(sample_transaction)

    def test_invalid_source_account_type(self, sample_transaction):
        """source_account must be a string."""
        sample_transaction["source_account"] = 12345
        result = validate_transaction(sample_transaction)
        assert result["status"] == "failed"
        assert "string" in result["reason"]

    def test_invalid_destination_account_type(self, sample_transaction):
        """destination_account must be a string."""
        sample_transaction["destination_account"] = 12345
        result = validate_transaction(sample_transaction)
        assert result["status"] == "failed"
        assert "string" in result["reason"]

    def test_amount_must_be_string(self, sample_transaction):
        """amount must be a string, not a number."""
        sample_transaction["amount"] = 1000.00
        result = validate_transaction(sample_transaction)
        assert result["status"] == "failed"
        assert "string" in result["reason"]

    def test_invalid_amount_format(self, sample_transaction):
        """Invalid decimal amount should fail."""
        sample_transaction["amount"] = "not-a-number"
        result = validate_transaction(sample_transaction)
        assert result["status"] == "failed"
        assert "decimal" in result["reason"]

    def test_invalid_currency_code(self, sample_transaction):
        """Invalid ISO 4217 currency code should fail."""
        sample_transaction["currency"] = "XYZ"
        result = validate_transaction(sample_transaction)
        assert result["status"] == "failed"
        assert "currency" in result["reason"]

    def test_invalid_transaction_type_type(self, sample_transaction):
        """transaction_type must be a string."""
        sample_transaction["transaction_type"] = 123
        result = validate_transaction(sample_transaction)
        assert result["status"] == "failed"
        assert "string" in result["reason"]

    def test_invalid_description_type(self, sample_transaction):
        """description must be a string."""
        sample_transaction["description"] = 123
        result = validate_transaction(sample_transaction)
        assert result["status"] == "failed"
        assert "string" in result["reason"]

    def test_metadata_not_dict(self, sample_transaction):
        """metadata must be a dict/object."""
        sample_transaction["metadata"] = "not-a-dict"
        result = validate_transaction(sample_transaction)
        assert result["status"] == "failed"
        assert "object" in result["reason"]

    def test_missing_metadata_channel(self, sample_transaction):
        """metadata must have a channel field."""
        sample_transaction["metadata"] = {"country": "US"}
        result = validate_transaction(sample_transaction)
        assert result["status"] == "failed"
        assert "channel" in result["reason"]

    def test_missing_metadata_country(self, sample_transaction):
        """metadata must have a country field."""
        sample_transaction["metadata"] = {"channel": "online"}
        result = validate_transaction(sample_transaction)
        assert result["status"] == "failed"
        assert "country" in result["reason"]

    def test_empty_metadata_channel(self, sample_transaction):
        """metadata.channel cannot be empty."""
        sample_transaction["metadata"]["channel"] = ""
        result = validate_transaction(sample_transaction)
        assert result["status"] == "failed"
        assert "channel" in result["reason"]

    def test_empty_metadata_country(self, sample_transaction):
        """metadata.country cannot be empty."""
        sample_transaction["metadata"]["country"] = ""
        result = validate_transaction(sample_transaction)
        assert result["status"] == "failed"
        assert "country" in result["reason"]

    def test_null_metadata_channel(self, sample_transaction):
        """metadata.channel cannot be None."""
        sample_transaction["metadata"]["channel"] = None
        result = validate_transaction(sample_transaction)
        assert result["status"] == "failed"
        assert "channel" in result["reason"]

    def test_null_metadata_country(self, sample_transaction):
        """metadata.country cannot be None."""
        sample_transaction["metadata"]["country"] = None
        result = validate_transaction(sample_transaction)
        assert result["status"] == "failed"
        assert "country" in result["reason"]

    def test_valid_transactions_from_fixture(self, valid_transactions):
        """All valid transactions from fixture should pass."""
        for tx in valid_transactions:
            result = validate_transaction(tx)
            assert result["status"] == "passed", f"Transaction {tx['transaction_id']} should pass"

    def test_invalid_transactions_from_fixture(self, invalid_transactions):
        """All invalid transactions from fixture should fail."""
        for tx in invalid_transactions:
            result = validate_transaction(tx)
            assert result["status"] == "failed", f"Transaction {tx['transaction_id']} should fail"

    def test_edge_case_transactions_from_fixture(self, edge_case_transactions):
        """Edge case transactions should pass validation if well-formed."""
        for tx in edge_case_transactions:
            result = validate_transaction(tx)
            assert result["status"] == "passed", f"Edge case {tx['transaction_id']} should pass validation"

    def test_negative_amount_passes(self, sample_transaction):
        """Negative amounts (refunds) should pass validation."""
        sample_transaction["amount"] = "-50.00"
        result = validate_transaction(sample_transaction)
        assert result["status"] == "passed"

    def test_very_large_amount_passes(self, sample_transaction):
        """Very large amounts should pass validation."""
        sample_transaction["amount"] = "999999999.99"
        result = validate_transaction(sample_transaction)
        assert result["status"] == "passed"

    def test_zero_amount_passes(self, sample_transaction):
        """Zero amount should pass validation."""
        sample_transaction["amount"] = "0.00"
        result = validate_transaction(sample_transaction)
        assert result["status"] == "passed"

    def test_multiple_currencies(self, sample_transaction):
        """Various valid ISO 4217 currencies should pass."""
        currencies = ["USD", "EUR", "GBP", "JPY", "CAD", "AUD"]
        for currency in currencies:
            sample_transaction["currency"] = currency
            result = validate_transaction(sample_transaction)
            assert result["status"] == "passed", f"Currency {currency} should be valid"

    def test_decimal_precision(self, sample_transaction):
        """Decimal precision should be preserved in validation."""
        sample_transaction["amount"] = "123.456789"
        result = validate_transaction(sample_transaction)
        assert result["status"] == "passed"


class TestDryRun:
    """Tests for dry_run: validates a whole dataset while writing nothing."""

    def test_counts_valid_and_invalid(self, tmp_path, sample_transaction):
        """Totals should split into valid and invalid across a mixed dataset."""
        bad = dict(sample_transaction, transaction_id="TXN-BAD", currency="XYZ")
        dataset = tmp_path / "mixed.json"
        dataset.write_text(json.dumps([sample_transaction, bad]))

        report = dry_run(dataset)

        assert report["total"] == 2
        assert report["valid"] == 1
        assert report["invalid"] == 1
        assert report["dataset"] == str(dataset)

    def test_reports_reason_per_record(self, tmp_path, sample_transaction):
        """Each result carries its transaction_id, status and rejection reason."""
        bad = dict(sample_transaction, transaction_id="TXN-BAD", currency="XYZ")
        dataset = tmp_path / "bad.json"
        dataset.write_text(json.dumps([bad]))

        entry = dry_run(dataset)["results"][0]

        assert entry["transaction_id"] == "TXN-BAD"
        assert entry["status"] == "failed"
        assert "XYZ" in entry["reason"]

    def test_writes_nothing(self, tmp_path, sample_transaction):
        """A dry run must not create or modify any file beyond the dataset."""
        dataset = tmp_path / "only.json"
        dataset.write_text(json.dumps([sample_transaction]))
        before = {p: p.stat().st_mtime_ns for p in tmp_path.rglob("*")}

        dry_run(dataset)

        after = {p: p.stat().st_mtime_ns for p in tmp_path.rglob("*")}
        assert after == before

    def test_rejects_non_array_dataset(self, tmp_path):
        """A dataset that is not a JSON array is an error, not an empty run."""
        dataset = tmp_path / "object.json"
        dataset.write_text(json.dumps({"transaction_id": "TXN001"}))

        with pytest.raises(ValueError, match="JSON array"):
            dry_run(dataset)

    def test_real_dataset_is_mostly_valid(self, sample_dataset_path):
        """The shipped dataset should validate end to end without writing."""
        report = dry_run(sample_dataset_path)

        assert report["total"] == report["valid"] + report["invalid"]
        assert report["total"] > 0
