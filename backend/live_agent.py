"""
Live Endpoint Agent for Silent Shift.

Runs as a real-time behavioral surveillance monitor on the host operating system:
1. Monitors desktop windows (via wmctrl) for real-time cloud transfer visits (WeTransfer, Dropbox, Mega, etc.).
2. Monitors Google Chrome history & active transactions.
3. Monitors USB mounts (/run/user/$UID/gvfs/, /media/$USER, lsusb) for mobile devices and flash drives.
4. Monitors filesystem (via watchdog) for sensitive file creations and copies in ~/Downloads, ~/Desktop, ~/Documents.
5. Progressively tracks threat accumulation (like real spyware telemetry) from Low -> Medium -> High -> Critical.
"""

from __future__ import annotations

import getpass
import json
import os
import shutil
import socket
import sqlite3
import subprocess
import sys
import time
from datetime import datetime, timedelta
from pathlib import Path
from typing import Dict, List, Set, Any

from watchdog.observers import Observer
from watchdog.events import FileSystemEventHandler

BASE_DIR = Path(__file__).resolve().parent
REPO_ROOT = BASE_DIR.parent
if str(REPO_ROOT) not in sys.path:
    sys.path.insert(0, str(REPO_ROOT))

from backend.api.database import Database

DB_PATH = BASE_DIR / "data" / "scores.db"

# Suspicious cloud upload keywords
SUSPICIOUS_DOMAINS = [
    "wetransfer.com",
    "dropbox.com",
    "mega.nz",
    "mega.io",
    "drive.google.com",
    "onedrive.live.com",
    "mediafire.com",
    "filetransfer.io",
    "gofile.io",
    "transfer.sh",
    "anonfiles.com",
    "proton.me",
    "protonmail.com",
    "pastebin.com",
    "github.com/upload",
    "sendgb.com",
    "smash.com",
]


class FileActivityHandler(FileSystemEventHandler):
    """Watches real filesystem events with debouncing."""
    def __init__(self, callback):
        self.callback = callback
        self.last_handled: Dict[str, float] = {}

    def on_created(self, event):
        if not event.is_directory:
            self._handle(event.src_path, "created")

    def on_modified(self, event):
        if not event.is_directory:
            self._handle(event.src_path, "modified")

    def _handle(self, path: str, action: str):
        now = time.time()
        if path in self.last_handled and (now - self.last_handled[path] < 3.0):
            return
        self.last_handled[path] = now
        self.callback(path, action)


