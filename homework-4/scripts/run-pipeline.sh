#!/bin/bash

################################################################################
# 4-Agent Pipeline Orchestrator
#
# Orchestrates the 4-agent bug detection and fixing pipeline:
# 1. Research Verifier - identifies bugs
# 2. Bug Fixer - applies fixes (conditional on bugs found)
# 3. Security Verifier & Unit Test Generator - parallel verification (conditional on changes)
#
# Usage: ./scripts/run-pipeline.sh [--dry-run|--execute]
# Default: --dry-run (safe testing mode)
################################################################################

set -euo pipefail

# Configuration
SCRIPT_DIR="$(cd "$(dirname "${BASH_SOURCE[0]}")" && pwd)"
PROJECT_ROOT="$(dirname "$SCRIPT_DIR")"
DRY_RUN="${1:---dry-run}"
TIMESTAMP=$(date '+%Y-%m-%d %H:%M:%S')
LOG_FILE="${PROJECT_ROOT}/pipeline-execution.log"

# Agent paths
RESEARCH_VERIFIER="${PROJECT_ROOT}/.claude/agents/research-verifier.agent.md"
BUG_FIXER="${PROJECT_ROOT}/.claude/agents/bug-fixer.agent.md"
SECURITY_VERIFIER="${PROJECT_ROOT}/.claude/agents/security-verifier.agent.md"
UNIT_TEST_GENERATOR="${PROJECT_ROOT}/.claude/agents/unit-test-generator.agent.md"

# Context paths (using XXX placeholder pattern)
CONTEXT_BASE="${PROJECT_ROOT}/context/bugs"
BUG_DIR="" # Will be determined after research phase

# Colors for output
RED='\033[0;31m'
GREEN='\033[0;32m'
YELLOW='\033[1;33m'
BLUE='\033[0;34m'
NC='\033[0m' # No Color

################################################################################
# Utility Functions
################################################################################

log() {
  echo -e "${BLUE}[$(date '+%H:%M:%S')]${NC} $*"
  echo "[${TIMESTAMP}] $*" >> "$LOG_FILE"
}

success() {
  echo -e "${GREEN}✓${NC} $*"
  echo "✓ $*" >> "$LOG_FILE"
}

warning() {
  echo -e "${YELLOW}⚠${NC} $*"
  echo "⚠ $*" >> "$LOG_FILE"
}

error() {
  echo -e "${RED}✗${NC} $*"
  echo "✗ $*" >> "$LOG_FILE"
}

step() {
  echo -e "\n${BLUE}━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━${NC}"
  echo -e "${BLUE}STEP: $*${NC}"
  echo -e "${BLUE}━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━${NC}"
  echo "[STEP] $*" >> "$LOG_FILE"
}

run_agent() {
  local agent_name="$1"
  local agent_path="$2"
  local agent_model="$3"

  if [[ "$DRY_RUN" == "--dry-run" ]]; then
    log "[DRY-RUN] Would invoke agent: $agent_name (model: $agent_model)"
    log "[DRY-RUN]   Agent file: $agent_path"
    log "[DRY-RUN]   Working directory: $(pwd)"
    return 0
  else
    log "[EXECUTE] Invoking agent: $agent_name (model: $agent_model)"
    log "[EXECUTE]   Agent definition: $agent_path"
    echo ""

    # Use the invoke-agent helper script to handle agent invocation
    # The helper:
    # 1. Uses Claude Code CLI with --permission-mode bypassPermissions
    # 2. Shows live output stream as agent executes
    # 3. Displays tool calls, results, and final cost
    # 4. Falls back to manual invocation guide on failure

    # Capture exit code while letting output stream through
    local agent_exit=0
    "$SCRIPT_DIR/invoke-agent.sh" "$agent_name" "$agent_path" "$agent_model" || agent_exit=$?

    echo ""

    if [[ $agent_exit -eq 0 ]]; then
      success "Agent completed successfully: $agent_name"
      log "Check output above for agent progress and results"
      return 0
    else
      error "Failed to complete agent: $agent_name (exit code: $agent_exit)"
      log "Review the agent output above for error details"
      log "You can manually invoke with: claude --agent $agent_name --model $agent_model --permission-mode bypassPermissions"
      return 1
    fi
  fi
}

