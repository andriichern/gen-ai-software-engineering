# How to Run

## 1. Setup

**Pipeline / service layer / MCP server (Python, shared `requirements.txt`)**
From the `homework-6` root:
```
bash scripts/setup.sh
```
Installs `pycountry`, `requests`, `fastmcp`, `pytest`, `pytest-cov`, `fastapi`, `httpx` via `pip3 install -r requirements.txt`.

**UI (`ui/`, SvelteKit/npm project)**
From `homework-6/ui`:
```
npm install
```
Installs the dependencies declared in `ui/package.json`.

## 2. Run the pipeline

From the `homework-6` root:
```
python3 orchestrator.py --source sample-transactions.json
```
`--source` defaults to `sample-transactions.json` if omitted. Runs all 5 stages in order and writes `shared/status.json`, `shared/report.json`, and one file per transaction under `shared/results/`.

## 3. Start the service layer

From the `homework-6` root:
```
bash scripts/start-services.sh
```
Launches the 5 stage services (`services/validation` on port 8001, `services/fraud_detection` on 8002, `services/compliance` on 8003, `services/settlement` on 8004, `services/reporting` on 8005) and the gateway (`gateway/main.py`) on port 8010, each via `uvicorn`, as background jobs under one shell. Stop them with Ctrl+C in that terminal (terminates the script and its backgrounded `uvicorn` processes).

## 4. Submit a request to the gateway

With the service layer running:
```
curl -X POST http://127.0.0.1:8010/process \
  -H "Content-Type: application/json" \
  -d '{
    "transaction_id": "TXN001",
    "timestamp": "2026-03-16T09:00:00Z",
    "source_account": "ACC-1001",
    "destination_account": "ACC-2001",
    "amount": "1500.00",
    "currency": "USD",
    "transaction_type": "transfer",
    "description": "Monthly rent payment",
    "metadata": { "channel": "online", "country": "US" }
  }'
```
The record above is `TXN001` from `sample-transactions.json`, matching the gateway's `TransactionIn` model (`gateway/main.py`). The response is JSON: `{"transaction_id": ..., "context": {...per-stage results...}, "stages_not_run": [...], "report": {...reporting service's result...}}`.

To submit several at once, POST an array to `/process/batch`:
```
curl -X POST http://127.0.0.1:8010/process/batch \
  -H "Content-Type: application/json" \
  -d '[
    {
      "transaction_id": "TXN001",
      "timestamp": "2026-03-16T09:00:00Z",
      "source_account": "ACC-1001",
      "destination_account": "ACC-2001",
      "amount": "1500.00",
      "currency": "USD",
      "transaction_type": "transfer",
      "description": "Monthly rent payment",
      "metadata": { "channel": "online", "country": "US" }
    },
    {
      "transaction_id": "TXN002",
      "timestamp": "2026-03-16T09:15:00Z",
      "source_account": "ACC-1002",
      "destination_account": "ACC-3001",
      "amount": "25000.00",
      "currency": "USD",
      "transaction_type": "wire_transfer",
      "description": "Equipment purchase",
      "metadata": { "channel": "branch", "country": "US" }
    }
  ]'
```
Each element takes the same shape as the single-transaction body. The response is a JSON array of the same per-transaction objects `/process` returns, one per submitted record, in submission order. No aggregate summary is returned; each transaction is processed independently of the others in the batch.

## 5. Change the stage order

The gateway's order is declared in `gateway/config.json`, currently:
```json
{
  "order": ["validation", "fraud_detection", "compliance", "settlement"]
}
```
Reporting is always called last and is not part of this list. Editing this file changes only the gateway's order (re-read at gateway startup); the pipeline's own order is hardcoded in `orchestrator.py` and is unaffected.

## 6. Run the MCP server

From the `homework-6` root:
```
uv run --no-project --with fastmcp mcp/server.py
```
Starts the `pipeline-status` MCP server over stdio (as declared in `.mcp.json`), exposing read-only tools/resources over the contents of `shared/`. It does not run or mutate the pipeline.

## 7. Run the UI / front-end

From `homework-6/ui`:
```
npm run dev
```
Runs the `vite dev` script declared in `ui/package.json`, starting the SvelteKit dev server.

## 8. Run the tests

From the `homework-6` root:
```
bash scripts/run_tests.sh
```
Runs `pytest tests/` with coverage (source scope set by `.coveragerc`: `pipeline`, `lib`, `orchestrator`, `services`, `gateway`; `ui` is excluded), writing `coverage_report.json` and `htmlcov/`. The script gates at an 80% coverage threshold by default (`--coverage N` to override), matching the 80% threshold configured in `.claude/settings.json`.
