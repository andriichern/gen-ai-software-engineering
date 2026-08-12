"""Unit tests for the API gateway under gateway/.

Exercised exclusively through FastAPI's in-process TestClient - no real port
is ever bound and no server process is ever spawned. Outbound calls the
gateway makes to the stage services are mocked at httpx.Client.post, so
these tests never depend on any service actually running (proving the
gateway is testable, and its retry/skip behaviour observable, in isolation).
"""
from __future__ import annotations

import json
from pathlib import Path

import httpx
import pytest
from fastapi.testclient import TestClient

import gateway.main as gateway_module

PROJECT_ROOT = Path(__file__).resolve().parent.parent


def _stage_result(stage: str) -> dict:
    """A minimal, valid result payload for a given stage."""
    if stage == "validation":
        return {"passed": True, "reason": None, "errors": []}
    if stage == "fraud_detection":
        return {"score": "0.10", "flagged": False, "factors": {}, "missing": []}
    if stage == "compliance":
        return {"status": "passed", "reason": None, "rule_outcomes": {}}
    if stage == "settlement":
        return {
            "status": "settled",
            "settlement_reference": "ref-1",
            "settlement_timestamp": "2026-03-16T10:00:00+00:00",
            "reason": "ok",
        }
    if stage == "reporting":
        return {
            "transaction_id": "TEST",
            "verdict": "SETTLED",
            "fraud_flagged": False,
            "reason": None,
            "stage_outcomes": {},
        }
    raise ValueError(stage)


def _stage_name_for_url(config: dict, url: str, path: str) -> str:
    for stage, service in config["services"].items():
        if service["url"] == url and service["path"] == path:
            return stage
    reporting = config["reporting"]
    if reporting["url"] == url and reporting["path"] == path:
        return "reporting"
    raise ValueError(f"unrecognized stage endpoint: {url}{path}")


class _FakeResponse:
    def __init__(self, json_body: dict, status_code: int = 200):
        self._json = json_body
        self.status_code = status_code

    def raise_for_status(self):
        if self.status_code >= 400:
            request = httpx.Request("POST", "http://fake")
            raise httpx.HTTPStatusError("error", request=request, response=httpx.Response(self.status_code, request=request))

    def json(self):
        return self._json


@pytest.fixture(autouse=True)
def _no_real_sleep(monkeypatch):
    """Retries in gateway.main sleep 0.1s between attempts; skip the wait so
    the retry-then-skip tests run instantly."""
    monkeypatch.setattr(gateway_module.time, "sleep", lambda *_a, **_kw: None)


@pytest.fixture
def sample_transaction():
    return {
        "transaction_id": "TXN-GW-1",
        "timestamp": "2026-03-16T10:00:00Z",
        "source_account": "ACC-1",
        "destination_account": "ACC-2",
        "amount": "1000.00",
        "currency": "USD",
        "transaction_type": "transfer",
        "description": "",
        "metadata": {"channel": "online", "country": "US"},
    }


_ORIGINAL_CLIENT_POST = httpx.Client.post


def _install_happy_mock(monkeypatch, config, call_log=None):
    """All stage services (and reporting) succeed on the first attempt.

    Only outbound calls to a known stage/reporting endpoint are intercepted;
    every other httpx.Client.post call (in particular, the TestClient's own
    in-process request to POST /process) is passed through unchanged.
    """

    def fake_post(self, url_path, *, json=None, timeout=None, **kwargs):  # noqa: A002
        stage = None
        for name, service in {**config["services"], "reporting": config["reporting"]}.items():
            endpoint = f"{service['url']}{service['path']}"
            if url_path == endpoint:
                stage = name
                break
        if stage is None:
            return _ORIGINAL_CLIENT_POST(self, url_path, json=json, timeout=timeout, **kwargs)
        if call_log is not None:
            call_log.append(stage)
        result = _stage_result(stage)
        if stage == "reporting":
            result = dict(result)
            result["transaction_id"] = json["transaction"]["transaction_id"]
        return _FakeResponse({"stage": stage, "result": result})

    monkeypatch.setattr(httpx.Client, "post", fake_post)


# ---------------------------------------------------------------------------
# Config parsing
# ---------------------------------------------------------------------------


def test_valid_config_yields_expected_order():
    config = gateway_module.load_config()
    assert config["order"] == ["validation", "fraud_detection", "compliance", "settlement"]
    assert "reporting" in config
    assert set(config["services"]) == set(config["order"])