dry_run_cmd() {
  if [[ "$DRY_RUN" == "--dry-run" ]]; then
    log "[DRY-RUN] Would execute: $*"
    return 0
  else
    log "[EXECUTE] Running: $*"
    eval "$@"
  fi
}

validate_agent() {
  local agent_file="$1"
  if [[ ! -f "$agent_file" ]]; then
    error "Agent not found: $agent_file"
    return 1
  fi
  success "Agent found: $(basename "$agent_file")"
  return 0
}

find_bug_directory() {
  # Find the most recently modified bug directory (by modification time, not alphabetically)
  local latest_bug_dir=""
  if [[ -d "$CONTEXT_BASE" ]]; then
    # Use find with -printf to get modification time, sort by time descending, take most recent
    latest_bug_dir=$(find "$CONTEXT_BASE" -maxdepth 1 -type d ! -name "bugs" -printf '%T@ %p\n' 2>/dev/null | sort -rn | head -1 | cut -d' ' -f2-)
  fi

  if [[ -z "$latest_bug_dir" ]]; then
    # Fallback: if no directory found by modification time, list available ones
    if ls -d "$CONTEXT_BASE"/*/ 2>/dev/null | head -1 > /dev/null; then
      latest_bug_dir=$(ls -d "$CONTEXT_BASE"/*/ | head -1)
    else
      return 1
    fi
  fi

  echo "$latest_bug_dir"
  return 0
}

verify_required_file() {
  local file="$1"
  local name="${2:-file}"

  if [[ ! -f "$file" ]]; then
    error "Required $name not found: $file"
    return 1
  fi

  if [[ ! -s "$file" ]]; then
    error "Required $name is empty: $file"
    return 1
  fi

  success "Verified $name exists: $(basename "$file")"
  return 0
}

has_bugs_been_found() {
  # Check if implementation-plan.md exists and has content indicating bugs were found
  local plan_file="${1}/implementation-plan.md"

  if [[ ! -f "$plan_file" ]]; then
    return 1
  fi

  # Check for "no fixes" or "no issues" markers
  if grep -qi "no verified issues found\|no fixes required\|no fixes to apply" "$plan_file" 2>/dev/null; then
    return 1
  fi

  # Check for at least one fix entry
  if grep -qi "^### Fix\|^## Fix\|Fix [0-9]\|fix:" "$plan_file" 2>/dev/null; then
    return 0
  fi

  return 1
}

has_changes_been_made() {
  # Check if fix-summary.md exists and indicates changes were made
  local summary_file="${1}/fix-summary.md"

  if [[ ! -f "$summary_file" ]]; then
    return 1
  fi

  # Check for success status or changes made
  if grep -qi "no fixes to apply\|no changes\|stopped at fix" "$summary_file" 2>/dev/null; then
    return 1
  fi

  # Check for successful fixes
  if grep -qi "fixes successful\|status.*passed\|changes made" "$summary_file" 2>/dev/null; then
    return 0
  fi

  # If we have fixes applied section with content, assume changes were made
  if grep -qi "^### Fix [0-9].*:.*passed\|^### Fix [0-9].*✅" "$summary_file" 2>/dev/null; then
    return 0
  fi

  return 1
}

################################################################################
# Initialize Pipeline
################################################################################

initialize_pipeline() {
  step "INITIALIZING PIPELINE"

  log "Mode: $DRY_RUN"
  log "Project root: $PROJECT_ROOT"
  log "Timestamp: $TIMESTAMP"
  log "Log file: $LOG_FILE"

  # Verify all agents exist
  validate_agent "$RESEARCH_VERIFIER" || return 1
  validate_agent "$BUG_FIXER" || return 1
  validate_agent "$SECURITY_VERIFIER" || return 1
  validate_agent "$UNIT_TEST_GENERATOR" || return 1

  # Verify context directory
  if [[ ! -d "$CONTEXT_BASE" ]]; then
    error "Context directory not found: $CONTEXT_BASE"
    return 1
  fi
  success "Context directory found"

  success "Pipeline initialization complete"
  return 0
}

################################################################################
# Phase 1: Research Verifier
################################################################################

