"""Unit tests for lib/stage_runner.py, lib/message_io.py and lib/dataset.py -
the shared file-lifecycle machinery every stage's CLI and the orchestrator
reuse."""
from __future__ import annotations

import json

import pytest

from lib.dataset import load_transactions
from lib.message_io import build_envelope, clear_directory, context_from_envelope_data, now_iso, read_json, write_json
from lib.models import FraudResult, StageContext, ValidationResult
from lib.stage_runner import run_downstream_stage, run_first_stage


# ---------------------------------------------------------------------------
# lib.message_io
# ---------------------------------------------------------------------------


def test_write_json_then_read_json_round_trips(tmp_path):
    path = tmp_path / "sub" / "a.json"
    write_json(path, {"hello": "world"})
    assert read_json(path) == {"hello": "world"}


def test_write_json_creates_parent_directories(tmp_path):
    path = tmp_path / "does" / "not" / "exist" / "a.json"
    write_json(path, {"x": 1})
    assert path.exists()


def test_build_envelope_shape():
    envelope = build_envelope("validation", "fraud_detection", {"transaction_id": "T1"})
    assert envelope["source_stage"] == "validation"
    assert envelope["target_stage"] == "fraud_detection"
    assert envelope["message_type"] == "transaction"
    assert envelope["data"] == {"transaction_id": "T1"}
    assert "message_id" in envelope
    assert "timestamp" in envelope


def test_context_from_envelope_data_builds_stage_context():
    data = {"validation_result": {"passed": True, "reason": None, "errors": []}}
    context = context_from_envelope_data(data)
    assert isinstance(context, StageContext)
    assert context.validation_result.passed is True
    assert context.fraud_result is None


def test_clear_directory_removes_only_files(tmp_path):
    d = tmp_path / "d"
    d.mkdir()
    (d / "a.json").write_text("{}")
    (d / "b.json").write_text("{}")
    sub = d / "keep_me"
    sub.mkdir()
    clear_directory(d)
    assert list(d.glob("*.json")) == []
    assert sub.exists()


def test_now_iso_returns_parseable_timestamp():
    from datetime import datetime

    value = now_iso()
    datetime.fromisoformat(value)


# ---------------------------------------------------------------------------
# lib.dataset
# ---------------------------------------------------------------------------


def test_load_transactions_from_json_array_file(tmp_path, valid_transactions):
    path = tmp_path / "dataset.json"
    path.write_text(json.dumps(valid_transactions))
    loaded = load_transactions(str(path))
    assert loaded == valid_transactions


def test_load_transactions_from_single_object_file(tmp_path, sample_transaction):
    path = tmp_path / "one.json"
    path.write_text(json.dumps(sample_transaction))
    loaded = load_transactions(str(path))
    assert loaded == [sample_transaction]


def test_load_transactions_from_directory(tmp_path, valid_transactions):
    d = tmp_path / "records"
    d.mkdir()
    for txn in valid_transactions:
        (d / f"{txn['transaction_id']}.json").write_text(json.dumps(txn))
    loaded = load_transactions(str(d))
    assert len(loaded) == len(valid_transactions)
    assert {r["transaction_id"] for r in loaded} == {t["transaction_id"] for t in valid_transactions}


def test_load_transactions_missing_source_raises_file_not_found(tmp_path):
    with pytest.raises(FileNotFoundError):
        load_transactions(str(tmp_path / "nope.json"))


def test_load_transactions_never_mutates_source(tmp_path, valid_transactions):
    path = tmp_path / "dataset.json"
    original = json.dumps(valid_transactions)
    path.write_text(original)
    load_transactions(str(path))
    assert path.read_text() == original


# ---------------------------------------------------------------------------
# lib.stage_runner.run_first_stage (Validation-shaped)
# ---------------------------------------------------------------------------


def _validation_compute(record, context):
    return ValidationResult(passed=True, reason=None, errors=[])


def test_run_first_stage_stages_and_processes_every_record(stage_dirs, put_input, valid_transactions):
    for txn in valid_transactions:
        put_input(txn)

    tally = run_first_stage(
        stage_name="validation",
        next_stage="fraud_detection",
        result_key="validation_result",
        compute_fn=_validation_compute,
        raw_input_dir=stage_dirs["input"],
        processing_dir=stage_dirs["processing"],
        output_dir=stage_dirs["output"],
        is_pass=lambda r: r.passed,
    )

    assert tally["processed"] == len(valid_transactions)
    assert tally["passed"] == len(valid_transactions)
    assert tally["failed"] == 0

    output_files = sorted(stage_dirs["output"].glob("*.json"))
    assert len(output_files) == len(valid_transactions)

    envelope = read_json(output_files[0])
    assert envelope["source_stage"] == "validation"
    assert envelope["target_stage"] == "fraud_detection"
    assert "validation_result" in envelope["data"]


