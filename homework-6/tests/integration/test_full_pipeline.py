"""End-to-end integration test: runs the real orchestrator against a
temporary shared/ tree seeded from sample-transactions.json, and validates
the full on-disk contract - status.json, report.json, and one results/ file
per transaction with the expected schema.
"""
from __future__ import annotations

import json

import pytest

import orchestrator
from lib.message_io import read_json


@pytest.fixture(autouse=True)
def _no_live_exchange_rates(monkeypatch, fake_rates):
    monkeypatch.setattr(orchestrator, "fetch_exchange_rates", lambda **kwargs: fake_rates)


@pytest.fixture
def isolated_shared(tmp_path, monkeypatch):
    shared = tmp_path / "shared"
    monkeypatch.setattr(orchestrator, "SHARED", shared)
    return shared


def test_full_pipeline_run_against_sample_transactions(isolated_shared, sample_dataset_path, tmp_path):
    assert sample_dataset_path.exists(), "sample-transactions.json must exist at the project root"
    input_records = json.loads(sample_dataset_path.read_text())
    if isinstance(input_records, dict):
        input_records = [input_records]

    orchestrator.run_pipeline(source=str(sample_dataset_path))

    # status.json exists, is valid JSON, and every stage's processed count
    # equals the total record count.
    status = read_json(isolated_shared / "status.json")
    assert status["run_completed_at"] is not None
    for stage in orchestrator.STAGE_NAMES:
        assert status["stages"][stage]["processed"] == len(input_records)

    # report.json exists with aggregate counts that sum to the total.
    report = read_json(isolated_shared / "report.json")
    assert report["total"] == len(input_records)
    assert report["settled"] + report["rejected"] + report["held"] + report["incomplete"] == report["total"]

    # Every transaction produced exactly one results/ file.
    result_files = sorted((isolated_shared / "results").glob("*.json"))
    assert len(result_files) == len(input_records)
    assert {p.stem for p in result_files} == {r["transaction_id"] for r in input_records}

    # Each final record matches the expected schema and joins the original
    # fields with the accumulated stage outcomes and verdict.
    for path in result_files:
        record = read_json(path)
        for field in ("transaction_id", "verdict", "fraud_flagged", "reason", "stage_outcomes"):
            assert field in record
        assert record["verdict"] in ("SETTLED", "REJECTED", "HELD", "INCOMPLETE")
        # Original record fields are preserved (joined, not replaced).
        assert "amount" in record
        assert "currency" in record

    # No orphaned files left behind in processing/ or output/.
    assert list((isolated_shared / "processing").glob("*.json")) == []
    assert list((isolated_shared / "output").glob("*.json")) == []
    # input/ is emptied once the run completes (nothing left to read it).
    assert list((isolated_shared / "input").glob("*.json")) == []


def test_full_pipeline_run_against_valid_transactions_fixture(isolated_shared, valid_transactions, tmp_path):
    """A second, independent run (using the curated fixture dataset instead
    of the live sample dataset) proves the pipeline is repeatable and not
    coupled to any particular input file."""
    dataset_path = tmp_path / "valid.json"
    dataset_path.write_text(json.dumps(valid_transactions))

    orchestrator.run_pipeline(source=str(dataset_path))

    results = list((isolated_shared / "results").glob("*.json"))
    assert len(results) == len(valid_transactions)

    for path in results:
        record = read_json(path)
        # Every valid-fixture transaction passed validation, so none can be
        # REJECTED for a validation reason; INCOMPLETE only if a downstream
        # rule couldn't run.
        assert record["verdict"] in ("SETTLED", "HELD", "INCOMPLETE")
