# Transaction Processing Pipeline

**Student:** Andrii Chernenko

**Date:** 12.08.2026

**AI tools used:** Claude Code, with the project's own `.claude/agents/` definitions (`documentation`, `pipeline-codegen`, `skills-hooks`, `specification`, `tests-codegen`, `tests-docs`) and `.claude/skills/` (`run-pipeline`, `validate-transactions`, `write-spec`); the `context7` MCP server for library documentation lookups; a custom `pipeline-status` MCP server (built on FastMCP) for read-only pipeline querying; and a `PreToolUse` hook that gates `git push`/`gh pr create` on a coverage threshold.

## Overview

This system takes a JSON array of raw financial transaction records and carries each one through a five-stage file-based pipeline — validation, fraud scoring, compliance screening, settlement and reporting — publishing an auditable outcome for every transaction. Each stage exchanges records through a shared working directory tree rather than direct function calls, associating records by `transaction_id` at every boundary.

Input is a transaction dataset (defaulting to `sample-transactions.json`) where each record carries an identifier, timestamp, source/destination accounts, a decimal amount and currency, a transaction type, description and open metadata. Output is one final JSON record per transaction in `shared/results/`, combining the original fields with every stage's result and a `final_status` of `rejected`, `held`, `settlement_refused` or `settled`, plus an aggregate run summary in `shared/report.json` and a live-updated `shared/status.json`.

## Pipeline stages

- **Validation** (`pipeline/validation.py`) — confirms every required field is present and correctly typed, that `amount` parses as a decimal, and that `currency` is a genuine ISO 4217 code. Passing records continue to Fraud Detection; failing records are written straight to `shared/results/` with a rejection reason and go no further. Also exposes a standalone dry-run that checks a dataset without writing anything.
- **Fraud Detection** (`pipeline/fraud_detection.py`) — scores every validated transaction with three weighted, explainable factors (high-value amount, cross-border/country mismatch, unusual-hour timing), converting amounts to USD using fetched exchange rates. Flags at a score of 0.50 or above but never rejects; every transaction continues to Compliance.
- **Compliance Check** (`pipeline/compliance.py`) — applies a GDPR / Data Protection Act 2018 baseline to every record. A fraud-flagged transaction is held for human review rather than auto-rejected; cleared transactions continue to Settlement, and held/rejected ones are finalized to `shared/results/`.
- **Settlement Processing** (`pipeline/settlement.py`) — settles compliance-cleared transactions against an internal simulated ledger, generating a settlement reference and UTC timestamp with no external call. Refuses (and finalizes) any record whose compliance result is missing or not cleared.
- **Reporting** (`pipeline/reporting.py`) — aggregates every processed record (settled and already-terminal ones) into the run summary written to `shared/report.json`, then joins each settled transaction's original fields with its accumulated stage results and writes the final record to `shared/results/`.

The orchestrator (`orchestrator.py`) wipes and recreates the `shared/` tree, copies the input dataset into `shared/input/`, fetches live exchange rates once for the currencies present in the input, then runs the five stages above in this fixed order, in-process, updating `shared/status.json` as each stage starts and completes.

## Architecture diagram

```
Input dataset (sample-transactions.json)
            |
            v
     shared/input/  (copied, read-only for the run)
            |
            v
     +----------------+
     |   Validation   |----fail----> shared/results/ (rejected)
     +----------------+
            | pass
            v
     +------------------+
     | Fraud Detection  |  (scores, flags, never rejects)
     +------------------+
            |
            v
     +----------------+
     |   Compliance   |----held/rejected----> shared/results/
     +----------------+
            | cleared
            v
     +----------------+
     |   Settlement   |----refused----> shared/results/
     +----------------+
            | settled
            v
     +----------------+
     |   Reporting    |----> shared/report.json  (run summary)
     +----------------+
            |
            v
     shared/results/  (final per-transaction record)
```

`shared/status.json` is updated live throughout by the orchestrator as each stage starts and completes.

## Tech stack

| Component                                         | Language / runtime                                                                                     | Frameworks & key libraries                                                                                                                              |
| ------------------------------------------------- | ------------------------------------------------------------------------------------------------------ | ------------------------------------------------------------------------------------------------------------------------------------------------------- |
| Pipeline (`orchestrator.py`, `pipeline/`, `lib/`) | Python 3 (Python 3.14.6 found in this environment; no version is pinned by a file in this folder)      | `pycountry` (ISO 4217 currency validation), `requests` (live exchange-rate fetch with retry), standard library `decimal`, `pathlib`, `uuid`, `argparse` |
| MCP server (`mcp/server.py`)                      | Python 3                                                                                               | `fastmcp` (FastMCP), standard library `json`, `os`, `pathlib`                                                                                           |
| UI (`ui/`)                                        | JavaScript (Node.js v24.14.1 found in this environment; no version is pinned by a file in this folder) | Svelte 5, SvelteKit 2 (with `@sveltejs/adapter-node`), Vite 5, Tailwind CSS 3, Prettier                                                                 |
