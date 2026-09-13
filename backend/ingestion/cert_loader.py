"""Load CERT r4.2 (or CERT-shaped) log files from a directory."""

from __future__ import annotations

from pathlib import Path

import pandas as pd

ACTIVITY_STEMS = ("logon", "file", "email", "http", "device")

DATE_FORMATS = (
    "%m/%d/%Y %H:%M:%S",
    "%Y-%m-%d %H:%M:%S",
    "%Y-%m-%d",
    "%m/%d/%Y",
)


def find_activity_file(data_dir: Path, stem: str) -> Path:
    matches = list(data_dir.rglob(f"{stem}.csv")) + list(data_dir.rglob(f"{stem}.CSV"))
    matches = [p for p in matches if "ldap" not in str(p).lower()]
    if not matches:
        raise FileNotFoundError(
            f"No {stem}.csv under {data_dir}. Unzip CERT r4.2 so it contains {stem}.csv."
        )
    return sorted(matches, key=lambda p: (len(p.parts), str(p)))[0]


def find_ldap_files(data_dir: Path) -> list[Path]:
    ldap_dirs = [p for p in data_dir.rglob("*") if p.is_dir() and p.name.lower() == "ldap"]
    files: list[Path] = []
    for folder in ldap_dirs:
        files.extend(folder.glob("*.csv"))
        files.extend(folder.glob("*.CSV"))
    files += list(data_dir.glob("ldap.csv")) + list(data_dir.glob("LDAP.csv"))
    files = sorted(set(files), key=lambda p: p.name)
    if not files:
        raise FileNotFoundError(
            f"No LDAP files under {data_dir}. CERT r4.2 uses an LDAP/ folder of monthly CSVs."
        )
    return files


def parse_dates(series: pd.Series) -> pd.Series:
    parsed = pd.to_datetime(series, errors="coerce")
    if parsed.notna().mean() > 0.8:
        return parsed
    for fmt in DATE_FORMATS:
        parsed = pd.to_datetime(series, format=fmt, errors="coerce")
        if parsed.notna().mean() > 0.8:
            return parsed
    return pd.to_datetime(series, errors="coerce")


def normalize_activity(df: pd.DataFrame) -> pd.DataFrame:
    df = df.copy()
    df.columns = [c.strip().lower() for c in df.columns]
    if "date" in df.columns:
        df["date"] = parse_dates(df["date"])
    if "user" in df.columns and "user_id" not in df.columns:
        df["user_id"] = df["user"].astype(str)
    elif "user_id" in df.columns:
        df["user_id"] = df["user_id"].astype(str)
    if "attachment_count" in df.columns and "attachments" not in df.columns:
        df["attachments"] = df["attachment_count"]
    return df


def normalize_ldap(df: pd.DataFrame) -> pd.DataFrame:
    df = df.copy()
    df.columns = [c.strip().lower() for c in df.columns]
    rename = {
        "employee_name": "name",
        "userid": "user_id",
        "user": "user_id",
        "supervisor": "manager_id",
        "supervisor_id": "manager_id",
        "projects": "team",
    }
    for src, dest in rename.items():
        if src in df.columns and dest not in df.columns:
            df = df.rename(columns={src: dest})
    if "user_id" not in df.columns:
        raise ValueError(f"LDAP file needs a user id column; got {list(df.columns)}")
    df["user_id"] = df["user_id"].astype(str)
    if "department" not in df.columns:
        if "functional_unit" in df.columns:
            df["department"] = df["functional_unit"]
        elif "business_unit" in df.columns:
            df["department"] = df["business_unit"]
        else:
            df["department"] = "Unknown"
    for col, default in (
        ("role", "Unknown"),
        ("department", "Unknown"),
        ("team", "Unknown"),
        ("manager_id", "Unknown"),
    ):
        if col not in df.columns:
            df[col] = default
        df[col] = df[col].fillna(default).astype(str)
    keep = ["user_id", "role", "department", "team", "manager_id"]
    if "name" in df.columns:
        keep.append("name")
    return df[keep]


def load_ldap(data_dir: Path) -> pd.DataFrame:
    frames = [normalize_ldap(pd.read_csv(path)) for path in find_ldap_files(data_dir)]
    ldap = pd.concat(frames, ignore_index=True)
    return ldap.drop_duplicates("user_id", keep="last")


def iter_activity(path: Path, chunksize: int = 400_000):
    for chunk in pd.read_csv(path, chunksize=chunksize):
        yield normalize_activity(chunk)


def load_cert_bundle(data_dir: str | Path) -> dict[str, pd.DataFrame]:
    """In-memory load for sample/small dumps. Real r4.2 HTTP logs should use chunked join."""
    data_dir = Path(data_dir)
    tables = {stem: normalize_activity(pd.read_csv(find_activity_file(data_dir, stem))) for stem in ACTIVITY_STEMS}
    tables["ldap"] = load_ldap(data_dir)
    return tables


def cert_paths(data_dir: str | Path) -> dict[str, Path | list[Path]]:
    data_dir = Path(data_dir)
    paths: dict[str, Path | list[Path]] = {
        stem: find_activity_file(data_dir, stem) for stem in ACTIVITY_STEMS
    }
    paths["ldap"] = find_ldap_files(data_dir)
    return paths
