"""Every chart in the project, built once and reused by the notebooks, the HTML report
and the Streamlit app (so the three always show identical figures).

Conventions (one visual system):
  * title = what the chart shows; subtitle = the one-sentence takeaway + data source tag
    ([REAL] export or [SYNTHETIC] scale-up); axis titles carry units.
  * categorical colours in a fixed order (blue, orange, aqua, ...), never by rank;
    sequential = one blue ramp; over/under coverage = blue/red diverging with a grey midpoint.
  * one y-axis per chart, hairline grids, 2px lines, hover on every mark.
"""
from __future__ import annotations

import numpy as np
import pandas as pd
import plotly.graph_objects as go

# ---------------------------------------------------------------------------
# Visual system
# ---------------------------------------------------------------------------
SERIES = ["#2a78d6", "#eb6834", "#1baf7a", "#eda100", "#e87ba4", "#008300", "#6250d6", "#e34948"]
BLUE_RAMP = ["#f4f8fe", "#cde2fb", "#9ec5f4", "#6da7ec", "#3987e5", "#256abf", "#184f95", "#0d366b"]
DIVERGING = [[0.0, "#d03b3b"], [0.35, "#f2b8b5"], [0.5, "#f0efec"], [0.65, "#b7d3f6"], [1.0, "#1c5cab"]]
NEUTRAL = "#a3a29c"
GOAL = "#52514e"
SURFACE = "#ffffff"
TEXT = "#1f1f1d"
TEXT_2 = "#52514e"
GRID = "#ebeae6"
AXIS = "#d5d4cf"
FONT = "Inter, -apple-system, BlinkMacSystemFont, 'Segoe UI', Helvetica, Arial, sans-serif"

REAL = "REAL · 2023 export, 2,330 tickets"
SYNTH = "SYNTHETIC · 20x scale-up calibrated to the export"
DAYS = ["Mon", "Tue", "Wed", "Thu", "Fri", "Sat", "Sun"]


def _style(fig: go.Figure, title: str, takeaway: str, source: str, x_title: str = "",
           y_title: str = "", height: int = 420, legend: bool = True) -> go.Figure:
    fig.update_layout(
        title=dict(text=f"<b>{title}</b>", x=0, xanchor="left", y=0.97, yanchor="top",
                   font=dict(size=16, color=TEXT),
                   subtitle=dict(text=f"{takeaway}<br><span style='color:{NEUTRAL}'>{source}</span>",
                                 font=dict(size=12.5, color=TEXT_2))),
        font=dict(family=FONT, size=12.5, color=TEXT),
        paper_bgcolor=SURFACE, plot_bgcolor=SURFACE, height=height,
        margin=dict(l=60, r=24, t=112, b=56),
        hoverlabel=dict(bgcolor="white", bordercolor=AXIS, font=dict(family=FONT, size=12, color=TEXT)),
        showlegend=legend,
        legend=dict(orientation="h", x=0, xanchor="left", y=-0.16, yanchor="top",
                    font=dict(size=12, color=TEXT_2), bgcolor="rgba(0,0,0,0)"),
        bargap=0.35, bargroupgap=0.08,
    )
    fig.update_xaxes(title=dict(text=x_title, font=dict(size=12, color=TEXT_2)), showgrid=False,
                     linecolor=AXIS, ticks="outside", tickcolor=AXIS, tickfont=dict(color=TEXT_2),
                     zeroline=False)
    fig.update_yaxes(title=dict(text=y_title, font=dict(size=12, color=TEXT_2)), gridcolor=GRID,
                     gridwidth=1, linecolor=AXIS, tickfont=dict(color=TEXT_2), zeroline=False)
    return fig


def _goal_line(fig, y, text, row=None, col=None):
    fig.add_hline(y=y, line=dict(color=GOAL, width=1), annotation_text=text,
                  annotation_position="top left", annotation_font=dict(size=11, color=TEXT_2))


def pct(x, d=0):
    return f"{100 * x:.{d}f}%"


# ---------------------------------------------------------------------------
# Volume patterns  [REAL]
# ---------------------------------------------------------------------------
def fig_monthly_volume(monthly: pd.DataFrame) -> go.Figure:
    m = monthly.copy()
    m["month"] = pd.to_datetime(m["created_month"])
    days = m["month"].dt.days_in_month
    m["per_day"] = m["tickets"] / days
    se = np.sqrt(m["tickets"]) / days                     # Poisson standard error
    fig = go.Figure(go.Bar(
        x=m["month"], y=m["per_day"], marker=dict(color=SERIES[0], cornerradius=4),
        error_y=dict(type="data", array=1.96 * se, color=NEUTRAL, thickness=1, width=4),
        customdata=np.c_[m["tickets"]],
        hovertemplate="%{x|%b %Y}<br>%{y:.1f} tickets/day (%{customdata[0]} in month)<extra></extra>"))
    avg = m["tickets"].sum() / days.sum()
    _goal_line(fig, avg, f"2023 average {avg:.1f}/day")
    fig.update_xaxes(dtick="M1", tickformat="%b")
    return _style(fig, "Tickets per day, by month",
                  "Volume did not grow: every month sits within noise of the 6.4/day average "
                  "(bars = 95% Poisson interval).", REAL, "", "Tickets per day", legend=False)


