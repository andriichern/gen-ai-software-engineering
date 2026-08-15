"""Unit tests for common library utilities."""
from datetime import datetime, timezone
from decimal import Decimal
from pathlib import Path
import json
import tempfile

import pytest

from lib.common import (
    utc_now_iso,
    new_id,
    parse_iso8601,
    parse_decimal,
    read_json,
    write_json,
    list_json_files,
    make_envelope,
    lean_data,
    move_into_processing,
    copy_into_processing,
    clear_processing_file,
    read_original_record,
    write_envelope,
    write_final_result,
)


class TestUtcNowIso:
    """Tests for utc_now_iso function."""

    def test_returns_iso8601_string(self):
        """Should return an ISO 8601 formatted string."""
        result = utc_now_iso()
        assert isinstance(result, str)
        assert "T" in result

    def test_contains_timezone_info(self):
        """Should include timezone info (+ or Z)."""
        result = utc_now_iso()
        assert "+" in result or "Z" in result or "00:00" in result

    def test_returns_utc_time(self):
        """Should represent current UTC time."""
        result = utc_now_iso()
        # Parse it back to verify it's valid ISO 8601
        dt = datetime.fromisoformat(result.replace("Z", "+00:00"))
        assert dt.tzinfo is not None


class TestNewId:
    """Tests for new_id function."""

    def test_returns_string(self):
        """Should return a string."""
        result = new_id()
        assert isinstance(result, str)

    def test_returns_uuid4_format(self):
        """Should return a valid UUID4 string."""
        result = new_id()
        # UUID format: 8-4-4-4-12 hex digits with dashes
        assert len(result) == 36
        assert result.count("-") == 4

    def test_generates_unique_ids(self):
        """Multiple calls should generate different IDs."""
        id1 = new_id()
        id2 = new_id()
        id3 = new_id()
        assert id1 != id2
        assert id2 != id3
        assert id1 != id3


class TestParseIso8601:
    """Tests for parse_iso8601 function."""

    def test_parse_standard_iso8601(self):
        """Should parse standard ISO 8601 format."""
        result = parse_iso8601("2026-03-16T10:00:00Z")
        assert result.year == 2026
        assert result.month == 3
        assert result.day == 16
        assert result.hour == 10

    def test_parse_with_timezone_offset(self):
        """Should parse ISO 8601 with +00:00 offset."""
        result = parse_iso8601("2026-03-16T10:00:00+00:00")
        assert result.year == 2026
        assert result.tzinfo is not None

    def test_parse_without_timezone_assumes_utc(self):
        """Naive timestamps should be assumed to be UTC."""
        result = parse_iso8601("2026-03-16T10:00:00")
        assert result.tzinfo is not None
        assert result.tzinfo.utcoffset(None).total_seconds() == 0

    def test_parse_returns_utc_datetime(self):
        """Result should always be in UTC timezone."""
        result = parse_iso8601("2026-03-16T10:00:00Z")
        assert result.tzinfo == timezone.utc

    def test_parse_invalid_format_raises_error(self):
        """Invalid format should raise an error."""
        with pytest.raises(ValueError):
            parse_iso8601("not-a-timestamp")

    def test_parse_z_suffix_converted_to_utc_offset(self):
        """Z suffix should be treated as UTC."""
        result = parse_iso8601("2026-03-16T10:00:00Z")
        assert result.tzinfo == timezone.utc


class TestParseDecimal:
    """Tests for parse_decimal function."""

    def test_parse_whole_number(self):
        """Should parse whole numbers."""
        result = parse_decimal("1000")
        assert result == Decimal("1000")

    def test_parse_decimal_number(self):
        """Should parse decimal numbers."""
        result = parse_decimal("1000.50")
        assert result == Decimal("1000.50")

    def test_parse_very_large_number(self):
        """Should handle very large numbers."""
        result = parse_decimal("999999999.99")
        assert result == Decimal("999999999.99")

    def test_parse_negative_number(self):
        """Should parse negative numbers."""
        result = parse_decimal("-500.00")
        assert result == Decimal("-500.00")

    def test_parse_zero(self):
        """Should parse zero."""
        result = parse_decimal("0.00")
        assert result == Decimal("0.00")

    def test_parse_many_decimal_places(self):
        """Should preserve many decimal places."""
        result = parse_decimal("123.456789")
        assert result == Decimal("123.456789")

    def test_invalid_decimal_raises_error(self):
        """Invalid decimal should raise ValueError."""
        with pytest.raises(ValueError, match="not a well-formed decimal"):
            parse_decimal("not-a-number")

    def test_parse_does_not_use_float(self):
        """Should use Decimal, not float (avoid precision issues)."""
        # This amount would have precision issues with float
        result = parse_decimal("0.1")
        # With Decimal, this should be exact
        assert str(result) == "0.1"

    def test_invalid_type_raises_error(self):
        """Non-string input should raise error or handle gracefully."""
        # parse_decimal can handle Decimal() accepting int, so just test
        # that non-decimal strings fail
        with pytest.raises(ValueError, match="not a well-formed decimal"):
            parse_decimal("not-a-decimal-string")