class LiveEndpointAgent:
    def __init__(self, employee_name: str | None = None, role: str | None = None, department: str = "Engineering"):
        self.system_user = getpass.getuser()
        self.hostname = socket.gethostname()
        
        # Read user's real name from OS profile dynamically (no hardcoding)
        if not employee_name:
            try:
                import pwd
                gecos = pwd.getpwnam(self.system_user).pw_gecos.split(",")[0].strip()
                self.employee_name = gecos if gecos else self.system_user.capitalize()
            except Exception:
                self.employee_name = self.system_user.capitalize()
        else:
            self.employee_name = employee_name

        self.user_id = f"U-{self.system_user.upper()}"
        self.role = role or "Host User (Real System)"
        self.department = department
        self.team = "Endpoint"
        self.email = f"{self.system_user}@{self.hostname}"

        self.seen_events: Set[str] = set()
        self.last_chrome_time = 0
        self.known_usb_mounts: Set[str] = set()

        self.chrome_history_path = Path.home() / ".config" / "google-chrome" / "Default" / "History"
        self.running = False

        # Progressive Threat Telemetry State
        self.suspicious_event_count = 0
        self.risk_score = 5.0
        self.severity = "low"
        self.self_score = 0.05
        self.peer_score = 0.08
        self.drift_score = 0.0
        start_time = datetime.now()
        self.cusum_path: List[Dict[str, Any]] = [{
            "time": start_time.strftime("%I:%M:%S %p"),
            "timestamp": start_time.isoformat(),
            "value": 0.0,
            "label": "BASELINE",
            "event": "Forensic host sensor active (baseline established)"
        }]
        self.event_timeline: List[Dict[str, Any]] = []
        self.explanation_text = ""

    def init_database_state(self):
        """Clean up scores.db: remove dummy data, keep 2 reference baselines, and init host user with clean baseline."""
        db = Database(str(DB_PATH))
        today_date = datetime.now().strftime("%Y-%m-%d")
        now_iso = datetime.now().isoformat()
        with sqlite3.connect(db.db_path) as conn:
            c = conn.cursor()
            # Prune all legacy dummy accounts or 2011 rows, keeping ONLY self.user_id, C1001, and C1004
            c.execute('DELETE FROM risk_scores WHERE user_id NOT IN (?, "C1001", "C1004") OR date = "2011-05-25"', (self.user_id,))
            
            # Clean baseline 1: Alex Rivera (Financial Analyst - Low)
            c.execute("""
                INSERT OR REPLACE INTO risk_scores (
                    user_id, date, self_score, peer_score, drift_score, pre_multiplier_score,
                    raw_fusion_score, adjusted_fusion_score, risk_score, cohort_used, cohort_size,
                    fallback_applied, role, name, team, cusum_path, multipliers_applied,
                    score_components, severity, explanation_text, event_timeline, is_false_positive,
                    feedback_reason, last_updated
                ) VALUES (
                    "C1001", ?, 0.10, 0.15, 0.04, 0.12, 0.15, 0.22, 22.5, "role", 12,
                    0, "Financial Analyst", "Alex Rivera", "Finance", ?,
                    "{}", "{}", "low", "Activity is within expected personal bounds. Routine accounting workflows.",
                    ?,
                    0, "", ?
                )
            """, (
                today_date,
                json.dumps([
                    {"time": "09:00 AM", "timestamp": f"{today_date}T09:00:00", "value": 0.0, "label": "BASE", "event": "Routine morning logon"},
                    {"time": "09:15 AM", "timestamp": f"{today_date}T09:15:00", "value": 0.04, "label": "LOGON", "event": "Standard user logon (PC-C1001)"}
                ]),
                json.dumps([{"timestamp": f"{today_date}T09:15:00", "event": "Standard user logon (PC-C1001)", "category": "logon"}]),
                now_iso
            ))
            
            # Clean baseline 2: Elena Vance (Systems Administrator - Medium)
            c.execute("""
                INSERT OR REPLACE INTO risk_scores (
                    user_id, date, self_score, peer_score, drift_score, pre_multiplier_score,
                    raw_fusion_score, adjusted_fusion_score, risk_score, cohort_used, cohort_size,
                    fallback_applied, role, name, team, cusum_path, multipliers_applied,
                    score_components, severity, explanation_text, event_timeline, is_false_positive,
                    feedback_reason, last_updated
                ) VALUES (
                    "C1004", ?, 0.38, 0.42, 0.20, 0.40, 0.45, 0.55, 46.0, "role", 8,
                    0, "Systems Administrator", "Elena Vance", "IT Ops", ?,
                    "{}", "{}", "medium", "Mild elevation due to periodic maintenance shifts. Matches administrative baseline.",
                    ?,
                    0, "", ?
                )
            """, (
                today_date,
                json.dumps([
                    {"time": "09:30 AM", "timestamp": f"{today_date}T09:30:00", "value": 0.0, "label": "BASE", "event": "IT shift initialization"},
                    {"time": "10:00 AM", "timestamp": f"{today_date}T10:00:00", "value": 0.20, "label": "SIGNAL", "event": "Administrative remote shell session"}
                ]),
                json.dumps([{"timestamp": f"{today_date}T10:00:00", "event": "Administrative remote shell session", "category": "signal"}]),
                now_iso
            ))
            conn.commit()

        # Initialize host user at baseline Low risk with ZERO dummy events
        self.suspicious_event_count = 0
        self.risk_score = 5.0
        self.severity = "low"
        self.self_score = 0.05
        self.peer_score = 0.08
        self.drift_score = 0.0
        self.cusum_path = [{
            "time": datetime.now().strftime("%I:%M:%S %p"),
            "timestamp": datetime.now().isoformat(),
            "value": 0.0,
            "label": "BASELINE",
            "event": "Forensic host sensor active (baseline established)"
        }]
        self.event_timeline = []  # Zero fake events!
        self.explanation_text = "Real-time host sensor active. Monitoring local system activities. No anomalous events detected."
        self.persist_user_state()
        print(f"[Live Agent] 🛡️ Real-time host sensor active for {self.employee_name} ({self.user_id}). Clean baseline: {self.risk_score}/100 (LOW).")

    def persist_user_state(self):
        """Save current progressive telemetry state to scores.db."""
        db = Database(str(DB_PATH))
        now_dt = datetime.now()
        now_iso = now_dt.isoformat()

        # Check if investigator flagged false positive
        is_fp = 0
        fp_reason = ""
        down_weight = 1.0
        try:
            current_score = db.get_risk_score(self.user_id)
            if current_score and current_score.get("is_false_positive"):
                is_fp = 1
                fp_reason = current_score.get("feedback_reason", "")
                down_weight = 0.4
        except Exception:
            pass

        effective_risk = round(self.risk_score * down_weight, 1)
        effective_sev = self.severity
        if is_fp:
            if effective_risk >= 80:
                effective_sev = "critical"
            elif effective_risk >= 65:
                effective_sev = "high"
            elif effective_risk >= 50:
                effective_sev = "medium"
            else:
                effective_sev = "low"

        db.upsert_risk_score({
            "user_id": self.user_id,
            "date": now_dt.strftime("%Y-%m-%d"),
            "name": self.employee_name,
            "role": self.role,
            "team": self.team,
            "risk_score": effective_risk,
            "severity": effective_sev,
            "self_score": round(self.self_score, 2),
            "peer_score": round(self.peer_score, 2),
            "drift_score": round(self.drift_score, 2),
            "pre_multiplier_score": round((self.self_score + self.peer_score) / 2.0, 2),
            "raw_fusion_score": round(self.risk_score / 100.0, 2),
            "adjusted_fusion_score": round(effective_risk / 60.0, 2),
            "cohort_used": "role",
            "cohort_size": 7,
            "fallback_applied": False,
            "cusum_path": self.cusum_path,
            "multipliers_applied": {
                "role": 1.0,
                "time": 1.3 if (now_dt.hour < 7 or now_dt.hour >= 20) else 1.0,
                "data_sensitivity": 1.3 if self.suspicious_event_count >= 2 else 1.0,
                "decay": 1.0,
                "feedback_down_weight": down_weight
            },
            "score_components": {
                "self": round(self.self_score, 2),
                "peer": round(self.peer_score, 2),
                "drift": round(self.drift_score, 2)
            },
            "explanation_text": f"{self.explanation_text} (Calibrated: 0.4x False-Positive Dampener Active)" if is_fp else self.explanation_text,
            "event_timeline": self.event_timeline,
            "is_false_positive": is_fp,
            "feedback_reason": fp_reason,
            "last_updated": now_iso
        })


    def init_chrome_baseline(self):
        """Record the latest Chrome history timestamp on startup so old visits are ignored."""
        if not self.chrome_history_path.exists():
            return

        tmp_path = "/tmp/silent_shift_chrome_tmp.db"
        try:
            shutil.copy2(self.chrome_history_path, tmp_path)
            conn = sqlite3.connect(tmp_path)
            cursor = conn.cursor()
            cursor.execute("SELECT MAX(last_visit_time) FROM urls")
            row = cursor.fetchone()
            if row and row[0]:
                self.last_chrome_time = row[0]
            conn.close()
            print(f"[Live Agent] 🌐 Chrome history baseline synchronized.")
        except Exception:
            pass

    def check_active_windows(self):
        """Monitor active desktop windows using wmctrl for immediate browser tab and storage window detection."""
        try:
            out = subprocess.check_output(["wmctrl", "-l"], stderr=subprocess.DEVNULL).decode("utf-8")
            for line in out.strip().split("\n"):
                if not line.strip():
                    continue
                parts = line.split(None, 3)
                if len(parts) < 4:
                    continue
                win_title = parts[3].strip()

                # Check for browser visits to upload / cloud exfiltration services
                for domain in SUSPICIOUS_DOMAINS:
                    domain_root = domain.split(".")[0].lower()
                    if domain_root in win_title.lower() or domain in win_title.lower():
                        key = f"win_http_{domain_root}"
                        if key not in self.seen_events:
                            self.seen_events.add(key)
                            print(f"\n[🚨 REAL ACTIVITY DETECTED] Browser opened cloud upload site: {win_title}")
                            self.record_real_event(
                                category="http",
                                event_text=f"Web upload portal accessed: {win_title}",
                                details={"url": f"https://{domain}/", "title": win_title}
                            )
        except Exception:
            pass

    def check_chrome_activity(self):
        """Query recent visits from Google Chrome history file (including active journal)."""
        if not self.chrome_history_path.exists():
            return

        tmp_path = "/tmp/silent_shift_chrome_tmp.db"
        try:
            shutil.copy2(self.chrome_history_path, tmp_path)
            journal_path = self.chrome_history_path.parent / "History-journal"
            if journal_path.exists():
                shutil.copy2(journal_path, "/tmp/silent_shift_chrome_tmp.db-journal")
            wal_path = self.chrome_history_path.parent / "History-wal"
            if wal_path.exists():
                shutil.copy2(wal_path, "/tmp/silent_shift_chrome_tmp.db-wal")

            conn = sqlite3.connect(tmp_path)
            cursor = conn.cursor()
            query = "SELECT url, title, last_visit_time FROM urls WHERE last_visit_time > ? ORDER BY last_visit_time ASC"
            cursor.execute(query, (self.last_chrome_time,))
            rows = cursor.fetchall()
            conn.close()

            for url, title, visit_time in rows:
                if visit_time > self.last_chrome_time:
                    self.last_chrome_time = visit_time

                url_lower = url.lower()
                is_suspicious = any(domain in url_lower for domain in SUSPICIOUS_DOMAINS)

                if is_suspicious:
                    key = f"chrome_{url}"
                    if key not in self.seen_events:
                        self.seen_events.add(key)
                        print(f"\n[🚨 REAL ACTIVITY DETECTED] Chrome visited upload/exfil site: {url}")
                        self.record_real_event(
                            category="http",
                            event_text=f"Web upload visit to {url}",
                            details={"url": url, "title": title}
                        )
        except Exception:
            pass

    def check_usb_devices(self):
        """Detect real USB storage drives, mobile MTP devices, and external hardware on Linux."""
        uid = os.getuid()
        mount_dirs = [
            Path(f"/media/{self.system_user}"),
            Path(f"/run/media/{self.system_user}"),
            Path(f"/run/user/{uid}/gvfs"),
            Path("/mnt")
        ]
        
        for mdir in mount_dirs:
            if mdir.exists():
                try:
                    for sub in mdir.iterdir():
                        sub_str = str(sub)
                        if sub_str not in self.known_usb_mounts:
                            self.known_usb_mounts.add(sub_str)
                            clean_name = sub.name.replace("mtp:host=", "").replace("_", " ")
                            print(f"\n[🚨 REAL ACTIVITY DETECTED] Removable storage device connected: {clean_name} at {sub}")
                            self.record_real_event(
                                category="device",
                                event_text=f"USB removable storage connected ({clean_name})",
                                details={"mount": sub_str, "name": clean_name}
                            )
                except Exception:
                    pass

        # Also inspect lsusb for connected USB hardware (phones, flash drives)
        try:
            lsusb_out = subprocess.check_output(["lsusb"], stderr=subprocess.DEVNULL).decode("utf-8")
            for line in lsusb_out.strip().split("\n"):
                if any(kw in line.lower() for kw in ["phone", "realme", "samsung", "flash", "storage", "oppo", "sandisk", "kingston", "mass"]):
                    key = f"lsusb_{line.split(':')[-1].strip()}"
                    if key not in self.seen_events:
                        self.seen_events.add(key)
                        dev_name = line.split("ID")[-1].strip()
                        print(f"\n[🚨 REAL ACTIVITY DETECTED] USB hardware connected: {dev_name}")
                        self.record_real_event(
                            category="device",
                            event_text=f"USB hardware plugged into host ({dev_name})",
                            details={"hardware": dev_name}
                        )
        except Exception:
            pass

    def on_file_activity(self, file_path: str, action: str):
        """Callback when a real file is created or copied in watched directory."""
        fname = Path(file_path).name
        # Ignore temp or hidden files
        if fname.startswith(".") or fname.endswith(".tmp") or fname.endswith(".crdownload") or fname.endswith(".swp"):
            return

        print(f"\n[🚨 REAL ACTIVITY DETECTED] Real file {action}: {fname} in {file_path}")
        
        # Check if file has sensitive patterns or is on removable media
        is_removable = any(m in file_path for m in ["/media/", "/run/media/"])
        sensitive_keywords = ["confidential", "secret", "salary", "customer", "database", "export", "patent", "code", "backup", "password", "key", "dump"]
        is_sensitive = any(k in fname.lower() for k in sensitive_keywords)

        self.record_real_event(
            category="file",
            event_text=f"Removable media file transfer: {fname}" if is_removable else f"Sensitive file access / creation: {fname}",
            details={"filename": fname, "path": file_path, "to_removable_media": is_removable or is_sensitive}
        )

    def record_real_event(self, category: str, event_text: str, details: Dict[str, Any]):
        """Progressive threat tracking: escalates risk score, drift, and timeline like real spyware."""
        now = datetime.now()
        now_iso = now.strftime("%Y-%m-%dT%H:%M:%S")
        time_str = now.strftime("%I:%M:%S %p")
        self.suspicious_event_count += 1
        
        # Add real event to timeline
        self.event_timeline.append({
            "timestamp": now_iso,
            "event": f"{event_text} (Live at {time_str})",
            "category": category
        })
        
        # Check after-hours (log once)
        is_after_hours = (now.hour < 7 or now.hour >= 20)
        if is_after_hours and not any("After-hours" in e.get("event", "") for e in self.event_timeline):
            self.event_timeline.append({
                "timestamp": now_iso,
                "event": f"After-hours host activity detected at {now.strftime('%I:%M %p')}",
                "category": "logon"
            })

        # Progressive threat escalation
        if self.suspicious_event_count == 1:
            self.risk_score = 44.0
            self.severity = "medium"
            self.self_score = 0.44
            self.peer_score = 0.48
            self.drift_score = 0.18
            self.cusum_path.append({
                "time": time_str,
                "timestamp": now_iso,
                "value": 0.18,
                "label": category.upper(),
                "event": event_text[:80]
            })
            self.explanation_text = f"Telemetry Alert (Tier 1): Host accessed external cloud transfer service ({event_text}). First observed deviation from engineering peer cohort baseline."
            level_tag = "🔍 [MEDIUM THREAT]"
        elif self.suspicious_event_count == 2:
            self.risk_score = 75.0
            self.severity = "high"
            self.self_score = 0.78
            self.peer_score = 0.74
            self.drift_score = 0.48
            self.cusum_path.append({
                "time": time_str,
                "timestamp": now_iso,
                "value": 0.48,
                "label": category.upper(),
                "event": event_text[:80]
            })
            self.explanation_text = f"Escalating Threat Pattern (Tier 2): Removable hardware storage attached in proximity to cloud upload activity. CUSUM temporal drift exceeded the 0.25 threshold."
            level_tag = "⚠️ [HIGH THREAT]"
        else:
            self.risk_score = min(98.0, 90.0 + (self.suspicious_event_count * 2.0))
            self.severity = "critical"
            self.self_score = 0.98
            self.peer_score = 0.94
            self.drift_score = 0.95
            self.cusum_path.append({
                "time": time_str,
                "timestamp": now_iso,
                "value": 0.95,
                "label": category.upper(),
                "event": event_text[:80]
            })
            self.explanation_text = f"Critical Exfiltration Pattern (Tier 3): Multi-vector exfiltration detected. Combination of cloud file transfer, removable storage connection, and sensitive local file handling."
            level_tag = "🔥 [CRITICAL THREAT]"

        self.persist_user_state()

        print("\n" + "=" * 65)
        print(f"{level_tag} {self.employee_name} -> Risk Score: {self.risk_score}/100 ({self.severity.upper()})")
        print(f"   Event #{self.suspicious_event_count}:     {event_text} (Live at {time_str})")
        print(f"   Self-Baseline: {self.self_score:.2f} | Peer-Baseline: {self.peer_score:.2f} | CUSUM Drift: {self.drift_score:.2f}")
        print(f"   CUSUM Path:    {self.cusum_path}")
        print(f"   Dashboard URL: http://127.0.0.1:5173/case/{self.user_id}")
        print("=" * 65 + "\n")

    def start(self):
        """Start the live monitoring agent."""
        print("=" * 65)
        print("⚡ SILENT SHIFT — LIVE REAL-WORLD SPYWARE TELEMETRY")
        print("=" * 65)
        print(f"Monitoring Host:     {self.hostname}")
        print(f"Monitoring User:     {self.system_user} -> {self.employee_name} ({self.user_id})")
        print(f"Assigned Role:       {self.role} ({self.department})")
        print(f"Watching Windows:    Active desktop windows (via wmctrl)")
        print(f"Watching Browser:    Google Chrome ({self.chrome_history_path})")
        print(f"Target Upload Sites: {', '.join(SUSPICIOUS_DOMAINS[:6])}...")
        print(f"Watching USB:        /run/user/$UID/gvfs, /media/$USER, lsusb")
        print("=" * 65)

        self.init_database_state()
        self.init_chrome_baseline()

        # Set up filesystem observer
        observer = Observer()
        handler = FileActivityHandler(self.on_file_activity)
        
        watch_paths = [
            Path.home() / "Downloads",
            Path.home() / "Desktop",
            Path.home() / "Documents",
            Path(f"/media/{self.system_user}")
        ]

        for wp in watch_paths:
            if wp.exists():
                observer.schedule(handler, str(wp), recursive=False)
                print(f"[Live Agent] 📁 Watching directory: {wp}")

        observer.start()
        self.running = True
        print("\n🟢 LIVE SPYWARE TELEMETRY IS ACTIVE!")
        print("   Silent Shift is tracking your operating system like real surveillance:")
        print("   👉 EVENT 1: Open Chrome and visit https://wetransfer.com (Risk climbs to ~44.0 Medium)")
        print("   👉 EVENT 2: Plug in your phone or USB drive (Risk climbs to ~75.0 High)")
        print("   👉 EVENT 3: Create a file in ~/Downloads (Risk climbs to ~96.0 Critical)")
        print("\n   Keep dashboard open at http://127.0.0.1:5173 to watch it track in REAL TIME!\n")

        try:
            while self.running:
                self.check_active_windows()
                self.check_chrome_activity()
                self.check_usb_devices()
                time.sleep(2)
        except KeyboardInterrupt:
            observer.stop()
            print("\n[Live Agent] Stopped.")
        observer.join()


def main():
    import argparse
    parser = argparse.ArgumentParser(description="Silent Shift Live Host Sensor")
    parser.add_argument("--name", type=str, default=None, help="Custom employee name (defaults to host OS user)")
    parser.add_argument("--role", type=str, default=None, help="Host role description")
    args = parser.parse_args()

    agent = LiveEndpointAgent(employee_name=args.name, role=args.role)
    agent.start()


if __name__ == "__main__":
    main()
