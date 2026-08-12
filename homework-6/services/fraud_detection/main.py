"""Fraud Detection stage service: a thin FastAPI wrapper around
pipeline.fraud_detection.score_transaction. No stage rule is
re-implemented here. Stateless: nothing is read from or written to disk or
shared/. Live exchange rates are an external input the scoring factor
needs (not persisted state); if they cannot be fetched, the high-value
factor degrades to not-applicable rather than the request erroring."""
from __future__ import annotations

from fastapi import FastAPI

from lib.exchange_rates import ExchangeRates, fetch_exchange_rates
from lib.models import StageContext, Transaction
from lib.service_schemas import StageRequest, StageResponse
from pipeline.fraud_detection import score_transaction

app = FastAPI(title="fraud-detection-service")

_rates_cache: ExchangeRates | None = None


def _get_rates() -> ExchangeRates:
    global _rates_cache
    if _rates_cache is None:
        try:
            _rates_cache = fetch_exchange_rates(retries=1, delay_seconds=0)
        except RuntimeError:
            _rates_cache = ExchangeRates(base="USD", rates={})
    return _rates_cache


@app.post("/score", response_model=StageResponse)
def score(request: StageRequest) -> StageResponse:
    record = Transaction.from_dict(request.transaction.model_dump())
    context = StageContext.from_dict(request.context.model_dump())
    result = score_transaction(record, context, _get_rates())
    return StageResponse(stage="fraud_detection", result=result.to_dict())
