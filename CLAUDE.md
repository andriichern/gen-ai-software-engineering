# CLAUDE.md

This file provides guidance to Claude Code (claude.ai/code) when working with code in this repository.

---

## Repository Overview

This is a course homework repository for **GenAI and Agentic AI for Software Engineering**. It contains six homework assignments (`homework-1` through `homework-6`), each a standalone project with its own stack, architecture, and submission requirements.

**Key principle**: Each homework deliberately uses different languages/frameworks to build breadth. Before suggesting patterns or tools, check the specific homework's existing files (especially `TASKS.md`, `package.json` / `pyproject.toml`, or existing source code) to understand what stack is already in place—don't assume a fixed technology choice.

---

## Repository Structure

```
├── README.md                           # Main submission guide with grading criteria
├── CLAUDE.local.md                     # Personal student notes (not shared)
├── homework-1/                         # Banking Transactions API (Node/Next.js/TypeScript)
│   ├── TASKS.md                        # Assignment requirements
│   ├── README.md                       # Project documentation (includes author/date/AI tools used)
│   ├── HOWTORUN.md                     # Setup, build, run, test commands
│   ├── src/                            # Source code
│   ├── __tests__/                      # Tests
│   ├── docs/screenshots/               # Evidence of AI usage and working app
│   └── [build config: package.json, tsconfig.json, vitest.config.ts, etc.]
├── homework-2/                         # Customer Support Ticket System (FastAPI + Svelte)
│   ├── TASKS.md
│   ├── README.md
│   ├── HOWTORUN.md
│   ├── [similar structure per stack]
├── homework-3/                         # Personal Finance Tracker (spec-driven)
├── homework-4/                         # 4-Agent Pipeline (agents + skills + sample app)
│   ├── TASKS.md                        # Requires: agents/, skills/, src/ (with bugs), tests/, docs/
│   ├── agents/                         # 4 required agents
│   ├── skills/                         # Custom skills for research quality & FIRST testing
│   ├── context/bugs/                   # Agent outputs (research, plans, fixes, reports)
│   └── [sample app source with seeded bugs/security issues]
├── homework-5/                         # MCP Server Configuration
├── homework-6/                         # Capstone Project
└── .claude/                            # Claude Code project settings
    └── skills/                         # Custom skills created during course
```

---

## Workflow for Each Homework

### 1. **Understand the Assignment**
- Read `homework-N/TASKS.md` for full requirements
- Check for any pre-existing files (e.g., starter code, sample app)
- Note the deliverables, especially README/HOWTORUN/screenshots requirements

### 2. **Implement**
- Choose your stack (or verify the existing one from TASKS.md / existing files)
- Follow the root README's submission conventions:
  - Create a feature branch: `git checkout -b homework-N-submission`
  - Implement according to TASKS.md
  - Create `README.md` with project overview, author, date, AI tools used
  - Create `HOWTORUN.md` with setup and run instructions
  - Add screenshots to `docs/screenshots/` showing AI usage and working app
  - Commit your work

### 3. **Submit**
- Push the branch: `git push origin homework-N-submission`
- Create a detailed PR on **your personal fork** (base: `main`, compare: `homework-N-submission`)
- PR body must include: implementation summary, AI tools/prompts used, challenges, 3-5 screenshots
- Assign the instructor (Alexey-Popov) for review

---

## Common Development Tasks

### Homework 1–3 Pattern (Application Development)

Each homework has different commands based on its stack. **Always check the homework's HOWTORUN.md first.** General patterns:

```bash
# Install dependencies
npm install          # Node projects
pip install -r requirements.txt  # Python projects

# Run development server
npm run dev          # Node/Svelte/Next.js
python -m uvicorn app.main:app --reload  # FastAPI

# Run tests
npm test             # Node projects (often Vitest)
pytest               # Python projects

# Linting/formatting
npm run lint         # Node projects
pylint src/          # Python projects
```

### Homework 4 (4-Agent Pipeline) – New Pattern

Homework 4 requires building a **single-command agentic pipeline**:

```bash
# Run entire pipeline (must execute all 4 agents in order)
npm run pipeline     # or: ./run-pipeline.sh
```

The pipeline orchestrates:
1. **Bug Research Verifier** (`agents/research-verifier.agent.md`) → `research/verified-research.md`
2. **Bug Fixer** (`agents/bug-fixer.agent.md`) → applies fixes, runs tests, outputs `fix-summary.md`
3. **Security Verifier** (`agents/security-verifier.agent.md`) → `security-report.md`
4. **Unit Test Generator** (`agents/unit-test-generator.agent.md`) → `test-report.md`