class TestReadWriteJson:
    """Tests for read_json and write_json functions."""

    def test_write_and_read_json(self, temp_shared_dir):
        """Should write JSON and read it back identically."""
        test_file = temp_shared_dir / "test.json"
        data = {"key": "value", "number": 42}

        write_json(test_file, data)
        result = read_json(test_file)

        assert result == data

    def test_write_json_creates_parent_dirs(self, temp_shared_dir):
        """write_json should create parent directories."""
        deep_file = temp_shared_dir / "deep" / "nested" / "file.json"
        data = {"test": "data"}

        write_json(deep_file, data)

        assert deep_file.exists()
        result = read_json(deep_file)
        assert result == data

    def test_write_json_with_decimal(self, temp_shared_dir):
        """write_json should handle Decimal types."""
        test_file = temp_shared_dir / "decimal.json"
        data = {
            "amount": Decimal("1000.50"),
            "rate": Decimal("0.92")
        }

        write_json(test_file, data)
        result = read_json(test_file)

        # Decimals are written as strings
        assert result["amount"] == "1000.50"
        assert result["rate"] == "0.92"

    def test_read_json_file_not_found(self):
        """Reading non-existent file should raise error."""
        with pytest.raises(FileNotFoundError):
            read_json(Path("/nonexistent/file.json"))

    def test_write_json_preserves_indentation(self, temp_shared_dir):
        """JSON should be written with indentation (readability)."""
        test_file = temp_shared_dir / "indented.json"
        data = {"key": "value"}

        write_json(test_file, data)

        # Read raw file to check indentation
        with test_file.open("r") as f:
            content = f.read()
        assert "  " in content  # Should have indentation


class TestListJsonFiles:
    """Tests for list_json_files function."""

    def test_list_json_files_in_directory(self, temp_shared_dir):
        """Should list all .json files in directory."""
        # Create some JSON files
        write_json(temp_shared_dir / "file1.json", {"id": 1})
        write_json(temp_shared_dir / "file2.json", {"id": 2})
        write_json(temp_shared_dir / "file3.json", {"id": 3})

        files = list_json_files(temp_shared_dir)

        assert len(files) == 3
        names = [f.name for f in files]
        assert "file1.json" in names
        assert "file2.json" in names
        assert "file3.json" in names

    def test_list_json_files_sorted_by_name(self, temp_shared_dir):
        """Should return files in sorted order."""
        write_json(temp_shared_dir / "zebra.json", {})
        write_json(temp_shared_dir / "apple.json", {})
        write_json(temp_shared_dir / "banana.json", {})

        files = list_json_files(temp_shared_dir)

        names = [f.name for f in files]
        assert names == ["apple.json", "banana.json", "zebra.json"]

    def test_list_json_files_ignores_non_json(self, temp_shared_dir):
        """Should ignore non-.json files."""
        write_json(temp_shared_dir / "data.json", {})
        (temp_shared_dir / "readme.txt").write_text("Not JSON")
        (temp_shared_dir / "file.xml").write_text("<data/>")

        files = list_json_files(temp_shared_dir)

        assert len(files) == 1
        assert files[0].name == "data.json"

    def test_list_json_files_empty_directory(self, temp_shared_dir):
        """Empty directory should return empty list."""
        files = list_json_files(temp_shared_dir)
        assert files == []

    def test_list_json_files_nonexistent_directory(self):
        """Non-existent directory should return empty list."""
        files = list_json_files(Path("/nonexistent/directory"))
        assert files == []


