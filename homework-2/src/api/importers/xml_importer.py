"""XML ticket import.

Expected shape:
<tickets>
  <ticket>
    <customer_id>...</customer_id>
    <customer_email>...</customer_email>
    ...
    <tags>vip,urgent</tags>
  </ticket>
</tickets>
"""
from __future__ import annotations

from xml.etree import ElementTree as ET

from pydantic import ValidationError

from ..models import ImportError_, ImportSummary, Ticket
from .base import RowParseError, row_to_ticket


def _element_to_row(element: ET.Element) -> dict[str, str]:
    return {child.tag: (child.text or "").strip() for child in element}


def parse_xml(content: bytes) -> tuple[list[Ticket], ImportSummary]:
    try:
        root = ET.fromstring(content)
    except ET.ParseError as exc:
        raise RowParseError(f"Invalid XML: {exc}") from exc

    ticket_elements = root.findall("ticket")

    tickets: list[Ticket] = []
    errors: list[ImportError_] = []
    total = 0

    for index, element in enumerate(ticket_elements):
        total += 1
        try:
            row = _element_to_row(element)
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
