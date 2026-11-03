"""Headcount business case: hire vs re-roster vs automate (synthetic scenario).

All options start from the same assumed situation: the scaled team of N FTE on a
weekday-weighted roster (today's roster is not in the data; see roster.HYPOTHESES).
Response SLA for each option comes from simulating the full synthetic year.
Costs are assumptions in config.yaml (to be confirmed with Finance).
"""
from __future__ import annotations

import numpy as np
import pandas as pd

from . import synth
from .automation import deflected_items
from .roster import coverage_from_shifts
from .staffing import simulate_roster


def simulate_growth(fct: pd.DataFrame, cfg: dict, roster: np.ndarray,
                    factors=(1.0, 1.05, 1.10, 1.15, 1.20, 1.25, 1.30),
                    deflection_level: str | None = None) -> pd.DataFrame:
    """Response SLA of a fixed roster as volume grows.

    Each point re-generates the synthetic year at the higher volume with the SAME random
    seeds as the main run, so factor 1.0 reproduces the main result exactly and the curve
    is not distorted by changing random draws.
    """
    st = cfg["staffing"]
    seed = cfg["random_seed"]
    rows = []
    for f in factors:
        c = {**cfg, "scenario": {**cfg["scenario"], "scale_factor": cfg["scenario"]["scale_factor"] * f}}
        t = synth.generate_tickets(fct, c, np.random.default_rng(seed))
        it = synth.build_work_items(t, c, np.random.default_rng(seed + 1))
        if deflection_level:
            t, it = deflected_items(t, it, cfg, deflection_level)
        s, _, _ = simulate_roster(f"growth_{f}", roster, it, st, seed + 100, t)
        rows.append({"volume_factor": f, "deflection": deflection_level or "none",
                     "queue_sl": s["queue_sl"], "response_sl": s["response_sl"],
                     "process_sl": s["process_sl"], "email_queue_sl": s["email_queue_sl"],
                     "utilisation": s["utilisation"]})
    return pd.DataFrame(rows)


def replicate_rosters(fct: pd.DataFrame, cfg: dict, coverage: pd.DataFrame, n_rep: int = 5,
                      rosters=("proposed", "by_day", "flat", "business_hours", "hire_by_day")) -> pd.DataFrame:
    """Re-run the comparison on n_rep independent synthetic years (new arrivals, new bootstrap,
    new handle times, new staffing noise) to show the roster ranking is not a random-draw artefact."""
    st = cfg["staffing"]
    rows = []
    for r in range(n_rep):
        base = cfg["random_seed"] + 10_000 * (r + 1)
        t = synth.generate_tickets(fct, cfg, np.random.default_rng(base))
        it = synth.build_work_items(t, cfg, np.random.default_rng(base + 1))
        for j, name in enumerate(rosters):
            s, _, _ = simulate_roster(name, coverage[f"scheduled_{name}"].to_numpy(), it, st, base + 100 + j, t)
            rows.append({"replication": r + 1, "roster": name, "response_sl": s["response_sl"],
                         "queue_sl": s["queue_sl"], "process_sl": s["process_sl"]})
    return pd.DataFrame(rows)


def options(cp: dict, auto: dict, tickets: pd.DataFrame, items: pd.DataFrame, cfg: dict,
            email_alert: dict) -> pd.DataFrame:
    """Compare the decision options on cost and simulated response SLA."""
    st, cost = cfg["staffing"], cfg["cost"]
    sim = cp["sim_summary"].set_index("roster")
    fte = cp["fte_current"]
    hire = cp["hire_options"].set_index("hypothesis").loc["by_day"]
    cov = cp["coverage"]

    # automation scenarios need their own simulation runs (fewer tickets)
    t_d, i_d = deflected_items(tickets, items, cfg, "base")
    s_c, _, _ = simulate_roster("automate_today", cov["scheduled_by_day"].to_numpy(), i_d, st,
                                cfg["random_seed"] + 401, t_d)
    s_bc, _, _ = simulate_roster("reroster_automate", cov["scheduled_proposed"].to_numpy(), i_d, st,
                                 cfg["random_seed"] + 402, t_d)
    a_base = auto["automation_summary"].set_index("level").loc["base"]

    def row(option, what, fte_, one_off, annual, sl, queue_sl, note):
        return {"option": option, "what_changes": what, "fte": fte_, "one_off_cost_eur": one_off,
                "annual_cost_change_eur": annual, "response_sl": sl, "queue_sl": queue_sl, "note": note}

    rows = [
        row("0. Status quo", "Today's roster (assumed weekday-weighted), no change", fte, 0, 0,
            sim.loc["by_day", "response_sl"], sim.loc["by_day", "queue_sl"],
            f"{int(cp['hire_options'].set_index('hypothesis').loc['by_day', 'hours_under_covered_today'])} "
            "of 168 weekly hours below requirement (mostly weekends)"),
        row("A. Hire", f"Keep today's roster, add {int(hire['extra_fte'])} FTE on the under-covered shifts",
            int(hire["fte_after_hiring"]), int(hire["extra_fte"]) * cost["hire_one_off_eur"],
            int(hire["extra_fte"]) * cost["fte_annual_eur"],
            sim.loc["hire_by_day", "response_sl"], sim.loc["hire_by_day", "queue_sl"],
            "Closes the gaps by adding people instead of moving them"),
        row("B. Re-roster", "Move existing shifts to match workload (demand-shaped roster)", fte, 0, 0,
            sim.loc["proposed", "response_sl"], sim.loc["proposed", "queue_sl"],
            "Same people and hours; change takes one roster cycle"),
        row("C. Automate", f"Self-service + routing deflects {a_base['deflected_share_of_tickets']:.0%} "
            "of tickets; roster unchanged", fte, cost["automation_one_off_eur"], cost["automation_annual_eur"],
            s_c["response_sl"], s_c["queue_sl"],
            f"Workload -{a_base['workload_reduction_share']:.0%}; deflection rates are assumptions"),
        row("B + C", "Re-roster now, add deflection over the quarter", fte, cost["automation_one_off_eur"],
            cost["automation_annual_eur"], s_bc["response_sl"], s_bc["queue_sl"],
            f"Frees ~{int(a_base['fte_freed'])} FTE of capacity for backlog clean-up or growth"),
    ]
    out = pd.DataFrame(rows)
    out["response_sl_with_email_alert"] = out["response_sl"] + email_alert["base_uplift_pp"] / 100
    out["first_year_cost_eur"] = out["one_off_cost_eur"] + out["annual_cost_change_eur"]
    return out
