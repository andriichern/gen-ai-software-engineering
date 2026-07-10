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

from ..models import ImportSummary, Ticket
from .base import RowParseError, build_summary, collect_tickets


def _element_to_row(element: ET.Element) -> dict[str, str]:
    return {child.tag: (child.text or "").strip() for child in element}


def parse_xml(content: bytes) -> tuple[list[Ticket], ImportSummary]:
    try:
        root = ET.fromstring(content)
    except ET.ParseError as exc:
        raise RowParseError(f"Invalid XML: {exc}") from exc

    rows = [_element_to_row(element) for element in root.findall("ticket")]

    errors = []
    tickets = collect_tickets(enumerate(rows), errors)
    return tickets, build_summary(len(rows), tickets, errors)
