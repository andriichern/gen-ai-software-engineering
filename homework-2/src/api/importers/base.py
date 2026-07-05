"""Shared row -> Ticket conversion used by all format-specific importers."""
from __future__ import annotations

from typing import Any

from pydantic import ValidationError

from ..models import ImportRowError, ImportSummary, Source, Ticket, TicketCreate, TicketMetadata


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


def collect_tickets(indexed_rows: Any, errors: list[ImportRowError]) -> list[Ticket]:
    """Shared per-row loop over (index, row) pairs: builds a Ticket for each
    row, appending a validation error to `errors` (in place) instead of
    raising for bad rows. Callers pre-filter rows that aren't even the right
    shape (e.g. a JSON array entry that isn't an object) before calling this,
    so indices stay aligned to the original input."""
    tickets: list[Ticket] = []
    for index, row in indexed_rows:
        try:
            tickets.append(row_to_ticket(row))
        except ValidationError as exc:
            errors.append(ImportRowError(index=index, error=str(exc)))
    return tickets


def build_summary(total: int, tickets: list[Ticket], errors: list[ImportRowError]) -> ImportSummary:
    return ImportSummary(total=total, successful=len(tickets), failed=len(errors), errors=errors)


__all__ = [
    "row_to_ticket",
    "collect_tickets",
    "build_summary",
    "RowParseError",
    "ValidationError",
]