def fig_volume_heatmap(heat: pd.DataFrame, value: str = "tickets_per_week") -> go.Figure:
    z = heat.pivot(index="dow_name", columns="hour", values=value).reindex(DAYS)
    label = "Tickets per week" if value == "tickets_per_week" else "Tickets (2023)"
    fig = go.Figure(go.Heatmap(
        z=z.values, x=[f"{h:02d}" for h in z.columns], y=z.index, colorscale=BLUE_RAMP,
        xgap=2, ygap=2, colorbar=dict(title=dict(text=label, side="right"), thickness=10, outlinewidth=0),
        hovertemplate="%{y} %{x}:00<br>%{z:.2f} " + label.lower() + "<extra></extra>"))
    fig.update_yaxes(autorange="reversed", showgrid=False)
    return _style(fig, "When tickets arrive: day of week x hour of day",
                  "Weekdays carry ~2.2x the weekend volume; within a day arrivals are almost flat "
                  "(no business-hours peak).", REAL, "Hour of day (ticket created)", "", height=380,
                  legend=False)


def fig_weekday_workload(rate: dict) -> go.Figure:
    created, resolved = rate["created_per_day"], rate["resolved_per_day"]
    fig = go.Figure()
    for i, (vals, name) in enumerate([(created, "New tickets per day"), (resolved, "Tickets resolved per day")]):
        fig.add_bar(x=DAYS, y=vals, name=name, marker=dict(color=SERIES[i], cornerradius=4),
                    hovertemplate="%{x}: %{y:.1f} per day<extra>" + name + "</extra>")
    return _style(fig, "New tickets vs resolutions by day of week",
                  f"Weekends get {rate['created_weekend_to_weekday']:.0%} of weekday arrivals but "
                  f"{rate['resolved_weekend_to_weekday']:.0%} of weekday resolutions: weekend workload "
                  "is much higher than ticket counts suggest.", REAL, "", "Tickets per day")


def fig_topic_pareto(pareto: pd.DataFrame, level: str = "topic") -> go.Figure:
    p = pareto[pareto["level"] == level].sort_values("rank")
    n_top = int(np.ceil(0.2 * len(p)))
    top_share = p["share"].head(n_top).sum()
    labels = p["category"].str.replace(" | ", "<br>", regex=False) if level != "topic" else p["category"]
    fig = go.Figure()
    fig.add_bar(x=labels, y=p["share"], name="Share of tickets",
                marker=dict(color=[SERIES[0] if r <= n_top else "#9ec5f4" for r in p["rank"]], cornerradius=4),
                customdata=np.c_[p["tickets"]],
                hovertemplate="%{x}<br>%{y:.1%} of tickets (%{customdata[0]})<extra></extra>")
    fig.add_scatter(x=labels, y=p["cum_share"], name="Cumulative share", mode="lines+markers",
                    line=dict(color=SERIES[1], width=2), marker=dict(size=7, line=dict(color=SURFACE, width=2)),
                    hovertemplate="Cumulative: %{y:.1%}<extra></extra>")
    fig.update_yaxes(tickformat=".0%", range=[0, 1.05])
    what = "topics" if level == "topic" else "topic x product combinations"
    return _style(fig, f"Pareto of ticket {what}",
                  f"Top 20% of {what} ({n_top} of {len(p)}) = {top_share:.0%} of tickets - volume is spread "
                  "out, far from an 80/20 pattern.", REAL, "", "Share of tickets (%)",
                  height=440 if level == "topic" else 520)


def fig_channel_mix(m: pd.DataFrame) -> go.Figure:
    """m: created_month, channel, share (support_ops.pipeline builds it as kpi_channel_mix)."""
    fig = go.Figure()
    for i, ch in enumerate(["Email", "Chat", "Phone"]):
        sub = m[m["channel"] == ch]
        fig.add_bar(x=sub["created_month"], y=sub["share"], name=ch, marker=dict(color=SERIES[i]),
                    hovertemplate="%{x|%b}: %{y:.0%}<extra>" + ch + "</extra>")
    fig.update_layout(barmode="stack", bargap=0.25)
    fig.update_yaxes(tickformat=".0%", range=[0, 1])
    fig.update_xaxes(dtick="M1", tickformat="%b")
    return _style(fig, "Channel mix by month",
                  "Email ~53%, chat ~36%, phone ~11% every month - the mix did not shift.", REAL,
                  "", "Share of tickets (%)")


# ---------------------------------------------------------------------------
# Efficiency & SLA  [REAL]
# ---------------------------------------------------------------------------
def fig_sla_trend(monthly: pd.DataFrame, goal: float = 0.90) -> go.Figure:
    m = monthly.copy()
    m["month"] = pd.to_datetime(m["created_month"])
    fig = go.Figure()
    for i, (k, name) in enumerate([("response", "Response SLA (first reply on time)"),
                                   ("resolution", "Resolution SLA (solved on time)")]):
        c = SERIES[i]
        fig.add_scatter(x=pd.concat([m["month"], m["month"][::-1]]),
                        y=pd.concat([m[f"{k}_attainment_hi"], m[f"{k}_attainment_lo"][::-1]]),
                        fill="toself", fillcolor=_rgba(c, 0.12),
                        line=dict(width=0), hoverinfo="skip", showlegend=False)
        fig.add_scatter(x=m["month"], y=m[f"{k}_attainment"], name=name, mode="lines+markers",
                        line=dict(color=c, width=2), marker=dict(size=7, line=dict(color=SURFACE, width=2)),
                        customdata=np.c_[m[f"{k}_attainment_lo"], m[f"{k}_attainment_hi"], m["tickets"]],
                        hovertemplate="%{x|%b %Y}: %{y:.1%}<br>95% CI %{customdata[0]:.1%}-%{customdata[1]:.1%}"
                                      " · %{customdata[2]} tickets<extra>" + name + "</extra>")
    _goal_line(fig, goal, f"Goal {goal:.0%}")
    fig.update_yaxes(tickformat=".0%", range=[0.5, 1.0])
    fig.update_xaxes(dtick="M1", tickformat="%b")
    first, last = m.iloc[0], m.iloc[-1]
    return _style(fig, "SLA attainment by month ticket was created",
                  f"Resolution SLA fell from {first['resolution_attainment']:.0%} (Jan) to "
                  f"{last['resolution_attainment']:.0%} (Dec); response SLA did not fall. Shaded = 95% CI.",
                  REAL, "", "Tickets meeting SLA (%)")


