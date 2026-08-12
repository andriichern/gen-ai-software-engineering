"""Tests for the command-line entry points of every stage, the orchestrator,
and the small predicate helpers beside them.

Each stage is independently runnable via its own `main()`, and the
orchestrator has one of its own. Those functions parse arguments and wire up
the same core logic the rest of the suite exercises directly -- so they are
tested here by patching `sys.argv` and pointing every path at a temporary
directory. Nothing writes into the project's real `shared/` tree.
"""
from __future__ import annotations

import json
from pathlib import Path

import pytest

import orchestrator as orchestrator_module
from lib.exchange_rates import ExchangeRates
from lib.models import ComplianceResult, FraudResult, SettlementResult, ValidationResult
from pipeline import compliance, fraud_detection, reporting, settlement, validation


# ---------------------------------------------------------------------------
# _is_pass predicates
#
# Each stage hands one of these to the shared runner to classify a result as
# passed or failed for the run tally. They encode a real rule: fraud "fails"
# on a flag, compliance only "passes" when cleared, and so on.
# ---------------------------------------------------------------------------


def test_validation_is_pass_follows_the_passed_flag():
    assert validation._is_pass(ValidationResult(passed=True, reason=None, errors=[])) is True
    assert validation._is_pass(ValidationResult(passed=False, reason="bad", errors=["bad"])) is False


def test_fraud_is_pass_is_the_inverse_of_flagged():
    """A flagged transaction counts as failed for the tally -- but flagging is
    never a rejection, which is asserted in the fraud stage's own tests."""
    flagged = FraudResult(score="0.90", flagged=True, factors={}, missing=[])
    clean = FraudResult(score="0.10", flagged=False, factors={}, missing=[])
    assert fraud_detection._is_pass(flagged) is False
    assert fraud_detection._is_pass(clean) is True


@pytest.mark.parametrize(
    "status, expected",
    [("passed", True), ("held", False), ("rejected", False)],
)
def test_compliance_is_pass_only_for_cleared(status, expected):
    result = ComplianceResult(status=status, reason=None, rule_outcomes={})
    assert compliance._is_pass(result) is expected


@pytest.mark.parametrize(
    "status, expected",
    [("settled", True), ("not_settled", False)],
)
def test_settlement_is_pass_only_when_settled(status, expected):
    result = SettlementResult(
        status=status,
        settlement_reference=None,
        settlement_timestamp=None,
        reason=None,
    )
    assert settlement._is_pass(result) is expected


# ---------------------------------------------------------------------------
# Validation's type-guard branches
#
# Both helpers are reached with non-string and wrong-length input from real
# malformed records, so the guards are behaviour rather than defensive noise.
# ---------------------------------------------------------------------------


@pytest.mark.parametrize("code", [None, 123, ["USD"], "US", "USDD", ""])
def test_iso4217_rejects_non_three_letter_strings(code):
    assert validation._is_valid_iso4217(code) is False


def test_iso4217_accepts_a_real_code_case_insensitively():
    assert validation._is_valid_iso4217("usd") is True


@pytest.mark.parametrize("value", [None, 42, {"t": 1}])
def test_iso8601_rejects_non_strings(value):
    assert validation._is_valid_iso8601_utc(value) is False


# ---------------------------------------------------------------------------
# Stage CLI entry points
# ---------------------------------------------------------------------------


@pytest.fixture
def cli_tree(tmp_path, sample_transaction):
    """A temporary shared/ tree with one raw record in input/, isolated from
    the project's own shared/ directory."""
    shared = tmp_path / "shared"
    for name in ("input", "processing", "output", "results"):
        (shared / name).mkdir(parents=True)
    record = dict(sample_transaction)
    (shared / "input" / f"{record['transaction_id']}.json").write_text(json.dumps(record))
    return shared


def _run_cli(monkeypatch, main_fn, argv: list[str]) -> None:
    monkeypatch.setattr("sys.argv", argv)
    main_fn()


def test_validation_main_annotates_every_record(monkeypatch, capsys, cli_tree):
    _run_cli(
        monkeypatch,
        validation.main,
        ["validation", "--input-dir", str(cli_tree / "input"), "--output-dir", str(cli_tree / "output")],
    )

    written = list((cli_tree / "output").glob("*.json"))
    assert len(written) == 1, "every record continues to output/, passing or failing"
    assert "[validation] done:" in capsys.readouterr().out


def test_validation_main_check_mode_writes_nothing(monkeypatch, capsys, tmp_path, sample_transaction):
    """--check is the standalone, read-only mode: it prints a JSON report and
    must leave the filesystem byte-identical."""
    dataset = tmp_path / "dataset.json"
    dataset.write_text(json.dumps([sample_transaction]))
    before = {p: p.stat().st_mtime_ns for p in tmp_path.rglob("*") if p.is_file()}

    _run_cli(monkeypatch, validation.main, ["validation", "--check", "--source", str(dataset)])

    report = json.loads(capsys.readouterr().out)
    assert report["total"] == 1
    assert report["valid"] + report["invalid"] == report["total"]
    assert len(report["results"]) == 1
    after = {p: p.stat().st_mtime_ns for p in tmp_path.rglob("*") if p.is_file()}
    assert before == after, "--check must write nothing at all"


