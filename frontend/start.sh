#!/usr/bin/env bash
# Person 1 UI + Person 2 scores. Run from repo root or frontend folder.
set -euo pipefail
ROOT="$(cd "$(dirname "$0")/.." && pwd)"
cd "$ROOT"

# Select Python binary (prefer repo .venv if present)
if [ -x "$ROOT/.venv/bin/python3" ]; then
  PYTHON="$ROOT/.venv/bin/python3"
elif command -v python3 >/dev/null 2>&1; then
  PYTHON="python3"
else
  echo "Error: Python 3 not found." >&2
  exit 1
fi

# Ensure Person 2 scores table exists
if [ ! -f "$ROOT/backend/output/daily_user_scores.csv" ]; then
  echo "Person 2 scores not found. Generating sample CERT data and Contract A scores..."
  "$PYTHON" -m backend --sample
fi

echo "Starting Person 1 Mock Server (Contract B API on port 8787)..."
"$PYTHON" frontend/mock_server.py &
MOCK_PID=$!
trap 'kill $MOCK_PID 2>/dev/null || true' EXIT

sleep 0.5
echo "Starting Vite Frontend Dashboard on http://127.0.0.1:5173..."
cd "$ROOT/frontend"
npx vite --host 127.0.0.1 --port 5173
