# Specification — Transaction Processing Pipeline

## 1. High-Level Objective

Process financial transactions through a five-stage pipeline that validates each record, detects fraud risk, checks regulatory compliance, settles the transaction, and produces an audit-trail report — all via file-based orchestration and CLI invocation.

## 2. Mid-Level Objectives

1. Every input transaction must be validated against the schema, and records failing validation must be reported with a reason and written to `shared/results/`.
2. The pipeline must support independent validation of the input source without processing it — checking every record's validity in isolation and reporting pass/fail with counts, without reading, creating, or modifying `shared/`.
3. Each transaction must receive a fraud-risk score on a scale of 0.00–1.00, derived from three weighted factors (high value, cross-border mismatch, unusual-hour timing), and flagged for review when the score meets or exceeds 0.50, per GDPR Article 22.
4. Compliance rules must apply uniformly to all records regardless of origin, with decisions logged to the audit trail; adverse actions must be decided by a human reviewer, never solely by an automated rule.
5. Successfully processed transactions must be settled with a generated reference and timestamp, audit records retained for five years under the legal-obligation lawful basis, and run state published as `status.json` and `report.json` for external observation without log parsing.
6. The pipeline must be designed to handle throughput up to 100,000 transactions per second and maintain 99.99% uptime, with no artificial single-threaded bottlenecks.

## 3. Implementation Notes

- **Decimal handling**: monetary values (`amount`) must always be represented as decimal types, never binary floats, to prevent rounding errors. [NEEDS CLARIFICATION: stack/language for the pipeline — none was specified, so the concrete decimal type cannot be named]
- **Currency codes**: must comply with ISO 4217; sample data may include invalid codes (e.g. `XYZ`) as test cases, which Validation must catch.
- **Negative amounts**: are valid and represent refunds or reversals; they are not malformed input.
- **Time handling**: all timing logic, including the fraud-detection unusual-hour window (06:00–22:00 UTC), operates in UTC only — no local-timezone conversion, DST handling, or per-country offset tables.
- **Association**: records are associated by `transaction_id`, never by file order or read sequence.
- **Audit trail**: every transaction record must include its ID, processing timestamp, stage name, and outcome in the audit log; no PII (account numbers, customer names, identifying data) may appear in plaintext in logs.
- **Compliance regime**: GDPR and the Data Protection Act 2018, applied uniformly to all records regardless of origin as a privacy-by-design choice per GDPR Article 22. Automated decisions with legal or significant effects must include a hold for human review rather than automated rejection.
- **Fraud scoring**: uses a transparent, weighted rule-based approach:
  - High-value amount (weight 0.50): triggered when absolute `amount` >= £10,000 or equivalent in the transaction's currency.
  - Cross-border mismatch (weight 0.30): triggered when source/destination account countries differ, or `metadata.country` differs from the baseline country (GB, unless transaction data implies otherwise).
  - Unusual-hour timing (weight 0.20): triggered when `timestamp` falls outside 06:00–22:00 UTC.
  - Scores cap at 1.00 and flag for review when >= 0.50. Fraud Detection flags only; Compliance Check decides whether to hold or reject per GDPR Article 22.
- **Settlement mechanism**: by default, an internal simulated ledger without external network calls, marking transactions settled with a generated reference and timestamp. Records containing account or PII data are retained for five years under the legal-obligation lawful basis per GDPR, then purged or anonymized.
- **Performance targets**: the architecture is designed to sustain up to 100,000 transactions per second with 99.99% uptime, with no artificial blocking I/O or single-threaded bottlenecks.

## 4. Context

### Beginning Context

The pipeline ingests transaction records from an input transaction source (defaulting to `sample-transactions.json` as a test fixture if not otherwise specified). Each record follows the default schema:

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

Before the run, `shared/` exists but is empty; the orchestrator creates its subdirectories if they do not exist.

### Ending Context

After a successful run, `shared/` contains:

