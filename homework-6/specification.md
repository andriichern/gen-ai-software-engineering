# Specification — Transaction Processing Pipeline

## 1. High-Level Objective

Process financial transactions through a fixed sequence of stages (Validation, Fraud Detection, Compliance Check, Settlement Processing, and Reporting), annotating each record with stage outcomes and publishing a final verdict for every transaction via file-based orchestration.

## 2. Mid-Level Objectives

1. All transactions are processed through exactly 5 stages in the orchestrator's fixed order; stages are independent and communicate only through the `shared/` file tree.
2. Each transaction receives exactly one final verdict from Reporting — SETTLED, REJECTED, HELD, or INCOMPLETE — based on pinned precedence rules and the outcomes accumulated from each stage.
3. Validation can run standalone (read-only, non-mutating) to check an input transaction source for validity without modifying any run state, file tree, or processing records.
4. Stages annotate transactions without ever terminating them; every record traverses every stage, and adverse findings are recorded as outcomes, never as rejections or removals from the flow.
5. The pipeline publishes run state via `status.json` (per-stage timestamps and counts) and `report.json` (aggregate summary) — self-describing plain JSON, allowing external observation without coupling to the pipeline or parsing logs.
6. PII in transaction records and audit trails is handled per GDPR requirements; audit and settlement records are retained for 5 years under GDPR's "legal obligation" lawful basis.

## 3. Implementation Notes

- **Decimal handling**: monetary values (`amount`) must always be represented as decimal types, never binary floats, to prevent rounding errors. In Python, this is the `Decimal` type from the `decimal` module.
- **Currency codes**: must comply with ISO 4217 (e.g., `USD`, `GBP`); sample data may include invalid codes as test cases, which Validation must catch and report.
- **Negative amounts**: are valid and represent refunds or reversals; they are not malformed input.
- **Time handling**: all timing logic, including the fraud-detection unusual-hour window (06:00–22:00 UTC), operates in UTC only — no local-timezone conversion, DST handling, or per-country offset tables.
- **Association**: records are associated by `transaction_id`, never by file order or read sequence.
- **Audit trail**: every transaction includes its ID, processing timestamp, stage name, and outcome in the audit log; no PII (account numbers, customer names, identifying data) may appear in plaintext in logs.
- **Compliance regime**: GDPR and the Data Protection Act 2018, applied uniformly to all records regardless of origin as a privacy-by-design choice. Per GDPR Article 22, automated decisions with legal or significant effects must include a hold for human review rather than automated rejection.
- **Fraud scoring**: uses a transparent, weighted rule-based approach:
  - High-value amount (weight 0.50): triggered when absolute `amount` >= $10,000 USD equivalent.
  - Cross-border mismatch (weight 0.30): triggered when source/destination account countries differ, or `metadata.country` differs from the baseline country (GB, unless transaction data implies otherwise).
  - Unusual-hour timing (weight 0.20): triggered when `timestamp` falls outside 06:00–22:00 UTC.
  - Scores cap at 1.00 and flag for review when >= 0.50. Fraud Detection flags only; Compliance Check decides whether to hold or reject, per GDPR Article 22.
- **Settlement mechanism**: by default, an internal simulated ledger without external network calls, marking transactions settled with a generated reference and timestamp. Records containing account or PII data are retained for 5 years under GDPR's legal-obligation basis, then purged or anonymized.
- **Performance targets**: the architecture is designed to sustain up to 100,000 transactions per second with 99.99% uptime, with no artificial blocking I/O or single-threaded bottlenecks.

## 4. Context

### Beginning Context

The pipeline ingests transaction records from an input transaction source (defaulting to `sample-transactions.json` if not otherwise specified). Each record follows the default schema:

```json
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
}
```

Before the run, `shared/` exists but is empty (or the orchestrator creates it if absent).

### Ending Context

After a successful run, `shared/` contains:

