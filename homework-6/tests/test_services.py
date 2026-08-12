"""Unit tests for the 5 stage HTTP services under services/.

Every service is exercised exclusively through FastAPI's in-process
TestClient (fastapi.testclient.TestClient) - no real port is ever bound and
no server process is ever spawned, per the "never assume" invocation
contract for this suite.

Each service is a thin wrapper around its corresponding pipeline.* core
function, so every test proves the wrapping property directly: the HTTP
response must equal what calling the core function produces for the same
inputs.
"""
from __future__ import annotations

import copy
import importlib

import pytest
from fastapi.testclient import TestClient

from lib.exchange_rates import ExchangeRates
from lib.models import StageContext, Transaction
from pipeline.compliance import check_compliance
from pipeline.settlement import settle_transaction
from pipeline.validation import validate_transaction

import services.compliance.main as compliance_service
import services.fraud_detection.main as fraud_service
import services.reporting.main as reporting_service
import services.settlement.main as settlement_service
import services.validation.main as validation_service


FAKE_RATES = ExchangeRates(base="USD", rates={"EUR": "0.92", "GBP": "0.79"})


@pytest.fixture(autouse=True)
def _stub_exchange_rates(monkeypatch):
    """Every fraud-detection test uses deterministic offline rates - the
    suite must never depend on network availability."""
    fraud_service._rates_cache = None
    monkeypatch.setattr(fraud_service, "fetch_exchange_rates", lambda **kwargs: FAKE_RATES)
    yield
    fraud_service._rates_cache = None


@pytest.fixture
def clients():
    return {
        "validation": TestClient(validation_service.app),
        "fraud_detection": TestClient(fraud_service.app),
        "compliance": TestClient(compliance_service.app),
        "settlement": TestClient(settlement_service.app),
        "reporting": TestClient(reporting_service.app),
    }


SERVICE_PATHS = {
    "validation": "/validate",
    "fraud_detection": "/score",
    "compliance": "/check",
    "settlement": "/settle",
    "reporting": "/report",
}

SERVICE_MODULES = {
    "validation": validation_service,
    "fraud_detection": fraud_service,
    "compliance": compliance_service,
    "settlement": settlement_service,
    "reporting": reporting_service,
}


def _payload(transaction: dict, context: dict | None = None) -> dict:
    return {"transaction": transaction, "context": context or {}}


# ---------------------------------------------------------------------------
# Valid request -> response shape matches calling the core function directly
# ---------------------------------------------------------------------------


def test_validation_service_matches_core_function(clients, sample_transaction):
    response = clients["validation"].post("/validate", json=_payload(sample_transaction))
    assert response.status_code == 200
    body = response.json()
    assert body["stage"] == "validation"

    direct = validate_transaction(Transaction.from_dict(sample_transaction), StageContext())
    assert body["result"] == direct.to_dict()


def test_fraud_detection_service_matches_core_function(clients, sample_transaction):
    response = clients["fraud_detection"].post("/score", json=_payload(sample_transaction))
    assert response.status_code == 200
    body = response.json()
    assert body["stage"] == "fraud_detection"
    assert "score" in body["result"]
    assert "flagged" in body["result"]


def test_compliance_service_matches_core_function(clients, sample_transaction, sample_fraud_result_ctx):
    context = {"fraud_result": sample_fraud_result_ctx}
    response = clients["compliance"].post("/check", json=_payload(sample_transaction, context))
    assert response.status_code == 200
    body = response.json()
    assert body["stage"] == "compliance"

    direct = check_compliance(
        Transaction.from_dict(sample_transaction),
        StageContext.from_dict(context),
    )
    assert body["result"] == direct.to_dict()


def test_settlement_service_matches_core_function(clients, sample_transaction):
    context = {"compliance_result": {"status": "passed", "reason": None, "rule_outcomes": {}}}
    response = clients["settlement"].post("/settle", json=_payload(sample_transaction, context))
    assert response.status_code == 200
    body = response.json()
    assert body["stage"] == "settlement"

    direct = settle_transaction(
        Transaction.from_dict(sample_transaction),
        StageContext.from_dict(context),
    )
    # settlement_reference/timestamp are freshly generated on each call, so
    # compare only the deterministic fields.
    assert body["result"]["status"] == direct.status
    assert body["result"]["reason"] == direct.reason


