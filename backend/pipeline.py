"""
Person 3 Pipeline

End-to-end processing pipeline:
1. Load Contract A data (daily_user_scores published by Person 2)
2. Compute pre-multiplier fused scores (LOCKED for CUSUM)
3. Run CUSUM drift detection
4. Apply risk fusion with all 4 multipliers (role, time, data, decay) + feedback down-weighting
5. Generate explanations disclosing small-cohort fallback
6. Store results with forensic timeline into SQLite database
"""

import sys
import os
from datetime import datetime, timedelta
from typing import List, Dict, Any, Optional
from pathlib import Path
import csv

# Add backend directory to path
BASE_DIR = Path(__file__).resolve().parent
REPO_ROOT = BASE_DIR.parent
sys.path.insert(0, str(BASE_DIR))

from drift.cusum import compute_cusum_for_user, default_detector
from fusion.fusion import default_fusion_engine, FusionResult, MultiplierConfig
from explain.generator import default_explanation_generator
from api.database import Database


def _format_date(raw_date: str) -> str:
    """Standardize CERT timestamp format."""
    try:
        dt = datetime.strptime(raw_date, "%m/%d/%Y %H:%M:%S")
        return dt.strftime("%Y-%m-%dT%H:%M:%S")
    except Exception:
        return raw_date


def load_ldap_names(cert_dir: Path) -> Dict[str, str]:
    """Load employee names from LDAP csv if available."""
    names: Dict[str, str] = {}
    ldap_path = cert_dir / "ldap.csv"
    if not ldap_path.exists():
        return names
    try:
        with open(ldap_path, mode="r", encoding="utf-8") as f:
            reader = csv.DictReader(f)
            for row in reader:
                uid = row.get("user_id") or row.get("user")
                name = row.get("employee_name") or row.get("name")
                if uid and name:
                    names[str(uid).strip()] = name.strip()
    except Exception as e:
        print(f"Notice: could not load LDAP names: {e}")
    return names


def extract_cert_events(cert_dir: Path, user_id: str) -> List[Dict[str, Any]]:
    """Extract concrete security events for a specific user from CERT log files."""
    if not cert_dir.exists():
        return []
    
    events = []
    try:
        # 1. Device logs (USB connects)
        dev_file = cert_dir / "device.csv"
        if dev_file.exists():
            with open(dev_file, mode="r", encoding="utf-8") as f:
                for row in csv.DictReader(f):
                    if (row.get("user") or row.get("user_id")) == user_id:
                        ts = _format_date(row.get("date", ""))
                        events.append({
                            "timestamp": ts,
                            "event": f"USB storage device connected ({row.get('pc', 'PC')}, drive {row.get('file_tree', 'R:')})",
                            "category": "device"
                        })

        # 2. File logs (removable media copy)
        file_file = cert_dir / "file.csv"
        if file_file.exists():
            with open(file_file, mode="r", encoding="utf-8") as f:
                for row in csv.DictReader(f):
                    if (row.get("user") or row.get("user_id")) == user_id:
                        is_rem = str(row.get("to_removable_media", "")).lower() in {"true", "1", "yes"}
                        if is_rem:
                            ts = _format_date(row.get("date", ""))
                            events.append({
                                "timestamp": ts,
                                "event": f"Copied file to removable media: {row.get('filename', 'document')}",
                                "category": "file"
                            })

        # 3. HTTP logs (cloud uploads)
        http_file = cert_dir / "http.csv"
        if http_file.exists():
            with open(http_file, mode="r", encoding="utf-8") as f:
                for row in csv.DictReader(f):
                    if (row.get("user") or row.get("user_id")) == user_id:
                        act = str(row.get("activity", "")).lower()
                        url = str(row.get("url", "")).lower()
                        if "upload" in act or any(c in url for c in ["dropbox", "wetransfer", "drive.google"]):
                            ts = _format_date(row.get("date", ""))
                            events.append({
                                "timestamp": ts,
                                "event": f"Web file upload to {row.get('url')}",
                                "category": "http"
                            })

        # 4. Email logs (external email)
        email_file = cert_dir / "email.csv"
        if email_file.exists():
            with open(email_file, mode="r", encoding="utf-8") as f:
                for row in csv.DictReader(f):
                    if (row.get("user") or row.get("user_id")) == user_id:
                        to = row.get("to", "")
                        if "@gmail.com" in to or "external" in to:
                            ts = _format_date(row.get("date", ""))
                            sz = int(float(row.get("size", 0))) // 1024
                            events.append({
                                "timestamp": ts,
                                "event": f"External email sent to {to} ({sz} KB)",
                                "category": "email"
                            })

        # 5. Logon logs (after-hours logon)
        logon_file = cert_dir / "logon.csv"
        if logon_file.exists():
            with open(logon_file, mode="r", encoding="utf-8") as f:
                for row in csv.DictReader(f):
                    if (row.get("user") or row.get("user_id")) == user_id:
                        d_str = row.get("date", "")
                        try:
                            hour = datetime.strptime(d_str, "%m/%d/%Y %H:%M:%S").hour
                            if (hour < 7 or hour >= 20) and "logon" in str(row.get("activity", "")).lower():
                                ts = _format_date(d_str)
                                events.append({
                                    "timestamp": ts,
                                    "event": f"After-hours logon detected at {hour:02d}:00",
                                    "category": "logon"
                                })
                        except Exception:
                            pass
    except Exception as e:
        print(f"Notice: reading CERT events for {user_id}: {e}")

    events.sort(key=lambda x: x["timestamp"])
    return events


