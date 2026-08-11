# Specification — Transaction Processing Pipeline

## 1. High-Level Objective

A file-based transaction processing pipeline that ingests raw financial transaction records and carries each one through validation, fraud scoring, compliance screening, settlement and reporting, publishing an auditable outcome for every transaction.

## 2. Mid-Level Objectives

1. Every ingested record is validated against the canonical transaction schema — required fields present and correctly typed, `amount` a well-formed decimal, `currency` a real ISO 4217 code — and records that fail are written to `shared/results/` with a human-readable rejection reason and go no further.
2. Every validated transaction receives a transparent, explainable risk score between `0.00` and `1.00` derived from stated weighted factors, and is flagged for review at `>= 0.50`; scoring flags but never rejects or blocks.
3. Compliance screening is the only stage that takes adverse action: flagged transactions are held for human review rather than automatically rejected, and no transaction that has not cleared compliance is ever settled.
4. Every stage appends an audit-trail entry for every transaction it handles, carrying an ISO 8601 UTC timestamp, the stage name, the transaction identifier and the outcome, with account numbers and other customer-identifying data never recorded in plaintext.
5. The pipeline publishes its own run state and outcomes as plain, self-describing JSON — `shared/status.json` updated live as each stage starts and completes, and `shared/report.json` written once at the end — so that any external process can observe a run's progress and results without coupling to the pipeline, parsing its logs, or counting files across directories.
6. The Validation stage can be invoked on its own against the input transaction source to report each record's identifier, pass/fail verdict and failure reason, together with total, valid and invalid counts, while writing nothing at all — so the input source can be checked for validity independently of, and without disturbing, a processing run.

## 3. Implementation Notes

- **Monetary values** must be represented as decimal strings and computed with a precise decimal type, never binary floating-point, so that no rounding error can enter a monetary calculation; [NEEDS CLARIFICATION: stack/language for the pipeline — none was specified, so the concrete decimal type cannot be named].
- **Currency codes** are validated against ISO 4217. Sample data may deliberately contain invalid codes, which Validation must catch as a rejection rather than treat as malformed input.
- **Negative amounts are valid data**, representing refunds and reversals, and must not be rejected as malformed.
- **Audit trail**: every stage logs one entry per transaction handled, containing an ISO 8601 timestamp, the stage name, the transaction identifier and the outcome.
- **PII handling**: account numbers, names and any other customer-identifying data are treated as sensitive and are never written to logs in plaintext.
- **All time logic is UTC.** Timestamps are compared directly in UTC with no local-timezone conversion, no per-country offset table and no daylight-saving handling. A transaction's own `timestamp` (when it occurred) is distinct from an inter-stage message's `timestamp` (when that hop was written); timing checks always use the former.
- **Records are associated by `transaction_id`** at every stage boundary — never by array index, list position or directory read order.
- **Compliance regime**: GDPR (UK GDPR where the context is UK-specific) together with the Data Protection Act 2018, governing PII handling and the audit trail, and forming the Compliance Check stage's baseline rule set. AML and financial-crime regimes are out of scope. The regime is applied uniformly to every record regardless of the data's country mix — a deliberate privacy-by-design choice, not a jurisdictional claim.
- **Fraud scoring approach**: a transparent, weighted rule-based score, never an opaque or learned model. This is a GDPR Article 22 consideration — profiling that drives an automated decision must have explainable logic. Applicable weights sum, capped at `1.00`:

  | Factor | Weight | Condition |
  |---|---|---|
  | High-value amount | `0.50` | absolute `amount` >= the high-value threshold (e.g. $10,000 or currency equivalent) |
  | Cross-border mismatch | `0.30` | source/destination account country mismatch, or `metadata.country` differs from the baseline country |
  | Unusual-hour timing | `0.20` | the transaction's own `timestamp` falls outside 06:00–22:00 UTC |

  A transaction is flagged for review at `>= 0.50`: the amount factor alone suffices, as does any two lesser factors. The baseline country is GB, matching the jurisdiction implied by the compliance regime, so that cross-border reasoning and compliance reasoning refer to the same home jurisdiction. Fraud Detection only flags — adverse action belongs to Compliance Check, satisfying GDPR Article 22's restriction on solely-automated decisions with legal or significant effects.
