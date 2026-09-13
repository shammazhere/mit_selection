"""
Live Threat Activity Simulator for Silent Shift.

Allows investigators and presenters to inject custom suspicious activity for
ANY employee (including themselves with custom names, roles, websites, and files),
and immediately runs the full detection pipeline:
1. Injects realistic normal baseline + custom attack actions into CERT logs.
2. Runs Person 2 models (Isolation Forest self-baseline + Cohort z-score).
3. Runs Person 3 engine (CUSUM drift + Context multipliers + Explanation generator).
4. Persists the flagged alert directly into SQLite so the dashboard updates live.
"""

from __future__ import annotations

import csv
import sys
from datetime import datetime, timedelta
from pathlib import Path
from typing import List, Dict, Any, Optional
import pandas as pd

BASE_DIR = Path(__file__).resolve().parent
REPO_ROOT = BASE_DIR.parent
if str(REPO_ROOT) not in sys.path:
    sys.path.insert(0, str(REPO_ROOT))

from backend.ingestion.publish import run_person2
from backend.pipeline import Person3Pipeline
from backend.api.database import Database

BASE_DIR = Path(__file__).resolve().parent
REPO_ROOT = BASE_DIR.parent
SAMPLE_CERT_DIR = BASE_DIR / "data" / "sample_cert"
OUTPUT_DIR = BASE_DIR / "output"
DB_PATH = BASE_DIR / "data" / "scores.db"


def inject_custom_threat(
    name: str = "Mohammed Shamaz",
    role: str = "Engineer",
    department: str = "Engineering",
    team: str = "Platform",
    user_id: Optional[str] = None,
    site_visited: str = "https://wetransfer.com/upload",
    file_copied: str = "confidential_customer_db.sql",
    external_email: str = "personal_leak@gmail.com",
    include_after_hours: bool = True,
    include_usb: bool = True,
    include_removable_media: bool = True,
    include_cloud_upload: bool = True,
    include_external_email: bool = True,
    attack_days: int = 5,
    baseline_days: int = 19,
) -> Dict[str, Any]:
    """
    Inject custom user activity and run the end-to-end detection pipeline.
    """
    total_days = baseline_days + attack_days
    start_date = datetime(2011, 5, 2, 8, 30, 0)
    
    # Generate clean user_id if not provided
    if not user_id:
        clean_name = "".join(c for c in name if c.isalnum()).upper()
        user_id = f"U-{clean_name[:8]}"
    
    pc = f"PC-{user_id}"
    email_addr = f"{user_id.lower()}@dtaa.com"
    supervisor = "M-ENG" if department == "Engineering" else ("M-FIN" if department == "Finance" else "M-IT")

    # 1. Update/Add to LDAP
    ldap_file = SAMPLE_CERT_DIR / "ldap.csv"
    if ldap_file.exists():
        ldap_df = pd.read_csv(ldap_file)
        # Remove existing if already present to allow re-running
        ldap_df = ldap_df[ldap_df["user_id"] != user_id]
    else:
        ldap_df = pd.DataFrame(columns=["employee_name", "user_id", "email", "role", "department", "team", "supervisor"])
    
    new_ldap_row = {
        "employee_name": name,
        "user_id": user_id,
        "email": email_addr,
        "role": role,
        "department": department,
        "team": team,
        "supervisor": supervisor,
    }
    ldap_df = pd.concat([ldap_df, pd.DataFrame([new_ldap_row])], ignore_index=True)
    ldap_df.to_csv(ldap_file, index=False)

    # 2. Build Activity Logs
    logon_rows = []
    device_rows = []
    file_rows = []
    http_rows = []
    email_rows = []

    for d in range(total_days):
        day = start_date + timedelta(days=d)
        is_attack_day = (d >= baseline_days)
        
        # --- LOGON ---
        if is_attack_day and include_after_hours:
            # Suspicious after-hours logon (e.g. 23:15 at night)
            logon_time = day.replace(hour=23, minute=15, second=0).strftime("%m/%d/%Y %H:%M:%S")
            logoff_time = day.replace(hour=23, minute=58, second=0).strftime("%m/%d/%Y %H:%M:%S")
        else:
            # Normal 9-to-5
            logon_time = day.replace(hour=8, minute=30, second=0).strftime("%m/%d/%Y %H:%M:%S")
            logoff_time = day.replace(hour=17, minute=30, second=0).strftime("%m/%d/%Y %H:%M:%S")
        
        logon_rows.append({"id": f"L-{user_id}-{d}", "date": logon_time, "user": user_id, "pc": pc, "activity": "Logon"})
        logon_rows.append({"id": f"Loff-{user_id}-{d}", "date": logoff_time, "user": user_id, "pc": pc, "activity": "Logoff"})

        # --- NORMAL DAILY WORK ---
        # Normal intranet visit
        http_rows.append({
            "id": f"H-{user_id}-{d}-0",
            "date": day.replace(hour=11, minute=0, second=0).strftime("%m/%d/%Y %H:%M:%S"),
            "user": user_id,
            "pc": pc,
            "url": "https://intranet.dtaa.com/dashboard",
            "activity": "WWW Visit",
            "content": ""
        })
        # Normal routine file
        file_rows.append({
            "id": f"F-{user_id}-{d}-0",
            "date": day.replace(hour=10, minute=30, second=0).strftime("%m/%d/%Y %H:%M:%S"),
            "user": user_id,
            "pc": pc,
            "filename": f"C:\\workspace\\project_{d}.py",
            "activity": "File Open",
            "to_removable_media": False,
            "from_removable_media": False,
            "content": ""
        })
        # Normal internal email
        email_rows.append({
            "id": f"E-{user_id}-{d}-0",
            "date": day.replace(hour=9, minute=15, second=0).strftime("%m/%d/%Y %H:%M:%S"),
            "user": user_id,
            "pc": pc,
            "to": "team@dtaa.com",
            "cc": "",
            "bcc": "",
            "from": email_addr,
            "activity": "Send",
            "size": 28000,
            "attachments": 0,
            "content": ""
        })

        # --- SUSPICIOUS ATTACK ACTIVITY (ATTACK DAYS ONLY) ---
        if is_attack_day:
            attack_offset = d - baseline_days
            
            # USB Connect
            if include_usb:
                device_rows.append({
                    "id": f"D-{user_id}-{d}",
                    "date": day.replace(hour=23, minute=20, second=0).strftime("%m/%d/%Y %H:%M:%S"),
                    "user": user_id,
                    "pc": pc,
                    "file_tree": "R:\\",
                    "activity": "Connect"
                })
            
            # File copy to removable media
            if include_removable_media:
                for k in range(3):
                    file_rows.append({
                        "id": f"F-{user_id}-{d}-exfil-{k}",
                        "date": day.replace(hour=23, minute=25 + k*2, second=0).strftime("%m/%d/%Y %H:%M:%S"),
                        "user": user_id,
                        "pc": pc,
                        "filename": f"R:\\exfil\\part_{k}_{file_copied}",
                        "activity": "File Copy",
                        "to_removable_media": True,
                        "from_removable_media": False,
                        "content": ""
                    })

            # Cloud upload
            if include_cloud_upload:
                http_rows.append({
                    "id": f"H-{user_id}-{d}-exfil",
                    "date": day.replace(hour=23, minute=35, second=0).strftime("%m/%d/%Y %H:%M:%S"),
                    "user": user_id,
                    "pc": pc,
                    "url": site_visited,
                    "activity": "Web Upload",
                    "content": ""
                })

            # External email exfiltration
            if include_external_email:
                email_rows.append({
                    "id": f"E-{user_id}-{d}-exfil",
                    "date": day.replace(hour=23, minute=40, second=0).strftime("%m/%d/%Y %H:%M:%S"),
                    "user": user_id,
                    "pc": pc,
                    "to": external_email,
                    "cc": "",
                    "bcc": "",
                    "from": email_addr,
                    "activity": "Send",
                    "size": 850000,
                    "attachments": 3,
                    "content": ""
                })

    # 3. Append to existing CSVs (filtering out old records of this user)
    for name_stem, new_records in [
        ("logon", logon_rows),
        ("device", device_rows),
        ("file", file_rows),
        ("http", http_rows),
        ("email", email_rows),
    ]:
        file_path = SAMPLE_CERT_DIR / f"{name_stem}.csv"
        if file_path.exists():
            existing_df = pd.read_csv(file_path)
            # Filter out previous runs for this user_id
            user_col = "user" if "user" in existing_df.columns else "user_id"
            if user_col in existing_df.columns:
                existing_df = existing_df[existing_df[user_col] != user_id]
            combined_df = pd.concat([existing_df, pd.DataFrame(new_records)], ignore_index=True)
        else:
            combined_df = pd.DataFrame(new_records)
        combined_df.to_csv(file_path, index=False)

    print(f"[Simulator] Injected activity for {name} ({user_id}) into CERT logs.")

    # 4. Run Person 2 Detection Engine
    print("[Simulator] Running Person 2 Detection Models (Isolation Forest & Peer Cohort)...")
    csv_path = run_person2(SAMPLE_CERT_DIR, OUTPUT_DIR)

    # 5. Run Person 3 Fusion, Drift & Explanation Engine
    print("[Simulator] Running Person 3 Fusion & Drift Engine...")
    db = Database(str(DB_PATH))
    pipeline = Person3Pipeline(db=db, csv_path=str(csv_path), cert_dir=str(SAMPLE_CERT_DIR))
    pipeline.run()

    # 6. Retrieve result for the user
    user_case = db.get_risk_score(user_id)
    print(f"[Simulator] Detection complete! {name} score: {user_case.get('risk_score')} [{user_case.get('severity').upper()}]")
    
    return user_case


