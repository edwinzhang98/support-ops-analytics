"""Build reports/report.html: one self-contained file (plotly.js inlined, no server, opens offline)
with the full analysis - question, data, method, every chart with its reading, conclusions,
recommendations and limitations. Figures come from support_ops.charts, the same functions the
notebooks and the Streamlit app use, and every number from reports/key_numbers.json.

Also writes reports/figures/*.png (static copies of the key charts for the README).
"""
from __future__ import annotations

import datetime as dt
import html
import json

import pandas as pd
import plotly.io as pio
from plotly.offline import get_plotlyjs

from . import charts as C
from . import rca
from .config import load_config, processed_path, reports_path
from .report_text import SECTIONS, recommendations_table

README_FIGURES = ["sla_trend", "resolution_composition", "volume_heatmap", "requirement_vs_roster",
                  "roster_sl", "options", "load_vs_breach", "breach_lateness", "backlog", "sensitivity"]


def _load(name: str) -> pd.DataFrame:
    return pd.read_parquet(processed_path(f"{name}.parquet"))


def build_figures() -> dict:
    kn = json.load(open(reports_path("key_numbers.json")))
    cfg = load_config()
    goal = cfg["sla"]["goal_attainment"]
    fct = _load("fct_tickets")
    return {
        "monthly_volume": C.fig_monthly_volume(_load("kpi_monthly")),
        "volume_heatmap": C.fig_volume_heatmap(_load("kpi_volume_heatmap")),
        "weekday_workload": C.fig_weekday_workload(rca.weekend_workload(fct)),
        "pareto_topic": C.fig_topic_pareto(_load("kpi_topic_pareto"), "topic"),
        "pareto_combo": C.fig_topic_pareto(_load("kpi_topic_pareto"), "topic x product"),
        "channel_mix": C.fig_channel_mix(_load("kpi_channel_mix")),
        "sla_trend": C.fig_sla_trend(_load("kpi_monthly"), goal),
        "resolution_composition": C.fig_resolution_composition(_load("rca_resolution_composition")),
        "resolution_hist": C.fig_resolution_time_hist(fct),
        "breakdown_channel": C.fig_breakdown(_load("kpi_by_dimension"), "channel", "response", goal),
        "breakdown_topic": C.fig_breakdown(_load("kpi_by_dimension"), "topic", "resolution", goal),
        "hotspots_response": C.fig_hotspots(_load("kpi_hotspots"), "response"),
        "hotspots_resolution": C.fig_hotspots(_load("kpi_hotspots"), "resolution"),
        "agent_scorecard": C.fig_agent_scorecard(_load("kpi_agent_scorecard")),
        "breach_lateness": C.fig_breach_lateness(fct),
        "load_vs_breach": C.fig_load_vs_breach(_load("rca_load_vs_sla")),
        "backlog": C.fig_backlog(_load("kpi_backlog_daily"), cfg["sla"]["aged_backlog_days"]),
        "weekly_flow": C.fig_weekly_flow(_load("kpi_backlog_daily")),
        "synth_validation": C.fig_synth_validation(_load("kpi_by_dimension"), _load("kpi_by_dimension_synth")),
        "erlang_curve": C.fig_erlang_curve(3.0, 11.5, 2, goal),
        "requirement_vs_roster": C.fig_requirement_vs_roster(_load("staff_coverage")),
        "gap_heatmap": C.fig_gap_heatmap(_load("staff_coverage")),
        "sim_queue": C.fig_sim_queue_week(_load("staff_sim_hourly"), _load("staff_demand")),
        "roster_sl": C.fig_roster_sl(_load("staff_sim_summary"), goal),
        "sensitivity": C.fig_sensitivity(_load("staff_sensitivity")),
        "growth": C.fig_growth(_load("staff_growth")),
        "automation_matrix": C.fig_automation_matrix(_load("topic_profile")),
        "hours_saved": C.fig_hours_saved(_load("automation_by_topic")),
        "options": C.fig_options(_load("business_options")),
        "email_alert": C.fig_email_alert(_load("rca_email_alert"), kn["response_sla_2023"], goal),
    }


def _table(df: pd.DataFrame, formats: dict | None = None) -> str:
    formats = formats or {}
    d = df.copy()
    for c, f in formats.items():
        if c in d:
            d[c] = d[c].map(lambda v, f=f: f.format(v) if pd.notna(v) else "")
    return d.to_html(index=False, border=0, classes="tbl", escape=True)


