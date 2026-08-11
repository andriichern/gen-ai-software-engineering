"""Tests for each stage's run_stage() file lifecycle and CLI entry point.

The per-stage decision functions (validate_transaction, score_transaction,
check_compliance, settle_transaction, build_report) are covered by their own
test modules. This module covers the layer around them: reading source
directories, moving/copying working files, writing envelopes to output/,
writing terminal records to results/, leaving processing/ empty, the
processed/passed/failed tallies, and the argparse main() entry points.
"""
import json
from decimal import Decimal
from pathlib import Path

import pytest

from lib.common import read_json
from pipeline import compliance, fraud_detection, reporting, settlement, validation


def _valid_record(transaction_id="TXN001", **overrides):
    record = {
        "transaction_id": transaction_id,
        "timestamp": "2026-03-16T10:00:00Z",
        "source_account": "ACC-1001",
        "destination_account": "ACC-2001",
        "amount": "1500.00",
        "currency": "USD",
        "transaction_type": "transfer",
        "description": "Monthly rent payment",
        "metadata": {"channel": "online", "country": "US"},
    }
    record.update(overrides)
    return record


# ---------------------------------------------------------------------------
# Validation
# ---------------------------------------------------------------------------


class TestValidationRunStage:
    def test_passing_record_writes_envelope_to_output(self, stage_dirs, put_input):
        put_input(_valid_record())

        tally = validation.run_stage(
            stage_dirs["input"], stage_dirs["processing"], stage_dirs["output"], stage_dirs["results"]
        )

        assert tally == {"processed": 1, "passed": 1, "failed": 0}
        envelope = read_json(stage_dirs["output"] / "TXN001.json")
        assert envelope["source_stage"] == "validation"
        assert envelope["target_stage"] == "fraud_detection"
        assert envelope["data"]["validation_result"]["status"] == "passed"
        # The lean envelope must not carry the full original record.
        assert "source_account" not in envelope["data"]

    def test_failing_record_writes_rejected_final_result(self, stage_dirs, put_input):
        put_input(_valid_record("TXN_BAD", currency="XYZ"))

        tally = validation.run_stage(
            stage_dirs["input"], stage_dirs["processing"], stage_dirs["output"], stage_dirs["results"]
        )

        assert tally == {"processed": 1, "passed": 0, "failed": 1}
        assert not (stage_dirs["output"] / "TXN_BAD.json").exists()
        final = read_json(stage_dirs["results"] / "TXN_BAD.json")
        assert final["final_status"] == "rejected"
        assert final["validation_result"]["status"] == "failed"
        assert final["reason"]
        # The final record joins the original transaction with the results.
        assert final["source_account"] == "ACC-1001"

    def test_input_is_copied_not_moved(self, stage_dirs, put_input):
        """Validation must leave shared/input/ intact for later stages to re-read."""
        put_input(_valid_record())

        validation.run_stage(
            stage_dirs["input"], stage_dirs["processing"], stage_dirs["output"], stage_dirs["results"]
        )

        assert (stage_dirs["input"] / "TXN001.json").exists()

    def test_processing_dir_is_empty_afterwards(self, stage_dirs, put_input):
        put_input(_valid_record())
        put_input(_valid_record("TXN002", currency="XYZ"))

        validation.run_stage(
            stage_dirs["input"], stage_dirs["processing"], stage_dirs["output"], stage_dirs["results"]
        )

        assert list(stage_dirs["processing"].iterdir()) == []

    def test_mixed_batch_tally(self, stage_dirs, put_input):
        put_input(_valid_record("OK1"))
        put_input(_valid_record("OK2"))
        put_input(_valid_record("BAD1", currency="XYZ"))

        tally = validation.run_stage(
            stage_dirs["input"], stage_dirs["processing"], stage_dirs["output"], stage_dirs["results"]
        )

        assert tally == {"processed": 3, "passed": 2, "failed": 1}

    def test_empty_input_dir_returns_zero_tally(self, stage_dirs):
        tally = validation.run_stage(
            stage_dirs["input"], stage_dirs["processing"], stage_dirs["output"], stage_dirs["results"]
        )
        assert tally == {"processed": 0, "passed": 0, "failed": 0}

    def test_missing_input_dir_returns_zero_tally(self, stage_dirs):
        """A non-existent source directory is an empty batch, not a crash."""
        tally = validation.run_stage(
            stage_dirs["shared"] / "nope", stage_dirs["processing"], stage_dirs["output"], stage_dirs["results"]
        )
        assert tally == {"processed": 0, "passed": 0, "failed": 0}

    def test_main_cli(self, stage_dirs, put_input, monkeypatch, capsys):
        put_input(_valid_record())
        monkeypatch.setattr(
            "sys.argv",
            [
                "validation.py",
                "--input-dir", str(stage_dirs["input"]),
                "--output-dir", str(stage_dirs["output"]),
                "--processing-dir", str(stage_dirs["processing"]),
                "--results-dir", str(stage_dirs["results"]),
            ],
        )

        validation.main()

        out = capsys.readouterr().out
        assert "[validation] processed=1 passed=1 failed=0" in out

    def test_default_shared_dir(self):
        assert validation._default_shared_dir() == Path("shared")