- `input/` — emptied of transaction files (all records have been read and processed; the directory is retained).
- `processing/` — cleared; no stage work-in-progress remains.
- `output/` — contains messages from the Reporting stage, awaiting any external consumer.
- `results/` — exactly one file per processed transaction, holding the final record with status, outcome reason, and audit trail.
- `status.json` — per-stage start/completion timestamps and transaction counts (processed, passed, failed) for each stage, written live as each stage completes.
- `report.json` — aggregate run summary: total transactions, valid/invalid counts, fraud-flag counts, compliance-hold counts, settlement counts, and any run-level errors or notes.

Transactions that fail validation or compliance checks are marked in `results/` and reported in `report.json`; they do not progress to later stages. The pipeline does not alter any input record; stage outputs are fresh files in `output/` or `results/`, with original data preserved.

## 5. Low-Level Tasks

Task: Validation Stage
Prompt: "Write a Validation stage that reads each input transaction, checks that required fields are present and correctly typed, validates that `amount` is a valid decimal string and `currency` is a recognized ISO 4217 code, ensures `timestamp` is ISO 8601 compliant, and writes each record's validation result (pass or fail, with reason) to the output directory. Additionally, support a standalone mode that checks all input records without processing them, writing nothing to `shared/`, and returning pass/fail counts and per-record reasons."
File to CREATE: `pipeline/validation.[ext]`
Function to CREATE: `validate_transaction(record: Transaction) -> ValidationResult`
Details: The Validation stage checks that every input transaction has the required fields (`transaction_id`, `timestamp`, `source_account`, `destination_account`, `amount`, `currency`, `transaction_type`), that `amount` is a valid decimal string (never a float), and that `currency` matches ISO 4217. Records failing validation are marked with a reason (e.g. "missing transaction_id", "invalid currency code"). The stage must also support a standalone invocation mode, invoked directly on the input source without processing, that reads every record, applies the same rules, reports each record's ID and verdict with reason, and returns total, valid, and invalid counts — all without touching `shared/` or modifying any state. This standalone capability is a testable requirement observable without disturbing any run in progress.

