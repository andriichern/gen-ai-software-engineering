"""In-memory storage for support tickets."""
from __future__ import annotations

from datetime import datetime
from typing import Optional
from uuid import UUID

from ..models import Category, Priority, Status, Ticket


class TicketNotFoundError(Exception):
    def __init__(self, ticket_id: UUID):
        self.ticket_id = ticket_id
        super().__init__(f"Ticket {ticket_id} not found")


class TicketStore:
    """Dict-backed ticket storage. No persistence across process restarts."""

    def __init__(self) -> None:
        self._tickets: dict[UUID, Ticket] = {}

    def create(self, ticket: Ticket) -> Ticket:
        self._tickets[ticket.id] = ticket
        return ticket

    def get(self, ticket_id: UUID) -> Ticket:
        ticket = self._tickets.get(ticket_id)
        if ticket is None:
            raise TicketNotFoundError(ticket_id)
        return ticket

    def list(
        self,
        category: Optional[Category] = None,
        priority: Optional[Priority] = None,
        status: Optional[Status] = None,
        customer_id: Optional[str] = None,
        assigned_to: Optional[str] = None,
        tag: Optional[str] = None,
    ) -> list[Ticket]:
        results = list(self._tickets.values())
        if category is not None:
            results = [t for t in results if t.category == category]
        if priority is not None:
            results = [t for t in results if t.priority == priority]
        if status is not None:
            results = [t for t in results if t.status == status]
        if customer_id is not None:
            results = [t for t in results if t.customer_id == customer_id]
        if assigned_to is not None:
            results = [t for t in results if t.assigned_to == assigned_to]
        if tag is not None:
            results = [t for t in results if tag in t.tags]
        return results

    def update(self, ticket_id: UUID, updated: Ticket) -> Ticket:
        if ticket_id not in self._tickets:
            raise TicketNotFoundError(ticket_id)
        updated.updated_at = datetime.utcnow()
        if updated.status in (Status.RESOLVED, Status.CLOSED) and updated.resolved_at is None:
            updated.resolved_at = updated.updated_at
        self._tickets[ticket_id] = updated
        return updated

    def delete(self, ticket_id: UUID) -> None:
        if ticket_id not in self._tickets:
            raise TicketNotFoundError(ticket_id)
        del self._tickets[ticket_id]

    def clear(self) -> None:
        """Reset all state. Used by tests."""
        self._tickets.clear()