# ---------------------------------------------------------------------------
# Fraud detection
# ---------------------------------------------------------------------------


class TestFraudDetectionRunStage:
    def test_scored_record_forwarded_to_compliance(self, stage_dirs, put_input, put_envelope, fake_rates):
        put_input(_valid_record())
        put_envelope("TXN001", {
            "transaction_id": "TXN001", "amount": "1500.00", "currency": "USD",
            "validation_result": {"status": "passed"},
        })

        tally = fraud_detection.run_stage(
            stage_dirs["input"], stage_dirs["processing"], stage_dirs["output"], fake_rates
        )

        assert tally == {"processed": 1, "passed": 1, "failed": 0}
        envelope = read_json(stage_dirs["output"] / "TXN001.json")
        assert envelope["source_stage"] == "fraud_detection"
        assert envelope["target_stage"] == "compliance"
        assert envelope["data"]["fraud_result"]["flagged"] is False
        # Fields the later stages need are re-read from the original record.
        assert envelope["data"]["country"] == "US"
        assert envelope["data"]["transaction_timestamp"] == "2026-03-16T10:00:00Z"

    def test_flagged_record_counts_as_failed_but_still_forwarded(
        self, stage_dirs, put_input, put_envelope, fake_rates
    ):
        """Flagging is never a rejection: the record still moves to compliance."""
        put_input(_valid_record("TXN_HIGH", amount="75000.00"))
        put_envelope("TXN_HIGH", {
            "transaction_id": "TXN_HIGH", "amount": "75000.00", "currency": "USD",
            "validation_result": {"status": "passed"},
        })

        tally = fraud_detection.run_stage(
            stage_dirs["input"], stage_dirs["processing"], stage_dirs["output"], fake_rates
        )

        assert tally == {"processed": 1, "passed": 0, "failed": 1}
        envelope = read_json(stage_dirs["output"] / "TXN_HIGH.json")
        assert envelope["data"]["fraud_result"]["flagged"] is True

    def test_source_envelope_is_moved_and_processing_cleared(
        self, stage_dirs, put_input, put_envelope, fake_rates
    ):
        put_input(_valid_record())
        put_envelope("TXN001", {
            "transaction_id": "TXN001", "amount": "1500.00", "currency": "USD",
            "validation_result": {"status": "passed"},
        })

        fraud_detection.run_stage(
            stage_dirs["input"], stage_dirs["processing"], stage_dirs["output"], fake_rates
        )

        assert list(stage_dirs["processing"].iterdir()) == []
        # output/ holds exactly the rewritten envelope, not a stale duplicate.
        assert [p.name for p in stage_dirs["output"].iterdir()] == ["TXN001.json"]

    def test_missing_rate_for_currency_raises(self, stage_dirs, put_input, put_envelope):
        put_input(_valid_record("TXN_EUR", currency="EUR"))
        put_envelope("TXN_EUR", {
            "transaction_id": "TXN_EUR", "amount": "500.00", "currency": "EUR",
            "validation_result": {"status": "passed"},
        })

        with pytest.raises(ValueError, match="no exchange rate available"):
            fraud_detection.run_stage(
                stage_dirs["input"], stage_dirs["processing"], stage_dirs["output"], {"USD": Decimal("1")}
            )

    def test_main_cli_fetches_rates_for_currencies_present(
        self, stage_dirs, put_input, put_envelope, monkeypatch, capsys
    ):
        put_input(_valid_record("TXN_EUR", currency="EUR", amount="500.00"))
        put_envelope("TXN_EUR", {
            "transaction_id": "TXN_EUR", "amount": "500.00", "currency": "EUR",
            "validation_result": {"status": "passed"},
        })

        requested = {}

        def fake_fetch(currencies):
            requested["currencies"] = set(currencies)
            return {"USD": Decimal("1"), "EUR": Decimal("0.92")}

        monkeypatch.setattr("lib.exchange_rates.fetch_exchange_rates", fake_fetch)
        monkeypatch.setattr(
            "sys.argv",
            [
                "fraud_detection.py",
                "--input-dir", str(stage_dirs["input"]),
                "--output-dir", str(stage_dirs["output"]),
                "--processing-dir", str(stage_dirs["processing"]),
            ],
        )

        fraud_detection.main()

        assert requested["currencies"] == {"EUR"}
        assert "[fraud_detection] processed=1" in capsys.readouterr().out

    def test_main_cli_skips_fetch_when_no_records(self, stage_dirs, monkeypatch, capsys):
        def boom(currencies):  # pragma: no cover - must never be called
            raise AssertionError("exchange rates must not be fetched for an empty batch")

        monkeypatch.setattr("lib.exchange_rates.fetch_exchange_rates", boom)
        monkeypatch.setattr(
            "sys.argv",
            [
                "fraud_detection.py",
                "--input-dir", str(stage_dirs["input"]),
                "--output-dir", str(stage_dirs["output"]),
                "--processing-dir", str(stage_dirs["processing"]),
            ],
        )

        fraud_detection.main()

        assert "[fraud_detection] processed=0 passed=0 failed=0" in capsys.readouterr().out

    def test_default_shared_dir(self):
        assert fraud_detection._default_shared_dir() == Path("shared")


