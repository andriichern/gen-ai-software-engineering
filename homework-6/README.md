# Transaction Processing Pipeline

**Student:** Andrii Chernenko
**Date:** 12.08.2026
**AI tools used:** Claude Code, with the custom agents `documentation`, `pipeline-codegen`, `skills-hooks`, `specification`, and `tests-codegen` (`.claude/agents/`); the skills `run-complete-flow`, `run-pipeline`, `validate-transactions`, and `write-spec` (`.claude/skills/`); the `context7` and `pipeline-status` MCP servers (`.mcp.json`); and a pre-push coverage-gate hook (`.claude/settings.json`).

## Overview

The system processes financial transaction records through a fixed sequence of stages — Validation, Fraud Detection, Compliance Check, Settlement Processing, and Reporting — annotating each record with the outcome of every stage it passes through and producing one final verdict per transaction (SETTLED, REJECTED, HELD, or INCOMPLETE). Input is a JSON list of transaction records (defaulting to `sample-transactions.json`); each record carries an ID, timestamp, source and destination accounts, a decimal amount and ISO 4217 currency, a transaction type, and optional metadata such as country and channel.

Records are never dropped or terminated early — every record traverses every stage, and adverse findings (a fraud score, a compliance hold) are recorded as annotations, not rejections. The same five stage functions can be run two ways: end to end through a standalone orchestrator that writes intermediate and final state to a `shared/` file tree, or individually over HTTP through a set of stage services fronted by a gateway that submits one transaction at a time and returns its accumulated results.

## Pipeline stages

- **Validation** — checks each transaction for required fields, a valid decimal `amount`, an ISO 4217 `currency`, and a valid ISO 8601 UTC `timestamp`; records a pass/fail outcome with a reason. Also supports a standalone, read-only mode that checks an input source without touching `shared/`.
- **Fraud Detection** — scores each transaction 0.00–1.00 from three weighted, additive factors (high-value amount, cross-border mismatch, unusual-hour timing) and flags it for review at a score of 0.50 or higher; it only flags, it never rejects.
- **Compliance Check** — applies GDPR / Data Protection Act 2018 rules; a flagged or non-compliant record is held for human review (never auto-rejected), per GDPR Article 22.
- **Settlement Processing** — settles records that passed Compliance Check by assigning a settlement reference and timestamp in an internal simulated ledger; held or compliance-absent records are marked not-settled with a reason.
- **Reporting** — the terminal stage; computes each transaction's final verdict from the accumulated stage outcomes by a pinned precedence rule, and is the sole writer of `shared/results/`, `shared/report.json`, and the stage tallies in `shared/status.json`.

## Architecture

```
sample-transactions.json (or --source)
              |
              v
   ORCHESTRATOR (orchestrator.py) -- fixed order, no service layer, no shared/ config
              |
              v
   shared/input/ --> [Validation] --> [Fraud Detection] --> [Compliance] --> [Settlement] --> [Reporting]
                        (shared/processing/ + shared/output/ carry each transaction between stages)
                                                                                    |
                                                                                    v
                                                          shared/results/*.json, shared/report.json, shared/status.json

   -------------------------------------------------------------------------------------------------

   SERVICE LAYER (independent of the orchestrator; reads/writes nothing in shared/)

   client --> gateway/main.py (POST /process)
                     |  order read once at startup from gateway/config.json
                     v
        [validation :8001] -> [fraud_detection :8002] -> [compliance :8003] -> [settlement :8004]
                     |  (order above is config.json's default; gateway.config.json is authoritative)
                     v
                        always last, not reorderable
                        [reporting :8005]
                     |
                     v
              JSON response: transaction_id, context, stages_not_run, report
```

The bullet order above is the orchestrator's hardcoded order (`STAGE_NAMES` in `orchestrator.py`): Validation, Fraud Detection, Compliance, Settlement, Reporting. The gateway's order for the four reorderable stages is a separate, independent setting read from `gateway/config.json`'s `"order"` list; Reporting is always invoked last by the gateway and is never part of that list. The orchestrator never reads `gateway/config.json`, and the gateway never touches `shared/` — the pipeline runs completely standalone, with no dependency on the service layer.

## Service layer

Each of the five stages is also exposed as its own stateless FastAPI HTTP service under `services/<stage>/main.py` (`validation`, `fraud_detection`, `compliance`, `settlement`, `reporting`), each a thin wrapper that imports and calls the corresponding `pipeline/` function unchanged. All five share one request/response contract (`lib/service_schemas.py`): a `StageRequest` of `{transaction, context}` and a `StageResponse` of `{stage, result}`.

The gateway (`gateway/main.py`, `POST /process`) accepts a single transaction, drives it through the stage services in the order declared by `gateway/config.json`, always calling Reporting last, and returns the accumulated context, any stages that did not run, and the reporting result. A stage service that is unreachable or errors is retried 3 times, then skipped, which forces that transaction's verdict to INCOMPLETE. Both the services and the gateway are stateless: nothing is read from or written to `shared/`, so the pipeline runs standalone with none of this layer present.

## Tech stack

| Component | Language / runtime | Frameworks & key libraries |
|---|---|---|
| Pipeline (`pipeline/`, `lib/`, `orchestrator.py`) | Python (3.14.6 on this machine; no version pin found in a manifest) | Standard library (`decimal`, `pathlib`); `pycountry` for ISO 4217 currency validation; `requests` for the live exchange-rate client |
| Service layer (`services/`, `gateway/`) | Python (same manifest, `requirements.txt`, as the pipeline) | `fastapi` for routing and request/response models; `httpx` for the gateway's outbound calls to stage services |
| MCP server (`mcp/server.py`) | Python | `fastmcp` |
| UI (`ui/`) | JavaScript (SvelteKit project) | `svelte`, `@sveltejs/kit`, `vite`, `tailwindcss` (per `ui/package.json`) |

All Python components share one manifest, `requirements.txt`, at the project root (`pycountry`, `requests`, `fastmcp`, `pytest`, `pytest-cov`, `fastapi`, `httpx`).
