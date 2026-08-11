---
name: run-pipeline
description: Run this folder's transaction-processing pipeline end to end and report the outcome. Checks the input dataset is present, clears the shared working tree, discovers the pipeline's entrypoint and runtime by reading the folder's own files, runs it with output streamed, then summarizes every processed transaction and every one that did not settle, with the stage and reason that stopped it. Entirely stack-agnostic — it names no language, runtime, tool, or entrypoint filename, and derives all of that fresh on every invocation.
argument-hint: "(optional) path to an alternate input transaction dataset"
---

Given $ARGUMENTS (may be empty), run the transaction-processing pipeline that lives in this folder and report what happened.

## 0. Scope and prohibitions

Operate **only** within this homework folder — the directory containing this `.claude/` tree. Never reach into sibling folders or the repository root for context, entrypoints, or configuration.

**Never read `TASKS.md`.** It is an assignment brief, not a description of what was built. It is not a source of stack information, entrypoint names, run commands, or anything else. Nothing in this run may depend on it.

During this run you must **not**:

- modify, reformat, or "fix" any source, configuration, or data file
- install, upgrade, or vendor any dependency
- run the test suite, a build, a linter, or the front-end
- retry a failed run with altered inputs, patched code, or a different command in the hope of a better result

You read, you clear the working tree, you run one command, you report. Nothing else.

## 1. Preflight — input dataset

Check that `sample-transactions.json` exists in this folder.

If it is absent, **stop immediately**. Report that the input dataset is missing and that the pipeline was not run. Do not substitute another file, do not synthesize records, do not continue to any later step.

If `$ARGUMENTS` names an alternate input dataset, verify that path exists too, and pass it to the entrypoint at step 4 in whatever way that entrypoint accepts an input path — determined by reading the entrypoint, not assumed.

## 2. Discover the pipeline entrypoint

**Hardcode nothing.** This folder's language, runtime, toolchain, and entrypoint are unknown to you at the start of every invocation, and you must derive them from the folder's real contents each time. Do not carry over an answer you remember from a previous run, and do not let familiarity with a common stack stand in for reading the files.

Work through these in order and stop at the first that yields a single confident answer.

**(a) A root-level program module that drives the whole pipeline.**
List the executable program modules at the root of this folder and read them. You are looking for the one that *orchestrates*: it invokes several processing stages in a fixed sequence, sets up or consumes the shared working directories, and reads the input dataset. Keep exactly that one.

Explicitly **reject** modules that:
- implement a single processing stage rather than sequencing several (these usually live in a subdirectory alongside their siblings, and each handles one concern)
- configure, discover, or run tests
- build, bundle, serve, or preview a user interface
- define shared helpers or utilities without driving anything

**(b) A manifest that declares named runnable commands.**
If no root-level module resolves it, look for manifests in this folder that declare named runnable commands, and read what each command actually does. Accept only a command that runs the **whole pipeline**. Reject commands that build, bundle, serve, preview, watch, format, lint, or run tests — a manifest whose commands are all of that kind belongs to a subordinate component (such as a user interface) and is not the pipeline's entrypoint, even if it is the only manifest present.

**(c) Corroborating documents.**
`research-notes.md` and `specification.md` in this folder may confirm which runtime or toolchain the code is written in — for example through the libraries, tooling, or platform they discuss. Use them to **confirm or disambiguate** a candidate found above; they are supporting evidence, not a substitute for reading the code. If either document leaves the stack unstated or marks it as an open question, that is simply an absent signal — not a blocker, and not something to ask about.

**(d) Derive the invocation from the entrypoint itself.**
Once the entrypoint file is identified, determine how to invoke it from that file's own form — its interpreter directive if it has one, its extension, and the syntax of its contents. Use the plainest, most direct invocation for that form. Do not wrap it in a task runner, container, or environment manager that the folder does not itself indicate.

**(e) A missing dependency manifest is normal.**
Many projects are run directly from source with no declared dependency manifest at all. Its absence is not an error, not a reason to install anything, and not a reason to stop.

**(f) Genuine ambiguity — ask.**
If after all of the above two or more distinct candidates each plausibly run the entire pipeline, do not guess. Stop and ask which to use, listing what you found and why each is a candidate. This is a last resort: a user interface manifest, a test configuration, and a single-stage module are *not* competing candidates, they are exclusions already handled above.

State the entrypoint and invocation you settled on, and the evidence for it, before running anything.

## 3. Clear the shared working tree

Locate the shared working directory this pipeline passes data through — the folder whose subdirectories represent the stages of the flow (intake, in-progress work, hand-off between stages, and final outcomes).

Empty it before every run, unconditionally:

- **Discover** its subdirectories and stale artifacts by listing what is actually there. Do not work from a remembered or assumed set of names.
- Delete the **files** inside each working subdirectory, and any leftover run artifacts (status, summary, or report files) sitting at the shared directory's root.
- **Preserve** the shared directory itself and its subdirectory structure — remove contents, not the directories.

If the shared directory does not exist yet, that is fine; the entrypoint is expected to create it. Note it and continue.

Report what was cleared.

## 4. Run the pipeline

Invoke the entrypoint exactly as derived in step 2, from this folder.

**Stream its output to the transcript in full.** This output is the primary artifact of the run and is captured as evidence — do not suppress, silence, redirect, or truncate it.

If the run exits non-zero or fails partway:

- report the actual failure and the real output, verbatim
- state plainly that the pipeline did **not** complete
- do **not** patch code, install anything, or re-run with different arguments to force a pass
- still perform step 5 over whatever partial results exist, clearly labelled as partial

## 5. Summarize the results

Read the final-outcome directory in the shared working tree — the one holding the terminal result of each transaction. Read each record and let the data define its own vocabulary: use the status values, stage result fields, and reason fields that are actually present. Do not assume a fixed set of status names, and do not map them onto names you expected.

Present, in this order:

**Run header** — the entrypoint used, the input dataset used, and the total number of records that reached the final-outcome directory.

**Counts by final status** — every distinct final status present, with its count.

**Per-transaction table** — one row per transaction:

| Transaction | Final status | Stopping stage |
|---|---|---|

The stopping stage is the last stage that recorded a result for that transaction. For transactions that completed the whole pipeline successfully, mark it `—`.

**Transactions that did not settle** — every transaction whose final status is not the successful terminal outcome, grouped by the stage that stopped it, each with the reason recorded by that stage. This deliberately includes transactions stopped anywhere in the flow, not only at the earliest stage: one held or blocked late in the pipeline is just as much an unsuccessful outcome as one turned away at intake, and omitting it would misrepresent the run. If a stopped transaction carries no reason field, say so rather than inventing one.

If every transaction settled successfully, say so explicitly instead of showing an empty section.

**Rollup** — if the run produced its own summary or report artifact in the shared tree, read it and fold in any figures it carries that the per-record data does not already show. If there is none, omit this section.

Finally, confirm whether the number of records in the final-outcome directory matches the number of records in the input dataset, and call out any discrepancy.
