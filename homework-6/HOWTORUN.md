# How to Run

## 1. Setup

**Pipeline / tests** — prerequisite: Python 3 (`python3`). Install dependencies from the `homework-6` root:

```bash
bash scripts/setup.sh
```

(runs `pip3 install -r requirements.txt`, covering `pycountry`, `requests`, `fastmcp`, `pytest`, `pytest-cov`).

**UI** — prerequisite: Node.js. Install dependencies from `ui/`:

```bash
cd ui
npm install
```

## 2. Run the pipeline

From the `homework-6` root:

```bash
python3 orchestrator.py [--input sample-transactions.json]
```

Wipes and recreates `shared/`, ingests the dataset, fetches live exchange rates, and runs the five stages in sequence, printing per-stage progress. Final records land in `shared/results/`, the run summary in `shared/report.json`.

## 3. Run the MCP server

From the `homework-6` root:

```bash
uv run --no-project --with fastmcp mcp/server.py
```

(this is the command declared for the `pipeline-status` server in `.mcp.json`; requires `uv`). Starts a stdio MCP server exposing the `get_transaction_status` and `list_pipeline_results` tools and the `pipeline://summary` resource, read-only against whatever is currently in `shared/`. It waits for an MCP client connection rather than printing output.

## 4. Run the UI

From `ui/`:

```bash
npm run dev
```

Starts the Vite/SvelteKit development server for the front-end.

## 5. Run the tests

From the `homework-6` root:

```bash
bash scripts/run_tests.sh
```

Runs the `pytest` suite (`tests/`) with coverage over `pipeline`, `lib` and `orchestrator` (the UI is excluded per `.coveragerc`), producing `coverage_report.json` and an HTML report in `htmlcov/`. Exits non-zero if any test fails or if coverage falls below the 80% threshold (the default in this script, matching the threshold set in `.claude/settings.json`). Pass `--coverage N` to gate at a different threshold.
