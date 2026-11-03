"""End-to-end pipeline: raw export -> clean -> KPIs (SQL) -> root cause -> synthetic
scale-up -> staffing model -> automation -> business case -> key numbers.

Everything the notebooks, report and dashboard show is read from data/processed/*.parquet
and reports/key_numbers.json, written here. Run with `python run.py` (or `make all`).
"""
from __future__ import annotations

import json
import time

import numpy as np
import pandas as pd

from . import automation, business_case, rca, staffing, synth
from .config import load_config, processed_path, reports_path
from .data import build_fct_tickets, run_quality_checks
from .kpis import build_kpis
from .sql import run_sql_file


def _save(name: str, df: pd.DataFrame) -> None:
    df = df.copy()
    df.attrs = {}
    df.to_parquet(processed_path(f"{name}.parquet"), index=False)


def synth_fct_view(tickets: pd.DataFrame, resp: pd.DataFrame) -> pd.DataFrame:
    """Synthetic tickets in the fct_tickets column layout, so the same KPI SQL runs on them."""
    t = tickets.copy()
    r = resp.set_index("ticket_id")
    t["frt_min"] = t["ticket_id"].map(r["response_min"]).replace(np.inf, np.nan)
    t["response_sla_met"] = t["ticket_id"].map(r["response_met"]).astype("boolean")
    t["created_dow_name"] = t["created_at"].dt.strftime("%a")
    t["hour_band"] = pd.cut(t["created_hour"], [-1, 5, 11, 17, 23],
                            labels=["00-06 Night", "06-12 Morning", "12-18 Afternoon", "18-24 Evening"]).astype(str)
    t["is_weekend"] = t["created_dow"] >= 6
    t["created_quarter"] = "Q" + t["created_at"].dt.quarter.astype(str)
    t["created_half"] = np.where(t["created_at"].dt.month <= 6, "H1", "H2")
    t["is_resolved"] = t["resolution_outcome"].str.startswith("Resolved")
    t["csat_positive"] = (t["csat_score"] >= 4).astype("boolean")
    t["agent_interactions"] = t["agent_interactions"].replace(0, np.nan)
    keep = ["ticket_id", "created_at", "created_date", "created_month", "created_dow", "created_dow_name",
            "created_hour", "hour_band", "is_weekend", "created_quarter", "created_half", "channel",
            "channel_group", "priority", "topic", "product_group", "agent_group", "response_target_min",
            "resolution_target_h", "frt_min", "response_sla_met", "resolution_h", "is_resolved",
            "resolution_sla_met", "resolution_outcome", "agent_interactions", "csat_score", "csat_positive"]
    return t[keep]


