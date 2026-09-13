"""Join CERT logs into one user-day activity table."""

from __future__ import annotations

import pandas as pd

FEATURE_COLUMNS = [
    "logon_count",
    "after_hours_logons",
    "mean_logon_hour",
    "unique_pcs",
    "file_events",
    "removable_media_events",
    "email_count",
    "external_emails",
    "email_size",
    "http_count",
    "http_uploads",
    "usb_events",
]


def _day(ts: pd.Series) -> pd.Series:
    return pd.to_datetime(ts).dt.normalize()


def _hours(ts: pd.Series) -> pd.Series:
    return pd.to_datetime(ts).dt.hour


def _safe_groupby_size(df: pd.DataFrame, cols: list[str]) -> pd.DataFrame:
    if df.empty:
        return pd.DataFrame(columns=cols + ["count"])
    out = df.groupby(cols).size().reset_index(name="count")
    return out


def build_user_days(tables: dict[str, pd.DataFrame]) -> pd.DataFrame:
    frames = []

    logon = tables["logon"].copy()
    if not logon.empty:
        logon["day"] = _day(logon["date"])
        logon["hour"] = _hours(logon["date"])
        activity = logon.get("activity", pd.Series("Logon", index=logon.index)).astype(str)
        is_logon = activity.str.lower().str.contains("logon")
        on = logon.loc[is_logon]
        grp = on.groupby(["user_id", "day"], dropna=False)
        logon_feat = grp.agg(
            logon_count=("user_id", "size"),
            mean_logon_hour=("hour", "mean"),
            unique_pcs=("pc", "nunique") if "pc" in on.columns else ("user_id", "size"),
        ).reset_index()
        after = on.loc[(on["hour"] < 7) | (on["hour"] >= 20)]
        after_counts = _safe_groupby_size(after, ["user_id", "day"]).rename(
            columns={"count": "after_hours_logons"}
        )
        logon_feat = logon_feat.merge(after_counts, on=["user_id", "day"], how="left")
        frames.append(logon_feat)

    files = tables["file"].copy()
    if not files.empty:
        files["day"] = _day(files["date"])
        file_feat = files.groupby(["user_id", "day"]).size().reset_index(name="file_events")
        removable = pd.Series(False, index=files.index)
        for col in ("to_removable_media", "from_removable_media"):
            if col in files.columns:
                removable = removable | files[col].astype(str).str.lower().isin(
                    ("true", "1", "yes")
                )
        rem = files.loc[removable]
        rem_counts = _safe_groupby_size(rem, ["user_id", "day"]).rename(
            columns={"count": "removable_media_events"}
        )
        file_feat = file_feat.merge(rem_counts, on=["user_id", "day"], how="left")
        frames.append(file_feat)

    email = tables["email"].copy()
    if not email.empty:
        email["day"] = _day(email["date"])
        email_feat = email.groupby(["user_id", "day"]).agg(
            email_count=("user_id", "size"),
            email_size=("size", "sum") if "size" in email.columns else ("user_id", "size"),
        ).reset_index()
        domain = None
        if "from" in email.columns:
            domain = email["from"].astype(str).str.extract(r"@([^>;,\s]+)", expand=False)
        recipients = email["to"].astype(str) if "to" in email.columns else pd.Series("", index=email.index)
        if domain is not None:
            external = []
            for rec, dom in zip(recipients.fillna(""), domain.fillna("")):
                rec_l = rec.lower()
                external.append(bool(dom) and dom.lower() not in rec_l)
            email = email.assign(_external=external)
            ext_counts = (
                email.loc[email["_external"]]
                .groupby(["user_id", "day"])
                .size()
                .reset_index(name="external_emails")
            )
            email_feat = email_feat.merge(ext_counts, on=["user_id", "day"], how="left")
        frames.append(email_feat)

    http = tables["http"].copy()
    if not http.empty:
        http["day"] = _day(http["date"])
        http_feat = http.groupby(["user_id", "day"]).size().reset_index(name="http_count")
        activity = http["activity"].astype(str).str.lower() if "activity" in http.columns else ""
        url = http["url"].astype(str).str.lower() if "url" in http.columns else ""
        upload = pd.Series(False, index=http.index)
        if isinstance(activity, pd.Series):
            upload = upload | activity.str.contains("upload", na=False)
        if isinstance(url, pd.Series):
            upload = upload | url.str.contains(
                r"dropbox|drive\.google|wetransfer|mail\.yahoo|gmail", na=False
            )
        up_counts = _safe_groupby_size(http.loc[upload], ["user_id", "day"]).rename(
            columns={"count": "http_uploads"}
        )
        http_feat = http_feat.merge(up_counts, on=["user_id", "day"], how="left")
        frames.append(http_feat)

    device = tables["device"].copy()
    if not device.empty:
        device["day"] = _day(device["date"])
        activity = device.get("activity", pd.Series("Connect", index=device.index)).astype(str)
        connects = device.loc[activity.str.lower().str.contains("connect")]
        usb = _safe_groupby_size(connects, ["user_id", "day"]).rename(
            columns={"count": "usb_events"}
        )
        frames.append(usb)

    if not frames:
        raise ValueError("No CERT activity rows to join")

    user_days = frames[0]
    for extra in frames[1:]:
        user_days = user_days.merge(extra, on=["user_id", "day"], how="outer")

    for col in FEATURE_COLUMNS:
        if col not in user_days.columns:
            user_days[col] = 0.0
        user_days[col] = user_days[col].fillna(0.0)

    user_days["user_id"] = user_days["user_id"].astype(str)
    user_days["day"] = pd.to_datetime(user_days["day"]).dt.normalize()
    return user_days.sort_values(["user_id", "day"]).reset_index(drop=True)


