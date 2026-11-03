import components as ui
import pandas as pd
import streamlit as st

from support_ops import charts as C
from support_ops import interactive

# Backlog Diagnosis. REAL: daily open backlog (re-run in DuckDB for any "aged" threshold), weekly flow,
# breach rate vs load, mix-vs-rate decomposition. SYNTHETIC: one simulated week of the 20x scale-up.

ui.page_header("Backlog Diagnosis",
               "Is work piling up because of volume spikes, or because capacity can't keep up?",
               "REAL", "SYNTHETIC")

k = ui.key_numbers()
cfg = ui.config()

ROSTERS = {"by_day": "Today (assumed): weekday-weighted", "flat": "Today (alt.): flat 24/7",
           "business_hours": "Today (alt.): day-weighted"}
ROSTERS_PROSE = {"by_day": "today's assumed weekday-weighted roster", "flat": "a flat 24/7 roster",
                 "business_hours": "a day-weighted roster"}
LOAD_MEASURES = ["tickets in progress at arrival", "tickets created the same day"]
DIMENSIONS = {"channel": "Channel", "topic": "Topic", "priority": "Priority", "agent_group": "Tier (agent group)"}
T0 = pd.Timestamp("2023-01-01")          # hour index 0 of the simulation (a Sunday)


@st.cache_data(show_spinner=False, max_entries=64)
def backlog(aged_days: int) -> pd.DataFrame:
    """Daily backlog split re-run in DuckDB (sql/04_backlog_daily.sql) with a different 'aged' threshold."""
    b = interactive.backlog_with_threshold(aged_days)
    counts = ["open_0_2d", "open_2d_to_threshold", "open_aged", "open_never_resolved", "open_active"]
    return b.astype({c: "int64" for c in counts})      # DuckDB returns these counts as floats


ui.takeaway(
    "Work is not piling up from volume spikes, and throughput keeps pace with arrivals. The open backlog grows only "
    f"because <b>{k['stale_never_resolved']} tickets are never closed</b>; active work stays flat at "
    f"~{k['active_backlog_mean']:.0f} tickets (max {k['active_backlog_max']}), as Little's law predicts "
    f"(~{k['active_backlog_littles_law']:.0f}), and breach rates do not rise when the desk is busier "
    f"(trend p = {k['rca_load_trend_p_min']:.2f}-{k['rca_load_trend_p_max']:.2f}). In the synthetic scale-up, a "
    "queue builds only where an assumed roster has too few people, not when volume spikes.")

# ---------------------------------------------------------------------------------------------------------
st.subheader("Open backlog: active work vs aged tickets")
c1, _ = st.columns([2, 3])
with c1:
    aged = st.slider("Count a ticket as aged after N days", 2, 30, int(cfg["sla"]["aged_backlog_days"]), 1,
                     format="%d days", key="p5_aged_days",
                     help="Re-runs the backlog SQL with this threshold. Default "
                          f"{cfg['sla']['aged_backlog_days']} days (config.yaml).")
b = backlog(aged)
snap = b.iloc[-1]
m = st.columns(4)
m[0].metric("Open at snapshot (tickets)", f"{int(snap['open_total']):,}",
            help=f"Tickets still open when the export was taken ({k['real_snapshot']}).")
m[1].metric(f"Aged > {aged} days (tickets)", f"{int(snap['open_aged']):,}",
            help="Open at the snapshot and older than the threshold.")
m[2].metric("Active backlog, mean (tickets)", f"{b['open_active'].mean():.1f}",
            help="Open tickets younger than the threshold at the end of each day, 2 Jan 2023 to the snapshot.")
m[3].metric("Active backlog, max (tickets)", f"{int(b['open_active'].max())}")
ui.show(C.fig_backlog(b, aged), key="p5_backlog")
day = pd.to_datetime(b["day"])
h1 = b.loc[day < "2023-07-01", "open_active"].mean()
h2 = b.loc[(day >= "2023-07-01") & (day < "2024-01-01"), "open_active"].mean()
st.caption(f"REAL. Re-computed in DuckDB (sql/04_backlog_daily.sql) with a {aged}-day threshold. Active backlog "
           f"averaged {h1:.1f} tickets a day in H1 and {h2:.1f} in H2 (computed from this table): flat at any "
           f"threshold. The never-resolved tickets had a median age of {k['stale_median_age_days']:.0f} days at "
           "the snapshot.")

# ---------------------------------------------------------------------------------------------------------
st.subheader("Is throughput keeping up with arrivals?")
ui.show(C.fig_weekly_flow(ui.load("kpi_backlog_daily")), key="p5_weekly_flow")

# ---------------------------------------------------------------------------------------------------------
st.subheader("Load test: is there a capacity signal?")
load = ui.load("rca_load_vs_sla")
c1, _ = st.columns([3, 2])
with c1:
    measure = st.radio("How busy the desk was when the ticket arrived", LOAD_MEASURES, horizontal=True,
                       key="p5_load_measure", format_func=str.capitalize)
ui.show(C.fig_load_vs_breach(load, measure), key="p5_load_vs_breach")
p = load[load["load_measure"] == measure].groupby("sla")["trend_p_value"].first()
st.caption(f"REAL. Cochran-Armitage trend test for this measure: response p = {p['response']:.2f}, resolution "
           f"p = {p['resolution']:.2f}. Across both measures and both SLAs, p = {k['rca_load_trend_p_min']:.2f}-"
           f"{k['rca_load_trend_p_max']:.2f}: no evidence that breaches rise with load. A capacity change outside "
           "the ticket data (time diverted to other work, tooling) cannot be excluded.")

