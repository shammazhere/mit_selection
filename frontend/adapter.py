"""Person 1 mock layer: map Person 2 Contract A CSV → Contract B JSON.

When Person 3's FastAPI is live, set VITE_API_BASE and this file is unused.
"""

from __future__ import annotations

import csv
import json
from collections import defaultdict
from datetime import datetime
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
DEFAULT_SCORES = ROOT / "backend" / "output" / "daily_user_scores.csv"
DEFAULT_LDAP = ROOT / "backend" / "data" / "sample_cert" / "ldap.csv"
CERT_DIR = ROOT / "backend" / "data" / "sample_cert"
FEEDBACK_PATH = Path(__file__).resolve().parent / "feedback_log.json"

SEVERITY = (
    (80, "critical"),
    (65, "high"),
    (50, "medium"),
)


def _bool(value: str) -> bool:
    return str(value).strip().lower() in {"1", "true", "yes"}


def load_ldap(path: Path = DEFAULT_LDAP) -> dict[str, str]:
    names: dict[str, str] = {}
    if not path.exists():
        return names
    with path.open(newline="", encoding="utf-8") as handle:
        for row in csv.DictReader(handle):
            uid = row.get("user_id") or row.get("user")
            name = row.get("employee_name") or row.get("name")
            if uid and name:
                names[str(uid)] = name
    return names


def load_scores(path: Path = DEFAULT_SCORES) -> list[dict]:
    if not path.exists():
        raise FileNotFoundError(
            f"Person 2 scores not found at {path}. Run: python -m backend --sample"
        )
    rows = []
    with path.open(newline="", encoding="utf-8") as handle:
        for row in csv.DictReader(handle):
            rows.append(
                {
                    "user_id": row["user_id"],
                    "date": row["date"],
                    "self_score": float(row["self_score"]),
                    "peer_score": float(row["peer_score"]),
                    "cohort_used": row["cohort_used"],
                    "cohort_size": int(float(row["cohort_size"])),
                    "fallback_applied": _bool(row["fallback_applied"]),
                    "role": row.get("role") or "Unknown",
                    "team": row.get("team") or "Unknown",
                    "manager_id": row.get("manager_id") or "Unknown",
                }
            )
    rows.sort(key=lambda r: (r["user_id"], r["date"]))
    return rows


def _pre(self_score: float, peer_score: float) -> float:
    return 0.45 * self_score + 0.55 * peer_score


def _cusum_path(days: list[dict]) -> list[float]:
    stat = 0.0
    path = []
    target, slack = 0.35, 0.08
    for day in days:
        pre = _pre(day["self_score"], day["peer_score"])
        increment = max(0.0, pre - target - slack)
        stat = max(0.0, stat + increment)
        path.append(round(stat, 4))
    return path


def _severity(risk: float) -> str:
    for threshold, label in SEVERITY:
        if risk >= threshold:
            return label
    return "low"


def _explain(latest: dict, drift: float, consecutive: int) -> str:
    self_fired = latest["self_score"] >= 0.50
    peer_fired = latest["peer_score"] >= 0.50
    drift_fired = drift >= 0.25
    bits = []
    if self_fired:
        bits.append(f"activity is unlike this user's own history (self-baseline {latest['self_score']:.2f})")
    else:
        bits.append("self-baseline is within the user's usual range")
    if peer_fired:
        if latest["fallback_applied"]:
            bits.append(
                f"unlike their peer cohort (peer-baseline {latest['peer_score']:.2f}) — compared against role peers; "
                f"fell back to department comparison because the role cohort had only "
                f"{latest['cohort_size']} members"
            )
        else:
            bits.append(
                f"unlike their peer cohort (peer-baseline {latest['peer_score']:.2f}) — compared against role peers "
                f"(cohort size n={latest['cohort_size']})"
            )
    else:
        bits.append(
            f"peer-baseline is in line with the {latest['cohort_used']} cohort "
            f"(n={latest['cohort_size']})"
        )
    if drift_fired:
        bits.append(
            f"the fused daily score has trended upward for {max(consecutive, 1)} "
            "consecutive days (sustained drift)"
        )
    else:
        bits.append("CUSUM does not yet show a sustained upward drift")
    risk = latest["_risk"]
    agreeing = int(self_fired) + int(peer_fired) + int(drift_fired)
    if agreeing >= 2 and risk >= 50:
        lead = f"Flagged at {latest['_severity']} severity (risk {risk:.0f}/100): "
    else:
        lead = (
            f"Low priority — only {agreeing} of 3 signals fired "
            f"(risk {risk:.0f}/100): "
        )
    return lead + "; ".join(bits) + "."


def _format_date(raw_date: str) -> str:
    try:
        dt = datetime.strptime(raw_date, "%m/%d/%Y %H:%M:%S")
        return dt.strftime("%Y-%m-%dT%H:%M:%S")
    except Exception:
        return raw_date


