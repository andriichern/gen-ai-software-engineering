"""Uniform HTTP request/response contract shared by all 5 stage services and
consumed by the gateway. Kept here (not duplicated per service) because it is
genuinely reused by every service and the gateway."""
from __future__ import annotations

from typing import Optional

from pydantic import BaseModel


class TransactionIn(BaseModel):
    transaction_id: str
    timestamp: str
    source_account: str
    destination_account: str
    amount: str
    currency: str
    transaction_type: str
    description: str = ""
    metadata: dict = {}


class StageContextIn(BaseModel):
    """Any entry may be absent — a partial or empty context is valid input."""

    validation_result: Optional[dict] = None
    fraud_result: Optional[dict] = None
    compliance_result: Optional[dict] = None
    settlement_result: Optional[dict] = None


class StageRequest(BaseModel):
    """Identical request shape across all 5 services."""

    transaction: TransactionIn
    context: StageContextIn = StageContextIn()


class StageResponse(BaseModel):
    """Identical response envelope across all 5 services: the stage name and
    that stage's own result payload, nothing else."""

    stage: str
    result: dict
