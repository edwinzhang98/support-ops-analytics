"""Capacity plan for the scaled (synthetic) operation.

Steps
 1. demand_by_how      average arrivals and workload per hour of the week (168 slots)
 2. requirement        productive agents needed per slot (blended pool):
                         N = max( Erlang C agents so live contacts are answered within 2 min
                                  [live work interrupts email work, so it sees the whole pool],
                                  ceil(total workload / max occupancy),
                                  1 agent minimum for 24/7 coverage )
                       scheduled = ceil(N / (1 - shrinkage))   (people are whole: rounded once, here)
 3. rosters            workload-matched roster (integer program) vs three hypotheses for
                       today's roster with the SAME number of weekly shifts
 4. simulate           replay the synthetic year under each roster (support_ops.simulation)
 5. sensitivity        how the answer moves with each assumption

The response time a customer sees combines the real pickup delay (from the export) with the
queue wait (staffing). We bracket how the two combine: the LATER of the two (optimistic: waits and
slow pickups overlap) and the SUM (conservative: they add up). Staffing can only remove the queue part.
"""
from __future__ import annotations

import math

import numpy as np
import pandas as pd

from . import erlang
from .roster import (
    DAYS, HYPOTHESES, combine_shifts, coverage_from_shifts, extra_shifts_to_cover, fte_from_shifts,
    hypothesis_roster, optimize_fixed_budget, optimize_min_shifts, roster_table,
)
from .simulation import run_roster, summarize_response
from .synth import HOLIDAYS_2023, build_work_items

T0 = pd.Timestamp("2023-01-01")
N_HOURS = (365 + 7) * 24          # one synthetic year + a week for follow-ups to finish

ROSTER_LABELS = {
    "proposed": "Proposed: workload-matched roster (optimised)",
    "by_day": "Today (assumed): weekday-weighted, 3 equal shifts",
    "flat": "Today (alt.): flat 24/7",
    "business_hours": "Today (alt.): day-weighted",
}


# ---------------------------------------------------------------------------
# 1. Demand
# ---------------------------------------------------------------------------
def demand_by_how(items: pd.DataFrame, tickets: pd.DataFrame) -> pd.DataFrame:
    """Average arrivals per hour for each hour of the week, excluding holidays."""
    hol = pd.to_datetime(HOLIDAYS_2023)
    year_days = pd.date_range("2023-01-01", "2023-12-31", freq="D")
    open_days = year_days[~year_days.isin(hol)]
    n_days = pd.Series(open_days.day_of_week).value_counts().sort_index()   # 0 = Mon

    ts = T0 + pd.to_timedelta(items["arrival_s"], unit="s")
    keep = ts.dt.normalize().isin(open_days)
    it = items[keep.to_numpy()]
    ts = ts[keep]
    how = (ts.dt.day_of_week * 24 + ts.dt.hour).to_numpy()

    out = pd.DataFrame({"how": np.arange(168)})
    out["dow"] = out["how"] // 24
    out["dow_name"] = [DAYS[d] for d in out["dow"]]
    out["hour"] = out["how"] % 24
    denom = out["dow"].map(n_days).to_numpy()
    for pool in ("live", "async"):
        m = (it["pool"] == pool).to_numpy()
        cnt = np.bincount(how[m], minlength=168)
        out[f"{pool}_per_hour"] = cnt / denom
        out[f"aht_{pool}_min"] = it.loc[m, "service_s"].mean() / 60
    t_ts = tickets["created_at"]
    tk = t_ts.dt.normalize().isin(open_days).to_numpy()
    th = (t_ts[tk].dt.day_of_week * 24 + t_ts[tk].dt.hour).to_numpy()
    out["tickets_per_hour"] = np.bincount(th, minlength=168) / denom
    out["erlangs_live"] = out["live_per_hour"] * out["aht_live_min"] / 60
    out["erlangs_async"] = out["async_per_hour"] * out["aht_async_min"] / 60
    out["erlangs_total"] = out["erlangs_live"] + out["erlangs_async"]
    return out


