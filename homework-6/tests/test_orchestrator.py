"""Unit tests for orchestrator.py.

Covers the orchestrator's own responsibilities in isolation: currency
filtering, wiping/recreating the shared tree, ingesting the input dataset,
live status publishing, stage sequencing, and the CLI entry point.

Every test stubs out fetch_exchange_rates, so no test here touches the
network. Stage sequencing tests stub the stage functions themselves, so a
failure points at the orchestrator rather than at a stage's business logic.
"""
import json
from decimal import Decimal
from pathlib import Path

import pytest

import orchestrator
from lib.common import read_json
from lib.exchange_rates import ExchangeRateError


@pytest.fixture
def offline_rates(monkeypatch, fake_rates):
    """Replace the live exchange-rate fetch with a deterministic stub."""
    calls = []

    def fake_fetch(currencies):
        calls.append(list(currencies))
        return dict(fake_rates)

    monkeypatch.setattr(orchestrator, "fetch_exchange_rates", fake_fetch)
    return calls


@pytest.fixture
def dataset(tmp_path, sample_dataset_path):
    """A copy of the real sample dataset, placed in the test's tmp tree."""
    target = tmp_path / "input-dataset.json"
    target.write_text(sample_dataset_path.read_text(encoding="utf-8"), encoding="utf-8")
    return target


def _write_dataset(path: Path, records) -> Path:
    path.write_text(json.dumps(records), encoding="utf-8")
    return path


# ---------------------------------------------------------------------------
# Currency validation
# ---------------------------------------------------------------------------


class TestIso4217Valid:
    @pytest.mark.parametrize("code", ["USD", "EUR", "GBP", "JPY"])
    def test_real_currency_codes(self, code):
        assert orchestrator._iso4217_valid(code) is True

    def test_lowercase_is_accepted(self):
        assert orchestrator._iso4217_valid("usd") is True

    @pytest.mark.parametrize("code", ["XYZ", "ZZZ", "US", "USDD", ""])
    def test_invalid_codes(self, code):
        assert orchestrator._iso4217_valid(code) is False

    @pytest.mark.parametrize("code", [None, 123, ["USD"], {"currency": "USD"}])
    def test_non_string_values(self, code):
        assert orchestrator._iso4217_valid(code) is False


# ---------------------------------------------------------------------------
# Shared tree setup
# ---------------------------------------------------------------------------


class TestWipeAndCreateSharedTree:
    def test_creates_all_four_directories(self, tmp_path):
        shared = tmp_path / "shared"

        dirs = orchestrator._wipe_and_create_shared_tree(shared)

        assert set(dirs) == {"input", "processing", "output", "results"}
        for path in dirs.values():
            assert path.is_dir()

    def test_creates_tree_when_parent_missing(self, tmp_path):
        shared = tmp_path / "deeply" / "nested" / "shared"

        dirs = orchestrator._wipe_and_create_shared_tree(shared)

        assert dirs["input"].is_dir()

    def test_wipes_pre_existing_content(self, tmp_path):
        shared = tmp_path / "shared"
        (shared / "results").mkdir(parents=True)
        stale = shared / "results" / "OLD.json"
        stale.write_text("{}", encoding="utf-8")
        stale_root = shared / "report.json"
        stale_root.write_text("{}", encoding="utf-8")

        dirs = orchestrator._wipe_and_create_shared_tree(shared)

        assert not stale.exists()
        assert not stale_root.exists()
        assert list(dirs["results"].iterdir()) == []


# ---------------------------------------------------------------------------
# Input ingestion
# ---------------------------------------------------------------------------


class TestCopyInputDataset:
    def test_writes_one_file_per_transaction(self, tmp_path, stage_dirs):
        source = _write_dataset(tmp_path / "ds.json", [
            {"transaction_id": "T1", "amount": "1.00", "currency": "USD"},
            {"transaction_id": "T2", "amount": "2.00", "currency": "USD"},
        ])

        records = orchestrator._copy_input_dataset(source, stage_dirs["input"])

        assert len(records) == 2
        assert read_json(stage_dirs["input"] / "T1.json")["amount"] == "1.00"
        assert read_json(stage_dirs["input"] / "T2.json")["currency"] == "USD"

    def test_real_sample_dataset_ingests(self, dataset, stage_dirs):
        records = orchestrator._copy_input_dataset(dataset, stage_dirs["input"])

        assert len(records) == 8
        assert len(list(stage_dirs["input"].glob("*.json"))) == 8

    def test_missing_file_raises_file_not_found(self, tmp_path, stage_dirs):
        with pytest.raises(FileNotFoundError, match="input dataset not found"):
            orchestrator._copy_input_dataset(tmp_path / "nope.json", stage_dirs["input"])

    def test_non_json_suffix_raises_value_error(self, tmp_path, stage_dirs):
        source = tmp_path / "ds.csv"
        source.write_text("transaction_id,amount\n", encoding="utf-8")

        with pytest.raises(ValueError, match="must be a JSON array"):
            orchestrator._copy_input_dataset(source, stage_dirs["input"])

    def test_json_object_instead_of_array_raises(self, tmp_path, stage_dirs):
        source = _write_dataset(tmp_path / "ds.json", {"transaction_id": "T1"})

        with pytest.raises(ValueError, match="must be a JSON array"):
            orchestrator._copy_input_dataset(source, stage_dirs["input"])

    def test_record_missing_transaction_id_raises(self, tmp_path, stage_dirs):
        source = _write_dataset(tmp_path / "ds.json", [{"amount": "1.00", "currency": "USD"}])

        with pytest.raises(ValueError, match="missing transaction_id"):
            orchestrator._copy_input_dataset(source, stage_dirs["input"])

    def test_record_with_empty_transaction_id_raises(self, tmp_path, stage_dirs):
        source = _write_dataset(tmp_path / "ds.json", [{"transaction_id": "", "amount": "1.00"}])

        with pytest.raises(ValueError, match="missing transaction_id"):
            orchestrator._copy_input_dataset(source, stage_dirs["input"])

    def test_empty_array_is_allowed(self, tmp_path, stage_dirs):
        source = _write_dataset(tmp_path / "ds.json", [])

        records = orchestrator._copy_input_dataset(source, stage_dirs["input"])

        assert records == []
        assert list(stage_dirs["input"].iterdir()) == []