def main():
    import argparse
    parser = argparse.ArgumentParser(description="Inject suspicious activity and detect live.")
    parser.add_argument("--name", default="Mohammed Shamaz", help="Employee name")
    parser.add_argument("--role", default="Senior Engineer", help="Role")
    parser.add_argument("--site", default="https://wetransfer.com/upload", help="Suspicious URL visited")
    parser.add_argument("--file", default="confidential_patent_leak.tar.gz", help="Sensitive file exfiltrated")
    parser.add_argument("--email", default="personal_drop@gmail.com", help="External email recipient")
    args = parser.parse_args()

    result = inject_custom_threat(
        name=args.name,
        role=args.role,
        site_visited=args.site,
        file_copied=args.file,
        external_email=args.email,
    )
    print("\n" + "=" * 60)
    print(f"LIVE DETECTION RESULTS FOR: {result['name']} ({result['user_id']})")
    print("=" * 60)
    print(f"Risk Score:     {result['risk_score']}/100 [{result['severity'].upper()}]")
    print(f"Self-Baseline:  {result['self_score']:.2f} (Isolation Forest)")
    print(f"Peer-Baseline:  {result['peer_score']:.2f} (Cohort Deviation)")
    print(f"Temporal Drift: {result['drift_score']:.2f} (CUSUM)")
    print(f"Explanation:    {result['explanation_text']}")
    print(f"Timeline Events: {len(result.get('event_timeline', []))} concrete events detected")
    print("=" * 60)


if __name__ == "__main__":
    main()
