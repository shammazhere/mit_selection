#!/usr/bin/env bash
# Silent Shift — Clean Slate Script
# Wipes all risk scores, feedback overrides, and audit logs for a fresh live demo.

ROOT="$(cd "$(dirname "$0")" && pwd)"
DB_PATH="$ROOT/backend/data/scores.db"

python3 -c "
import sqlite3
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

# Remove any temporary agent cache
rm -f /tmp/silent_shift_chrome_tmp* 2>/dev/null || true
