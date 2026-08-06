# Specification — Transaction Processing Pipeline

## 1. High-Level Objective

A banking transaction-processing pipeline that takes raw transaction records and moves each one through validation, fraud scoring, compliance review, settlement, and reporting, with the five stages exchanging work as JSON files in a shared directory tree beneath a single command-line orchestrator.

## 2. Mid-Level Objectives

1. Each ingested record is validated against the canonical schema before any other stage sees it — required fields present, `amount` parseable as a decimal whether positive or negative, `currency` a genuine ISO 4217 code — and whatever fails is written to `shared/results/` with a `reason` identifying the precise failure and proceeds no further.
2. Each validated record is assigned a weighted risk score from 0.00 to 1.00 together with the individual factors that produced it, so the outcome can be explained after the fact; the scoring stage flags records for review and has no power to reject or block one.
3. Each record arriving at compliance is judged against the data-protection rules covering its PII and account data and leaves cleared, held, or rejected; held and rejected records end there with a `reason` recorded, and nothing that has not cleared can be settled.
4. Each cleared record is settled into a settlement record carrying a timestamp, a generated reference, and a status, retained for the statutory period governing financial and audit data.
5. Each record, however it ends, finishes as exactly one file in `shared/results/` joining its original fields to the results gathered at every stage it reached, and the run as a whole yields an aggregate summary of its outcomes.
6. Each stage records an audit entry per record — ISO 8601 UTC timestamp, stage name, transaction ID, outcome — with no PII in plaintext, and the pipeline publishes its run state and results as plain, self-describing JSON so that a run's progress and outcome can be observed by any external process without coupling to the pipeline, parsing its logs, or counting files across directories.

## 3. Implementation Notes

- **Monetary handling.** Amounts are carried in a precise decimal type from parsing through comparison, settlement, and aggregation. `amount` arrives as a string and is parsed directly into that type, never routed through a binary float at any point, because the resulting rounding error would be both silent and cumulative. `[NEEDS CLARIFICATION: stack/language for the pipeline — none was specified, so the concrete decimal type cannot be named]`
- **Negative amounts.** A negative `amount` marks a refund and is legitimate input. Validation accepts it, and fraud scoring compares the **absolute** amount against the high-value threshold so a refund is judged by size rather than direction.
- **Currency codes.** ISO 4217. Input may carry codes that are not valid ISO 4217; Validation rejects those with a specific reason rather than treating them as a fault in the source.
- **Audit trail.** One entry per record per stage, holding an ISO 8601 UTC timestamp, the stage name, the transaction ID, and the outcome.
- **PII.** Account numbers, names, and free-text descriptions are sensitive; none is ever logged in plaintext, and audit entries identify a record by `transaction_id` alone.
- **Time.** Every time comparison is made in UTC — no conversion to local time, no per-country offset table, no DST handling. A transaction's own `timestamp` says when it occurred while an inter-stage message's `timestamp` says when that hop was written, and all timing rules use the former.
- **Identity.** Records are matched between stages on `transaction_id` alone, never on array index, list position, or the order in which a directory happens to be read.
- **Compliance regime.** GDPR — UK GDPR where the context is UK-specific — with the Data Protection Act 2018, governing PII handling and the audit trail and forming the Compliance Check stage's baseline rule set. It applies uniformly to every record whatever its country of origin. That uniformity is a deliberate privacy-by-design choice rather than a jurisdictional claim, since GDPR's territorial scope normally follows where data subjects are. AML and financial-crime regimes such as UK MLR 2017 and FCA customer due diligence fall outside scope.
- **Fraud scoring.** A transparent, weighted rule-based score rather than an opaque or learned model, because GDPR Article 22 requires that profiling behind an automated decision have explainable logic. Applicable weights sum and cap at 1.00:

  | Factor | Weight | Condition |
  |---|---|---|
  | High-value amount | 0.50 | absolute `amount` at or above $10,000, or its equivalent in the transaction's currency |
  | Cross-border mismatch | 0.30 | source and destination account countries differ, or `metadata.country` differs from the baseline country |
  | Unusual-hour timing | 0.20 | the transaction's own `timestamp` falls outside 06:00–22:00 UTC |

  A score of 0.50 or above flags the record for review — the high-value factor reaches that alone, as does any pair of the lesser factors. The **baseline country is GB**, matching the jurisdiction the compliance regime implies, so cross-border is judged against the same country the compliance rules reason about. Weighing a non-baseline currency against the high-value threshold calls for current exchange rates covering whichever currencies actually appear in the input.
