#!/bin/bash

################################################################################
# Agent Invoker Helper
#
# Invokes a project agent (defined in .claude/agents/<name>.agent.md) headlessly
# via the Claude Code CLI's non-interactive mode:
#
#   claude --agent <name> --model <model> -p "<task>" --permission-mode bypassPermissions
#
# --agent loads the named project agent as the session's system prompt (Claude
# Code auto-discovers .claude/agents/*.agent.md by their frontmatter `name:`).
# --permission-mode bypassPermissions is required because there is no TTY to
# approve file edits / test runs in a headless script; scope is limited to this
# project directory (no --add-dir), and every change lands on a git branch so
# it stays reviewable/reversible.
#
# Usage: ./invoke-agent.sh <agent-name> <agent-path> <model>
################################################################################

set -euo pipefail

AGENT_NAME="${1:?Agent name required}"
AGENT_PATH="${2:?Agent path required}"
AGENT_MODEL="${3:?Model required}"

# Max USD the CLI will spend on this single agent invocation before aborting.
MAX_BUDGET_USD="${AGENT_MAX_BUDGET_USD:-3}"

# Colors
RED='\033[0;31m'
GREEN='\033[0;32m'
YELLOW='\033[1;33m'
BLUE='\033[0;34m'
NC='\033[0m'

log() {
  echo -e "${BLUE}[invoke-agent]${NC} $*" >&2
}

success() {
  echo -e "${GREEN}✓${NC} $*" >&2
}

error() {
  echo -e "${RED}✗${NC} $*" >&2
}

warning() {
  echo -e "${YELLOW}⚠${NC} $*" >&2
}

################################################################################
# Task prompts per agent
#
# Each agent's full workflow (what to read, what to produce, where to write
# it) already lives in its .agent.md body, which becomes the session's system
# prompt via --agent. The -p prompt only needs to kick the agent off.
################################################################################

task_prompt_for() {
  case "$1" in
    research-verifier)
      echo "Run your full 3-phase workflow (research, verify, plan) against the current state of src/. Create research/codebase-research.md, research/verified-research.md, and the implementation plan under context/bugs/. Begin now."
      ;;
    bug-fixer)
      echo "Read the implementation plan under context/bugs/ (most recently modified bug directory) and apply the fixes it describes, sequentially with checkpoints, running tests after each one. Create fix-summary.md in that same directory. Begin now."
      ;;
    security-verifier)
      echo "Read fix-summary.md under context/bugs/ (most recently modified bug directory), scan the changed files for vulnerabilities, and create security-report.md in that same directory. Begin now."
      ;;
    unit-test-generator)
      echo "Read fix-summary.md under context/bugs/ (most recently modified bug directory), generate/append unit tests for the changed code, run them, and create test-report.md in that same directory. Begin now."
      ;;
    *)
      echo "Follow your defined workflow for this repository and complete it fully. Begin now."
      ;;
  esac
}

################################################################################
# Invocation
################################################################################