# ---------------------------------------------------------------------------
# 2. Requirement
# ---------------------------------------------------------------------------
def requirement(demand: pd.DataFrame, st: dict, sl_goal: float | None = None,
                max_occupancy: float | None = None, shrinkage: float | None = None,
                volume_factor: float = 1.0, aht_factor: float = 1.0,
                model: str = "blended") -> pd.DataFrame:
    sl_goal = st["sl_goal"] if sl_goal is None else sl_goal
    max_occ = st["max_occupancy"] if max_occupancy is None else max_occupancy
    shrink = st["shrinkage"] if shrinkage is None else shrinkage
    min_agents = st["min_agents_per_pool"]
    rows = []
    for r in demand.itertuples():
        lam_l, lam_a = r.live_per_hour * volume_factor, r.async_per_hour * volume_factor
        aht_l, aht_a = r.aht_live_min * aht_factor, r.aht_async_min * aht_factor
        a_l, a_a = lam_l * aht_l / 60, lam_a * aht_a / 60
        if model == "blended":
            # live contacts: whole agents from Erlang C (live work can interrupt email work, so the
            # whole pool serves them); workload: a fractional need (Erlangs / max occupancy).
            n_live = erlang.required_agents(lam_l, aht_l, st["live_target_min"], sl_goal, 1.0, 0)
            n_work = (a_l + a_a) / max_occ
            n = max(n_live, n_work, min_agents)
            binding = ("live response" if n_live >= n_work and n_live > min_agents else
                       "workload / occupancy cap" if n_work > min_agents else "24/7 minimum")
        elif model == "two_pool":
            n_live = erlang.required_agents(lam_l, aht_l, st["live_target_min"], sl_goal, max_occ, min_agents)
            n_work = erlang.required_agents(lam_a, aht_a, st["async_target_min"], sl_goal, max_occ, min_agents)
            n, binding = n_live + n_work, "two separate pools"
        else:
            raise ValueError(model)
        # people are whole: round once, after shrinkage (not once for agents and again for people)
        sched = erlang.scheduled_agents(n, shrink)
        rows.append({"how": r.how, "erlangs_live": a_l, "erlangs_async": a_a,
                     "erlangs_total": a_l + a_a, "agents_live_response": n_live,
                     "agents_workload": n_work, "productive_required": n,
                     "scheduled_required": sched, "binding": binding,
                     "occupancy_at_requirement": (a_l + a_a) / (sched * (1 - shrink)) if sched else 0.0,
                     "live_sl_at_requirement": erlang.service_level_fractional(
                         sched * (1 - shrink), a_l, aht_l, st["live_target_min"])})
    return demand[["how", "dow", "dow_name", "hour"]].merge(pd.DataFrame(rows), on="how")


def continuous_fte(demand: pd.DataFrame, st: dict, shift_h: int = 8) -> float:
    """No-rounding lower bound: weekly workload / max occupancy / (1 - shrinkage) / hours per FTE."""
    agent_hours = (demand["erlangs_total"] / st["max_occupancy"] / (1 - st["shrinkage"])).sum()
    return float(agent_hours / (shift_h * st["shifts_per_fte_week"]))


def min_fte_for_requirement(req: pd.DataFrame, starts: list[int], shifts_per_fte: int = 5) -> tuple[int, int]:
    """(weekly shifts, FTE) of the cheapest workload-matched roster meeting the requirement."""
    sh = optimize_min_shifts(req["scheduled_required"].to_numpy(), starts)
    n = int(sh["agents"].sum())
    return n, fte_from_shifts(n, shifts_per_fte)


# ---------------------------------------------------------------------------
# 3-4. Rosters and simulation
# ---------------------------------------------------------------------------
def erlang_check(roster: np.ndarray, demand: pd.DataFrame, st: dict, shrinkage: float) -> dict:
    """Analytic cross-check of a roster: Erlang C service level per hour (volume-weighted)."""
    p = np.asarray(roster, float) * (1 - shrinkage)
    sl_live, sl_async = [], []
    for pi, r in zip(p, demand.itertuples()):
        a_l, a_a = r.erlangs_live, r.erlangs_async
        sl_live.append(erlang.service_level_fractional(pi, a_l, r.aht_live_min, st["live_target_min"]))
        # async work gets the capacity left over after live work
        sl_async.append(erlang.service_level_fractional(max(pi - a_l, 0.0), a_a, r.aht_async_min,
                                                        st["async_target_min"]))
    w_l, w_a = demand["live_per_hour"].to_numpy(), demand["async_per_hour"].to_numpy()
    return {"erlang_live_queue_sl": float(np.average(sl_live, weights=w_l)),
            "erlang_async_queue_sl": float(np.average(sl_async, weights=w_a)),
            "erlang_live_sl_by_how": np.array(sl_live), "erlang_async_sl_by_how": np.array(sl_async)}


