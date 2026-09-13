"""
Person 3 Pipeline

End-to-end processing pipeline:
1. Load Contract A data (daily_user_scores)
2. Compute pre-multiplier fused scores
3. Run CUSUM drift detection
4. Apply risk fusion with multipliers
5. Generate explanations
6. Store results in database
"""

import sys
import os
from datetime import datetime, timedelta
from typing import List, Dict, Any, Optional
import csv

# Add backend directory to path
sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))

from drift.cusum import compute_cusum_for_user, default_detector
from fusion.fusion import default_fusion_engine, FusionResult
from fusion.fusion import MultiplierConfig
from explain.generator import default_explanation_generator
from api.database import Database


class Person3Pipeline:
    """
    Person 3 processing pipeline.
    
    Steps:
    1. Load daily_user_scores from CSV/SQLite
    2. Compute pre-multiplier fused score (LOCKED for CUSUM)
    3. Run CUSUM drift detection on locked score
    4. Apply risk fusion with all multipliers
    5. Generate explanations
    6. Store results in database
    """
    
    def __init__(self, db: Database, csv_path: Optional[str] = None):
        """
        Initialize pipeline.
        
        Args:
            db: Database instance for persistence
            csv_path: Path to daily_user_scores CSV file
        """
        self.db = db
        self.csv_path = csv_path or "data/daily_user_scores.csv"
        self.fusion_engine = default_fusion_engine
        self.cusum_detector = default_detector
        self.explanation_generator = default_explanation_generator
        self.multiplier_config = MultiplierConfig()
    
    def load_contract_a_data(self) -> List[Dict[str, Any]]:
        """Load Contract A data from CSV."""
        scores = []
        
        if not os.path.exists(self.csv_path):
            print(f"CSV file not found: {self.csv_path}")
            return scores
        
        with open(self.csv_path, "r") as f:
            reader = csv.DictReader(f)
            for row in reader:
                scores.append({
                    "user_id": row["user_id"],
                    "date": row["date"],
                    "self_score": float(row["self_score"]),
                    "peer_score": float(row["peer_score"]),
                    "cohort_used": row["cohort_used"],
                    "cohort_size": int(row["cohort_size"]),
                    "fallback_applied": row["fallback_applied"].lower() == "true",
                    "role": row["role"]
                })
        
        print(f"Loaded {len(scores)} records from {self.csv_path}")
        return scores
    
    def group_by_user(self, scores: List[Dict[str, Any]]) -> Dict[str, List[Dict[str, Any]]]:
        """Group scores by user_id."""
        user_scores = {}
        for score in scores:
            user_id = score["user_id"]
            if user_id not in user_scores:
                user_scores[user_id] = []
            user_scores[user_id].append(score)
        
        # Sort by date
        for user_id in user_scores:
            user_scores[user_id].sort(key=lambda x: x["date"])
        
        return user_scores
    
    def process_user(
        self,
        user_id: str,
        user_score_records: List[Dict[str, Any]]
    ) -> Optional[Dict[str, Any]]:
        """
        Process a single user's scores through the pipeline.
        
        Args:
            user_id: User identifier
            user_score_records: List of daily scores for this user
            
        Returns:
            Processed result with all scores and metadata
        """
        if not user_score_records:
            return None
        
        # Get latest record for this user
        latest = user_score_records[-1]
        
        # Step 1: Compute pre-multiplier fused score (LOCKED for CUSUM)
        pre_multiplier_score = self.fusion_engine.compute_pre_multiplier_score(
            latest["self_score"],
            latest["peer_score"]
        )
        
        # Step 2: Run CUSUM on all daily pre-multiplier scores
        all_pre_scores = [
            self.fusion_engine.compute_pre_multiplier_score(
                s["self_score"],
                s["peer_score"]
            )
            for s in user_score_records
        ]
        
        cusum_result = self.cusum_detector.process_user(user_id, all_pre_scores)
        
        # Get drift score (0-1)
        drift_score = cusum_result.drift_score
        
        # Step 3: Apply risk fusion with multipliers
        # Determine timestamp for time multiplier
        timestamp = datetime.fromisoformat(latest["date"] + "T10:00:00")  # Default to 10am
        
        # Check for admin/privileged role
        role = latest["role"]
        data_flags = [] if "data_flags" not in latest else latest["data_flags"]
        
        fusion_result = self.fusion_engine.compute_risk_score(
            self_score=latest["self_score"],
            peer_score=latest["peer_score"],
            drift_score=drift_score,
            role=role,
            timestamp=timestamp,
            data_flags=data_flags,
            days_since_last_anomaly=0,  # Would be computed from feedback
            fallback_applied=latest["fallback_applied"]
        )
        
        # Step 4: Generate explanation
        explanation_result = self.explanation_generator.generate_explanation(
            self_score=latest["self_score"],
            peer_score=latest["peer_score"],
            drift_score=drift_score,
            cohort_used=latest["cohort_used"],
            cohort_size=latest["cohort_size"],
            fallback_applied=latest["fallback_applied"],
            days_of_drift=cusum_result.days_to_detection if cusum_result.drift_detected else None,
            max_drift_path_value=cusum_result.max_cumsum,
            role=role
        )
        
        # Step 5: Build final result
        result = {
            "user_id": user_id,
            "date": latest["date"],
            "name": latest.get("name", f"User {user_id}"),
            "role": role,
            "self_score": latest["self_score"],
            "peer_score": latest["peer_score"],
            "drift_score": drift_score,
            "pre_multiplier_score": pre_multiplier_score,
            "raw_fusion_score": fusion_result.raw_fusion_score,
            "adjusted_fusion_score": fusion_result.adjusted_fusion_score,
            "risk_score": fusion_result.risk_score,
            "cohort_used": latest["cohort_used"],
            "cohort_size": latest["cohort_size"],
            "fallback_applied": latest["fallback_applied"],
            "explanation_text": explanation_result.explanation_text,
            "cusum_path": cusum_result.raw_path,
            "multipliers_applied": fusion_result.multipliers_applied,
            "score_components": fusion_result.score_components,
            "severity": self._assess_severity(fusion_result.risk_score),
            "last_updated": datetime.utcnow().isoformat()
        }
        
        return result
    
    def _assess_severity(self, risk_score: float) -> str:
        """Assess severity level based on risk score."""
        if risk_score >= 80:
            return "critical"
        elif risk_score >= 60:
            return "high"
        elif risk_score >= 40:
            return "medium"
        else:
            return "low"
    
    def run(self, limit: Optional[int] = None) -> List[Dict[str, Any]]:
        """
        Run the full pipeline.
        
        Args:
            limit: Optional limit on number of users to process
            
        Returns:
            List of processed results
        """
        # Step 1: Load data
        scores = self.load_contract_a_data()
        if not scores:
            print("No scores to process")
            return []
        
        # Step 2: Group by user
        user_scores = self.group_by_user(scores)
        
        # Step 3: Process each user
        results = []
        for i, (user_id, user_records) in enumerate(user_scores.items()):
            if limit and i >= limit:
                break
            
            result = self.process_user(user_id, user_records)
            if result:
                results.append(result)
                
                # Store in database
                self.db.upsert_risk_score(result)
        
        print(f"Processed {len(results)} users")
        return results


