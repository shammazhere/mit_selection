"""CERT-shaped sample logs so Person 2 can run before the real r4.2 dump is dropped in."""

from __future__ import annotations

from datetime import datetime, timedelta
from pathlib import Path

import pandas as pd


def write_sample_cert(out_dir: str | Path, days: int = 24, n_users: int = 20) -> Path:
    out_dir = Path(out_dir)
    out_dir.mkdir(parents=True, exist_ok=True)
    start = datetime(2011, 5, 2, 8, 15, 0)

    roles: list[str] = []
    depts: list[str] = []
    teams: list[str] = []
    managers: list[str] = []

    for i in range(n_users):
        if i < 6:
            roles.append("Accountant")
            depts.append("Finance")
            teams.append("AP")
            managers.append("M-FIN")
        elif i < 12:
            roles.append("Engineer")
            depts.append("Engineering")
            teams.append("Platform")
            managers.append("M-ENG")
        elif i < 18:
            roles.append("Administrator")
            depts.append("IT")
            teams.append("Ops")
            managers.append("M-IT")
        else:
            # Small cohort (size 2 in a 20-person org) to demonstrate Section 7.2
            # small-cohort fallback to department comparison
            roles.append("Financial Controller")
            depts.append("Finance")
            teams.append("Treasury")
            managers.append("M-FIN")

    users = [f"C{1000 + i}" for i in range(n_users)]
    insider = users[0]  # C1000: Critical threat
    controller = users[18] if n_users > 18 else None  # C1018: High threat + small cohort fallback
    engineer_spike = users[7] if n_users > 7 else None  # C1007: Medium threat spike

    ldap = pd.DataFrame(
        {
            "employee_name": [f"User {u}" for u in users],
            "user_id": users,
            "email": [f"{u.lower()}@dtaa.com" for u in users],
            "role": roles,
            "department": depts,
            "team": teams,
            "supervisor": managers,
        }
    )

    logon_rows, file_rows, email_rows, http_rows, device_rows = [], [], [], [], []
    for d in range(days):
        day = start + timedelta(days=d)
        for i, user in enumerate(users):
            pc = f"PC-{user}"
            is_insider = (user == insider)
            is_controller = (user == controller)
            is_eng_spike = (user == engineer_spike)

            # --- Logon activity ---
            if is_insider and d >= 14:
                logon_hour = 21  # After-hours logon
            elif is_controller and d >= 16:
                logon_hour = 20  # After-hours logon
            elif is_eng_spike and d >= 19:
                logon_hour = 22  # Off-hours spike
            else:
                logon_hour = 8

            logon_rows.append(
                {
                    "id": f"L-{user}-{d}",
                    "date": (day.replace(hour=logon_hour, minute=12)).strftime("%m/%d/%Y %H:%M:%S"),
                    "user": user,
                    "pc": pc,
                    "activity": "Logon",
                }
            )
            logon_rows.append(
                {
                    "id": f"Loff-{user}-{d}",
                    "date": (day.replace(hour=17, minute=40)).strftime("%m/%d/%Y %H:%M:%S"),
                    "user": user,
                    "pc": pc,
                    "activity": "Logoff",
                }
            )

            # --- File activity ---
            if is_insider:
                ramp = d / max(days - 1, 1)
                n_files = 8 + int(42 * ramp)
            elif is_controller and d >= 15:
                n_files = 30 + (d - 15) * 2
            elif is_eng_spike and d >= 19:
                n_files = 26
            else:
                # Normal baseline with subtle natural day-to-day variation
                n_files = 8 + ((d + i) % 3)

            for f in range(n_files):
                removable = False
                if is_insider and d >= 10 and f < max(1, d - 9):
                    removable = True
                elif is_controller and d >= 16 and f < 4:
                    removable = True

                file_rows.append(
                    {
                        "id": f"F-{user}-{d}-{f}",
                        "date": (day.replace(hour=11, minute=min(f, 59))).strftime("%m/%d/%Y %H:%M:%S"),
                        "user": user,
                        "pc": pc,
                        "filename": f"C:\\docs\\report_{f}.pdf" if not removable else f"R:\\docs\\confidential_export_{f}.pdf",
                        "activity": "File Copy" if removable else "File Open",
                        "to_removable_media": removable,
                        "from_removable_media": False,
                        "content": "",
                    }
                )

            # --- Email activity ---
            if is_insider and d >= 12:
                n_email = 14
                to_addr = "partner@gmail.com"
                email_size = 840000
                attachments = 2
            elif is_controller and d >= 17:
                n_email = 12
                to_addr = "finance-external@cloudvault.com"
                email_size = 420000
                attachments = 1
            else:
                n_email = 10 + ((d * 2 + i) % 4)
                to_addr = "colleague@dtaa.com"
                email_size = 35000 + ((d + i) % 5) * 3000
                attachments = 0

            for e in range(n_email):
                email_rows.append(
                    {
                        "id": f"E-{user}-{d}-{e}",
                        "date": (day.replace(hour=10, minute=min(e, 59))).strftime("%m/%d/%Y %H:%M:%S"),
                        "user": user,
                        "pc": pc,
                        "to": to_addr,
                        "cc": "",
                        "bcc": "",
                        "from": f"{user.lower()}@dtaa.com",
                        "activity": "Send",
                        "size": email_size,
                        "attachments": attachments,
                        "content": "",
                    }
                )

            # --- HTTP activity ---
            if is_insider and d >= 16:
                url = "https://dropbox.com/upload"
                activity = "WWW Upload"
            elif is_controller and d >= 18:
                url = "https://wetransfer.com/upload"
                activity = "WWW Upload"
            else:
                url = "https://intranet.dtaa.com/home"
                activity = "WWW Visit"

            http_rows.append(
                {
                    "id": f"H-{user}-{d}",
                    "date": (day.replace(hour=13, minute=5)).strftime("%m/%d/%Y %H:%M:%S"),
                    "user": user,
                    "pc": pc,
                    "url": url,
                    "activity": activity,
                    "content": "",
                }
            )

            # --- Device / USB activity ---
            if (is_insider and d >= 10) or (is_controller and d >= 16 and d % 2 == 0):
                device_rows.append(
                    {
                        "id": f"D-{user}-{d}",
                        "date": (day.replace(hour=16, minute=50)).strftime("%m/%d/%Y %H:%M:%S"),
                        "user": user,
                        "pc": pc,
                        "file_tree": "R:\\",
                        "activity": "Connect",
                    }
                )
            elif d % 9 == 0 and i == 7:
                device_rows.append(
                    {
                        "id": f"D-{user}-{d}",
                        "date": (day.replace(hour=12, minute=1)).strftime("%m/%d/%Y %H:%M:%S"),
                        "user": user,
                        "pc": pc,
                        "file_tree": "R:\\",
                        "activity": "Connect",
                    }
                )

    pd.DataFrame(logon_rows).to_csv(out_dir / "logon.csv", index=False)
    pd.DataFrame(file_rows).to_csv(out_dir / "file.csv", index=False)
    pd.DataFrame(email_rows).to_csv(out_dir / "email.csv", index=False)
    pd.DataFrame(http_rows).to_csv(out_dir / "http.csv", index=False)
    pd.DataFrame(device_rows).to_csv(out_dir / "device.csv", index=False)
    ldap.to_csv(out_dir / "ldap.csv", index=False)
    return out_dir