def _rgba(hex_color: str, a: float) -> str:
    h = hex_color.lstrip("#")
    return f"rgba({int(h[0:2], 16)},{int(h[2:4], 16)},{int(h[4:6], 16)},{a})"


def fig_resolution_composition(comp: pd.DataFrame) -> go.Figure:
    c = comp.copy()
    c["month"] = pd.to_datetime(c["created_month"])
    fig = go.Figure()
    parts = [("share_on_time", "Resolved within SLA", "#9ec5f4"),
             ("share_resolved_late", "Resolved late", SERIES[1]),
             ("share_never_resolved", "Never resolved (still open at snapshot)", "#52514e")]
    for col, name, color in parts:
        fig.add_bar(x=c["month"], y=c[col], name=name, marker=dict(color=color),
                    hovertemplate="%{x|%b}: %{y:.1%}<extra>" + name + "</extra>")
    fig.update_layout(barmode="stack", bargap=0.25)
    fig.update_yaxes(tickformat=".0%", range=[0, 1])
    fig.update_xaxes(dtick="M1", tickformat="%b")
    return _style(fig, "What happened to each month's tickets",
                  "The decline is 'resolved late' growing from ~7% to ~23% of tickets; 'never resolved' "
                  "is a constant ~13-23% every month.", REAL, "Month created", "Share of tickets created (%)")


def fig_resolution_time_hist(fct: pd.DataFrame) -> go.Figure:
    r = fct[fct["is_resolved"]]
    fig = go.Figure()
    for i, h in enumerate(["H1", "H2"]):
        sub = r[r["created_half"] == h]["resolution_h"]
        fig.add_histogram(x=sub, name=f"{h} 2023 (n={len(sub)})", xbins=dict(start=0, end=156, size=12),
                          histnorm="percent", marker=dict(color=SERIES[i], line=dict(color=SURFACE, width=2)),
                          opacity=0.85, hovertemplate="%{x} h: %{y:.1f}% of resolved tickets<extra></extra>")
    fig.add_vline(x=48, line=dict(color=GOAL, width=1), annotation_text="48 h target (email/phone)",
                  annotation_font=dict(size=11, color=TEXT_2))
    fig.add_vline(x=24, line=dict(color=NEUTRAL, width=1), annotation_text="24 h (chat)",
                  annotation_position="top left", annotation_font=dict(size=11, color=TEXT_2))
    fig.update_layout(barmode="group", bargap=0.1)
    over_h1 = (r[r.created_half == "H1"]["resolution_h"] > 48).mean()
    over_h2 = (r[r.created_half == "H2"]["resolution_h"] > 48).mean()
    return _style(fig, "How long resolved tickets took, first vs second half of 2023",
                  f"Most tickets still close within 2 days, but the slow tail (48-144 h) grew from "
                  f"{over_h1:.0%} to {over_h2:.0%} of resolved tickets.", REAL, "Hours from creation to resolution",
                  "Share of resolved tickets (%)")


def fig_breakdown(bydim: pd.DataFrame, dimension: str, sla: str = "resolution",
                  goal: float = 0.90) -> go.Figure:
    d = bydim[bydim["dimension"] == dimension].copy()
    d = d.sort_values("segment" if dimension in ("day_of_week", "hour_band", "quarter", "half")
                      else f"{sla}_attainment")
    col = f"{sla}_attainment"
    fig = go.Figure(go.Scatter(
        x=d[col], y=d["segment"], mode="markers", marker=dict(size=10, color=SERIES[0], line=dict(color=SURFACE, width=2)),
        error_x=dict(type="data", symmetric=False, array=d[f"{col}_hi"] - d[col],
                     arrayminus=d[col] - d[f"{col}_lo"], color=NEUTRAL, thickness=1.5, width=0),
        customdata=np.c_[d["tickets"], d[f"{col}_lo"], d[f"{col}_hi"]],
        hovertemplate="%{y}: %{x:.1%} (95% CI %{customdata[1]:.1%}-%{customdata[2]:.1%}, "
                      "%{customdata[0]} tickets)<extra></extra>"))
    overall = (bydim[bydim.dimension == dimension][col] * bydim[bydim.dimension == dimension]["tickets"]).sum() / \
        bydim[bydim.dimension == dimension]["tickets"].sum()
    fig.add_vline(x=overall, line=dict(color=GOAL, width=1), annotation_text=f"All tickets {overall:.1%}",
                  annotation_font=dict(size=11, color=TEXT_2))
    fig.update_xaxes(tickformat=".0%", showgrid=True, gridcolor=GRID)
    fig.update_yaxes(showgrid=False)
    nice = dimension.replace("_", " ")
    return _style(fig, f"{sla.title()} SLA attainment by {nice}",
                  "Dots = attainment, lines = 95% confidence interval. Overlapping intervals mean the "
                  "difference may be noise.", REAL, "Tickets meeting SLA (%)", "",
                  height=max(300, 120 + 38 * len(d)), legend=False)


