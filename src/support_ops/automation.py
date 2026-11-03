"""Automation / self-service opportunity sizing.

Volume and complexity per topic come from the REAL export. Deflection rates are
ASSUMPTIONS (config.yaml -> automation.topics, low / base / high). Workload saved is
measured on the synthetic work items (same topic mix, scaled volume), and the staffing
effect is re-run through the same Erlang C requirement used in the capacity plan.
"""
from __future__ import annotations

import numpy as np
import pandas as pd

from .roster import fte_from_shifts
from .staffing import demand_by_how, min_fte_for_requirement, requirement

LEVELS = ("low", "base", "high")


def topic_profile(fct: pd.DataFrame, cfg: dict) -> pd.DataFrame:
    """Real-data profile of each topic + the lever and deflection assumptions."""
    g = fct.groupby("topic")
    prof = pd.DataFrame({
        "tickets": g.size(),
        "interactions_mean": g["agent_interactions"].mean(),
        "tier2_share": g["agent_group"].apply(lambda s: (s == "2nd line support").mean()),
        "resolution_median_h": g["resolution_h"].median(),
        "resolution_attainment": g["resolution_sla_met"].mean(),
        "response_attainment": g["response_sla_met"].mean(),
        "csat_avg": g["csat_score"].mean(),
    })
    prof["share"] = prof["tickets"] / prof["tickets"].sum()
    # complexity index: average percentile rank of three proxies (0 = simplest topic)
    proxies = prof[["interactions_mean", "tier2_share", "resolution_median_h"]].rank(pct=True)
    prof["complexity_index"] = proxies.mean(axis=1)
    topics = cfg["automation"]["topics"]
    prof["lever"] = [topics.get(t, {}).get("lever", "None identified") for t in prof.index]
    for i, lvl in enumerate(LEVELS):
        prof[f"deflection_{lvl}"] = [topics.get(t, {}).get("deflection", [0, 0, 0])[i] for t in prof.index]
    prof["deflected_share_of_all_tickets_base"] = prof["share"] * prof["deflection_base"]
    prof = prof.sort_values("tickets", ascending=False)
    prof.index.name = "topic"
    return prof.reset_index()


def deflect(tickets: pd.DataFrame, items: pd.DataFrame, rates: dict[str, float],
            rng: np.random.Generator) -> tuple[pd.DataFrame, pd.DataFrame]:
    """Remove a random `rates[topic]` share of each topic's tickets (and their work items)."""
    u = rng.random(len(tickets))
    r = tickets["topic"].map(rates).fillna(0).to_numpy()
    keep_ids = tickets.loc[u >= r, "ticket_id"]
    return (tickets[tickets["ticket_id"].isin(keep_ids)],
            items[items["ticket_id"].isin(keep_ids)].reset_index(drop=True))


def automation_impact(fct: pd.DataFrame, tickets: pd.DataFrame, items: pd.DataFrame,
                      cfg: dict) -> dict[str, pd.DataFrame]:
    st = cfg["staffing"]
    prof = topic_profile(fct, cfg)
    weeks = 365 / 7
    work_h_week = items.groupby("topic")["service_s"].sum() / 3600 / weeks
    synth_tickets_year = tickets.groupby("topic").size()

    by_topic = []
    for lvl in LEVELS:
        for r in prof.itertuples():
            rate = getattr(r, f"deflection_{lvl}")
            by_topic.append({
                "level": lvl, "topic": r.topic, "lever": r.lever, "deflection_rate": rate,
                "real_tickets_2023": r.tickets, "real_tickets_deflected": r.tickets * rate,
                "scaled_tickets_year": int(synth_tickets_year.get(r.topic, 0)),
                "scaled_tickets_deflected_year": synth_tickets_year.get(r.topic, 0) * rate,
                "workload_hours_week": float(work_h_week.get(r.topic, 0.0)),
                "agent_hours_saved_week": float(work_h_week.get(r.topic, 0.0)) * rate,
            })
    by_topic = pd.DataFrame(by_topic)

    base_req = requirement(demand_by_how(items, tickets), st)
    _, base_fte = min_fte_for_requirement(base_req, st["shift_starts"], st["shifts_per_fte_week"])
    summary = []
    for i, lvl in enumerate(LEVELS):
        rates = dict(zip(prof["topic"], prof[f"deflection_{lvl}"]))
        t_kept, i_kept = deflect(tickets, items, rates, np.random.default_rng(cfg["random_seed"] + 50 + i))
        req = requirement(demand_by_how(i_kept, t_kept), st)
        _, fte = min_fte_for_requirement(req, st["shift_starts"], st["shifts_per_fte_week"])
        sub = by_topic[by_topic["level"] == lvl]
        summary.append({
            "level": lvl,
            "deflected_share_of_tickets": sub["real_tickets_deflected"].sum() / prof["tickets"].sum(),
            "real_tickets_deflected_2023": sub["real_tickets_deflected"].sum(),
            "scaled_tickets_deflected_year": sub["scaled_tickets_deflected_year"].sum(),
            "agent_hours_saved_week": sub["agent_hours_saved_week"].sum(),
            "workload_reduction_share": sub["agent_hours_saved_week"].sum() / sub["workload_hours_week"].sum(),
            "fte_demand_shaped_before": base_fte,
            "fte_demand_shaped_after": fte,
            "fte_freed": base_fte - fte,
        })
    return {"topic_profile": prof, "automation_by_topic": by_topic,
            "automation_summary": pd.DataFrame(summary)}


def deflected_items(tickets: pd.DataFrame, items: pd.DataFrame, cfg: dict, level: str = "base"):
    prof_rates = {t: v["deflection"][LEVELS.index(level)] for t, v in cfg["automation"]["topics"].items()}
    return deflect(tickets, items, prof_rates, np.random.default_rng(cfg["random_seed"] + 50 + LEVELS.index(level)))


def growth_headroom(items: pd.DataFrame, tickets: pd.DataFrame, cfg: dict, fte_available: int,
                    factors=np.round(np.arange(1.0, 1.61, 0.05), 2)) -> pd.DataFrame:
    """FTE needed (workload-matched roster) as volume grows, to find when hiring becomes necessary."""
    st = cfg["staffing"]
    demand = demand_by_how(items, tickets)
    rows = []
    for f in factors:
        req = requirement(demand, st, volume_factor=float(f))
        _, fte = min_fte_for_requirement(req, st["shift_starts"], st["shifts_per_fte_week"])
        rows.append({"volume_factor": float(f), "fte_demand_shaped": fte,
                     "fits_current_team": fte <= fte_available})
    return pd.DataFrame(rows)
