"""Validation stage service: a thin FastAPI wrapper around
pipeline.validation.validate_transaction. No stage rule is re-implemented
here. Stateless: nothing is read from or written to disk or shared/."""
from __future__ import annotations

from fastapi import FastAPI

from lib.models import StageContext, Transaction
from lib.service_schemas import StageRequest, StageResponse
from pipeline.validation import validate_transaction

app = FastAPI(title="validation-service")


@app.post("/validate", response_model=StageResponse)
def validate(request: StageRequest) -> StageResponse:
    record = Transaction.from_dict(request.transaction.model_dump())
    context = StageContext.from_dict(request.context.model_dump())
    result = validate_transaction(record, context)
    return StageResponse(stage="validation", result=result.to_dict())