def test_run_first_stage_never_modifies_raw_input_dir(stage_dirs, put_input, sample_transaction):
    put_input(sample_transaction)
    before = sorted(p.name for p in stage_dirs["input"].glob("*.json"))

    run_first_stage(
        stage_name="validation",
        next_stage="fraud_detection",
        result_key="validation_result",
        compute_fn=_validation_compute,
        raw_input_dir=stage_dirs["input"],
        processing_dir=stage_dirs["processing"],
        output_dir=stage_dirs["output"],
        is_pass=lambda r: r.passed,
    )

    after = sorted(p.name for p in stage_dirs["input"].glob("*.json"))
    assert before == after


def test_run_first_stage_empty_input_dir_processes_nothing(stage_dirs):
    tally = run_first_stage(
        stage_name="validation",
        next_stage="fraud_detection",
        result_key="validation_result",
        compute_fn=_validation_compute,
        raw_input_dir=stage_dirs["input"],
        processing_dir=stage_dirs["processing"],
        output_dir=stage_dirs["output"],
        is_pass=lambda r: r.passed,
    )
    assert tally == {"processed": 0, "passed": 0, "failed": 0}


def test_run_first_stage_tallies_failures(stage_dirs, put_input, sample_transaction):
    put_input(sample_transaction)

    tally = run_first_stage(
        stage_name="validation",
        next_stage="fraud_detection",
        result_key="validation_result",
        compute_fn=lambda record, context: ValidationResult(passed=False, reason="bad", errors=["bad"]),
        raw_input_dir=stage_dirs["input"],
        processing_dir=stage_dirs["processing"],
        output_dir=stage_dirs["output"],
        is_pass=lambda r: r.passed,
    )
    assert tally == {"processed": 1, "passed": 0, "failed": 1}


# ---------------------------------------------------------------------------
# lib.stage_runner.run_downstream_stage (Fraud/Compliance/Settlement-shaped)
# ---------------------------------------------------------------------------


def _fraud_compute(record, context):
    return FraudResult(score="0.10", flagged=False, factors={}, missing=[])


def test_run_downstream_stage_reads_original_and_accumulates_context(
    stage_dirs, put_input, put_envelope, sample_transaction
):
    put_input(sample_transaction)
    put_envelope(
        sample_transaction["transaction_id"],
        {
            "transaction_id": sample_transaction["transaction_id"],
            "amount": sample_transaction["amount"],
            "currency": sample_transaction["currency"],
            "validation_result": {"passed": True, "reason": None, "errors": []},
        },
    )

    tally = run_downstream_stage(
        stage_name="fraud_detection",
        next_stage="compliance",
        result_key="fraud_result",
        compute_fn=_fraud_compute,
        source_dir=stage_dirs["output"],
        processing_dir=stage_dirs["processing"],
        output_dir=stage_dirs["output"],
        input_dir=stage_dirs["input"],
        is_pass=lambda r: not r.flagged,
    )

    assert tally == {"processed": 1, "passed": 1, "failed": 0}
    output_files = list(stage_dirs["output"].glob("*.json"))
    assert len(output_files) == 1
    envelope = read_json(output_files[0])
    # Accumulated: both validation_result (carried forward) and the new
    # fraud_result are present.
    assert "validation_result" in envelope["data"]
    assert "fraud_result" in envelope["data"]
    assert envelope["source_stage"] == "fraud_detection"
    assert envelope["target_stage"] == "compliance"


def test_run_downstream_stage_passes_extra_kwargs(stage_dirs, put_input, put_envelope, sample_transaction, fake_rates):
    put_input(sample_transaction)
    put_envelope(
        sample_transaction["transaction_id"],
        {"transaction_id": sample_transaction["transaction_id"], "amount": sample_transaction["amount"], "currency": sample_transaction["currency"]},
    )

    seen_rates = {}

    def compute(record, context, rates=None):
        seen_rates["rates"] = rates
        return FraudResult(score="0.0", flagged=False, factors={}, missing=[])

    run_downstream_stage(
        stage_name="fraud_detection",
        next_stage="compliance",
        result_key="fraud_result",
        compute_fn=compute,
        source_dir=stage_dirs["output"],
        processing_dir=stage_dirs["processing"],
        output_dir=stage_dirs["output"],
        input_dir=stage_dirs["input"],
        is_pass=lambda r: True,
        extra_kwargs={"rates": fake_rates},
    )
    assert seen_rates["rates"] is fake_rates


def test_run_downstream_stage_empty_source_processes_nothing(stage_dirs):
    tally = run_downstream_stage(
        stage_name="fraud_detection",
        next_stage="compliance",
        result_key="fraud_result",
        compute_fn=_fraud_compute,
        source_dir=stage_dirs["output"],
        processing_dir=stage_dirs["processing"],
        output_dir=stage_dirs["output"],
        input_dir=stage_dirs["input"],
        is_pass=lambda r: True,
    )
    assert tally == {"processed": 0, "passed": 0, "failed": 0}