def run(verbose: bool = True) -> dict:
    t_start = time.time()
    log = (lambda *a: print(f"[{time.time() - t_start:6.1f}s]", *a, flush=True)) if verbose else (lambda *a: None)
    cfg = load_config()
    seed = cfg["random_seed"]
    goal = cfg["sla"]["goal_attainment"]

    # 1. clean + quality checks -------------------------------------------------
    fct = build_fct_tickets()
    dq = run_quality_checks()
    log(f"fct_tickets: {len(fct)} rows; DQ checks: {dq.status.value_counts().to_dict()}")

    # 2. KPIs (SQL) --------------------------------------------------------------
    k = build_kpis()
    log("KPI SQL done:", ", ".join(k))
    mix = (fct.groupby(["created_month", "channel"]).size() / fct.groupby("created_month").size()).rename("share")
    _save("kpi_channel_mix", mix.reset_index())

    # 3. root cause tests (real) -------------------------------------------------
    load = rca.load_vs_sla(fct)
    slots = rca.time_slot_tests(fct)
    late = rca.breach_lateness(fct)
    alert = rca.email_alert_lever(fct)
    comp = rca.resolution_composition(k["kpi_monthly"])
    het = rca.heterogeneity(fct)
    for name, df in [("rca_load_vs_sla", load), ("rca_time_slots", slots), ("rca_breach_lateness", late),
                     ("rca_email_alert", alert["table"]), ("rca_resolution_composition", comp),
                     ("rca_heterogeneity", het)]:
        _save(name, df)
    cp_on = rca.changepoint(comp.set_index("created_month")["share_on_time"])
    cp_late = rca.changepoint(comp.set_index("created_month")["share_resolved_late"])
    stale = rca.stale_backlog(fct, k["kpi_backlog_daily"], cfg["sla"]["aged_backlog_days"])
    weekend = rca.weekend_workload(fct)
    recov = rca.recovery_scenario(fct)
    log("RCA done")

    # 4. synthetic scale-up -----------------------------------------------------
    tickets = synth.generate_tickets(fct, cfg, np.random.default_rng(seed))
    calib = synth.calibration_summary(fct, cfg)
    log(f"synthetic tickets: {len(tickets)}")

    # 5. capacity plan ------------------------------------------------------------
    cp = staffing.capacity_plan(tickets, cfg)
    items = cp["items"]
    for name in ["demand", "requirement", "coverage", "sim_summary", "hire_options"]:
        _save(f"staff_{name}", cp[name])
    _save("staff_sim_hourly", cp["sim_hourly"])
    _save("staff_sim_response", cp["sim_response"])
    for name in ["proposed", "by_day", "flat", "business_hours"]:
        _save(f"staff_roster_table_{name}", cp[f"roster_table_{name}"])
    # stress test of the weekend-workload assumption: follow-ups that land at weekends wait until Monday
    cp_wd = staffing.capacity_plan(tickets, cfg, follow_up_timing="weekdays")
    _save("staff_sim_summary_deferred", cp_wd["sim_summary"])
    _save("staff_hire_options_deferred", cp_wd["hire_options"])
    _save("synth_tickets", tickets)
    _save("synth_work_items", items)
    log(f"capacity plan: {cp['fte_current']} FTE; rosters simulated: {len(cp['sim_summary'])}")

    # synthetic validation: same KPI SQL on the synthetic tickets (today's assumed roster)
    resp_today = cp["sim_response"][cp["sim_response"]["roster"] == "by_day"]
    sv = synth_fct_view(tickets, resp_today)
    sv_path = processed_path("synth_fct_tickets.parquet")
    sv.to_parquet(sv_path, index=False)
    for name, f in [("kpi_monthly", "01_kpi_monthly.sql"), ("kpi_by_dimension", "02_kpi_by_dimension.sql"),
                    ("kpi_volume_heatmap", "06_volume_heatmap.sql")]:
        _save(f"{name}_synth", run_sql_file(f, {"fct_tickets_path": str(sv_path)}))

    # 6. sensitivity ----------------------------------------------------------------
    sens = staffing.sensitivity(tickets, cfg, items)
    _save("staff_sensitivity", sens)
    log("sensitivity done")

    # 7. automation + growth -------------------------------------------------------
    auto = automation.automation_impact(fct, tickets, items, cfg)
    for name, df in auto.items():
        _save(name, df)
    proposed_cov = cp["coverage"]["scheduled_proposed"].to_numpy()
    growth = pd.concat([business_case.simulate_growth(fct, cfg, proposed_cov),
                        business_case.simulate_growth(fct, cfg, proposed_cov, deflection_level="base")],
                       ignore_index=True)
    _save("staff_growth", growth)
    reps = business_case.replicate_rosters(fct, cfg, cp["coverage"])
    _save("staff_replications", reps)
    log("automation + growth + replications done")

    # 8. business case -------------------------------------------------------------------
    opts = business_case.options(cp, auto, tickets, items, cfg)
    _save("business_options", opts)
    log("business case done")

    # 9. key numbers -------------------------------------------------------------------
    kn = key_numbers(cfg, fct, dq, k, comp, load, slots, late, alert, het, cp_on, cp_late, stale, weekend,
                     recov, tickets, calib, cp, sens, auto, growth, opts, reps, cp_wd)
    with open(reports_path("key_numbers.json"), "w") as fh:
        json.dump(kn, fh, indent=2, default=float)
    log(f"key numbers written ({len(kn)} values)")
    return kn


def _r(x, d=6):
    return None if x is None or (isinstance(x, float) and np.isnan(x)) else round(float(x), d)


