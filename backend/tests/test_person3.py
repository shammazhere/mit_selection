from __future__ import annotations

import unittest
import tempfile
from pathlib import Path
from datetime import datetime

from backend.drift.cusum import CUSUMDetector, compute_cusum_for_user
from backend.fusion.fusion import RiskFusionEngine, MultiplierConfig
from backend.explain.generator import ExplanationGenerator
from backend.api.database import Database
from backend.api.main import app
from fastapi.testclient import TestClient


class Person3Tests(unittest.TestCase):
    def setUp(self):
        self.tmp = tempfile.TemporaryDirectory()
        self.db_path = str(Path(self.tmp.name) / "test_scores.db")
        self.db = Database(self.db_path)

    def tearDown(self):
        self.tmp.cleanup()

    def test_cusum_accumulates_on_sustained_drift(self):
        detector = CUSUMDetector(threshold=0.25, slack=0.08, mean_est=0.35)
        
        # In-control normal baseline (scores ~0.2)
        normal_scores = [0.20, 0.22, 0.19, 0.25, 0.21, 0.24]
        normal_res = detector.process_user("normal_user", normal_scores)
        self.assertFalse(normal_res.drift_detected)
        self.assertEqual(normal_res.max_cumsum, 0.0)
        self.assertEqual(normal_res.drift_score, 0.0)

        # Drifting sequence (consistently elevated scores ~0.7-0.9)
        drifting_scores = [0.20, 0.22, 0.65, 0.75, 0.85, 0.90, 0.95]
        drift_res = detector.process_user("drifting_user", drifting_scores)
        self.assertTrue(drift_res.drift_detected)
        self.assertGreater(drift_res.max_cumsum, 0.25)
        self.assertGreater(drift_res.drift_score, 0.50)
        self.assertEqual(len(drift_res.raw_path), len(drifting_scores))

    def test_risk_fusion_pre_multiplier_locked(self):
        engine = RiskFusionEngine(self_weight=0.35, peer_weight=0.35, drift_weight=0.30)
        pre1 = engine.compute_pre_multiplier_score(0.8, 0.6)
        self.assertAlmostEqual(pre1, 0.70, places=3)

    def test_risk_fusion_multipliers_and_feedback(self):
        engine = RiskFusionEngine()
        
        # Standard score
        res_standard = engine.compute_risk_score(
            self_score=0.6, peer_score=0.6, drift_score=0.5,
            role="Accountant", timestamp=datetime(2026, 9, 13, 10, 0),
            data_flags=[], days_since_last_anomaly=0, feedback_down_weight=1.0
        )
        
        # Privileged admin after-hours with removable media
        res_privileged = engine.compute_risk_score(
            self_score=0.6, peer_score=0.6, drift_score=0.5,
            role="System Administrator", timestamp=datetime(2026, 9, 13, 22, 0),
            data_flags=["removable_media"], days_since_last_anomaly=0, feedback_down_weight=1.0
        )
        self.assertGreater(res_privileged.risk_score, res_standard.risk_score)
        
        # Feedback down-weighted (0.4x)
        res_feedback = engine.compute_risk_score(
            self_score=0.6, peer_score=0.6, drift_score=0.5,
            role="Accountant", timestamp=datetime(2026, 9, 13, 10, 0),
            data_flags=[], days_since_last_anomaly=0, feedback_down_weight=0.4
        )
        self.assertLess(res_feedback.risk_score, res_standard.risk_score)

    def test_explanation_discloses_fallback(self):
        generator = ExplanationGenerator()
        res = generator.generate_explanation(
            self_score=0.85,
            peer_score=0.80,
            drift_score=0.75,
            cohort_used="department",
            cohort_size=3,
            fallback_applied=True,
            days_of_drift=5,
            role="Financial Controller"
        )
        self.assertTrue(res.fallback_disclosed)
        self.assertIn("fell back to department-level comparison", res.explanation_text)
        self.assertIn("3 members", res.explanation_text)

    def test_database_feedback_recalibration(self):
        # Insert initial alert
        self.db.upsert_risk_score({
            "user_id": "C999",
            "date": "2026-09-13",
            "self_score": 0.85,
            "peer_score": 0.80,
            "drift_score": 0.70,
            "pre_multiplier_score": 0.825,
            "raw_fusion_score": 0.78,
            "adjusted_fusion_score": 0.90,
            "risk_score": 90.0,
            "cohort_used": "role",
            "cohort_size": 10,
            "fallback_applied": False,
            "role": "Engineer",
            "name": "Test User",
            "severity": "critical",
            "explanation_text": "High alert test explanation",
            "cusum_path": [0.1, 0.3, 0.5],
            "multipliers_applied": {"role": 1.0},
            "score_components": {"self": 0.85},
            "event_timeline": [{"timestamp": "2026-09-13T10:00:00", "event": "Test event"}]
        })

        rec = self.db.get_risk_score("C999")
        self.assertIsNotNone(rec)
        self.assertEqual(rec["risk_score"], 90.0)
        self.assertEqual(rec["severity"], "critical")
        self.assertFalse(rec["is_false_positive"])

        # Record false positive feedback
        fb = self.db.record_feedback("C999", is_false_positive=True, reason="Authorized penetration test")
        self.assertEqual(fb["down_weight"], 0.4)

        # Recalibrated record check
        updated = self.db.get_risk_score("C999")
        self.assertEqual(updated["risk_score"], 36.0)  # 90 * 0.4
        self.assertEqual(updated["severity"], "low")
        self.assertTrue(updated["is_false_positive"])
        self.assertEqual(updated["feedback_reason"], "Authorized penetration test")

    def test_fastapi_endpoints_contract_b(self):
        client = TestClient(app)
        
        # 1. Health
        r = client.get("/health")
        self.assertEqual(r.status_code, 200)

        # 2. Queue (Contract B specifies a list)
        r = client.get("/queue")
        self.assertEqual(r.status_code, 200)
        data = r.json()
        self.assertIsInstance(data, list)
        if len(data) > 0:
            item = data[0]
            for field in ["user_id", "name", "role", "risk_score", "severity"]:
                self.assertIn(field, item)

        # 3. Case detail
        if len(data) > 0:
            uid = data[0]["user_id"]
            r_case = client.get(f"/case/{uid}")
            self.assertEqual(r_case.status_code, 200)
            case_data = r_case.json()
            for field in ["user_id", "risk_score", "self_score", "peer_score", "drift_score", "explanation_text", "cusum_path", "event_timeline"]:
                self.assertIn(field, case_data)
            self.assertIsInstance(case_data["cusum_path"], list)
            self.assertIsInstance(case_data["event_timeline"], list)

        # 4. Feedback endpoint
        r_fb = client.post("/feedback", json={"user_id": "C1000", "is_false_positive": True, "reason": "Test feedback"})
        self.assertEqual(r_fb.status_code, 200)
        self.assertTrue(r_fb.json().get("ok"))


if __name__ == "__main__":
    unittest.main()
