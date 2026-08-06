# Specification Template — Transaction Processing Pipeline

The single source of truth for how a `specification.md` for this transaction-processing pipeline must be structured and produced. It is consumed independently by:

- the `specification-agent` subagent (`.claude/agents/specification.agent.md`) — input arrives entirely as text in its invocation prompt;
- the `write-spec` skill (`.claude/skills/write-spec/SKILL.md`) — input arrives entirely as slash-command arguments.

Neither depends on the other. Both read this file in full at the start of every invocation and follow it exactly — never a cached or remembered copy, since it may have changed since the last run. Neither explores the repository to discover input: **input is supplied, never hunted for.** Given the same input, both must produce the same document — and given no input at all, both must still produce a complete specification from the firm defaults below.

**Fixed and non-negotiable**: 5 top-level output sections, and exactly 5 Low-Level Tasks in a fixed stage order (Validation → Fraud Detection → Compliance Check → Settlement Processing → Reporting). Everything else — thresholds, rules, stack, report contents — derives from the input, via the Gap-Handling Protocol.

---

## Scope (firm)

**The specification describes the pipeline and nothing else.** The pipeline is exactly: an orchestrator plus the 5 stages, communicating through the `shared/` file tree, invoked as a plain CLI program.

Everything else in the surrounding project is a **separate deliverable, specified and built elsewhere** — and must not appear anywhere in the spec, in any section, in any framing, even as an aside, a rationale, or a "note." Non-exhaustive: front-ends, UIs, web servers, HTTP APIs, dashboards, monitoring tools, schedulers, tests and coverage targets, documentation, MCP servers, hooks, CI, packaging, deployment, presentations.

Two rules follow, and both are absolute:

1. **Never name an external tool or consumer.** Not a specific one, not a generic one. The spec never says who reads the pipeline's output, because the pipeline neither knows nor cares. Where the temptation arises, state the *pipeline's own obligation* instead — see the Pipeline file contract below, which exists precisely so run state is observable by anything, without the spec ever naming what.
2. **Never cite provenance.** Input documents are data, not references. The spec never mentions the assignment, homework, capstone, task numbering, agent names, this template, or the filenames it was derived from. It reads as a standalone technical specification written for the pipeline, with no trace of how it was produced. (`sample-transactions.json` is the sole exception, and only as the named default input fixture — never as a source of requirements.)

---

## Input Contract

**Every input is optional.** The pipeline's purpose, stages, and rules are already fully determined by this template — supplied input refines the specifics, it doesn't enable the document. An invocation with no input at all is normal and must produce a complete specification from the firm defaults below, with `[NEEDS CLARIFICATION: ...]` covering only what the defaults genuinely leave open (in practice: the stack).

What input can refine, when given:

1. **Transaction data** — sample record(s) or a description of the record shape, overriding the default schema.
2. **Stack/language** — never assume one if unstated; never infer it from files that happen to exist.
3. **Special constraints** — compliance regime, performance targets, specific risk rules.
4. **Business context** — domain constraints worth reflecting in the objectives.

Supplied context often arrives mixed with out-of-scope material (front-end requirements, test/coverage mandates, documentation and tooling deliverables). **Filter it against the Scope section above and carry through only what describes the pipeline itself.** Silently drop the rest — it is not a gap, so never mark it `[NEEDS CLARIFICATION]` and never note its exclusion in the spec.

**The defaults below apply only when the corresponding input isn't given — actual input always takes precedence.** Where a default is marked "firm," treat it as settled: don't add a `[NEEDS CLARIFICATION: ...]` marker for it unless the input contradicts it.

### Default transaction record schema

If the input supplies no schema of its own, or supplies a subset, fall back to:

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

- `amount` is a **string** holding a decimal value — never a binary float; Implementation Notes must say so explicitly.
- `currency` is expected to be ISO 4217, but sample data may deliberately include invalid codes (e.g. `XYZ`) — a case Validation must catch, not an error in the input.
- `amount` may be negative (refunds) — valid data, not malformed input.
- `metadata` is an open object; `channel` and `country` are what's been seen, not an exhaustive list.

If the actual data uses a different or extended schema, that data wins — use what's given.

