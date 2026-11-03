"""Root-cause tests on the REAL export (2,330 tickets).

Question: is the SLA decline caused by volume, by efficiency, or by a schedule mismatch?
Each function returns a small table plus the numbers quoted in the docs.
"""
from __future__ import annotations

import numpy as np
import pandas as pd
from scipy import stats


def corr_ci(x, y, method: str = "spearman") -> dict:
    """Correlation with a 95% CI (Fisher z)."""
    x, y = np.asarray(x, float), np.asarray(y, float)
    m = np.isfinite(x) & np.isfinite(y)
    x, y = x[m], y[m]
    r, p = (stats.spearmanr(x, y) if method == "spearman" else stats.pearsonr(x, y))[:2]
    z, se = np.arctanh(r), 1 / np.sqrt(len(x) - 3)
    return {"r": float(r), "lo": float(np.tanh(z - 1.96 * se)), "hi": float(np.tanh(z + 1.96 * se)),
            "p": float(p), "n": int(len(x))}


def _wilson(x: float, n: float) -> tuple[float, float]:
    if n == 0:
        return (np.nan, np.nan)
    p, z = x / n, 1.96
    c = (p + z * z / (2 * n)) / (1 + z * z / n)
    h = z * np.sqrt(p * (1 - p) / n + z * z / (4 * n * n)) / (1 + z * z / n)
    return (c - h, c + h)


def cochran_armitage(x: np.ndarray, n: np.ndarray, scores: np.ndarray | None = None) -> float:
    """Two-sided p-value of the Cochran-Armitage test for a trend in proportions."""
    x, n = np.asarray(x, float), np.asarray(n, float)
    s = np.arange(len(n), dtype=float) if scores is None else np.asarray(scores, float)
    pbar = x.sum() / n.sum()
    sbar = (n * s).sum() / n.sum()
    t = (x * (s - sbar)).sum()
    var = pbar * (1 - pbar) * (n * (s - sbar) ** 2).sum()
    return float(2 * stats.norm.sf(abs(t / np.sqrt(var))))


def workload_at_creation(fct: pd.DataFrame) -> pd.DataFrame:
    """Per ticket: tickets created the same day, and tickets in progress (created before,
    resolved after) when it arrived - the queue an agent would face."""
    out = fct[["ticket_id", "created_at", "created_date", "response_sla_met", "resolution_sla_met"]].copy()
    out["tickets_same_day"] = fct.groupby("created_date")["ticket_id"].transform("size").to_numpy()
    c = fct["created_at"].to_numpy()
    r = fct["resolved_at"].to_numpy()
    r_filled = np.where(pd.isna(r), np.datetime64("2100-01-01"), r).astype("datetime64[us]")
    in_prog = (c[None, :] < c[:, None]) & (r_filled[None, :] > c[:, None]) & ~pd.isna(r)[None, :]
    out["in_progress_at_arrival"] = in_prog.sum(axis=1)
    return out


def load_vs_sla(fct: pd.DataFrame, n_bins: int = 5) -> pd.DataFrame:
    """If capacity were short, tickets arriving into a busier desk should breach more.

    Ticket-level test: bin tickets by the load they arrived into (quintiles), compare
    breach rates, and test for a trend (Cochran-Armitage). Correlating DAILY breach
    rates with daily volume is avoided on purpose: on a 2-ticket day the breach rate
    is usually 0 by chance, which makes busier days look worse even at constant risk.
    """
    w = workload_at_creation(fct)
    jitter = np.random.default_rng(0).uniform(0, 1e-3, len(w))   # break ties at random, not by time order
    rows = []
    for load_col, load_label in [("tickets_same_day", "tickets created the same day"),
                                 ("in_progress_at_arrival", "tickets in progress at arrival")]:
        w["bin"] = pd.qcut((w[load_col] + jitter).rank(method="first"), n_bins, labels=False)
        for sla in ["response_sla_met", "resolution_sla_met"]:
            sub = w[w[sla].notna()]
            g = sub.groupby("bin").agg(n=(sla, "size"), met=(sla, "sum"),
                                       load_min=(load_col, "min"), load_max=(load_col, "max"))
            g["breaches"] = g["n"] - g["met"]
            p = cochran_armitage(g["breaches"].to_numpy(), g["n"].to_numpy())
            for b, r in g.iterrows():
                lo, hi = _wilson(r["breaches"], r["n"])
                rows.append({"load_measure": load_label, "sla": sla.replace("_sla_met", ""),
                             "quintile": int(b) + 1, "load_range": f"{int(r.load_min)}-{int(r.load_max)}",
                             "tickets": int(r["n"]), "breach_rate": r["breaches"] / r["n"],
                             "breach_rate_lo": lo, "breach_rate_hi": hi, "trend_p_value": p})
    return pd.DataFrame(rows)