def fig_hotspots(hot: pd.DataFrame, sla: str = "response", top: int = 12) -> go.Figure:
    h = hot[hot["sla_type"] == sla].sort_values("excess_breaches", ascending=False).head(top)
    h = h.iloc[::-1]
    colors = [SERIES[1] if s else "#cfcec9" for s in h["significant_fdr5"]]
    fig = go.Figure(go.Scatter(
        x=h["breach_rate"], y=h["combination"] + "  (n=" + h["n"].astype(str) + ")", mode="markers",
        marker=dict(size=10, color=colors, line=dict(color=SURFACE, width=2)),
        error_x=dict(type="data", symmetric=False, array=h["breach_rate_hi"] - h["breach_rate"],
                     arrayminus=h["breach_rate"] - h["breach_rate_lo"], color=NEUTRAL, thickness=1.5, width=0),
        customdata=np.c_[h["excess_breaches"], h["q_value"]],
        hovertemplate="%{y}<br>Breach rate %{x:.1%} · excess breaches %{customdata[0]:.1f} · "
                      "FDR q = %{customdata[1]:.3f}<extra></extra>"))
    overall = hot.loc[hot.sla_type == sla, "overall_rate"].iloc[0]
    fig.add_vline(x=overall, line=dict(color=GOAL, width=1), annotation_text=f"All tickets {overall:.1%}",
                  annotation_font=dict(size=11, color=TEXT_2))
    fig.update_xaxes(tickformat=".0%", showgrid=True, gridcolor=GRID)
    fig.update_yaxes(showgrid=False, tickfont=dict(size=11))
    n_sig = int(hot.loc[hot.sla_type == sla, "significant_fdr5"].sum())
    n_test = int((hot.sla_type == sla).sum())
    msg = (f"{n_sig} of {n_test} combinations survive a false-discovery-rate check (orange). "
           + ("All involve Phone, the channel with a 2-minute target." if sla == "response" and n_sig
              else "Breaches are spread evenly - no combination stands out."))
    return _style(fig, f"Where {sla} SLA breaches concentrate (top {top} by excess breaches)",
                  msg, REAL, "Breach rate (%)", "", height=150 + 34 * len(h), legend=False)


def fig_agent_scorecard(agents: pd.DataFrame, sla: str = "resolution") -> go.Figure:
    a = agents.sort_values(f"{sla}_attainment")
    col = f"{sla}_attainment"
    colors = [SERIES[0] if g == "1st line support" else SERIES[2] for g in a["agent_group"]]
    fig = go.Figure(go.Scatter(
        x=a[col], y=a["agent_name"], mode="markers", marker=dict(size=10, color=colors, line=dict(color=SURFACE, width=2)),
        error_x=dict(type="data", symmetric=False, array=a[f"{col}_hi"] - a[col],
                     arrayminus=a[col] - a[f"{col}_lo"], color=NEUTRAL, thickness=1.5, width=0),
        customdata=np.c_[a["tickets"], a["agent_group"]],
        hovertemplate="%{y} (%{customdata[1]}): %{x:.1%}, %{customdata[0]} tickets<extra></extra>",
        showlegend=False))
    for i, (g, c) in enumerate([("1st line support", SERIES[0]), ("2nd line support", SERIES[2])]):
        fig.add_scatter(x=[None], y=[None], mode="markers", marker=dict(size=10, color=c), name=g)
    team = (a[col] * a["tickets"]).sum() / a["tickets"].sum()
    fig.add_vline(x=team, line=dict(color=GOAL, width=1), annotation_text=f"Team {team:.1%}",
                  annotation_font=dict(size=11, color=TEXT_2))
    fig.update_xaxes(tickformat=".0%", showgrid=True, gridcolor=GRID)
    fig.update_yaxes(showgrid=False)
    return _style(fig, f"{sla.title()} SLA attainment by agent (current ticket owner)",
                  "Intervals overlap for 7 of 8 agents; the decline is team-wide, not a few people. "
                  "Agent = current owner, so use for coaching, not ratings.", REAL, "Tickets meeting SLA (%)", "",
                  height=420)


def fig_breach_lateness(fct: pd.DataFrame) -> go.Figure:
    b = fct[(fct["response_sla_met"] == False) & fct["frt_min"].notna()].copy()  # noqa: E712
    b["late"] = b["frt_min"] - b["response_target_min"]
    fig = go.Figure()
    for i, ch in enumerate(["Chat", "Phone", "Email"]):
        sub = b[b["channel"] == ch]["late"].clip(lower=0.05)
        fig.add_box(x=sub, name=f"{ch} (n={len(sub)})", orientation="h", marker=dict(color=SERIES[i], size=5),
                    line=dict(color=SERIES[i], width=1.5), fillcolor=_rgba(SERIES[i], 0.12), boxpoints="all",
                    jitter=0.4, pointpos=0, hovertemplate="%{x:.1f} min late<extra>" + ch + "</extra>")
    fig.update_xaxes(type="log", tickvals=[0.1, 1, 2, 5, 15, 60, 240, 1440],
                     ticktext=["0.1", "1", "2", "5", "15", "60", "240", "1,440"], showgrid=True, gridcolor=GRID)
    return _style(fig, "How late are first-response breaches?",
                  "Chat/phone breaches are ~2 minutes late (slow pickup); email breaches are ~3.5 hours late "
                  "(missed, not queued). Neither looks like a queue of tickets waiting for agents.",
                  REAL, "Minutes past the response target (log scale)", "", height=360, legend=False)