- **Settlement mechanism**: internal simulated ledger settlement — transactions are marked settled with a settlement timestamp and a generated settlement reference, with no external API or network call and no data shared with any third-party processor, satisfying data minimization. Settlement and audit records containing account or PII data are retained for 5 years under GDPR's "legal obligation" lawful basis, which overrides erasure requests during that window; records are purged or anonymized afterwards.
- **Performance targets**: the architecture is held to 99.99% uptime and sustained throughput of up to 100,000 transactions/second — design targets the architecture must not preclude, not a benchmark any particular run demonstrates. No artificial single-threaded bottleneck or per-transaction blocking I/O that would cap throughput far below target.

## 4. Context

### Beginning context

An input transaction source supplying raw transaction records as a JSON array, defaulting to `sample-transactions.json` when no other source is given. The source is always overridable and its record count is variable. Each record has the shape:

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

`metadata` is an open object; `channel` and `country` are fields that have been observed, not an exhaustive list. Before a run, the `shared/` tree does not yet exist or holds no files.

### Ending context

```
shared/
├── input/       ← the ingested records, one file per transaction; read-only for the run's duration, emptied of files once the run finishes successfully (every stage needing an original field has already read it by then; the directory itself is never removed)
├── processing/  ← the currently-running stage's work in progress
├── output/      ← the last completed stage's messages, awaiting the next stage
├── results/     ← final destination only: exactly one final record per transaction
├── status.json  ← per-stage start/completion timestamps and processed/passed/failed counts, written live as the run progresses
└── report.json  ← the aggregate run summary, written once at the end
```

Once a run finishes, `results/` holds exactly one final record per ingested transaction, combining the original transaction fields with the results accumulated by every stage that handled it. `processing/` and `output/` remain as directories, emptied of files. Nothing under `shared/` is removed once created — only emptied.

## 5. Low-Level Tasks

```
Task: Validation Stage
Prompt: "Implement the validation stage. For each ingested transaction record, confirm every required field is present and correctly typed, that the amount parses as a precise decimal, and that the currency is a real ISO 4217 code. Return a validation result carrying a pass/fail status, a human-readable reason when it fails, and the UTC timestamp of the check. Records that pass continue to fraud detection; records that fail are written straight to the final results with their rejection reason and go no further. Also provide a standalone, non-mutating invocation of this stage that checks the input transaction source without processing it."
File to CREATE: pipeline/validation.[ext]
Function to CREATE: validate_transaction(record: Transaction) -> ValidationResult
Details: Checks presence and type of every canonical field — transaction_id, timestamp, source_account, destination_account, amount, currency, transaction_type, description and metadata, including metadata.channel and metadata.country. Confirms the timestamp parses as ISO 8601, that amount is a decimal string parsing without loss, and that currency is a genuine ISO 4217 code — an unrecognized code such as XYZ is a rejection, not an input error. Negative amounts are valid and must pass. A failure produces a reason naming the specific field or value at fault. Passing records are annotated and forwarded; failing records are finalized immediately with their reason. The stage is additionally invocable on its own against the input transaction source, applying exactly these same rules and reporting every record's identifier, its pass/fail verdict and the reason for any failure, along with the total, valid and invalid counts. That invocation changes nothing: no part of the shared/ tree is read, created or modified, no record is altered, and nothing is written anywhere, leaving a run in progress or already finished untouched. It reads the input transaction source directly and never shared/input/, whose contents exist only for the duration of a run.
```