- `input/` — emptied of transaction files (all records have been read and processed; the directory is retained).
- `processing/` — cleared; no stage work-in-progress remains.
- `output/` — contains messages from the last completed stage, awaiting the next stage.
- `results/` — exactly one file per processed transaction, written solely by Reporting, holding the final record with accumulated stage outcomes, final verdict, and audit trail.
- `status.json` — per-stage start/completion timestamps and counts (processed, passed, failed), written live as each stage starts and completes.
- `report.json` — aggregate run summary: total transactions, valid/invalid counts, fraud-flag counts, compliance-hold counts, settled counts, and any run-level errors or notes.

## 5. Low-Level Tasks

Task: Validation Stage
Prompt: "Write a Validation stage for a transaction processing pipeline. The stage must check each input transaction for well-formedness and required fields (transaction_id, timestamp, source_account, destination_account, amount, currency, transaction_type). Validate that amount is a valid decimal string, currency is a valid ISO 4217 code, and timestamp is a valid ISO 8601 UTC datetime. Record the validation outcome (pass or fail with reason) for each transaction. Return a ValidationResult with the outcome and any error messages. Additionally, support a standalone, read-only mode that checks all input records without touching the shared/ tree, reporting pass/fail with reasons and aggregate counts. Ensure the function handles empty or partial context gracefully, since validation depends only on the record itself."
File to CREATE: `pipeline/validation.py`
Function to CREATE: `validate_transaction(record: Transaction, context: StageContext) -> ValidationResult`
Details: Validation checks that every input transaction has the required fields (`transaction_id`, `timestamp`, `source_account`, `destination_account`, `amount`, `currency`, `transaction_type`), that `amount` is a valid decimal string (never a float), `currency` matches ISO 4217, and `timestamp` is valid ISO 8601 UTC. Records failing validation are marked with a reason. The stage also supports a standalone invocation mode (non-mutating, read-only) to check the input source directly without processing — it reads every record, applies the same validation rules, reports each record's ID, verdict, and failure reason, and returns total, valid, and invalid counts. This standalone capability changes nothing: no part of `shared/` is read, created, or modified; no record is altered; no state is written anywhere. The state of any run in progress or already finished remains untouched. Validation rules depend only on the record itself, never on prior stage results, so it always produces a valid outcome and never records any rule as *not-applicable*.

Task: Fraud Detection Stage
Prompt: "Write a Fraud Detection stage for a transaction processing pipeline. The stage must score each validated transaction on a scale of 0.00–1.00 using three weighted factors: high-value amount (weight 0.50, threshold $10,000 USD equivalent), cross-border mismatch (weight 0.30, triggered when source/destination countries differ or metadata.country differs from baseline country GB), and unusual-hour timing (weight 0.20, triggered when timestamp falls outside 06:00–22:00 UTC). All weights are additive and capped at 1.00. Flag the record for review when the score is >= 0.50. Output each record with its score and flag status. Fraud Detection flags only; it never rejects or blocks. Return a FraudResult with score, flags, and outcome. Ensure the function handles empty or partial context gracefully — if validation is absent from the context, record fraud detection as not-applicable."
File to CREATE: `pipeline/fraud_detection.py`
Function to CREATE: `score_transaction(record: Transaction, context: StageContext, rates: ExchangeRates) -> FraudResult`
Details: Fraud Detection computes a transparent, weighted risk score for every transaction using three factors: (1) high-value amount (absolute `amount` >= $10,000 USD equivalent, 0.50 weight); (2) cross-border mismatch (source/destination account countries differ, or `metadata.country` differs from baseline GB, 0.30 weight); (3) unusual-hour timing in UTC (timestamp outside 06:00–22:00, 0.20 weight). Scores are additive, capped at 1.00. Records scoring >= 0.50 are flagged for review per GDPR Article 22. A fraud flag is never a verdict; it is an annotation recorded alongside whatever final verdict Reporting computes. Fraud Detection flags only; it never auto-rejects or auto-blocks. When context is empty or partial (e.g., Validation has not run), Fraud Detection records rules it cannot evaluate as *not-applicable*, naming what was missing, and continues.

