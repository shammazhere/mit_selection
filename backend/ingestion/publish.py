"""Publish Contract A: daily_user_scores for Person 3."""

from __future__ import annotations

from pathlib import Path

import pandas as pd

from backend.ingestion.cert_loader import load_cert_bundle
from backend.ingestion.synthetic_cert import write_sample_cert
from backend.ingestion.user_day import build_user_days
from backend.models.cohorts import attach_cohorts
from backend.models.peer_baseline import score_peer_cohort
from backend.models.self_baseline import score_self_baseline

CONTRACT_A_COLUMNS = [
    "user_id",
    "date",
    "self_score",
    "peer_score",
    "cohort_used",
    "cohort_size",
    "fallback_applied",
    "role",
    "team",
    "manager_id",
]


def to_contract_a(scored: pd.DataFrame) -> pd.DataFrame:
    out = scored.copy()
    out["date"] = pd.to_datetime(out["day"]).dt.strftime("%Y-%m-%d")
    out["self_score"] = out["self_score"].astype(float).clip(0, 1).round(6)
    out["peer_score"] = out["peer_score"].astype(float).clip(0, 1).round(6)
    out["fallback_applied"] = out["fallback_applied"].astype(bool)
    out["cohort_size"] = out["cohort_size"].astype(int)
    return out[CONTRACT_A_COLUMNS].sort_values(["date", "user_id"]).reset_index(drop=True)


def run_person2(data_dir: str | Path, out_dir: str | Path) -> Path:
    data_dir = Path(data_dir)
    http_files = list(data_dir.rglob("http.csv")) + list(data_dir.rglob("http.CSV"))
    large = any(p.stat().st_size > 80_000_000 for p in http_files)
    if large:
        from backend.ingestion.cert_loader import load_ldap
        from backend.ingestion.user_day import build_user_days_from_dir

        user_days = build_user_days_from_dir(data_dir)
        ldap = load_ldap(data_dir)
    else:
        tables = load_cert_bundle(data_dir)
        user_days = build_user_days(tables)
        ldap = tables["ldap"]
    with_cohorts = attach_cohorts(user_days, ldap)
    with_self = score_self_baseline(with_cohorts)
    scored = score_peer_cohort(with_self)
    contract = to_contract_a(scored)

    out_dir = Path(out_dir)
    out_dir.mkdir(parents=True, exist_ok=True)
    csv_path = out_dir / "daily_user_scores.csv"
    sqlite_path = out_dir / "daily_user_scores.sqlite"
    contract.to_csv(csv_path, index=False)
    try:
        import sqlite3

        with sqlite3.connect(sqlite_path) as conn:
            contract.to_sql("daily_user_scores", conn, if_exists="replace", index=False)
    except Exception:
        pass
    return csv_path


def main() -> None:
    import argparse

    parser = argparse.ArgumentParser(description="Person 2 — publish daily_user_scores (Contract A)")
    parser.add_argument(
        "--data-dir",
        type=Path,
        default=Path("backend/data/cert_r4.2"),
        help="CERT r4.2 folder (logon/file/email/http/device csv + LDAP/)",
    )
    parser.add_argument(
        "--out-dir",
        type=Path,
        default=Path("backend/output"),
    )
    parser.add_argument(
        "--sample",
        action="store_true",
        help="Generate CERT-shaped sample logs (use until real r4.2 is available)",
    )
    args = parser.parse_args()
    # Real CERT: unzip r4.2 into backend/data/cert_r4.2 (logs + LDAP/) then
    # python -m backend --data-dir backend/data/cert_r4.2

    if args.sample or not args.data_dir.exists():
        sample_dir = Path("backend/data/sample_cert")
        print(f"Writing CERT-shaped sample logs to {sample_dir}")
        write_sample_cert(sample_dir)
        data_dir = sample_dir
    else:
        data_dir = args.data_dir

    path = run_person2(data_dir, args.out_dir)
    print(f"Published Contract A → {path}")
    preview = pd.read_csv(path)
    print(f"Rows: {len(preview)}  users: {preview['user_id'].nunique()}  days: {preview['date'].nunique()}")
    print(preview.sort_values("peer_score", ascending=False).head(8).to_string(index=False))


if __name__ == "__main__":
    main()
