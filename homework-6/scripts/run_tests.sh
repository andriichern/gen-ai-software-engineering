#!/bin/bash
# Run the transaction-processing pipeline test suite with coverage measurement.
#
#   bash scripts/run_tests.sh                 # gate at the default 80% threshold
#   bash scripts/run_tests.sh --coverage 90   # gate at 90%
#   bash scripts/run_tests.sh 90              # same, shorthand
#
# Exits 0 only if every test passes AND coverage >= threshold.
# Dependencies are never installed automatically: missing ones are reported
# with the exact command to install them, and the script stops.

set -uo pipefail

PROJECT_ROOT="$(cd "$(dirname "${BASH_SOURCE[0]}")/.." && pwd)"
cd "$PROJECT_ROOT"

# ---------------------------------------------------------------------------
# Arguments
# ---------------------------------------------------------------------------
COVERAGE_THRESHOLD=80
while [ $# -gt 0 ]; do
    case "$1" in
        --coverage)
            COVERAGE_THRESHOLD="${2:-80}"
            shift 2
            ;;
        --coverage=*)
            COVERAGE_THRESHOLD="${1#*=}"
            shift
            ;;
        [0-9]*)
            COVERAGE_THRESHOLD="$1"
            shift
            ;;
        -h|--help)
            echo "Usage: $0 [--coverage N]"
            exit 0
            ;;
        *)
            echo "Unknown argument: $1" >&2
            echo "Usage: $0 [--coverage N]" >&2
            exit 2
            ;;
    esac
done
COVERAGE_THRESHOLD="${COVERAGE_THRESHOLD%\%}"

RED='\033[0;31m'; GREEN='\033[0;32m'; YELLOW='\033[1;33m'; NC='\033[0m'

# ---------------------------------------------------------------------------
# Step 1: Prerequisites (verified, never auto-installed)
# ---------------------------------------------------------------------------
echo "Checking prerequisites..."

if ! command -v python3 >/dev/null 2>&1; then
    echo -e "${RED}Error: python3 not found.${NC}" >&2
    echo "Install Python 3.8+ and re-run." >&2
    exit 1
fi
echo "Found: $(python3 --version)"

MISSING=""
check_module() {
    # $1 = importable module name, $2 = pip package name
    if ! python3 -c "import $1" >/dev/null 2>&1; then
        MISSING="$MISSING $2"
    fi
}

check_module pytest pytest
check_module pytest_cov pytest-cov
check_module coverage coverage
check_module pycountry pycountry     # ISO 4217 validation in pipeline/validation.py
check_module requests requests       # live exchange-rate client in lib/exchange_rates.py
check_module fastapi fastapi         # stage services (services/) and the gateway (gateway/)
check_module httpx httpx             # gateway's outbound calls; FastAPI TestClient transport

if [ -n "$MISSING" ]; then
    echo -e "${RED}Error: missing required package(s):${NC}$MISSING" >&2
    echo "" >&2
    echo "Install them with:" >&2
    echo "    python3 -m pip install$MISSING" >&2
    echo "" >&2
    echo "(Nothing is installed automatically by this script.)" >&2
    exit 1
fi
echo "All required packages present."

# ---------------------------------------------------------------------------
# Step 2: Run the suite with coverage
# ---------------------------------------------------------------------------
echo ""
echo -e "${YELLOW}Running tests with coverage (threshold: ${COVERAGE_THRESHOLD}%)...${NC}"
echo ""

RAW_COVERAGE_JSON=".coverage_raw.json"

# --cov with no value picks up the [run] source list from .coveragerc
# (pipeline, lib, orchestrator, services, gateway). The UI is deliberately
# out of scope.
python3 -m pytest tests/ \
    --cov \
    --cov-report="json:${RAW_COVERAGE_JSON}" \
    --cov-report=term-missing \
    --cov-report=html:htmlcov
TEST_EXIT_CODE=$?

# ---------------------------------------------------------------------------
# Step 3: Transform coverage output into the structured report
# ---------------------------------------------------------------------------
echo ""
echo -e "${YELLOW}Building coverage_report.json ...${NC}"

if [ ! -f "$RAW_COVERAGE_JSON" ]; then
    echo -e "${RED}Error: coverage produced no output (${RAW_COVERAGE_JSON} missing).${NC}" >&2
    exit 1