def fig_load_vs_breach(load: pd.DataFrame, measure: str = "tickets in progress at arrival") -> go.Figure:
    d = load[load["load_measure"] == measure]
    fig = go.Figure()
    for i, sla in enumerate(["response", "resolution"]):
        s = d[d["sla"] == sla]
        p = s["trend_p_value"].iloc[0]
        fig.add_scatter(x=s["quintile"].astype(str) + "<br>" + s["load_range"], y=s["breach_rate"],
                        name=f"{sla.title()} breach rate (trend p = {p:.2f})", mode="lines+markers",
                        line=dict(color=SERIES[i], width=2), marker=dict(size=8, line=dict(color=SURFACE, width=2)),
                        error_y=dict(type="data", symmetric=False, array=s["breach_rate_hi"] - s["breach_rate"],
                                     arrayminus=s["breach_rate"] - s["breach_rate_lo"], color=_rgba(SERIES[i], 0.5),
                                     thickness=1.5, width=4),
                        hovertemplate="Quintile %{x}: %{y:.1%}<extra>" + sla + "</extra>")
    fig.update_yaxes(tickformat=".0%", rangemode="tozero")
    return _style(fig, "Do tickets that arrive into a busier desk breach more?",
                  "No: breach rates are flat across load quintiles (trend tests not significant). "
                  "There is no sign that capacity ran out in 2023.", REAL,
                  f"Load quintile ({measure})", "Breach rate (%)")


# ---------------------------------------------------------------------------
# Backlog  [REAL] + [SYNTHETIC]
# ---------------------------------------------------------------------------
def fig_backlog(backlog: pd.DataFrame, aged_days: int = 7) -> go.Figure:
    b = backlog.copy()
    b["day"] = pd.to_datetime(b["day"])
    fig = go.Figure()
    fig.add_scatter(x=b["day"], y=b["open_active"], name=f"Active (open <= {aged_days} days)", stackgroup="one",
                    line=dict(color=SERIES[0], width=1.5), fillcolor=_rgba(SERIES[0], 0.35),
                    hovertemplate="%{x|%d %b}: %{y} active<extra></extra>")
    fig.add_scatter(x=b["day"], y=b["open_aged"], name=f"Aged (open > {aged_days} days)", stackgroup="one",
                    line=dict(color="#52514e", width=1.5), fillcolor=_rgba("#52514e", 0.25),
                    hovertemplate="%{x|%d %b}: %{y} aged<extra></extra>")
    return _style(fig, "Open tickets at the end of each day",
                  f"The backlog grows only because of aged tickets nobody closes; active work stays at "
                  f"~{b['open_active'].mean():.0f} tickets (max {b['open_active'].max()}).", REAL, "",
                  "Open tickets")


def fig_weekly_flow(backlog: pd.DataFrame) -> go.Figure:
    b = backlog.copy()
    b["week"] = pd.to_datetime(b["day"]).dt.to_period("W-SUN").dt.start_time
    w = b.groupby("week")[["arrivals", "resolutions"]].sum().iloc[1:-1]
    fig = go.Figure()
    for i, (c, name) in enumerate([("arrivals", "Tickets created"), ("resolutions", "Tickets resolved")]):
        fig.add_scatter(x=w.index, y=w[c], name=name, mode="lines", line=dict(color=SERIES[i], width=2),
                        hovertemplate="Week of %{x|%d %b}: %{y}<extra>" + name + "</extra>")
    gap = (w["arrivals"] - w["resolutions"]).mean()
    return _style(fig, "Weekly arrivals vs resolutions",
                  f"Resolutions track arrivals week by week; the steady gap (~{gap:.0f}/week) is the tickets that "
                  "are never resolved, not arrival spikes.", REAL, "", "Tickets per week")


def fig_sim_queue_week(sim_hourly: pd.DataFrame, demand: pd.DataFrame, rosters=("by_day", "proposed"),
                       week_start_hour: int = 24 * 15) -> go.Figure:
    names = {"by_day": "Today's roster (assumed weekday-weighted)", "proposed": "Proposed demand-shaped roster",
             "flat": "Flat 24/7", "business_hours": "Day-weighted"}
    t0 = pd.Timestamp("2023-01-01")
    fig = go.Figure()
    for i, r in enumerate(rosters):
        h = sim_hourly[sim_hourly["roster"] == r].iloc[week_start_hour: week_start_hour + 168]
        ts = t0 + pd.to_timedelta(h["hour_index"], unit="h")
        fig.add_scatter(x=ts, y=h["queue_len"], name=names.get(r, r), mode="lines",
                        line=dict(color=SERIES[i], width=2, shape="hv"),
                        hovertemplate="%{x|%a %H:00}: %{y} items waiting<extra>" + names.get(r, r) + "</extra>")
    fig.update_xaxes(dtick=24 * 3600 * 1000, tickformat="%a %d %b")
    return _style(fig, "Work items waiting for an agent, one simulated week",
                  "Arrivals are flat, so a queue that builds on weekends is a staffing gap, not a volume spike. "
                  "The demand-shaped roster keeps the queue short all week.", SYNTH, "",
                  "Items waiting (snapshot each hour)")


# ---------------------------------------------------------------------------
# Staffing model  [SYNTHETIC]
# ---------------------------------------------------------------------------
def _how_labels(df):
    return [f"{d} {h:02d}" for d, h in zip(df["dow_name"], df["hour"])]


