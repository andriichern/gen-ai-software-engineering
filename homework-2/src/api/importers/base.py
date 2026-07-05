"""Shared row -> Ticket conversion used by all format-specific importers."""
from __future__ import annotations

from typing import Any

from pydantic import ValidationError

from ..models import Source, Ticket, TicketCreate, TicketMetadata


class RowParseError(Exception):
    """Raised when a raw record can't even be shaped into a row dict (e.g. bad XML)."""


def _split_tags(raw: Any) -> list[str]:
    if raw is None or raw == "":
        return []
    if isinstance(raw, list):
        return [str(t).strip() for t in raw if str(t).strip()]
    return [t.strip() for t in str(raw).split(",") if t.strip()]


def row_to_ticket(row: dict[str, Any]) -> Ticket:
    """Convert a flat field dict (as produced by CSV/JSON/XML parsing) into a Ticket.

    Raises pydantic.ValidationError on invalid/missing fields.
    """
    metadata = TicketMetadata(
        source=row.get("source") or Source.API,
        browser=row.get("browser") or None,
        device_type=row.get("device_type") or None,
    )
    payload = {
        "customer_id": row.get("customer_id"),
        "customer_email": row.get("customer_email"),
        "customer_name": row.get("customer_name"),
        "subject": row.get("subject"),
        "description": row.get("description"),
        "category": row.get("category") or None,
        "priority": row.get("priority") or None,
        "status": row.get("status") or "new",
        "assigned_to": row.get("assigned_to") or None,
        "tags": _split_tags(row.get("tags")),
        "metadata": metadata,
    }
    create = TicketCreate.model_validate(payload)
    return Ticket.from_create(create)


__all__ = ["row_to_ticket", "RowParseError", "ValidationError"]
