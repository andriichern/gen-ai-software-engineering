"""True end-to-end integration test: the real orchestrator, the real stages,
the real sample dataset, on a real (temporary) filesystem tree.

The only thing stubbed is the live exchange-rate HTTP call, which is replaced
with fixed ECB-shaped rates so the suite is deterministic and runs offline.
Everything else -- file movement between input/processing/output/results,
message envelopes, the audit trail, status.json, report.json -- is exercised
for real.
"""
import json
from decimal import Decimal
from pathlib import Path

import pytest

import orchestrator
from lib.common import read_json

FIXED_RATES = {"USD": Decimal("1"), "EUR": Decimal("0.92"), "GBP": Decimal("0.79")}

# Expected outcome per record of sample-transactions.json under the
# specification's rules (thresholds: >= 10000 USD high value, non-GB country
# cross-border, outside 06:00-22:00 unusual hour, flag at score >= 0.50).
EXPECTED_FINAL_STATUS = {
    "TXN001": "settled",   # 1500 USD, US, 09:00 -> 0.30, not flagged
    "TXN002": "held",      # 25000 USD high value + cross-border -> flagged
    "TXN003": "settled",   # 9999.99 USD, just under the high-value threshold
    "TXN004": "held",      # 500 EUR, cross-border 0.30 + 02:47 unusual hour 0.20 -> 0.50
    "TXN005": "held",      # 75000 USD high value -> flagged
    "TXN006": "rejected",  # currency XYZ is not ISO 4217 -> validation failure
    "TXN007": "settled",   # -100 GBP refund settles like any other record
    "TXN008": "settled",   # 3200 USD, cross-border only at 10:15 -> 0.30
}


@pytest.fixture
def pipeline_run(tmp_path, sample_dataset_path, monkeypatch):
    """Execute one full pipeline run in an isolated tmp tree and return its paths."""
    monkeypatch.setattr(orchestrator, "fetch_exchange_rates", lambda currencies: dict(FIXED_RATES))

    dataset = tmp_path / "sample-transactions.json"
    dataset.write_text(sample_dataset_path.read_text(encoding="utf-8"), encoding="utf-8")
    shared = tmp_path / "shared"

    orchestrator.run(dataset, shared)

    return {
        "shared": shared,
        "input": shared / "input",
        "processing": shared / "processing",
        "output": shared / "output",
        "results": shared / "results",
        "status": shared / "status.json",
        "report": shared / "report.json",
        "source_records": json.loads(dataset.read_text(encoding="utf-8")),
    }


class TestFullPipelineEndToEnd:
    def test_every_input_transaction_produces_a_result(self, pipeline_run):
        results = sorted(p.stem for p in pipeline_run["results"].glob("*.json"))
        expected = sorted(r["transaction_id"] for r in pipeline_run["source_records"])

        assert results == expected

    def test_no_orphaned_working_files_remain(self, pipeline_run):
        """processing/, output/ and input/ must all be empty at rest after a run."""
        assert list(pipeline_run["processing"].glob("*.json")) == []
        assert list(pipeline_run["output"].glob("*.json")) == []
        assert list(pipeline_run["input"].glob("*.json")) == []
        # The directories themselves survive.
        for key in ("processing", "output", "input", "results"):
            assert pipeline_run[key].is_dir()

    def test_every_result_is_valid_json_with_expected_schema(self, pipeline_run):
        for path in pipeline_run["results"].glob("*.json"):
            record = read_json(path)

            assert record["transaction_id"] == path.stem
            assert record["final_status"] in {"settled", "held", "rejected", "settlement_refused"}
            # Original transaction fields are carried into the final record.
            assert record["amount"]
            assert record["currency"]
            assert record["source_account"]
            # Validation always runs; later results appear only if reached.
            assert record["validation_result"]["status"] in {"passed", "failed"}

    def test_settled_records_carry_full_stage_chain(self, pipeline_run):
        settled = [read_json(p) for p in pipeline_run["results"].glob("*.json")
                   if read_json(p)["final_status"] == "settled"]

        assert settled, "the sample dataset should produce at least one settled record"
        for record in settled:
            assert record["validation_result"]["status"] == "passed"
            assert record["fraud_result"]["flagged"] is False
            assert record["compliance_result"]["status"] == "cleared"
            assert record["settlement_result"]["status"] == "settled"
            assert record["settlement_result"]["settlement_reference"]
            assert record["settlement_result"]["retention_period_years"] == 5

    def test_expected_outcome_per_transaction(self, pipeline_run):
        actual = {
            p.stem: read_json(p)["final_status"]
            for p in pipeline_run["results"].glob("*.json")
        }

        assert actual == EXPECTED_FINAL_STATUS

    def test_rejected_record_never_reached_later_stages(self, pipeline_run):
        record = read_json(pipeline_run["results"] / "TXN006.json")

        assert record["final_status"] == "rejected"
        assert record["validation_result"]["status"] == "failed"
        assert record["reason"]
        # A validation-rejected record must never be scored, cleared or settled.
        assert "fraud_result" not in record
        assert "compliance_result" not in record
        assert "settlement_result" not in record

    def test_held_record_stops_before_settlement(self, pipeline_run):
        record = read_json(pipeline_run["results"] / "TXN005.json")

        assert record["final_status"] == "held"
        assert record["fraud_result"]["flagged"] is True
        assert record["compliance_result"]["status"] == "held"
        assert "settlement_result" not in record

    def test_refund_settles_with_negative_amount_preserved(self, pipeline_run):
        record = read_json(pipeline_run["results"] / "TXN007.json")

        assert record["final_status"] == "settled"
        assert record["settlement_result"]["settled_amount"] == "-100.00"
        assert record["settlement_result"]["currency"] == "GBP"


