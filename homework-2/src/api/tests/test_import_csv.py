"""CSV import tests, using the real sample/invalid fixture files (Task 3)."""
from __future__ import annotations

import csv
import io

from api.importers.csv_importer import parse_csv


def _read(path):
    return path.read_bytes()


def test_sample_csv_all_50_rows_import_successfully(fixtures_dir):
    tickets, summary = parse_csv(_read(fixtures_dir / "sample_tickets.csv"))
    assert summary.total == 50
    assert summary.successful == 50
    assert summary.failed == 0
    assert len(tickets) == 50


def test_invalid_csv_reports_errors_without_aborting_batch(fixtures_dir):
    tickets, summary = parse_csv(_read(fixtures_dir / "invalid_tickets.csv"))
    assert summary.total == 6
    assert summary.successful == 2
    assert summary.failed == 4
    assert len(tickets) == 2
    error_fields = {"customer_email", "description", "subject", "category"}
    assert {e.error.split("\n")[1].strip() for e in summary.errors} <= error_fields


def test_csv_tags_column_parsed_into_list(fixtures_dir):
    raw = _read(fixtures_dir / "sample_tickets.csv")
    reader = csv.DictReader(io.StringIO(raw.decode("utf-8-sig")))
    row_with_tags = next(row for row in reader if row["tags"])
    expected_tags = [t.strip() for t in row_with_tags["tags"].split(",") if t.strip()]

    tickets, _ = parse_csv(raw)
    matching = next(t for t in tickets if t.customer_id == row_with_tags["customer_id"])
    assert matching.tags == expected_tags


def test_csv_with_only_header_yields_zero_tickets():
    content = b"customer_id,customer_email,customer_name,subject,description\n"
    tickets, summary = parse_csv(content)
    assert summary.total == 0
    assert summary.successful == 0
    assert tickets == []


def test_import_endpoint_creates_tickets_from_csv(client, fixtures_dir):
    content = _read(fixtures_dir / "sample_tickets.csv")
    response = client.post(
        "/tickets/import", files={"file": ("sample_tickets.csv", content, "text/csv")}
    )
    assert response.status_code == 200
    assert response.json()["successful"] == 50
    assert len(client.get("/tickets").json()) == 50


def test_import_endpoint_rejects_unsupported_extension(client):
    response = client.post(
        "/tickets/import", files={"file": ("sample_tickets.txt", b"irrelevant", "text/plain")}
    )
    assert response.status_code == 400