Task: Compliance Check Stage
Prompt: "Write a Compliance Check stage for a transaction processing pipeline. The stage applies GDPR and the Data Protection Act 2018 rules uniformly to all records. For any record flagged by Fraud Detection or triggering a compliance rule (e.g. PII handling, audit trail completeness), issue a hold for human review rather than an automated rejection per GDPR Article 22. Record the compliance decision (pass, hold, or not-applicable for missing fraud status) with reason; passed records proceed to Settlement, held records are reported in the final verdict. Return a ComplianceResult with the outcome and any audit notes. Ensure the function handles empty or partial context gracefully — if Fraud Detection is absent, record the fraud-conditional hold rule as not-applicable, naming what was missing."
File to CREATE: `pipeline/compliance.py`
Function to CREATE: `check_compliance(record: Transaction, context: StageContext) -> ComplianceResult`
Details: Compliance Check applies GDPR and Data Protection Act 2018 rules uniformly to every record, regardless of origin. It checks for fraud flags from prior stages and evaluates compliance rules (PII handling, audit trail completeness, cross-border data flow validity). Per GDPR Article 22, it must never make a solely automated decision with legal or significant effect; instead, it issues a hold for human review of flagged or non-compliant records, never an automated rejection. Passed records are marked and proceed to Settlement; held records are reported in the audit trail and marked for review in the final verdict. When Validation is absent from the context, Compliance Check evaluates all non-validation-dependent rules and records validation-conditional rules as *not-applicable*. When Fraud Detection is absent, Compliance Check records the fraud-conditional hold rule as *not-applicable*, naming the missing annotation. It never invents or substitutes values, and never treats absence as a clean pass.