- **Flagging is not rejection.** Fraud Detection annotates and passes the record on; it never rejects or blocks. Adverse action rests with Compliance Check, which holds a flagged record for human review instead of deciding against it automatically — this is what satisfies GDPR Article 22's restriction on solely-automated decisions producing legal or similarly significant effects.
- **Settlement.** An internal simulated ledger: the record is marked settled with a settlement timestamp and a generated reference. No external API or network call takes place and no data reaches a third-party processor, keeping the design data-minimizing by default. Settlement and audit records containing account or PII data are held for **5 years**, a standard financial record-keeping period, on GDPR's legal-obligation basis — which overrides erasure requests throughout that window — and are purged or anonymized afterwards.
- **Performance and scalability.** 99.99% uptime and sustained throughput of up to 100,000 transactions per second. These are targets the architecture is held to — no artificial single-threaded bottleneck, no per-transaction blocking I/O that would cap throughput far beneath them — rather than a benchmark any given run is expected to demonstrate under load.
- **Volume.** The number of records is arbitrary and varies from run to run; no count may be assumed or hardcoded anywhere.

## 4. Context

**Beginning context.** An input transaction source stands ready for ingestion: an arbitrary, variable-length set of records in the canonical schema — `transaction_id`, `timestamp`, `source_account`, `destination_account`, `amount` as a decimal string, `currency`, `transaction_type`, `description`, `metadata.channel`, `metadata.country`. The source is overridable, with `sample-transactions.json` serving as the default fixture when none is named. No `shared/` tree need exist beforehand; the orchestrator creates it.

**Ending context.** The run leaves this tree, which constitutes its complete record:

```
shared/
├── input/       ← the ingested records, one file per transaction; read-only once written
├── processing/  ← the currently-running stage's work in progress; holds no files at rest
├── output/      ← the last completed stage's messages awaiting the next stage; holds no files once Reporting finishes
├── results/     ← exactly one final record per transaction, joining its original fields to the results gathered at every stage it reached
├── status.json  ← per-stage start and completion timestamps with processed/passed/failed counts, written live as the run progresses
└── report.json  ← the aggregate run summary, written once at the end
```

`status.json` and `report.json` are first-class obligations of the pipeline rather than conveniences: together with `results/`, they are how it publishes run state and outcomes as plain, self-describing JSON observable by any external process without coupling, log parsing, or file counting. Every directory outlives the run — `processing/` and `output/` are emptied, never removed.

## 5. Low-Level Tasks