fi

COVERAGE_EXIT_CODE=$(python3 - "$RAW_COVERAGE_JSON" "$COVERAGE_THRESHOLD" "$TEST_EXIT_CODE" <<'PYEOF'
import json
import subprocess
import sys
from datetime import datetime, timezone

raw_path, threshold, test_exit = sys.argv[1], float(sys.argv[2]), int(sys.argv[3])

with open(raw_path) as fh:
    raw = json.load(fh)

totals = raw.get("totals", {})
total_pct = round(float(totals.get("percent_covered", 0.0)), 2)

files = []
for name, data in sorted(raw.get("files", {}).items()):
    summary = data.get("summary", {})
    files.append({
        "file": name,
        "coverage_percent": round(float(summary.get("percent_covered", 0.0)), 2),
        "lines": summary.get("num_statements", 0),
        "covered": summary.get("covered_lines", 0),
        "missing_lines": summary.get("missing_lines", 0),
        "branches": summary.get("num_branches", 0),
        "partial_branches": summary.get("num_partial_branches", 0),
        "uncovered_line_numbers": data.get("missing_lines", []),
    })

try:
    version = subprocess.run(
        [sys.executable, "-m", "pytest", "--version"],
        capture_output=True, text=True, check=False,
    ).stdout.strip().splitlines()[0]
except Exception:
    version = "pytest"

report = {
    "language": "python",
    "language_version": sys.version.split()[0],
    "framework": version,
    "coverage_tool": "coverage.py " + raw.get("meta", {}).get("version", ""),
    "branch_coverage": raw.get("meta", {}).get("branch_coverage", False),
    "scope": ["pipeline", "lib", "orchestrator", "services", "gateway"],
    "excluded": ["ui"],
    "total_coverage_percent": total_pct,
    # Also exposed under coverage.py's native key path so that
    # scripts/check-coverage.sh (which probes .totals.percent_covered) can
    # read this report directly.
    "totals": {
        "percent_covered": total_pct,
        "percent_covered_display": str(int(total_pct)),
        "covered_lines": totals.get("covered_lines", 0),
        "num_statements": totals.get("num_statements", 0),
        "missing_lines": totals.get("missing_lines", 0),
    },
    "coverage_threshold": threshold,
    "covered_lines": totals.get("covered_lines", 0),
    "total_statements": totals.get("num_statements", 0),
    "missing_lines": totals.get("missing_lines", 0),
    "tests_passed": test_exit == 0,
    "coverage_passed": total_pct >= threshold,
    "passed": test_exit == 0 and total_pct >= threshold,
    "files": files,
    "timestamp": datetime.now(timezone.utc).isoformat(),
}

with open("coverage_report.json", "w") as fh:
    json.dump(report, fh, indent=2)

print(0 if total_pct >= threshold else 1)
PYEOF
)

COVERAGE_PCT=$(python3 -c "import json;print(json.load(open('coverage_report.json'))['total_coverage_percent'])")
rm -f "$RAW_COVERAGE_JSON"

# ---------------------------------------------------------------------------
# Step 4: Summary
# ---------------------------------------------------------------------------
echo ""
echo "============================================"
echo "Test Summary"
echo "============================================"

if [ "$TEST_EXIT_CODE" -eq 0 ]; then
    echo -e "Tests:    ${GREEN}PASSED${NC}"
else
    echo -e "Tests:    ${RED}FAILED${NC} (see the failure output above)"
fi

if [ "$COVERAGE_EXIT_CODE" -eq 0 ]; then
    echo -e "Coverage: ${GREEN}${COVERAGE_PCT}% >= ${COVERAGE_THRESHOLD}% threshold${NC}"
else
    echo -e "Coverage: ${RED}WARNING - ${COVERAGE_PCT}% < ${COVERAGE_THRESHOLD}% threshold${NC}"
fi

echo ""
echo "Reports:"
echo "  - Structured coverage: coverage_report.json"
echo "  - Browsable coverage:  htmlcov/index.html"

if [ "$TEST_EXIT_CODE" -ne 0 ] || [ "$COVERAGE_EXIT_CODE" -ne 0 ]; then
    exit 1
fi
exit 0