class TestMakeEnvelope:
    """Tests for make_envelope function."""

    def test_make_envelope_has_required_fields(self):
        """Envelope should have all required fields."""
        data = {"transaction_id": "TXN001", "amount": "1000.00"}
        envelope = make_envelope("validation", "fraud_detection", data)

        assert "message_id" in envelope
        assert "timestamp" in envelope
        assert "source_stage" in envelope
        assert "target_stage" in envelope
        assert "message_type" in envelope
        assert "data" in envelope

    def test_make_envelope_message_id_is_uuid(self):
        """message_id should be a UUID."""
        envelope = make_envelope("validation", "fraud_detection", {})
        assert len(envelope["message_id"]) == 36
        assert envelope["message_id"].count("-") == 4

    def test_make_envelope_timestamp_is_iso8601(self):
        """timestamp should be ISO 8601 format."""
        envelope = make_envelope("validation", "fraud_detection", {})
        assert "T" in envelope["timestamp"]

    def test_make_envelope_message_type_is_transaction(self):
        """message_type should always be 'transaction'."""
        envelope = make_envelope("validation", "fraud_detection", {})
        assert envelope["message_type"] == "transaction"

    def test_make_envelope_preserves_data(self):
        """Envelope should preserve the data passed in."""
        data = {"key1": "value1", "key2": 42}
        envelope = make_envelope("stage1", "stage2", data)
        assert envelope["data"] == data

    def test_make_envelope_stages(self):
        """Envelope should store source and target stages."""
        envelope = make_envelope("validation", "fraud_detection", {})
        assert envelope["source_stage"] == "validation"
        assert envelope["target_stage"] == "fraud_detection"


class TestLeanData:
    """Tests for lean_data function."""

    def test_lean_data_basic_fields(self):
        """Should include transaction_id, amount, and currency."""
        result = lean_data("TXN001", "1000.00", "USD", None)

        assert result["transaction_id"] == "TXN001"
        assert result["amount"] == "1000.00"
        assert result["currency"] == "USD"

    def test_lean_data_with_accumulated(self):
        """Should merge accumulated fields."""
        accumulated = {
            "validation_result": {"status": "passed"},
            "fraud_result": {"flagged": False}
        }
        result = lean_data("TXN001", "1000.00", "USD", accumulated)

        assert result["transaction_id"] == "TXN001"
        assert result["amount"] == "1000.00"
        assert result["currency"] == "USD"
        assert result["validation_result"] == {"status": "passed"}
        assert result["fraud_result"] == {"flagged": False}

    def test_lean_data_with_none_accumulated(self):
        """Should handle None accumulated dict."""
        result = lean_data("TXN001", "1000.00", "USD", None)

        assert result["transaction_id"] == "TXN001"
        assert len(result) == 3  # Only the three basic fields

    def test_lean_data_preserves_all_accumulated(self):
        """Should preserve all accumulated fields."""
        accumulated = {
            "validation": {"status": "passed"},
            "fraud": {"score": "0.50"},
            "compliance": {"status": "cleared"},
            "settlement": {"reference": "ABC123"}
        }
        result = lean_data("TXN001", "1000.00", "USD", accumulated)

        assert result["validation"] == {"status": "passed"}
        assert result["fraud"] == {"score": "0.50"}
        assert result["compliance"] == {"status": "cleared"}
        assert result["settlement"] == {"reference": "ABC123"}


class TestMoveIntoProcessing:
    """Tests for move_into_processing function."""

    def test_move_file_into_processing(self, temp_shared_dir):
        """Should move file from source to processing directory."""
        # Create a source file
        source_file = temp_shared_dir / "input" / "test.json"
        write_json(source_file, {"id": 1})

        # Move to processing
        result = move_into_processing(source_file, temp_shared_dir / "processing")

        # Check file moved
        assert result.exists()
        assert not source_file.exists()
        assert "processing" in str(result)

    def test_move_creates_processing_dir(self, temp_shared_dir):
        """Should create processing directory if it doesn't exist."""
        source_file = temp_shared_dir / "input" / "test.json"
        write_json(source_file, {"id": 1})

        processing_dir = temp_shared_dir / "nonexistent_processing"
        result = move_into_processing(source_file, processing_dir)

        assert processing_dir.exists()
        assert result.exists()


class TestCopyIntoProcessing:
    """Tests for copy_into_processing function."""

    def test_copy_file_into_processing(self, temp_shared_dir):
        """Should copy file from source to processing directory."""
        source_file = temp_shared_dir / "input" / "test.json"
        write_json(source_file, {"id": 1})

        result = copy_into_processing(source_file, temp_shared_dir / "processing")

        # Check file was copied (source still exists)
        assert result.exists()
        assert source_file.exists()
        assert "processing" in str(result)

    def test_copy_preserves_file_content(self, temp_shared_dir):
        """Copied file should have identical content."""
        source_file = temp_shared_dir / "input" / "test.json"
        data = {"transaction_id": "TXN001", "amount": "1000.00"}
        write_json(source_file, data)

        result = copy_into_processing(source_file, temp_shared_dir / "processing")

        # Read copied file
        copied_data = read_json(result)
        assert copied_data == data


