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

# Ensure Person 3 database exists and is populated
if [ ! -f "$ROOT/backend/data/scores.db" ]; then
  echo "Running Person 3 pipeline to populate risk scores database..."
  "$PYTHON" backend/pipeline.py
fi

echo "Starting Person 3 FastAPI Backend (Contract B API on http://127.0.0.1:8787)..."
"$PYTHON" -m uvicorn backend.api.main:app --host 127.0.0.1 --port 8787 &
API_PID=$!
trap 'kill $API_PID 2>/dev/null || true' EXIT

sleep 1
echo "Starting Vite Frontend Dashboard on http://127.0.0.1:5173..."
cd "$ROOT/frontend"
npx vite --host 127.0.0.1 --port 5173
