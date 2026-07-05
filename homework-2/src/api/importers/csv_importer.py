"""CSV ticket import."""
from __future__ import annotations

import csv
import io

from pydantic import ValidationError

from ..models import ImportError_, ImportSummary, Ticket
from .base import row_to_ticket


def parse_csv(content: bytes) -> tuple[list[Ticket], ImportSummary]:
    text = content.decode("utf-8-sig")
    reader = csv.DictReader(io.StringIO(text))

    tickets: list[Ticket] = []
    errors: list[ImportError_] = []
    total = 0

    for index, row in enumerate(reader):
        total += 1
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
