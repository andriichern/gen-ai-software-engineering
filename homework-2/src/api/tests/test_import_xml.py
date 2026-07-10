"""XML import tests, using the real sample/invalid fixture files (Task 3)."""
from __future__ import annotations

import pytest

from api.importers.base import RowParseError
from api.importers.xml_importer import parse_xml


def _read(path):
    return path.read_bytes()


def test_sample_xml_all_30_records_import_successfully(fixtures_dir):
    tickets, summary = parse_xml(_read(fixtures_dir / "sample_tickets.xml"))
    assert summary.total == 30
    assert summary.successful == 30
    assert summary.failed == 0
    assert len(tickets) == 30


def test_invalid_xml_reports_errors_without_aborting_batch(fixtures_dir):
    tickets, summary = parse_xml(_read(fixtures_dir / "invalid_tickets.xml"))
    assert summary.total == 5
    assert summary.successful == 1
    assert summary.failed == 4
    assert len(tickets) == 1


def test_malformed_xml_syntax_raises_row_parse_error():
    with pytest.raises(RowParseError):
        parse_xml(b"<tickets><ticket><subject>unclosed</ticket></tickets>")


def test_empty_tickets_root_yields_zero_tickets():
    tickets, summary = parse_xml(b"<tickets></tickets>")
    assert summary.total == 0
    assert tickets == []


def test_import_endpoint_creates_tickets_from_xml(client, fixtures_dir):
    content = _read(fixtures_dir / "sample_tickets.xml")
    response = client.post(
        "/tickets/import", files={"file": ("sample_tickets.xml", content, "application/xml")}
    )
    assert response.status_code == 200
    assert response.json()["successful"] == 30
    assert len(client.get("/tickets").json()) == 30