class Person3Pipeline:
    """
    Person 3 processing pipeline.
    
    Steps:
    1. Load daily_user_scores from Person 2's Contract A CSV
    2. Compute pre-multiplier fused score (LOCKED for CUSUM)
    3. Run CUSUM drift detection on locked score
    4. Apply risk fusion with all multipliers and feedback down-weighting
    5. Generate explanations (disclosing small-cohort fallback per Section 7.2)
    6. Store results and forensic timeline into SQLite database
    """
    
    def __init__(
        self,
        db: Database,
        csv_path: Optional[str] = None,
        cert_dir: Optional[str] = None
    ):
        self.db = db
        # Locate Contract A CSV
        candidates = [
            csv_path,
            str(REPO_ROOT / "backend" / "output" / "daily_user_scores.csv"),
            str(BASE_DIR / "output" / "daily_user_scores.csv"),
            str(BASE_DIR / "data" / "daily_user_scores.csv"),
            "data/daily_user_scores.csv"
        ]
        self.csv_path = next((c for c in candidates if c and os.path.exists(c)), str(REPO_ROOT / "backend" / "output" / "daily_user_scores.csv"))
        
        # Locate CERT directory
        cert_candidates = [
            cert_dir,
            str(REPO_ROOT / "backend" / "data" / "sample_cert"),
            str(BASE_DIR / "data" / "sample_cert")
        ]
        self.cert_dir = Path(next((c for c in cert_candidates if c and os.path.exists(c)), str(BASE_DIR / "data" / "sample_cert")))
        
        self.fusion_engine = default_fusion_engine
        self.cusum_detector = default_detector
        self.explanation_generator = default_explanation_generator
        self.multiplier_config = MultiplierConfig()
        self.ldap_names = load_ldap_names(self.cert_dir)
    
    def load_contract_a_data(self) -> List[Dict[str, Any]]:
        """Load Contract A data from CSV."""
        scores = []
        if not os.path.exists(self.csv_path):
            print(f"Contract A CSV file not found at: {self.csv_path}")
            return scores
        
        with open(self.csv_path, "r", encoding="utf-8") as f:
            reader = csv.DictReader(f)
            for row in reader:
                scores.append({
                    "user_id": row["user_id"],
                    "date": row["date"],
                    "self_score": float(row["self_score"]),
                    "peer_score": float(row["peer_score"]),
                    "cohort_used": row["cohort_used"],
                    "cohort_size": int(float(row["cohort_size"])),
                    "fallback_applied": str(row["fallback_applied"]).strip().lower() in {"1", "true", "yes"},
                    "role": row.get("role", "Unknown"),
                    "team": row.get("team", ""),
                    "manager_id": row.get("manager_id", "")
                })
        
        print(f"Loaded {len(scores)} records from {self.csv_path}")
        return scores
    
    def group_by_user(self, scores: List[Dict[str, Any]]) -> Dict[str, List[Dict[str, Any]]]:
        """Group scores by user_id and sort chronologically."""
        user_scores = {}
        for score in scores:
            user_id = score["user_id"]
            if user_id not in user_scores:
                user_scores[user_id] = []
            user_scores[user_id].append(score)
        
        for user_id in user_scores:
            user_scores[user_id].sort(key=lambda x: x["date"])
        
        return user_scores
    
    def build_event_timeline(self, user_id: str, days: List[Dict[str, Any]], forensic_events: List[Dict[str, Any]]) -> List[Dict[str, Any]]:
        """Assemble signal elevations and forensic events into the Case timeline."""
        timeline = []
        for day in days:
            pre = self.fusion_engine.compute_pre_multiplier_score(day["self_score"], day["peer_score"])
            if day["self_score"] >= 0.50:
                timeline.append({
                    "timestamp": f"{day['date']}T09:00:00",
                    "event": f"Self-baseline elevated ({day['self_score']:.2f})",
                    "category": "signal"
                })
            if day["peer_score"] >= 0.50:
                timeline.append({
                    "timestamp": f"{day['date']}T12:00:00",
                    "event": f"Peer-cohort deviation elevated ({day['peer_score']:.2f})",
                    "category": "signal"
                })
            if day["fallback_applied"]:
                timeline.append({
                    "timestamp": f"{day['date']}T08:00:00",
                    "event": f"Department-level cohort fallback applied (role cohort had {day['cohort_size']} members)",
                    "category": "fallback"
                })
            if pre >= 0.50:
                timeline.append({
                    "timestamp": f"{day['date']}T17:30:00",
                    "event": f"Combined self+peer pre-multiplier score reached {pre:.2f}",
                    "category": "signal"
                })
        
        # Combine with physical CERT events
        combined = sorted(timeline + forensic_events, key=lambda e: e["timestamp"])
        return [{"timestamp": e["timestamp"], "event": e["event"]} for e in combined[-32:]]
    
    def process_user(
        self,
        user_id: str,
        user_score_records: List[Dict[str, Any]]
    ) -> Optional[Dict[str, Any]]:
        """Process a single user's scores through CUSUM, fusion, and explanation."""
        if not user_score_records:
            return None
        
        latest = user_score_records[-1]
        
        # Step 1: Pre-multiplier fused score (LOCKED for CUSUM)
        pre_multiplier_score = self.fusion_engine.compute_pre_multiplier_score(
            latest["self_score"],
            latest["peer_score"]
        )
        
        # Step 2: Run CUSUM on all historical daily pre-multiplier scores
        all_pre_scores = [
            self.fusion_engine.compute_pre_multiplier_score(s["self_score"], s["peer_score"])
            for s in user_score_records
        ]
        cusum_result = self.cusum_detector.process_user(user_id, all_pre_scores)
        drift_score = cusum_result.drift_score
        
        # Step 3: Extract forensic events from CERT
        forensic_events = extract_cert_events(self.cert_dir, user_id)
        
        # Dynamic context flags for multipliers
        data_flags = []
        has_removable = any("removable media" in e["event"].lower() or "usb" in e["event"].lower() for e in forensic_events)
        if has_removable:
            data_flags.append("removable_media")
        
        has_upload = any("upload" in e["event"].lower() or "external email" in e["event"].lower() for e in forensic_events)
        if has_upload:
            data_flags.append("cloud_upload")
        
        # Check for after-hours logon activity
        has_after_hours = any("after-hours" in e["event"].lower() for e in forensic_events)
        if has_after_hours:
            timestamp = datetime.fromisoformat(f"{latest['date']}T22:30:00")
        else:
            timestamp = datetime.fromisoformat(f"{latest['date']}T10:00:00")
        
        # Feedback down-weight
        down_weight = self.db.get_feedback_down_weight(user_id, latest["date"])
        
        # Compute risk score with all 4 multipliers + feedback down-weight
        role = latest["role"]
        fusion_result = self.fusion_engine.compute_risk_score(
            self_score=latest["self_score"],
            peer_score=latest["peer_score"],
            drift_score=drift_score,
            role=role,
            timestamp=timestamp,
            data_flags=data_flags,
            days_since_last_anomaly=0,
            fallback_applied=latest["fallback_applied"],
            feedback_down_weight=down_weight
        )
        
        # Step 4: Count consecutive drift days
        consecutive_drift = 0
        for val in reversed(cusum_result.raw_path):
            if val >= self.cusum_detector.threshold:
                consecutive_drift += 1
            else:
                break
        
        # Step 5: Generate explanation
        explanation_result = self.explanation_generator.generate_explanation(
            self_score=latest["self_score"],
            peer_score=latest["peer_score"],
            drift_score=drift_score,
            cohort_used=latest["cohort_used"],
            cohort_size=latest["cohort_size"],
            fallback_applied=latest["fallback_applied"],
            days_of_drift=consecutive_drift if consecutive_drift > 0 else None,
            max_drift_path_value=cusum_result.max_cumsum,
            role=role
        )
        
        # Step 6: Build full forensic timeline
        event_timeline = self.build_event_timeline(user_id, user_score_records, forensic_events)
        
        # Step 7: Resolve employee name
        display_name = self.ldap_names.get(user_id, f"User {user_id}")
        
        # Severity calculation
        risk = fusion_result.risk_score
        severity = self._assess_severity(risk)
        
        return {
            "user_id": user_id,
            "date": latest["date"],
            "name": display_name,
            "role": role,
            "team": latest.get("team", ""),
            "self_score": latest["self_score"],
            "peer_score": latest["peer_score"],
            "drift_score": drift_score,
            "pre_multiplier_score": pre_multiplier_score,
            "raw_fusion_score": fusion_result.raw_fusion_score,
            "adjusted_fusion_score": fusion_result.adjusted_fusion_score,
            "risk_score": risk,
            "cohort_used": latest["cohort_used"],
            "cohort_size": latest["cohort_size"],
            "fallback_applied": latest["fallback_applied"],
            "explanation_text": explanation_result.explanation_text,
            "cusum_path": cusum_result.raw_path,
            "multipliers_applied": fusion_result.multipliers_applied,
            "score_components": fusion_result.score_components,
            "severity": severity,
            "event_timeline": event_timeline,
            "is_false_positive": down_weight < 1.0,
            "feedback_reason": "",
            "last_updated": datetime.utcnow().isoformat()
        }
    
    def _assess_severity(self, risk_score: float) -> str:
        """Assess severity level based on risk score."""
        if risk_score >= 80:
            return "critical"
        elif risk_score >= 65:
            return "high"
        elif risk_score >= 50:
            return "medium"
        else:
            return "low"
    
    def run(self, limit: Optional[int] = None) -> List[Dict[str, Any]]:
        """Run the full pipeline."""
        scores = self.load_contract_a_data()
        if not scores:
            print("No Contract A scores to process")
            return []
        
        user_scores = self.group_by_user(scores)
        results = []
        for i, (user_id, user_records) in enumerate(user_scores.items()):
            if limit and i >= limit:
                break
            
            result = self.process_user(user_id, user_records)
            if result:
                results.append(result)
                self.db.upsert_risk_score(result)
        
        print(f"Pipeline processed {len(results)} users into {self.db.db_path}")
        return results


def main():
    """Run Person 3 pipeline."""
    print("=" * 60)
    print("Person 3 Pipeline — Fusion, Drift & API Engine")
    print("=" * 60)
    
    db_path = os.environ.get("SILENT_SHIFT_DB", str(BASE_DIR / "data" / "scores.db"))
    db = Database(db_path)
    pipeline = Person3Pipeline(db=db)
    results = pipeline.run()
    
    if results:
        results.sort(key=lambda x: x["risk_score"], reverse=True)
        print("\nTop Ranked Alerts:")
        for i, r in enumerate(results[:6]):
            print(f"{i+1}. {r['name']} ({r['user_id']}) — {r['role']}")
            print(f"   Risk: {r['risk_score']} [{r['severity'].upper()}] | Self: {r['self_score']:.2f}, Peer: {r['peer_score']:.2f}, Drift: {r['drift_score']:.2f}")
            print(f"   Fallback: {'Department (Disclosed)' if r['fallback_applied'] else 'Role'}")
            print(f"   Explanation: {r['explanation_text']}")
            print()
    print("Pipeline run complete.")


if __name__ == "__main__":
    main()
