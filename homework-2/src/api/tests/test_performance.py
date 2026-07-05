"""Lightweight performance benchmarks with generous thresholds (Task 3 / Task 5).

These aren't rigorous load tests -- they exist to catch obvious accidental
O(n^2) regressions, not to certify production throughput.
"""
from __future__ import annotations

import time

from api.models import TicketCreate
from api.routers.tickets import store as ticket_store
from api.services.classification import classify_ticket
from api.services.store import TicketStore
from api.models import Ticket


def test_bulk_csv_import_completes_quickly(client, fixtures_dir):
    content = (fixtures_dir / "sample_tickets.csv").read_bytes()
    start = time.perf_counter()
    response = client.post("/tickets/import", files={"file": ("sample_tickets.csv", content, "text/csv")})
    elapsed = time.perf_counter() - start
    assert response.status_code == 200
    assert elapsed < 3.0


def test_bulk_json_import_completes_quickly(client, fixtures_dir):
    content = (fixtures_dir / "sample_tickets.json").read_bytes()
    start = time.perf_counter()
    response = client.post(
        "/tickets/import", files={"file": ("sample_tickets.json", content, "application/json")}
    )
    elapsed = time.perf_counter() - start
    assert response.status_code == 200
    assert elapsed < 3.0


def test_bulk_xml_import_completes_quickly(client, fixtures_dir):
    content = (fixtures_dir / "sample_tickets.xml").read_bytes()
    start = time.perf_counter()
    response = client.post("/tickets/import", files={"file": ("sample_tickets.xml", content, "application/xml")})
    elapsed = time.perf_counter() - start
    assert response.status_code == 200
    assert elapsed < 3.0


def test_classification_throughput_for_200_tickets():
    start = time.perf_counter()
    for i in range(200):
        classify_ticket(f"Issue {i}", "I forgot my password and cannot log in to my account.")
    elapsed = time.perf_counter() - start
    assert elapsed < 2.0


def test_list_and_filter_with_many_tickets_is_fast(client):
    for i in range(300):
        ticket = Ticket.from_create(
            TicketCreate(
                customer_id=f"c{i}",
                customer_email=f"u{i}@example.com",
                customer_name=f"User {i}",
                subject="Bulk seeded ticket",
                description="Seeded directly into the store for a performance benchmark.",
                category="billing_question" if i % 2 == 0 else "technical_issue",
                priority="high" if i % 3 == 0 else "medium",
            )
        )
        ticket_store.create(ticket)

    start = time.perf_counter()
    response = client.get("/tickets", params={"category": "billing_question", "priority": "high"})
    elapsed = time.perf_counter() - start

    assert response.status_code == 200
    assert elapsed < 1.0