# ---------------------------------------------------------------------------
# Compliance
# ---------------------------------------------------------------------------


def _fraud_data(transaction_id="TXN001", flagged=False, score="0.00", **overrides):
    data = {
        "transaction_id": transaction_id,
        "amount": "1500.00",
        "currency": "USD",
        "validation_result": {"status": "passed"},
        "fraud_result": {"score": score, "flagged": flagged, "factors": {}},
        "country": "US",
        "transaction_timestamp": "2026-03-16T10:00:00Z",
    }
    data.update(overrides)
    return data


class TestComplianceRunStage:
    def test_cleared_record_forwarded_to_settlement(self, stage_dirs, put_input, put_envelope):
        put_input(_valid_record())
        put_envelope("TXN001", _fraud_data())

        tally = compliance.run_stage(
            stage_dirs["input"], stage_dirs["processing"], stage_dirs["output"], stage_dirs["results"]
        )

        assert tally == {"processed": 1, "passed": 1, "failed": 0}
        envelope = read_json(stage_dirs["output"] / "TXN001.json")
        assert envelope["target_stage"] == "settlement"
        assert envelope["data"]["compliance_result"]["status"] == "cleared"
        assert not (stage_dirs["results"] / "TXN001.json").exists()

    def test_flagged_record_is_held_and_terminates(self, stage_dirs, put_input, put_envelope):
        put_input(_valid_record("TXN_FLAG"))
        put_envelope("TXN_FLAG", _fraud_data("TXN_FLAG", flagged=True, score="0.70"))

        tally = compliance.run_stage(
            stage_dirs["input"], stage_dirs["processing"], stage_dirs["output"], stage_dirs["results"]
        )

        assert tally == {"processed": 1, "passed": 0, "failed": 1}
        assert not (stage_dirs["output"] / "TXN_FLAG.json").exists()
        final = read_json(stage_dirs["results"] / "TXN_FLAG.json")
        assert final["final_status"] == "held"
        assert "0.70" in final["reason"]
        assert final["compliance_result"]["status"] == "held"

    def test_missing_fraud_result_defaults_to_cleared(self, stage_dirs, put_input, put_envelope):
        data = _fraud_data("TXN_NOFRAUD")
        del data["fraud_result"]
        put_input(_valid_record("TXN_NOFRAUD"))
        put_envelope("TXN_NOFRAUD", data)

        tally = compliance.run_stage(
            stage_dirs["input"], stage_dirs["processing"], stage_dirs["output"], stage_dirs["results"]
        )

        assert tally["passed"] == 1

    def test_processing_dir_cleared(self, stage_dirs, put_input, put_envelope):
        put_input(_valid_record())
        put_envelope("TXN001", _fraud_data())

        compliance.run_stage(
            stage_dirs["input"], stage_dirs["processing"], stage_dirs["output"], stage_dirs["results"]
        )

        assert list(stage_dirs["processing"].iterdir()) == []

    def test_main_cli(self, stage_dirs, put_input, put_envelope, monkeypatch, capsys):
        put_input(_valid_record())
        put_envelope("TXN001", _fraud_data())
        monkeypatch.setattr(
            "sys.argv",
            [
                "compliance.py",
                "--input-dir", str(stage_dirs["input"]),
                "--output-dir", str(stage_dirs["output"]),
                "--processing-dir", str(stage_dirs["processing"]),
                "--results-dir", str(stage_dirs["results"]),
            ],
        )

        compliance.main()

        assert "[compliance] processed=1 passed=1 failed=0" in capsys.readouterr().out

    def test_default_shared_dir(self):
        assert compliance._default_shared_dir() == Path("shared")