**Data source and volume are never structural facts.** Describe ingestion from "an input transaction source" generically; name `sample-transactions.json` only as the default fallback fixture. Never bake today's sample record count into any section as if it were a design constraint — the pipeline handles an arbitrary, variable number of records.

### Pipeline file contract (firm)

Stages communicate only through files. The spec's Context section must describe this tree:

```
shared/
├── input/       ← the ingested records, one file per transaction; read-only once written
├── processing/  ← the currently-running stage's work in progress
├── output/      ← the last completed stage's messages, awaiting the next stage
├── results/     ← final destination only: exactly one final record per transaction
├── status.json  ← per-stage start/completion timestamps and processed/passed/failed counts, written live as the run progresses
└── report.json  ← the aggregate run summary, written once at the end
```

**`status.json` and `report.json` are a first-class requirement of the pipeline, not a convenience.** State them as an observability obligation: the pipeline publishes its run state and outcomes as plain, self-describing JSON, so that any external process can observe a run's progress and results without coupling to the pipeline, parsing its logs, or counting files across directories. Say it exactly that way — as what the pipeline owes, never as a service to a named reader.

### Default compliance regime (firm)

**GDPR only** (UK GDPR where the context is UK-specific) plus the Data Protection Act 2018 — governing PII handling (account numbers, names, any customer-identifying data) and the audit trail, and forming the Compliance Check stage's baseline rule set. AML/financial-crime regimes (e.g. UK MLR 2017, FCA customer due diligence) are explicitly **out of scope** — don't add AML-style checks unless the input asks.

**Apply uniformly to every record, regardless of the data's country mix.** GDPR's territorial scope normally follows where data subjects are, not where a sample dataset originates — so applying it to majority-non-EU/UK data is a **deliberate privacy-by-design choice, not a jurisdictional claim.** State it in those terms in both Implementation Notes and the Compliance Check task.

### Default fraud-detection scoring approach (firm)

A **transparent, weighted rule-based score** — never an opaque or learned model. This is a GDPR Article 22 consideration: profiling that drives an automated decision must have explainable logic. Score runs `0.00`–`1.00`; applicable weights sum, capped at `1.00`:

| Factor | Weight | Condition |
|---|---|---|
| High-value amount | `0.50` | absolute `amount` >= the high-value threshold (e.g. $10,000 or currency equivalent) |
| Cross-border mismatch | `0.30` | source/destination account country mismatch, or `metadata.country` differs from the baseline country |
| Unusual-hour timing | `0.20` | the transaction's own `timestamp` falls outside 06:00–22:00 **UTC** |

Flag for review at `>= 0.50` — the amount factor alone suffices, as does any two lesser factors. State these weights and the threshold plainly in Implementation Notes and the Fraud Detection task.

**All time logic is UTC.** The unusual-hour window is compared directly in UTC — no local-timezone conversion, no per-country offset table, no DST handling. Note also the distinction between a transaction's own `timestamp` (when it occurred) and an inter-stage message's `timestamp` (when that hop was written); timing checks always use the former.

**Baseline country**: default to the jurisdiction implied by the compliance regime (GB, per the GDPR default) — unless the transaction data clearly implies a different home jurisdiction (e.g. most records originate elsewhere), in which case use that. Keeping the fraud baseline and compliance jurisdiction consistent avoids flagging "cross-border" against one country while reasoning about another.

**Fraud Detection only flags — it never auto-rejects or auto-blocks.** Adverse action belongs to Compliance Check, satisfying Article 22's restriction on solely-automated decisions with legal or significant effects.

**Cite GDPR Article 22 by name** wherever this reasoning appears — in the scoring approach, in the flag-only rule, and in Compliance Check's hold-rather-than-reject behavior. Paraphrasing the restriction without naming the Article is not sufficient.

### Default settlement mechanism (firm)

Absent a named settlement partner or network, use **option 1**. Options 2 and 3 apply only if the input implies differentiated or externally-integrated settlement (routed by `transaction_type`/amount):

1. **Internal simulated ledger settlement** (firm default) — mark transactions settled with a settlement timestamp and generated reference; no external API or network call, no data shared with any third-party processor (data minimization). Simplest to implement and test.
2. **UK Faster Payments (FPS)-style** — near-real-time interbank settlement for standard domestic transfers below the per-payment limit.
3. **UK CHAPS-style** — same-day RTGS-style settlement for time-critical or high-value wire transfers.

