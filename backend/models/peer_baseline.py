"""Peer-cohort z-score → peer_score in [0, 1]."""

from __future__ import annotations

import numpy as np
import pandas as pd

from backend.ingestion.user_day import FEATURE_COLUMNS
from backend.models.cohorts import PEER_DEPT, PEER_ROLE_MANAGER


def _z_to_unit(max_abs_z: float) -> float:
    return float(np.clip(1.0 - np.exp(-max_abs_z / 2.0), 0.0, 1.0))


def _max_abs_z(row_features: np.ndarray, pool: np.ndarray) -> float:
    if pool.shape[0] <= 1:
        return 0.0
    mean = pool.mean(axis=0)
    std = pool.std(axis=0, ddof=1)
    std = np.where(std < 1e-9, 1.0, std)
    return float(np.max(np.abs((row_features - mean) / std)))


def _mask_pool(group: str, i: int, roles, managers, depts) -> np.ndarray:
    if group == PEER_DEPT:
        return depts == depts[i]
    if group == PEER_ROLE_MANAGER:
        return (roles == roles[i]) & (managers == managers[i])
    return roles == roles[i]


def score_peer_cohort(user_days: pd.DataFrame) -> pd.DataFrame:
    df = user_days.copy()
    features = [c for c in FEATURE_COLUMNS if c in df.columns]
    df["peer_score"] = 0.0

    # Pre-calculate overall cohort statistics across all member-days
    # This prevents single-active-user days (e.g. weekends) from returning 0.0
    cohort_stats: dict[tuple, tuple[np.ndarray, np.ndarray]] = {}
    for (group, role, mgr, dept), grp in df.groupby(["peer_group", "role", "manager_id", "department"], dropna=False):
        mat = grp[features].to_numpy(dtype=float)
        mean = mat.mean(axis=0)
        std = mat.std(axis=0, ddof=1) if len(mat) > 1 else np.ones(mat.shape[1])
        std = np.where(std < 1e-9, 1.0, std)
        cohort_stats[(group, role, mgr, dept)] = (mean, std)

    for _, day_grp in df.groupby("day", dropna=False):
        feature_mat = day_grp[features].to_numpy(dtype=float)
        roles = day_grp["role"].to_numpy()
        managers = day_grp["manager_id"].to_numpy()
        depts = day_grp["department"].to_numpy()
        groups = day_grp["peer_group"].to_numpy()
        labels = day_grp.index

        for i, idx in enumerate(labels):
            row_feat = feature_mat[i]
            pool = feature_mat[_mask_pool(groups[i], i, roles, managers, depts)]
            same_day_z = _max_abs_z(row_feat, pool)

            # Compare against cohort baseline distribution as well
            key = (groups[i], roles[i], managers[i], depts[i])
            if key in cohort_stats:
                c_mean, c_std = cohort_stats[key]
                cohort_z = float(np.max(np.abs((row_feat - c_mean) / c_std)))
            else:
                cohort_z = 0.0

            eff_z = max(same_day_z, cohort_z)
            df.at[idx, "peer_score"] = _z_to_unit(eff_z)

    return df
