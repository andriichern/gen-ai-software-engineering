"""JSON ticket import."""
from __future__ import annotations

import json

from pydantic import ValidationError

from ..models import ImportError_, ImportSummary, Ticket
from .base import RowParseError, row_to_ticket


def parse_json(content: bytes) -> tuple[list[Ticket], ImportSummary]:
    try:
        data = json.loads(content)
    except json.JSONDecodeError as exc:
        raise RowParseError(f"Invalid JSON: {exc}") from exc

    if isinstance(data, dict):
        data = data.get("tickets", [])
    if not isinstance(data, list):
        raise RowParseError("Expected a JSON array of tickets or {'tickets': [...]}")

    tickets: list[Ticket] = []
    errors: list[ImportError_] = []
    total = 0

    for index, row in enumerate(data):
        total += 1
        if not isinstance(row, dict):
            errors.append(ImportError_(index=index, error="Record is not a JSON object"))
            continue
        try:
            tickets.append(row_to_ticket(row))
        except ValidationError as exc:
            errors.append(ImportError_(index=index, error=str(exc)))

    summary = ImportSummary(
        total=total,
        successful=len(tickets),
        failed=len(errors),
        errors=errors,
    )
    return tickets, summary