# ---------------------------------------------------------------------------
# Status publishing
# ---------------------------------------------------------------------------


class TestStatusPublisher:
    def test_writes_file_on_construction(self, tmp_path):
        path = tmp_path / "status.json"

        orchestrator.StatusPublisher(path)

        state = read_json(path)
        assert state["stages"] == {}
        assert state["run_started_at"]

    def test_start_stage_records_start_time(self, tmp_path):
        path = tmp_path / "status.json"
        publisher = orchestrator.StatusPublisher(path)

        publisher.start_stage("validation")

        state = read_json(path)
        assert "start" in state["stages"]["validation"]
        assert "end" not in state["stages"]["validation"]

    def test_complete_stage_records_tally(self, tmp_path):
        path = tmp_path / "status.json"
        publisher = orchestrator.StatusPublisher(path)
        publisher.start_stage("validation")

        publisher.complete_stage("validation", {"processed": 8, "passed": 7, "failed": 1})

        stage = read_json(path)["stages"]["validation"]
        assert stage["processed"] == 8
        assert stage["passed"] == 7
        assert stage["failed"] == 1
        assert stage["start"] and stage["end"]

    def test_complete_run_stamps_completion(self, tmp_path):
        path = tmp_path / "status.json"
        publisher = orchestrator.StatusPublisher(path)

        publisher.complete_run()

        assert read_json(path)["run_completed_at"]

    def test_multiple_stages_accumulate(self, tmp_path):
        path = tmp_path / "status.json"
        publisher = orchestrator.StatusPublisher(path)

        for stage in ("validation", "fraud_detection"):
            publisher.start_stage(stage)
            publisher.complete_stage(stage, {"processed": 1, "passed": 1, "failed": 0})

        assert set(read_json(path)["stages"]) == {"validation", "fraud_detection"}

    def test_status_file_is_flushed_live_not_only_at_end(self, tmp_path):
        """status.json must be readable mid-run, since the UI polls it."""
        path = tmp_path / "status.json"
        publisher = orchestrator.StatusPublisher(path)
        publisher.start_stage("validation")

        # Readable and parseable before complete_run() is ever called.
        state = read_json(path)
        assert "run_completed_at" not in state
        assert state["stages"]["validation"]["start"]


# ---------------------------------------------------------------------------
# run() orchestration
# ---------------------------------------------------------------------------