def _seed_output_message(shared: Path, transaction_id: str, context: dict) -> None:
    """Write a lean inter-stage message into output/, as an upstream stage
    would leave it for the next one."""
    (shared / "output" / f"{transaction_id}.json").write_text(
        json.dumps(
            {
                "message_id": "11111111-1111-1111-1111-111111111111",
                "timestamp": "2026-03-16T10:00:00+00:00",
                "source_stage": "upstream",
                "target_stage": "next",
                "message_type": "transaction",
                "data": {"transaction_id": transaction_id, "amount": "1000.00", "currency": "USD", **context},
            }
        )
    )


def test_fraud_detection_main_annotates_from_output_dir(monkeypatch, capsys, cli_tree, sample_transaction):
    transaction_id = sample_transaction["transaction_id"]
    _seed_output_message(cli_tree, transaction_id, {"validation_result": {"passed": True, "reason": None, "errors": []}})
    # The stage fetches live rates in its CLI path; pin them so the test never
    # depends on network access.
    monkeypatch.setattr(
        fraud_detection, "fetch_exchange_rates", lambda *a, **kw: ExchangeRates(base="USD", rates={"USD": 1})
    )

    _run_cli(
        monkeypatch,
        fraud_detection.main,
        [
            "fraud_detection",
            "--input-dir", str(cli_tree / "output"),
            "--output-dir", str(cli_tree / "output"),
            "--original-dir", str(cli_tree / "input"),
        ],
    )

    message = json.loads((cli_tree / "output" / f"{transaction_id}.json").read_text())
    assert "fraud_result" in message["data"]
    assert "[fraud_detection] done:" in capsys.readouterr().out


def test_compliance_main_annotates_from_output_dir(monkeypatch, capsys, cli_tree, sample_transaction):
    transaction_id = sample_transaction["transaction_id"]
    _seed_output_message(cli_tree, transaction_id, {"validation_result": {"passed": True, "reason": None, "errors": []}})

    _run_cli(
        monkeypatch,
        compliance.main,
        [
            "compliance",
            "--input-dir", str(cli_tree / "output"),
            "--output-dir", str(cli_tree / "output"),
            "--original-dir", str(cli_tree / "input"),
        ],
    )

    message = json.loads((cli_tree / "output" / f"{transaction_id}.json").read_text())
    assert "compliance_result" in message["data"]
    assert "[compliance] done:" in capsys.readouterr().out


def test_settlement_main_annotates_from_output_dir(monkeypatch, capsys, cli_tree, sample_transaction):
    transaction_id = sample_transaction["transaction_id"]
    _seed_output_message(
        cli_tree,
        transaction_id,
        {"compliance_result": {"status": "passed", "reason": None, "rule_outcomes": {}}},
    )

    _run_cli(
        monkeypatch,
        settlement.main,
        [
            "settlement",
            "--input-dir", str(cli_tree / "output"),
            "--output-dir", str(cli_tree / "output"),
            "--original-dir", str(cli_tree / "input"),
        ],
    )

    message = json.loads((cli_tree / "output" / f"{transaction_id}.json").read_text())
    assert "settlement_result" in message["data"]
    assert "[settlement] done:" in capsys.readouterr().out


def test_reporting_main_writes_results_and_report(monkeypatch, capsys, cli_tree, sample_transaction):
    transaction_id = sample_transaction["transaction_id"]
    _seed_output_message(cli_tree, transaction_id, {"validation_result": {"passed": True, "reason": None, "errors": []}})
    report_path = cli_tree / "report.json"

    _run_cli(
        monkeypatch,
        reporting.main,
        [
            "reporting",
            "--input-dir", str(cli_tree / "output"),
            "--original-dir", str(cli_tree / "input"),
            "--results-dir", str(cli_tree / "results"),
            "--report-path", str(report_path),
        ],
    )

    assert (cli_tree / "results" / f"{transaction_id}.json").exists()
    assert report_path.exists()
    # Only validation ran, so the verdict is INCOMPLETE -- a missing stage
    # outranks every other condition in the precedence table.
    final = json.loads((cli_tree / "results" / f"{transaction_id}.json").read_text())
    assert final["verdict"] == "INCOMPLETE"
    assert "[reporting] done:" in capsys.readouterr().out


# ---------------------------------------------------------------------------
# Orchestrator CLI
# ---------------------------------------------------------------------------


def test_orchestrator_main_passes_source_through(monkeypatch):
    captured: list[str] = []
    monkeypatch.setattr(orchestrator_module, "run_pipeline", lambda source: captured.append(source))

    _run_cli(monkeypatch, orchestrator_module.main, ["orchestrator", "--source", "my-dataset.json"])

    assert captured == ["my-dataset.json"]


def test_orchestrator_main_defaults_to_the_sample_dataset(monkeypatch):
    captured: list[str] = []
    monkeypatch.setattr(orchestrator_module, "run_pipeline", lambda source: captured.append(source))

    _run_cli(monkeypatch, orchestrator_module.main, ["orchestrator"])

    assert captured == ["sample-transactions.json"]
