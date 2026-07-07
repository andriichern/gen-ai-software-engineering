#!/usr/bin/env bash
# Starts both the API (http://localhost:8000) and the frontend
# (http://localhost:5173) together. Ctrl+C stops both cleanly.
set -uo pipefail

SCRIPT_DIR="$(cd "$(dirname "${BASH_SOURCE[0]}")" && pwd)"

API_PID=""
APP_PID=""

cleanup() {
  echo
  echo "Stopping servers ..."
  [ -n "$API_PID" ] && kill "$API_PID" 2>/dev/null
  [ -n "$APP_PID" ] && kill "$APP_PID" 2>/dev/null
  # npm run dev spawns vite as a child process that a plain `kill` above may
  # not reach, so also sweep by name as a safety net.
  pkill -f "uvicorn api.main" 2>/dev/null
  pkill -f "node .*vite" 2>/dev/null
  wait 2>/dev/null
}
trap cleanup EXIT INT TERM

"$SCRIPT_DIR/run-api.sh" &
API_PID=$!

"$SCRIPT_DIR/run-app.sh" &
APP_PID=$!

echo "API:      http://localhost:8000"
echo "Frontend: http://localhost:5173"
echo "Press Ctrl+C to stop both."

wait "$API_PID" "$APP_PID"
