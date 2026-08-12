# Specification Template — Transaction Processing Pipeline

The single source of truth for how a `specification.md` for this transaction-processing pipeline must be structured and produced. It is consumed independently by:

- the `specification-agent` subagent (`.claude/agents/specification.agent.md`) — input arrives entirely as text in its invocation prompt;
- the `write-spec` skill (`.claude/skills/write-spec/SKILL.md`) — input arrives entirely as slash-command arguments.

Neither depends on the other. Both read this file in full at the start of every invocation and follow it exactly — never a cached or remembered copy, since it may have changed since the last run. Neither explores the repository to discover input: **input is supplied, never hunted for.** Given the same input, both must produce the same document — and given no input at all, both must still produce a complete specification from the firm defaults below.

**Fixed and non-negotiable**: 5 top-level output sections followed by 3 appendices (`## Stage Services`, `## API Gateway`, `## UI`, in that order), and exactly 5 Low-Level Tasks in a fixed stage order (Validation → Fraud Detection → Compliance Check → Settlement Processing → Reporting). That order is the **orchestrator's** order and is never negotiable; the reorderability the Stage independence contract makes possible belongs to the API Gateway alone and never alters §5's table. Everything else — thresholds, rules, stacks, report contents — derives from the input, via the Gap-Handling Protocol.

The document involves **three independent stacks**: the pipeline's, the service layer's (shared by the stage services and the gateway), and the UI's. They are resolved separately and never inferred from one another.

---

## Scope (firm)

**The specification describes the pipeline, and the pipeline is the whole point of the document.** The pipeline is exactly: an orchestrator plus the 5 stages, communicating through the `shared/` file tree, invoked as a plain CLI program. Sections 1–5 are about the pipeline and only the pipeline.

Everything else in the surrounding project is a **separate deliverable, specified and built elsewhere** — and must not appear anywhere in sections 1–5, in any framing, even as an aside, a rationale, or a "note." Non-exhaustive: monitoring tools, schedulers, tests and coverage targets, documentation, MCP servers, hooks, CI, packaging, deployment, presentations.

### The three appendices

Three things beyond the pipeline are permitted, each confined to its own appendix after §5, in this fixed order: **`## Stage Services`**, **`## API Gateway`**, **`## UI`**. All three are always present — none is optional, and none may be declined by input.

All three are subject to the same three absolute limits:

- **They never appear in sections 1–5.** Those sections are written exactly as though no appendix existed, and would still be complete and correct if all three were deleted.
- **They never change a pipeline rule.** Where anything in an appendix would conflict with a pipeline rule, default, or contract — the file contract, the CLI-only invocation, the orchestrator's fixed stage order, the stage behavior, the 5 pinned Low-Level Tasks — **the pipeline wins and the appendix requirement is dropped**, silently and without a marker.
- **They stay proportionate.** No appendix grows to rival the pipeline's treatment, and no appendix concern is ever elaborated at the expense of a pipeline one.

**HTTP, web servers, ports and network protocols are permitted inside the `## Stage Services` and `## API Gateway` appendices only.** Everywhere else in the document — above all in sections 1–5 — they remain banned exactly as before. The pipeline is a CLI program that speaks to no network.

Two rules follow, and both are absolute:

1. **Sections 1–5 never name an external tool or consumer.** Not a specific one, not a generic one. Those sections never say who reads the pipeline's output, because the pipeline neither knows nor cares — and this holds even though stage services, a gateway and a UI are specified elsewhere in the same document. Where the temptation arises, state the *pipeline's own obligation* instead — see the Pipeline file contract below, which exists precisely so run state is observable by anything, without those sections ever naming what. Each appendix is the sole place its own subject may be named.
2. **Never cite provenance.** Input documents are data, not references. The spec never mentions the assignment, homework, capstone, task numbering, agent names, this template, or the filenames it was derived from. It reads as a standalone technical specification written for the pipeline, with no trace of how it was produced. (`sample-transactions.json` is the sole exception, and only as the named default input fixture — never as a source of requirements.)

---

## Input Contract