# ---------------------------------------------------------------------------------------------------------
st.subheader("Mix or rate: did the ticket mix change, or performance within segments?")
c1, c2, _ = st.columns([1, 1, 2])
with c1:
    comparison = st.selectbox("Comparison", ["Q1 -> Q4", "H1 -> H2"], key="p5_decomp_comparison",
                              format_func=lambda s: s.replace("->", "→"))
with c2:
    sla = st.radio("SLA", ["resolution", "response"], horizontal=True, key="p5_decomp_sla",
                   format_func=str.capitalize)
dec = ui.load("kpi_rca_decomposition")
d = dec[(dec["comparison"] == comparison) & (dec["sla_type"] == sla)]
t = d.groupby("dimension", as_index=False)[["mix_effect", "rate_effect"]].sum()
t["total_change"] = t["mix_effect"] + t["rate_effect"]
t[["mix_effect", "rate_effect", "total_change"]] = t[["mix_effect", "rate_effect", "total_change"]] * 100
t["dimension"] = t["dimension"].map(DIMENSIONS)
t = t.sort_values("dimension")
st.dataframe(t, hide_index=True, width="stretch", column_config={
    "dimension": st.column_config.TextColumn("Tickets grouped by"),
    "mix_effect": st.column_config.NumberColumn("Mix effect (pts)", format="%+.2f",
                                                help="Change explained by a different share of tickets per segment"),
    "rate_effect": st.column_config.NumberColumn("Rate effect (pts)", format="%+.2f",
                                                 help="Change explained by attainment within each segment"),
    "total_change": st.column_config.NumberColumn("Total change (pts)", format="%+.2f")})
start_label, end_label = comparison.split(" -> ")
st.markdown(
    f"{sla.capitalize()} SLA attainment changed by **{t['total_change'].iloc[0]:+.1f} points** from {start_label} "
    f"to {end_label}. Shifts in the ticket mix explain {t['mix_effect'].min():+.2f} to {t['mix_effect'].max():+.2f} "
    f"points, depending on how tickets are grouped; the rest ({t['rate_effect'].min():+.1f} to "
    f"{t['rate_effect'].max():+.1f}) is a change in attainment within segments.")
st.caption("REAL. Shift-share decomposition, sql/08_rca_decomposition.sql. Mix + rate = total change for every "
           "grouping.")

# ---------------------------------------------------------------------------------------------------------
st.subheader("Simulated queue: volume spike or staffing gap?")
ui.badges("SYNTHETIC")
c1, c2, _ = st.columns([2, 2, 1])
with c1:
    week = st.slider("Week of the synthetic year", 1, 50, 3, 1, key="p5_week",
                     help="Week 1 starts on Monday 2 January 2023.")
with c2:
    roster = st.selectbox("Roster to compare with the proposed roster", list(ROSTERS), key="p5_roster",
                          format_func=ROSTERS.get)
sim = ui.load("staff_sim_hourly")
start = 24 * (1 + 7 * (week - 1))      # hour 24 = Monday 2 Jan 00:00
ui.show(C.fig_sim_queue_week(sim, ui.load("staff_demand"), rosters=(roster, "proposed"), week_start_hour=start),
        key="p5_sim_queue")


def weekend_vs_weekday(r: str) -> tuple[float, float]:
    h = sim[sim["roster"] == r].iloc[start: start + 168]
    weekend = (T0 + pd.to_timedelta(h["hour_index"], unit="h")).dt.day_of_week >= 5
    return float(h.loc[weekend, "queue_len"].mean()), float(h.loc[~weekend, "queue_len"].mean())


(we_r, wd_r), (we_p, wd_p) = weekend_vs_weekday(roster), weekend_vs_weekday("proposed")
st.caption(f"SYNTHETIC. Week {week} starts Monday {T0 + pd.Timedelta(hours=start):%d %b %Y}. Average items waiting at "
           f"weekends vs weekdays: {we_r:.1f} vs {wd_r:.1f} under {ROSTERS_PROSE[roster]}; {we_p:.1f} vs {wd_p:.1f} "
           "under the proposed roster. Arrivals follow the same weekly pattern every week, so a queue that builds "
           "under one roster only, at the hours it has fewer people, is a staffing gap. A volume spike would raise "
           "the queue under every roster at the same time.")

ui.how_to_read(f"""
- **Open backlog.** Each day the stacked areas count tickets still open at midnight. Blue is active work
  (younger than the threshold); grey is aged (older). The default threshold is longer than any resolution seen
  in the export, so in practice "aged" means never resolved. Move the slider: the grey area changes, the blue stays
  flat.
- **Little's law** says that, on average, open work = arrival rate x time each item stays open. Arrivals per day x
  average days a ticket stays active gives ~{k['active_backlog_littles_law']:.0f} tickets, close to the
  ~{k['active_backlog_mean']:.0f} we observe. If capacity were short, time in system and the active backlog would
  both rise.
- **Weekly flow.** When the created and resolved lines track each other, throughput is keeping up. The steady gap
  is tickets that are never resolved, not arrival spikes.
- **Load test.** Tickets are split into five equal groups by how busy the desk was when they arrived. Flat lines
  mean busier moments do not produce more breaches; a trend-test p-value above 0.05 means no evidence of a slope.
- **Mix vs rate (shift-share).** The SLA change is split in two. *Mix* is the part caused by a different share of
  tickets in each segment (say, more chat). *Rate* is the part caused by attainment changing within each segment.
  A mix effect near zero means a change in the ticket mix did not cause the SLA change.
- **Simulated queue.** In the synthetic year the work arrives in the same weekly pattern every week. A volume spike
  would push the queue up under every roster at once. A staffing gap pushes it up only under the roster that is
  short of people at that hour; under the assumed weekday-weighted roster, that is at weekends.
""")