run_research_verifier() {
  step "PHASE 1: BUG RESEARCH VERIFIER"

  log "Research Verifier will:"
  log "  - Analyze source code in src/"
  log "  - Identify code-logic bugs (validation, state machines, comparisons, data handling)"
  log "  - Verify findings and assign severity levels"
  log "  - Create research/codebase-research.md"
  log "  - Create research/verified-research.md"
  log "  - Create implementation-plan.md for Bug Fixer"
  echo ""

  run_agent "research-verifier" "$RESEARCH_VERIFIER" "claude-sonnet-5" || return 1

  # Determine bug directory
  BUG_DIR=$(find_bug_directory) || {
    warning "Could not find bug context directory"
    BUG_DIR="${CONTEXT_BASE}/order-validation-and-logic"
  }

  log "Using bug context directory: $BUG_DIR"

  success "Research Verifier phase complete"
}

check_research_results() {
  step "CHECKING RESEARCH RESULTS"

  if [[ -z "$BUG_DIR" ]]; then
    BUG_DIR=$(find_bug_directory) || {
      error "Could not locate bug directory"
      return 1
    }
  fi

  local plan_file="${BUG_DIR}/implementation-plan.md"

  # Verify implementation plan exists and is not empty
  if ! verify_required_file "$plan_file" "implementation-plan.md"; then
    return 1
  fi

  if has_bugs_been_found "$BUG_DIR"; then
    success "Bugs found! Proceeding to Bug Fixer phase"
    return 0
  else
    warning "No bugs found by Research Verifier"
    log "Implementation plan indicates no issues to fix"
    return 1
  fi
}

################################################################################
# Phase 2: Bug Fixer
################################################################################

run_bug_fixer() {
  step "PHASE 2: BUG FIXER"

  if [[ -z "$BUG_DIR" ]]; then
    error "Bug directory not set. This should not happen."
    return 1
  fi

  log "Bug Fixer will:"
  log "  - Read implementation-plan.md from $BUG_DIR"
  log "  - Apply fixes sequentially with checkpoints"
  log "  - Run tests after each fix"
  log "  - Handle failures with retry logic and rollback"
  log "  - Create fix-summary.md with before/after test results"
  echo ""

  run_agent "bug-fixer" "$BUG_FIXER" "claude-haiku-4-5" || return 1

  success "Bug Fixer phase complete"
}

check_fixer_results() {
  step "CHECKING BUG FIXER RESULTS"

  if [[ -z "$BUG_DIR" ]]; then
    error "Bug directory not set"
    return 1
  fi

  local summary_file="${BUG_DIR}/fix-summary.md"

  # Verify fix summary exists and is not empty
  if ! verify_required_file "$summary_file" "fix-summary.md"; then
    return 1
  fi

  if has_changes_been_made "$BUG_DIR"; then
    success "Changes were made! Proceeding to parallel verification phases"
    return 0
  else
    warning "No changes were made by Bug Fixer"
    log "Skipping Security Verifier and Unit Test Generator phases"
    return 1
  fi
}

################################################################################
# Phase 3: Security Verifier (Parallel)
################################################################################

run_security_verifier() {
  step "PHASE 3A: SECURITY VULNERABILITIES VERIFIER (parallel)"

  if [[ -z "$BUG_DIR" ]]; then
    error "Bug directory not set"
    return 1
  fi

  log "Security Verifier will:"
  log "  - Read fix-summary.md to identify changed files"
  log "  - Scan changed code for security vulnerabilities"
  log "  - Check OWASP Top 15 framework issues"
  log "  - Verify injection, secrets, comparisons, validation, deps, XSS/CSRF"
  log "  - Create security-report.md with severity ratings and remediation"
  echo ""

  run_agent "security-verifier" "$SECURITY_VERIFIER" "claude-sonnet-5" || return 1

  success "Security Verifier phase complete"
}

################################################################################
# Phase 4: Unit Test Generator (Parallel)
################################################################################

