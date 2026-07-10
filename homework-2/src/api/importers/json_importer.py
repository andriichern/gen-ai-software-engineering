"""JSON ticket import."""
from __future__ import annotations

import json

from ..models import ImportRowError, ImportSummary, Ticket
from .base import RowParseError, build_summary, collect_tickets


def parse_json(content: bytes) -> tuple[list[Ticket], ImportSummary]:
    try:
        data = json.loads(content)
    except json.JSONDecodeError as exc:
        raise RowParseError(f"Invalid JSON: {exc}") from exc

    if isinstance(data, dict):
        data = data.get("tickets", [])
    if not isinstance(data, list):
        raise RowParseError("Expected a JSON array of tickets or {'tickets': [...]}")

    errors: list[ImportRowError] = []
    valid_rows = []
    for index, row in enumerate(data):
        if isinstance(row, dict):
            valid_rows.append((index, row))
        else:
            errors.append(ImportRowError(index=index, error="Record is not a JSON object"))

    tickets = collect_tickets(valid_rows, errors)
    return tickets, build_summary(len(data), tickets, errors)
