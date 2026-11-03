"""Run the SQL files in sql/ with DuckDB.

Each SQL file is standalone: it reads its inputs through DuckDB variables with a
default (e.g. `coalesce(getvariable('fct_tickets_path'), 'data/processed/fct_tickets.parquet')`),
so it can be run from the repo root with no setup. This module sets the variables
to absolute paths so the files also work from notebooks and the dashboard.

Usage from the command line (prints the result):
    python -m support_ops.sql sql/01_kpi_monthly.sql
"""
from __future__ import annotations

import sys
from pathlib import Path

import duckdb
import pandas as pd

from .config import SQL_DIR, load_config, processed_path


def default_variables() -> dict[str, str]:
    cfg = load_config()
    return {
        "raw_csv_path": cfg["data"]["raw_csv"],
        "fct_tickets_path": str(processed_path("fct_tickets.parquet")),
        "goal_attainment": str(cfg["sla"]["goal_attainment"]),
        "aged_backlog_days": str(cfg["sla"]["aged_backlog_days"]),
    }


def connect(variables: dict[str, str] | None = None) -> duckdb.DuckDBPyConnection:
    con = duckdb.connect()
    for k, v in {**default_variables(), **(variables or {})}.items():
        con.execute(f"SET VARIABLE {k} = ?", [v])
    return con


def run_sql_file(name: str | Path, variables: dict[str, str] | None = None) -> pd.DataFrame:
    """Execute one SQL file and return the result of its final SELECT."""
    path = Path(name)
    if not path.is_absolute() and not path.exists():
        path = SQL_DIR / path.name
    con = connect(variables)
    try:
        return con.execute(path.read_text()).df()
    finally:
        con.close()


if __name__ == "__main__":
    pd.set_option("display.width", 200)
    pd.set_option("display.max_columns", 30)
    for f in sys.argv[1:]:
        print(f"-- {f}")
        print(run_sql_file(f).to_string(max_rows=60))