# Prints a live, human-readable feed of an agent's stream-json output:
# assistant text/tool calls as they happen, tool results, and the final
# result/cost line. Sets RESULT_LINE (the raw "type":"result" JSON) so the
# caller can inspect success/cost/output after the stream ends.
render_stream_line() {
  local line="$1"
  local type
  type=$(printf '%s' "$line" | jq -r '.type // empty' 2>/dev/null) || return 0

  case "$type" in
    assistant)
      printf '%s' "$line" | jq -r '
        .message.content[]? |
        if .type == "text" then "  💬 " + .text
        elif .type == "tool_use" then "  🔧 " + .name + " " + ((.input | tostring)[0:120])
        else empty end' 2>/dev/null
      ;;
    user)
      printf '%s' "$line" | jq -r '
        .message.content[]? | select(.type == "tool_result") |
        "  ↩  " + ((.content | if type == "array" then map(.text // "") | join(" ") else tostring end)[0:200] | gsub("\n"; " "))' 2>/dev/null
      ;;
    result)
      RESULT_LINE="$line"
      ;;
  esac
}

invoke_via_claude_cli() {
  if ! command -v claude &> /dev/null; then
    error "Claude Code CLI not found in PATH"
    return 1
  fi

  local task
  task="$(task_prompt_for "$AGENT_NAME")"

  log "Invoking via: claude --agent $AGENT_NAME --model $AGENT_MODEL -p ... --permission-mode bypassPermissions"
  echo -e "${BLUE}  ── live output: $AGENT_NAME ──${NC}" >&2

  RESULT_LINE=""
  local output_file
  output_file=$(mktemp)
  local claude_exit=0

  # Capture full output AND exit code properly
  set +e
  claude --agent "$AGENT_NAME" \
      --model "$AGENT_MODEL" \
      --permission-mode bypassPermissions \
      --max-budget-usd "$MAX_BUDGET_USD" \
      --output-format stream-json \
      --verbose \
      -p "$task" 2>&1 | tee "$output_file" | while IFS= read -r line; do
        render_stream_line "$line" >&2
      done
  claude_exit=${PIPESTATUS[0]}
  set -e

  echo -e "${BLUE}  ── end output: $AGENT_NAME ──${NC}" >&2

  # Parse result from captured output
  RESULT_LINE=$(grep '"type":"result"' "$output_file" 2>/dev/null | tail -1)

  if [[ "$claude_exit" -ne 0 ]]; then
    error "claude CLI exited non-zero ($claude_exit) for agent: $AGENT_NAME"
    log "Full output saved. Check error details above."
    rm -f "$output_file"
    return 1
  fi

  if [[ -z "$RESULT_LINE" ]]; then
    error "No result received from agent: $AGENT_NAME (stream ended early)"
    log "Output file: $output_file"
    rm -f "$output_file"
    return 1
  fi

  local is_error cost result_text
  is_error=$(printf '%s' "$RESULT_LINE" | jq -r '.is_error // false')
  cost=$(printf '%s' "$RESULT_LINE" | jq -r '.total_cost_usd // "?"')
  result_text=$(printf '%s' "$RESULT_LINE" | jq -r '.result // ""')

  if [[ "$is_error" == "true" ]]; then
    error "Agent reported an error (cost: \$${cost})"
    echo "$result_text" >&2
    rm -f "$output_file"
    return 1
  fi

  echo -e "${BLUE}  ── final report: $AGENT_NAME ──${NC}" >&2
  echo "$result_text" >&2
  echo "" >&2

  success "Agent invoked via Claude CLI (cost: \$${cost})"
  rm -f "$output_file"
  return 0
}

print_manual_invocation() {
  echo ""
  echo "═══════════════════════════════════════════════════════════════"
  echo "AGENT INVOCATION GUIDE (automatic invocation failed)"
  echo "═══════════════════════════════════════════════════════════════"
  echo ""
  echo "To manually invoke this agent:"
  echo "  \$ claude --agent $AGENT_NAME --model $AGENT_MODEL --permission-mode bypassPermissions -p \"$(task_prompt_for "$AGENT_NAME")\""
  echo ""
  echo "Or interactively:"
  echo "  1. Open Claude Code in this project directory"
  echo "  2. Ask it to use the $AGENT_NAME agent"
  echo ""
  echo "Agent Details:"
  echo "  Name: $AGENT_NAME"
  echo "  Path: $AGENT_PATH"
  echo "  Model: $AGENT_MODEL"
  echo "═══════════════════════════════════════════════════════════════"
  echo ""
}

################################################################################
# Main
################################################################################

main() {
  log "Invoking agent: $AGENT_NAME"
  log "  Path: $AGENT_PATH"
  log "  Model: $AGENT_MODEL"
  echo ""

  if [[ ! -f "$AGENT_PATH" ]]; then
    error "Agent file not found: $AGENT_PATH"
    return 1
  fi

  if invoke_via_claude_cli; then
    return 0
  fi

  warning "Could not automatically invoke agent"
  print_manual_invocation
  error "Agent invocation failed"
  return 1
}

main "$@"
exit $?