def fig_requirement_vs_roster(cov: pd.DataFrame, rosters=("by_day", "proposed")) -> go.Figure:
    names = {"by_day": "Today's roster (assumed weekday-weighted)", "proposed": "Proposed roster",
             "flat": "Today (alt.): flat 24/7", "business_hours": "Today (alt.): day-weighted"}
    x = np.arange(168)
    fig = go.Figure()
    fig.add_scatter(x=x, y=cov["scheduled_required"], name="Required (Erlang C + shrinkage)", mode="lines",
                    line=dict(color=TEXT, width=2, shape="hv"), text=_how_labels(cov),
                    hovertemplate="%{text}: %{y} agents required<extra></extra>")
    for i, r in enumerate(rosters):
        fig.add_scatter(x=x, y=cov[f"scheduled_{r}"], name=names.get(r, r), mode="lines",
                        line=dict(color=SERIES[i], width=2, shape="hv"), text=_how_labels(cov),
                        hovertemplate="%{text}: %{y:.0f} scheduled<extra>" + names.get(r, r) + "</extra>")
    fig.update_xaxes(tickvals=list(range(0, 168, 24)), ticktext=DAYS, range=[0, 168])
    fig.update_yaxes(rangemode="tozero", dtick=1)
    under = int((cov[f"scheduled_{rosters[0]}"] < cov["scheduled_required"]).sum())
    return _style(fig, "Agents needed vs agents scheduled, every hour of the week",
                  f"Same headcount: today's assumed roster is short in {under} of 168 hours (weekends, where "
                  "follow-up work continues); the proposed roster covers every hour.", SYNTH,
                  "Hour of week", "Agents scheduled (people on shift)", height=440)


def fig_gap_heatmap(cov: pd.DataFrame, roster: str = "by_day") -> go.Figure:
    g = cov.assign(gap=cov[f"scheduled_{roster}"] - cov["scheduled_required"])
    z = g.pivot(index="dow_name", columns="hour", values="gap").reindex(DAYS)
    lim = max(2, float(np.abs(z.values).max()))
    fig = go.Figure(go.Heatmap(
        z=z.values, x=[f"{h:02d}" for h in z.columns], y=z.index, colorscale=DIVERGING, zmid=0,
        zmin=-lim, zmax=lim, xgap=2, ygap=2,
        colorbar=dict(title=dict(text="Agents vs need", side="right"), thickness=10, outlinewidth=0),
        hovertemplate="%{y} %{x}:00: %{z:+.0f} agents vs requirement<extra></extra>"))
    fig.update_yaxes(autorange="reversed", showgrid=False)
    return _style(fig, "Coverage gap by hour: today's assumed roster minus requirement",
                  "Red = short of agents, blue = more than needed. Today's assumed roster puts spare people on "
                  "weekdays and runs short at weekends.", SYNTH, "Hour of day", "", height=360, legend=False)


def fig_roster_sl(sim: pd.DataFrame, goal: float = 0.90) -> go.Figure:
    order = ["business_hours", "by_day", "flat", "proposed", "hire_by_day"]
    names = {"business_hours": "Today (alt.):<br>day-weighted", "by_day": "Today (assumed):<br>weekday-weighted",
             "flat": "Today (alt.):<br>flat 24/7", "proposed": "Proposed:<br>demand-shaped",
             "hire_by_day": "Hire: today's roster<br>+ extra FTE"}
    s = sim.set_index("roster").reindex([o for o in order if o in set(sim["roster"])])
    colors = [SERIES[0] if r == "proposed" else ("#9ec5f4" if r.startswith("hire") else "#cfcec9") for r in s.index]
    fig = go.Figure(go.Bar(
        x=[names[r] for r in s.index], y=s["response_sl"], marker=dict(color=colors, cornerradius=4),
        text=[f"{v:.1%}<br>{int(f)} FTE" for v, f in zip(s["response_sl"], s["fte"])], textposition="outside",
        textfont=dict(color=TEXT, size=12),
        customdata=np.c_[s["queue_sl"], s["process_sl"], s["fte"]],
        hovertemplate="%{x}<br>Response SLA %{y:.1%}<br>Queue on time %{customdata[0]:.1%} · pickup on time "
                      "%{customdata[1]:.1%} · %{customdata[2]} FTE<extra></extra>"))
    floor = float(s["process_sl"].iloc[0])
    fig.add_hline(y=floor, line=dict(color=SERIES[1], width=1.5),
                  annotation_text=f"Process ceiling {floor:.1%} (pickup delays, no queue)",
                  annotation_position="top left", annotation_font=dict(size=11, color=TEXT_2))
    _goal_line(fig, goal, f"Goal {goal:.0%}")
    fig.update_yaxes(tickformat=".0%", range=[0.75, 0.95])
    gain = s.loc["proposed", "response_sl"] - s.loc["by_day", "response_sl"]
    return _style(fig, "Simulated response SLA by roster (same synthetic year)",
                  f"Re-rostering the same people lifts response SLA by {gain * 100:.1f} points to the process "
                  "ceiling; no roster can beat the ceiling - only faster pickup can.", SYNTH, "",
                  "Tickets answered on time (%)", height=460, legend=False)


