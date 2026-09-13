from __future__ import annotations

import json
import threading
import time
import unittest
import urllib.error
import urllib.request
from http.server import ThreadingHTTPServer
from pathlib import Path
import sys

ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT / "frontend"))

import mock_server


class LiveApiTests(unittest.TestCase):
    @classmethod
    def setUpClass(cls):
        cases, queue = mock_server.load_store()
        mock_server.Handler.cases = cases
        mock_server.Handler.queue = queue
        cls.httpd = ThreadingHTTPServer(("127.0.0.1", 0), mock_server.Handler)
        cls.port = cls.httpd.server_address[1]
        cls.thread = threading.Thread(target=cls.httpd.serve_forever, daemon=True)
        cls.thread.start()
        time.sleep(0.05)
        cls.base = f"http://127.0.0.1:{cls.port}"

    @classmethod
    def tearDownClass(cls):
        cls.httpd.shutdown()
        cls.httpd.server_close()

    def get(self, path: str):
        with urllib.request.urlopen(self.base + path, timeout=5) as res:
            return json.loads(res.read().decode())

    def test_health_and_queue_and_case_and_feedback(self):
        health = self.get("/health")
        self.assertTrue(health["ok"])
        self.assertGreater(health["queued"], 0)
        queue = self.get("/queue")
        self.assertGreaterEqual(queue[0]["risk_score"], queue[-1]["risk_score"])
        user_id = queue[0]["user_id"]
        detail = self.get(f"/case/{user_id}")
        self.assertEqual(detail["user_id"], user_id)
        self.assertTrue(detail["explanation_text"])
        self.assertTrue(detail["cusum_path"])
        self.assertTrue(detail["event_timeline"])
        payload = json.dumps(
            {"user_id": user_id, "is_false_positive": True, "reason": "test"}
        ).encode()
        req = urllib.request.Request(
            self.base + "/feedback",
            data=payload,
            headers={"Content-Type": "application/json"},
            method="POST",
        )
        with urllib.request.urlopen(req, timeout=5) as res:
            body = json.loads(res.read().decode())
        self.assertTrue(body["ok"])


if __name__ == "__main__":
    unittest.main()
