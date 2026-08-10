# Specification — Transaction Processing Pipeline

## 1. High-Level Objective

The pipeline ingests transaction records, validates them, assesses fraud risk, enforces compliance with data protection law, settles the transactions, and produces a reconciled run report with full audit trail.

## 2. Mid-Level Objectives

1. Validate every transaction for schema correctness, required fields, and valid currency codes; write invalid records to output with reason, blocking them from later stages.
2. Score every valid transaction for fraud risk using a transparent, weighted rule-based approach; flag high-risk records (score ≥ 0.50) for manual review without auto-rejecting.
3. Check every transaction against data protection compliance requirements (GDPR), applying privacy-by-design principles to all records regardless of geographic origin; hold flagged transactions pending review rather than auto-reacting.
4. Settle every compliant transaction via internal ledger simulation, producing settlement timestamps and audit records retained for 5 years under GDPR's legal obligation basis.
5. Generate a machine-readable run report and per-stage status timeline, observable by any external process without coupling to the pipeline or log parsing.

## 3. Implementation Notes

- **Monetary values** must be represented as decimal strings, never binary floating-point; [NEEDS CLARIFICATION: stack/language for the pipeline — none was specified, so the concrete decimal type cannot be named].
- Currency codes follow ISO 4217; invalid codes (e.g., `XYZ`) are validation failures, not malformed input.
- Negative amounts are valid transaction data (refunds).
- All time logic operates in UTC; the transaction's own `timestamp` (when it occurred) is distinct from inter-stage message timestamps (when a hop was written). Timing checks always use the transaction's own `timestamp`. Unusual-hour timing (outside 06:00–22:00 UTC) is a fraud-score factor; no local-timezone conversion, DST handling, or per-country offset table.
- Transactions are associated by `transaction_id`, never by position or read order.
- Audit trail logs every transaction's passage through the pipeline: entry timestamp, stage name, transaction ID, outcome (pass/flag/hold/settle), and exit timestamp. PII (account numbers, customer names, identifying metadata) is never logged in plaintext.
- The compliance regime is **GDPR and the Data Protection Act 2018** (or UK GDPR in UK-specific contexts), applied uniformly to all records as a deliberate privacy-by-design choice. AML and financial-crime regimes are out of scope unless explicitly stated otherwise.
- Fraud detection uses a **transparent, weighted rule-based score** (0.00–1.00) with the following factors:
  - High-value amount (weight 0.50): absolute `amount` ≥ $10,000 (or currency equivalent)
  - Cross-border mismatch (weight 0.30): source/destination country mismatch or `metadata.country` differs from GB (the baseline jurisdiction)
  - Unusual-hour timing (weight 0.20): `timestamp` falls outside 06:00–22:00 UTC
  - Applicable weights sum and cap at 1.00; flag at score ≥ 0.50.
- Fraud Detection flags transactions for review; it does not auto-reject or auto-block. Compliance Check applies holds instead of rejections, per GDPR Article 22's restriction on solely-automated decisions with legal or significant effects.
- Settlement is via **internal simulated ledger**, assigning a settlement timestamp and reference to each transaction without external API or network calls. Settlement and audit records are retained for **5 years** (standard UK financial record-keeping) under GDPR's legal obligation lawful basis; records are purged or anonymized thereafter.
- Performance targets: **99.99% uptime** and sustained throughput capability up to **100,000 transactions per second**. Architecture must avoid single-threaded bottlenecks and per-transaction blocking I/O.

## 4. Context

**Beginning Context**

The pipeline receives transaction records from an input transaction source. At the start of a run, the `shared/` directory is empty or contains only leftover files from prior runs; the pipeline's first stage clears and re-initializes it. Each transaction is ingested as a separate file into `shared/input/`.

**Ending Context**

After a successful run, the `shared/` directory tree contains:

- `shared/input/` — empty of files; the directory itself remains. All ingested records have been read by stages that required original fields.
- `shared/processing/` — empty; the currently-running stage clears this between transactions.
- `shared/output/` — empty; the last-completed stage's output is consumed by the next stage.
- `shared/results/` — exactly one file per transaction, containing the final record with validation status, fraud score, compliance decision, settlement reference (if settled), and audit trail.
- `shared/status.json` — per-stage start/completion timestamps, processed count, passed count, and failed count. Written live as each stage progresses, providing observability into run state without coupling to the pipeline, parsing logs, or counting files.
- `shared/report.json` — aggregate run summary: total transactions processed, validation pass/fail counts, fraud flags, compliance holds, settled count, and overall run status. Written once at the end.

## 5. Low-Level Tasks

Task: Validation Stage
Prompt: "Validate each transaction record for required fields, schema correctness, and valid ISO 4217 currency code. Return a structured validation result containing pass/fail status and, if invalid, the specific error reason. Write invalid records to output with reason; they are blocked from proceeding to Fraud Detection."
File to CREATE: `pipeline/validation.[ext]`
Function to CREATE: `validate_transaction(record: Transaction) -> ValidationResult`
Details: Checks presence and type of `transaction_id`, `timestamp` (ISO 8601), `source_account`, `destination_account`, `amount` (non-empty decimal string), `currency` (ISO 4217), `transaction_type`, `description`, and optional `metadata`. Rejects records with missing required fields, non-ISO timestamp format, non-decimal `amount`, or unrecognized currency code. Logs each check to the audit trail with timestamp, stage name, transaction ID, and outcome (pass or fail reason).

