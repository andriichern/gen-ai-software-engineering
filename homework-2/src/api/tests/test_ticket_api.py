"""API endpoint tests for /tickets CRUD (Task 3)."""
from __future__ import annotations

VALID_PAYLOAD = dict(
    customer_id="cust-1",
    customer_email="jane@example.com",
    customer_name="Jane Doe",
    subject="Cannot access account",
    description="I forgot my password and cannot log in at all.",
)


def test_health_check(client):
    response = client.get("/health")
    assert response.status_code == 200
    assert response.json() == {"status": "ok"}


def test_create_ticket_success(client):
    response = client.post("/tickets", json=VALID_PAYLOAD)
    assert response.status_code == 201
    body = response.json()
    assert body["customer_id"] == "cust-1"
    assert body["category"] == "other"
    assert body["priority"] == "medium"


def test_create_ticket_validation_error(client):
    response = client.post("/tickets", json={**VALID_PAYLOAD, "customer_email": "bad"})
    assert response.status_code == 400


def test_create_ticket_with_auto_classify_flag(client):
    response = client.post("/tickets", params={"auto_classify": True}, json=VALID_PAYLOAD)
    assert response.status_code == 201
    body = response.json()
    assert body["category"] == "account_access"
    assert body["classification_confidence"] is not None


def test_get_ticket_success(client):
    created = client.post("/tickets", json=VALID_PAYLOAD).json()
    response = client.get(f"/tickets/{created['id']}")
    assert response.status_code == 200
    assert response.json()["id"] == created["id"]


def test_get_ticket_not_found(client):
    response = client.get("/tickets/00000000-0000-0000-0000-000000000000")
    assert response.status_code == 404


def test_list_tickets_no_filter_returns_all(client):
    client.post("/tickets", json=VALID_PAYLOAD)
    client.post("/tickets", json={**VALID_PAYLOAD, "customer_id": "cust-2"})
    response = client.get("/tickets")
    assert response.status_code == 200
    assert len(response.json()) == 2


def test_list_tickets_combined_filter_by_category_and_priority(client):
    client.post("/tickets", json={**VALID_PAYLOAD, "category": "billing_question", "priority": "high"})
    client.post("/tickets", json={**VALID_PAYLOAD, "category": "billing_question", "priority": "low"})
    client.post("/tickets", json={**VALID_PAYLOAD, "category": "technical_issue", "priority": "high"})

    response = client.get("/tickets", params={"category": "billing_question", "priority": "high"})
    assert response.status_code == 200
    results = response.json()
    assert len(results) == 1
    assert results[0]["category"] == "billing_question"
    assert results[0]["priority"] == "high"


def test_update_ticket_success_marks_overridden(client):
    created = client.post("/tickets", json=VALID_PAYLOAD).json()
    response = client.put(f"/tickets/{created['id']}", json={"category": "billing_question", "priority": "high"})
    assert response.status_code == 200
    body = response.json()
    assert body["category"] == "billing_question"
    assert body["priority"] == "high"
    assert body["classification_overridden"] is True


def test_update_ticket_not_found(client):
    response = client.put(
        "/tickets/00000000-0000-0000-0000-000000000000", json={"category": "billing_question"}
    )
    assert response.status_code == 404


def test_delete_ticket_success_then_get_404(client):
    created = client.post("/tickets", json=VALID_PAYLOAD).json()
    delete_response = client.delete(f"/tickets/{created['id']}")
    assert delete_response.status_code == 204
    get_response = client.get(f"/tickets/{created['id']}")
    assert get_response.status_code == 404


def test_delete_ticket_not_found(client):
    response = client.delete("/tickets/00000000-0000-0000-0000-000000000000")
    assert response.status_code == 404


def test_auto_classify_not_found(client):
    response = client.post("/tickets/00000000-0000-0000-0000-000000000000/auto-classify")
    assert response.status_code == 404


def test_import_endpoint_rejects_malformed_file(client):
    response = client.post(
        "/tickets/import",
        files={"file": ("broken.xml", b"<tickets><ticket><subject>x</ticket></tickets>", "application/xml")},
    )
    assert response.status_code == 422


def test_list_tickets_filters_by_status_customer_id_assigned_to_and_tag(client):
    client.post(
        "/tickets",
        json={
            **VALID_PAYLOAD,
            "customer_id": "cust-tagged",
            "assigned_to": "agent-1",
            "tags": ["vip"],
            "status": "in_progress",
        },
    )
    client.post("/tickets", json={**VALID_PAYLOAD, "customer_id": "cust-other"})

    assert len(client.get("/tickets", params={"status": "in_progress"}).json()) == 1
    assert len(client.get("/tickets", params={"customer_id": "cust-tagged"}).json()) == 1
    assert len(client.get("/tickets", params={"assigned_to": "agent-1"}).json()) == 1
    assert len(client.get("/tickets", params={"tag": "vip"}).json()) == 1
    assert len(client.get("/tickets", params={"tag": "nonexistent"}).json()) == 0
