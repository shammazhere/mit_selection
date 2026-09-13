#!/usr/bin/env python3
"""Person 1 mocked Contract B API, served from Person 2's daily_user_scores.csv."""

from __future__ import annotations

import json
from http.server import BaseHTTPRequestHandler, ThreadingHTTPServer
from pathlib import Path
from urllib.parse import urlparse
import sys

sys.path.insert(0, str(Path(__file__).resolve().parent))
from adapter import load_store

HOST = "127.0.0.1"
PORT = 8787
FEEDBACK_PATH = Path(__file__).resolve().parent / "feedback_log.json"


class Handler(BaseHTTPRequestHandler):
    cases: dict = {}
    queue: list = []

    def log_message(self, fmt: str, *args) -> None:
        print("[mock-api]", fmt % args)

    def _cors(self) -> None:
        self.send_header("Access-Control-Allow-Origin", "*")
        self.send_header("Access-Control-Allow-Methods", "GET, POST, OPTIONS")
        self.send_header("Access-Control-Allow-Headers", "Content-Type")

    def _json(self, code: int, payload) -> None:
        body = json.dumps(payload).encode()
        self.send_response(code)
        self._cors()
        self.send_header("Content-Type", "application/json")
        self.send_header("Content-Length", str(len(body)))
        self.end_headers()
        self.wfile.write(body)

    def do_OPTIONS(self) -> None:
        self.send_response(204)
        self._cors()
        self.end_headers()

    def do_GET(self) -> None:
        parsed = urlparse(self.path)
        if parsed.path == "/queue":
            self._json(200, self.queue)
            return
        if parsed.path.startswith("/case/"):
            user_id = parsed.path.split("/case/", 1)[1].strip("/")
            case = self.cases.get(user_id)
            if not case:
                self._json(404, {"error": f"unknown user {user_id}"})
                return
            self._json(200, case)
            return
        if parsed.path in {"/", "/health"}:
            self._json(200, {"ok": True, "users": len(self.cases), "queued": len(self.queue)})
            return
        self._json(404, {"error": "not found"})

    def do_POST(self) -> None:
        parsed = urlparse(self.path)
        if parsed.path != "/feedback":
            self._json(404, {"error": "not found"})
            return
        length = int(self.headers.get("Content-Length", "0"))
        raw = self.rfile.read(length) if length else b"{}"
        try:
            payload = json.loads(raw.decode() or "{}")
        except json.JSONDecodeError:
            self._json(400, {"error": "invalid json"})
            return
        if not payload.get("user_id"):
            self._json(400, {"error": "user_id required"})
            return
        log = []
        if FEEDBACK_PATH.exists():
            try:
                log = json.loads(FEEDBACK_PATH.read_text(encoding="utf-8"))
            except Exception:
                log = []
        log.append(payload)
        FEEDBACK_PATH.write_text(json.dumps(log, indent=2), encoding="utf-8")
        try:
            cases, queue = load_store()
            Handler.cases = cases
            Handler.queue = queue
        except Exception:
            pass
        self._json(200, {"ok": True})


def main() -> None:
    cases, queue = load_store()
    Handler.cases = cases
    Handler.queue = queue
    server = ThreadingHTTPServer((HOST, PORT), Handler)
    print(f"Person 1 mock API (Contract B) on http://{HOST}:{PORT}", flush=True)
    print(f"Queue size: {len(queue)}  |  sourced from Person 2 daily_user_scores.csv", flush=True)
    server.serve_forever()


if __name__ == "__main__":
    main()