class TestRunOrchestration:
    def test_stages_run_in_fixed_order(self, tmp_path, dataset, offline_rates, monkeypatch, capsys):
        called = []

        def make_stub(name):
            def stub(*args, **kwargs):
                called.append(name)
                return {"processed": 1, "passed": 1, "failed": 0}
            return stub

        for name in orchestrator.STAGE_ORDER:
            module = {
                "validation": orchestrator.validation,
                "fraud_detection": orchestrator.fraud_detection,
                "compliance": orchestrator.compliance,
                "settlement": orchestrator.settlement,
                "reporting": orchestrator.reporting,
            }[name]
            monkeypatch.setattr(module, "run_stage", make_stub(name))

        orchestrator.run(dataset, tmp_path / "shared")

        assert called == list(orchestrator.STAGE_ORDER)

    def test_only_valid_currencies_are_requested(self, tmp_path, dataset, offline_rates, monkeypatch):
        """The sample dataset contains the bogus code XYZ, which must be filtered out."""
        for module in (orchestrator.validation, orchestrator.fraud_detection, orchestrator.compliance,
                       orchestrator.settlement, orchestrator.reporting):
            monkeypatch.setattr(module, "run_stage",
                                lambda *a, **k: {"processed": 0, "passed": 0, "failed": 0})

        orchestrator.run(dataset, tmp_path / "shared")

        requested = offline_rates[0]
        assert "XYZ" not in requested
        # USD is passed through too; fetch_exchange_rates drops the base itself.
        assert set(requested) == {"USD", "EUR", "GBP"}

    def test_usd_only_dataset_requests_no_quotes(self, tmp_path, offline_rates, monkeypatch):
        source = _write_dataset(tmp_path / "ds.json", [
            {"transaction_id": "T1", "amount": "1.00", "currency": "USD"},
        ])
        for module in (orchestrator.validation, orchestrator.fraud_detection, orchestrator.compliance,
                       orchestrator.settlement, orchestrator.reporting):
            monkeypatch.setattr(module, "run_stage",
                                lambda *a, **k: {"processed": 0, "passed": 0, "failed": 0})

        orchestrator.run(source, tmp_path / "shared")

        assert offline_rates[0] == ["USD"]

    def test_status_json_has_every_stage_after_run(self, tmp_path, dataset, offline_rates, monkeypatch):
        for module in (orchestrator.validation, orchestrator.fraud_detection, orchestrator.compliance,
                       orchestrator.settlement, orchestrator.reporting):
            monkeypatch.setattr(module, "run_stage",
                                lambda *a, **k: {"processed": 3, "passed": 2, "failed": 1})
        shared = tmp_path / "shared"

        orchestrator.run(dataset, shared)

        status = read_json(shared / "status.json")
        assert set(status["stages"]) == set(orchestrator.STAGE_ORDER)
        assert status["run_completed_at"]
        for stage in orchestrator.STAGE_ORDER:
            assert status["stages"][stage]["processed"] == 3

    def test_input_dir_cleared_after_successful_run(self, tmp_path, dataset, offline_rates, monkeypatch):
        for module in (orchestrator.validation, orchestrator.fraud_detection, orchestrator.compliance,
                       orchestrator.settlement, orchestrator.reporting):
            monkeypatch.setattr(module, "run_stage",
                                lambda *a, **k: {"processed": 0, "passed": 0, "failed": 0})
        shared = tmp_path / "shared"

        orchestrator.run(dataset, shared)

        assert (shared / "input").is_dir()
        assert list((shared / "input").glob("*.json")) == []

    def test_exchange_rate_failure_exits_with_code_1(self, tmp_path, dataset, monkeypatch, capsys):
        def failing_fetch(currencies):
            raise ExchangeRateError("source unreachable after 3 attempts")

        monkeypatch.setattr(orchestrator, "fetch_exchange_rates", failing_fetch)

        with pytest.raises(SystemExit) as exc_info:
            orchestrator.run(dataset, tmp_path / "shared")

        assert exc_info.value.code == 1
        assert "source unreachable" in capsys.readouterr().err

    def test_missing_input_dataset_propagates(self, tmp_path, offline_rates):
        with pytest.raises(FileNotFoundError):
            orchestrator.run(tmp_path / "does-not-exist.json", tmp_path / "shared")

    def test_run_recreates_shared_tree_from_scratch(self, tmp_path, dataset, offline_rates, monkeypatch):
        """A stale result from a previous run must not survive into the new one."""
        shared = tmp_path / "shared"
        (shared / "results").mkdir(parents=True)
        (shared / "results" / "STALE.json").write_text("{}", encoding="utf-8")
        for module in (orchestrator.validation, orchestrator.fraud_detection, orchestrator.compliance,
                       orchestrator.settlement, orchestrator.reporting):
            monkeypatch.setattr(module, "run_stage",
                                lambda *a, **k: {"processed": 0, "passed": 0, "failed": 0})

        orchestrator.run(dataset, shared)

        assert not (shared / "results" / "STALE.json").exists()


# ---------------------------------------------------------------------------
# CLI entry point
# ---------------------------------------------------------------------------


class TestMain:
    def test_main_passes_cli_args_to_run(self, tmp_path, monkeypatch):
        seen = {}

        def fake_run(input_source, shared_dir):
            seen["input"] = input_source
            seen["shared"] = shared_dir

        monkeypatch.setattr(orchestrator, "run", fake_run)
        monkeypatch.setattr("sys.argv", [
            "orchestrator.py", "--input", "custom.json", "--shared-dir", str(tmp_path / "sh"),
        ])

        orchestrator.main()

        assert seen["input"] == Path("custom.json")
        assert seen["shared"] == tmp_path / "sh"

    def test_main_uses_defaults(self, monkeypatch):
        seen = {}

        monkeypatch.setattr(orchestrator, "run",
                            lambda input_source, shared_dir: seen.update(
                                input=input_source, shared=shared_dir))
        monkeypatch.setattr("sys.argv", ["orchestrator.py"])

        orchestrator.main()

        assert seen["input"] == Path(orchestrator.DEFAULT_INPUT)
        assert seen["shared"] == Path("shared")

    def test_stage_order_constant(self):
        assert orchestrator.STAGE_ORDER == (
            "validation", "fraud_detection", "compliance", "settlement", "reporting",
        )