# ---------------------------------------------------------------------------
# Settlement
# ---------------------------------------------------------------------------


def _cleared_data(transaction_id="TXN001", compliance_status="cleared", **overrides):
    data = _fraud_data(transaction_id)
    data["compliance_result"] = {"status": compliance_status, "reason": None,
                                 "checked_at": "2026-03-16T10:00:00+00:00"}
    data.update(overrides)
    return data


class TestSettlementRunStage:
    def test_cleared_record_settles_to_output(self, stage_dirs, put_input, put_envelope):
        put_input(_valid_record())
        put_envelope("TXN001", _cleared_data())

        tally = settlement.run_stage(
            stage_dirs["input"], stage_dirs["processing"], stage_dirs["output"], stage_dirs["results"]
        )

        assert tally == {"processed": 1, "passed": 1, "failed": 0}
        envelope = read_json(stage_dirs["output"] / "TXN001.json")
        assert envelope["target_stage"] == "reporting"
        result = envelope["data"]["settlement_result"]
        assert result["status"] == "settled"
        assert result["settled_amount"] == "1500.00"
        assert result["retention_period_years"] == 5
        assert result["settlement_reference"]

    def test_uncleared_record_is_refused(self, stage_dirs, put_input, put_envelope):
        put_input(_valid_record("TXN_HELD"))
        put_envelope("TXN_HELD", _cleared_data("TXN_HELD", compliance_status="held"))

        tally = settlement.run_stage(
            stage_dirs["input"], stage_dirs["processing"], stage_dirs["output"], stage_dirs["results"]
        )

        assert tally == {"processed": 1, "passed": 0, "failed": 1}
        assert not (stage_dirs["output"] / "TXN_HELD.json").exists()
        final = read_json(stage_dirs["results"] / "TXN_HELD.json")
        assert final["final_status"] == "settlement_refused"
        assert "not cleared" in final["reason"]

    def test_missing_compliance_result_is_refused(self, stage_dirs, put_input, put_envelope):
        data = _cleared_data("TXN_NOCOMP")
        del data["compliance_result"]
        put_input(_valid_record("TXN_NOCOMP"))
        put_envelope("TXN_NOCOMP", data)

        tally = settlement.run_stage(
            stage_dirs["input"], stage_dirs["processing"], stage_dirs["output"], stage_dirs["results"]
        )

        assert tally["failed"] == 1
        assert read_json(stage_dirs["results"] / "TXN_NOCOMP.json")["final_status"] == "settlement_refused"

    def test_refund_settles_with_negative_amount(self, stage_dirs, put_input, put_envelope):
        put_input(_valid_record("TXN_REFUND", amount="-100.00", transaction_type="refund"))
        put_envelope("TXN_REFUND", _cleared_data("TXN_REFUND", amount="-100.00"))

        tally = settlement.run_stage(
            stage_dirs["input"], stage_dirs["processing"], stage_dirs["output"], stage_dirs["results"]
        )

        assert tally["passed"] == 1
        envelope = read_json(stage_dirs["output"] / "TXN_REFUND.json")
        assert envelope["data"]["settlement_result"]["settled_amount"] == "-100.00"

    def test_processing_dir_cleared(self, stage_dirs, put_input, put_envelope):
        put_input(_valid_record())
        put_envelope("TXN001", _cleared_data())

        settlement.run_stage(
            stage_dirs["input"], stage_dirs["processing"], stage_dirs["output"], stage_dirs["results"]
        )

        assert list(stage_dirs["processing"].iterdir()) == []

    def test_main_cli(self, stage_dirs, put_input, put_envelope, monkeypatch, capsys):
        put_input(_valid_record())
        put_envelope("TXN001", _cleared_data())
        monkeypatch.setattr(
            "sys.argv",
            [
                "settlement.py",
                "--input-dir", str(stage_dirs["input"]),
                "--output-dir", str(stage_dirs["output"]),
                "--processing-dir", str(stage_dirs["processing"]),
                "--results-dir", str(stage_dirs["results"]),
            ],
        )

        settlement.main()

        assert "[settlement] processed=1 passed=1 failed=0" in capsys.readouterr().out

    def test_default_shared_dir(self):
        assert settlement._default_shared_dir() == Path("shared")