Each agent has its own `.agent.md` file; read and execute them in order. See [TASKS.md](homework-4/TASKS.md) for the full agent specifications.

---

## Key Architectural Decisions

### Multi-Stack Repository
- **No fixed tech stack across homeworks.** Each assignment chooses its own based on requirements.
- Check existing files before proposing a new stack for a homework.
- Don't assume Node/TypeScript everywhere—Homework 2 uses FastAPI + Svelte, Homework 3 uses a different approach.

### AI Usage Documentation
- Each homework's README **must document** which AI tools were used and how (prompts, workflow, verification steps).
- PR description should include concrete examples of AI-assisted work with screenshots.
- Grading weights AI Usage Documentation at 25%.

### Submission Quality
- Bare or one-line PRs are rejected. Every PR must include:
  - Clear summary of implementation
  - AI tools used + prompts
  - Challenges and solutions
  - 3–5 screenshots in PR body and `docs/screenshots/`
- README and HOWTORUN are **required** (graded at 15% and 10% respectively).

### Homework 4 Specifics
- **Two custom skills must be created:**
  1. `skills/research-quality-measurement.md` — define research quality levels; used by research-verifier agent
  2. `skills/unit-tests-FIRST.md` — define FIRST principles (Fast, Independent, Repeatable, Self-validating, Timely); used by test-generator agent
- Each of the 4 agents must have an **explicit model choice** (frontmatter in `.agent.md`), justified in the README
- Sample application (in `src/`) must have ≥2 intentional bugs and ≥1 security issue; pipeline must fix them all
- All agent outputs must be committed to repo: `research/`, `context/bugs/`, `fix-summary.md`, `security-report.md`, `test-report.md`

---

## Debugging & Development Tips

### Per-Homework Testing
- Check HOWTORUN.md for test commands—they vary by stack and framework
- Run tests after each change in Homework 4 (agents expect `npm test` or equivalent to work)
- Property-based tests (Homework 1 uses fast-check) catch edge cases; run them locally

### Agent & Skill Creation (Homework 4)
- Skills are reusable YAML/Markdown files in `.claude/skills/` or `homework-4/skills/`
- Each agent reads input files (research, plan, fixes) and outputs structured markdown
- Agents must **use the skills they need** (e.g., research-verifier uses research-quality-measurement skill when writing verified-research.md)
- Store agent outputs in `context/bugs/XXX/` so they're version-controlled and visible in PR

### Submission Validation
- Before opening a PR, run the `/submission-check` skill to verify README, HOWTORUN, and screenshots are in place
- Homework 4: verify pipeline runs end-to-end with one command and all 4 agent outputs are generated

---

## Using Claude Code in This Repository

### Useful Slash Commands
- `/init` — Create or update CLAUDE.md (this file)
- `/submission-check` — Verify homework-N meets submission requirements before PR
- `/feature-dev` — For major feature work (uses architecture discovery + planning)
- `/run` — Start the homework's dev server or run the app
- `/code-review` — Review code before opening a PR
- `/ultrareview` — Cloud-based multi-agent code review (for complex features)

### Skills Available
- `homework-scaffold` — Set up folder structure for a new homework (reads TASKS.md, creates README/HOWTORUN stubs)
- `superpowers:brainstorming` — Before creative work (designing agents, skills, architecture)
- `superpowers:systematic-debugging` — For tricky bugs
- `superpowers:test-driven-development` — For Homework 4 test generation
- `superpowers:requesting-code-review` — Before merging to main

### Custom Skills for This Repo
Stored in `.claude/skills/`. Check what exists before creating new ones to avoid duplication.

---

## Student Notes

From `CLAUDE.local.md`:
- You're deliberately varying stacks per homework to build breadth
- You value understanding the **why** behind architectural choices, not just the end result
- **Submission conventions** are strict: detailed PRs, screenshots, AI usage docs are graded
- Each homework is a standalone project; don't cross-pollinate code between them unless explicitly allowed

---

## Links

- **Main README** (submission guide, grading criteria): [README.md](README.md)
- **Recommended agents/skills** for course work: [recommended-agents-skills-pipelines.md](recommended-agents-skills-pipelines.md)
- **Course**: GenAI and Agentic AI for Software Engineering
