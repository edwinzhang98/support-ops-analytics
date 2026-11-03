"""What-if recalculations used by the dashboard's interactive controls.

Kept here (not in the page code) so the logic is testable and identical to the pipeline:
every function re-uses the same requirement / roster / costing code as the batch run.
"""
from __future__ import annotations

import numpy as np
import pandas as pd

from .roster import coverage_from_shifts, fte_from_shifts, optimize_min_shifts
from .sql import run_sql_file
from .staffing import requirement


def staffing_whatif(demand: pd.DataFrame, st: dict, today_scheduled: np.ndarray, *,
                    sl_goal: float, max_occupancy: float, shrinkage: float, aht_factor: float = 1.0,
                    volume_factor: float = 1.0, live_target_min: float | None = None) -> dict:
    """Recompute the hourly requirement and the cheapest demand-shaped roster for new assumptions,
    and compare with today's (assumed) roster."""
    st2 = {**st}
    if live_target_min is not None:
        st2["live_target_min"] = live_target_min
    req = requirement(demand, st2, sl_goal=sl_goal, max_occupancy=max_occupancy, shrinkage=shrinkage,
                      aht_factor=aht_factor, volume_factor=volume_factor)
    shifts = optimize_min_shifts(req["scheduled_required"].to_numpy(), st["shift_starts"])
    n_shifts = int(shifts["agents"].sum())
    req = req.assign(scheduled_proposed=coverage_from_shifts(shifts),
                     scheduled_today=np.asarray(today_scheduled, float))
    short = req["scheduled_today"] < req["scheduled_required"]
    return {
        "requirement": req,
        "shifts": shifts,
        "fte_needed": fte_from_shifts(n_shifts, st["shifts_per_fte_week"]),
        "weekly_shifts": n_shifts,
        "hours_today_short": int(short.sum()),
        "agent_hours_short_today": float((req["scheduled_required"] - req["scheduled_today"]).clip(lower=0).sum()),
        "peak_required": int(req["scheduled_required"].max()),
        "min_required": int(req["scheduled_required"].min()),
    }


def deflection_whatif(profile: pd.DataFrame, work_by_topic: pd.Series, demand: pd.DataFrame, st: dict,
                      rates: dict[str, float]) -> dict:
    """Deflection rates per topic -> tickets and agent-hours removed -> FTE needed afterwards.

    Topics are spread evenly over the week in the synthetic data (attributes are drawn
    independently of time), so removing x% of the workload scales every hour's demand by (1 - x).
    """
    t = profile.set_index("topic")
    rate = pd.Series(rates).reindex(t.index).fillna(0.0)
    tickets_removed = (t["tickets"] * rate).sum()
    hours = work_by_topic.reindex(t.index).fillna(0.0)
    hours_saved = float((hours * rate).sum())
    reduction = hours_saved / float(hours.sum())
    base = requirement(demand, st)
    after = requirement(demand, st, volume_factor=1 - reduction)
    fte_before = fte_from_shifts(int(optimize_min_shifts(base["scheduled_required"].to_numpy(),
                                                         st["shift_starts"])["agents"].sum()))
    fte_after = fte_from_shifts(int(optimize_min_shifts(after["scheduled_required"].to_numpy(),
                                                        st["shift_starts"])["agents"].sum()))
    by_topic = pd.DataFrame({"topic": t.index, "tickets_2023": t["tickets"].to_numpy(),
                             "deflection_rate": rate.to_numpy(),
                             "tickets_deflected_2023": (t["tickets"] * rate).to_numpy(),
                             "agent_hours_saved_week": (hours * rate).to_numpy()})
    return {"by_topic": by_topic, "deflected_share": tickets_removed / t["tickets"].sum(),
            "hours_saved_week": hours_saved, "workload_reduction": reduction,
            "fte_before": fte_before, "fte_after": fte_after}


def costed_options(opts: pd.DataFrame, fte_annual_eur: float, hire_one_off_eur: float,
                   automation_one_off_eur: float, automation_annual_eur: float,
                   alert_uplift_pp: float) -> pd.DataFrame:
    """Re-price the options with new cost assumptions (SLA effects come from the simulation)."""
    o = opts.copy()
    extra_fte = (o["fte"] - o.loc[o["option"] == "0. Status quo", "fte"].iloc[0]).clip(lower=0)
    is_auto = o["option"].isin(["C. Automate", "B + C"])
    o["one_off_cost_eur"] = extra_fte * hire_one_off_eur + is_auto * automation_one_off_eur
    o["annual_cost_change_eur"] = extra_fte * fte_annual_eur + is_auto * automation_annual_eur
    o["first_year_cost_eur"] = o["one_off_cost_eur"] + o["annual_cost_change_eur"]
    o["response_sl_with_email_alert"] = o["response_sl"] + alert_uplift_pp / 100
    return o


def backlog_with_threshold(aged_days: float) -> pd.DataFrame:
    """Daily backlog split re-run in SQL with a different 'aged' threshold."""
    return run_sql_file("04_backlog_daily.sql", {"aged_backlog_days": str(aged_days)})


def heatmap_filtered(fct: pd.DataFrame, channels: list[str] | None = None,
                     topics: list[str] | None = None) -> pd.DataFrame:
    """Weekday x hour average tickets per week for a filtered slice of the real export."""
    f = fct
    if channels:
        f = f[f["channel"].isin(channels)]
    if topics:
        f = f[f["topic"].isin(topics)]
    days = pd.Series(pd.date_range(fct["created_date"].min(), fct["created_date"].max()))
    n_days = days.dt.day_of_week.value_counts().sort_index()          # 0 = Mon
    grid = pd.MultiIndex.from_product([range(1, 8), range(24)], names=["dow", "hour"])
    cnt = f.groupby(["created_dow", "created_hour"]).size().reindex(grid, fill_value=0).rename("tickets")
    out = cnt.reset_index()
    out["dow_name"] = out["dow"].map(dict(enumerate(["Mon", "Tue", "Wed", "Thu", "Fri", "Sat", "Sun"], 1)))
    out["tickets_per_week"] = out["tickets"] / out["dow"].map(lambda d: n_days[d - 1])
    return out


def email_alert_sl(now: float, email_breaches: int, evaluable: int, catch_rate: float) -> float:
    return now + email_breaches * catch_rate / evaluable
