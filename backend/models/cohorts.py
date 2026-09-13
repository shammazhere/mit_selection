"""Role, manager, and department cohorts. Contract A fallback is department."""

from __future__ import annotations

import pandas as pd

MIN_COHORT_SIZE = 5
CONTRACT_COHORT_ROLE = "role"
CONTRACT_COHORT_DEPT = "department"
PEER_ROLE_MANAGER = "role_manager"
PEER_ROLE = "role"
PEER_DEPT = "department"


def attach_cohorts(
    user_days: pd.DataFrame,
    ldap: pd.DataFrame,
    min_cohort_size: int = MIN_COHORT_SIZE,
) -> pd.DataFrame:
    meta = ldap[["user_id", "role", "department", "team", "manager_id"]].drop_duplicates("user_id")
    df = user_days.merge(meta, on="user_id", how="left")
    for col in ("role", "department", "team", "manager_id"):
        df[col] = df[col].fillna("Unknown").astype(str)

    people = df.drop_duplicates("user_id")
    people = people.assign(role_manager=people["role"] + "|" + people["manager_id"])
    rm_sizes = people.groupby("role_manager")["user_id"].nunique()
    role_sizes = people.groupby("role")["user_id"].nunique()
    mgr_sizes = people.groupby("manager_id")["user_id"].nunique()
    dept_sizes = people.groupby("department")["user_id"].nunique()

    df["role_manager_key"] = df["role"] + "|" + df["manager_id"]
    df["role_manager_cohort_size"] = df["role_manager_key"].map(rm_sizes).fillna(1).astype(int)
    df["role_cohort_size"] = df["role"].map(role_sizes).fillna(1).astype(int)
    df["manager_cohort_size"] = df["manager_id"].map(mgr_sizes).fillna(1).astype(int)
    df["dept_cohort_size"] = df["department"].map(dept_sizes).fillna(1).astype(int)

    df["peer_group"] = PEER_DEPT
    df["cohort_used"] = CONTRACT_COHORT_DEPT
    df["fallback_applied"] = True
    df["cohort_size"] = df["dept_cohort_size"]

    use_role = df["role_cohort_size"] >= min_cohort_size
    df.loc[use_role, "peer_group"] = PEER_ROLE
    df.loc[use_role, "cohort_used"] = CONTRACT_COHORT_ROLE
    df.loc[use_role, "fallback_applied"] = False
    df.loc[use_role, "cohort_size"] = df.loc[use_role, "role_cohort_size"]

    use_rm = df["role_manager_cohort_size"] >= min_cohort_size
    df.loc[use_rm, "peer_group"] = PEER_ROLE_MANAGER
    df.loc[use_rm, "cohort_used"] = CONTRACT_COHORT_ROLE
    df.loc[use_rm, "fallback_applied"] = False
    df.loc[use_rm, "cohort_size"] = df.loc[use_rm, "role_manager_cohort_size"]
    return df
