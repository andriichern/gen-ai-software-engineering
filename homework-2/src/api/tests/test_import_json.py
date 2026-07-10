"""JSON import tests, using the real sample/invalid fixture files (Task 3)."""
from __future__ import annotations

import json

import pytest

from api.importers.base import RowParseError
from api.importers.json_importer import parse_json


def _read(path):
    return path.read_bytes()


def test_sample_json_all_20_records_import_successfully(fixtures_dir):
    tickets, summary = parse_json(_read(fixtures_dir / "sample_tickets.json"))
    assert summary.total == 20
    assert summary.successful == 20
    assert summary.failed == 0
    assert len(tickets) == 20


def test_invalid_json_reports_errors_without_aborting_batch(fixtures_dir):
    tickets, summary = parse_json(_read(fixtures_dir / "invalid_tickets.json"))
    assert summary.total == 5
    assert summary.successful == 1
    assert summary.failed == 4
    assert len(tickets) == 1


def test_json_object_wrapped_in_tickets_key_is_accepted():
    payload = {
        "tickets": [
            {
                "customer_id": "c1",
                "customer_email": "a@b.com",
                "customer_name": "A",
                "subject": "Hi",
                "description": "A valid description here.",
            }
        ]
    }
    tickets, summary = parse_json(json.dumps(payload).encode())
    assert summary.total == 1
    assert summary.successful == 1
    assert len(tickets) == 1


def test_malformed_json_syntax_raises_row_parse_error():
    with pytest.raises(RowParseError):
        parse_json(b"{not valid json")


def test_non_list_non_dict_json_raises_row_parse_error():
    with pytest.raises(RowParseError):
        parse_json(b"42")


def test_non_dict_item_in_list_is_reported_as_error():
    tickets, summary = parse_json(json.dumps(["not-a-dict-record"]).encode())
    assert summary.total == 1
    assert summary.failed == 1
    assert tickets == []


def test_import_endpoint_creates_tickets_from_json(client, fixtures_dir):
    content = _read(fixtures_dir / "sample_tickets.json")
    response = client.post(
        "/tickets/import", files={"file": ("sample_tickets.json", content, "application/json")}
    )
    assert response.status_code == 200
    assert response.json()["successful"] == 20
    assert len(client.get("/tickets").json()) == 20
