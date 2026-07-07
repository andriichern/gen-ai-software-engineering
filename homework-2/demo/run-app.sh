#!/usr/bin/env bash
# Starts the Svelte frontend dev server (http://localhost:5173), installing
# node_modules on first run if needed.
set -euo pipefail

SCRIPT_DIR="$(cd "$(dirname "${BASH_SOURCE[0]}")" && pwd)"
APP_DIR="$(cd "$SCRIPT_DIR/../src/app" && pwd)"

if [ ! -d "$APP_DIR/node_modules" ]; then
  echo "Installing frontend dependencies ..."
  (cd "$APP_DIR" && npm install)
fi

echo "Starting frontend on http://localhost:5173 ..."
cd "$APP_DIR"
exec npm run dev
