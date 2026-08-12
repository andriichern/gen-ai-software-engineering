---
name: run-complete-flow
description: Run homework-6's five main agents end to end, in one fixed order — specification, then pipeline code generation, then skills and hooks, then tests, then documentation. A plain wrapper and nothing more: it confirms the destructive run once, dispatches each agent exactly once in sequence, and reports what each one reported. It does no work of its own, makes no decisions for any agent, and never reorders, skips, repeats, or parallelizes the chain. Optional arguments (stack, UI stack, transaction data, constraints) are passed through to the agents that consume them.
argument-hint: "(optional) pipeline stack, UI stack (or 'no UI'), transaction data, compliance or risk constraints"
---

Given $ARGUMENTS (may be empty):

## What this command is

A wrapper around five agents, run in one fixed order:

1. `specification-agent`
2. `pipeline-codegen-agent`
3. `skills-hooks-agent`
4. `tests-codegen-agent`
5. `documentation-agent`

**You orchestrate. You do not participate.** Each agent owns its own work, its own rules, and its own output. Your entire job is to confirm once, dispatch five times in order, and relay what came back.

Absolute boundaries, all of them non-negotiable:

- **Do no work yourself.** Write no file, generate no code, no spec, no test, and no documentation. Run no part of the pipeline. If an agent produces something incomplete or wrong, **report it — never fix it, never finish it, never work around it.**
- **Never substitute your judgement for an agent's.** Do not verify, re-check, second-guess, or re-interpret what an agent reports. Do not re-read its output files to form your own opinion of whether it succeeded. Its report is the result.
- **Never deviate from the order.** Never reorder, never skip a step, never run two in parallel, never dispatch any agent a second time, and never dispatch an agent that is not one of the four above.
- **Never assume.** Do not infer a stack, resolve a marker, answer a question on an agent's behalf, or fill any gap yourself. The agents ask the user directly; that is theirs, not yours.
- **Never continue past the chain.** When step 4 reports, write the summary and stop. No follow-up work, no improvements, no offers to fix what you saw.

## Step 0 — Confirm the destructive run, once

This chain **destroys and regenerates existing work**. Before dispatching anything, state plainly what will be lost:

- **Deleted outright**: `pipeline/`, `lib/`, `orchestrator.*`, `research-notes.md`, `shared/`, and — only when a UI stack is resolved — `ui/`, including any installed dependency tree inside it.
- **Overwritten**: `specification.md`, the test suite and its configuration, `README.md`, `HOWTORUN.md`, and — from the skills-and-hooks step — `.claude/skills/run-pipeline/SKILL.md`, `.claude/skills/validate-transactions/SKILL.md`, and `.claude/settings.json`, each replaced with that agent's embedded version. Any local edit to those three is lost.
- **Left alone**: `scripts/` (agents may add to it, but nothing there is deleted), and everything else in the folder.

Then ask the user once, with `AskUserQuestion`, whether to proceed.

**Anything other than an explicit go-ahead means stop.** Dispatch nothing, delete nothing, and say the run was not started. Do not ask again, do not offer a partial run, and do not reinterpret hesitation as consent.

## Step 1 — `specification-agent`

Dispatch it, passing `$ARGUMENTS` through **verbatim**. Add nothing of your own — no context, no repo details, no explanation of why it is being run, no suggested stack.

Wait for it. Capture: the path written, and every `[NEEDS CLARIFICATION: ...]` marker it reports.

**If it fails to produce a specification, stop the chain.** Report what failed.

Markers are not a failure — the specification agent never asks, by design, and leaves gaps as markers for the next agent to resolve with the user. Continue.

## Step 2 — `pipeline-codegen-agent`

Dispatch it with no instructions of your own, except this: **where `$ARGUMENTS` explicitly stated a pipeline stack or a UI stack (including an explicit "no UI"), pass those statements through verbatim** so the agent is not asked to re-resolve what the user already settled. Pass nothing else — no marker interpretation, no suggestion, no default.

If `$ARGUMENTS` stated no stack, pass nothing about stacks. The agent will ask the user directly; that is correct and expected. **Never answer for it, and never pre-empt the question.**

Wait for it. Capture: the pipeline stack used and how it resolved, the UI decision (built or not, in which stack), files created, the self-test result, and any question it asked with its answer.

**If it fails, or its self-test fails, stop the chain.** Do not run tests against a pipeline that did not build or did not pass its own self-test. Report what failed and that the remaining steps were skipped.

## Step 3 — `skills-hooks-agent`

Dispatch it with no arguments and nothing of your own. It reproduces its own embedded files exactly; it needs no context from the previous steps and must not be given any.

Wait for it. Capture: the files it wrote, and anything it reported as failed or skipped.

**If it fails, report the failure and continue to Step 4 anyway.** Its output is not something the remaining steps depend on, so a failure here never halts the chain. Do not retry it, and do not write or repair any of its files yourself.

## Step 4 — `tests-codegen-agent`

Dispatch it. Pass through any coverage threshold `$ARGUMENTS` supplied; otherwise pass nothing and let its own default stand.

Wait for it. Capture: what was generated, whether the suite passed, and the coverage figure reported.

Then decide, and only between these two:

- **It failed to produce a test suite**, could not determine the stack, or errored out leaving the work incomplete → **stop**. Do not dispatch documentation. Report what failed.
- **It produced and ran a suite** → **continue**, whether or not every test passed and whether or not coverage met the threshold. A shortfall or a failing test is a result worth documenting, not a reason to halt.

## Step 5 — `documentation-agent`

Dispatch it with no arguments and no findings from the previous steps. It discovers everything itself — including the stack — and must not be made dependent on this chain having run.

Wait for it. Capture: the files it wrote, the components and stacks it discovered, any discrepancy it flagged between the project's documents and its code, and anything it left undetermined.

## Step 6 — Report

Summarize the run, step by step. For each of the five: whether it ran, what it produced, what it asked and how the user answered, and — for any step not reached — that it was skipped and why.

Then add, drawn only from what the agents themselves reported:

- The pipeline stack, and how it was resolved.
- The UI decision: built or not, in which stack, and whether `ui/` was deleted.
- The coverage figure and whether it met its threshold.
- Any discrepancy the documentation agent flagged.
- Anything any agent reported as undetermined, unresolved, or declined.

Report what they reported. Do not add conclusions of your own, do not editorialize on quality, and do not recommend next steps. Then stop.
