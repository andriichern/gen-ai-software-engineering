---
name: write-spec
description: Generate homework-6/specification.md for the transaction processing pipeline by following the shared template at .claude/templates/specification-template.md. Runs with no arguments and produces the same document the specification-agent does — it reads only the template, never explores the repo, and never assumes anything the template doesn't already settle. Optional arguments supply transaction data, a stack, or constraints; anything still genuinely open is left as a [NEEDS CLARIFICATION: ...] marker rather than a question. Produces only specification.md, scoped to the pipeline alone.
argument-hint: "(optional) transaction data, stack/language, compliance or risk constraints"
---

Given $ARGUMENTS (may be empty):

1. Read `.claude/templates/specification-template.md` in full, fresh — never a cached or remembered copy. It governs everything below; where this file and the template appear to differ, the template wins.

2. **The template plus `$ARGUMENTS` are your only input.** Do not explore the repository, do not search it for context, and do not read any other file to inform the document — no `TASKS.md`, no source files, no config, no dependency manifest, no previous `specification.md`. The pipeline's purpose, stages, and rules are already fully settled by the template's firm defaults, so an empty `$ARGUMENTS` is a normal invocation that still produces a complete specification.

   The single exception: if `$ARGUMENTS` supplies no transaction data, you may read `sample-transactions.json` — **solely to confirm the record shape**, never as a source of business context, requirements, volume, or specific values. If it is absent or unreadable, fall back to the template's default schema; that is not an error and not a gap. How the finished spec may refer to that file is the template's rule, not yours.

3. **Never assume, never infer from what happens to exist.** The stack is whatever `$ARGUMENTS` states and nothing else — the presence of a manifest, a virtualenv, or source files from an earlier run says nothing, and none of them may be consulted. With no stack given, leave it `[NEEDS CLARIFICATION: ...]` per the template's Gap-Handling Protocol; never ask, never block.

4. Apply the template's Scope section to anything `$ARGUMENTS` supplies: carry through only what describes the orchestrator and the 5 pipeline stages, silently dropping the rest (dropped material is not a gap), and cite no provenance in the finished document.

5. Follow the template's Steps 1–5 and its Self-Check checklist exactly. Regenerate from scratch; never read or reuse an existing `specification.md`.

6. Write the result to `specification.md` in the homework-6 root. **Produce only that one file** — no other files, no other side effects, no follow-up work.

7. Report: the path written, and the full list of `[NEEDS CLARIFICATION: ...]` markers left in the document. Then stop.