```
Task: Validation Stage
Prompt: "Implement the Validation stage. Read each transaction record from shared/input, moving it into shared/processing while you work on it, and check it against the canonical schema: every required field present; amount a well-formed decimal string, positive or negative; currency a valid ISO 4217 code; transaction_type, metadata.channel and metadata.country present and well-formed. Annotate the records that pass with their validation result and write them to shared/output for the next stage. Write the records that fail directly to shared/results with a reason field naming the precise failure, such as 'invalid currency code: XYZ', and carry them no further. Emit an audit-trail entry for every record — ISO 8601 UTC timestamp, stage name, transaction ID, outcome — with no PII in plaintext."
File to CREATE: pipeline/validation.[ext]
Function to CREATE: validate_transaction(record: Transaction) -> ValidationResult
Details: Confirms the presence and type of every canonical field; confirms amount parses as a decimal rather than a float and treats a negative value as a legitimate refund; confirms currency is a real ISO 4217 code; rejects anything malformed or incomplete with a reason string specific enough to act on; leaves passing records untouched beyond the validation result it attaches.

Task: Fraud Detection Stage
Prompt: "Implement the Fraud Detection stage. Read validated records from shared/output, moving each into shared/processing while you work on it, and compute a weighted risk score between 0.00 and 1.00: add 0.50 when the absolute amount reaches $10,000 or its equivalent in the transaction's currency at current rates, 0.30 when the transaction is cross-border because source and destination account countries differ or metadata.country differs from the GB baseline, and 0.20 when the transaction's own timestamp falls outside 06:00-22:00 UTC. Sum the applicable weights, cap at 1.00, and flag for review at 0.50 or above. Never reject on the score: attach the score, the contributing factors, and the flag, then pass every record to Compliance Check via shared/output whether flagged or not. Emit an audit-trail entry per record."
File to CREATE: pipeline/fraud_detection.[ext]
Function to CREATE: score_transaction(record: Transaction, rates: ExchangeRates) -> FraudResult
Details: Produces a score explainable factor by factor, as GDPR Article 22 requires of profiling behind an automated decision; scores the absolute amount so refunds are judged by size; uses exchange rates supplied by the orchestrator rather than fetching any itself; reads any original field it needs from shared/input rather than assuming the inter-stage message carries it; takes timing from the transaction's own timestamp and never from the message envelope's; flags only, never rejects.

Task: Compliance Check Stage
Prompt: "Implement the Compliance Check stage. Read fraud-scored records from shared/output, moving each into shared/processing while you work on it, and apply the GDPR and Data Protection Act 2018 baseline to the record's PII and account data before it becomes eligible for settlement. Put records that fraud scoring flagged on hold for human review rather than rejecting them automatically, as GDPR Article 22 requires. Annotate the records that clear with their compliance result and write them to shared/output to continue to Settlement. Write the records that are held or rejected directly to shared/results with a reason field, joining the original transaction to the results gathered so far, and carry them no further. Emit an audit-trail entry per record."
File to CREATE: pipeline/compliance.[ext]
Function to CREATE: check_compliance(record: Transaction, fraud: FraudResult) -> ComplianceResult
Details: Applies the data-protection baseline uniformly to every record whatever its origin, as a privacy-by-design choice rather than a jurisdictional claim; confirms no PII is carried or logged in plaintext; converts a fraud flag into a hold with a stated reason instead of an automated adverse decision; returns cleared, held, or rejected, with a specific reason for anything but cleared; guarantees an uncleared record can never reach Settlement. AML and sanctions screening lie outside scope.

Task: Settlement Processing Stage
Prompt: "Implement the Settlement Processing stage. Read compliance-cleared records from shared/output, moving each into shared/processing while you work on it, and settle it against an internal simulated ledger with no external API call, no network call, and no data leaving to any third party. Produce a settlement record carrying an ISO 8601 UTC settlement timestamp, a generated unique settlement reference, and a status. Perform every monetary calculation with the precise decimal type. Annotate the record with its settlement result and write it back to shared/output for Reporting. Emit an audit-trail entry per record."
File to CREATE: pipeline/settlement.[ext]
Function to CREATE: settle_transaction(record: Transaction, compliance: ComplianceResult) -> SettlementResult
Details: Accepts only cleared records and refuses to settle anything whose compliance result is absent or not cleared; generates a settlement reference unique to each transaction; settles negative amounts as the legitimate refunds they are; notes that the settlement record falls under the 5-year retention period on GDPR's legal-obligation basis.

Task: Reporting Stage
Prompt: "Implement the Reporting stage. Read the finished records from shared/output and produce two outputs. Write the aggregate run summary to shared/report.json: total records ingested, counts of validated, rejected, flagged, held and settled, and aggregate risk indicators such as the distribution of scores and the total settled value per currency. Then write each transaction's final record to shared/results, joining the fresh original read from shared/input to the results gathered at every stage it reached, matched on transaction_id. When the stage finishes, shared/output and shared/processing must hold no files while both directories remain in place. Emit an audit-trail entry per record."
File to CREATE: pipeline/reporting.[ext]
Function to CREATE: build_report(records: list[ProcessedTransaction]) -> RunReport
Details: Counts transactions only, never counting the summary itself among them; joins on transaction_id rather than on position or read order; computes every monetary aggregate with the precise decimal type; keeps the summary at shared/report.json and the per-transaction finals in shared/results without mixing the two; leaves the shared tree standing, emptied rather than dismantled.
```
