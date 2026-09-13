"""
Database Layer

SQLite persistence for feedback and caching.
"""

import sqlite3
from typing import Optional, List, Dict, Any
from datetime import datetime
import os
import json


class Database:
    """SQLite database wrapper for feedback persistence."""
    
    def __init__(self, db_path: str = "data/scores.db"):
        """Initialize database connection."""
        self.db_path = db_path
        self._ensure_data_dir()
        self._init_database()
    
    def _ensure_data_dir(self):
        """Create data directory if it doesn't exist."""
        data_dir = os.path.dirname(self.db_path)
        if data_dir and not os.path.exists(data_dir):
            os.makedirs(data_dir)
    
    def _init_database(self):
        """Initialize database schema."""
        with sqlite3.connect(self.db_path) as conn:
            cursor = conn.cursor()
            
            # Table for cached risk scores (per user per day)
            cursor.execute("""
                CREATE TABLE IF NOT EXISTS risk_scores (
                    user_id TEXT NOT NULL,
                    date TEXT NOT NULL,
                    self_score REAL NOT NULL,
                    peer_score REAL NOT NULL,
                    drift_score REAL NOT NULL,
                    pre_multiplier_score REAL NOT NULL,
                    raw_fusion_score REAL NOT NULL,
                    adjusted_fusion_score REAL NOT NULL,
                    risk_score REAL NOT NULL,
                    cohort_used TEXT,
                    cohort_size INTEGER,
                    fallback_applied INTEGER NOT NULL,
                    role TEXT,
                    name TEXT,
                    cusum_path TEXT,
                    multipliers_applied TEXT,
                    score_components TEXT,
                    severity TEXT,
                    explanation_text TEXT,
                    last_updated TEXT NOT NULL,
                    PRIMARY KEY (user_id, date)
                )
            """)
            
            # Table for feedback
            cursor.execute("""
                CREATE TABLE IF NOT EXISTS feedback (
                    id INTEGER PRIMARY KEY AUTOINCREMENT,
                    user_id TEXT NOT NULL,
                    is_false_positive INTEGER NOT NULL,
                    reason TEXT,
                    created_at TEXT NOT NULL,
                    down_weight REAL NOT NULL DEFAULT 1.0
                )
            """)
            
            # Table for feedback statistics
            cursor.execute("""
                CREATE TABLE IF NOT EXISTS feedback_stats (
                    user_id TEXT NOT NULL,
                    feedback_date TEXT NOT NULL,
                    false_positive_count INTEGER NOT NULL DEFAULT 0,
                    total_feedback INTEGER NOT NULL DEFAULT 0,
                    down_weight REAL NOT NULL DEFAULT 1.0,
                    last_updated TEXT NOT NULL,
                    PRIMARY KEY (user_id, feedback_date)
                )
            """)
            
            conn.commit()
    
    def upsert_risk_score(self, score_data: Dict[str, Any]):
        """Upsert a risk score record."""
        with sqlite3.connect(self.db_path) as conn:
            cursor = conn.cursor()
            
            # Convert lists/dicts to JSON for storage
            if "cusum_path" in score_data and isinstance(score_data["cusum_path"], list):
                score_data["cusum_path"] = json.dumps(score_data["cusum_path"])
            if "multipliers_applied" in score_data and isinstance(score_data["multipliers_applied"], dict):
                score_data["multipliers_applied"] = json.dumps(score_data["multipliers_applied"])
            if "score_components" in score_data and isinstance(score_data["score_components"], dict):
                score_data["score_components"] = json.dumps(score_data["score_components"])
            
            # Convert boolean to integer
            score_data["fallback_applied"] = 1 if score_data.get("fallback_applied", False) else 0
            
            cursor.execute("""
                INSERT OR REPLACE INTO risk_scores (
                    user_id, date, self_score, peer_score, drift_score,
                    pre_multiplier_score, raw_fusion_score, adjusted_fusion_score,
                    risk_score, cohort_used, cohort_size, fallback_applied,
                    role, name, cusum_path, multipliers_applied,
                    score_components, severity, explanation_text, last_updated
                ) VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?)
            """, (
                score_data.get("user_id"),
                score_data.get("date"),
                score_data.get("self_score"),
                score_data.get("peer_score"),
                score_data.get("drift_score"),
                score_data.get("pre_multiplier_score"),
                score_data.get("raw_fusion_score"),
                score_data.get("adjusted_fusion_score"),
                score_data.get("risk_score"),
                score_data.get("cohort_used"),
                score_data.get("cohort_size"),
                score_data.get("fallback_applied"),
                score_data.get("role"),
                score_data.get("name"),
                score_data.get("cusum_path"),
                score_data.get("multipliers_applied"),
                score_data.get("score_components"),
                score_data.get("severity"),
                score_data.get("explanation_text"),
                score_data.get("last_updated") or datetime.utcnow().isoformat()
            ))
            
            conn.commit()
    
    def get_risk_score(self, user_id: str, date: Optional[str] = None) -> Optional[Dict[str, Any]]:
        """Get a risk score by user_id and optionally date."""
        with sqlite3.connect(self.db_path) as conn:
            conn.row_factory = sqlite3.Row
            cursor = conn.cursor()
            
            if date:
                cursor.execute("""
                    SELECT * FROM risk_scores WHERE user_id = ? AND date = ?
                """, (user_id, date))
            else:
                cursor.execute("""
                    SELECT * FROM risk_scores WHERE user_id = ?
                    ORDER BY date DESC LIMIT 1
                """, (user_id,))
            
            row = cursor.fetchone()
            if row:
                return self._row_to_dict(row)
            return None
    
    def get_all_risk_scores(self, limit: int = 100, offset: int = 0) -> List[Dict[str, Any]]:
        """Get all risk scores with pagination."""
        with sqlite3.connect(self.db_path) as conn:
            conn.row_factory = sqlite3.Row
            cursor = conn.cursor()
            
            cursor.execute("""
                SELECT * FROM risk_scores
                ORDER BY risk_score DESC
                LIMIT ? OFFSET ?
            """, (limit, offset))
            
            rows = cursor.fetchall()
            return [self._row_to_dict(row) for row in rows]
    
    def record_feedback(
        self,
        user_id: str,
        is_false_positive: bool,
        reason: Optional[str] = None
    ) -> Dict[str, Any]:
        """Record feedback and update down-weight statistics."""
        with sqlite3.connect(self.db_path) as conn:
            cursor = conn.cursor()
            now = datetime.utcnow().isoformat()
            feedback_date = datetime.utcnow().strftime("%Y-%m-%d")
            
            # Insert feedback record
            cursor.execute("""
                INSERT INTO feedback (user_id, is_false_positive, reason, created_at)
                VALUES (?, ?, ?, ?)
            """, (user_id, 1 if is_false_positive else 0, reason, now))
            
            feedback_id = cursor.lastrowid
            
            # Update feedback stats
            cursor.execute("""
                INSERT INTO feedback_stats (user_id, feedback_date, false_positive_count, 
                    total_feedback, down_weight, last_updated)
                VALUES (?, ?, 0, 1, 1.0, ?)
                ON CONFLICT(user_id, feedback_date) DO UPDATE SET
                    total_feedback = total_feedback + 1,
                    false_positive_count = false_positive_count + ?,
                    last_updated = ?
            """, (user_id, feedback_date, now, 1 if is_false_positive else 0, now))
            
            # Update down_weight based on false positive ratio
            cursor.execute("""
                UPDATE feedback_stats SET down_weight = 
                    CASE WHEN total_feedback > 0 
                    THEN 1.0 - (false_positive_count * 0.1)
                    ELSE 1.0 END
                WHERE user_id = ? AND feedback_date = ?
            """, (user_id, feedback_date))
            
            conn.commit()
            
            # Get updated down_weight
            cursor.execute("""
                SELECT down_weight FROM feedback_stats 
                WHERE user_id = ? AND feedback_date = ?
            """, (user_id, feedback_date))
            
            row = cursor.fetchone()
            down_weight = row[0] if row else 1.0
            
            return {
                "feedback_id": feedback_id,
                "down_weight": down_weight,
                "timestamp": now
            }
    
    def get_feedback_down_weight(self, user_id: str, date: str) -> float:
        """Get the down-weight factor for a user's feedback."""
        with sqlite3.connect(self.db_path) as conn:
            cursor = conn.cursor()
            feedback_date = date.split("T")[0]  # Extract date part
            
            cursor.execute("""
                SELECT down_weight FROM feedback_stats 
                WHERE user_id = ? AND feedback_date <= ?
                ORDER BY feedback_date DESC LIMIT 1
            """, (user_id, feedback_date))
            
            row = cursor.fetchone()
            return row[0] if row else 1.0
    
    def _row_to_dict(self, row: sqlite3.Row) -> Dict[str, Any]:
        """Convert sqlite3.Row to dictionary with JSON deserialization."""
        result = dict(row)
        
        # Deserialize JSON fields
        json_fields = ["cusum_path", "multipliers_applied", "score_components"]
        for field in json_fields:
            if field in result and result[field]:
                try:
                    result[field] = json.loads(result[field])
                except (json.JSONDecodeError, TypeError):
                    pass
        
        # Convert integers to booleans
        if "fallback_applied" in result:
            result["fallback_applied"] = bool(result["fallback_applied"])
        
        if "is_false_positive" in result:
            result["is_false_positive"] = bool(result["is_false_positive"])
        
        return result
    
    def close(self):
        """Close database connection."""
        # Connection is closed automatically by context manager
        pass