Task: Fraud Detection Stage
Prompt: "Write a Fraud Detection stage that scores each transaction on a scale of 0.00–1.00 using three weighted factors: high-value amount (weight 0.50, threshold £10,000 or equivalent), cross-border mismatch (weight 0.30, triggered when source/destination countries differ or metadata.country differs from baseline), and unusual-hour timing (weight 0.20, triggered when timestamp falls outside 06:00–22:00 UTC). All weights are additive and capped at 1.00. Flag the record for review when the score is >= 0.50. Output each record with its score and flag status; write no rejection, only a flag for Compliance Check to review."
File to CREATE: `pipeline/fraud_detection.[ext]`
Function to CREATE: `score_transaction(record: Transaction, rates: ExchangeRates) -> FraudResult`
Details: The Fraud Detection stage computes a transparent, rule-based risk score for every validated transaction. It checks: (1) whether the absolute amount meets or exceeds the high-value threshold (£10,000 or its equivalent in the transaction's currency, using exchange rates as needed); (2) whether the source and destination accounts' countries differ, or whether `metadata.country` differs from the baseline country (GB, or another if the data implies it); and (3) whether the transaction's `timestamp` falls outside 06:00–22:00 UTC (no local timezone conversion, UTC only). Scores are additive with a ceiling of 1.00. Records scoring >= 0.50 are flagged for review per GDPR Article 22; flagging is non-rejecting — the flag signals Compliance Check, which decides the outcome. The output includes each record's score and flag status, written to `output/` for the next stage.

Task: Compliance Check Stage
Prompt: "Write a Compliance Check stage that reviews each transaction against GDPR and the Data Protection Act 2018, applied uniformly to all records. For any record flagged by Fraud Detection or triggering a compliance rule (e.g. PII in plaintext, cross-border flow without audit trail), issue a hold for human review rather than an automated rejection per GDPR Article 22. Record the compliance decision (pass or hold) with reason; passed records proceed to Settlement, held records are reported in the final report. Write all decisions to output/ for the next stage."
File to CREATE: `pipeline/compliance.[ext]`
Function to CREATE: `check_compliance(record: Transaction, fraud: FraudResult) -> ComplianceResult`
Details: The Compliance Check stage applies GDPR and Data Protection Act 2018 rules uniformly to every record, regardless of origin. It checks fraud flags and compliance rules (e.g. PII handling, audit trail completeness, cross-border data flow validity). Per GDPR Article 22, it must never make a solely automated decision with legal or significant effect; instead, it issues a hold for human review of flagged or non-compliant records, never an automated rejection. Passed records are marked and proceed to Settlement Processing; held records are reported in the audit trail and marked for review in the final report. All decisions are written to `output/`.

Task: Settlement Processing Stage
Prompt: "Write a Settlement Processing stage that settles each compliant transaction by generating a unique settlement reference and timestamp, recording the settlement in an internal ledger, and writing the settled record (with reference and settlement timestamp) to the output directory. Retain the settlement and audit records in a secure, queryable store for five years under the legal-obligation lawful basis per GDPR; mark records with account or PII data for secure retention and eventual purge/anonymization. Write no external API calls or third-party network integration."
File to CREATE: `pipeline/settlement.[ext]`
Function to CREATE: `settle_transaction(record: Transaction, compliance: ComplianceResult) -> SettlementResult`
Details: The Settlement Processing stage settles each transaction that passed Compliance Check by assigning a settlement reference (e.g. a UUID) and a settlement timestamp (distinct from the transaction's own timestamp). It marks the transaction settled in an internal simulated ledger and writes the settled record to `output/` for the Reporting stage. No external settlement network (e.g. Faster Payments, CHAPS) is invoked; settlement is internal and immediate. Audit records containing account numbers or PII are retained for five years under GDPR's legal-obligation basis, then purged or anonymized. The settlement record itself is written to `results/` once reported.

Task: Reporting Stage
Prompt: "Write a Reporting stage that reads all records from the preceding stages (validation results, fraud flags, compliance holds, settlements), aggregates them into a comprehensive transaction-by-transaction report, and writes two final artifacts: `results/[transaction_id].json` for each transaction (holding its full audit trail, status, and any failures or holds), and `report.json` at the top level of shared/ (holding aggregate counts: total transactions, valid/invalid, fraud-flagged, compliance-held, settled, and any run-level errors). Also publish `status.json` with per-stage timestamps and counts as the run progresses. Ensure timestamps, transaction IDs, and reasons are included in each record."
File to CREATE: `pipeline/reporting.[ext]`
Function to CREATE: `build_report(records: list[ProcessedTransaction]) -> RunReport`
Details: The Reporting stage synthesizes all preceding stages' outputs into a complete audit-trail record for every transaction. For each transaction, it writes a file to `results/` containing the transaction ID, all audit-trail entries (validation verdict, fraud score, compliance decision, settlement reference and timestamp if applicable), final status (passed or failed, with reason), and timestamp of reporting. It simultaneously aggregates run-level metrics: total records processed, valid/invalid counts, fraud-flag counts, compliance-hold counts, settled-transaction counts, and any run-level errors. This aggregate is written to `report.json`. The stage also ensures that `status.json` is maintained live, with each stage's start/completion timestamps and per-stage transaction counts (processed, passed, failed) — observable by external processes without log parsing or coupling to pipeline internals.

## UI

An optional minimal front-end may accompany the pipeline to provide a user interface for (1) starting a pipeline run, (2) displaying run status in real time as the pipeline processes, and (3) presenting a results dashboard showing each transaction's outcome, pass/fail counts, and the reason each held or failed record was rejected. The UI reads the `shared/` file tree (specifically `status.json` and `results/` files) to display state and outcomes; it starts a run by invoking the pipeline's CLI exactly as a user would, and it never reads or imports pipeline source code or writes to `shared/` itself. The pipeline is complete and fully usable from the CLI without any front-end present. [NEEDS CLARIFICATION: stack/framework for the UI — none was specified]