**Every input is optional.** The pipeline's purpose, stages, and rules are already fully determined by this template — supplied input refines the specifics, it doesn't enable the document. An invocation with no input at all is normal and must produce a complete specification from the firm defaults below, with `[NEEDS CLARIFICATION: ...]` covering only what the defaults genuinely leave open (in practice: the pipeline stack, the service layer's HTTP framework, and the UI stack — see Step 2).

What input can refine, when given:

1. **Transaction data** — sample record(s) or a description of the record shape, overriding the default schema.
2. **Stack/language** — never assume one if unstated; never infer it from files that happen to exist. The three stacks are **independent**: any may be given without the others, and they need not match. The one fixed relation: the service layer's *language* always follows the pipeline's, because the services import the stage functions directly — so only the service layer's **HTTP framework** is separately supplied.
3. **Special constraints** — compliance regime, performance targets, specific risk rules.
4. **Business context** — domain constraints worth reflecting in the objectives.
5. **UI stack or UI requirements** — routed to the `## UI` appendix, never into sections 1–5.
6. **Service-layer HTTP framework, gateway stage order, service ports or URLs** — routed to the `## Stage Services` / `## API Gateway` appendices, never into sections 1–5.

Supplied context often arrives mixed with out-of-scope material (test/coverage mandates, documentation and tooling deliverables). **Filter it against the Scope section above and carry through only what describes the pipeline itself or belongs in one of the three appendices.** Silently drop the rest — it is not a gap, so never mark it `[NEEDS CLARIFICATION]` and never note its exclusion in the spec.

Front-end and service-layer material is not dropped: route each to the appendix that owns it. But route only what fits that appendix's firm default — anything beyond it (authentication, persistence of its own, analytics, a monitoring surface, a second front-end, service-to-service messaging) is still out of scope and still dropped silently.

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

### Stage independence contract (firm)

**Every stage is fully independent of every other.** No stage requires another to have run first, and the 4 processing stages produce a correct, complete run in any order. This is a property of the pipeline itself, not of anything built on top of it — it holds when the orchestrator runs them in its own fixed order, and it is what makes a configurable order possible at all. State it in §§1–5 as a pipeline requirement, never with reference to what exploits it.

Three rules make it true, and all three belong in §§1–5:

1. **Uniform contract.** Every stage takes the transaction record plus an accumulated context of the stage results produced so far, and returns only its own result. Any prior result may be absent from that context, and **absence is a normal, expected condition — never an error**. A stage that cannot evaluate a rule because the annotation it would key on is missing records an explicit *not-applicable* outcome naming what was missing, and continues. It never throws, never guesses the missing value, never re-derives another stage's result, and never treats absence as a clean pass.
2. **No stage terminates a transaction.** Stages annotate; they never reject, drop, or route a record out of the flow. **Every transaction traverses every stage**, whatever its validation, fraud or compliance outcome. An adverse finding is recorded as that stage's result and nothing more.
3. **Reporting is terminal and owns the verdict.** Reporting always runs last — the one stage whose position is fixed — and computes each transaction's single final verdict from the accumulated annotations, then writes the final records. **It is the only stage that writes to `results/`.**

**Verdict precedence** (highest wins), pinned:

| Precedence | Condition | Verdict |
|---|---|---|
| 1 | any stage did not run | `INCOMPLETE` |
| 2 | validation failed | `REJECTED` (validation) |
| 3 | compliance rejected | `REJECTED` (compliance) |
| 4 | compliance held | `HELD` |
| 5 | settled | `SETTLED` |
| — | none of the above | `INCOMPLETE` |

A fraud flag is **never a verdict**. It is recorded as an attribute of whatever verdict applies — consistent with the firm rule below that Fraud Detection only flags and never rejects. And a transaction is never reported `SETTLED` on a run where some stage did not run: rule 1 outranks everything else, so a missing stage yields `INCOMPLETE` rather than a verdict inferred from the annotations that happen to have survived.

Every final record names which stages ran and which did not, so the verdict is always traceable to the evidence behind it.

Cover this contract in Mid-Level Objectives as testable requirements, in Implementation Notes, and in the `Details` of each Low-Level Task.

### Pipeline file contract (firm)

Stages communicate only through files. The spec's Context section must describe this tree:

```
shared/
├── input/       ← the ingested records, one file per transaction; read-only for the run's duration, emptied of files once the run finishes successfully (every stage needing an original field has already read it by then; the directory itself is never removed)
├── processing/  ← the currently-running stage's work in progress
├── output/      ← the last completed stage's messages, awaiting the next stage
├── results/     ← final destination only: exactly one final record per transaction, written solely by Reporting (no other stage writes here, per the Stage independence contract)
├── status.json  ← per-stage start/completion timestamps and processed/passed/failed counts, written live as the run progresses
└── report.json  ← the aggregate run summary, written once at the end
```

**`status.json` and `report.json` are a first-class requirement of the pipeline, not a convenience.** State them as an observability obligation: the pipeline publishes its run state and outcomes as plain, self-describing JSON, so that any external process can observe a run's progress and results without coupling to the pipeline, parsing its logs, or counting files across directories. Say it exactly that way — as what the pipeline owes, never as a service to a named reader.

### Standalone validation of the input source (firm)

**The Validation stage is invocable on its own, to check the input source without processing it.** In this mode it reads every record from the input transaction source, applies exactly the same validation rules a full run applies, and reports each record's identifier, its pass/fail verdict and the reason for any failure, together with the total, valid and invalid counts.

**It changes nothing.** No part of the `shared/` tree is read, created, or modified; no record is altered; nothing is written anywhere. The state of a run in progress or already finished is untouched by it.

State this as an obligation the pipeline owes — the input source can be checked for validity independently of, and without disturbing, a processing run. As with `status.json` and `report.json`, say what the pipeline provides, never who or what makes use of it. It reads the input transaction source directly, never `shared/input/`, whose contents exist only for the duration of a run.

Cover it in Mid-Level Objectives as a testable requirement, and in the Validation Stage's `Details` in Low-Level Tasks. It adds no entry to the pinned Low-Level Tasks table.

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

**Fraud Detection only flags — it never auto-rejects or auto-blocks.** Adverse action belongs to Compliance Check, satisfying Article 22's restriction on solely-automated decisions with legal or significant effects. Under the Stage independence contract, "adverse action" means Compliance *records* a hold or rejection as its own result — it still never removes the transaction from the flow.

**When Compliance runs with no fraud annotation in its context** — because Fraud Detection has not run yet in the order it was given — it evaluates every rule that does not depend on a risk score, and records the fraud-conditional rule as *not-applicable*, naming the missing annotation as the reason. It never computes the score itself, never substitutes a default or assumed score, and never reads the absence as a clean result.

**Cite GDPR Article 22 by name** wherever this reasoning appears — in the scoring approach, in the flag-only rule, and in Compliance Check's hold-rather-than-reject behavior. Paraphrasing the restriction without naming the Article is not sufficient.

### Default settlement mechanism (firm)

Absent a named settlement partner or network, use **option 1**. Options 2 and 3 apply only if the input implies differentiated or externally-integrated settlement (routed by `transaction_type`/amount):

1. **Internal simulated ledger settlement** (firm default) — mark transactions settled with a settlement timestamp and generated reference; no external API or network call, no data shared with any third-party processor (data minimization). Simplest to implement and test.
2. **UK Faster Payments (FPS)-style** — near-real-time interbank settlement for standard domestic transfers below the per-payment limit.
3. **UK CHAPS-style** — same-day RTGS-style settlement for time-critical or high-value wire transfers.

Under the Stage independence contract, **Settlement annotates every transaction it receives**, whatever Compliance recorded and whether or not Compliance has run at all. A transaction that has not cleared compliance is not marked settled — it receives an explicit *not-settled* result naming the reason, and where the compliance annotation is simply absent, that reason is the missing annotation. Whether a transaction ultimately counts as settled is Reporting's verdict to make, never Settlement's.

Settlement and audit records containing account or PII data are retained for a firm default of **5 years** (standard UK financial record-keeping) under GDPR's "legal obligation" lawful basis, which overrides erasure requests during that window; records are purged or anonymized afterwards. If option 2 or 3 is used, mark the partner/protocol integration specifics `[NEEDS CLARIFICATION: ...]`.

### Default performance/scalability targets (firm)

**99.99% uptime** and sustained throughput of up to **100,000 transactions/second**.

These are **design targets the architecture is held to, not a benchmark the sample run must demonstrate** — no artificial single-threaded bottlenecks, no per-transaction blocking I/O that would cap throughput far below target. State both numbers in Implementation Notes, phrased so they can't be read as a claim that the pipeline has been load-tested at that scale.

### Stage Services (firm, always present)

Each of the 5 stages is additionally exposed as its **own independently deployable HTTP service** — a thin wrapper, never a reimplementation. The pipeline is untouched by their existence: the orchestrator continues to call the stage functions directly, in-process, in its own fixed order, and never speaks HTTP.

Firm defaults:

- **Location**: one directory per service under `services/`, named for the stage it wraps.
- **Language**: the pipeline's, necessarily — each service imports its stage's core function and calls it unchanged. There is no second implementation of any stage rule, so a service and an orchestrator run can never disagree about a record.
- **HTTP framework**: not assumed. If input names one, use it; otherwise mark it once, per Step 2. It is shared with the gateway.
- **Contract**: a service accepts **one** transaction record plus the accumulated context, and returns its stage's own result. The request and response shapes are **identical across all 5 services** — that uniformity is what lets a caller treat them as interchangeable. **Reporting is no exception**: it is called per transaction like the rest, which is why the gateway produces no batch aggregate. Batching, where it happens at all, is the caller's loop and never a service's concern.
- **Stateless.** A service reads and writes **nothing** on disk: no part of `shared/`, no file of its own, no database, no cache. Everything it needs arrives in the request; everything it produces leaves in the response. `shared/` remains exclusively the orchestrator's.
- **Services never call one another** and hold no knowledge of any other service — no successor URL, no ordering, no notion that other stages exist. Sequencing belongs entirely to the caller.
- **Absent context is normal**, exactly as the Stage independence contract requires: a service given a partial or empty context returns a valid result carrying a *not-applicable* outcome, never an error.

### API Gateway (firm, always present)

A single HTTP gateway accepts submitted transactions and drives them through the stage services **in a configurable order**.

Firm defaults:

- **Location**: `gateway/` at the project root.
- **Stack**: the service layer's — same language, same HTTP framework, same single marker.
- **API — two submission endpoints, differing only in arity.** One accepts a **single transaction record** and returns that transaction's accumulated stage results and final verdict. The other accepts an **array of records** and returns an array of exactly those same per-transaction objects. **The response mirrors the request**: an object in yields an object out, an array in yields an array out — the batch response is the single response repeated, never a differently-shaped or aggregated one. Both drive every transaction through the same chain in the same configured order, and each transaction is processed independently of the others in its batch.
- **No run summary.** Reporting is invoked once per transaction, so a batch returns per-transaction verdicts and nothing else — no aggregate counts, no batch report. This follows from the uniform service contract rather than overriding it: aggregate summaries belong to the pipeline's own `report.json`, which the gateway neither produces nor touches.
- **Configurable order — the gateway's alone.** A configuration file read at startup lists the 4 reorderable stages in the order to invoke them, together with each service's base URL. Changing that file changes the order; nothing else does. **Reporting is always invoked last and is never part of the reorderable list.** The orchestrator's fixed order is entirely unaffected by this file and never reads it — the two orders are independent, and the pipeline's is not configurable at all.
- **Orchestration, not choreography.** The gateway calls each service in turn, accumulating each result into the context it passes to the next. Services are never asked to forward anything to one another.
- **Failure handling**: if a stage service is unreachable or errors, retry **3 times**, then **skip that stage and continue the chain**, recording that the stage did not run. Per the verdict precedence, a skipped stage makes the transaction's final verdict `INCOMPLETE` — so a lost stage degrades the result honestly rather than failing the request or inventing a verdict.
- **Stateless, like the services**: the gateway writes nothing into `shared/` and reads nothing from it. A gateway request and an orchestrator run can therefore run concurrently without interfering, because they share no state.

Describe both appendices **stack-agnostically** beyond what input supplied: state what they must do, never which framework, server, or client library does it.

### UI (firm, always present, secondary)

A minimal UI accompanies the pipeline. It is **not** part of the pipeline and never a precondition for it — but it is always specified and always built, exactly like the service layer. There is no declining it: a missing UI stack is a marker to resolve (Step 2), never grounds for omitting the section or skipping the front-end.

When the UI section states this independence, the subject of the sentence is **the pipeline, never the UI** — the claim is that *the pipeline* is complete, correct, and fully usable from the CLI with no front-end present. Writing it the other way round ("the UI is fully usable from the CLI…") is nonsense; keep the two apart.

Its responsibilities are exactly these three, and nothing else:

1. **Start a pipeline run.**
2. **Show run status in real time** while a run is in progress.
3. **Present a small dashboard** of results, in the verdict vocabulary §5 defines — never a generic pass/fail one:
   - counts per verdict (`SETTLED`, `HELD`, `REJECTED`, `INCOMPLETE`);
   - each transaction's own verdict and the reason behind it;
   - **the fraud flag surfaced as an attribute alongside the verdict**, never as a verdict of its own — matching the rule that Fraud Detection only flags;
   - which stages ran and which did not for each transaction, so an `INCOMPLETE` verdict is traceable to the stage that produced it.

Anything beyond those three — editing or submitting transactions, calling the API gateway, showing service state, authentication, user accounts, persistence of its own, historical runs, analytics, configuration screens, export, alerting — is out of scope and is dropped silently. **The UI knows nothing of the stage services or the gateway**; it starts runs through the pipeline's CLI and reads the `shared/` tree, and that is all.

Firm defaults:

- **Location**: a `ui/` directory at the project root.
- **Data source**: it reads the `shared/` tree the pipeline already writes — the aggregate counts from `report.json`, live progress from `status.json`, and **each transaction's verdict from its record in `results/`**, since the aggregate summary carries counts rather than per-transaction detail. It never reads the pipeline's source, never imports its modules, never writes anywhere inside `shared/`, and never requires the pipeline to produce anything it does not already produce under the Pipeline file contract. Starting a run means invoking the pipeline exactly as the CLI does.
- **Stack**: independent of the pipeline's and the service layer's, and never assumed. If input names one, use it; if not, mark it (Step 2) — a missing UI stack never blocks the document.

Describe the UI **stack-agnostically**: state what it must do, never which framework, library, bundler, styling approach, or component model does it. Naming any of those when input didn't supply them is inventing, exactly as it would be for the pipeline.

**Input cannot decline the UI.** A request for no front-end is out-of-scope material like any other — dropped silently, not honored and not marked. The `## UI` section is always written in full.

---

## Step 1 — Extract From Input

Extract, filtering everything through the Scope section:

- the one-sentence purpose of the pipeline (→ §1)
- concrete, testable behavioral requirements (→ §2)
- technical constraints: monetary types, currency handling, logging, PII (→ §3)
- starting and ending file-system state (→ §4)
- anything shaping the 5 stages' specific rules (→ §5)
- anything describing the UI, kept separate from all of the above (→ UI section)

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

**The UI stack is a second, independent gap** with its own single marker, placed in the UI section and nowhere else. When no UI stack is given, that marker is also a pinned string, reproduced verbatim:

```
[NEEDS CLARIFICATION: stack/framework for the UI — none was specified]
```

**The service layer's HTTP framework is a third, independent gap** with its own single marker, placed in the `## Stage Services` appendix and nowhere else — not repeated in `## API Gateway`, which shares the same framework and simply refers to it. When no framework is given, that marker is also a pinned string, reproduced verbatim:

```
[NEEDS CLARIFICATION: HTTP framework for the stage services and API gateway — none was specified]
```

Note what this marker does **not** cover: the service layer's *language* is never a gap, because it always follows the pipeline's. Where the pipeline stack is itself unresolved, the service layer's language is unresolved with it — that is the pipeline-stack marker's business, and it gets no second marker here.

The three markers are resolved separately and none implies another: a spec may carry all three, any subset, or none. Never merge them, and never let one stack silently settle another. With no input at all, the finished document therefore carries exactly three `[NEEDS CLARIFICATION: ...]` markers — these three, and nothing else.

Input cannot decline the UI, so this marker is never replaced by a "none required" note — when no UI stack is given, the marker appears, full stop.

## Step 3 — Write `specification.md`

The document's first line is pinned — reproduce it exactly, never reworded:

```markdown
# Specification — Transaction Processing Pipeline
```

Then exactly these 5 sections, in order, under these exact headings (`## 1. High-Level Objective`, `## 2. Mid-Level Objectives`, `## 3. Implementation Notes`, `## 4. Context`, `## 5. Low-Level Tasks`), with a banking emphasis throughout (compliance, PII/security, audit trail, precise monetary handling) rather than generic software-project content.

These 5 sections are the specification. Three further sections — `## Stage Services`, `## API Gateway`, `## UI`, in that order — follow them, described at the end of this step; they are appendices to the document, never peers of the five.

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
| `Validation Stage` | `pipeline/validation.[ext]` | `validate_transaction(record: Transaction, context: StageContext) -> ValidationResult` |
| `Fraud Detection Stage` | `pipeline/fraud_detection.[ext]` | `score_transaction(record: Transaction, context: StageContext, rates: ExchangeRates) -> FraudResult` |
| `Compliance Check Stage` | `pipeline/compliance.[ext]` | `check_compliance(record: Transaction, context: StageContext) -> ComplianceResult` |
| `Settlement Processing Stage` | `pipeline/settlement.[ext]` | `settle_transaction(record: Transaction, context: StageContext) -> SettlementResult` |
| `Reporting Stage` | `pipeline/reporting.[ext]` | `build_report(records: list[ProcessedTransaction]) -> RunReport` |

`StageContext` is a mapping from stage name to that stage's result, holding only what has been produced so far — **any entry may be absent, and every stage must behave correctly when one is.** No stage takes another stage's result as a named parameter: that is precisely the coupling the Stage independence contract removes, and reintroducing it in any signature is a defect. Reporting is the exception to the shape, not to the principle — it receives the whole batch because it computes the aggregate and the per-transaction verdicts.

The one permitted adaptation: when a stack **is** given, re-spell the signatures in that language's own syntax and naming convention, keeping the same function names, parameters, and return types. With no stack given, reproduce them exactly as written. `[ext]` stays literal until a stack is known.

`File to CREATE` identifies which stage each module implements — the code-generation agent settles the final on-disk layout from its own conventions research, so never elaborate beyond the pinned path.

**Every stage's `Details` must state how it behaves when the context is empty or partial** — which of its rules it can still evaluate, and that the rest are recorded as *not-applicable* naming what was missing — and that it annotates without ever terminating the transaction. Reporting's `Details` additionally carries the verdict precedence table and its sole ownership of `results/`.

The Validation Stage's `Details` must additionally cover its standalone, non-mutating invocation per the firm default above — what it reports and that it writes nothing. This adds no row to the table and no second `Function to CREATE`.

Only `Prompt` and `Details` are written fresh: their **substance** comes from Step 1 and the firm defaults, stated in your own words.

### Then the three appendices

After §5, exactly three sections follow, in this order, under these exact headings: `## Stage Services`, `## API Gateway`, `## UI`. Each is short and visibly an appendix beside the pipeline's treatment. None adds a `Task`, a row to §5's pinned table, or a `Function to CREATE`, and none restates, qualifies, or reinterprets anything in §§1–5.

**`## Stage Services`** states, and states nothing more:

- **Purpose** — each of the 5 stages additionally exposed as its own independently deployable HTTP service, wrapping the stage's existing function without reimplementing it.
- **Location** — one directory per service under `services/`, unless input names another.
- **Contract** — the uniform request/response shape shared by all 5, in your own words: transaction plus accumulated context in, that stage's own result out; a partial or empty context is valid input and yields a *not-applicable* outcome, not an error.
- **Constraints** — stateless (nothing on disk, nothing in `shared/`); services never call one another and know of no other service; the orchestrator is unaffected and never speaks HTTP.
- **Stack** — the pipeline's language, plus whatever HTTP framework input named, or the pinned marker from Step 2.

**`## API Gateway`** states, and states nothing more:

- **Purpose** — accepts submitted transactions and drives them through the stage services, returning each transaction's accumulated results and final verdict.
- **Endpoints** — two, differing only in arity: one taking a single record and returning one result object, one taking an array and returning an array of those same objects. State that the response mirrors the request and that no aggregate summary is returned.
- **Location** — `gateway/` at the project root, unless input names another.
- **Configurable order** — a startup configuration file listing the 4 reorderable stages in invocation order and each service's base URL; Reporting always last and never in that list. Say plainly that this order is the gateway's alone and that **the orchestrator's fixed order is unaffected and not configurable**.
- **Failure handling** — retry 3 times, then skip the stage and continue, recording it as not-run; the resulting verdict is `INCOMPLETE` per §5's precedence.
- **Constraints** — stateless; writes nothing into `shared/` and reads nothing from it; sequencing lives here and nowhere else.
- **Stack** — the service layer's; refer to the `## Stage Services` marker rather than repeating it.

**`## UI`** — one final section under the exact heading `## UI`. Keep it short — a handful of lines, visibly an appendix beside the pipeline's treatment. It states, and states nothing more:

- **Responsibilities** — the three from the UI firm default, in your own words, stack-agnostically.
- **Location** — `ui/` at the project root, unless input names another.
- **Data source** — that it reads the `shared/` tree and starts a run by invoking the pipeline's CLI; that it writes nothing into `shared/` and imports no pipeline code.
- **Stack** — whatever input named, or the pinned marker from Step 2.

All three appendices are written in full on every invocation. A request for no front-end is dropped as out-of-scope material and changes nothing here.

## Step 4 — Self-Check (before writing)

Fix anything that fails, then write:

- [ ] **Pinned strings reproduced verbatim**: the document title, the 5 section headings, and every `Task` / `File to CREATE` / `Function to CREATE` value from Step 3's table — no rewording, no re-derivation (signatures re-spelled in the resolved language only when a stack was given)
- [ ] All 5 sections present and in order, followed by `## Stage Services`, `## API Gateway`, `## UI` in that order; Context has both Beginning and Ending
- [ ] Mid-Level Objectives are each concrete and testable, none padded or force-merged
- [ ] Implementation Notes covers every item listed in Step 3, and names GDPR Article 22 explicitly where the flag-only / hold-rather-than-reject reasoning appears
- [ ] Exactly 5 Low-Level Tasks, in the fixed order, each with all 5 fields
- [ ] **Stage independence contract stated in §§1–5**: the uniform `(record, context)` contract with absent entries normal; no stage terminating a transaction; Reporting terminal, owning the verdict and solely writing `results/`; the pinned verdict precedence table with a skipped stage yielding `INCOMPLETE` and a fraud flag never being a verdict
- [ ] **No signature takes another stage's result as a named parameter** — every one matches Step 3's table exactly
- [ ] Each stage's `Details` states its behavior on an empty or partial context, naming what it records as *not-applicable*
- [ ] Validation's standalone, non-mutating invocation appears in both Mid-Level Objectives and the Validation Stage's `Details`, stated as the pipeline's own obligation with no consumer named, and adds no row to the pinned table
- [ ] **One marker per open question.** With no stack or framework given at all, exactly three `[NEEDS CLARIFICATION: ...]` markers appear in the whole document — the pinned pipeline-stack string on the monetary-values bullet, the pinned service-layer-framework string in `## Stage Services`, and the pinned UI-stack string in `## UI` — each appearing once, with nothing else noting any of them as pending
- [ ] **Scope**: nothing outside the orchestrator + 5 stages is requested or described in §§1–5 — no HTTP, web server, port, network protocol, monitoring tool, test/coverage target, documentation, MCP server, hook, CI, or presentation, in any framing
- [ ] **§§1–5 name no external consumer or tool**; run-state observability is stated as the pipeline's own obligation via `status.json`/`report.json`, and the services, gateway and UI are not named, alluded to, or implied anywhere in those five sections
- [ ] **Stage independence is stated in §§1–5 as a pipeline property**, never justified by the gateway's reordering or by anything else that consumes it
- [ ] **All three appendices present**, always — none omitted, none replaced by a "not required" note, whatever the input asked for
- [ ] **The UI dashboard is described in §5's verdict vocabulary**, with the fraud flag surfaced as an attribute rather than a verdict, and with stages-run visibility; it reads per-transaction verdicts from `results/` and knows nothing of the services or gateway
- [ ] **The gateway's configurable order is stated as the gateway's alone**, with the orchestrator's fixed order explicitly unaffected and not configurable, and Reporting excluded from the reorderable list
- [ ] **Appendices stay subordinate**: none adds a row to §5's table or a `Function to CREATE`, none names a framework or library input didn't supply, none claims a responsibility beyond its firm default, and each is short enough to read as an appendix
- [ ] **Deleting all three appendices would leave §§1–5 complete and correct** — nothing in them depends on any appendix
- [ ] **No provenance**: no mention of the assignment, homework, capstone, task numbering, agent names, this template, or any source filename (only `sample-transactions.json`, and only as the default input fixture)
- [ ] No business rule, threshold, or regulation invented without support — unsupported specifics carry `[NEEDS CLARIFICATION: ...]`, and no gap was resolved by asking an interactive question

## Step 5 — Output

**Always regenerate from scratch.** If a file exists at the target path, do not read it, reuse it, or treat it as correct — it may predate this invocation's input or this version of the template. Overwrite it with the draft from Steps 1–4.

Write to the path given (default `specification.md` in the current working directory). Produce **only that one file** — no other files, no other side effects. Then report: the path written, and every `[NEEDS CLARIFICATION: ...]` marker left in the document, so the caller knows what to resolve before the spec reaches the code-generation agent.