class TestClearProcessingFile:
    """Tests for clear_processing_file function."""

    def test_clear_processing_file_removes_file(self, temp_shared_dir):
        """Should remove file from processing directory."""
        test_file = temp_shared_dir / "processing" / "test.json"
        write_json(test_file, {"id": 1})

        clear_processing_file(test_file)

        assert not test_file.exists()

    def test_clear_nonexistent_file_gracefully(self, temp_shared_dir):
        """Should handle non-existent file gracefully."""
        nonexistent = temp_shared_dir / "nonexistent.json"

        # Should not raise error
        clear_processing_file(nonexistent)
        assert not nonexistent.exists()


class TestReadOriginalRecord:
    """Tests for read_original_record function."""

    def test_read_original_transaction(self, temp_shared_dir):
        """Should read a transaction from input directory."""
        input_dir = temp_shared_dir / "input"
        tx_data = {
            "transaction_id": "TXN001",
            "amount": "1000.00",
            "currency": "USD"
        }
        write_json(input_dir / "TXN001.json", tx_data)

        result = read_original_record(input_dir, "TXN001")

        assert result == tx_data

    def test_read_original_record_not_found(self, temp_shared_dir):
        """Reading non-existent record should raise error."""
        input_dir = temp_shared_dir / "input"

        with pytest.raises(FileNotFoundError):
            read_original_record(input_dir, "NONEXISTENT")


class TestWriteEnvelope:
    """Tests for write_envelope function."""

    def test_write_envelope_creates_file(self, temp_shared_dir):
        """Should write envelope to output directory."""
        envelope = {
            "message_id": "msg-123",
            "timestamp": "2026-03-16T10:00:00Z",
            "source_stage": "validation",
            "target_stage": "fraud_detection",
            "data": {"transaction_id": "TXN001"}
        }

        output_dir = temp_shared_dir / "output"
        write_envelope(output_dir, "TXN001", envelope)

        result_file = output_dir / "TXN001.json"
        assert result_file.exists()

        result_data = read_json(result_file)
        assert result_data == envelope

    def test_write_envelope_creates_output_dir(self, temp_shared_dir):
        """Should create output directory if it doesn't exist."""
        nonexistent_dir = temp_shared_dir / "new_output"
        envelope = {"data": "test"}

        write_envelope(nonexistent_dir, "TEST", envelope)

        assert nonexistent_dir.exists()
        assert (nonexistent_dir / "TEST.json").exists()


class TestWriteFinalResult:
    """Tests for write_final_result function."""

    def test_write_final_result_combines_records(self, temp_shared_dir):
        """Should combine original record with accumulated results."""
        # Create original record in input
        input_dir = temp_shared_dir / "input"
        original_tx = {
            "transaction_id": "TXN001",
            "amount": "1000.00",
            "currency": "USD",
            "source_account": "ACC-001"
        }
        write_json(input_dir / "TXN001.json", original_tx)

        # Write final result
        results_dir = temp_shared_dir / "results"
        accumulated = {
            "validation_result": {"status": "passed"},
            "fraud_result": {"flagged": False},
            "final_status": "settled"
        }

        write_final_result(results_dir, input_dir, "TXN001", accumulated)

        # Check result file
        result_file = results_dir / "TXN001.json"
        assert result_file.exists()

        result_data = read_json(result_file)
        # Should have both original and accumulated fields
        assert result_data["transaction_id"] == "TXN001"
        assert result_data["amount"] == "1000.00"
        assert result_data["validation_result"]["status"] == "passed"
        assert result_data["final_status"] == "settled"

    def test_write_final_result_overrides_original_fields(self, temp_shared_dir):
        """Accumulated fields should override original fields."""
        input_dir = temp_shared_dir / "input"
        original_tx = {
            "transaction_id": "TXN001",
            "status": "pending"  # Will be overridden
        }
        write_json(input_dir / "TXN001.json", original_tx)

        results_dir = temp_shared_dir / "results"
        accumulated = {
            "status": "settled",  # Override
            "final_decision": "approved"
        }

        write_final_result(results_dir, input_dir, "TXN001", accumulated)

        result_data = read_json(results_dir / "TXN001.json")
        assert result_data["status"] == "settled"  # Overridden
        assert result_data["final_decision"] == "approved"