def time_slot_tests(fct: pd.DataFrame) -> pd.DataFrame:
    rows = []
    for col, label in [("created_hour", "hour of day"), ("created_dow", "day of week"),
                       ("hour_band", "6-hour band"), ("is_weekend", "weekday vs weekend")]:
        for sla in ["response_sla_met", "resolution_sla_met"]:
            sub = fct[fct[sla].notna()]
            tab = pd.crosstab(sub[col], sub[sla])
            chi2, p, dof, _ = stats.chi2_contingency(tab)
            rows.append({"slot": label, "sla": sla.replace("_sla_met", ""), "chi2": chi2, "dof": dof,
                         "p_value": p})
    return pd.DataFrame(rows)


def breach_lateness(fct: pd.DataFrame) -> pd.DataFrame:
    """How late are response breaches? Minutes late = queueing; hours late = missed tickets."""
    b = fct[fct["response_sla_met"] == False].copy()  # noqa: E712
    b["minutes_late"] = b["frt_min"] - b["response_target_min"]
    out = b.groupby("channel").agg(
        breaches=("ticket_id", "size"),
        never_answered=("frt_min", lambda s: int(s.isna().sum())),
        median_minutes_late=("minutes_late", "median"),
        p25_minutes_late=("minutes_late", lambda s: s.quantile(0.25)),
        p75_minutes_late=("minutes_late", lambda s: s.quantile(0.75)),
        share_over_60_min_late=("minutes_late", lambda s: float((s > 60).mean())),
    )
    return out.reset_index()


def email_alert_lever(fct: pd.DataFrame, catch_rates=(0.25, 0.50, 0.75), alert_min: float = 45) -> dict:
    """Unanswered-email alert at 45 min. ASSUMPTION: a share of emails that would otherwise
    breach get answered by the 60-min deadline once the alert fires."""
    ev = fct[fct["response_sla_met"].notna()]
    email_breach = ev[(ev["channel"] == "Email") & (ev["response_sla_met"] == False)]  # noqa: E712
    n_ev, n_eb = len(ev), len(email_breach)
    base = ev["response_sla_met"].mean()
    rows = [{"catch_rate": c, "breaches_avoided": n_eb * c,
             "response_sl_after": base + n_eb * c / n_ev,
             "uplift_pp": 100 * n_eb * c / n_ev} for c in catch_rates]
    return {"table": pd.DataFrame(rows), "email_breaches": n_eb, "evaluable": n_ev,
            "response_sl_now": base, "base_uplift_pp": 100 * n_eb * 0.5 / n_ev, "alert_min": alert_min}


def changepoint(series: pd.Series) -> dict:
    """Single mean-shift changepoint (min SSE) and a flat-ramp-flat fit, on monthly values."""
    y = series.to_numpy(float)
    n = len(y)
    best = None
    for k in range(2, n - 1):
        sse = ((y[:k] - y[:k].mean()) ** 2).sum() + ((y[k:] - y[k:].mean()) ** 2).sum()
        if best is None or sse < best[0]:
            best = (sse, k)
    k = best[1]
    ramp = None
    x = np.arange(n)
    for a in range(0, n - 2):
        for b in range(a + 1, n):
            pred = np.interp(x, [a, b], [y[: a + 1].mean(), y[b:].mean()])
            sse = ((y - pred) ** 2).sum()
            if ramp is None or sse < ramp[0]:
                ramp = (sse, a, b)
    sst = ((y - y.mean()) ** 2).sum()
    return {"step_month_index": int(k), "step_month": str(series.index[k])[:7],
            "mean_before": float(y[:k].mean()), "mean_after": float(y[k:].mean()),
            "step_r2": float(1 - best[0] / sst),
            "ramp_start": str(series.index[ramp[1]])[:7], "ramp_end": str(series.index[ramp[2]])[:7],
            "ramp_r2": float(1 - ramp[0] / sst)}


def resolution_composition(monthly: pd.DataFrame) -> pd.DataFrame:
    m = monthly.copy()
    m["share_on_time"] = m["resolution_met"] / m["tickets"]
    m["share_resolved_late"] = m["resolved_late"] / m["tickets"]
    m["share_never_resolved"] = m["unresolved_overdue"] / m["tickets"]
    return m[["created_month", "tickets", "share_on_time", "share_resolved_late", "share_never_resolved"]]


