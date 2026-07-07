#!/usr/bin/env bash
# Starts the FastAPI backend (http://localhost:8000), installing its venv/deps
# on first run if needed.
set -euo pipefail

SCRIPT_DIR="$(cd "$(dirname "${BASH_SOURCE[0]}")" && pwd)"
SRC_DIR="$(cd "$SCRIPT_DIR/../src" && pwd)"
API_DIR="$SRC_DIR/api"
VENV_DIR="$API_DIR/.venv"

PYTHON_BIN="${PYTHON_BIN:-}"
if [ -z "$PYTHON_BIN" ]; then
  if command -v python3.9 >/dev/null 2>&1; then
    PYTHON_BIN=python3.9
  else
    PYTHON_BIN=python3
  fi
fi

if [ ! -d "$VENV_DIR" ]; then
  echo "Creating API virtualenv at $VENV_DIR ..."
  "$PYTHON_BIN" -m venv "$VENV_DIR"
fi

echo "Installing/checking API dependencies ..."
"$VENV_DIR/bin/pip" install -q -r "$API_DIR/requirements.txt"

echo "Starting API on http://localhost:8000 ..."
cd "$SRC_DIR"
exec "$VENV_DIR/bin/python" -m uvicorn api.main:app --host 0.0.0.0 --port 8000 --reload