```
Task: Fraud Detection Stage
Prompt: "Implement the fraud detection stage. Score each validated transaction for risk using transparent, weighted rules, converting amounts to a common currency using supplied exchange rates so the high-value test is comparable across currencies. Return a fraud result carrying the score, the individual factors that contributed, whether the transaction is flagged, and the UTC timestamp of the scoring. This stage flags but never rejects — every transaction continues to compliance screening regardless of its score."
File to CREATE: pipeline/fraud_detection.[ext]
Function to CREATE: score_transaction(record: Transaction, rates: ExchangeRates) -> FraudResult
Details: Sums applicable weights, capped at 1.00 — high-value amount 0.50 when the absolute amount reaches the high-value threshold of $10,000 or its currency equivalent, cross-border mismatch 0.30 when the source and destination account countries differ or metadata.country differs from the GB baseline, and unusual-hour timing 0.20 when the transaction's own timestamp falls outside 06:00–22:00 UTC. Flags for review at a score of 0.50 or above, so the amount factor alone suffices, as does any two lesser factors. The score must be explainable, with each contributing factor recorded alongside it, per GDPR Article 22. Uses the transaction's own timestamp, never the inter-stage message timestamp, and compares directly in UTC without timezone conversion. Emits no rejection under any circumstances.
```

```
Task: Compliance Check Stage
Prompt: "Implement the compliance check stage. Screen each scored transaction against the GDPR and Data Protection Act 2018 baseline rule set, and decide whether it clears, is held for human review, or is rejected. Return a compliance result carrying the decision, a reason when it is not cleared, and the UTC timestamp of the check. Transactions flagged by fraud detection are held for human review rather than automatically rejected."
File to CREATE: pipeline/compliance.[ext]
Function to CREATE: check_compliance(record: Transaction, fraud: FraudResult) -> ComplianceResult
Details: Applies the GDPR and Data Protection Act 2018 baseline uniformly to every record regardless of the data's country mix — a deliberate privacy-by-design choice, not a jurisdictional claim. A transaction flagged by fraud detection is held for human review, never auto-rejected, satisfying GDPR Article 22's restriction on solely-automated decisions with legal or significant effects; the hold reason records the score that caused it. Cleared transactions continue to settlement. Held or rejected transactions are finalized immediately with their reason and go no further — a transaction that has not cleared compliance is never settled. Confirms PII is handled per the regime, with account identifiers never emitted in plaintext to the audit trail.
```

```
Task: Settlement Processing Stage
Prompt: "Implement the settlement processing stage. For each compliance-cleared transaction, settle it against an internal simulated ledger — no external API or network call — and return a settlement result carrying the settled amount and currency, a generated settlement reference, the UTC settlement timestamp, and the retention period applying to the record."
File to CREATE: pipeline/settlement.[ext]
Function to CREATE: settle_transaction(record: Transaction, compliance: ComplianceResult) -> SettlementResult
Details: Receives only compliance-cleared transactions. Settles internally against a simulated ledger, marking the transaction settled with a UTC settlement timestamp and a generated unique settlement reference; no external API or network call is made and no data is shared with any third-party processor, satisfying data minimization. Monetary amounts are carried through with a precise decimal type, never binary floating-point, and the original currency is preserved. Records the 5-year retention period applying to settlement and audit records containing account or PII data, held under GDPR's "legal obligation" lawful basis, which overrides erasure requests during that window.
```

```
Task: Reporting Stage
Prompt: "Implement the reporting stage. Aggregate every processed transaction into a run summary written to shared/report.json, then build each transaction's final record by joining the original transaction with the results accumulated by every stage that handled it, and place it in shared/results/."
File to CREATE: pipeline/reporting.[ext]
Function to CREATE: build_report(records: list[ProcessedTransaction]) -> RunReport
Details: Computes the aggregate run summary — total records processed, counts by outcome across validated, rejected, flagged, held and settled, the distribution of risk scores, and total settled value broken down by currency using precise decimal arithmetic — and writes it to shared/report.json at the shared/ root, never inside results/. Then assembles each transaction's final record by joining the original transaction, read fresh from the ingested records, with its accumulated stage results, associating them by transaction_id and never by position or read order, and moves it into shared/results/. Afterwards processing/ and output/ remain as directories emptied of files.
```
