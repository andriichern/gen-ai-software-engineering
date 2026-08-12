"""API Gateway: drives submitted transactions through the stage services in
the order configured in gateway/config.json (read once at startup), then
always calls Reporting last. Reporting is never part of the reorderable
list. Stateless: writes nothing into shared/, reads nothing from shared/.

Two submission endpoints, differing only in arity:

  POST /process        one transaction object  -> one result object
  POST /process/batch  an array of them        -> an array of those results

Both drive each transaction through the same chain, in the same configured
order, and return the same per-transaction shape - the batch response is
the single response repeated, never a different or aggregated one. There is
no run summary: Reporting is called once per transaction, keeping the
request/response contract identical across all five stage services.

Failure handling: an unreachable/erroring stage service is retried 3 times,
then skipped (recorded as not-run) and the chain continues - never failing
the whole request, or the rest of a batch, over one dead stage.
"""
from __future__ import annotations

import json
import time
from pathlib import Path

import httpx
from fastapi import FastAPI
from pydantic import BaseModel

CONFIG_PATH = Path(__file__).resolve().parent / "config.json"
RETRY_ATTEMPTS = 3
REQUEST_TIMEOUT = 5.0

RESULT_KEY_BY_STAGE = {
    "validation": "validation_result",
    "fraud_detection": "fraud_result",
    "compliance": "compliance_result",
    "settlement": "settlement_result",
}


def load_config() -> dict:
    return json.loads(CONFIG_PATH.read_text())


# Read once at startup, per the spec: "A configuration file read at startup
# lists the 4 reorderable stages ... Changing that file changes the order;
# nothing else does." The gateway process must be restarted to pick up a
# config change - it is never re-read mid-run.
CONFIG = load_config()

app = FastAPI(title="pipeline-gateway")


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


def _call_stage(client: httpx.Client, url: str, path: str, transaction: dict, context: dict) -> dict | None:
    """POSTs to a stage service, retrying up to RETRY_ATTEMPTS times. Returns
    the parsed result dict on success, or None if every attempt failed."""
    payload = {"transaction": transaction, "context": context}
    for attempt in range(1, RETRY_ATTEMPTS + 1):
        try:
            response = client.post(f"{url}{path}", json=payload, timeout=REQUEST_TIMEOUT)
            response.raise_for_status()
            return response.json()["result"]
        except (httpx.HTTPError, KeyError):
            if attempt < RETRY_ATTEMPTS:
                time.sleep(0.1)
    return None


def _process_one(client: httpx.Client, transaction_data: dict) -> dict:
    """Drives one transaction through the configured order, then Reporting.
    The single source of chain logic: both endpoints go through here, so a
    batch can never diverge from a single submission."""
    context: dict = {}
    not_run: list[str] = []

    for stage in CONFIG["order"]:
        service = CONFIG["services"][stage]
        result = _call_stage(client, service["url"], service["path"], transaction_data, context)
        if result is None:
            not_run.append(stage)
            continue
        context[RESULT_KEY_BY_STAGE[stage]] = result

    reporting = CONFIG["reporting"]
    reporting_result = _call_stage(client, reporting["url"], reporting["path"], transaction_data, context)

    return {
        "transaction_id": transaction_data["transaction_id"],
        "context": context,
        "stages_not_run": not_run,
        "report": reporting_result,
    }


@app.post("/process")
def process(transaction: TransactionIn) -> dict:
    with httpx.Client() as client:
        return _process_one(client, transaction.model_dump())


@app.post("/process/batch")
def process_batch(transactions: list[TransactionIn]) -> list[dict]:
    # One client for the whole batch; transactions are processed in the order
    # submitted, each through the full chain, independently of the others.
    with httpx.Client() as client:
        return [_process_one(client, transaction.model_dump()) for transaction in transactions]
