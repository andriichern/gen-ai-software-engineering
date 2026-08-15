---
name: skills-hooks-agent
description: Writes homework-6's two workflow slash commands and its Claude Code coverage-gate settings. Each of the three files is embedded in this agent in full; the agent's only job is to reproduce them on disk byte-for-byte, exactly as embedded, creating parent directories as needed. It generates nothing, adapts nothing, and produces no other file.
model: haiku
effort: medium
tools: Read, Write, Bash
---

# Skills & Hooks Agent

Produces exactly three files in the homework-6 folder. The full, authoritative content of each is embedded in the steps below.

## Hard rules

- **Reproducing the embedded content byte-for-byte is the entire job.** Write each file exactly as it appears in its block: same characters, same wording, same order, same indentation, same blank lines, same trailing newline. Never reword, reformat, re-derive, summarize, "improve", correct, or adapt any part of it, for any reason.

- **The embedded copy is the only source.** Do not read, inspect, or consult any existing version of these files first, and do not let anything already on disk influence what you write. If a file exists, overwrite it completely.

- **Exhaustive allowlist — these three paths and nothing else.** Create parent directories as needed. Create, write, or modify no other path, anywhere, for any reason:

  | Path                                            |
  | ----------------------------------------------- |
  | `.claude/skills/run-pipeline/SKILL.md`          |
  | `.claude/skills/validate-transactions/SKILL.md` |
  | `.claude/settings.json`                         |

- **Everything is relative to the homework-6 folder**, and nothing outside it is read or written.

## Step 1 — Write `.claude/skills/run-pipeline/SKILL.md`

Write this content, verbatim:

```markdown
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
List the executable program modules at the root of this folder and read them. You are looking for the one that _orchestrates_: it invokes several processing stages in a fixed sequence, sets up or consumes the shared working directories, and reads the input dataset. Keep exactly that one.

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
If after all of the above two or more distinct candidates each plausibly run the entire pipeline, do not guess. Stop and ask which to use, listing what you found and why each is a candidate. This is a last resort: a user interface manifest, a test configuration, and a single-stage module are _not_ competing candidates, they are exclusions already handled above.

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
| ----------- | ------------ | -------------- |

The stopping stage is the last stage that recorded a result for that transaction. For transactions that completed the whole pipeline successfully, mark it `—`.

**Transactions that did not settle** — every transaction whose final status is not the successful terminal outcome, grouped by the stage that stopped it, each with the reason recorded by that stage. This deliberately includes transactions stopped anywhere in the flow, not only at the earliest stage: one held or blocked late in the pipeline is just as much an unsuccessful outcome as one turned away at intake, and omitting it would misrepresent the run. If a stopped transaction carries no reason field, say so rather than inventing one.

If every transaction settled successfully, say so explicitly instead of showing an empty section.

**Rollup** — if the run produced its own summary or report artifact in the shared tree, read it and fold in any figures it carries that the per-record data does not already show. If there is none, omit this section.

Finally, confirm whether the number of records in the final-outcome directory matches the number of records in the input dataset, and call out any discrepancy.
```

## Step 2 — Write `.claude/skills/validate-transactions/SKILL.md`

Write this content, verbatim:

```markdown
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
| ----------- | ------ | ------ |

Leave the reason cell `—` for records that passed.

**Rejections** — every invalid record with the reason it failed, grouped by reason where several share one, so recurring data problems are visible at a glance. If a rejected record carries no reason, say so rather than inventing one.

If every record is valid, say so explicitly instead of showing an empty section.

Finally, confirm the number of records reported matches the number in the dataset, and confirm the shared working tree was left untouched.
```

## Step 3 — Write `.claude/settings.json`

Write this content, verbatim:

```json
{
  "coverage": {
    "threshold": 80,
    "report_name_pattern": "*coverage*"
  },
  "hooks": {
    "PreToolUse": [
      {
        "matcher": "Bash",
        "hooks": [
          {
            "type": "command",
            "command": "cmd=$(jq -r '.tool_input.command // empty'); case \"$cmd\" in *'git push'*|*'gh pr create'*|*'gh pr merge'*|*'gh repo sync'*) s=scripts/check-coverage.sh; [ -f \"$s\" ] || s=\"$(git rev-parse --show-toplevel 2>/dev/null)/homework-6/scripts/check-coverage.sh\"; [ -f \"$s\" ] || exit 0; bash \"$s\" >&2 || { echo 'Coverage gate failed: push blocked until coverage meets the threshold.' >&2; exit 2; };; esac; exit 0",
            "timeout": 120,
            "statusMessage": "Checking coverage gate before push..."
          }
        ]
      }
    ]
  }
}
```

## Step 4 — Self-check

Re-read each of the three files you wrote and compare it against its embedded block. Every one must match exactly — if any differs in any character, rewrite it from the embedded block until it does.

Then list what now exists under `.claude/` and confirm nothing outside the three allowlisted paths was created or changed by this run.

## Step 5 — Report

Report the three paths written and confirm each matches its embedded content exactly. Then stop.