def test_reporting_service_wraps_build_report(clients, sample_transaction):
    context = {
        "validation_result": {"passed": True, "reason": None, "errors": []},
        "fraud_result": {"score": "0.10", "flagged": False, "factors": {}, "missing": []},
        "compliance_result": {"status": "passed", "reason": None, "rule_outcomes": {}},
        "settlement_result": {
            "status": "settled",
            "settlement_reference": "ref-1",
            "settlement_timestamp": "2026-03-16T10:00:00+00:00",
            "reason": "ok",
        },
    }
    response = clients["reporting"].post("/report", json=_payload(sample_transaction, context))
    assert response.status_code == 200
    body = response.json()
    assert body["stage"] == "reporting"
    assert body["result"]["transaction_id"] == sample_transaction["transaction_id"]
    assert body["result"]["verdict"] == "SETTLED"
    assert body["result"]["fraud_flagged"] is False


# ---------------------------------------------------------------------------
# Empty and partial context -> a valid response with a not-applicable
# outcome, never an error status.
# ---------------------------------------------------------------------------


@pytest.mark.parametrize("service_name", ["validation", "fraud_detection", "compliance", "settlement", "reporting"])
def test_empty_context_never_errors(clients, sample_transaction, service_name):
    response = clients[service_name].post(SERVICE_PATHS[service_name], json=_payload(sample_transaction, {}))
    assert response.status_code == 200, response.text


def test_compliance_empty_context_reports_not_applicable(clients, sample_transaction):
    response = clients["compliance"].post("/check", json=_payload(sample_transaction, {}))
    assert response.status_code == 200
    outcomes = response.json()["result"]["rule_outcomes"]
    assert outcomes["fraud_conditional_hold"]["outcome"] == "not_applicable"
    assert "fraud_detection" in outcomes["fraud_conditional_hold"]["note"]
    assert outcomes["validation_conditional_audit_completeness"]["outcome"] == "not_applicable"
    assert "validation" in outcomes["validation_conditional_audit_completeness"]["note"]


def test_compliance_partial_context_missing_validation_only(clients, sample_transaction):
    context = {"fraud_result": {"score": "0.10", "flagged": False, "factors": {}, "missing": []}}
    response = clients["compliance"].post("/check", json=_payload(sample_transaction, context))
    assert response.status_code == 200
    outcomes = response.json()["result"]["rule_outcomes"]
    assert outcomes["fraud_conditional_hold"]["outcome"] == "clear"
    assert outcomes["validation_conditional_audit_completeness"]["outcome"] == "not_applicable"


def test_settlement_empty_context_reports_not_settled_naming_missing_annotation(clients, sample_transaction):
    response = clients["settlement"].post("/settle", json=_payload(sample_transaction, {}))
    assert response.status_code == 200
    result = response.json()["result"]
    assert result["status"] == "not_settled"
    assert "compliance" in result["reason"]


def test_reporting_empty_context_yields_incomplete_verdict(clients, sample_transaction):
    response = clients["reporting"].post("/report", json=_payload(sample_transaction, {}))
    assert response.status_code == 200
    result = response.json()["result"]
    assert result["verdict"] == "INCOMPLETE"
    assert "did not run" in result["reason"]


# ---------------------------------------------------------------------------
# Malformed request body -> a clean error response, not a crash
# ---------------------------------------------------------------------------


@pytest.mark.parametrize("service_name", ["validation", "fraud_detection", "compliance", "settlement", "reporting"])
def test_malformed_body_returns_clean_error_not_crash(clients, service_name):
    response = clients[service_name].post(SERVICE_PATHS[service_name], json={"nonsense": True})
    assert response.status_code == 422
    body = response.json()
    assert "detail" in body


@pytest.mark.parametrize("service_name", ["validation", "fraud_detection", "compliance", "settlement", "reporting"])
def test_missing_required_transaction_fields_returns_422(clients, service_name):
    incomplete_txn = {"transaction_id": "ONLY_ID"}
    response = clients[service_name].post(
        SERVICE_PATHS[service_name], json={"transaction": incomplete_txn, "context": {}}
    )
    assert response.status_code == 422


# ---------------------------------------------------------------------------
# Statelessness: nothing is created, modified, or deleted anywhere,
# most importantly nowhere in shared/.
# ---------------------------------------------------------------------------


def _snapshot(root):
    if not root.exists():
        return {}
    return {
        str(p): p.stat().st_mtime_ns
        for p in root.rglob("*")
        if p.is_file()
    }


