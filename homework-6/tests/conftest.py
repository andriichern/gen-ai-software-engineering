"""Shared pytest fixtures and configuration for all tests."""
import json
import tempfile
from decimal import Decimal
from pathlib import Path
from typing import Any, Dict, List

import pytest


@pytest.fixture
def temp_shared_dir():
    """Create a temporary shared directory structure for tests."""
    with tempfile.TemporaryDirectory() as tmpdir:
        shared = Path(tmpdir) / "shared"
        shared.mkdir()
        (shared / "input").mkdir()
        (shared / "processing").mkdir()
        (shared / "output").mkdir()
        (shared / "results").mkdir()
        yield shared


@pytest.fixture
def valid_transactions() -> List[Dict[str, Any]]:
    """Load valid transaction fixtures."""
    fixture_path = Path(__file__).parent / "fixtures" / "valid_transactions.json"
    with fixture_path.open("r") as f:
        return json.load(f)


@pytest.fixture
def invalid_transactions() -> List[Dict[str, Any]]:
    """Load invalid transaction fixtures."""
    fixture_path = Path(__file__).parent / "fixtures" / "invalid_transactions.json"
    with fixture_path.open("r") as f:
        return json.load(f)


@pytest.fixture
def edge_case_transactions() -> List[Dict[str, Any]]:
    """Load edge case transaction fixtures."""
    fixture_path = Path(__file__).parent / "fixtures" / "edge_cases.json"
    with fixture_path.open("r") as f:
        return json.load(f)


@pytest.fixture
def sample_transaction() -> Dict[str, Any]:
    """A single valid transaction for testing."""
    return {
        "transaction_id": "TEST_001",
        "timestamp": "2026-03-16T10:00:00Z",
        "source_account": "ACC-TEST01",
        "destination_account": "ACC-TEST02",
        "amount": "1000.00",
        "currency": "USD",
        "transaction_type": "transfer",
        "description": "Test transaction",
        "metadata": {
            "channel": "online",
            "country": "US"
        }
    }


@pytest.fixture
def sample_validation_result() -> Dict[str, Any]:
    """A sample validation result."""
    return {
        "status": "passed",
        "reason": None,
        "checked_at": "2026-03-16T10:00:00+00:00"
    }


@pytest.fixture
def sample_fraud_result() -> Dict[str, Any]:
    """A sample fraud detection result."""
    return {
        "score": "0.50",
        "factors": {
            "high_value_amount": True,
            "cross_border_mismatch": False,
            "unusual_hour_timing": False
        },
        "flagged": True,
        "scored_at": "2026-03-16T10:00:00+00:00"
    }


@pytest.fixture
def sample_compliance_result() -> Dict[str, Any]:
    """A sample compliance check result."""
    return {
        "status": "cleared",
        "reason": None,
        "checked_at": "2026-03-16T10:00:00+00:00"
    }


@pytest.fixture
def sample_exchange_rates() -> Dict[str, Decimal]:
    """Sample exchange rates for testing."""
    return {
        "USD": Decimal("1"),
        "EUR": Decimal("0.92"),
        "GBP": Decimal("0.79"),
    }


# ---------------------------------------------------------------------------
# On-disk stage fixtures
#
# The unit tests above exercise the pure decision functions. The fixtures
# below support testing each stage's run_stage() file lifecycle and the
# orchestrator, which is where the real directory/envelope contract lives.
# ---------------------------------------------------------------------------


@pytest.fixture
def stage_dirs(tmp_path) -> Dict[str, Path]:
    """A fresh shared/ working tree (input, processing, output, results)."""
    shared = tmp_path / "shared"
    dirs = {
        "shared": shared,
        "input": shared / "input",
        "processing": shared / "processing",
        "output": shared / "output",
        "results": shared / "results",
    }
    for key, path in dirs.items():
        if key != "shared":
            path.mkdir(parents=True, exist_ok=True)
    return dirs


@pytest.fixture
def put_input(stage_dirs):
    """Write an original transaction record into shared/input/."""

    def _put(record: Dict[str, Any]) -> Path:
        path = stage_dirs["input"] / f"{record['transaction_id']}.json"
        path.write_text(json.dumps(record), encoding="utf-8")
        return path

    return _put


@pytest.fixture
def put_envelope(stage_dirs):
    """Write an inter-stage message envelope into shared/output/.

    Mirrors lib.common.make_envelope's shape but with deterministic values, so
    a downstream stage can be driven in isolation from its predecessors.
    """

    def _put(transaction_id: str, data: Dict[str, Any], source_stage: str = "upstream",
             target_stage: str = "downstream") -> Path:
        envelope = {
            "message_id": f"msg-{transaction_id}",
            "timestamp": "2026-03-16T10:00:00+00:00",
            "source_stage": source_stage,
            "target_stage": target_stage,
            "message_type": "transaction",
            "data": data,
        }
        path = stage_dirs["output"] / f"{transaction_id}.json"
        path.write_text(json.dumps(envelope), encoding="utf-8")
        return path

    return _put


@pytest.fixture
def fake_rates() -> Dict[str, Decimal]:
    """Deterministic offline exchange rates.

    Every test that would otherwise reach the live Frankfurter API uses these,
    so the suite never depends on network availability.
    """
    return {"USD": Decimal("1"), "EUR": Decimal("0.92"), "GBP": Decimal("0.79")}


@pytest.fixture
def sample_dataset_path() -> Path:
    """Path to the real sample-transactions.json shipped with the project."""
    return Path(__file__).resolve().parent.parent / "sample-transactions.json"