def build_user_days_from_dir(data_dir) -> pd.DataFrame:
    """Chunked join so full CERT r4.2 (multi-GB HTTP) does not need to sit in RAM."""
    from backend.ingestion.cert_loader import cert_paths, iter_activity, load_ldap

    paths = cert_paths(data_dir)
    parts = []
    for stem, builder in (
        ("logon", _logon_features),
        ("file", _file_features),
        ("email", _email_features),
        ("http", _http_features),
        ("device", _device_features),
    ):
        chunks = []
        for chunk in iter_activity(paths[stem]):
            feat = builder(chunk)
            if feat is not None and not feat.empty:
                chunks.append(feat)
        if chunks:
            parts.append(_collapse_partials(pd.concat(chunks, ignore_index=True)))
    if not parts:
        raise ValueError("No CERT activity rows to join")
    user_days = parts[0]
    for extra in parts[1:]:
        user_days = user_days.merge(extra, on=["user_id", "day"], how="outer")
    for col in FEATURE_COLUMNS:
        if col not in user_days.columns:
            user_days[col] = 0.0
        user_days[col] = user_days[col].fillna(0.0)
    user_days["user_id"] = user_days["user_id"].astype(str)
    user_days["day"] = pd.to_datetime(user_days["day"]).dt.normalize()
    _ = load_ldap  # imported for callers that want ldap alongside
    return user_days.sort_values(["user_id", "day"]).reset_index(drop=True)


def _collapse_partials(df: pd.DataFrame) -> pd.DataFrame:
    if df.empty:
        return df
    sum_cols = [c for c in df.columns if c not in ("user_id", "day", "mean_logon_hour")]
    agg = {c: "sum" for c in sum_cols}
    if "mean_logon_hour" in df.columns:
        agg["mean_logon_hour"] = "mean"
    return df.groupby(["user_id", "day"], as_index=False).agg(agg)


def _logon_features(logon: pd.DataFrame) -> pd.DataFrame:
    return build_user_days({"logon": logon, "file": logon.iloc[0:0], "email": logon.iloc[0:0], "http": logon.iloc[0:0], "device": logon.iloc[0:0]})[
        ["user_id", "day"] + [c for c in ("logon_count", "after_hours_logons", "mean_logon_hour", "unique_pcs") if True]
    ]


def _file_features(files: pd.DataFrame) -> pd.DataFrame:
    out = build_user_days({"file": files, "logon": files.iloc[0:0], "email": files.iloc[0:0], "http": files.iloc[0:0], "device": files.iloc[0:0]})
    return out[["user_id", "day", "file_events", "removable_media_events"]]


def _email_features(email: pd.DataFrame) -> pd.DataFrame:
    out = build_user_days({"email": email, "logon": email.iloc[0:0], "file": email.iloc[0:0], "http": email.iloc[0:0], "device": email.iloc[0:0]})
    return out[["user_id", "day", "email_count", "external_emails", "email_size"]]


def _http_features(http: pd.DataFrame) -> pd.DataFrame:
    out = build_user_days({"http": http, "logon": http.iloc[0:0], "file": http.iloc[0:0], "email": http.iloc[0:0], "device": http.iloc[0:0]})
    return out[["user_id", "day", "http_count", "http_uploads"]]


def _device_features(device: pd.DataFrame) -> pd.DataFrame:
    out = build_user_days({"device": device, "logon": device.iloc[0:0], "file": device.iloc[0:0], "email": device.iloc[0:0], "http": device.iloc[0:0]})
    return out[["user_id", "day", "usb_events"]]