# ---------------------------------------------------------------------------
# Reporting
# ---------------------------------------------------------------------------


def _settled_data(transaction_id="TXN001", amount="1500.00", currency="USD"):
    data = _cleared_data(transaction_id)
    data["amount"] = amount
    data["currency"] = currency
    data["settlement_result"] = {
        "status": "settled",
        "settlement_reference": f"ref-{transaction_id}",
        "settlement_timestamp": "2026-03-16T10:00:05+00:00",
        "settled_amount": amount,
        "currency": currency,
        "retention_period_years": 5,
    }
    return data


class TestReportingRunStage:
    def test_settled_record_finalized_and_report_written(self, stage_dirs, put_input, put_envelope):
        put_input(_valid_record())
        put_envelope("TXN001", _settled_data())

        tally = reporting.run_stage(
            stage_dirs["input"], stage_dirs["processing"], stage_dirs["output"], stage_dirs["results"]
        )

        assert tally == {"processed": 1, "passed": 1, "failed": 0}
        final = read_json(stage_dirs["results"] / "TXN001.json")
        assert final["final_status"] == "settled"
        assert final["settlement_result"]["settlement_reference"] == "ref-TXN001"
        # The final record is the original joined with every stage result.
        assert final["source_account"] == "ACC-1001"

        report = read_json(stage_dirs["shared"] / "report.json")
        assert report["total_records"] == 1
        assert report["counts"]["settled"] == 1

    def test_report_includes_records_terminated_in_earlier_stages(
        self, stage_dirs, put_input, put_envelope
    ):
        """Rejected/held records already sitting in results/ must be counted."""
        (stage_dirs["results"] / "TXN_REJ.json").write_text(json.dumps({
            "transaction_id": "TXN_REJ",
            "validation_result": {"status": "failed"},
            "final_status": "rejected",
        }), encoding="utf-8")
        (stage_dirs["results"] / "TXN_HELD.json").write_text(json.dumps({
            "transaction_id": "TXN_HELD",
            "validation_result": {"status": "passed"},
            "fraud_result": {"flagged": True, "score": "0.70"},
            "compliance_result": {"status": "held"},
            "final_status": "held",
        }), encoding="utf-8")
        put_input(_valid_record())
        put_envelope("TXN001", _settled_data())

        reporting.run_stage(
            stage_dirs["input"], stage_dirs["processing"], stage_dirs["output"], stage_dirs["results"]
        )

        report = read_json(stage_dirs["shared"] / "report.json")
        assert report["total_records"] == 3
        assert report["counts"]["rejected"] == 1
        assert report["counts"]["held"] == 1
        assert report["counts"]["settled"] == 1

    def test_settled_value_aggregated_by_currency(self, stage_dirs, put_input, put_envelope):
        put_input(_valid_record("A", currency="USD", amount="1000.00"))
        put_input(_valid_record("B", currency="USD", amount="500.00"))
        put_input(_valid_record("C", currency="EUR", amount="250.00"))
        put_envelope("A", _settled_data("A", amount="1000.00", currency="USD"))
        put_envelope("B", _settled_data("B", amount="500.00", currency="USD"))
        put_envelope("C", _settled_data("C", amount="250.00", currency="EUR"))

        tally = reporting.run_stage(
            stage_dirs["input"], stage_dirs["processing"], stage_dirs["output"], stage_dirs["results"]
        )

        assert tally["processed"] == 3
        report = read_json(stage_dirs["shared"] / "report.json")
        assert report["total_settled_value_by_currency"]["USD"] == "1500.00"
        assert report["total_settled_value_by_currency"]["EUR"] == "250.00"

    def test_processing_and_output_dirs_left_empty(self, stage_dirs, put_input, put_envelope):
        """Reporting defers clearing processing/ until after the report is built."""
        put_input(_valid_record())
        put_envelope("TXN001", _settled_data())

        reporting.run_stage(
            stage_dirs["input"], stage_dirs["processing"], stage_dirs["output"], stage_dirs["results"]
        )

        assert list(stage_dirs["processing"].iterdir()) == []
        assert list(stage_dirs["output"].iterdir()) == []

    def test_empty_batch_still_writes_report(self, stage_dirs):
        tally = reporting.run_stage(
            stage_dirs["input"], stage_dirs["processing"], stage_dirs["output"], stage_dirs["results"]
        )

        assert tally == {"processed": 0, "passed": 0, "failed": 0}
        report = read_json(stage_dirs["shared"] / "report.json")
        assert report["total_records"] == 0

    def test_main_cli(self, stage_dirs, put_input, put_envelope, monkeypatch, capsys):
        put_input(_valid_record())
        put_envelope("TXN001", _settled_data())
        monkeypatch.setattr(
            "sys.argv",
            [
                "reporting.py",
                "--input-dir", str(stage_dirs["input"]),
                "--output-dir", str(stage_dirs["output"]),
                "--processing-dir", str(stage_dirs["processing"]),
                "--results-dir", str(stage_dirs["results"]),
            ],
        )

        reporting.main()

        assert "[reporting] processed=1 passed=1 failed=0" in capsys.readouterr().out

    def test_default_shared_dir(self):
        assert reporting._default_shared_dir() == Path("shared")
