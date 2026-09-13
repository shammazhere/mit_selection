#!/usr/bin/env bash
set -euo pipefail
cd "$(dirname "$0")/.."
source .venv/bin/activate
python -m unittest backend.tests.test_person2 frontend.test_adapter -v
python frontend/mock_server.py