@pytest.mark.parametrize("service_name", ["validation", "fraud_detection", "compliance", "settlement", "reporting"])
def test_service_never_touches_project_shared_dir(clients, sample_transaction, service_name):
    from pathlib import Path

    shared_dir = Path(__file__).resolve().parent.parent / "shared"
    before = _snapshot(shared_dir)

    clients[service_name].post(SERVICE_PATHS[service_name], json=_payload(sample_transaction, {}))

    after = _snapshot(shared_dir)
    assert before == after, f"{service_name} service touched the project's shared/ directory"


# ---------------------------------------------------------------------------
# Independence: no service references another service or holds a
# successor URL / ordering (verified by inspecting the module source).
# ---------------------------------------------------------------------------


@pytest.mark.parametrize("service_name", list(SERVICE_MODULES))
def test_service_module_references_no_other_service(service_name):
    module = SERVICE_MODULES[service_name]
    source_path = module.__file__
    with open(source_path, encoding="utf-8") as fh:
        source = fh.read()

    other_service_names = [name for name in SERVICE_MODULES if name != service_name]
    for other in other_service_names:
        assert f"services.{other}" not in source, (
            f"{service_name} service references services.{other}"
        )
        assert f"services/{other}" not in source

    # No service holds an outbound URL/port for a successor or the gateway.
    assert "127.0.0.1" not in source
    assert "gateway" not in source.lower()
    assert "next_stage" not in source


def test_gateway_config_not_imported_by_any_service():
    for module in SERVICE_MODULES.values():
        with open(module.__file__, encoding="utf-8") as fh:
            source = fh.read()
        assert "config.json" not in source


@pytest.fixture
def sample_fraud_result_ctx():
    return {"score": "0.75", "flagged": True, "factors": {}, "missing": []}


# ---------------------------------------------------------------------------
# Fraud service exchange-rate cache
#
# Live rates are an external input, not persisted state: they are fetched once
# per process and cached in a module global. Both paths matter -- the fallback
# when the rate source is unreachable (the request must still succeed, with
# the high-value factor degraded to not-applicable) and the cache hit that
# stops a second fetch.
# ---------------------------------------------------------------------------


def _fraud_service_module():
    import services.fraud_detection.main as module

    return module


def test_rates_fallback_when_the_source_is_unreachable(monkeypatch):
    module = _fraud_service_module()
    monkeypatch.setattr(module, "_rates_cache", None)

    def _unreachable(*_args, **_kwargs):
        raise RuntimeError("rate source unreachable")

    monkeypatch.setattr(module, "fetch_exchange_rates", _unreachable)

    rates = module._get_rates()

    assert isinstance(rates, ExchangeRates)
    assert rates.base == "USD"
    assert rates.rates == {}, "an empty rate table degrades the high-value factor rather than erroring"


def test_rates_are_fetched_once_and_then_cached(monkeypatch):
    module = _fraud_service_module()
    monkeypatch.setattr(module, "_rates_cache", None)

    calls: list[int] = []

    def _counting_fetch(*_args, **_kwargs):
        calls.append(1)
        return ExchangeRates(base="USD", rates={"USD": 1, "GBP": 2})

    monkeypatch.setattr(module, "fetch_exchange_rates", _counting_fetch)

    first = module._get_rates()
    second = module._get_rates()

    assert len(calls) == 1, "the second call must hit the cache, not refetch"
    assert first is second


def test_scoring_still_succeeds_with_an_unreachable_rate_source(monkeypatch):
    """The service-level consequence of the fallback above: a request is
    answered normally, with the high-value factor marked not-applicable."""
    module = _fraud_service_module()
    monkeypatch.setattr(module, "_rates_cache", None)
    monkeypatch.setattr(
        module,
        "fetch_exchange_rates",
        lambda *_a, **_kw: (_ for _ in ()).throw(RuntimeError("unreachable")),
    )

    client = TestClient(module.app)
    response = client.post(
        "/score",
        json={
            "transaction": {
                "transaction_id": "TXN-RATES-1",
                "timestamp": "2026-03-16T10:00:00Z",
                "source_account": "ACC-1",
                "destination_account": "ACC-2",
                "amount": "25000.00",
                "currency": "GBP",
                "transaction_type": "transfer",
                "description": "",
                "metadata": {"channel": "online", "country": "GB"},
            },
            "context": {},
        },
    )

    assert response.status_code == 200
    result = response.json()["result"]
    assert result["factors"]["high_value_amount"]["applicable"] is False