def _tables(kn: dict) -> dict:
    dq = _load("dq_checks")
    dq_view = dq[["check_id", "area", "check_name", "observed", "expected", "status", "action_taken"]].copy()
    dq_view["observed"] = dq_view["observed"].map(lambda v: f"{v:,.2f}".rstrip("0").rstrip("."))
    dq_view["expected"] = dq_view["expected"].map(lambda v: "" if pd.isna(v) else f"{v:,.0f}")
    opts = _load("business_options")
    opts_view = opts[["option", "what_changes", "fte", "one_off_cost_eur", "annual_cost_change_eur",
                      "first_year_cost_eur", "response_sl", "response_sl_sum"]].rename(columns={
        "response_sl": "response SLA (optimistic)", "response_sl_sum": "response SLA (conservative)"})
    roster = _load("staff_roster_table_proposed")
    today = _load("staff_roster_table_by_day")
    auto = _load("automation_summary")
    sens = _load("staff_sensitivity")[["parameter", "value", "fte_demand_shaped", "extra_fte_if_today_roster_kept"]]
    decomp = _load("kpi_rca_decomposition").query("sla_type == 'resolution' and comparison == 'Q1 -> Q4'")
    decomp = decomp.groupby("dimension")[["mix_effect", "rate_effect"]].sum().reset_index()
    decomp["total_change"] = decomp["mix_effect"] + decomp["rate_effect"]
    r = _load("staff_replications")
    reps = r.pivot(index="replication", columns="roster", values="response_sl")
    reps_sum = r.pivot(index="replication", columns="roster", values="response_sl_sum")
    reps = reps.join(reps_sum, rsuffix=" (cons.)")
    reps.columns = [c if c.endswith("(cons.)") else f"{c} (opt.)" for c in reps.columns]
    reps = reps.reset_index()
    return {
        "dq": _table(dq_view),
        "options": _table(opts_view, {"one_off_cost_eur": "€{:,.0f}", "annual_cost_change_eur": "€{:,.0f}",
                                      "first_year_cost_eur": "€{:,.0f}", "response SLA (optimistic)": "{:.1%}",
                                      "response SLA (conservative)": "{:.1%}"}),
        "roster_proposed": _table(roster),
        "roster_today": _table(today),
        "automation": _table(auto, {"deflected_share_of_tickets": "{:.1%}", "real_tickets_deflected_2023": "{:,.0f}",
                                    "scaled_tickets_deflected_year": "{:,.0f}", "agent_hours_saved_week": "{:,.1f}",
                                    "workload_reduction_share": "{:.1%}"}),
        "sensitivity": _table(sens),
        "decomposition": _table(decomp, {"mix_effect": "{:+.2%}", "rate_effect": "{:+.2%}", "total_change": "{:+.2%}"}),
        "replications": _table(reps, {c: "{:.2%}" for c in reps.columns if c != "replication"}),
        "recommendations": recommendations_table(kn),
    }