Task: Settlement Processing Stage
Prompt: "Write a Settlement Processing stage for a transaction processing pipeline. The stage settles each transaction that passed Compliance Check by assigning a unique settlement reference and timestamp, recording the settlement in an internal simulated ledger, and marking the record settled. Do not make external API calls or network integration — settlement is internal and immediate. Handle records held by Compliance Check by marking them not-settled with reason. Return a SettlementResult with the outcome (settled, not-settled), settlement reference (if settled), settlement timestamp, and any reason for non-settlement. Audit and settlement records containing account or PII data are retained for five years under GDPR's legal-obligation basis, then purged or anonymized. Ensure the function handles empty or partial context gracefully — if Compliance Check is absent from context, record settlement as not-settled, naming that the compliance annotation was missing."
File to CREATE: `pipeline/settlement.py`
Function to CREATE: `settle_transaction(record: Transaction, context: StageContext) -> SettlementResult`
Details: Settlement Processing settles each transaction that passed Compliance Check by assigning a unique settlement reference (e.g., a UUID) and settlement timestamp (distinct from the transaction's own timestamp). It marks the transaction settled in an internal simulated ledger — no external settlement network is invoked; settlement is immediate and internal. If Compliance has held the transaction, settlement marks it *not-settled*, naming the hold reason. If Compliance is absent from the context, settlement records *not-settled*, naming that compliance status is unknown. Audit and settlement records containing PII are retained for 5 years under GDPR's legal-obligation basis, then purged or anonymized. When context is empty or partial, Settlement records rules it cannot evaluate as *not-applicable*, naming what was missing.

Task: Reporting Stage
Prompt: "Write a Reporting stage for a transaction processing pipeline. This stage is always invoked last and is the only stage that writes to the results/ directory. It receives a list of all processed transactions (the whole batch) with their accumulated stage outcomes. For each transaction, compute a single final verdict from the accumulated annotations using the pinned precedence rules: (1) if any stage did not run, verdict is INCOMPLETE; (2) if validation failed, verdict is REJECTED (validation); (3) if compliance rejected, verdict is REJECTED (compliance); (4) if compliance held, verdict is HELD; (5) if all checks passed and settlement completed, verdict is SETTLED; otherwise INCOMPLETE. A fraud flag is never a verdict; it is an attribute of the final verdict. Write each final record to results/ (one file per transaction) with transaction_id, verdict, fraud_flagged (boolean), stage_outcomes (all stage results), and reason (if rejected or held). Also write aggregate summary to report.json: total transactions, settled, rejected, held, incomplete counts, and a brief summary. Ensure status.json contains per-stage start/completion timestamps and counts (processed, passed, failed)."
File to CREATE: `pipeline/reporting.py`
Function to CREATE: `build_report(records: list[ProcessedTransaction]) -> RunReport`
Details: Reporting is the terminal stage and runs last. It receives the complete batch of processed transactions, each with accumulated outcomes from all prior stages. For each transaction, it computes a single final verdict using the pinned precedence table:

| Precedence | Condition | Verdict |
|---|---|---|
| 1 | any stage did not run | `INCOMPLETE` |
| 2 | validation failed | `REJECTED` (validation) |
| 3 | compliance rejected | `REJECTED` (compliance) |
| 4 | compliance held | `HELD` |
| 5 | settled | `SETTLED` |
| — | none of the above | `INCOMPLETE` |

A fraud flag is never a verdict; it is recorded as an attribute of whatever verdict applies. Reporting is the sole owner of `shared/results/` and writes exactly one file per transaction with transaction_id, final verdict, fraud_flagged status, all accumulated stage outcomes, and a reason (if rejected or held). Reporting also writes `shared/report.json` with aggregate counts (total, settled, rejected, held, incomplete) and a summary of the run. Reporting ensures `shared/status.json` contains per-stage start/completion timestamps and counts (processed, passed, failed) for external observation without log parsing. Every transaction receives a final verdict; if any stage is absent from the accumulated results, the precedence rule dictates INCOMPLETE.

---

## Stage Services

Each of the 5 stages is additionally exposed as its own independently deployable HTTP service, wrapping the stage's core function without reimplementing it.

**Purpose:** Thin wrappers around the pipeline's stage functions, allowing external callers to invoke stages individually via HTTP.

**Location:** One directory per service under `services/`, named for the stage (`validation`, `fraud_detection`, `compliance`, `settlement`, `reporting`).

**Contract:** Each service accepts a POST request with the transaction record plus accumulated context from prior stages (or an empty context), and returns that stage's own result in the response. A partial or empty context is valid input and yields a *not-applicable* outcome, never an error. The request and response shapes are identical across all 5 services, allowing a caller to treat them interchangeably.

**Constraints:** Services are stateless — nothing is read from or written to disk, the `shared/` tree, or any external persistence. Services never call one another and hold no knowledge of other services or their URLs. Sequencing belongs entirely to the caller.

**Stack:** Python (matching the pipeline) with FastAPI as the HTTP framework. Each service is a thin wrapper importing and calling the corresponding stage function unchanged — there is no second implementation of any stage rule, so a service invocation and an orchestrator run agree on every record.

---

## API Gateway

A single HTTP gateway accepts submitted transactions and drives them through the stage services in a configurable order, returning each transaction's accumulated results and final verdict.

**Purpose:** Orchestrate stage services via HTTP, allowing external clients to submit transactions and receive processed results without running the pipeline CLI.

**Location:** `gateway/` at the project root.

**Configurable order — the gateway's alone:** A configuration file read at startup lists the 4 reorderable stages (Validation, Fraud Detection, Compliance, Settlement) in the order to invoke them, together with each service's base URL. Changing that file changes the order; nothing else does. **Reporting is always invoked last and is never part of the reorderable list.** The orchestrator's fixed order is entirely unaffected by this file and never reads it — the two orders are independent, and the pipeline's is not configurable at all.

**Orchestration, not choreography:** The gateway calls each service in turn, accumulating each result into the context it passes to the next. Services are never asked to forward anything to one another.

**Failure handling:** If a stage service is unreachable or errors, the gateway retries 3 times, then skips that stage and continues the chain, recording that the stage did not run. Per the verdict precedence, a skipped stage makes the transaction's final verdict `INCOMPLETE` — so a lost stage degrades the result honestly rather than failing the request.

**Constraints:** Stateless; writes nothing into `shared/` and reads nothing from it. A gateway request and an orchestrator run can therefore run concurrently without interfering.

**Stack:** Python with FastAPI (same as the pipeline and stage services). Refer to `## Stage Services` for the HTTP framework choice.

---

## UI

No front-end is required for this pipeline. The pipeline is fully usable from the CLI and requires no UI.
