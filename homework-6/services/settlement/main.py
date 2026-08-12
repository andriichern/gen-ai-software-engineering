"""Settlement Processing stage service: a thin FastAPI wrapper around
pipeline.settlement.settle_transaction. No stage rule is re-implemented
here. Stateless: nothing is read from or written to disk or shared/."""
from __future__ import annotations

from fastapi import FastAPI

from lib.models import StageContext, Transaction
from lib.service_schemas import StageRequest, StageResponse
from pipeline.settlement import settle_transaction

app = FastAPI(title="settlement-service")


@app.post("/settle", response_model=StageResponse)
def settle(request: StageRequest) -> StageResponse:
    record = Transaction.from_dict(request.transaction.model_dump())
    context = StageContext.from_dict(request.context.model_dump())
    result = settle_transaction(record, context)
    return StageResponse(stage="settlement", result=result.to_dict())
