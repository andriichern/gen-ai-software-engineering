"""Bonus coverage for the /category management API (added beyond TASKS.md's
original Task 3 file list, since the category-management feature itself was
added after the spec was written)."""
from __future__ import annotations

from api.services.category_registry import category_registry


def test_list_categories_includes_builtins(client):
    response = client.get("/category/list")
    assert response.status_code == 200
    keys = {c["category"] for c in response.json()}
    assert {"account_access", "billing_question", "technical_issue"} <= keys
    assert "other" not in keys


def test_get_category_success(client):
    response = client.get("/category/account_access")
    assert response.status_code == 200
    assert "password" in response.json()["keywords"]


def test_get_category_not_found(client):
    response = client.get("/category/does_not_exist")
    assert response.status_code == 404


def test_create_category_success(client):
    response = client.post("/category", json={"key": "shipping_delay", "keywords": ["tracking lost"]})
    assert response.status_code == 201
    assert response.json() == {"category": "shipping_delay", "keywords": ["tracking lost"]}


def test_create_category_is_idempotent_and_merges_keywords(client):
    client.post("/category", json={"key": "shipping_delay", "keywords": ["tracking lost"]})
    response = client.post("/category", json={"key": "shipping_delay", "keywords": ["tracking lost", "late package"]})
    assert response.status_code == 201
    assert response.json()["keywords"] == ["tracking lost", "late package"]
    assert len(category_registry.list_all()) == 6  # 5 builtins + this one, no duplicate entry


def test_create_category_rejects_reserved_other_key(client):
    response = client.post("/category", json={"key": "other", "keywords": []})
    assert response.status_code == 400


def test_create_category_rejects_invalid_key_format(client):
    response = client.post("/category", json={"key": "Not A Key!", "keywords": []})
    assert response.status_code == 400


def test_update_category_merges_without_duplicating(client):
    client.post("/category", json={"key": "shipping_delay", "keywords": ["tracking lost"]})
    response = client.put("/category/shipping_delay", json={"keywords": ["tracking lost", "carrier delay"]})
    assert response.status_code == 200
    assert response.json()["keywords"] == ["tracking lost", "carrier delay"]


def test_update_category_not_found(client):
    response = client.put("/category/does_not_exist", json={"keywords": ["x"]})
    assert response.status_code == 404


def test_new_category_is_used_by_classification_after_creation(client):
    client.post("/category", json={"key": "shipping_delay", "keywords": ["tracking lost"]})
    created = client.post(
        "/tickets",
        json=dict(
            customer_id="c1", customer_email="a@b.com", customer_name="A",
            subject="Order issue", description="My tracking lost somewhere in transit.",
        ),
    ).json()
    result = client.post(f"/tickets/{created['id']}/auto-classify").json()
    assert result["category"] == "shipping_delay"
