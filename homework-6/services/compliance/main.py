"""Compliance Check stage service: a thin FastAPI wrapper around
pipeline.compliance.check_compliance. No stage rule is re-implemented
here. Stateless: nothing is read from or written to disk or shared/."""
from __future__ import annotations

from fastapi import FastAPI

from lib.models import StageContext, Transaction
from lib.service_schemas import StageRequest, StageResponse
from pipeline.compliance import check_compliance

app = FastAPI(title="compliance-service")


@app.post("/check", response_model=StageResponse)
def check(request: StageRequest) -> StageResponse:
    record = Transaction.from_dict(request.transaction.model_dump())
    context = StageContext.from_dict(request.context.model_dump())
    result = check_compliance(record, context)
    return StageResponse(stage="compliance", result=result.to_dict())
