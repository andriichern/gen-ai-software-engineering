"""CSV ticket import."""
from __future__ import annotations

import csv
import io

from ..models import ImportSummary, Ticket
from .base import build_summary, collect_tickets


def parse_csv(content: bytes) -> tuple[list[Ticket], ImportSummary]:
    text = content.decode("utf-8-sig")
    rows = list(csv.DictReader(io.StringIO(text)))

    errors = []
    tickets = collect_tickets(enumerate(rows), errors)
    return tickets, build_summary(len(rows), tickets, errors)
