#!/bin/bash
# Language-agnostic coverage gate hook
# Discovers coverage report, extracts coverage %, blocks push if below threshold

set -e

# Configuration
THRESHOLD="${COVERAGE_THRESHOLD:-80}"
SEARCH_DIR="$(cd "$(dirname "${BASH_SOURCE[0]}")/.." && pwd)"  # homework-6 folder
IGNORED_DIRS=("node_modules" "venv" "__pycache__" "htmlcov" ".pytest_cache" "dist" "build")

# Colors for output
RED='\033[0;31m'
GREEN='\033[0;32m'
YELLOW='\033[1;33m'
NC='\033[0m'  # No Color

# ============================================================================
# Helper Functions
# ============================================================================

log_error() {
    echo -e "${RED}✗ $1${NC}" >&2
}

log_success() {
    echo -e "${GREEN}✓ $1${NC}"
}

log_warn() {
    echo -e "${YELLOW}⚠ $1${NC}"
}

# Check if path should be ignored
should_ignore() {
    local path="$1"
    for ignored in "${IGNORED_DIRS[@]}"; do
        if [[ "$path" == *"/$ignored/"* ]] || [[ "$path" == *"/$ignored" ]]; then
            return 0
        fi
    done
    return 1
}

# ============================================================================
# Step 1: Discover Coverage File
# ============================================================================

find_coverage_file() {
    local coverage_file=""
    local newest_time=0

    # Priority 1: Look for standard coverage report files (JSON, XML, etc.)
    # Common patterns: coverage_report.json, coverage.json, coverage.xml, .coverage, etc.
    local priority_patterns=(
        "coverage_report.json"
        "coverage.json"
        ".coverage"
        "coverage.xml"
        "coverage.txt"
    )

    for pattern in "${priority_patterns[@]}"; do
        if [[ -f "$SEARCH_DIR/$pattern" ]]; then
            echo "$SEARCH_DIR/$pattern"
            return 0
        fi
    done

    # Priority 2: Search in common coverage output directories
    local coverage_dirs=(
        "coverage"
        "htmlcov"
        ".coverage-reports"
        "coverage-reports"
    )

    for dir in "${coverage_dirs[@]}"; do
        if [[ -d "$SEARCH_DIR/$dir" ]]; then
            while IFS= read -r file; do
                local mtime=$(stat -f%m "$file" 2>/dev/null || stat -c%Y "$file" 2>/dev/null || echo 0)
                if (( mtime > newest_time )); then
                    newest_time=$mtime
                    coverage_file="$file"
                fi
            done < <(find "$SEARCH_DIR/$dir" -type f \( -name "*.json" -o -name "*.xml" -o -name "*.txt" \) 2>/dev/null)
        fi
    done

    echo "$coverage_file"
}

# ============================================================================
# Step 2: Detect File Format
# ============================================================================

detect_format() {
    local file="$1"

    if [[ "$file" == *.json ]]; then
        echo "json"
    elif [[ "$file" == *.xml ]]; then
        echo "xml"
    elif [[ "$file" == *.txt ]] || [[ "$file" == *.out ]] || [[ "$file" == *.log ]]; then
        echo "text"
    else
        # Try to detect by content
        if head -1 "$file" 2>/dev/null | grep -q "^{"; then
            echo "json"
        elif head -1 "$file" 2>/dev/null | grep -q "^<"; then
            echo "xml"
        else
            echo "text"
        fi
    fi
}

# ============================================================================
# Step 3: Extract Coverage Percentage
# ============================================================================

extract_from_json() {
    local file="$1"

    # Try common JSON paths for coverage percentage
    local paths=(
        ".totals.percent_covered"
        ".totals.percent_covered_display"
        ".total.coverage"
        ".total.percentage"
        ".coverage"
        ".percent_covered"
        ".percentage"
        ".pct_covered"
    )

    for path in "${paths[@]}"; do
        if command -v jq &> /dev/null; then
            local result=$(jq -r "$path // empty" "$file" 2>/dev/null | head -1)
            if [[ -n "$result" && "$result" != "null" ]]; then
                # Handle both "69.17" and "69" formats
                echo "$result" | grep -oE '^[0-9]+(\.[0-9]+)?' | head -1
                return 0
            fi
        fi
    done

    return 1
}

