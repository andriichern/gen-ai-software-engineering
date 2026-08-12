"""Unit tests for orchestrator.py."""
from __future__ import annotations

import inspect
import json
from unittest.mock import patch

import pytest

import orchestrator
from lib.exchange_rates import ExchangeRates
from lib.message_io import read_json


@pytest.fixture(autouse=True)
def _no_live_exchange_rates(monkeypatch, fake_rates):
    """No orchestrator test may depend on network availability."""
    monkeypatch.setattr(orchestrator, "fetch_exchange_rates", lambda **kwargs: fake_rates)


@pytest.fixture
def isolated_shared(tmp_path, monkeypatch):
    """Redirect orchestrator.SHARED to a throwaway directory so tests never
    touch the project's real shared/ tree."""
    shared = tmp_path / "shared"
    monkeypatch.setattr(orchestrator, "SHARED", shared)
    return shared


# ---------------------------------------------------------------------------
# The stage order is fixed and hardcoded
# ---------------------------------------------------------------------------


def test_orchestrator_stage_order_is_hardcoded_constant():
    assert orchestrator.STAGE_NAMES == [
        "validation",
        "fraud_detection",
        "compliance",
        "settlement",
        "reporting",
    ]


def test_orchestrator_imports_no_service_or_gateway_module():
    import_lines = [
        line.strip()
        for line in inspect.getsource(orchestrator).splitlines()
        if line.strip().startswith("import ") or line.strip().startswith("from ")
    ]
    assert not any("services" in line for line in import_lines)
    assert not any("gateway" in line for line in import_lines)


def test_orchestrator_reads_no_gateway_config_file():
    source = inspect.getsource(orchestrator)
    assert "gateway/config.json" not in source
    assert "config.json" not in source


def test_orchestrator_exposes_no_way_to_change_stage_order():
    """No CLI flag, no environment variable, and run_pipeline's only
    parameter is the dataset source - never an order override."""
    main_source = inspect.getsource(orchestrator.main)
    assert "--order" not in main_source
    add_argument_lines = [line for line in main_source.splitlines() if "add_argument" in line]
    assert not any("order" in line.lower() for line in add_argument_lines)

    sig = inspect.signature(orchestrator.run_pipeline)
    assert list(sig.parameters) == ["source"]

    module_source = inspect.getsource(orchestrator)
    assert "os.environ" not in module_source
    assert "getenv" not in module_source


# ---------------------------------------------------------------------------
# Directory setup / recovery
# ---------------------------------------------------------------------------


def test_reset_shared_tree_creates_all_subdirectories(isolated_shared):
    result = orchestrator._reset_shared_tree()
    assert result == isolated_shared
    for sub in ("input", "processing", "output", "results"):
        assert (isolated_shared / sub).is_dir()


def test_reset_shared_tree_wipes_pre_existing_contents(isolated_shared):
    isolated_shared.mkdir(parents=True)
    stray = isolated_shared / "stray.txt"
    stray.write_text("leftover")
    orchestrator._reset_shared_tree()
    assert not stray.exists()


def test_run_pipeline_missing_source_file_errors_clearly(isolated_shared, sample_dataset_path):
    with pytest.raises(FileNotFoundError):
        orchestrator.run_pipeline(source="does-not-exist.json")


# ---------------------------------------------------------------------------
# Full run: sequencing, output files, per-stage counts
# ---------------------------------------------------------------------------


def test_full_run_processes_every_transaction_through_every_stage(isolated_shared, valid_transactions, tmp_path):
    dataset = tmp_path / "dataset.json"
    dataset.write_text(json.dumps(valid_transactions))

    orchestrator.run_pipeline(source=str(dataset))

    status = read_json(isolated_shared / "status.json")
    assert status["run_completed_at"] is not None

    for stage in orchestrator.STAGE_NAMES:
        assert status["stages"][stage]["processed"] == len(valid_transactions)
        assert status["stages"][stage]["started_at"] is not None
        assert status["stages"][stage]["completed_at"] is not None

    results = list((isolated_shared / "results").glob("*.json"))
    assert len(results) == len(valid_transactions)

    report = read_json(isolated_shared / "report.json")
    assert report["total"] == len(valid_transactions)

    # No record reaches results/ before Reporting: input/ is emptied only
    # after the run completes, and output/processing/ end up empty.
    assert list((isolated_shared / "input").glob("*.json")) == []
    assert list((isolated_shared / "output").glob("*.json")) == []
    assert list((isolated_shared / "processing").glob("*.json")) == []


def test_stages_run_in_order_via_status_timestamps(isolated_shared, valid_transactions, tmp_path):
    dataset = tmp_path / "dataset.json"
    dataset.write_text(json.dumps(valid_transactions))

    orchestrator.run_pipeline(source=str(dataset))

    status = read_json(isolated_shared / "status.json")
    started_times = [status["stages"][s]["started_at"] for s in orchestrator.STAGE_NAMES]
    completed_times = [status["stages"][s]["completed_at"] for s in orchestrator.STAGE_NAMES]

    # Each stage starts no earlier than the previous stage completed.
    for i in range(1, len(orchestrator.STAGE_NAMES)):
        assert started_times[i] >= completed_times[i - 1]


def test_final_results_include_verdict_and_expected_schema_fields(isolated_shared, valid_transactions, tmp_path):
    dataset = tmp_path / "dataset.json"
    dataset.write_text(json.dumps(valid_transactions))
    orchestrator.run_pipeline(source=str(dataset))

    for path in (isolated_shared / "results").glob("*.json"):
        record = read_json(path)
        assert "transaction_id" in record
        assert "verdict" in record
        assert "fraud_flagged" in record
        assert "stage_outcomes" in record
        assert record["verdict"] in ("SETTLED", "REJECTED", "HELD", "INCOMPLETE")


def test_run_pipeline_runs_correctly_with_no_service_running(isolated_shared, valid_transactions, tmp_path):
    """The pipeline is fully self-contained: it never makes an HTTP call to
    any stage service or the gateway, so it must succeed even though no
    service process is running anywhere in this test environment."""
    dataset = tmp_path / "dataset.json"
    dataset.write_text(json.dumps(valid_transactions))

    with patch("httpx.Client.post", side_effect=AssertionError("orchestrator must never call a service")):
        orchestrator.run_pipeline(source=str(dataset))

    report = read_json(isolated_shared / "report.json")
    assert report["total"] == len(valid_transactions)


def test_directory_creation_from_scratch_when_input_dir_absent(isolated_shared, sample_transaction, tmp_path):
    """A missing shared/ tree is created, not treated as an error."""
    dataset = tmp_path / "one.json"
    dataset.write_text(json.dumps([sample_transaction]))
    assert not isolated_shared.exists()

    orchestrator.run_pipeline(source=str(dataset))

    assert isolated_shared.exists()
    assert (isolated_shared / "results").is_dir()
