"""Ticket API routes."""
from __future__ import annotations

from uuid import UUID

from fastapi import APIRouter, Depends, HTTPException, Query, UploadFile

from ..importers.base import RowParseError
from ..importers.csv_importer import parse_csv
from ..importers.json_importer import parse_json
from ..importers.xml_importer import parse_xml
from ..models import (
    ClassificationResult,
    ImportSummary,
    Ticket,
    TicketCreate,
    TicketFilters,
    TicketUpdate,
)
from ..services.classification import classify_ticket
from ..services.store import TicketNotFoundError, TicketStore

router = APIRouter(prefix="/tickets", tags=["tickets"])
store = TicketStore()

_PARSERS = {
    "csv": parse_csv,
    "json": parse_json,
    "xml": parse_xml,
}


def _apply_classification(ticket: Ticket) -> None:
    result: ClassificationResult = classify_ticket(ticket.subject, ticket.description)
    ticket.category = result.category
    ticket.priority = result.priority
    ticket.classification_confidence = result.confidence


@router.post("", response_model=Ticket, status_code=201)
def create_ticket(payload: TicketCreate, auto_classify: bool = Query(False)):
    ticket = Ticket.from_create(payload)
    if auto_classify:
        _apply_classification(ticket)
    return store.create(ticket)


@router.post("/import", response_model=ImportSummary)
async def import_tickets(file: UploadFile, auto_classify: bool = Query(False)):
    suffix = (file.filename or "").rsplit(".", 1)[-1].lower()
    parser = _PARSERS.get(suffix)
    if parser is None:
        raise HTTPException(
            status_code=400,
            detail=f"Unsupported file format '{suffix}'. Expected one of: csv, json, xml.",
        )

    content = await file.read()
    try:
        tickets, summary = parser(content)
    except RowParseError as exc:
        raise HTTPException(status_code=422, detail=str(exc)) from exc

    for ticket in tickets:
        if auto_classify:
            _apply_classification(ticket)
        store.create(ticket)

    return summary


@router.get("", response_model=list[Ticket])
def list_tickets(filters: TicketFilters = Depends()):
    return store.list(filters)


@router.get("/{ticket_id}", response_model=Ticket)
def get_ticket(ticket_id: UUID):
    try:
        return store.get(ticket_id)
    except TicketNotFoundError as exc:
        raise HTTPException(status_code=404, detail=str(exc)) from exc


@router.put("/{ticket_id}", response_model=Ticket)
def update_ticket(ticket_id: UUID, payload: TicketUpdate):
    try:
        existing = store.get(ticket_id)
    except TicketNotFoundError as exc:
        raise HTTPException(status_code=404, detail=str(exc)) from exc

    updates = payload.model_dump(exclude_unset=True)
    if "category" in updates or "priority" in updates:
        existing.classification_overridden = True

    merged = existing.model_copy(update=updates)
    return store.update(ticket_id, merged)


@router.delete("/{ticket_id}", status_code=204)
def delete_ticket(ticket_id: UUID):
    try:
        store.delete(ticket_id)
    except TicketNotFoundError as exc:
        raise HTTPException(status_code=404, detail=str(exc)) from exc


@router.post("/{ticket_id}/auto-classify", response_model=ClassificationResult)
def auto_classify_ticket(ticket_id: UUID):
    try:
        ticket = store.get(ticket_id)
    except TicketNotFoundError as exc:
        raise HTTPException(status_code=404, detail=str(exc)) from exc

    result = classify_ticket(ticket.subject, ticket.description)

    if not ticket.classification_overridden:
        ticket.category = result.category
        ticket.priority = result.priority
        ticket.classification_confidence = result.confidence
        store.update(ticket_id, ticket)

    return result