def stale_backlog(fct: pd.DataFrame, backlog: pd.DataFrame, aged_days: float = 7) -> dict:
    never = fct[fct["resolution_outcome"] == "Unresolved, overdue"]
    breaches = (~fct["resolution_sla_met"]).sum()
    active = backlog["open_active"]
    # Little's law check: arrivals/day x average days a ticket counts as "active" (capped at the aged threshold)
    days_active = np.where(fct["is_resolved"], np.minimum(fct["resolution_h"] / 24, aged_days), aged_days)
    days_window = (fct["created_date"].max() - fct["created_date"].min()).days + 1
    littles = len(fct) / days_window * days_active.mean()      # arrivals per calendar day x days active
    return {
        "never_resolved": int(len(never)), "never_resolved_share": len(never) / len(fct),
        "never_resolved_share_of_breaches": len(never) / breaches,
        "never_resolved_median_age_days": float(never["age_at_snapshot_days"].median()),
        "never_resolved_age_p25_days": float(never["age_at_snapshot_days"].quantile(0.25)),
        "never_resolved_age_p75_days": float(never["age_at_snapshot_days"].quantile(0.75)),
        "never_resolved_by_status": never["status"].value_counts().to_dict(),
        "open_at_snapshot": int(backlog["open_total"].iloc[-1]),
        "aged_at_snapshot": int(backlog["open_aged"].iloc[-1]),
        "active_backlog_mean": float(active.mean()), "active_backlog_max": int(active.max()),
        "littles_law_expected_active": float(littles),
    }


def weekend_workload(fct: pd.DataFrame) -> dict:
    days = pd.Series(pd.date_range(fct["created_date"].min(), fct["created_date"].max())).dt.day_of_week
    n_days = days.value_counts().sort_index()

    def per_day(ts):
        c = ts.dropna().dt.day_of_week.value_counts().reindex(range(7), fill_value=0)
        return c / n_days

    cr, rs = per_day(fct["created_at"]), per_day(fct["resolved_at"])
    return {"created_weekend_to_weekday": float(cr[5:].mean() / cr[:5].mean()),
            "resolved_weekend_to_weekday": float(rs[5:].mean() / rs[:5].mean()),
            "created_per_day": cr.round(2).tolist(), "resolved_per_day": rs.round(2).tolist()}


def heterogeneity(fct: pd.DataFrame) -> pd.DataFrame:
    """Do agents / priorities / topics differ more than chance? (chi-square)"""
    rows = []
    for dim in ["agent_name", "priority", "topic", "channel", "agent_group", "product_group"]:
        for sla in ["response_sla_met", "resolution_sla_met"]:
            sub = fct[fct[sla].notna()]
            tab = pd.crosstab(sub[dim], sub[sla])
            chi2, p, dof, _ = stats.chi2_contingency(tab)
            rows.append({"dimension": dim, "sla": sla.replace("_sla_met", ""), "chi2": chi2,
                         "dof": dof, "p_value": p})
    return pd.DataFrame(rows)


def recovery_scenario(fct: pd.DataFrame) -> dict:
    """What on-time resolution would H2 have had with H1's late-resolution rate? (target, not forecast)"""
    h = fct.groupby("created_half")["resolution_outcome"].value_counts(normalize=True).unstack()
    late_h1, late_h2 = h.loc["H1", "Resolved late"], h.loc["H2", "Resolved late"]
    on_h2 = h.loc["H2", "Resolved within SLA"]
    return {"late_share_h1": float(late_h1), "late_share_h2": float(late_h2),
            "never_share_h1": float(h.loc["H1", "Unresolved, overdue"]),
            "never_share_h2": float(h.loc["H2", "Unresolved, overdue"]),
            "on_time_h1": float(h.loc["H1", "Resolved within SLA"]), "on_time_h2": float(on_h2),
            "on_time_h2_if_late_back_to_h1": float(on_h2 + (late_h2 - late_h1))}


def monthly_seasonality(fct: pd.DataFrame) -> dict:
    """Chi-square goodness of fit: monthly ticket counts vs counts expected from each month's weekday mix
    (weekday and weekend daily rates from the whole year; days in the export window only).
    Returns the p-value and a per-month table (observed, expected, z)."""
    days = pd.DataFrame({"date": pd.date_range(fct["created_date"].min(), fct["created_date"].max())})
    counts = fct.groupby("created_date").size()
    days["n"] = days["date"].map(counts).fillna(0)
    days["weekend"] = days["date"].dt.day_of_week >= 5
    days["exp"] = days["weekend"].map(days.groupby("weekend")["n"].mean())
    by_m = days.groupby(days["date"].dt.month)[["n", "exp"]].sum()
    by_m["exp"] = by_m["exp"] * by_m["n"].sum() / by_m["exp"].sum()
    by_m["z"] = (by_m["n"] - by_m["exp"]) / np.sqrt(by_m["exp"])
    by_m.index = [pd.Timestamp(2023, m, 1).strftime("%b") for m in by_m.index]
    table = by_m.rename(columns={"n": "observed", "exp": "expected"})
    return {"p": float(stats.chisquare(table["observed"], table["expected"]).pvalue), "table": table}


def monthly_seasonality_p(fct: pd.DataFrame) -> float:
    return monthly_seasonality(fct)["p"]