def fig_sensitivity(sens: pd.DataFrame) -> go.Figure:
    base = int(sens.iloc[0]["fte_demand_shaped"])
    s = sens.iloc[1:].copy()
    s["label"] = s["parameter"] + ": " + s["value"]
    s = s.sort_values("delta_fte_vs_base", key=np.abs)
    colors = [SERIES[1] if d > 0 else (SERIES[0] if d < 0 else "#cfcec9") for d in s["delta_fte_vs_base"]]
    fig = go.Figure(go.Bar(
        y=s["label"], x=s["delta_fte_vs_base"], orientation="h", marker=dict(color=colors, cornerradius=4),
        customdata=np.c_[s["fte_demand_shaped"], s["extra_fte_if_today_roster_kept"]],
        text=[f"{int(v):d} FTE" for v in s["fte_demand_shaped"]], textposition="outside",
        textfont=dict(size=11, color=TEXT_2),
        hovertemplate="%{y}<br>%{customdata[0]} FTE needed (%{x:+d} vs base)<br>"
                      "Extra FTE if today's roster is kept: %{customdata[1]}<extra></extra>"))
    fig.add_vline(x=0, line=dict(color=TEXT, width=1))
    fig.update_xaxes(showgrid=True, gridcolor=GRID, zeroline=False)
    fig.update_yaxes(showgrid=False, tickfont=dict(size=11))
    return _style(fig, f"Sensitivity: FTE needed vs the base case ({base} FTE)",
                  "Handle time and what 'interactions' means move the answer most; the SLA goal barely matters "
                  "because total workload, not the 2-minute live target, sets headcount.", SYNTH,
                  "Change in FTE needed vs base case", "", height=520, legend=False)


def fig_growth(growth: pd.DataFrame) -> go.Figure:
    fig = go.Figure()
    for i, (lvl, name) in enumerate([("none", "Proposed roster, no deflection"),
                                     ("base", "Proposed roster + self-service (base deflection)")]):
        g = growth[growth["deflection"] == lvl]
        fig.add_scatter(x=(g["volume_factor"] - 1), y=g["response_sl"], name=name, mode="lines+markers",
                        line=dict(color=SERIES[i], width=2), marker=dict(size=7, line=dict(color=SURFACE, width=2)),
                        hovertemplate="Volume %{x:+.0%}: response SLA %{y:.1%}<extra>" + name + "</extra>")
    floor = growth["process_sl"].mean()
    fig.add_hline(y=floor, line=dict(color=SERIES[1], width=1, dash="solid"),
                  annotation_text=f"Process ceiling {floor:.1%}", annotation_position="bottom left",
                  annotation_font=dict(size=11, color=TEXT_2))
    fig.update_xaxes(tickformat="+.0%")
    fig.update_yaxes(tickformat=".0%")
    return _style(fig, "How much volume growth the same 24 FTE can absorb",
                  "With today's headcount re-rostered, SLA holds near the ceiling for modest growth; "
                  "deflection buys extra headroom before a hire is needed.", SYNTH,
                  "Ticket volume vs 2023", "Response SLA (%)")


def fig_erlang_curve(lam: float, aht: float, target_min: float, goal: float, max_agents: int = 12) -> go.Figure:
    from .erlang import service_level, traffic_intensity
    a = traffic_intensity(lam, aht)
    ns = list(range(max(1, int(np.floor(a)) + 1), max_agents + 1))
    sl = [service_level(n, a, aht, target_min) for n in ns]
    occ = [a / n for n in ns]
    fig = go.Figure(go.Bar(x=ns, y=sl, marker=dict(color=[SERIES[0] if v >= goal else "#cfcec9" for v in sl],
                                                   cornerradius=4),
                           customdata=np.c_[occ], text=[f"{v:.0%}" for v in sl], textposition="outside",
                           textfont=dict(size=11, color=TEXT_2),
                           hovertemplate="%{x} agents: %{y:.1%} answered within target · occupancy "
                                         "%{customdata[0]:.0%}<extra></extra>"))
    _goal_line(fig, goal, f"Goal {goal:.0%}")
    fig.update_yaxes(tickformat=".0%", range=[0, 1.12])
    fig.update_xaxes(dtick=1)
    return _style(fig, "Erlang C: service level for each extra agent",
                  f"{lam:.1f} contacts/hour x {aht:.1f} min = {a:.2f} agents of work. Each extra agent buys less "
                  "service level than the one before.", "Illustration of the formula used in the model",
                  "Productive agents on duty", f"Answered within {target_min:g} min (%)", height=380, legend=False)


# ---------------------------------------------------------------------------
# Automation & business case
# ---------------------------------------------------------------------------
def fig_automation_matrix(profile: pd.DataFrame) -> go.Figure:
    p = profile.copy()
    fig = go.Figure(go.Scatter(
        x=p["share"], y=p["complexity_index"], mode="markers+text", text=p["topic"], textposition="top center",
        textfont=dict(size=11, color=TEXT),
        marker=dict(size=10 + 60 * p["deflection_base"], color=_rgba(SERIES[0], 0.75),
                    line=dict(color=SURFACE, width=2)),
        customdata=np.c_[p["tickets"], p["deflection_base"], p["tier2_share"], p["interactions_mean"]],
        hovertemplate="%{text}<br>%{x:.1%} of tickets (%{customdata[0]})<br>Complexity index %{y:.2f} · "
                      "tier-2 %{customdata[2]:.0%} · %{customdata[3]:.1f} interactions<br>"
                      "Base deflection assumption %{customdata[1]:.0%}<extra></extra>"))
    fig.update_xaxes(tickformat=".0%", showgrid=True, gridcolor=GRID, rangemode="tozero")
    fig.update_yaxes(range=[0, 1.05])
    return _style(fig, "Automation candidates: volume vs complexity",
                  "Bubble size = assumed deflection. Pricing/licensing and invoicing are high-volume and among the "
                  "least complex; feature requests can be routed out of support entirely.", REAL,
                  "Share of tickets (%)", "Complexity index (0 = simplest topic)", height=460, legend=False)