def test_load_config_reads_the_real_config_file():
    config = gateway_module.load_config()
    on_disk = json.loads(gateway_module.CONFIG_PATH.read_text())
    assert config == on_disk


def test_config_with_unknown_stage_name_is_rejected_clearly(monkeypatch, sample_transaction):
    """An order entry with no matching entry under "services" must fail
    loudly (a clear server error) rather than being silently accepted or
    fabricating a result for it."""
    bad_config = {
        "order": ["validation", "not_a_real_stage"],
        "services": {
            "validation": {"url": "http://127.0.0.1:8001", "path": "/validate"},
        },
        "reporting": {"url": "http://127.0.0.1:8005", "path": "/report"},
    }
    monkeypatch.setattr(gateway_module, "CONFIG", bad_config)
    _install_happy_mock(monkeypatch, {**bad_config, "services": {**bad_config["services"]}})

    client = TestClient(gateway_module.app, raise_server_exceptions=False)
    response = client.post("/process", json=sample_transaction)
    # Unknown stage -> KeyError inside process() -> a clean 500, not a
    # fabricated 200 with an invented result for "not_a_real_stage".
    assert response.status_code == 500


# ---------------------------------------------------------------------------
# Order is honored; Reporting is always called last regardless of config
# ---------------------------------------------------------------------------


def test_order_is_honored_and_reporting_called_last(monkeypatch, sample_transaction):
    config = gateway_module.load_config()
    monkeypatch.setattr(gateway_module, "CONFIG", config)
    call_log: list[str] = []
    _install_happy_mock(monkeypatch, config, call_log)

    client = TestClient(gateway_module.app)
    response = client.post("/process", json=sample_transaction)

    assert response.status_code == 200
    assert call_log[:4] == config["order"]
    assert call_log[-1] == "reporting"


def test_reversed_order_is_honored_and_reporting_still_last(monkeypatch, sample_transaction):
    config = gateway_module.load_config()
    reversed_config = {
        "order": list(reversed(config["order"])),
        "services": config["services"],
        "reporting": config["reporting"],
    }
    monkeypatch.setattr(gateway_module, "CONFIG", reversed_config)
    call_log: list[str] = []
    _install_happy_mock(monkeypatch, reversed_config, call_log)

    client = TestClient(gateway_module.app)
    response = client.post("/process", json=sample_transaction)

    assert response.status_code == 200
    assert call_log[:4] == reversed_config["order"]
    assert call_log[-1] == "reporting"


def test_two_different_orders_both_produce_complete_results(monkeypatch, sample_transaction):
    config = gateway_module.load_config()
    orders = [
        config["order"],
        ["compliance", "settlement", "fraud_detection", "validation"],
    ]
    result_key_by_stage = gateway_module.RESULT_KEY_BY_STAGE

    for order in orders:
        variant_config = {"order": order, "services": config["services"], "reporting": config["reporting"]}
        monkeypatch.setattr(gateway_module, "CONFIG", variant_config)
        _install_happy_mock(monkeypatch, variant_config)

        client = TestClient(gateway_module.app)
        response = client.post("/process", json=sample_transaction)
        assert response.status_code == 200
        body = response.json()

        assert not body["stages_not_run"]
        for stage in order:
            assert result_key_by_stage[stage] in body["context"]
        assert body["report"] is not None


# ---------------------------------------------------------------------------
# Retry-then-skip against a mocked dead service
# ---------------------------------------------------------------------------


