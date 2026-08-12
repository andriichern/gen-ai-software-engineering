"""Reporting stage service: a thin FastAPI wrapper around
pipeline.reporting.build_report. No verdict rule is re-implemented here -
build_report is reused unchanged, called with a single-transaction batch so
the uniform per-transaction request/response contract still holds. Stateless:
nothing is read from or written to disk or shared/."""
from __future__ import annotations

from fastapi import FastAPI

from lib.models import ProcessedTransaction, StageContext, Transaction
from lib.service_schemas import StageRequest, StageResponse
from pipeline.reporting import build_report

app = FastAPI(title="reporting-service")


@app.post("/report", response_model=StageResponse)
def report(request: StageRequest) -> StageResponse:
    record = Transaction.from_dict(request.transaction.model_dump())
    context = StageContext.from_dict(request.context.model_dump())
    processed = ProcessedTransaction(
        transaction_id=record.transaction_id,
        amount=record.amount,
        currency=record.currency,
        context=context,
    )
    run_report = build_report([processed])
    verdict_record = run_report.verdicts[0]
    result = {
        "transaction_id": verdict_record.transaction_id,
        "verdict": verdict_record.verdict,
        "fraud_flagged": verdict_record.fraud_flagged,
        "reason": verdict_record.reason,
        "stage_outcomes": verdict_record.stage_outcomes,
    }
    return StageResponse(stage="reporting", result=result)
