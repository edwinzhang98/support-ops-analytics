"""Run the KPI SQL files (sql/01..09) and cache their results as parquet.

The SQL files hold the metric logic; this module only executes them, adds the
multiple-testing correction to the hotspot table and writes data/processed/kpi_*.parquet.
The same SQL is also run on the synthetic ticket table (suffix '_synth') to check
that the scale-up reproduces the real mix and SLA levels.
"""
from __future__ import annotations

import numpy as np
import pandas as pd
from scipy.stats import binomtest

from .config import processed_path
from .sql import run_sql_file

KPI_FILES = {
    "kpi_monthly": "01_kpi_monthly.sql",
    "kpi_by_dimension": "02_kpi_by_dimension.sql",
    "kpi_hotspots": "03_breach_hotspots.sql",
    "kpi_backlog_daily": "04_backlog_daily.sql",
    "kpi_agent_scorecard": "05_agent_scorecard.sql",
    "kpi_volume_heatmap": "06_volume_heatmap.sql",
    "kpi_topic_pareto": "07_topic_pareto.sql",
    "kpi_rca_decomposition": "08_rca_decomposition.sql",
    "kpi_load_vs_sla": "09_load_vs_sla.sql",
}


def benjamini_hochberg(p: np.ndarray) -> np.ndarray:
    """BH-adjusted p-values (q-values), monotone, capped at 1."""
    p = np.asarray(p, dtype=float)
    n = len(p)
    order = np.argsort(p)
    ranked = p[order] * n / np.arange(1, n + 1)
    q = np.minimum.accumulate(ranked[::-1])[::-1]
    out = np.empty(n)
    out[order] = np.minimum(q, 1.0)
    return out


def add_hotspot_significance(df: pd.DataFrame) -> pd.DataFrame:
    """One-sided binomial test (is this combination worse than overall?) + BH within SLA type.

    Combinations overlap and are tested against an overall rate that includes them,
    so p-values are approximate; the BH step guards against reading noise as a hotspot
    when ~1,000+ combinations are scanned.
    """
    df = df.copy()
    df["p_value"] = [
        binomtest(int(b), int(n), float(r), alternative="greater").pvalue
        for b, n, r in zip(df["breaches"], df["n"], df["overall_rate"])
    ]
    df["q_value"] = np.nan
    for s, idx in df.groupby("sla_type").groups.items():
        df.loc[idx, "q_value"] = benjamini_hochberg(df.loc[idx, "p_value"].to_numpy())
    df["significant_fdr5"] = df["q_value"] < 0.05
    return df


def build_kpis(fct_path: str | None = None, suffix: str = "") -> dict[str, pd.DataFrame]:
    variables = {"fct_tickets_path": fct_path} if fct_path else None
    out: dict[str, pd.DataFrame] = {}
    for name, sql_file in KPI_FILES.items():
        df = run_sql_file(sql_file, variables)
        if name == "kpi_hotspots":
            df = add_hotspot_significance(df)
        df.to_parquet(processed_path(f"{name}{suffix}.parquet"), index=False)
        out[name] = df
    return out