CSS = """
:root{--text:#1f1f1d;--text2:#52514e;--muted:#8a8984;--line:#e6e5e0;--bg:#ffffff;--soft:#f6f6f4;--accent:#2a78d6;
--real-bg:#e8f1fc;--real:#184f95;--syn-bg:#fdeee7;--syn:#9a3a12;}
*{box-sizing:border-box}
body{margin:0;background:var(--bg);color:var(--text);font:15px/1.6 Inter,-apple-system,BlinkMacSystemFont,'Segoe UI',Helvetica,Arial,sans-serif}
.wrap{max-width:1080px;margin:0 auto;padding:40px 24px 80px}
header.top{border-bottom:1px solid var(--line);padding-bottom:18px;margin-bottom:28px}
h1{font-size:30px;line-height:1.2;margin:0 0 6px;font-weight:700}
h2{font-size:22px;margin:48px 0 10px;padding-top:12px;border-top:1px solid var(--line)}
h3{font-size:17px;margin:28px 0 6px}
p{margin:8px 0 12px}
.meta{color:var(--text2);font-size:14px}
.badge{display:inline-block;padding:1px 8px;border-radius:4px;font-size:12px;font-weight:600;margin-right:6px}
.b-real{background:var(--real-bg);color:var(--real)}.b-syn{background:var(--syn-bg);color:var(--syn)}
.b-asm{background:#f0efec;color:#52514e}
.summary{background:var(--soft);border-radius:8px;padding:18px 22px;margin:18px 0}
.summary ol{margin:6px 0 0 18px;padding:0}.summary li{margin:6px 0}
.callout{border-left:3px solid var(--accent);background:#f6f9fe;padding:10px 14px;margin:14px 0}
.fig{margin:18px 0 6px;border:1px solid var(--line);border-radius:8px;padding:6px 8px;overflow:hidden}
.read{color:var(--text2);font-size:14px;margin:4px 2px 20px}
table.tbl{border-collapse:collapse;width:100%;font-size:13px;margin:10px 0 18px;display:block;overflow-x:auto}
table.tbl th{background:var(--soft);text-align:left;font-weight:600;padding:7px 9px;border-bottom:1px solid var(--line);white-space:nowrap}
table.tbl td{padding:6px 9px;border-bottom:1px solid var(--line);vertical-align:top}
nav.toc{columns:2;font-size:14px;margin:10px 0 0}nav.toc a{color:var(--accent);text-decoration:none}
code{background:var(--soft);padding:1px 5px;border-radius:4px;font-size:13px}
footer{margin-top:60px;color:var(--muted);font-size:13px;border-top:1px solid var(--line);padding-top:14px}
@media (max-width:700px){.wrap{padding:24px 16px 60px}h1{font-size:24px}nav.toc{columns:1}}
"""


def build(out_name: str = "report.html", export_png: bool = True) -> str:
    kn = json.load(open(reports_path("key_numbers.json")))
    figs = build_figures()
    tables = _tables(kn)
    cfg = {"displayModeBar": False, "responsive": True}

    def fig_html(name: str) -> str:
        return "<div class='fig'>" + pio.to_html(figs[name], include_plotlyjs=False, full_html=False,
                                                    config=cfg, default_width="100%") + "</div>"

    body, toc = [], []
    for sec in SECTIONS:
        toc.append(f"<a href='#{sec['id']}'>{html.escape(sec['title'])}</a><br>")
        body.append(f"<h2 id='{sec['id']}'>{html.escape(sec['title'])}</h2>")
        for block in sec["blocks"](kn):
            kind, val = block[0], block[1]
            if kind == "html":
                body.append(val)
            elif kind == "fig":
                body.append(fig_html(val))
                if len(block) > 2:
                    body.append(f"<p class='read'>{block[2]}</p>")
            elif kind == "table":
                body.append(tables[val])
    page = f"""<!doctype html><html lang="en"><head><meta charset="utf-8">
<meta name="viewport" content="width=device-width, initial-scale=1">
<title>Support SLA &amp; Capacity Review</title><style>{CSS}</style>
<script type="text/javascript">{get_plotlyjs()}</script></head><body><div class="wrap">
<header class="top"><h1>Support SLA &amp; Capacity Review</h1>
<div class="meta">Operations Analytics · prepared for the Support Director · data: ticket export
{kn['real_first_created']} to {kn['real_last_created']} (snapshot {kn['real_snapshot']}) · built {dt.date.today().isoformat()}</div>
<div style="margin-top:10px"><span class="badge b-real">REAL</span>numbers from the 2,330-ticket export
&nbsp; <span class="badge b-syn">SYNTHETIC</span>numbers from the 20x scale-up used for staffing
&nbsp; <span class="badge b-asm">ASSUMPTION</span>inputs not in the data</div>
<nav class="toc">{''.join(toc)}</nav></header>
{''.join(body)}
<footer>Generated by <code>python run.py</code> from <code>src/support_ops/report.py</code>. Charts are the same
functions used by the notebooks and the Streamlit app (<code>src/support_ops/charts.py</code>); numbers come from
<code>reports/key_numbers.json</code>.</footer></div></body></html>"""
    out = reports_path(out_name)
    out.write_text(page, encoding="utf-8")
    if export_png:
        for name in README_FIGURES:
            f = figs[name]
            f.write_image(str(reports_path("figures", f"{name}.png")), width=1100,
                          height=int(f.layout.height or 420), scale=1.6)
    return str(out)