Settlement and audit records containing account or PII data are retained for a firm default of **5 years** (standard UK financial record-keeping) under GDPR's "legal obligation" lawful basis, which overrides erasure requests during that window; records are purged or anonymized afterwards. If option 2 or 3 is used, mark the partner/protocol integration specifics `[NEEDS CLARIFICATION: ...]`.

### Default performance/scalability targets (firm)

**99.99% uptime** and sustained throughput of up to **100,000 transactions/second**.

These are **design targets the architecture is held to, not a benchmark the sample run must demonstrate** — no artificial single-threaded bottlenecks, no per-transaction blocking I/O that would cap throughput far below target. State both numbers in Implementation Notes, phrased so they can't be read as a claim that the pipeline has been load-tested at that scale.

---

## Step 1 — Extract From Input

Extract, filtering everything through the Scope section:

- the one-sentence purpose of the pipeline (→ §1)
- concrete, testable behavioral requirements (→ §2)
- technical constraints: monetary types, currency handling, logging, PII (→ §3)
- starting and ending file-system state (→ §4)
- anything shaping the 5 stages' specific rules (→ §5)

Do not invent business context that wasn't given or implied. If the input is thin, proceed to Step 2 before writing anything.

## Step 2 — Gap-Handling Protocol

- **Reasonably inferable from what's given** (e.g. decimal typing from the `amount` field's shape, risk logic from a stated business constraint): infer conservatively, and phrase it as derived rather than asserted as fact.
- **Genuinely unstated and not inferable** (no stack preference anywhere, no compliance regime named, no thresholds given): never silently invent, and never stop to ask. Write it inline as `[NEEDS CLARIFICATION: <specific question>]` and keep going. This applies to every consumer, including ones that *could* ask the user — a gap belongs in the document as a marker, so the output stays reproducible and non-blocking.

Never fabricate numeric thresholds, named regulations, or business rules unsupported by the input. Generic best practices this template already mandates (ISO 8601 timestamps, decimal-never-float) need no marker.

Out-of-scope material is **not** a gap — drop it per the Scope section rather than marking it.

**One marker per open question, never several for the same one.** An unresolved stack is a single gap, however many downstream details it touches (decimal type, module extensions, tooling) — it gets exactly one marker, not one per consequence. When no stack is given, that marker is a pinned string: place it at the end of the monetary-values bullet in Implementation Notes, verbatim, and nowhere else in the document:

```
[NEEDS CLARIFICATION: stack/language for the pipeline — none was specified, so the concrete decimal type cannot be named]
```

Everything else the stack would have settled is simply written generically, with no further marker and no commentary about the choice being pending.

## Step 3 — Write `specification.md`

The document's first line is pinned — reproduce it exactly, never reworded:

```markdown
# Specification — Transaction Processing Pipeline
```

Then exactly these 5 sections, in order, under these exact headings (`## 1. High-Level Objective`, `## 2. Mid-Level Objectives`, `## 3. Implementation Notes`, `## 4. Context`, `## 5. Low-Level Tasks`), with a banking emphasis throughout (compliance, PII/security, audit trail, precise monetary handling) rather than generic software-project content.

**1. High-Level Objective** — one sentence, derived from Step 1.

**2. Mid-Level Objectives** — a **numbered** list (`1.`, `2.`, …, never bullets) of concrete, testable requirements, favoring the banking angle: compliance hooks, data-protection measures, audit/logging, observability, performance. Include only what the input supports plus what's structurally implied by the 5 stages (e.g. "records failing validation are written to `shared/results/` with a reason field" is safe even with minimal input). 4–5 is typical; go higher only when each addition is genuinely distinct, and never pad or force-merge to hit a number.

**3. Implementation Notes** — must state: precise decimal type, never binary float (name the concrete type if the stack is known, otherwise state it generically and flag the stack per Step 2); ISO 4217 currency codes; negative amounts are valid; audit trail with timestamp, stage name, transaction ID, outcome; PII never logged in plaintext; UTC-only time handling; association by `transaction_id`, never by position or read order; and the compliance regime, fraud-scoring approach, settlement mechanism with its retention period, and performance targets per the firm defaults above (or whatever the input names). Plus any additional constraint from Step 1.