extract_from_xml() {
    local file="$1"

    # Cobertura XML format: line-rate or branch-rate attributes
    grep -oP 'line-rate="\K[0-9]+(\.[0-9]+)?' "$file" 2>/dev/null | head -1 && return 0
    grep -oP 'branch-rate="\K[0-9]+(\.[0-9]+)?' "$file" 2>/dev/null | head -1 && return 0

    return 1
}

extract_from_text() {
    local file="$1"

    # Search for patterns with keywords: total, overall, coverage, percent
    # Match patterns like: "69.17%", "Coverage: 69%", "total coverage: 69.17", etc.
    grep -oE '(total|overall|coverage|percent)[^0-9]*([0-9]+(\.[0-9]+)?)' "$file" 2>/dev/null | \
        grep -oE '[0-9]+(\.[0-9]+)?' | \
        head -1

    return 0
}

extract_coverage() {
    local file="$1"
    local format="$2"
    local coverage=""

    case "$format" in
        json)
            coverage=$(extract_from_json "$file" 2>/dev/null)
            ;;
        xml)
            coverage=$(extract_from_xml "$file" 2>/dev/null)
            ;;
        text|*)
            coverage=$(extract_from_text "$file" 2>/dev/null)
            ;;
    esac

    echo "$coverage"
}

# ============================================================================
# Step 4: Compare Against Threshold
# ============================================================================

compare_coverage() {
    local coverage="$1"
    local threshold="$2"

    # Convert to float for comparison
    local coverage_val=$(printf "%.2f" "$coverage" 2>/dev/null)
    local threshold_val=$(printf "%.2f" "$threshold" 2>/dev/null)

    # Use awk for floating point comparison
    if awk "BEGIN {exit !($coverage_val >= $threshold_val)}"; then
        return 0  # Pass
    else
        return 1  # Fail
    fi
}

# ============================================================================
# Context Detection (for multi-homework repos)
# ============================================================================

is_homework6_push() {
    # Detect if this push involves homework-6 changes
    # Returns 0 (true) if homework-6 affected, 1 (false) if not

    # Check if we're currently in homework-6 directory
    if [[ "$SEARCH_DIR" == *"/homework-6" ]]; then
        return 0
    fi

    # Check if git diff includes homework-6 files
    if git diff --name-only origin/HEAD...HEAD 2>/dev/null | grep -q "^homework-6/"; then
        return 0
    fi

    # Check if any staged changes are in homework-6
    if git diff --cached --name-only 2>/dev/null | grep -q "^homework-6/"; then
        return 0
    fi

    return 1
}

# ============================================================================
# Main Execution
# ============================================================================

main() {
    echo ""
    echo "════════════════════════════════════════════════════════════════"
    echo "Coverage Gate Check"
    echo "════════════════════════════════════════════════════════════════"

    # Skip if this push doesn't involve homework-6 (for multi-homework repos)
    if ! is_homework6_push; then
        log_warn "No homework-6 changes detected; skipping coverage gate."
        echo ""
        return 0
    fi

    # Find coverage file
    coverage_file=$(find_coverage_file)

    if [[ -z "$coverage_file" ]]; then
        log_warn "No coverage report found in $SEARCH_DIR"
        log_warn "Skipping coverage check. Run tests to generate coverage report."
        echo ""
        return 0  # Allow push if no coverage file found (tests haven't been run yet)
    fi

    log_success "Found coverage report: $(basename "$coverage_file")"

    # Detect format
    format=$(detect_format "$coverage_file")
    log_success "Detected format: $format"

    # Extract coverage
    coverage=$(extract_coverage "$coverage_file" "$format")

    if [[ -z "$coverage" ]]; then
        log_warn "Could not extract coverage percentage from $coverage_file"
        log_warn "Skipping coverage check."
        echo ""
        return 0  # Allow push if extraction fails
    fi

    # Format coverage for display
    coverage_display=$(printf "%.2f" "$coverage")

    echo ""
    echo "Coverage Metrics:"
    echo "  Actual:    $coverage_display%"
    echo "  Threshold: $THRESHOLD%"
    echo ""

    # Compare
    if compare_coverage "$coverage" "$THRESHOLD"; then
        log_success "Coverage gate passed: $coverage_display% >= $THRESHOLD%"
        echo ""
        return 0
    else
        log_error "Coverage gate FAILED: $coverage_display% < $THRESHOLD%"
        echo ""
        log_error "Push blocked. Please run tests and improve coverage before pushing."
        echo "  Command: bash run_tests.sh"
        echo ""
        return 1
    fi
}

main "$@"