def test_retry_then_skip_dead_service_yields_incomplete_and_continues_chain(monkeypatch, sample_transaction):
    config = gateway_module.load_config()
    monkeypatch.setattr(gateway_module, "CONFIG", config)

    dead_stage = "fraud_detection"
    attempts_for_dead_stage = {"count": 0}
    call_log: list[str] = []

    def fake_post(self, url_path, *, json=None, timeout=None, **_kwargs):
        dead_endpoint = f"{config['services'][dead_stage]['url']}{config['services'][dead_stage]['path']}"
        if url_path == dead_endpoint:
            attempts_for_dead_stage["count"] += 1
            raise httpx.ConnectError("connection refused", request=httpx.Request("POST", url_path))

        stage = None
        for name, service in {**config["services"], "reporting": config["reporting"]}.items():
            endpoint = f"{service['url']}{service['path']}"
            if url_path == endpoint:
                stage = name
                break
        if stage is None:
            return _ORIGINAL_CLIENT_POST(self, url_path, json=json, timeout=timeout, **_kwargs)
        call_log.append(stage)
        result = _stage_result(stage)
        if stage == "reporting":
            result = dict(result)
            result["transaction_id"] = json["transaction"]["transaction_id"]
        return _FakeResponse({"stage": stage, "result": result})

    monkeypatch.setattr(httpx.Client, "post", fake_post)

    client = TestClient(gateway_module.app)
    response = client.post("/process", json=sample_transaction)

    # The whole request does not fail over one dead stage.
    assert response.status_code == 200
    body = response.json()

    assert attempts_for_dead_stage["count"] == gateway_module.RETRY_ATTEMPTS == 3
    assert body["stages_not_run"] == [dead_stage]
    # No result was fabricated for the skipped stage.
    assert gateway_module.RESULT_KEY_BY_STAGE[dead_stage] not in body["context"]
    # The chain continued: the other 3 reorderable stages and reporting ran.
    assert set(call_log) == {"validation", "compliance", "settlement", "reporting"}
    assert call_log[-1] == "reporting"

    # Reporting is only told about the stages that actually ran (fraud_result
    # absent), so the transaction's own verdict computation will read
    # INCOMPLETE from build_report given a missing annotation - here we
    # assert the gateway did not invent a value for it.
    assert "fraud_result" not in body["context"]


# ---------------------------------------------------------------------------
# End-to-end submission
# ---------------------------------------------------------------------------


def test_end_to_end_submission_returns_accumulated_results_and_verdict(monkeypatch, sample_transaction):
    config = gateway_module.load_config()
    monkeypatch.setattr(gateway_module, "CONFIG", config)
    _install_happy_mock(monkeypatch, config)

    client = TestClient(gateway_module.app)
    response = client.post("/process", json=sample_transaction)

    assert response.status_code == 200
    body = response.json()
    assert body["transaction_id"] == sample_transaction["transaction_id"]
    assert set(body["context"]) == {
        "validation_result",
        "fraud_result",
        "compliance_result",
        "settlement_result",
    }
    assert body["report"]["transaction_id"] == sample_transaction["transaction_id"]
    assert body["report"]["verdict"] == "SETTLED"
    assert body["stages_not_run"] == []


# ---------------------------------------------------------------------------
# Statelessness: nothing written into shared/, nothing read from it.
# ---------------------------------------------------------------------------


def _snapshot(root: Path) -> dict:
    if not root.exists():
        return {}
    return {str(p): p.stat().st_mtime_ns for p in root.rglob("*") if p.is_file()}


def test_gateway_is_stateless_wrt_shared(monkeypatch, sample_transaction):
    config = gateway_module.load_config()
    monkeypatch.setattr(gateway_module, "CONFIG", config)
    _install_happy_mock(monkeypatch, config)

    shared_dir = PROJECT_ROOT / "shared"
    before = _snapshot(shared_dir)

    client = TestClient(gateway_module.app)
    client.post("/process", json=sample_transaction)

    after = _snapshot(shared_dir)
    assert before == after, "gateway touched the project's shared/ directory"


def test_gateway_module_never_reads_shared_directory():
    """The gateway's docstring documents its statelessness in prose ("writes
    nothing into shared/"); what matters is that no code in the module opens
    a path under shared/. Check for actual filesystem access patterns
    instead of the word itself."""
    source = Path(gateway_module.__file__).read_text(encoding="utf-8")
    forbidden_patterns = ["Path(\"shared", "Path('shared", "open(\"shared", "open('shared"]
    for pattern in forbidden_patterns:
        assert pattern not in source


# ---------------------------------------------------------------------------
# Batch submission: POST /process/batch
#
# The batch endpoint differs from /process only in arity. Both go through the
# same _process_one(), so these tests exist to prove that stays true -- a
# batch must never diverge from repeated single submissions.
# ---------------------------------------------------------------------------


def _second_transaction(sample: dict) -> dict:
    other = dict(sample)
    other["transaction_id"] = "TXN-GW-2"
    other["amount"] = "2000.00"
    return other


def test_batch_returns_an_array_of_the_same_shape(monkeypatch, sample_transaction):
    config = gateway_module.load_config()
    monkeypatch.setattr(gateway_module, "CONFIG", config)
    _install_happy_mock(monkeypatch, config)

    client = TestClient(gateway_module.app)
    single = client.post("/process", json=sample_transaction).json()
    batch = client.post("/process/batch", json=[sample_transaction]).json()

    assert isinstance(single, dict), "the single endpoint must return an object"
    assert isinstance(batch, list), "the batch endpoint must return an array"
    assert len(batch) == 1
    assert set(batch[0]) == set(single), "batch elements must have the single response's shape"


