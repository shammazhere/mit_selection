"""
Generate Sample Contract A Data

Creates a CSV file matching the daily_user_scores schema for testing.
"""

import csv
import random
from datetime import datetime, timedelta
import os

# Ensure data directory exists
os.makedirs("data", exist_ok=True)

# Sample users with different characteristics
USERS = [
    {"user_id": "u001", "name": "Alice Chen", "role": "Senior Engineer", "department": "Engineering"},
    {"user_id": "u002", "name": "Bob Smith", "role": "IT Administrator", "department": "IT"},
    {"user_id": "u003", "name": "Carol Johnson", "role": "Financial Analyst", "department": "Finance"},
    {"user_id": "u004", "name": "David Williams", "role": "HR Manager", "department": "HR"},
    {"user_id": "u005", "name": "Eve Davis", "role": "System Administrator", "department": "IT"},
    {"user_id": "u006", "name": "Frank Miller", "role": "Software Developer", "department": "Engineering"},
    {"user_id": "u007", "name": "Grace Lee", "role": "Project Lead", "department": "Engineering"},
    {"user_id": "u008", "name": "Henry Wilson", "role": "Data Scientist", "department": "Engineering"},
    {"user_id": "u009", "name": "Ivy Taylor", "role": "Marketing Manager", "department": "Marketing"},
    {"user_id": "u010", "name": "Jack Brown", "role": "Network Engineer", "department": "IT"}
]

def generate_sample_scores():
    """Generate sample scores for demonstration."""
    random.seed(42)  # Reproducible results
    
    today = datetime.now()
    scores = []
    
    # Generate scores for each user over 10 days
    for user in USERS:
        base_self_score = random.uniform(0.3, 0.7)
        base_peer_score = random.uniform(0.3, 0.7)
        
        # Simulate some users having higher scores (anomalies)
        if user["user_id"] in ["u002", "u005"]:  # Admins - higher self scores
            base_self_score = random.uniform(0.6, 0.9)
        
        if user["user_id"] in ["u003", "u009"]:  # Finance/Marketing - potential anomalies
            base_peer_score = random.uniform(0.6, 0.85)
        
        for day_offset in range(10):
            date = (today - timedelta(days=9 - day_offset)).strftime("%Y-%m-%d")
            
            # Add some drift over time for certain users
            drift_factor = 0
            if user["user_id"] in ["u002", "u005"] and day_offset > 5:
                drift_factor = (day_offset - 5) * 0.05  # Gradual increase
            
            # Add some randomness
            self_score = min(1.0, max(0.0, base_self_score + random.uniform(-0.05, 0.05) + drift_factor))
            peer_score = min(1.0, max(0.0, base_peer_score + random.uniform(-0.05, 0.05)))
            
            # Determine cohort
            cohort_used = "role" if day_offset < 3 else "department"  # Some fallbacks
            cohort_size = random.randint(3, 15) if cohort_used == "department" else random.randint(2, 8)
            
            # Small cohort triggers fallback
            fallback_applied = cohort_size < 4
            
            scores.append({
                "user_id": user["user_id"],
                "date": date,
                "self_score": round(self_score, 4),
                "peer_score": round(peer_score, 4),
                "cohort_used": cohort_used,
                "cohort_size": cohort_size,
                "fallback_applied": fallback_applied,
                "role": user["role"]
            })
    
    return scores


def write_scores_to_csv(scores, filename="data/daily_user_scores.csv"):
    """Write scores to CSV file."""
    fieldnames = [
        "user_id", "date", "self_score", "peer_score",
        "cohort_used", "cohort_size", "fallback_applied", "role"
    ]
    
    with open(filename, "w", newline="") as f:
        writer = csv.DictWriter(f, fieldnames=fieldnames)
        writer.writeheader()
        writer.writerows(scores)
    
    print(f"Generated {len(scores)} score records to {filename}")
    return filename


def write_scores_to_sqlite(scores, db_path="data/scores.db"):
    """Write scores to SQLite database."""
    import sqlite3
    
    conn = sqlite3.connect(db_path)
    cursor = conn.cursor()
    
    # Create table
    cursor.execute("""
        CREATE TABLE IF NOT EXISTS daily_user_scores (
            user_id TEXT NOT NULL,
            date TEXT NOT NULL,
            self_score REAL NOT NULL,
            peer_score REAL NOT NULL,
            cohort_used TEXT,
            cohort_size INTEGER,
            fallback_applied INTEGER NOT NULL,
            role TEXT,
            PRIMARY KEY (user_id, date)
        )
    """)
    
    # Insert scores
    for score in scores:
        cursor.execute("""
            INSERT OR REPLACE INTO daily_user_scores 
            (user_id, date, self_score, peer_score, cohort_used, cohort_size, fallback_applied, role)
            VALUES (?, ?, ?, ?, ?, ?, ?, ?)
        """, (
            score["user_id"],
            score["date"],
            score["self_score"],
            score["peer_score"],
            score["cohort_used"],
            score["cohort_size"],
            1 if score["fallback_applied"] else 0,
            score["role"]
        ))
    
    conn.commit()
    conn.close()
    
    print(f"Generated {len(scores)} score records to {db_path}")
    return db_path


if __name__ == "__main__":
    print("Generating sample Contract A data...")
    
    scores = generate_sample_scores()
    
    # Write to both CSV and SQLite
    csv_file = write_scores_to_csv(scores)
    sqlite_db = write_scores_to_sqlite(scores)
    
    print("\nSample records:")
    for i, score in enumerate(scores[:5]):
        print(f"  {i+1}. {score}")
    
    print(f"\nTotal records: {len(scores)}")
    print(f"\nFiles created:")
    print(f"  CSV: {csv_file}")
    print(f"  SQLite: {sqlite_db}")
