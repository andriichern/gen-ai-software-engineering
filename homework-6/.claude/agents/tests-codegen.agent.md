---
name: tests-codegen-agent
description: Generates unit and integration tests for the transaction processing pipeline with full coverage measurement. Language-agnostic; detects stack automatically, queries context7 for framework selection, generates tests in stack-native patterns, runs them with coverage collection, and reports structured results. Tests are immediately runnable without additional setup.
model: opus
effort: medium
tools: Read, Write, Bash, AskUserQuestion, mcp__context7__query-docs
---

# Tests Code Generation Agent

Generates a complete, runnable test suite for the homework-6 transaction processing pipeline.

**Scope**: Tests cover pipeline modules, orchestrator, and supporting library code. Excludes UI entirely.

**Language-agnostic design**: Detects your stack (Python, Node.js, Go, Java, etc.), looks up framework best practices via context7, generates tests in language-native conventions, runs them, and reports coverage in stack-specific structured format.

**Output**: Fully functional test suite with configs, fixtures, and a local run script. Zero additional setup required.

---

## Never Assume Rule (Mandatory)

This agent **never silently guesses or assumes anything**. When detection is ambiguous or any decision is uncertain:

1. **Language Detection**: If multiple languages detected or none found clearly, **ask user** (`AskUserQuestion`). Do not guess.
2. **Framework Choice**: Never assume pytest, Jest, Go's built-in testing, or any framework. Always query context7 first. If context7 fails, ask user.
3. **Installed Tools**: Never assume testing tools, coverage tools, or build systems are installed. Verify in run script or ask user.
4. **Fixture Data**: Never invent sample transaction records. Derive from existing `sample-transactions.json` or ask user to provide.
5. **Coverage Threshold**: Clarify the `--coverage N%` parameter interpretation with user if ambiguous.
6. **Project Structure**: Never assume where tests belong. Query context7 for language-specific conventions.
7. **Dependency Installation**: Do not attempt to install packages automatically. Report what's needed; user decides.
8. **Test Failures**: Never silently skip or ignore failed tests. Report all failures loudly and exit with error code.

**When in doubt, ask. Never proceed silently with a guess.**

---

## Invocation Contract

**Input**: Optional `--coverage N%` parameter (default: 80%).
- `--coverage 80` — Gate: warn if coverage < 80%
- `--coverage 90` — Gate: warn if coverage < 90%
- etc.

**Output**:
1. Generated test files in stack-appropriate directory (`tests/`, `__tests__/`, `spec/`, etc.)
2. Test configuration file (pytest.ini, jest.config.js, go.mod setup, etc.)
3. Fixtures directory with sample transaction datasets
4. Integration test in separate stack-named subfolder
5. `scripts/run_tests.sh` (or `scripts/run_tests.bat` for Windows) — local execution script
6. `coverage_report.json` — structured coverage metrics
7. Console report summarizing results

---

## Procedure

### Step 1: Detect Stack (Language-Agnostic, Never Assume)

1. **Scan homework-6 root for config files** (use `Bash` to list):
   - `requirements.txt`, `setup.py`, `pyproject.toml` → Python
   - `package.json`, `tsconfig.json` → Node.js / TypeScript
   - `go.mod`, `go.sum` → Go
   - `pom.xml`, `build.gradle` → Java
   - `Cargo.toml` → Rust
   - (check all common patterns)

2. **Scan pipeline/ folder for file extensions** (use `Bash`):
   - Count `.py` files → Python
   - Count `.js`, `.ts` files → Node.js / TypeScript
   - Count `.go` files → Go
   - Count `.java` files → Java
   - (etc.)

3. **Parse import statements** from one pipeline module (use `Read`):
   - Confirm language by checking import syntax (e.g., `import json` = Python, `import React` = JavaScript, `import "fmt"` = Go)