run_unit_test_generator() {
  step "PHASE 3B: UNIT TEST GENERATOR (parallel)"

  if [[ -z "$BUG_DIR" ]]; then
    error "Bug directory not set"
    return 1
  fi

  log "Unit Test Generator will:"
  log "  - Auto-detect programming language and test framework"
  log "  - Extract changed files from fix-summary.md"
  log "  - Analyze changed code logic and edge cases"
  log "  - Generate tests following FIRST principles"
  log "  - Target 95%+ code coverage (happy path + errors + edges)"
  log "  - Create/append test files and generate test-report.md"
  echo ""

  run_agent "unit-test-generator" "$UNIT_TEST_GENERATOR" "claude-haiku-4-5" || return 1

  success "Unit Test Generator phase complete"
}

################################################################################
# Parallel Execution
################################################################################

wait_file_stable() {
  local file="$1"
  local max_wait=5000  # milliseconds
  local elapsed=0
  local check_interval=100  # milliseconds
  local prev_size=0
  local curr_size=0

  log "Waiting for $file to become stable..."

  # Get initial size
  prev_size=$(stat -f%z "$file" 2>/dev/null || echo 0)

  # Wait until file size doesn't change for 200ms (two consecutive checks)
  while [[ $elapsed -lt $max_wait ]]; do
    sleep 0.1  # 100ms
    elapsed=$((elapsed + 100))

    curr_size=$(stat -f%z "$file" 2>/dev/null || echo 0)

    if [[ "$prev_size" -eq "$curr_size" ]]; then
      # Size unchanged on consecutive check - file is stable
      success "File is stable ($curr_size bytes)"
      return 0
    fi

    prev_size=$curr_size
  done

  error "File did not stabilize within ${max_wait}ms"
  return 1
}

run_parallel_phases() {
  step "RUNNING PARALLEL VERIFICATION PHASES"

  # Ensure fix-summary.md is stable before parallel agents start reading it
  if [[ -z "$BUG_DIR" ]]; then
    error "Bug directory not set before parallel phases"
    return 1
  fi

  local summary_file="${BUG_DIR}/fix-summary.md"
  if ! wait_file_stable "$summary_file"; then
    error "fix-summary.md did not stabilize - aborting parallel phases"
    return 1
  fi

  log "Starting Security Verifier and Unit Test Generator in parallel..."

  if [[ "$DRY_RUN" == "--dry-run" ]]; then
    # In dry-run mode, simulate parallel execution with logging
    log "[DRY-RUN - Background Job 1] Security Verifier"
    run_security_verifier &
    SECURITY_PID=$!

    log "[DRY-RUN - Background Job 2] Unit Test Generator"
    run_unit_test_generator &
    TEST_PID=$!

    log "Simulating parallel execution..."
    log "  Job 1 PID: $SECURITY_PID (Security Verifier)"
    log "  Job 2 PID: $TEST_PID (Unit Test Generator)"
    log "  Agents would run simultaneously"

    # Wait for both jobs
    if ! wait $SECURITY_PID; then
      error "Security Verifier phase failed (PID: $SECURITY_PID)"
      return 1
    fi
    if ! wait $TEST_PID; then
      error "Unit Test Generator phase failed (PID: $TEST_PID)"
      return 1
    fi

    success "Parallel phase simulation complete"
  else
    # In execute mode, actually run agents in parallel
    log "Invoking Security Verifier in background..."
    run_security_verifier &
    SECURITY_PID=$!

    log "Invoking Unit Test Generator in background..."
    run_unit_test_generator &
    TEST_PID=$!

    log "Both agents now running in parallel..."
    log "  Security Verifier PID: $SECURITY_PID"
    log "  Unit Test Generator PID: $TEST_PID"

    # Wait for Security Verifier
    log "Waiting for Security Verifier to complete (PID: $SECURITY_PID)..."
    if wait $SECURITY_PID; then
      success "Security Verifier completed successfully"
    else
      error "Security Verifier encountered an error (PID: $SECURITY_PID)"
      return 1
    fi

    # Wait for Unit Test Generator
    log "Waiting for Unit Test Generator to complete (PID: $TEST_PID)..."
    if wait $TEST_PID; then
      success "Unit Test Generator completed successfully"
    else
      error "Unit Test Generator encountered an error (PID: $TEST_PID)"
      return 1
    fi

    success "All parallel phases completed successfully"
  fi
}

################################################################################
# Summary & Completion
################################################################################