class TestStatusJson:
    def test_status_json_is_valid_and_complete(self, pipeline_run):
        status = read_json(pipeline_run["status"])

        assert status["run_started_at"]
        assert status["run_completed_at"]
        assert list(status["stages"]) == list(orchestrator.STAGE_ORDER)

    def test_every_stage_reports_a_consistent_tally(self, pipeline_run):
        status = read_json(pipeline_run["status"])

        for stage in orchestrator.STAGE_ORDER:
            entry = status["stages"][stage]
            assert entry["start"] and entry["end"]
            assert entry["processed"] == entry["passed"] + entry["failed"]

    def test_stage_counts_match_the_dataset_flow(self, pipeline_run):
        status = read_json(pipeline_run["status"])
        total = len(pipeline_run["source_records"])

        # Validation sees every input record; one fails (TXN006/XYZ).
        assert status["stages"]["validation"]["processed"] == total
        assert status["stages"]["validation"]["failed"] == 1

        # Only validated records reach fraud detection.
        assert status["stages"]["fraud_detection"]["processed"] == total - 1

        # Compliance sees the same set; flagged ones are held there.
        assert status["stages"]["compliance"]["processed"] == total - 1
        held = status["stages"]["compliance"]["failed"]
        assert held == sum(1 for v in EXPECTED_FINAL_STATUS.values() if v == "held")

        # Settlement and reporting see only the cleared remainder.
        settled = sum(1 for v in EXPECTED_FINAL_STATUS.values() if v == "settled")
        assert status["stages"]["settlement"]["processed"] == settled
        assert status["stages"]["reporting"]["processed"] == settled


class TestReportJson:
    def test_report_json_is_valid_and_totals_match(self, pipeline_run):
        report = read_json(pipeline_run["report"])

        assert report["total_records"] == len(pipeline_run["source_records"])
        counts = report["counts"]
        assert counts["settled"] == sum(1 for v in EXPECTED_FINAL_STATUS.values() if v == "settled")
        assert counts["held"] == sum(1 for v in EXPECTED_FINAL_STATUS.values() if v == "held")
        assert counts["rejected"] == sum(1 for v in EXPECTED_FINAL_STATUS.values() if v == "rejected")

    def test_report_counts_reconcile_with_results_dir(self, pipeline_run):
        report = read_json(pipeline_run["report"])
        statuses = [read_json(p)["final_status"] for p in pipeline_run["results"].glob("*.json")]

        assert report["total_records"] == len(statuses)
        assert report["counts"]["settled"] == statuses.count("settled")

    def test_settled_value_by_currency_is_exact_decimal_arithmetic(self, pipeline_run):
        report = read_json(pipeline_run["report"])
        by_currency = report["total_settled_value_by_currency"]

        expected = {}
        for path in pipeline_run["results"].glob("*.json"):
            record = read_json(path)
            if record["final_status"] != "settled":
                continue
            settlement = record["settlement_result"]
            currency = settlement["currency"]
            expected[currency] = expected.get(currency, Decimal("0")) + Decimal(settlement["settled_amount"])

        assert {k: Decimal(v) for k, v in by_currency.items()} == expected
        # Amounts are strings, never floats, so no precision is lost.
        assert all(isinstance(v, str) for v in by_currency.values())

    def test_risk_score_distribution_present(self, pipeline_run):
        report = read_json(pipeline_run["report"])

        assert "risk_score_distribution" in report
        assert sum(report["risk_score_distribution"].values()) > 0


