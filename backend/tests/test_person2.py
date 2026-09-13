from __future__ import annotations

import unittest
from pathlib import Path
import tempfile

from backend.ingestion.cert_loader import load_cert_bundle
from backend.ingestion.publish import run_person2, to_contract_a, CONTRACT_A_COLUMNS
from backend.ingestion.synthetic_cert import write_sample_cert
from backend.ingestion.user_day import build_user_days
from backend.models.cohorts import attach_cohorts
from backend.models.peer_baseline import score_peer_cohort
from backend.models.self_baseline import score_self_baseline


class Person2Tests(unittest.TestCase):
    @classmethod
    def setUpClass(cls):
        cls.tmp = tempfile.TemporaryDirectory()
        cls.data_dir = Path(cls.tmp.name) / "cert"
        write_sample_cert(cls.data_dir, days=20, n_users=18)
        cls.tables = load_cert_bundle(cls.data_dir)
        cls.user_days = build_user_days(cls.tables)
        cls.with_cohorts = attach_cohorts(cls.user_days, cls.tables["ldap"])
        cls.scored = score_peer_cohort(score_self_baseline(cls.with_cohorts))

    @classmethod
    def tearDownClass(cls):
        cls.tmp.cleanup()

    def test_user_days_have_expected_features(self):
        self.assertIn("logon_count", self.user_days.columns)
        self.assertIn("usb_events", self.user_days.columns)
        self.assertGreater(len(self.user_days), 100)

    def test_fallback_flagged_for_tiny_role(self):
        ldap = self.tables["ldap"].copy()
        ldap.loc[ldap["user_id"] == "C1000", "role"] = "CFO"
        tagged = attach_cohorts(self.user_days, ldap, min_cohort_size=5)
        insider = tagged[tagged["user_id"] == "C1000"]
        self.assertTrue(insider["fallback_applied"].all())
        self.assertTrue((insider["cohort_used"] == "department").all())
        self.assertIn("manager_cohort_size", tagged.columns)
        self.assertIn("role_manager_cohort_size", tagged.columns)

    def test_isolation_forest_scores_unit_interval(self):
        s = self.scored["self_score"]
        self.assertGreaterEqual(s.min(), 0.0)
        self.assertLessEqual(s.max(), 1.0)
        self.assertGreater(s.max(), 0.0)

    def test_insider_has_high_peer_score(self):
        insider = self.scored[self.scored["user_id"] == "C1000"]
        peers = self.scored[self.scored["user_id"] != "C1000"]
        self.assertGreater(insider["peer_score"].max(), peers["peer_score"].median())

    def test_contract_a_schema(self):
        out_dir = Path(self.tmp.name) / "out"
        path = run_person2(self.data_dir, out_dir)
        df = __import__("pandas").read_csv(path)
        self.assertEqual(list(df.columns), CONTRACT_A_COLUMNS)
        self.assertTrue(set(df["cohort_used"]).issubset({"role", "department"}))
        self.assertTrue(((df["self_score"] >= 0) & (df["self_score"] <= 1)).all())
        self.assertTrue(((df["peer_score"] >= 0) & (df["peer_score"] <= 1)).all())


if __name__ == "__main__":
    unittest.main()
