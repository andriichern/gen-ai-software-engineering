# Stack Discovery Rules

Shared procedure for determining, at run time, what this project is actually built with. Read this file in full at the start of every invocation, fresh — never a cached or remembered copy.

**This file contains rules, not answers.** It names no language, framework, runtime, package, or entrypoint filename as an expected result. Every conclusion must come from a file read during the current run. If a rule below mentions a manifest name, that is a pattern to look for on disk — not a claim about what this project uses.

---

## Scope: three components, no others

Discovery runs per component, because different components may use entirely different stacks. Discover exactly these three, each independently:

| Component | How to locate it |
|---|---|
| **Pipeline** | The directory holding the pipeline stage modules, plus the orchestrator/runner at the project root that drives them |
| **MCP server** | The directory holding the custom MCP server implementation, plus the MCP configuration file at the project root |
| **UI / front-end** | The directory holding the user-facing application |

Locate each by inspecting the directory tree, not by assuming a name. If a component's directory cannot be found, record it as absent — do not substitute a guess, and do not report a component that does not exist.

Discover nothing else. Other directories (tests, scripts, docs, build output, dependency caches, version-control internals) are **out of scope** for stack discovery. Where test tooling is relevant to a caller, derive it from the pipeline component's stack and its test configuration files rather than treating it as a fourth component.

---

## Step 0: start from the project's own documents

Before scanning anything, read the project's own descriptive documents, if they exist:

- The project specification.
- The research/decision notes.

These usually state the languages and frameworks outright, which is faster and better-informed than inferring them from a directory listing. Read them first, every run.

From them, form a **hypothesis** for each in-scope component: its expected language, runtime and frameworks. A hypothesis is not a finding. It is a claim to be confirmed cheaply in the steps below, because these documents describe what was *planned*, and plans drift — a library named in a spec may have been dropped, and notes often record options that were considered and rejected. Nothing may be reported on their authority alone.

Two limits on what these documents may settle:

- **They may inform language, runtime and frameworks only.** Entrypoints, run commands and install commands are never taken from prose — always from a manifest, a config file, or a committed script, as written on disk.
- **Where a component is not covered**, or the documents are absent, it simply has no hypothesis. Discover it from scratch using the full procedure.

---

## Per-component procedure

Repeat all five steps for each component in scope.

**Where a hypothesis exists from Step 0, steps 1–3 become confirmation rather than search:** locate the component's manifest and check that it agrees. If it does, the hypothesis is confirmed — record it and move on, without further scanning. If it does not, or no manifest is found, fall back to the full procedure as written below.

### 1. Find the manifest

Look inside the component directory, then at the project root, for a dependency/build manifest. Common patterns to search for:

- `requirements.txt`, `pyproject.toml`, `setup.py`, `setup.cfg`, `Pipfile`
- `package.json`
- `go.mod`
- `pom.xml`, `build.gradle`, `build.gradle.kts`
- `Cargo.toml`
- `Gemfile`, `composer.json`, `*.csproj`, `mix.exs`

This list is a starting set, not a closed one. If a manifest of another kind is present, use it.

### 2. Identify the language and runtime

Corroborate the manifest against the source itself:

- Count source-file extensions inside the component directory.
- Read one representative source file and check its import/include syntax.
- Look for a declared runtime or language version — in the manifest, in a version-pinning file, or in a config file belonging to the component.

Report a runtime version only if a file states it, or if an inspection-only command returned it. Never infer a version from a dependency's own version number.

### 3. Identify frameworks and key libraries

Read the manifest's declared dependencies. Report only what is declared there or demonstrably imported in the component's source. Distinguish direct dependencies from transitive ones; a lockfile lists both, so prefer the manifest for what the project actually chose. Do not report a library merely because it is installed somewhere on the machine.

### 4. Find the entrypoint

Determine how the component is started:

- A script/task defined in the manifest itself (this is the most reliable source, and takes precedence over inference).
- A file containing the component's main/startup construct.
- A configuration file that declares a command to launch the component.

Record the exact entrypoint path or script name as written.

### 5. Derive the run command

Build the command from what step 4 found, using the invocation convention of the discovered runtime. Prefer, in order:

1. A command the manifest or a config file states verbatim.
2. A command a committed helper script in the project performs.
3. The runtime's standard way of invoking the entrypoint found in step 4.

Note the working directory the command must be run from. If a component requires dependency installation first, derive that command from the manifest the same way.

---

## Conflict clause: disk wins

Where a document from Step 0 disagrees with the files on disk — the spec names one language and the sources are plainly another, or it lists a library the manifest does not declare — **the disk wins, without exception**. Report the stack the code actually shows.

This is not an ambiguity and must not stop the run. Resolve it in favour of the code, then **note the discrepancy in your final report to the user**, stating what the document claimed and what was found. That note goes to the user only; it never appears in any generated output.

---

## Ambiguity clause

If, for any component, the signals conflict (a manifest for one language beside sources predominantly of another), or no manifest and no recognizable sources are found, **stop and ask** using `AskUserQuestion`. State what was found — manifests located, extension counts, imports parsed — and ask which stack applies.

Never guess. Never resolve ambiguity by picking the more common option, the first one found, or the one that appears elsewhere in the project. A component's stack is independent of the other components' stacks.

---

## Reporting contract

For each of the three components, produce:

- Component name and directory (or `absent`)
- Language and runtime, with version if a file stated one
- Frameworks and key libraries, as declared
- Entrypoint, as written on disk
- Run command, plus its working directory and any prerequisite install command

Plus, once for the run: any discrepancy found under the conflict clause, and any component whose stack came from a confirmed hypothesis versus a full scan.

Every field must be traceable to a file read during this run. Where something could not be determined, say so explicitly rather than filling it in.
