"""End-to-end integration workflows across multiple endpoints (Task 5 / Task 3)."""
from __future__ import annotations

from concurrent.futures import ThreadPoolExecutor


def test_complete_ticket_lifecycle(client):
    created = client.post(
        "/tickets",
        params={"auto_classify": True},
        json=dict(
            customer_id="cust-1",
            customer_email="jane@example.com",
            customer_name="Jane Doe",
            subject="Cannot access account",
            description="I forgot my password and cannot log in at all.",
        ),
    ).json()
    assert created["category"] == "account_access"

    resolved = client.put(f"/tickets/{created['id']}", json={"status": "resolved"}).json()
    assert resolved["status"] == "resolved"
    assert resolved["resolved_at"] is not None

    delete_response = client.delete(f"/tickets/{created['id']}")
    assert delete_response.status_code == 204
    assert client.get(f"/tickets/{created['id']}").status_code == 404


def test_bulk_import_with_auto_classification_verification(client, fixtures_dir):
    content = (fixtures_dir / "sample_tickets.csv").read_bytes()
    response = client.post(
        "/tickets/import",
        params={"auto_classify": True},
        files={"file": ("sample_tickets.csv", content, "text/csv")},
    )
    assert response.status_code == 200
    assert response.json()["successful"] == 50

    tickets = client.get("/tickets").json()
    assert len(tickets) == 50
    assert all(t["classification_confidence"] is not None for t in tickets)
    assert any(t["category"] != "other" for t in tickets)


def test_concurrent_ticket_creation(client):
    def create_one(i):
        return client.post(
            "/tickets",
            json=dict(
                customer_id=f"cust-{i}",
                customer_email=f"user{i}@example.com",
                customer_name=f"User {i}",
                subject="Concurrent test ticket",
                description="Created as part of a concurrency test scenario.",
            ),
        )

    with ThreadPoolExecutor(max_workers=25) as executor:
        responses = list(executor.map(create_one, range(25)))

    assert all(r.status_code == 201 for r in responses)
    ids = {r.json()["id"] for r in responses}
    assert len(ids) == 25
    assert len(client.get("/tickets").json()) == 25


def test_combined_filtering_by_category_and_priority(client):
    client.post(
        "/tickets",
        json=dict(
            customer_id="c1", customer_email="a@b.com", customer_name="A",
            subject="x", description="Placeholder description text.",
            category="billing_question", priority="high",
        ),
    )
    client.post(
        "/tickets",
        json=dict(
            customer_id="c2", customer_email="b@b.com", customer_name="B",
            subject="x", description="Placeholder description text.",
            category="billing_question", priority="low",
        ),
    )

    response = client.get("/tickets", params={"category": "billing_question", "priority": "high"})
    results = response.json()
    assert len(results) == 1
    assert results[0]["customer_id"] == "c1"


def test_custom_category_affects_end_to_end_classification(client):
    client.post("/category", json={"key": "shipping_delay", "keywords": ["package late", "tracking lost"]})

    created = client.post(
        "/tickets",
        json=dict(
            customer_id="c1", customer_email="a@b.com", customer_name="A",
            subject="Where is my order", description="My package late and tracking lost entirely.",
        ),
    ).json()

    result = client.post(f"/tickets/{created['id']}/auto-classify").json()
    assert result["category"] == "shipping_delay"