def simulate_roster(name: str, roster: np.ndarray, items: pd.DataFrame, st: dict,
                    seed: int, tickets: pd.DataFrame | None = None) -> tuple[dict, pd.DataFrame, pd.DataFrame]:
    rng = np.random.default_rng(seed)
    out = run_roster(items, roster, st["shrinkage"], rng, T0, N_HOURS)
    resp = summarize_response(items, out["wait_s"], tickets)
    resp["roster"] = name
    summary = {
        "roster": name,
        "weekly_shifts": int(round(np.sum(roster) / 8)),
        "utilisation": out["utilisation"],
        "live_queue_sl": resp.loc[resp.channel != "Email", "queue_met"].mean(),
        "email_queue_sl": resp.loc[resp.channel == "Email", "queue_met"].mean(),
        "queue_sl": resp["queue_met"].mean(),
        "process_sl": resp["process_met"].mean(),
        "response_sl": resp["response_met"].mean(),
        "response_sl_sum": resp["response_met_sum"].mean(),
        "response_sl_chat": resp.loc[resp.channel == "Chat", "response_met"].mean(),
        "response_sl_phone": resp.loc[resp.channel == "Phone", "response_met"].mean(),
        "response_sl_email": resp.loc[resp.channel == "Email", "response_met"].mean(),
        "mean_queue_wait_min_email": resp.loc[resp.channel == "Email", "queue_wait_min"].mean(),
        "p95_queue_wait_min_email": resp.loc[resp.channel == "Email", "queue_wait_min"].quantile(0.95),
        "max_queue_len": int(out["queue_len"].max()),
    }
    hourly = pd.DataFrame({"hour_index": np.arange(N_HOURS), "scheduled": out["scheduled"],
                           "productive": out["servers"], "queue_len": out["queue_len"]})
    hourly["roster"] = name
    return summary, resp, hourly


def capacity_plan(tickets: pd.DataFrame, cfg: dict, follow_up_timing: str = "anytime") -> dict:
    """Run the full capacity plan for the base assumptions. Returns tables for caching.

    follow_up_timing: "anytime" (base: follow-up work is done when it arises, incl. weekends) or
    "weekdays" (follow-ups that would fall on a weekend wait until Monday) - a stress test of the
    weekend-workload assumption.
    """
    st = cfg["staffing"]
    seed = cfg["random_seed"]
    items = build_work_items(tickets, cfg, np.random.default_rng(seed + 1), semantics="touches",
                             follow_up_timing=follow_up_timing)
    demand = demand_by_how(items, tickets)
    req = requirement(demand, st)
    starts = st["shift_starts"]

    # workload-matched roster: cheapest cover -> FTE -> best spread of that many shifts
    min_shifts, fte = min_fte_for_requirement(req, starts, st["shifts_per_fte_week"])
    budget = fte * st["shifts_per_fte_week"]
    proposed = optimize_fixed_budget(req["scheduled_required"].to_numpy(), budget, starts, fte,
                                     weights=demand["tickets_per_hour"].to_numpy() + 1e-6)
    daily_share = demand.groupby("dow")["tickets_per_hour"].sum().to_numpy()
    shift_sets = {"proposed": proposed}
    for kind in HYPOTHESES:
        shift_sets[kind] = hypothesis_roster(kind, budget, daily_share)
    coverage = {k: coverage_from_shifts(v) for k, v in shift_sets.items()}

    # hire option: keep everyone where they are today, add the fewest shifts that close every gap
    hire = []
    for kind in HYPOTHESES:
        extra = extra_shifts_to_cover(shift_sets[kind], req["scheduled_required"].to_numpy(), starts)
        n_extra = int(extra["agents"].sum())
        extra_fte = fte_from_shifts(n_extra, st["shifts_per_fte_week"]) if n_extra else 0
        hire.append({"hypothesis": kind, "description": HYPOTHESES[kind],
                     "extra_weekly_shifts": n_extra, "extra_fte_equivalent": n_extra / st["shifts_per_fte_week"],
                     "extra_fte": extra_fte, "fte_after_hiring": fte + extra_fte,
                     "hours_under_covered_today": int(np.sum(coverage_from_shifts(shift_sets[kind])
                                                             < req["scheduled_required"].to_numpy()))})
        shift_sets[f"hire_{kind}"] = combine_shifts(shift_sets[kind], extra)
    coverage = {k: coverage_from_shifts(v) for k, v in shift_sets.items()}
    hire = pd.DataFrame(hire)

    # simulate every roster on the same synthetic year
    summaries, responses, hourly = [], [], []
    for i, (name, cov) in enumerate(coverage.items()):
        s, r, h = simulate_roster(name, cov, items, st, seed + 100 + i, tickets)
        s.update({k: v for k, v in erlang_check(cov, demand, st, st["shrinkage"]).items()
                  if not k.endswith("_by_how")})
        s["fte"] = math.ceil(s["weekly_shifts"] / st["shifts_per_fte_week"])
        summaries.append(s)
        responses.append(r)
        hourly.append(h)
    sim = pd.DataFrame(summaries)

    cov_df = demand[["how", "dow", "dow_name", "hour", "tickets_per_hour"]].copy()
    cov_df["scheduled_required"] = req["scheduled_required"].to_numpy()
    for name, cov in coverage.items():
        cov_df[f"scheduled_{name}"] = cov
        chk = erlang_check(cov, demand, st, st["shrinkage"])
        cov_df[f"erlang_live_sl_{name}"] = chk["erlang_live_sl_by_how"]
        cov_df[f"erlang_async_sl_{name}"] = chk["erlang_async_sl_by_how"]

    tables = {f"roster_table_{k}": roster_table(v).reset_index().rename(columns={"label": "shift"})
              for k, v in shift_sets.items() if k in ("proposed", "by_day", "flat", "business_hours")}
    return {
        "items": items, "demand": demand, "requirement": req, "coverage": cov_df,
        "sim_summary": sim, "sim_response": pd.concat(responses, ignore_index=True),
        "sim_hourly": pd.concat(hourly, ignore_index=True), "hire_options": hire,
        "fte_current": fte, "weekly_shifts_current": budget, "min_shifts_demand_shaped": min_shifts,
        "fte_continuous": continuous_fte(demand, st),
        "min_coverage_ratio_proposed": proposed.attrs.get("min_coverage_ratio"), **tables,
    }