def key_numbers(cfg, fct, dq, k, comp, load, slots, late, alert, het, cp_on, cp_late, stale, weekend, recov,
                tickets, calib, cp, sens, auto, growth, opts, reps, cp_wd) -> dict:
    m = k["kpi_monthly"]
    bd = k["kpi_by_dimension"].set_index(["dimension", "segment"])
    q = bd.loc["quarter"]
    hot = k["kpi_hotspots"]
    pareto = k["kpi_topic_pareto"]
    pt = pareto[pareto.level == "topic"]
    ptp = pareto[pareto.level == "topic x product"]
    agents = k["kpi_agent_scorecard"]
    sim = cp["sim_summary"].set_index("roster")
    hire = cp["hire_options"].set_index("hypothesis")
    a_sum = auto["automation_summary"].set_index("level")
    opt = opts.set_index("option")
    g_none = growth[growth.deflection == "none"].set_index("volume_factor")
    g_base = growth[growth.deflection == "base"].set_index("volume_factor")
    floor = float(sim.loc["proposed", "process_sl"])

    st_cfg = cfg["staffing"]

    def holds(g):
        """Largest tested volume growth at which the roster still meets the staffing goal:
        queue on-time >= SL goal and agent utilisation <= max occupancy. Returns (growth, capped)."""
        ok = ((g["queue_sl"] >= st_cfg["sl_goal"]) & (g["utilisation"] <= st_cfg["max_occupancy"])).to_numpy()
        n_ok = len(ok) if ok.all() else int(np.argmin(ok))
        return (float(g.index[n_ok - 1] - 1) if n_ok else 0.0), bool(ok.all())

    h_none, h_none_capped = holds(g_none)
    h_base, h_base_capped = holds(g_base)

    def within_1pt(g):
        """Largest tested growth at which simulated response SLA (optimistic rule) is within 1 point of
        its no-growth level: the early-warning threshold."""
        ok = (g["response_sl"] >= g["response_sl"].iloc[0] - 0.01).to_numpy()
        n_ok = len(ok) if ok.all() else int(np.argmin(ok))
        return float(g.index[n_ok - 1] - 1) if n_ok else 0.0
    sim_wd = cp_wd["sim_summary"].set_index("roster")
    hire_wd = cp_wd["hire_options"].set_index("hypothesis")
    late_tbl = fct[(fct["channel"] == "Email") & (fct["response_sla_met"] == False)]  # noqa: E712
    late_min = late_tbl["frt_min"] - late_tbl["response_target_min"]
    days_window = (fct["created_date"].max() - fct["created_date"].min()).days + 1
    wk = fct.set_index("created_at").resample("W-SUN").size()
    weekly = wk.iloc[1:-1]          # complete Monday-Sunday weeks only

    kn = {
        # --- data -----------------------------------------------------------------
        "real_tickets": int(len(fct)),
        "real_first_created": str(fct["created_at"].min())[:10],
        "real_last_created": str(fct["created_at"].max())[:10],
        "real_snapshot": str(fct["snapshot_at"].iloc[0])[:16],
        "real_agents": int(fct["agent_name"].nunique()),
        "real_tickets_per_day": _r(len(fct) / days_window, 2),
        "real_days_in_window": int(days_window),
        "real_weekday_tickets_per_day": _r(np.mean([calib["daily_rate_by_weekday"][d] for d in range(1, 6)]), 2),
        "real_weekend_tickets_per_day": _r(np.mean([calib["daily_rate_by_weekday"][d] for d in (6, 7)]), 2),
        "dq_checks_total": int(len(dq)),
        "dq_checks_flagged": int((dq.status == "FLAG").sum()),
        "dq_response_flag_mismatches": int(fct["response_flag_mismatch"].sum()),
        "dq_resolution_flag_mismatches": int(fct["resolution_flag_mismatch"].sum()),
        "dq_topic_case_duplicates_rows": int((fct["topic_raw"] == "Pricing and Licensing").sum()),
        "dq_interactions_sentinel_rows": int((fct["agent_interactions_raw"] == 60).sum()),
        "dq_negative_frt_rows": int(fct["frt_invalid"].sum()),
        # --- SLA policy ---------------------------------------------------------------
        "response_target_min_email": 60, "response_target_min_chat_phone": 2,
        "resolution_target_h_chat": 24, "resolution_target_h_email_phone": 48,
        "sla_goal": cfg["sla"]["goal_attainment"],
        # --- volume -----------------------------------------------------------------------
        "volume_h1": int((fct.created_half == "H1").sum()), "volume_h2": int((fct.created_half == "H2").sum()),
        "volume_change_h2_vs_h1": _r((fct.created_half == "H2").sum() / (fct.created_half == "H1").sum() - 1),
        "volume_monthly_min": int(m["tickets"].min()), "volume_monthly_max": int(m["tickets"].max()),
        "volume_weekly_mean": _r(weekly.mean(), 1), "volume_weekly_min": int(weekly.min()),
        "volume_weekly_max": int(weekly.max()),
        "volume_month_seasonality_p": _r(rca.monthly_seasonality_p(fct), 3),
        "weekend_to_weekday_volume": _r(weekend["created_weekend_to_weekday"]),
        "weekend_to_weekday_resolutions": _r(weekend["resolved_weekend_to_weekday"]),
        "pareto_top20pct_topics_n": int(np.ceil(0.2 * len(pt))),
        "pareto_top20pct_topics_share": _r(pt.sort_values("rank")["share"].head(int(np.ceil(0.2 * len(pt)))).sum()),
        "pareto_top20pct_combos_n": int(np.ceil(0.2 * len(ptp))), "pareto_combos_total": int(len(ptp)),
        "pareto_top20pct_combos_share": _r(ptp.sort_values("rank")["share"].head(int(np.ceil(0.2 * len(ptp)))).sum()),
        "top_topic": pt.sort_values("rank")["category"].iloc[0],
        "top_topic_share": _r(pt.sort_values("rank")["share"].iloc[0]),
        "channel_share_email": _r(bd.loc[("channel", "Email"), "share_of_tickets"]),
        "channel_share_chat": _r(bd.loc[("channel", "Chat"), "share_of_tickets"]),
        "channel_share_phone": _r(bd.loc[("channel", "Phone"), "share_of_tickets"]),
        # --- SLA attainment ------------------------------------------------------------------
        "response_sla_2023": _r(fct["response_sla_met"].mean()),
        "response_evaluable": int(fct["response_sla_met"].notna().sum()),
        "resolution_sla_2023": _r(fct["resolution_sla_met"].mean()),
        "response_sla_raw_flag_2023": _r((fct["response_sla_flag_raw"] == "Within SLA").mean()),
        "response_sla_q1": _r(q.loc["Q1", "response_attainment"]), "response_sla_q4": _r(q.loc["Q4", "response_attainment"]),
        "resolution_sla_q1": _r(q.loc["Q1", "resolution_attainment"]),
        "resolution_sla_q4": _r(q.loc["Q4", "resolution_attainment"]),
        "resolution_sla_q4_lo": _r(q.loc["Q4", "resolution_attainment_lo"]),
        "resolution_sla_q4_hi": _r(q.loc["Q4", "resolution_attainment_hi"]),
        "resolution_sla_q1_lo": _r(q.loc["Q1", "resolution_attainment_lo"]),
        "resolution_sla_q1_hi": _r(q.loc["Q1", "resolution_attainment_hi"]),
        "resolution_sla_jan": _r(m["resolution_attainment"].iloc[0]),
        "resolution_sla_dec": _r(m["resolution_attainment"].iloc[-1]),
        "response_sla_h1": _r(bd.loc[("half", "H1"), "response_attainment"]),
        "response_sla_h2": _r(bd.loc[("half", "H2"), "response_attainment"]),
        "resolution_sla_h1": _r(bd.loc[("half", "H1"), "resolution_attainment"]),
        "resolution_sla_h2": _r(bd.loc[("half", "H2"), "resolution_attainment"]),
        "response_sla_email": _r(bd.loc[("channel", "Email"), "response_attainment"]),
        "response_sla_chat": _r(bd.loc[("channel", "Chat"), "response_attainment"]),
        "response_sla_phone": _r(bd.loc[("channel", "Phone"), "response_attainment"]),
        "late_share_of_resolved_jan": _r(m["breach_rate_among_resolved"].iloc[0]),
        "late_share_of_resolved_q4": _r(m.iloc[9:]["resolved_late"].sum() / m.iloc[9:]["resolved"].sum()),
        "resolution_p90_h_jan": _r(m["resolution_p90_h"].iloc[0], 1),
        "resolution_p90_h_dec": _r(m["resolution_p90_h"].iloc[-1], 1),
        "resolution_median_h_h1": _r(fct[fct.created_half == "H1"]["resolution_h"].median(), 1),
        "resolution_median_h_h2": _r(fct[fct.created_half == "H2"]["resolution_h"].median(), 1),
        "share_resolved_over_48h_h1": _r(bd.loc[("half", "H1"), "share_resolved_over_48h"]),
        "share_resolved_over_48h_h2": _r(bd.loc[("half", "H2"), "share_resolved_over_48h"]),
        # --- root cause --------------------------------------------------------------------------
        "rca_mix_effect_q1_q4_channel_pp": _r(100 * k["kpi_rca_decomposition"].query(
            "sla_type=='resolution' and comparison=='Q1 -> Q4' and dimension=='channel'")["mix_effect"].sum(), 4),
        "rca_rate_effect_q1_q4_channel_pp": _r(100 * k["kpi_rca_decomposition"].query(
            "sla_type=='resolution' and comparison=='Q1 -> Q4' and dimension=='channel'")["rate_effect"].sum(), 4),
        "rca_mix_effect_q1_q4_topic_pp": _r(100 * k["kpi_rca_decomposition"].query(
            "sla_type=='resolution' and comparison=='Q1 -> Q4' and dimension=='topic'")["mix_effect"].sum(), 4),
        "rca_rate_effect_q1_q4_topic_pp": _r(100 * k["kpi_rca_decomposition"].query(
            "sla_type=='resolution' and comparison=='Q1 -> Q4' and dimension=='topic'")["rate_effect"].sum(), 4),
        "rca_on_time_share_h1": _r(recov["on_time_h1"]), "rca_on_time_share_h2": _r(recov["on_time_h2"]),
        "rca_late_share_h1": _r(recov["late_share_h1"]), "rca_late_share_h2": _r(recov["late_share_h2"]),
        "rca_never_share_h1": _r(recov["never_share_h1"]), "rca_never_share_h2": _r(recov["never_share_h2"]),
        "rca_on_time_h2_if_late_back_to_h1": _r(recov["on_time_h2_if_late_back_to_h1"]),
        "rca_step_month_late_share": cp_late["step_month"], "rca_late_share_before_step": _r(cp_late["mean_before"]),
        "rca_late_share_after_step": _r(cp_late["mean_after"]), "rca_ramp_start": cp_late["ramp_start"],
        "rca_ramp_end": cp_late["ramp_end"], "rca_ramp_r2": _r(cp_late["ramp_r2"], 3),
        "rca_step_r2": _r(cp_late["step_r2"], 3),
        "rca_load_trend_p_min": _r(load["trend_p_value"].min(), 3),
        "rca_load_trend_p_max": _r(load["trend_p_value"].max(), 3),
        "rca_hour_of_day_p_response": _r(slots.query("slot=='hour of day' and sla=='response'")["p_value"].iloc[0], 3),
        "rca_day_of_week_p_response": _r(slots.query("slot=='day of week' and sla=='response'")["p_value"].iloc[0], 3),
        "rca_weekend_p_response": _r(slots.query("slot=='weekday vs weekend' and sla=='response'")["p_value"].iloc[0], 3),
        "rca_agent_p_resolution": _r(het.query("dimension=='agent_name' and sla=='resolution'")["p_value"].iloc[0], 3),
        "rca_priority_p_resolution": _r(het.query("dimension=='priority' and sla=='resolution'")["p_value"].iloc[0], 3),
        "rca_priority_p_response": _r(het.query("dimension=='priority' and sla=='response'")["p_value"].iloc[0], 3),
        "rca_topic_p_resolution": _r(het.query("dimension=='topic' and sla=='resolution'")["p_value"].iloc[0], 3),
        "hotspots_tested_per_sla": int((hot.sla_type == "response").sum()),
        "hotspots_significant_response": int(hot.query("sla_type=='response'")["significant_fdr5"].sum()),
        "hotspots_significant_resolution": int(hot.query("sla_type=='resolution'")["significant_fdr5"].sum()),
        "phone_response_breach_rate": _r(1 - bd.loc[("channel", "Phone"), "response_attainment"]),
        "late_email_breach_median_min_late": _r(late.set_index("channel").loc["Email", "median_minutes_late"], 1),
        "late_chat_breach_median_min_late": _r(late.set_index("channel").loc["Chat", "median_minutes_late"], 2),
        "late_phone_breach_median_min_late": _r(late.set_index("channel").loc["Phone", "median_minutes_late"], 2),
        "email_breaches": int(alert["email_breaches"]),
        "email_alert_uplift_pp_low": _r(alert["table"]["uplift_pp"].iloc[0], 4),
        "email_alert_uplift_pp_base": _r(alert["table"]["uplift_pp"].iloc[1], 4),
        "email_alert_uplift_pp_high": _r(alert["table"]["uplift_pp"].iloc[2], 4),
        "email_alert_response_sla_base": _r(alert["table"]["response_sl_after"].iloc[1]),
        "email_alert_response_sla_high": _r(alert["table"]["response_sl_after"].iloc[2]),
        "stale_never_resolved": stale["never_resolved"], "stale_share_of_tickets": _r(stale["never_resolved_share"]),
        "stale_share_of_resolution_breaches": _r(stale["never_resolved_share_of_breaches"]),
        "stale_median_age_days": _r(stale["never_resolved_median_age_days"], 0),
        "stale_age_p25_days": _r(stale["never_resolved_age_p25_days"], 0),
        "stale_age_p75_days": _r(stale["never_resolved_age_p75_days"], 0),
        "stale_in_progress": int(stale["never_resolved_by_status"].get("In progress", 0)),
        "stale_open_no_response": int(stale["never_resolved_by_status"].get("Open", 0)),
        "active_backlog_mean": _r(stale["active_backlog_mean"], 1), "active_backlog_max": stale["active_backlog_max"],
        "active_backlog_littles_law": _r(stale["littles_law_expected_active"], 1),
        "agent_resolution_sla_min": _r(agents["resolution_attainment"].min()),
        "agent_resolution_sla_max": _r(agents["resolution_attainment"].max()),
        "agents_declined_h1_to_h2": int((agents["resolution_attainment_change"] < 0).sum()),
        "csat_breached": _r(fct.loc[~fct.resolution_sla_met, "csat_score"].mean(), 2),
        "csat_met": _r(fct.loc[fct.resolution_sla_met, "csat_score"].mean(), 2),
        # --- synthetic + staffing ---------------------------------------------------------------
        "synth_scale_factor": cfg["scenario"]["scale_factor"],
        "synth_tickets": int(len(tickets)), "synth_tickets_per_day": _r(len(tickets) / 365, 1),
        "synth_work_items": int(len(cp["items"])),
        "synth_workload_min_per_ticket": _r(cp["items"]["service_s"].sum() / 60 / len(tickets), 1),
        "synth_max_mix_gap_pp": None,   # filled below
        "staff_fte_current": cp["fte_current"], "staff_weekly_shifts": cp["weekly_shifts_current"],
        "staff_peak_scheduled": int(cp["requirement"]["scheduled_required"].max()),
        "staff_min_scheduled": int(cp["requirement"]["scheduled_required"].min()),
        "staff_weekday_scheduled_min": int(cp["requirement"].query("dow < 5")["scheduled_required"].min()),
        "staff_weekday_scheduled_max": int(cp["requirement"].query("dow < 5")["scheduled_required"].max()),
        "staff_weekday_scheduled_mean": _r(cp["requirement"].query("dow < 5")["scheduled_required"].mean(), 2),
        "staff_weekend_scheduled_min": int(cp["requirement"].query("dow >= 5")["scheduled_required"].min()),
        "staff_weekend_scheduled_max": int(cp["requirement"].query("dow >= 5")["scheduled_required"].max()),
        "staff_weekend_scheduled_mean": _r(cp["requirement"].query("dow >= 5")["scheduled_required"].mean(), 2),
        "staff_min_shifts": int(cp["min_shifts_demand_shaped"]),
        "staff_hours_binding_workload": int((cp["requirement"]["binding"] == "workload / occupancy cap").sum()),
        "staff_hours_binding_live": int((cp["requirement"]["binding"] == "live response").sum()),
        "staff_process_ceiling": _r(floor),
        "staff_sl_today_by_day": _r(sim.loc["by_day", "response_sl"]),
        "staff_sl_today_flat": _r(sim.loc["flat", "response_sl"]),
        "staff_sl_today_business_hours": _r(sim.loc["business_hours", "response_sl"]),
        "staff_sl_proposed": _r(sim.loc["proposed", "response_sl"]),
        "staff_sl_hire_by_day": _r(sim.loc["hire_by_day", "response_sl"]),
        "staff_queue_sl_today_by_day": _r(sim.loc["by_day", "queue_sl"]),
        "staff_queue_sl_proposed": _r(sim.loc["proposed", "queue_sl"]),
        "staff_gain_pp_vs_by_day": _r(100 * (sim.loc["proposed", "response_sl"] - sim.loc["by_day", "response_sl"]), 4),
        "staff_gain_pp_vs_flat": _r(100 * (sim.loc["proposed", "response_sl"] - sim.loc["flat", "response_sl"]), 4),
        "staff_gain_pp_vs_business_hours": _r(100 * (sim.loc["proposed", "response_sl"]
                                                     - sim.loc["business_hours", "response_sl"]), 4),
        "staff_hours_under_today_by_day": int(hire.loc["by_day", "hours_under_covered_today"]),
        "staff_hours_under_today_business_hours": int(hire.loc["business_hours", "hours_under_covered_today"]),
        "staff_hire_extra_fte_by_day": int(hire.loc["by_day", "extra_fte"]),
        "staff_hire_extra_shifts_by_day": int(hire.loc["by_day", "extra_weekly_shifts"]),
        "staff_hire_extra_fte_equiv_by_day": _r(hire.loc["by_day", "extra_fte_equivalent"], 1),
        "staff_fte_continuous": _r(cp["fte_continuous"], 1),
        "staff_sl_sum_today_by_day": _r(sim.loc["by_day", "response_sl_sum"]),
        "staff_sl_sum_today_flat": _r(sim.loc["flat", "response_sl_sum"]),
        "staff_sl_sum_today_business_hours": _r(sim.loc["business_hours", "response_sl_sum"]),
        "staff_sl_sum_proposed": _r(sim.loc["proposed", "response_sl_sum"]),
        "staff_sl_sum_hire_by_day": _r(sim.loc["hire_by_day", "response_sl_sum"]),
        "staff_gain_pp_vs_by_day_sum": _r(100 * (sim.loc["proposed", "response_sl_sum"]
                                                 - sim.loc["by_day", "response_sl_sum"]), 4),
        "staff_hire_minus_reroster_pp": _r(100 * (sim.loc["hire_by_day", "response_sl"]
                                                  - sim.loc["proposed", "response_sl"]), 4),
        "staff_hire_minus_reroster_pp_sum": _r(100 * (sim.loc["hire_by_day", "response_sl_sum"]
                                                      - sim.loc["proposed", "response_sl_sum"]), 4),
        "staff_hours_under_today_flat": int(hire.loc["flat", "hours_under_covered_today"]),
        "deferred_fte": int(cp_wd["fte_current"]),
        "deferred_sl_today_by_day": _r(sim_wd.loc["by_day", "response_sl"]),
        "deferred_sl_proposed": _r(sim_wd.loc["proposed", "response_sl"]),
        "deferred_gain_pp_vs_by_day": _r(100 * (sim_wd.loc["proposed", "response_sl"]
                                                - sim_wd.loc["by_day", "response_sl"]), 4),
        "deferred_gain_pp_vs_by_day_sum": _r(100 * (sim_wd.loc["proposed", "response_sl_sum"]
                                                    - sim_wd.loc["by_day", "response_sl_sum"]), 4),
        "deferred_hours_under_today_by_day": int(hire_wd.loc["by_day", "hours_under_covered_today"]),
        "email_breach_near_miss_share": _r(((late_min > 0) & (late_min <= 60)).sum() / len(late_tbl)),
        "email_breach_never_answered": int(late_tbl["frt_min"].isna().sum()),
        "staff_hire_extra_fte_business_hours": int(hire.loc["business_hours", "extra_fte"]),
        "staff_hire_extra_fte_flat": int(hire.loc["flat", "extra_fte"]),
        "staff_utilisation_proposed": _r(sim.loc["proposed", "utilisation"], 3),
        "staff_erlang_live_sl_proposed": _r(sim.loc["proposed", "erlang_live_queue_sl"]),
        "staff_des_live_sl_proposed": _r(sim.loc["proposed", "live_queue_sl"]),
        "sens_fte_min": int(sens["fte_demand_shaped"].min()), "sens_fte_max": int(sens["fte_demand_shaped"].max()),
        "sens_fte_half_agent": int(sens.query("value=='half_agent'")["fte_demand_shaped"].iloc[0]),
        "sens_fte_aht_low": int(sens.query("value=='x0.7'")["fte_demand_shaped"].iloc[0]),
        "sens_fte_aht_high": int(sens.query("value=='x1.3'")["fte_demand_shaped"].iloc[0]),
        "sens_fte_two_pool": int(sens.query("parameter=='Pool design'")["fte_demand_shaped"].iloc[0]),
        "sens_fte_scale_10x": int(sens.query("value=='10x export'")["fte_demand_shaped"].iloc[0]),
        "sens_fte_scale_40x": int(sens.query("value=='40x export'")["fte_demand_shaped"].iloc[0]),
        "sens_fte_goal_80": int(sens.query("value=='80%' and parameter.str.startswith('Service')",
                                           engine="python")["fte_demand_shaped"].iloc[0]),
        "sens_fte_goal_95": int(sens.query("value=='95%' and parameter.str.startswith('Service')",
                                           engine="python")["fte_demand_shaped"].iloc[0]),
        "growth_holds_until_no_deflection": _r(h_none, 2),
        "growth_holds_until_no_deflection_is_range_end": h_none_capped,
        "growth_holds_until_with_deflection": _r(h_base, 2),
        "growth_holds_until_with_deflection_is_range_end": h_base_capped,
        "growth_max_tested": _r(float(growth["volume_factor"].max()) - 1, 2),
        "growth_sl_within_1pt_no_deflection": _r(within_1pt(g_none), 2),
        "growth_sl_within_1pt_with_deflection": _r(within_1pt(g_base), 2),
        "growth_sl_at_plus10_no_deflection": _r(g_none.loc[1.10, "response_sl"]) if 1.10 in g_none.index else None,
        "growth_sl_at_plus25_no_deflection": _r(g_none.loc[1.25, "response_sl"]) if 1.25 in g_none.index else None,
        # --- automation ----------------------------------------------------------------------------
        "auto_deflected_share_low": _r(a_sum.loc["low", "deflected_share_of_tickets"]),
        "auto_deflected_share_base": _r(a_sum.loc["base", "deflected_share_of_tickets"]),
        "auto_deflected_share_high": _r(a_sum.loc["high", "deflected_share_of_tickets"]),
        "auto_real_tickets_deflected_base": _r(a_sum.loc["base", "real_tickets_deflected_2023"], 0),
        "auto_hours_saved_week_low": _r(a_sum.loc["low", "agent_hours_saved_week"], 1),
        "auto_hours_saved_week_base": _r(a_sum.loc["base", "agent_hours_saved_week"], 1),
        "auto_hours_saved_week_high": _r(a_sum.loc["high", "agent_hours_saved_week"], 1),
        "auto_workload_reduction_base": _r(a_sum.loc["base", "workload_reduction_share"]),
        "auto_fte_freed_low": int(a_sum.loc["low", "fte_freed"]),
        "auto_fte_freed_base": int(a_sum.loc["base", "fte_freed"]),
        "auto_fte_freed_high": int(a_sum.loc["high", "fte_freed"]),
        # --- business case ------------------------------------------------------------------------
        "cost_fte_annual_eur": cfg["cost"]["fte_annual_eur"],
        "bc_hire_annual_cost_eur": int(opt.loc["A. Hire", "annual_cost_change_eur"]),
        "bc_hire_one_off_eur": int(opt.loc["A. Hire", "one_off_cost_eur"]),
        "bc_hire_first_year_eur": int(opt.loc["A. Hire", "first_year_cost_eur"]),
        "bc_hire_first_year_whole_hires_eur": int(hire.loc["by_day", "extra_fte"] * (cfg["cost"]["fte_annual_eur"]
                                                                                  + cfg["cost"]["hire_one_off_eur"])),
        "bc_hire_sl": _r(opt.loc["A. Hire", "response_sl"]),
        "bc_reroster_sl": _r(opt.loc["B. Re-roster", "response_sl"]),
        "bc_automate_sl": _r(opt.loc["C. Automate", "response_sl"]),
        "bc_combined_sl": _r(opt.loc["B + C", "response_sl"]),
        "bc_status_quo_sl": _r(opt.loc["0. Status quo", "response_sl"]),
        "bc_hire_sl_sum": _r(opt.loc["A. Hire", "response_sl_sum"]),
        "bc_reroster_sl_sum": _r(opt.loc["B. Re-roster", "response_sl_sum"]),
        "bc_automate_sl_sum": _r(opt.loc["C. Automate", "response_sl_sum"]),
        "bc_combined_sl_sum": _r(opt.loc["B + C", "response_sl_sum"]),
        "bc_status_quo_sl_sum": _r(opt.loc["0. Status quo", "response_sl_sum"]),
        "bc_automation_first_year_eur": int(opt.loc["C. Automate", "first_year_cost_eur"]),
        "bc_automation_capacity_value_eur": int(a_sum.loc["base", "fte_freed"] * cfg["cost"]["fte_annual_eur"]),
    }
    vb = k["kpi_by_dimension"]
    sb = pd.read_parquet(processed_path("kpi_by_dimension_synth.parquet"))
    mrg = vb.merge(sb, on=["dimension", "segment"], suffixes=("_real", "_synth"))
    mrg = mrg[mrg.dimension.isin(["channel", "topic", "priority"])]
    kn["synth_max_mix_gap_pp"] = _r(100 * (mrg["share_of_tickets_real"] - mrg["share_of_tickets_synth"]).abs().max(), 4)
    kn["synth_resolution_sla"] = _r(tickets["resolution_sla_met"].mean())
    w = reps.pivot(index="replication", columns="roster", values="response_sl")
    gain = 100 * (w["proposed"] - w["by_day"])
    kn["rep_n"] = int(len(w))
    kn["rep_gain_pp_vs_by_day_mean"] = _r(gain.mean(), 4)
    kn["rep_gain_pp_vs_by_day_min"] = _r(gain.min(), 4)
    kn["rep_gain_pp_vs_by_day_max"] = _r(gain.max(), 4)
    kn["rep_sl_proposed_min"] = _r(w["proposed"].min())
    kn["rep_sl_proposed_max"] = _r(w["proposed"].max())
    kn["rep_sl_by_day_min"] = _r(w["by_day"].min())
    kn["rep_sl_by_day_max"] = _r(w["by_day"].max())
    kn["rep_ranking_stable"] = bool(((w["proposed"] > w["by_day"]) & (w["by_day"] > w["business_hours"])).all())
    ws = reps.pivot(index="replication", columns="roster", values="response_sl_sum")
    gs = 100 * (ws["proposed"] - ws["by_day"])
    kn["rep_gain_pp_vs_by_day_sum_min"] = _r(gs.min(), 4)
    kn["rep_gain_pp_vs_by_day_sum_max"] = _r(gs.max(), 4)
    hp = 100 * (w["hire_by_day"] - w["proposed"])
    kn["rep_hire_minus_reroster_pp_min"] = _r(hp.min(), 4)
    kn["rep_hire_minus_reroster_pp_max"] = _r(hp.max(), 4)
    hps = 100 * (ws["hire_by_day"] - ws["proposed"])
    kn["rep_hire_minus_reroster_pp_sum_min"] = _r(hps.min(), 4)
    kn["rep_hire_minus_reroster_pp_sum_max"] = _r(hps.max(), 4)
    kn["rep_ranking_stable_sum"] = bool(((ws["proposed"] > ws["by_day"]) & (ws["by_day"] > ws["business_hours"])).all())
    return kn