def main():
    """Main entry point."""
    print("=" * 60)
    print("Person 3 Pipeline - Fusion, Drift & API")
    print("=" * 60)
    
    # Initialize database
    db = Database("data/scores.db")
    
    # Initialize pipeline
    pipeline = Person3Pipeline(db=db)
    
    # Run pipeline
    results = pipeline.run(limit=10)  # Process up to 10 users
    
    # Print summary
    print("\n" + "=" * 60)
    print("Pipeline Complete - Summary")
    print("=" * 60)
    
    if results:
        # Sort by risk score descending
        results.sort(key=lambda x: x["risk_score"], reverse=True)
        
        print(f"\nTop 5 highest risk users:")
        for i, result in enumerate(results[:5]):
            print(f"{i+1}. {result['name']} ({result['user_id']})")
            print(f"   Role: {result['role']}")
            print(f"   Risk Score: {result['risk_score']:.1f}")
            print(f"   Self: {result['self_score']:.2f}, Peer: {result['peer_score']:.2f}, Drift: {result['drift_score']:.2f}")
            print(f"   Severity: {result['severity'].upper()}")
            print(f"   Explanation: {result['explanation_text'][:100]}...")
            print()
        
        print(f"\nTotal users processed: {len(results)}")
        print(f"Database: data/scores.db")
    else:
        print("No results to display")
        print("Run the sample data generator first:")
        print("  python backend/generate_sample_data.py")


if __name__ == "__main__":
    main()