# ---------------------------------------------------------------------------
# 5. Sensitivity
# ---------------------------------------------------------------------------
def sensitivity(tickets: pd.DataFrame, cfg: dict, base_items: pd.DataFrame | None = None) -> pd.DataFrame:
    """One-at-a-time sensitivity of the FTE requirement (workload-matched roster) and of the
    extra FTE needed if today's weekday-weighted pattern is kept instead of re-rostering."""
    st = cfg["staffing"]
    starts = st["shift_starts"]
    seed = cfg["random_seed"]
    items_cache: dict[str, pd.DataFrame] = {}

    def demand_for(semantics: str) -> pd.DataFrame:
        if semantics not in items_cache:
            items_cache[semantics] = (base_items if (semantics == "touches" and base_items is not None)
                                      else build_work_items(tickets, cfg, np.random.default_rng(seed + 1),
                                                            semantics=semantics))
        return demand_by_how(items_cache[semantics], tickets)

    base_demand = demand_for("touches")
    daily_share = base_demand.groupby("dow")["tickets_per_hour"].sum().to_numpy()
    _, base_fte = min_fte_for_requirement(requirement(base_demand, st), starts, st["shifts_per_fte_week"])
    today = hypothesis_roster("by_day", base_fte * st["shifts_per_fte_week"], daily_share)

    def evaluate(label: str, value: str, demand: pd.DataFrame, **kw) -> dict:
        req = requirement(demand, st, **kw)
        n_shifts, fte = min_fte_for_requirement(req, starts, st["shifts_per_fte_week"])
        extra = int(extra_shifts_to_cover(today, req["scheduled_required"].to_numpy(), starts)["agents"].sum())
        return {"parameter": label, "value": value, "fte_demand_shaped": fte,
                "extra_fte_if_today_roster_kept": fte_from_shifts(extra, st["shifts_per_fte_week"]) if extra else 0,
                "peak_scheduled_per_hour": int(req["scheduled_required"].max()),
                "min_scheduled_per_hour": int(req["scheduled_required"].min())}

    rows = [evaluate("Base case", "base", base_demand)]
    for sem in ("half_agent", "chat_in_session"):
        rows.append(evaluate("Meaning of 'agent interactions'", sem, demand_for(sem)))
    for f in (0.7, 1.3):
        rows.append(evaluate("Handle time per touch", f"x{f}", base_demand, aht_factor=f))
    for s in (0.2, 0.4):
        rows.append(evaluate("Shrinkage", f"{s:.0%}", base_demand, shrinkage=s))
    for o in (0.80, 0.90):
        rows.append(evaluate("Max occupancy", f"{o:.0%}", base_demand, max_occupancy=o))
    for g in (0.80, 0.85, 0.95):
        rows.append(evaluate("Service-level goal (live, 2 min)", f"{g:.0%}", base_demand, sl_goal=g))
    for v, lab in ((0.5, "10x export"), (2.0, "40x export")):
        rows.append(evaluate("Volume (scale factor)", lab, base_demand, volume_factor=v))
    two = requirement(base_demand, st, model="two_pool")
    n_shifts, fte = min_fte_for_requirement(two, starts, st["shifts_per_fte_week"])
    extra = int(extra_shifts_to_cover(today, two["scheduled_required"].to_numpy(), starts)["agents"].sum())
    rows.append({"parameter": "Pool design", "value": "two separate pools (chat/phone vs email)",
                 "fte_demand_shaped": fte,
                 "extra_fte_if_today_roster_kept": fte_from_shifts(extra, st["shifts_per_fte_week"]) if extra else 0,
                 "peak_scheduled_per_hour": int(two["scheduled_required"].max()),
                 "min_scheduled_per_hour": int(two["scheduled_required"].min())})
    out = pd.DataFrame(rows)
    base = out.iloc[0]
    out["delta_fte_vs_base"] = out["fte_demand_shaped"] - base["fte_demand_shaped"]
    out["base_fte_today"] = base_fte
    return out