def _cert_events(user_id: str, cert_path: Path = CERT_DIR) -> list[dict]:
    """Extract concrete security events for this user directly from CERT log files if present."""
    if not cert_path.exists():
        return []

    events = []
    try:
        dev_file = cert_path / "device.csv"
        if dev_file.exists():
            with dev_file.open(newline="", encoding="utf-8") as f:
                for row in csv.DictReader(f):
                    if (row.get("user") or row.get("user_id")) == user_id:
                        ts = _format_date(row.get("date", ""))
                        events.append({
                            "timestamp": ts,
                            "event": f"USB storage device connected ({row.get('pc', 'PC')}, drive {row.get('file_tree', 'R:')})",
                            "category": "device"
                        })

        file_file = cert_path / "file.csv"
        if file_file.exists():
            with file_file.open(newline="", encoding="utf-8") as f:
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

        http_file = cert_path / "http.csv"
        if http_file.exists():
            with http_file.open(newline="", encoding="utf-8") as f:
                for row in csv.DictReader(f):
                    if (row.get("user") or row.get("user_id")) == user_id:
                        act = row.get("activity", "")
                        url = row.get("url", "")
                        if "upload" in act.lower() or "dropbox" in url.lower() or "wetransfer" in url.lower():
                            ts = _format_date(row.get("date", ""))
                            events.append({
                                "timestamp": ts,
                                "event": f"Web file upload to {url}",
                                "category": "http"
                            })

        email_file = cert_path / "email.csv"
        if email_file.exists():
            with email_file.open(newline="", encoding="utf-8") as f:
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

        logon_file = cert_path / "logon.csv"
        if logon_file.exists():
            with logon_file.open(newline="", encoding="utf-8") as f:
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
    except Exception:
        pass

    events.sort(key=lambda x: x["timestamp"])
    return events


def _timeline(days: list[dict], user_id: str = "") -> list[dict]:
    baseline_events = []
    for day in days:
        pre = _pre(day["self_score"], day["peer_score"])
        if day["self_score"] >= 0.50:
            baseline_events.append(
                {
                    "timestamp": f"{day['date']}T09:00:00",
                    "event": f"Self-baseline elevated ({day['self_score']:.2f})",
                    "category": "signal"
                }
            )
        if day["peer_score"] >= 0.50:
            baseline_events.append(
                {
                    "timestamp": f"{day['date']}T12:00:00",
                    "event": f"Peer-cohort deviation elevated ({day['peer_score']:.2f})",
                    "category": "signal"
                }
            )
        if day["fallback_applied"]:
            baseline_events.append(
                {
                    "timestamp": f"{day['date']}T08:00:00",
                    "event": "Department-level cohort fallback applied (small role cohort)",
                    "category": "fallback"
                }
            )
        if pre >= 0.50:
            baseline_events.append(
                {
                    "timestamp": f"{day['date']}T17:30:00",
                    "event": f"Combined self+peer pre-multiplier score reached {pre:.2f}",
                    "category": "signal"
                }
            )

    forensic_events = _cert_events(user_id) if user_id else []
    combined = sorted(baseline_events + forensic_events, key=lambda e: e["timestamp"])
    # Return formatted items matching Contract B shape: {"timestamp": ..., "event": ...}
    return [{"timestamp": e["timestamp"], "event": e["event"]} for e in combined[-32:]]


def _load_feedback() -> dict[str, dict]:
    if not FEEDBACK_PATH.exists():
        return {}
    try:
        items = json.loads(FEEDBACK_PATH.read_text(encoding="utf-8"))
        return {item["user_id"]: item for item in items if isinstance(item, dict) and "user_id" in item}
    except Exception:
        return {}


def build_cases(scores: list[dict], names: dict[str, str]) -> dict[str, dict]:
    by_user: dict[str, list[dict]] = defaultdict(list)
    for row in scores:
        by_user[row["user_id"]].append(row)

    feedback_map = _load_feedback()
    cases = {}
    for user_id, days in by_user.items():
        path = _cusum_path(days)
        latest = dict(days[-1])
        drift = min(1.0, path[-1] / 0.40) if path else 0.0
        consecutive = 0
        for value in reversed(path):
            if value > 0.25:
                consecutive += 1
            else:
                break

        raw_risk = round(min(100.0, 100.0 * (0.75 * _pre(latest["self_score"], latest["peer_score"]) + 0.25 * drift)), 1)
        
        # Apply feedback down-weighting if marked as false positive
        is_fp = user_id in feedback_map
        risk = round(raw_risk * 0.4, 1) if is_fp else raw_risk

        latest["_risk"] = risk
        latest["_severity"] = _severity(risk)
        self_fired = latest["self_score"] >= 0.50
        peer_fired = latest["peer_score"] >= 0.50
        drift_fired = path[-1] > 0.25 if path else False
        agreeing = int(self_fired) + int(peer_fired) + int(drift_fired)
        alert = (agreeing >= 2 and risk >= 50) and not is_fp

        cases[user_id] = {
            "user_id": user_id,
            "name": names.get(user_id, f"User {user_id}"),
            "role": latest["role"],
            "team": latest["team"],
            "risk_score": risk,
            "severity": latest["_severity"],
            "last_updated": latest["date"],
            "self_score": round(latest["self_score"], 4),
            "peer_score": round(latest["peer_score"], 4),
            "drift_score": round(drift, 4),
            "cohort_used": latest["cohort_used"],
            "fallback_applied": latest["fallback_applied"],
            "explanation_text": _explain(latest, drift, consecutive),
            "cusum_path": path,
            "event_timeline": _timeline(days, user_id),
            "alert": alert,
            "is_false_positive": is_fp,
            "feedback_reason": feedback_map.get(user_id, {}).get("reason", ""),
        }
    return cases


def queue_payload(cases: dict[str, dict]) -> list[dict]:
    rows = [
        {
            "user_id": c["user_id"],
            "name": c["name"],
            "role": c["role"],
            "risk_score": c["risk_score"],
            "severity": c["severity"],
            "last_updated": c["last_updated"],
            "fallback_applied": c["fallback_applied"],
        }
        for c in cases.values()
        if c["alert"]
    ]
    rows.sort(key=lambda r: r["risk_score"], reverse=True)
    return rows


def load_store(scores_path: Path = DEFAULT_SCORES, ldap_path: Path = DEFAULT_LDAP):
    scores = load_scores(scores_path)
    names = load_ldap(ldap_path)
    cases = build_cases(scores, names)
    return cases, queue_payload(cases)
