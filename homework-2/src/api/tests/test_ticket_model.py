"""Data validation tests for the Ticket/TicketCreate Pydantic models (Task 3)."""
from __future__ import annotations

import pytest
from pydantic import ValidationError

from api.models import Priority, Status, Ticket, TicketCreate

VALID_PAYLOAD = dict(
    customer_id="cust-1",
    customer_email="jane@example.com",
    customer_name="Jane Doe",
    subject="Cannot access account",
    description="I forgot my password and cannot log in at all.",
)


def test_valid_ticket_create_succeeds():
    ticket_create = TicketCreate(**VALID_PAYLOAD)
    assert ticket_create.customer_email == "jane@example.com"
    assert ticket_create.status == Status.NEW


def test_invalid_email_is_rejected():
    with pytest.raises(ValidationError, match="customer_email"):
        TicketCreate(**{**VALID_PAYLOAD, "customer_email": "not-an-email"})


def test_subject_below_min_length_is_rejected():
    with pytest.raises(ValidationError, match="subject"):
        TicketCreate(**{**VALID_PAYLOAD, "subject": ""})


def test_subject_above_max_length_is_rejected():
    with pytest.raises(ValidationError, match="subject"):
        TicketCreate(**{**VALID_PAYLOAD, "subject": "x" * 201})


def test_description_below_min_length_is_rejected():
    with pytest.raises(ValidationError, match="description"):
        TicketCreate(**{**VALID_PAYLOAD, "description": "short"})


def test_description_above_max_length_is_rejected():
    with pytest.raises(ValidationError, match="description"):
        TicketCreate(**{**VALID_PAYLOAD, "description": "x" * 2001})


def test_unknown_category_value_is_rejected():
    with pytest.raises(ValidationError, match="category"):
        TicketCreate(**{**VALID_PAYLOAD, "category": "not_a_category"})


def test_invalid_priority_enum_value_is_rejected():
    with pytest.raises(ValidationError, match="priority"):
        TicketCreate(**{**VALID_PAYLOAD, "priority": "urgentish"})


def test_ticket_from_create_applies_defaults_when_unset():
    ticket_create = TicketCreate(**VALID_PAYLOAD)
    ticket = Ticket.from_create(ticket_create)
    assert ticket.category == "other"
    assert ticket.priority == Priority.MEDIUM
    assert ticket.status == Status.NEW
    assert ticket.resolved_at is None
    assert ticket.tags == []
