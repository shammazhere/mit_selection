"""Per-user Isolation Forest self-baseline → self_score in [0, 1]."""

from __future__ import annotations

import numpy as np
import pandas as pd
from sklearn.ensemble import IsolationForest

from backend.ingestion.user_day import FEATURE_COLUMNS

RNG = 16


def _scale_anomaly(raw: np.ndarray, dec: np.ndarray | None = None) -> np.ndarray:
    """Map IsolationForest scores to [0, 1] anomalous.
    
    If decision_function is provided:
      dec >= 0 -> inlier (score 0)
      dec < 0 -> anomaly (score scaled proportionally up to 1.0)
    Otherwise falls back to score_samples scaling.
    """
    if dec is not None:
        # Values with dec >= 0 are considered normal inliers
        # Values with dec < 0 are outliers; scale smoothly to [0, 1]
        anomaly = np.where(dec < 0, -dec, 0.0)
        max_val = np.max(anomaly)
        if max_val < 1e-6:
            return np.zeros_like(raw)
        # Scale with a reference scale of 0.10 (standard IF outlier depth)
        scaled = anomaly / max(0.10, max_val * 0.8)
        return np.clip(scaled, 0.0, 1.0)

    anomaly = -raw
    lo, hi = np.quantile(anomaly, 0.05), np.quantile(anomaly, 0.95)
    if hi - lo < 1e-9:
        return np.zeros_like(anomaly)
    scaled = (anomaly - lo) / (hi - lo)
    return np.clip(scaled, 0.0, 1.0)


def score_self_baseline(user_days: pd.DataFrame) -> pd.DataFrame:
    df = user_days.copy()
    df["self_score"] = 0.0
    features = [c for c in FEATURE_COLUMNS if c in df.columns]

    for user_id, grp in df.groupby("user_id"):
        idx = grp.index
        x = grp[features].to_numpy(dtype=float)
        if len(grp) < 8:
            continue
        model = IsolationForest(
            n_estimators=100,
            contamination="auto",
            random_state=RNG,
        )
        model.fit(x)
        raw = model.score_samples(x)
        dec = model.decision_function(x)
        df.loc[idx, "self_score"] = _scale_anomaly(raw, dec)

    return df