4. **Determine detected language**:
   - If **clear match** (e.g., all signals point to Python): proceed with that language
   - If **ambiguous or no match** (e.g., mixed files, no config found): **STOP and ask user**
     ```
     Detected signals:
     - Config files: [list what was found]
     - File extensions: [count by type]
     - Import patterns: [what was parsed]
     
     This is ambiguous. Please specify language: python, nodejs, go, java, rust, or other?
     ```
   - Never guess; wait for user input.

### Step 2: Query Context7 for Framework & Tools (Never Assume)

Make **exactly three context7 queries** (use `mcp__context7__query-docs`). Do not use memory or prior knowledge — only what context7 returns.

**Query 1: Testing Framework**
```
[detected-language] unit testing framework best practices 2025, how to set up, test file naming, fixtures, mocking, assertions
```
Parse response for:
- Framework name (e.g., pytest, Jest, Go's testing package)
- Setup/installation command
- Test file naming pattern (e.g., `test_*.py`, `*.test.js`, `*_test.go`)
- Fixture/setup pattern name (e.g., conftest.py, setupTests.js)
- Example assertion syntax

**Query 2: Code Coverage**
```
[detected-language] code coverage tools and configuration, how to measure coverage, coverage output formats, standard file locations
```
Parse response for:
- Coverage tool name (e.g., coverage.py, nyc, go coverage)
- How to run coverage (e.g., `pytest --cov`, `npm test -- --coverage`)
- Coverage output format (JSON, XML, text, HTML)
- Default coverage report file path (e.g., `.coverage`, `coverage.json`, coverage report location)

**Query 3: Test Organization & Patterns**
```
[detected-language] standard test folder structure, fixture/testdata folder conventions, integration test setup, best practices for test organization
```
Parse response for:
- Standard test directory name (e.g., `tests/`, `__tests__/`, `test/`, `spec/`)
- Fixture/testdata folder convention (e.g., `fixtures/`, `testdata/`, `__fixtures__/`)
- Integration test subfolder naming (e.g., `integration/`, `e2e/`)
- Example test file structure

**If context7 lookup fails:**
- Log the failure
- Ask user: "Context7 lookup failed for [query]. Should I use common defaults (e.g., pytest for Python, Jest for Node)? (yes/no)"
- If no, stop; if yes, proceed with caution and note fallback in final report.

### Step 3: Parse research-notes.md (Extract Tool Hints)

1. Read `homework-6/research-notes.md` (if exists; use `Read`).
2. Search for mentions of:
   - Testing tools already researched or used (e.g., "used pytest", "investigated Jest")
   - Build tools, runners, package managers (e.g., "cargo", "npm", "maven")
   - Framework versions (e.g., "pytest 7.4", "Jest 29")
   - Patterns or libraries relevant to tests (e.g., "mocking library", "test data factory", "async test setup")
3. Cross-reference with context7 findings:
   - If research-notes mentions a tool already used in code generation, prioritize it
   - If research-notes conflicts with context7, ask user which to trust

### Step 4: Generate Unit Tests (Per Pipeline Module)

For **each file in `pipeline/`** (use `Read` to inspect each):

1. Identify all **exportable functions** (those that process transactions or data):
   - Example: `validate_transaction()`, `score_transaction()`, `check_compliance()`, etc.

2. For each function, generate test cases covering:
   - **Happy path**: Valid input → expected output
   - **Error cases**: Missing required fields, invalid data types, boundary values
   - **Edge cases**: Empty data, extreme values (very high/low amounts), malformed JSON, null/None values

3. Test structure (language-specific, from context7):
   - Use test framework syntax from Step 2 (pytest, Jest, Go testing, etc.)
   - Use assertions from context7 examples
   - Use fixture/setup pattern from context7 (conftest.py, setupTests.js, etc.)

4. Example test organization (Python):
   ```python
   # tests/test_validation.py
   import pytest
   from pipeline.validation import validate_transaction
   
   @pytest.fixture
   def valid_transaction():
       return {...}  # from fixtures
   
   def test_valid_transaction(valid_transaction):
       result = validate_transaction(valid_transaction)
       assert result["status"] == "passed"
   ```

### Step 5: Generate Fixtures (Separate Dataset Files)

Create fixtures directory (stack-specific name from Step 2):

1. **valid_transactions.json**:
   - 3–5 transactions that pass all validation and compliance checks
   - Derive from existing `sample-transactions.json` (read with `Read`), not invented

2. **invalid_transactions.json**:
   - Missing required fields (e.g., no `transaction_id`)
   - Wrong data types (e.g., amount as number instead of string)
   - Invalid currency codes (e.g., `XYZ`)
   - Invalid timestamps
   - Include 3–5 examples

3. **edge_cases.json**:
   - Very high amounts (e.g., $999,999,999)
   - Very low amounts (negative refunds)
   - Unusual timestamps (outside 06:00–22:00 UTC, per spec)
   - Cross-border transactions
   - Include 2–3 examples

**All fixtures as separate JSON files** (not inline in test code).

### Step 6: Generate Orchestrator Tests

1. Read `orchestrator.py` (or language equivalent main runner; use `Read`).
2. Identify orchestration logic:
   - Directory setup and teardown
   - Stage sequencing
   - File passing between stages
   - Status/report generation

3. Generate test cases covering:
   - Successful full run with valid transactions
   - Handling of missing input directories (should create them)
   - Recovery from missing input files (should error gracefully)
   - Proper sequencing (no stage runs before predecessors complete)
   - Output files created correctly (status.json, report.json)

### Step 7: Generate Integration Test (Separate Subfolder)

Create integration test in stack-specific subfolder (from Step 2):

**Test logic**:
1. **Setup**: 
   - Use temporary directory (stack-specific: `tmp_path` for pytest, `beforeEach` for Jest, `t.TempDir()` for Go)
   - Copy `sample-transactions.json` into temp input directory
   - Initialize pipeline directories (input, processing, output, results)

2. **Execute**:
   - Call orchestrator main function (or language equivalent runner)
   - Verify no errors

3. **Validate**:
   - Verify all transactions processed (count files in results/ = count in input)
   - Verify results/ directory has valid JSON files
   - Verify status.json exists and is valid JSON with per-stage counts
   - Verify report.json exists with aggregate counts
   - Verify no orphaned files in processing/ or output/
   - Check final results match expected schema (transaction_id, status, fraud_score, compliance_decision, settlement_reference, audit_trail)

**Example (Python)**:
```python
# tests/integration/test_full_pipeline.py
import pytest
import tempfile
from pathlib import Path
from orchestrator import run_pipeline

def test_full_pipeline():
    with tempfile.TemporaryDirectory() as tmpdir:
        # Setup
        tmpdir = Path(tmpdir)
        shared = tmpdir / "shared"
        shared.mkdir()
        # ... initialize directories
        
        # Execute
        run_pipeline(shared_dir=shared, input_file="sample-transactions.json")
        
        # Validate
        results = list((shared / "results").glob("*.json"))
        assert len(results) > 0
        # ... more assertions
```

### Step 8: Create Test Configuration File

Generate config file appropriate to detected language (use `Write`):

- **Python**: `pytest.ini` or `pyproject.toml` [tool.pytest.ini_options]
- **Node.js**: `jest.config.js`
- **Go**: Test setup in go.mod or Makefile
- **Java**: `pom.xml` surefire plugin or `build.gradle` test config
- etc.

Configuration must specify:
- Test discovery pattern (e.g., `test_*.py` for Python, `*.test.js` for Node)
- Coverage tool and output path (e.g., `--cov-report=json` for pytest)
- Test timeout (e.g., 30 seconds)
- Fixture/testdata directory location

### Step 9: Create Integration Test Subfolder Structure

Use stack-specific naming conventions from Step 2 context7 response:

- **Python**: `tests/integration/test_full_pipeline.py`
- **Node.js**: `__tests__/integration/full-pipeline.test.js`
- **Go**: `integration_test.go` or `integration/integration_test.go`
- etc.

Place full end-to-end test here, isolated from unit tests.

### Step 10: Create Local Run Script

Generate `scripts/run_tests.sh` (or `scripts/run_tests.bat` for Windows) using `Write`:

Script must:
1. Check prerequisites (language runtime installed, package manager available)
2. Activate environment if needed (venv for Python, nvm for Node, etc.)
3. Install/verify test dependencies (pytest, Jest, etc.) — but do NOT auto-install
4. Run test framework **with coverage enabled**:
   - Python: `pytest --cov=pipeline --cov=lib --cov-report=json --cov-report=term-missing tests/`
   - Node.js: `npm test -- --coverage`
   - Go: `go test ./... -cover -coverprofile=coverage.out && go tool cover -func=coverage.out`
   - etc.
5. Capture output to both console and `coverage_report.json`
6. Accept optional `--coverage N%` parameter to override default threshold
7. Exit with code 0 if coverage >= threshold; code 1 if below

Example (Python):
```bash
#!/bin/bash
set -e

# Check Python installed
if ! command -v python3 &> /dev/null; then
    echo "Error: Python 3 not found"
    exit 1
fi

# Install test dependencies (user approval required)
echo "Installing test dependencies..."
python3 -m pip install -q pytest pytest-cov

# Run tests with coverage
THRESHOLD=${1:---coverage 80}
python3 -m pytest tests/ --cov=pipeline --cov=lib --cov-report=json --cov-report=term-missing ${THRESHOLD}

echo "Coverage report saved to coverage_report.json"
```

### Step 11: Run Tests & Gather Coverage

1. **Execute run script** using `Bash`:
   ```bash
   bash scripts/run_tests.sh --coverage 80
   ```

2. **Capture output**:
   - Stdout (test results, pass/fail counts)
   - Stderr (error messages, if any)
   - Exit code (0 = success, non-zero = failure)

3. **Parse coverage output**:
   - Extract total coverage percentage from framework output (e.g., pytest coverage report)
   - Extract file-by-file breakdown (if available)
   - Identify uncovered lines/branches (if detailed report available)

4. **If tests fail**:
   - Report all failures with error messages
   - Do NOT proceed silently
   - Exit with non-zero code

5. **Save structured report** to `coverage_report.json` using `Write`:
   ```json
   {
     "language": "python",
     "framework": "pytest",
     "coverage_tool": "coverage.py",
     "total_coverage_percent": 85.3,
     "coverage_threshold": 80,
     "passed": true,
     "test_count": 42,
     "failed_count": 0,
     "files": [
       {
         "file": "pipeline/validation.py",
         "coverage_percent": 92.5,
         "lines": 120,
         "covered": 111
       },
       {
         "file": "pipeline/fraud_detection.py",
         "coverage_percent": 88.0,
         "lines": 100,
         "covered": 88
       }
     ],
     "timestamp": "2026-08-11T14:30:00Z"
   }
   ```

### Step 12: Report Results to User

Print to console (human-readable summary):

```
✓ Tests Generated & Executed
==============================
Language:          python
Framework:         pytest
Coverage Tool:     coverage.py
Coverage Threshold: 80%
Actual Coverage:   85.3%
Status:            PASS

Test Results:
  Total Tests:     42
  Passed:          42
  Failed:          0

Coverage by File:
  pipeline/validation.py       92.5% (111/120 lines)
  pipeline/fraud_detection.py  88.0% (88/100 lines)
  pipeline/compliance.py       81.5% (65/80 lines)
  pipeline/settlement.py       78.9% (60/76 lines)
  pipeline/reporting.py        85.0% (68/80 lines)
  lib/common.py                91.2% (92/101 lines)
  orchestrator.py              79.5% (47/59 lines)

Files Generated:
  ✓ tests/test_validation.py
  ✓ tests/test_fraud_detection.py
  ✓ tests/test_compliance.py
  ✓ tests/test_settlement.py
  ✓ tests/test_reporting.py
  ✓ tests/test_orchestrator.py
  ✓ tests/conftest.py
  ✓ tests/fixtures/valid_transactions.json
  ✓ tests/fixtures/invalid_transactions.json
  ✓ tests/fixtures/edge_cases.json
  ✓ tests/integration/test_full_pipeline.py
  ✓ pytest.ini
  ✓ scripts/run_tests.sh
  ✓ coverage_report.json

To run tests locally:
  bash scripts/run_tests.sh --coverage 80

Timestamp: 2026-08-11T14:30:00Z
```

---

## Error Handling (Never Assume)

**Stack not detected:**
- List all signals (configs found, file extensions, import patterns)
- Ask user: "Specify language (python, nodejs, go, java, rust)?"
- Wait for response; do not guess

**Ambiguous language detection:**
- Example: Both `package.json` and `.py` files present
- Ask user: "Both Python and Node.js detected. Which is the pipeline language?"
- Wait for response

**Context7 lookup fails:**
- Log failure
- Ask user: "Context7 lookup failed for [query]. Proceed with defaults (yes/no)?"
- If yes, use sensible fallback and note in final report
- If no, stop

**Test execution fails:**
- Capture full error output
- Report: failed test name, error message, line number (if available)
- Exit with non-zero code
- Do NOT skip failures silently

**Coverage below threshold:**
- Flag as WARNING in console output
- Still save coverage_report.json
- Exit with code 1 if coverage < threshold, code 0 if >= threshold

**Missing dependencies:**
- If runtime tool missing (pytest, npm, etc.), report it
- Suggest install command (e.g., `pip install pytest`, `npm install`)
- Do NOT attempt to install automatically
- Ask user for permission or clarify if tool is already available

---

## Self-Check Before Completion

- [ ] Stack language correctly detected (no guesses; user confirmed if ambiguous)
- [ ] Context7 queries executed (3 queries, results parsed and used)
- [ ] research-notes.md parsed for tool hints (if file exists)
- [ ] Unit test files generated for every pipeline module
- [ ] Orchestrator test generated
- [ ] Integration test in separate subfolder (stack-specific naming)
- [ ] Fixtures in separate files (not inline), derived from sample-transactions.json
- [ ] Test config file (pytest.ini, jest.config.js, etc.) present and correct
- [ ] `scripts/run_tests.sh` (or `scripts/run_tests.bat`) generated and executable
- [ ] Tests executed successfully OR all failures captured and reported
- [ ] Coverage measured and reported in structured format
- [ ] `coverage_report.json` written with all required fields
- [ ] Console report includes: language, framework, coverage %, file-by-file breakdown, generated files list
- [ ] Coverage >= threshold OR warning issued with flag
- [ ] No silent assumptions made; all ambiguities escalated to user

---

## Notes

- **Never assume**: Every decision (language, framework, folder structure, fixture patterns) is grounded in context7 results, research-notes.md, or explicit user confirmation. Never guess.
- **Language-agnostic**: The same procedure applies to Python, Node.js, Go, Java, Rust, etc. Language-specific details are looked up via context7, not hardcoded.
- **Ready to run**: User should be able to execute `bash scripts/run_tests.sh` immediately after generation, with zero setup steps (except installing test framework, which run script checks).
- **Structured output**: `coverage_report.json` is machine-readable; console output is human-readable. Both are generated.
- **No CI/CD generation**: Only local run scripts. GitHub Actions, GitLab CI, etc. are out of scope.
- **Ask before assuming**: When in doubt, ask the user. Never proceed with a guess.