def test_batch_preserves_submission_order(monkeypatch, sample_transaction):
    config = gateway_module.load_config()
    monkeypatch.setattr(gateway_module, "CONFIG", config)
    _install_happy_mock(monkeypatch, config)

    second = _second_transaction(sample_transaction)
    client = TestClient(gateway_module.app)
    body = client.post("/process/batch", json=[sample_transaction, second]).json()

    assert [item["transaction_id"] for item in body] == ["TXN-GW-1", "TXN-GW-2"]


def test_batch_result_matches_single_submission(monkeypatch, sample_transaction):
    """A transaction submitted inside a batch must produce the same outcome as
    submitting it alone. Compared on deterministic fields only: settlement
    generates a fresh reference and timestamp on every call, so whole-object
    equality would fail for reasons that say nothing about batching."""
    config = gateway_module.load_config()
    monkeypatch.setattr(gateway_module, "CONFIG", config)
    _install_happy_mock(monkeypatch, config)

    client = TestClient(gateway_module.app)
    single = client.post("/process", json=sample_transaction).json()
    batched = client.post("/process/batch", json=[sample_transaction]).json()[0]

    assert batched["transaction_id"] == single["transaction_id"]
    assert batched["stages_not_run"] == single["stages_not_run"]
    assert batched["report"]["verdict"] == single["report"]["verdict"]
    assert batched["report"]["fraud_flagged"] == single["report"]["fraud_flagged"]
    assert sorted(batched["context"]) == sorted(single["context"])


def test_batch_response_carries_no_aggregate_summary(monkeypatch, sample_transaction):
    """Reporting is called once per transaction, so the gateway returns
    per-transaction verdicts and nothing else -- no run-level counts."""
    config = gateway_module.load_config()
    monkeypatch.setattr(gateway_module, "CONFIG", config)
    _install_happy_mock(monkeypatch, config)

    client = TestClient(gateway_module.app)
    body = client.post("/process/batch", json=[sample_transaction, _second_transaction(sample_transaction)]).json()

    assert isinstance(body, list), "an aggregate would require an envelope; the response is a bare array"
    for item in body:
        assert not {"summary", "total", "settled", "held", "rejected", "incomplete"} & set(item)


def test_batch_transactions_are_independent(monkeypatch, sample_transaction):
    """One transaction losing a stage must not affect the others in its batch."""
    config = gateway_module.load_config()
    monkeypatch.setattr(gateway_module, "CONFIG", config)

    def fake_post(self, url_path, *, json=None, timeout=None, **kwargs):  # noqa: A002
        for name, service in {**config["services"], "reporting": config["reporting"]}.items():
            if url_path == f"{service['url']}{service['path']}":
                # Settlement is unreachable for the second transaction only.
                if name == "settlement" and json["transaction"]["transaction_id"] == "TXN-GW-2":
                    raise httpx.ConnectError("service down")
                result = _stage_result(name)
                if name == "reporting":
                    result = dict(result)
                    result["transaction_id"] = json["transaction"]["transaction_id"]
                return _FakeResponse({"stage": name, "result": result})
        return _ORIGINAL_CLIENT_POST(self, url_path, json=json, timeout=timeout, **kwargs)

    monkeypatch.setattr(httpx.Client, "post", fake_post)

    client = TestClient(gateway_module.app)
    body = client.post("/process/batch", json=[sample_transaction, _second_transaction(sample_transaction)]).json()

    assert body[0]["stages_not_run"] == []
    assert body[1]["stages_not_run"] == ["settlement"]


def test_empty_batch_returns_empty_array(monkeypatch):
    config = gateway_module.load_config()
    monkeypatch.setattr(gateway_module, "CONFIG", config)

    client = TestClient(gateway_module.app)
    response = client.post("/process/batch", json=[])

    assert response.status_code == 200
    assert response.json() == []


def test_batch_with_an_invalid_record_is_rejected_cleanly(monkeypatch, sample_transaction):
    """A malformed element fails validation of the request body itself -- a
    422, never a crash and never a partially-processed batch."""
    config = gateway_module.load_config()
    monkeypatch.setattr(gateway_module, "CONFIG", config)
    _install_happy_mock(monkeypatch, config)

    client = TestClient(gateway_module.app)
    response = client.post("/process/batch", json=[sample_transaction, {"transaction_id": "missing-fields"}])

    assert response.status_code == 422