Task: Fraud Detection Stage
Prompt: "Score each transaction using the fraud-detection scoring model: high-value amount (0.50), cross-border mismatch (0.30), and unusual-hour timing (0.20). Use a baseline country of GB unless the data implies otherwise. Flag at score ≥ 0.50. Return a fraud result with score, individual factor contributions, and flag status. Fraud Detection does not auto-reject or auto-block; it only flags for review per GDPR Article 22."
File to CREATE: `pipeline/fraud_detection.[ext]`
Function to CREATE: `score_transaction(record: Transaction, rates: ExchangeRates) -> FraudResult`
Details: Applies the transparent, weighted rule-based score (0.00–1.00) to each record. High-value threshold is $10,000 USD or equivalent in other currencies. Cross-border mismatch detects source/destination country mismatch or divergence of `metadata.country` from the baseline (GB). Unusual-hour timing checks the transaction's own `timestamp` in UTC; any time outside 06:00–22:00 UTC (no local-timezone offset) is flagged. Outputs the final score, individual factor values, and a flag boolean (true if score ≥ 0.50). Logs to audit trail: timestamp, stage name, transaction ID, fraud score, and flag status.

Task: Compliance Check Stage
Prompt: "Apply data protection compliance checks (GDPR and Data Protection Act 2018). For each transaction, verify PII handling and cross-check fraud flags. Transactions flagged by Fraud Detection are placed on hold pending review, not auto-rejected, per GDPR Article 22. Return a compliance result with hold status, review reason, and compliance decision. Records on hold are written to output; settled records proceed to Settlement Processing."
File to CREATE: `pipeline/compliance.[ext]`
Function to CREATE: `check_compliance(record: Transaction, fraud: FraudResult) -> ComplianceResult`
Details: Applies GDPR and Data Protection Act 2018 checks uniformly to all records, treating privacy as a design principle across the entire dataset. Verifies that account identifiers and customer names are not logged in plaintext in upstream audit trails; flagged transactions are placed on hold for manual review rather than auto-rejected, satisfying GDPR Article 22's restriction on solely-automated decisions with legal or significant effects. Compliant records are approved for settlement; fraud-flagged records are held with a review reason logged. Outputs compliance decision (approved/hold), hold reason if applicable, and compliance audit trail including timestamp, stage name, transaction ID, and decision.

Task: Settlement Processing Stage
Prompt: "Settle each approved transaction via internal ledger simulation. Assign a settlement timestamp and a generated settlement reference (e.g., UUID or sequential ID) to each record. Retain settlement and audit records for 5 years under GDPR's legal obligation lawful basis; implement or document the purge/anonymization schedule for records after the retention period. Return a settlement result with reference, timestamp, and settlement status. Do not call external APIs or settlement networks unless explicitly specified."
File to CREATE: `pipeline/settlement.[ext]`
Function to CREATE: `settle_transaction(record: Transaction, compliance: ComplianceResult) -> SettlementResult`
Details: Performs internal ledger settlement for each approved transaction. Generates a unique settlement reference (non-guessable identifier) and records the settlement timestamp (distinct from the transaction's original `timestamp`). No external API calls or third-party network integration unless specified. Records containing account numbers, transaction amounts, and settlement references are retained in the audit trail for 5 years (standard UK financial record-keeping) under GDPR's legal obligation basis, overriding erasure requests during the retention window. After 5 years, records are purged or anonymized per applicable data protection policy. Outputs settlement reference, settlement timestamp, and settlement status (settled/failed). Logs to audit trail: timestamp, stage name, transaction ID, settlement reference, and settlement outcome.

Task: Reporting Stage
Prompt: "Aggregate all settled and processed transactions into a final run report. Count transactions by outcome (validated, fraud-flagged, compliance-held, settled, failed). Generate run-level statistics and timestamps for pipeline start and end. Produce two machine-readable outputs: status.json (per-stage progress with timestamps and counts) and report.json (aggregate run summary). Both must be observable by external processes without coupling to the pipeline."
File to CREATE: `pipeline/reporting.[ext]`
Function to CREATE: `build_report(records: list[ProcessedTransaction]) -> RunReport`
Details: Collects outcomes from all upstream stages and produces two outputs. `status.json` contains per-stage telemetry: stage name, start timestamp, completion timestamp, processed count, passed count, and failed count for each stage, updated live as stages complete. `report.json` contains aggregate statistics: total transactions, validation pass/fail counts, fraud flags, compliance holds, settled count, overall success/failure, pipeline start time, and pipeline end time. Both outputs are plain, self-describing JSON that any external process can consume for observability and audit purposes without parsing logs or coupling to the pipeline's internal structure. Logs all transaction outcomes and aggregate counts to the audit trail.
