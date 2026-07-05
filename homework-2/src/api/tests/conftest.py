"""Shared pytest fixtures: a TestClient plus isolation between tests."""
from __future__ import annotations

from pathlib import Path

import pytest
from fastapi.testclient import TestClient

from api.main import app
from api.routers.tickets import store
from api.services.category_registry import category_registry

FIXTURES_DIR = Path(__file__).parent / "fixtures"


@pytest.fixture
def client():
    return TestClient(app)


@pytest.fixture(autouse=True)
def reset_state():
    """Ticket store and category registry are process-wide singletons; reset
    them before every test so tests can't leak state into each other."""
    store.clear()
    category_registry.reset()
    yield
    store.clear()
    category_registry.reset()


@pytest.fixture
def fixtures_dir() -> Path:
    return FIXTURES_DIR