print_summary() {
  step "PIPELINE EXECUTION SUMMARY"

  if [[ -z "$BUG_DIR" ]]; then
    BUG_DIR=$(find_bug_directory) || BUG_DIR="${CONTEXT_BASE}/order-validation-and-logic"
  fi

  echo -e "\n${BLUE}Pipeline Mode:${NC} $DRY_RUN"
  echo -e "${BLUE}Context Directory:${NC} $BUG_DIR"
  echo -e "${BLUE}Log File:${NC} $LOG_FILE"

  echo -e "\n${BLUE}Generated Files:${NC}"

  # Check Phase 1 outputs
  if [[ -f "$BUG_DIR/implementation-plan.md" ]]; then
    echo -e "  ${GREEN}✓${NC} Research Phase: implementation-plan.md"
  else
    echo -e "  ${YELLOW}○${NC} Research Phase: implementation-plan.md (not yet generated)"
  fi

  # Check Phase 2 outputs
  if [[ -f "$BUG_DIR/fix-summary.md" ]]; then
    echo -e "  ${GREEN}✓${NC} Fixer Phase: fix-summary.md"
  else
    echo -e "  ${YELLOW}○${NC} Fixer Phase: fix-summary.md (not yet generated)"
  fi

  # Check Phase 3 outputs
  if [[ -f "$BUG_DIR/security-report.md" ]]; then
    echo -e "  ${GREEN}✓${NC} Security Phase: security-report.md"
  else
    echo -e "  ${YELLOW}○${NC} Security Phase: security-report.md (not yet generated)"
  fi

  # Check Phase 4 outputs
  if [[ -f "$BUG_DIR/test-report.md" ]]; then
    echo -e "  ${GREEN}✓${NC} Test Phase: test-report.md"
  else
    echo -e "  ${YELLOW}○${NC} Test Phase: test-report.md (not yet generated)"
  fi

  echo -e "\n${BLUE}Next Steps:${NC}"
  if [[ "$DRY_RUN" == "--dry-run" ]]; then
    echo "  1. Review pipeline flow above"
    echo "  2. Run real pipeline: $SCRIPT_DIR/run-pipeline.sh --execute"
    echo "  3. Check log file: $LOG_FILE"
  else
    echo "  1. Review generated output files in $BUG_DIR"
    echo "  2. Check application fixes in src/"
    echo "  3. Review test results and coverage"
  fi

  success "Pipeline summary complete"
}

################################################################################
# Error Handling
################################################################################

cleanup_on_error() {
  error "Pipeline execution failed"
  echo ""
  log "Cleaning up background processes..."
  if [[ ! -z "${SECURITY_PID:-}" ]]; then
    kill $SECURITY_PID 2>/dev/null || true
  fi
  if [[ ! -z "${TEST_PID:-}" ]]; then
    kill $TEST_PID 2>/dev/null || true
  fi
  return 1
}

trap 'cleanup_on_error' ERR

################################################################################
# Main Pipeline Orchestration
################################################################################

main() {
  log "═══════════════════════════════════════════════════════════════"
  log "4-AGENT BUG DETECTION AND FIXING PIPELINE"
  log "═══════════════════════════════════════════════════════════════"
  log "Mode: $DRY_RUN"

  # Validate arguments
  if [[ ! "$DRY_RUN" =~ ^--(dry-run|execute)$ ]]; then
    error "Invalid argument: $DRY_RUN"
    echo "Usage: $0 [--dry-run|--execute]"
    return 1
  fi

  # Initialize
  initialize_pipeline || return 1

  # Phase 1: Research
  run_research_verifier || return 1

  # Check research results
  if ! check_research_results; then
    warning "Skipping remaining phases: no bugs found"
    print_summary
    success "Pipeline completed (no bugs to fix)"
    return 0
  fi

  # Phase 2: Bug Fixing
  run_bug_fixer || return 1

  # Check fixer results
  if ! check_fixer_results; then
    warning "Skipping parallel phases: no changes made"
    print_summary
    success "Pipeline completed (no changes applied)"
    return 0
  fi

  # Phase 3 & 4: Parallel Verification
  run_parallel_phases || return 1

  # Summary
  print_summary
  success "Pipeline completed successfully!"

  log "═══════════════════════════════════════════════════════════════"

  return 0
}

# Run main function
cd "$PROJECT_ROOT"
main "$@"
exit $?
