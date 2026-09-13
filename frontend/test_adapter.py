from __future__ import annotations

import unittest
from pathlib import Path
import sys

ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT / "frontend"))

from adapter import load_store, queue_payload, build_cases, load_scores, load_ldap


class AdapterTests(unittest.TestCase):
    def test_person2_csv_maps_to_contract_b_queue(self):
        cases, queue = load_store()
        self.assertTrue(queue, "expected at least one flagged user from Person 2 scores")
        self.assertEqual(queue, sorted(queue, key=lambda r: r["risk_score"], reverse=True))
        top = queue[0]
        for key in ("user_id", "name", "role", "risk_score", "severity", "last_updated"):
            self.assertIn(key, top)
        self.assertIn(top["severity"], {"medium", "high", "critical"})
        self.assertGreaterEqual(top["risk_score"], 50)

    def test_case_has_explanation_and_cusum(self):
        cases, queue = load_store()
        user_id = queue[0]["user_id"]
        detail = cases[user_id]
        self.assertTrue(detail["explanation_text"])
        self.assertTrue(detail["cusum_path"])
        self.assertIn("self-baseline", detail["explanation_text"])
        self.assertTrue(detail["event_timeline"])
        self.assertIn(detail["cohort_used"], {"role", "department"})

    def test_insider_is_present(self):
        cases, _ = load_store()
        self.assertIn("C1000", cases)
        self.assertGreater(cases["C1000"]["self_score"], 0)


if __name__ == "__main__":
    unittest.main()
