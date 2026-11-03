"""Build and load the cleaned ticket table and data-quality results.

Pipeline step 1: raw CSV -> sql/00_fct_tickets.sql -> data/processed/fct_tickets.parquet
Pipeline step 2: sql/90_data_quality_checks.sql (+ a file line count) -> dq_checks.parquet
"""
from __future__ import annotations

from pathlib import Path

import pandas as pd

from .config import load_config, processed_path
from .sql import run_sql_file


def build_fct_tickets() -> pd.DataFrame:
    raw = Path(load_config()["data"]["raw_csv"])
    if not raw.exists():
        raise FileNotFoundError(
            f"Raw export not found at {raw}. Set data.raw_csv in config.yaml "
            "or SUPPORT_TICKETS_CSV in a .env file (see README)."
        )
    df = run_sql_file("00_fct_tickets.sql")
    df.to_parquet(processed_path("fct_tickets.parquet"), index=False)
    return df


def run_quality_checks() -> pd.DataFrame:
    dq = run_sql_file("90_data_quality_checks.sql")
    # Line count of the file itself (header + one line per ticket): no SQL needed
    raw = Path(load_config()["data"]["raw_csv"])
    with open(raw, "rb") as fh:
        n_lines = sum(1 for _ in fh)
    extra = pd.DataFrame([{
        "check_id": 0, "area": "Reconciliation",
        "check_name": "Data lines in the CSV file (excluding header)",
        "observed": float(n_lines - 1), "expected": float(dq.loc[dq.check_id == 1, "observed"].iloc[0]),
        "status": None, "action_taken": "File lines reconcile with rows parsed by DuckDB",
    }])
    extra["status"] = ["PASS" if extra.observed.iloc[0] == extra.expected.iloc[0] else "FLAG"]
    dq = pd.concat([extra, dq], ignore_index=True)
    dq.to_parquet(processed_path("dq_checks.parquet"), index=False)
    return dq


def load_tickets() -> pd.DataFrame:
    """Cleaned real tickets (one row per ticket)."""
    return pd.read_parquet(processed_path("fct_tickets.parquet"))


def load_processed(name: str) -> pd.DataFrame:
    """Any cached table in data/processed, by file stem (e.g. 'kpi_monthly')."""
    return pd.read_parquet(processed_path(f"{name}.parquet"))
