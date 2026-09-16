#!/usr/bin/env bash
# Silent Shift — Clean Slate Script
# Wipes all risk scores, feedback overrides, and audit logs for a fresh live demo.
# Works from repo root, frontend directory, or any subfolder.

SCRIPT_DIR="$(cd "$(dirname "${BASH_SOURCE[0]}")" && pwd -P)"
if [ "$(basename "$SCRIPT_DIR")" = "frontend" ] || [ "$(basename "$SCRIPT_DIR")" = "backend" ]; then
    ROOT="$(cd "$SCRIPT_DIR/.." && pwd -P)"
else
    ROOT="$SCRIPT_DIR"
fi

DB_PATH="$ROOT/backend/data/scores.db"

python3 -c "
import sqlite3, os
p = '$DB_PATH'
try:
    conn = sqlite3.connect(p)
    conn.executescript('''
        DELETE FROM risk_scores;
        DELETE FROM feedback;
        DELETE FROM feedback_stats;
        DELETE FROM audit_access_log;
        DELETE FROM sqlite_sequence;
        VACUUM;
    ''')
    conn.close()
    print('🧹 [Silent Shift] All history, scores, and feedback wiped clean!')
except Exception as e:
    print(f'Error clearing DB: {e}')
"

# Remove temporary sensor caches
rm -f /tmp/silent_shift_chrome_tmp* 2>/dev/null || true