def fig_hours_saved(by_topic: pd.DataFrame) -> go.Figure:
    piv = by_topic.pivot(index="topic", columns="level", values="agent_hours_saved_week")
    piv = piv[piv["high"] > 0].sort_values("base")
    fig = go.Figure(go.Bar(
        y=piv.index, x=piv["base"], orientation="h", marker=dict(color=SERIES[0], cornerradius=4),
        error_x=dict(type="data", symmetric=False, array=piv["high"] - piv["base"],
                     arrayminus=piv["base"] - piv["low"], color=NEUTRAL, thickness=1.5, width=4),
        customdata=np.c_[piv["low"], piv["high"]],
        hovertemplate="%{y}: %{x:.0f} agent-hours/week (range %{customdata[0]:.0f}-%{customdata[1]:.0f})"
                      "<extra></extra>"))
    total = by_topic.groupby("level")["agent_hours_saved_week"].sum()
    fig.update_xaxes(showgrid=True, gridcolor=GRID)
    fig.update_yaxes(showgrid=False)
    return _style(fig, "Agent-hours saved per week by topic (base case, low-high range)",
                  f"~{total['base']:.0f} agent-hours/week in the base case ({total['low']:.0f}-{total['high']:.0f}); "
                  "deflection rates are assumptions to validate with a pilot.", SYNTH,
                  "Agent-hours saved per week", "", height=380, legend=False)


def fig_options(opts: pd.DataFrame) -> go.Figure:
    o = opts.copy()
    fig = go.Figure()
    fig.add_bar(x=o["option"], y=o["response_sl"], name="Response SLA (simulated)",
                marker=dict(color=[SERIES[0] if x.startswith("B") else "#cfcec9" for x in o["option"]],
                            cornerradius=4),
                text=[f"{v:.1%}<br>{int(c / 1000):,}k EUR yr 1" for v, c in zip(o["response_sl"],
                                                                         o["first_year_cost_eur"])],
                textposition="outside", textfont=dict(size=11, color=TEXT),
                customdata=np.c_[o["fte"], o["one_off_cost_eur"], o["annual_cost_change_eur"], o["what_changes"]],
                hovertemplate="%{x}<br>%{customdata[3]}<br>Response SLA %{y:.1%} · %{customdata[0]} FTE<br>"
                              "One-off %{customdata[1]:,.0f} EUR · recurring %{customdata[2]:+,.0f} EUR/yr"
                              "<extra></extra>")
    fig.update_yaxes(tickformat=".0%", range=[0.80, 0.92])
    return _style(fig, "Options: response SLA and first-year cost",
                  "Re-rostering reaches the same SLA as hiring, at no cost. Automation adds headroom; none of the "
                  "options moves the process ceiling - that needs the pickup fixes.", SYNTH, "",
                  "Response SLA (%)", height=440, legend=False)


def fig_email_alert(alert: pd.DataFrame, now: float, goal: float = 0.90) -> go.Figure:
    a = alert.copy()
    x = ["Today"] + [f"Alert catches<br>{c:.0%} of late emails" for c in a["catch_rate"]]
    y = [now] + a["response_sl_after"].tolist()
    fig = go.Figure(go.Bar(x=x, y=y, marker=dict(color=["#cfcec9"] + [SERIES[0]] * len(a), cornerradius=4),
                           text=[f"{v:.1%}" for v in y], textposition="outside", textfont=dict(color=TEXT),
                           hovertemplate="%{x}: %{y:.1%}<extra></extra>"))
    _goal_line(fig, goal, f"Goal {goal:.0%}")
    fig.update_yaxes(tickformat=".0%", range=[0.80, 0.95])
    return _style(fig, "Response SLA with an 'unanswered at 45 minutes' email alert",
                  "Email breaches are hours late, so a reminder before the 60-minute deadline targets them "
                  "directly. Catch rates are assumptions; the breach counts are real.", REAL, "",
                  "Tickets answered on time (%)", height=400, legend=False)


def fig_synth_validation(real_bydim: pd.DataFrame, synth_bydim: pd.DataFrame,
                         dims=("channel", "topic", "priority")) -> go.Figure:
    rows = []
    for d in dims:
        r = real_bydim[real_bydim.dimension == d].set_index("segment")["share_of_tickets"]
        s = synth_bydim[synth_bydim.dimension == d].set_index("segment")["share_of_tickets"]
        for seg in r.index:
            rows.append({"label": f"{seg}", "dim": d, "real": r[seg], "synth": s.get(seg, np.nan)})
    v = pd.DataFrame(rows)
    fig = go.Figure()
    for i, (c, name) in enumerate([("real", "Real export"), ("synth", "Synthetic scale-up")]):
        fig.add_bar(x=v["label"], y=v[c], name=name, marker=dict(color=SERIES[i], cornerradius=4),
                    hovertemplate="%{x}: %{y:.1%}<extra>" + name + "</extra>")
    fig.update_yaxes(tickformat=".0%")
    gap = (v["real"] - v["synth"]).abs().max()
    return _style(fig, "Synthetic scale-up vs real export: ticket mix",
                  f"Every channel, topic and priority share matches within {gap * 100:.1f} points.",
                  "REAL vs SYNTHETIC", "", "Share of tickets (%)", height=420)
