# How to Run: Homework 4 - 4-Agent Pipeline

This document provides complete instructions for setting up, running, testing, and executing the 4-agent bug detection and fixing pipeline.

---

## Table of Contents

1. [Project Setup](#project-setup)
2. [Running Tests](#running-tests)
3. [Running the Application](#running-the-application)
4. [Running the Pipeline](#running-the-pipeline)
5. [Pipeline Outputs](#pipeline-outputs)
6. [Troubleshooting](#troubleshooting)

---

## Project Setup

### Prerequisites

- **Node.js**: v18+ (check: `node --version`)
- **npm**: v9+ (check: `npm --version`)
- **TypeScript**: Built into dev dependencies
- **NestJS CLI**: Installed via npm

### Installation Steps

1. **Install Dependencies**

   ```bash
   npm install
   ```

   This installs all required packages:
   - NestJS framework
   - TypeScript and type definitions
   - Testing framework (Jest)
   - Linting and formatting tools (ESLint, Prettier)
   - Class validation libraries

2. **Build the Project**

   ```bash
   npm run build
   ```

   This compiles TypeScript to JavaScript and outputs to the `dist/` directory.

3. **Verify Installation**

   ```bash
   npm test
   ```

   Should show test results (expect some failures from seeded bugs).

---

## Running Tests

### Run All Tests

```bash
npm test
```

Executes the full test suite using Jest. Output shows:
- Number of test suites
- Number of passing/failing tests
- Test execution time

**Before pipeline run**: Tests may fail due to intentional bugs in the application.  
**After pipeline run**: Tests should pass after bugs are fixed.

### Run Tests in Watch Mode

```bash
npm run test:watch
```

Re-runs tests automatically whenever source files change. Useful during development.

### Run Tests with Coverage Report

```bash
npm run test:cov
```

Generates a coverage report showing what percentage of code is tested. Output includes:
- Per-file coverage percentages
- Line coverage, branch coverage, function coverage
- HTML report in `coverage/` directory (open `coverage/lcov-report/index.html` in browser)

### Run Tests in Debug Mode

```bash
npm run test:debug
```

Starts tests with Node debugger enabled. Useful for troubleshooting specific test failures.

---

## Running the Application

### Development Mode

```bash
npm run start:dev
```

Starts the NestJS application in development (watch) mode:
- Application runs on `http://localhost:3000`
- Automatically restarts when source files change
- Shows detailed logs of requests and operations

### Production Mode

First build:
```bash
npm run build
npm run start:prod
```

Runs the compiled application from the `dist/` directory (faster, no watch mode).

### Debug Mode

```bash
npm run start:debug
```

Starts application with debugger enabled. Connect a debugger tool to port 9229.

### Format Code

```bash
npm run format
```

Auto-formats all TypeScript source code using Prettier for consistent style.

### Lint Code

```bash
npm run lint
```

Checks code for style issues and potential bugs using ESLint. Can auto-fix many issues.

---

## Running the Pipeline

The 4-agent pipeline automates bug detection, fixing, security verification, and unit test generation.

### Pipeline Overview

The pipeline executes in this order:

```
Phase 1: Research Verifier
    ↓ (check: bugs found?)
Phase 2: Bug Fixer
    ↓ (check: changes made?)
Phase 3-4: Security Verifier + Unit Test Generator (parallel)
```

**Conditional execution**:
- If no bugs found by Research Verifier → skip remaining phases
- If Bug Fixer makes no changes → skip verification phases

### Run Pipeline (Dry-Run Mode)

**Dry-run** shows what would be executed without actually running the agents. Use this to verify pipeline logic.

**Via npm script** (recommended):
```bash
npm run pipeline
```

**Via bash script**:
```bash
bash scripts/run-pipeline.sh --dry-run
```

**Output**:
- Displays each phase's steps and commands
- Shows conditional checks and branching logic
- Does not modify source code
- Does not generate agent outputs
- Safe for testing and documentation

### Run Pipeline (Execute Mode)

**Execute mode** actually runs all agents and generates real outputs. Only run after verifying the pipeline in dry-run mode.

```bash
npm run pipeline:execute
```

Or directly:
```bash
bash scripts/run-pipeline.sh --execute
```

**Output**:
- Executes each agent in order
- Generates output files (fix-summary.md, security-report.md, test-report.md)
- Applies actual bug fixes to source code
- Generates and runs unit tests
- Creates detailed reports

### Pipeline Execution Examples

**Example 1: Quick verification (dry-run)**
```bash
npm run pipeline
```

Expected output:
```
[STEP] INITIALIZING PIPELINE
✓ Agent found: research-verifier.agent.md
✓ Agent found: bug-fixer.agent.md
[STEP] PHASE 1: BUG RESEARCH VERIFIER
[DRY-RUN] Would execute: claude run agent .claude/agents/research-verifier.agent.md --model claude-sonnet-5
[STEP] CHECKING RESEARCH RESULTS
✓ Bugs found! Proceeding to Bug Fixer phase
...
```

**Example 2: Full execution**
```bash
npm run pipeline:execute
```

Will take several minutes as agents analyze and fix bugs.

---

## Pipeline Outputs

After running the pipeline in execute mode, check the generated files:

### Phase 1: Research Verifier Outputs

**Location**: `research/` and `context/bugs/XXX/`

- **`research/codebase-research.md`** — Initial findings from source code analysis
- **`research/verified-research.md`** — Verified bugs with severity levels
- **`context/bugs/XXX/implementation-plan.md`** — Detailed fix plan for Bug Fixer

### Phase 2: Bug Fixer Outputs

**Location**: `context/bugs/XXX/`

- **`context/bugs/XXX/fix-summary.md`** — Summary of applied fixes, test results before/after

**Modified source code**: Changes in `src/` directory (actual bug fixes)

### Phase 3: Security Verifier Outputs

**Location**: `context/bugs/XXX/`

- **`context/bugs/XXX/security-report.md`** — Security vulnerabilities found, severity levels, remediation steps

### Phase 4: Unit Test Generator Outputs

**Location**: `context/bugs/XXX/` + `__tests__/` or `tests/`

- **`context/bugs/XXX/test-report.md`** — Test generation summary, before/after metrics, coverage
- **Test files**: New/updated test files in `__tests__/` directory

### Log File

- **`pipeline-execution.log`** — Detailed execution log of all pipeline steps

---

## Understanding Pipeline Outputs

### Implementation Plan Example

The implementation plan lists all bugs found:

```markdown
# Implementation Plan

## Summary
Total Bugs: 3
Critical: 1 | High: 2 | Medium: 0 | Low: 0

## Bugs by Priority

### Fix 1: Missing validation in orderService [CRITICAL]
- File: src/services/order.service.ts (lines 45-60)
- Issue: Order quantities not validated before processing
- Impact: Invalid orders accepted, causing data inconsistency
- Fix: Add type checking and range validation

### Fix 2: Weak equality operator [HIGH]
- File: src/utils/comparison.ts (line 22)
- Issue: Uses == instead of ===
- Fix: Replace with strict equality
```

### Fix Summary Example

```markdown
# Fix Summary

## Overview
Total Fixes Attempted: 3
Fixes Successful: 3
Fixes Failed: 0
Overall Status: All Passed

## Baseline Test Results
Before any fixes:
- Total Tests: 15
- Passed: 10
- Failed: 5

## Fixes Applied

### Fix 1: Missing validation in orderService
Status: ✅ PASSED (Attempt 1)
Files Modified: src/services/order.service.ts
Changes: Added type validation and range checks
Test Result: 2 previously failing tests now pass

## Overall Status
All Fixes Attempted: Yes
Fixes Successful: 3
Fixes Failed: 0
Final Test Status: PASS (15/15 tests passing)
```

### Security Report Example

```markdown
# Security Vulnerability Report

## Summary
Scan Date: 2024-08-02
Scan Type: Incremental - Changed Files Only
Total Findings: 2 | Critical: 1 | High: 1 | Medium: 0 | Low: 0

## Findings

### Finding 1: Hardcoded API Key
Severity: CRITICAL
File: src/config/secrets.ts (line 8)
Issue: API key hardcoded in source
Remediation: Move to environment variable
```

### Test Report Example

```markdown
# Test Report: Unit Tests for Changed Code

## Summary
Baseline → Final:
- Tests: 15 → 22 (+7)
- Passing: 10 → 22 (+12)
- Failing: 5 → 0
- Coverage: 75% → 92% (+17%)

## Generated Tests
Tests Added: 7
Test Files Modified: src/services/order.service.test.ts, src/utils/comparison.test.ts

## Coverage Analysis
Changed Code Coverage: 92%
Target Met: 95%+ ✅

## FIRST Principles Applied
✅ Fast: Tests mock external dependencies
✅ Independent: Each test self-contained
✅ Repeatable: Deterministic test data
✅ Self-validating: Clear assertions
✅ Timely: Tests for changed code
```

---

## Troubleshooting

### Issue: Pipeline script not found

**Error**: `bash: scripts/run-pipeline.sh: No such file or directory`

**Solution**:
1. Verify you're in the project root: `pwd` should show `homework-4`
2. Check file exists: `ls -l scripts/run-pipeline.sh`
3. Make executable: `chmod +x scripts/run-pipeline.sh`

### Issue: npm script not working

**Error**: `npm ERR! missing script: pipeline`

**Solution**:
1. Verify package.json has pipeline scripts: `grep "pipeline" package.json`
2. Reinstall dependencies: `npm install`
3. Clear npm cache: `npm cache clean --force`

### Issue: Tests fail before pipeline run

**Expected behavior**: Some tests fail due to intentional bugs in the app.

**Verify**:
```bash
npm test
# You should see some failures related to the seeded bugs
```

**After pipeline run**: Tests should pass.

### Issue: Dry-run shows no output

**Solution**:
1. Ensure you're using `--dry-run` flag: `npm run pipeline`
2. Check terminal output (may scroll quickly—pipe to less): `npm run pipeline | less`
3. Check log file: `cat pipeline-execution.log`

### Issue: Build fails

**Error**: `npm run build` fails with TypeScript errors

**Solution**:
1. Check TypeScript version: `npx tsc --version`
2. Ensure tsconfig.json is valid: `cat tsconfig.json`
3. Clear build: `rm -rf dist/ && npm run build`

### Issue: Specific test fails

**Solution**:
1. Run with watch mode: `npm run test:watch`
2. Run specific file: `npm test -- filename.spec.ts`
3. Run with coverage: `npm run test:cov` (see coverage report)
4. Debug mode: `npm run test:debug` (attach debugger)

### Issue: Port 3000 already in use

**When running**: `npm run start:dev`

**Solution**:
1. Kill existing process: `lsof -ti:3000 | xargs kill -9`
2. Or use different port: `PORT=3001 npm run start:dev`
3. Or use process manager: `npx pm2 start npm -- run start:dev`

---

## Next Steps

1. **Understand the bugs**: Review `context/bugs/XXX/bug-context.md` to see intentional issues
2. **Run dry-run**: `npm run pipeline` to see pipeline logic
3. **Execute pipeline**: `npm run pipeline:execute` to apply fixes
4. **Review results**: Check output files in `context/bugs/XXX/`
5. **Verify fixes**: `npm test` should show all tests passing
6. **Check coverage**: `npm run test:cov` to see test coverage metrics

---

## Commands Quick Reference

```bash
# Setup
npm install                 # Install dependencies
npm run build              # Build project

# Testing
npm test                   # Run all tests
npm run test:watch        # Watch mode
npm run test:cov          # With coverage report
npm run test:debug        # Debug mode

# Running app
npm run start:dev         # Development mode
npm run start:prod        # Production mode
npm start:debug           # Debug mode
npm run format            # Format code
npm run lint              # Lint code

# Pipeline
npm run pipeline          # Dry-run (safe)
npm run pipeline:execute  # Execute (makes changes)

# Direct scripts
bash scripts/run-pipeline.sh --dry-run      # Dry-run
bash scripts/run-pipeline.sh --execute      # Execute
```

---

## Support

- **Pipeline not working?** Check `pipeline-execution.log` for detailed error messages
- **Need to understand agents?** Read `.claude/agents/[agent-name].agent.md`
- **Skills reference?** Check `.claude/skills/` for research-quality-measurement and unit-tests-FIRST
- **Task description?** See `TASKS.md` for full assignment requirements