class TestRerunIdempotency:
    def test_second_run_wipes_and_reproduces_the_same_outcome(
        self, tmp_path, sample_dataset_path, monkeypatch
    ):
        """Running twice must not accumulate stale results or double-count."""
        monkeypatch.setattr(orchestrator, "fetch_exchange_rates", lambda currencies: dict(FIXED_RATES))
        dataset = tmp_path / "sample-transactions.json"
        dataset.write_text(sample_dataset_path.read_text(encoding="utf-8"), encoding="utf-8")
        shared = tmp_path / "shared"

        orchestrator.run(dataset, shared)
        first = {p.stem: read_json(p)["final_status"] for p in (shared / "results").glob("*.json")}
        first_report = read_json(shared / "report.json")

        orchestrator.run(dataset, shared)
        second = {p.stem: read_json(p)["final_status"] for p in (shared / "results").glob("*.json")}
        second_report = read_json(shared / "report.json")

        assert first == second
        assert first_report["total_records"] == second_report["total_records"]
        assert first_report["counts"] == second_report["counts"]

    def test_stale_results_from_a_previous_run_are_removed(
        self, tmp_path, sample_dataset_path, monkeypatch
    ):
        monkeypatch.setattr(orchestrator, "fetch_exchange_rates", lambda currencies: dict(FIXED_RATES))
        dataset = tmp_path / "sample-transactions.json"
        dataset.write_text(sample_dataset_path.read_text(encoding="utf-8"), encoding="utf-8")
        shared = tmp_path / "shared"
        (shared / "results").mkdir(parents=True)
        (shared / "results" / "GHOST.json").write_text(
            json.dumps({"transaction_id": "GHOST", "final_status": "settled"}), encoding="utf-8"
        )

        orchestrator.run(dataset, shared)

        assert not (shared / "results" / "GHOST.json").exists()
        assert read_json(shared / "report.json")["total_records"] == 8


class TestSubsetDatasets:
    """End-to-end runs over the dedicated fixture datasets."""

    def _run(self, tmp_path, monkeypatch, records):
        monkeypatch.setattr(orchestrator, "fetch_exchange_rates", lambda currencies: dict(FIXED_RATES))
        dataset = tmp_path / "ds.json"
        dataset.write_text(json.dumps(records), encoding="utf-8")
        shared = tmp_path / "shared"
        orchestrator.run(dataset, shared)
        return shared

    def test_all_valid_fixtures_reach_a_terminal_state(
        self, tmp_path, monkeypatch, valid_transactions
    ):
        shared = self._run(tmp_path, monkeypatch, valid_transactions)

        results = list((shared / "results").glob("*.json"))
        assert len(results) == len(valid_transactions)
        for path in results:
            assert read_json(path)["validation_result"]["status"] == "passed"

    def test_all_invalid_fixtures_are_rejected_at_validation(
        self, tmp_path, monkeypatch, invalid_transactions
    ):
        usable = [t for t in invalid_transactions if t.get("transaction_id")]
        shared = self._run(tmp_path, monkeypatch, usable)

        results = list((shared / "results").glob("*.json"))
        assert len(results) == len(usable)
        for path in results:
            record = read_json(path)
            assert record["final_status"] == "rejected"
            assert record["validation_result"]["status"] == "failed"

        report = read_json(shared / "report.json")
        assert report["counts"]["rejected"] == len(usable)
        assert report["counts"]["settled"] == 0

    def test_edge_case_fixtures_run_without_error(
        self, tmp_path, monkeypatch, edge_case_transactions
    ):
        shared = self._run(tmp_path, monkeypatch, edge_case_transactions)

        results = list((shared / "results").glob("*.json"))
        assert len(results) == len(edge_case_transactions)
        assert list((shared / "processing").glob("*.json")) == []
        assert read_json(shared / "report.json")["total_records"] == len(edge_case_transactions)

    def test_empty_dataset_produces_an_empty_report(self, tmp_path, monkeypatch):
        shared = self._run(tmp_path, monkeypatch, [])

        assert list((shared / "results").glob("*.json")) == []
        report = read_json(shared / "report.json")
        assert report["total_records"] == 0
        assert report["counts"]["settled"] == 0