**4. Context** — *Beginning context*: the input transaction source and the state before a run. *Ending context*: the `shared/` tree per the Pipeline file contract, with what each path holds once the run finishes.

**5. Low-Level Tasks** — exactly 5, in the fixed order. Each in this exact format:

```
Task: [Pipeline Stage Name]
Prompt: "[Exact prompt to give the code-generation agent]"
File to CREATE: [path]
Function to CREATE: [function signature]
Details: [What the stage checks, transforms, or decides]
```

**`Task`, `File to CREATE`, and `Function to CREATE` are pinned strings — copy them verbatim from this table, never paraphrase or re-derive them:**

| Task | File to CREATE | Function to CREATE |
|---|---|---|
| `Validation Stage` | `pipeline/validation.[ext]` | `validate_transaction(record: Transaction) -> ValidationResult` |
| `Fraud Detection Stage` | `pipeline/fraud_detection.[ext]` | `score_transaction(record: Transaction, rates: ExchangeRates) -> FraudResult` |
| `Compliance Check Stage` | `pipeline/compliance.[ext]` | `check_compliance(record: Transaction, fraud: FraudResult) -> ComplianceResult` |
| `Settlement Processing Stage` | `pipeline/settlement.[ext]` | `settle_transaction(record: Transaction, compliance: ComplianceResult) -> SettlementResult` |
| `Reporting Stage` | `pipeline/reporting.[ext]` | `build_report(records: list[ProcessedTransaction]) -> RunReport` |

The one permitted adaptation: when a stack **is** given, re-spell the signatures in that language's own syntax and naming convention, keeping the same function names, parameters, and return types. With no stack given, reproduce them exactly as written. `[ext]` stays literal until a stack is known.

`File to CREATE` identifies which stage each module implements — the code-generation agent settles the final on-disk layout from its own conventions research, so never elaborate beyond the pinned path.

Only `Prompt` and `Details` are written fresh: their **substance** comes from Step 1 and the firm defaults, stated in your own words.

## Step 4 — Self-Check (before writing)

Fix anything that fails, then write:

- [ ] **Pinned strings reproduced verbatim**: the document title, the 5 section headings, and every `Task` / `File to CREATE` / `Function to CREATE` value from Step 3's table — no rewording, no re-derivation (signatures re-spelled in the resolved language only when a stack was given)
- [ ] All 5 sections present and in order; Context has both Beginning and Ending
- [ ] Mid-Level Objectives are each concrete and testable, none padded or force-merged
- [ ] Implementation Notes covers every item listed in Step 3, and names GDPR Article 22 explicitly where the flag-only / hold-rather-than-reject reasoning appears
- [ ] Exactly 5 Low-Level Tasks, in the fixed order, each with all 5 fields
- [ ] **One marker per open question.** With no stack given, exactly one `[NEEDS CLARIFICATION: ...]` appears in the whole document — the pinned stack string on the monetary-values bullet — and nothing else notes the stack as pending
- [ ] **Scope**: nothing outside the orchestrator + 5 stages is requested or described anywhere — no front-end, UI, web server, dashboard, monitoring tool, test/coverage target, documentation, MCP server, hook, CI, or presentation, in any section or framing
- [ ] **No external consumer or tool is named anywhere**; run-state observability is stated as the pipeline's own obligation via `status.json`/`report.json`
- [ ] **No provenance**: no mention of the assignment, homework, capstone, task numbering, agent names, this template, or any source filename (only `sample-transactions.json`, and only as the default input fixture)
- [ ] No business rule, threshold, or regulation invented without support — unsupported specifics carry `[NEEDS CLARIFICATION: ...]`, and no gap was resolved by asking an interactive question

## Step 5 — Output

**Always regenerate from scratch.** If a file exists at the target path, do not read it, reuse it, or treat it as correct — it may predate this invocation's input or this version of the template. Overwrite it with the draft from Steps 1–4.

Write to the path given (default `specification.md` in the current working directory). Produce **only that one file** — no other files, no other side effects. Then report: the path written, and every `[NEEDS CLARIFICATION: ...]` marker left in the document, so the caller knows what to resolve before the spec reaches the code-generation agent.
