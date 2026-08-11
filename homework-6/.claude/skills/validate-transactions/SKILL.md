---
name: validate-transactions
description: Validate every transaction in this folder's dataset without processing them and without running the full pipeline. Discovers the validation stage and its no-write mode by reading the folder's own files, runs only that stage in a mode that writes nothing, then reports total, valid and invalid counts with a table of results and the reason each rejected transaction failed. Entirely stack-agnostic — it names no language, runtime, tool, flag, or filename, and derives all of that fresh on every invocation.
argument-hint: "(optional) path to an alternate input transaction dataset"
---

Given $ARGUMENTS (may be empty), validate this folder's transaction dataset without processing it, and report the outcome.

## 0. Scope and prohibitions

Operate **only** within this homework folder — the directory containing this `.claude/` tree. Never reach into sibling folders or the repository root for context, entrypoints, or configuration.

**Never read `TASKS.md`.** It is an assignment brief, not a description of what was built. It is not a source of stack information, stage names, run commands, flags, or anything else. Nothing in this run may depend on it.

During this run you must **not**:

- modify, reformat, or "fix" any source, configuration, or data file
- install, upgrade, or vendor any dependency
- run the full pipeline, any stage other than validation, the test suite, a build, a linter, or the front-end
- write to, clear, or otherwise disturb the shared working tree — this run leaves it exactly as it found it
- retry a failed run with altered inputs, patched code, or a different command in the hope of a better result

This command inspects and reports. It changes nothing.

## 1. Preflight — resolve the dataset

Determine which dataset to validate:

- If `$ARGUMENTS` names a dataset path, that is the dataset. Verify it exists.
- Otherwise the dataset is `sample-transactions.json` in this folder. Verify it exists.

**If the resolved dataset does not exist, stop immediately.** Report which path was checked and that no validation was performed. Do not substitute another file, do not fall back to the other path, do not synthesize records, and do not continue to discovery or to any later step. Terminate before reading anything else.

## 2. Discover the validation stage and its no-write mode

**Hardcode nothing.** This folder's language, runtime, toolchain, stage layout, and command-line conventions are unknown to you at the start of every invocation, and you must derive them from the folder's real contents each time. Do not carry over an answer you remember from a previous run, and do not let familiarity with a common stack stand in for reading the files.

**(a) Find the validation stage.**
Locate the modules that implement the pipeline's individual processing stages — typically siblings in one directory, each handling a single concern. Read them and identify the one that performs **validation**: it checks records for required fields, well-formed types, a sensible amount, and a recognized currency, and yields a pass/fail outcome carrying a human-readable reason.

Explicitly **reject**:
- the module that sequences all the stages rather than implementing one
- sibling stages that score risk, screen against policy, settle, or aggregate and report
- shared helpers and utilities that drive nothing
- anything that configures, discovers, or runs tests
- anything that builds, bundles, serves, or previews a user interface

**(b) Find its no-write mode.**
Read the validation stage's own standalone entrypoint and the arguments it accepts, including their help text. You are looking for a mode that validates records and **reports without writing anything** — no directory read, created, or modified, no record altered. Identify both how that mode is requested and how the dataset to validate is supplied to it.

**(c) If it has no such mode, stop.**
Report that the validation stage exposes no way to run without side effects, and name what its entrypoint does accept. Do **not** run it in a mode that writes, do **not** redirect its directories at a scratch location as a workaround, and do **not** edit it to add one. Terminate and let the user decide.

**(d) Corroborating documents.**
`research-notes.md` and `specification.md` in this folder may confirm which runtime or toolchain the code is written in. Use them to **confirm or disambiguate** a candidate found above; they are supporting evidence, not a substitute for reading the code. If either leaves the stack unstated or marks it as an open question, that is simply an absent signal — not a blocker, and not something to ask about.

**(e) Derive the invocation from the stage itself.**
Determine how to invoke it from that file's own form — its interpreter directive if it has one, its extension, and the syntax of its contents. Use the plainest, most direct invocation for that form, run from this folder so the stage resolves its own imports the way it expects. Do not wrap it in a task runner, container, or environment manager that the folder does not itself indicate. A missing dependency manifest is normal and is not a reason to install anything.

State the stage, the no-write mode, and the full invocation you settled on, and the evidence for each, before running anything.

## 3. Run validation in no-write mode

Record what the shared working tree contains before you start, if it exists.

Invoke the validation stage exactly as derived, in its no-write mode, pointing it at the dataset resolved in step 1. Capture its output.

If it exits non-zero: report the actual failure and the real output, verbatim, state plainly that validation did not complete, and stop. Do not patch anything and do not re-run with different arguments.

Afterwards, confirm the shared working tree is **unchanged** from before the run. If anything changed, say so prominently — the mode was not actually side-effect-free, and that is a defect worth reporting.

## 4. Report the results

Parse whatever structured report the no-write mode emitted. Let the data define its own vocabulary: use the status values and reason fields actually present, and do not map them onto names you expected.

Present, in this order:

**Header** — the dataset validated, the stage and mode used.

**Counts** — total records, valid, invalid.

**Results table** — one row per transaction:

| Transaction | Status | Reason |
|---|---|---|

Leave the reason cell `—` for records that passed.

**Rejections** — every invalid record with the reason it failed, grouped by reason where several share one, so recurring data problems are visible at a glance. If a rejected record carries no reason, say so rather than inventing one.

If every record is valid, say so explicitly instead of showing an empty section.

Finally, confirm the number of records reported matches the number in the dataset, and confirm the shared working tree was left untouched.
