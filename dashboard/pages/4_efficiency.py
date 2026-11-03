import components as ui
import streamlit as st

from support_ops import charts as C

# Efficiency & SLA [REAL]: which SLA fell and by how much, what changed inside resolution, attainment by
# segment, breach hotspots (with a false-discovery check), agents, and how late response breaches are.

ui.page_header("Efficiency & SLA",
               "Which SLA is falling, by how much, and is the problem concentrated anywhere?", "REAL")

k = ui.key_numbers()
P = ui.pct
goal = k["sla_goal"]
fct = ui.load("fct_tickets")
hot = ui.load("kpi_hotspots")
het = ui.load("rca_heterogeneity")          # chi-square by attribute (agent, priority, topic, channel, ...)
slots = ui.load("rca_time_slots")           # chi-square by time slot (hour, day, 6-hour band, weekend)
SLAS = {"response": "Response", "resolution": "Resolution"}


def p_text(p: float) -> str:
    return "p < 0.001" if p < 0.001 else (f"p = {p:.3f}" if p < 0.01 else f"p = {p:.2f}")


ui.takeaway(
    f"Resolution SLA fell from {P(k['resolution_sla_q1'])} in Q1 to {P(k['resolution_sla_q4'])} in Q4 (95% CI "
    f"{P(k['resolution_sla_q4_lo'], 0)} to {P(k['resolution_sla_q4_hi'], 0)}); response SLA did not fall "
    f"({P(k['response_sla_h1'])} in H1, {P(k['response_sla_h2'])} in H2). The decline is spread across every channel, "
    f"priority, topic, tier and agent: none of the {k['hotspots_tested_per_sla']:,} segment combinations tested for "
    "resolution stands out after a false-discovery check.")

c1, c2, c3, c4 = st.columns(4)
c1.metric("Resolution SLA, Q4 (%)", P(k["resolution_sla_q4"]),
          ui.pp(100 * (k["resolution_sla_q4"] - k["resolution_sla_q1"])), delta_color="normal",
          delta_description=f"vs {P(k['resolution_sla_q1'])} in Q1",
          help=f"Share of tickets solved within target (chat {k['resolution_target_h_chat']} h, email/phone "
               f"{k['resolution_target_h_email_phone']} h). Q1 {P(k['resolution_sla_q1'])} → Q4 "
               f"{P(k['resolution_sla_q4'])}; January {P(k['resolution_sla_jan'])}, December "
               f"{P(k['resolution_sla_dec'])}.")
c2.metric("Response SLA, H2 (%)", P(k["response_sla_h2"]),
          ui.pp(round(100 * k["response_sla_h2"], 1) - round(100 * k["response_sla_h1"], 1)), delta_color="normal",
          delta_description=f"vs {P(k['response_sla_h1'])} in H1",
          help=f"Share of tickets with a first reply within target (email {k['response_target_min_email']} min, "
               f"chat/phone {k['response_target_min_chat_phone']} min). H1 {P(k['response_sla_h1'])} → H2 "
               f"{P(k['response_sla_h2'])}; 2023 overall {P(k['response_sla_2023'])}.")
c3.metric("Resolved late, H2 (% of tickets)", P(k["rca_late_share_h2"]),
          ui.pp(round(100 * k["rca_late_share_h2"], 1) - round(100 * k["rca_late_share_h1"], 1)), delta_color="inverse",
          delta_description=f"vs {P(k['rca_late_share_h1'])} in H1",
          help="Tickets that were resolved, but after the target, as a share of ALL tickets created: "
               f"{P(k['rca_late_share_h1'])} in H1 → {P(k['rca_late_share_h2'])} in H2. Never-resolved tickets fell "
               f"over the same period ({P(k['rca_never_share_h1'])} → {P(k['rca_never_share_h2'])}).")
c4.metric("90th percentile, Dec (h)", f"{k['resolution_p90_h_dec']:.0f}",
          f"+{k['resolution_p90_h_dec'] - k['resolution_p90_h_jan']:.0f} h", delta_color="inverse",
          delta_description=f"vs {k['resolution_p90_h_jan']:.0f} h in Jan",
          help="Resolution time of the slowest 10% of resolved tickets (90th percentile), January "
               f"{k['resolution_p90_h_jan']:.0f} h → December {k['resolution_p90_h_dec']:.0f} h. The median barely "
               f"moved: {k['resolution_median_h_h1']:.1f} h in H1, {k['resolution_median_h_h2']:.1f} h in H2.")

# ---------------------------------------------------------------------------------------------
st.subheader("Which SLA fell?")
ui.show(C.fig_sla_trend(ui.load("kpi_monthly"), goal), key="p4_sla_trend")

st.subheader("What changed inside resolution?")
ui.show(C.fig_resolution_composition(ui.load("rca_resolution_composition")), key="p4_resolution_composition")
st.caption(f"Resolved late: {P(k['rca_late_share_h1'])} of tickets in H1, {P(k['rca_late_share_h2'])} in H2. Never "
           f"resolved fell slightly ({P(k['rca_never_share_h1'])} → {P(k['rca_never_share_h2'])}), so part of the late "
           "rise may be tickets that would previously have gone stale and now close late.")
ui.show(C.fig_resolution_time_hist(fct), key="p4_resolution_hist")
st.caption(f"Median resolution time {k['resolution_median_h_h1']:.1f} h (H1) → {k['resolution_median_h_h2']:.1f} h "
           f"(H2); 90th percentile {k['resolution_p90_h_jan']:.0f} h (Jan) → {k['resolution_p90_h_dec']:.0f} h (Dec). "
           "A capacity shortfall would slow everything; here only a subset of tickets got slower.")

# ---------------------------------------------------------------------------------------------
st.subheader("Attainment by segment")
DIMS = {"channel": "Channel", "priority": "Priority", "topic": "Topic", "product_group": "Product group",
        "agent_group": "Agent group (tier)", "day_of_week": "Day of week", "hour_band": "Time of day (6-hour band)",
        "day_type": "Weekday vs weekend", "quarter": "Quarter"}
SLOT_NAMES = {"day_of_week": "day of week", "hour_band": "6-hour band", "day_type": "weekday vs weekend"}
b1, b2, _ = st.columns([1, 1, 1], vertical_alignment="bottom")
dim = b1.selectbox("Break down by", list(DIMS), format_func=DIMS.get, key="p4_dimension")
sla = b2.radio("SLA", list(SLAS), index=1, format_func=SLAS.get, horizontal=True, key="p4_breakdown_sla")
ui.show(C.fig_breakdown(ui.load("kpi_by_dimension"), dim, sla, goal), key="p4_breakdown")
if dim == "quarter":
    st.caption("Quarter is the trend itself; see the monthly chart at the top of the page.")
else:
    if dim in SLOT_NAMES:
        p = float(slots.loc[(slots["slot"] == SLOT_NAMES[dim]) & (slots["sla"] == sla), "p_value"].iloc[0])
    else:
        p = float(het.loc[(het["dimension"] == dim) & (het["sla"] == sla), "p_value"].iloc[0])
    verdict = ("larger than chance" if p < 0.01 else
               "borderline; with this many tests it is weak evidence" if p < 0.05 else "consistent with chance")
    note = (f" Expected: the target is {k['response_target_min_email']} minutes for email but "
            f"{k['response_target_min_chat_phone']} for chat and phone."
            if (dim, sla) == ("channel", "response") else "")
    st.caption(f"Chi-square test of whether {sla} SLA differs across these segments more than chance: {p_text(p)} "
               f"({verdict}).{note}")

# ---------------------------------------------------------------------------------------------
st.subheader("Breach hotspots")
h1, h2, h3 = st.columns([0.8, 1, 1.5], vertical_alignment="bottom")
hot_sla = h1.radio("SLA", list(SLAS), index=1, format_func=SLAS.get, horizontal=True, key="p4_hot_sla")
min_n = h2.slider("Minimum tickets per combination", 30, 200, 30, step=10, key="p4_hot_min_n")
only_sig = h3.checkbox("Only show combinations that survive the false-discovery check", key="p4_hot_only_sig")
n_all = int((hot["sla_type"] == hot_sla).sum())
sel = hot[(hot["sla_type"] == hot_sla) & (hot["n"] >= min_n)]
if only_sig:
    sel = sel[sel["significant_fdr5"]]
if sel.empty:
    st.info(f"No {hot_sla} combination with at least {min_n} tickets survives the false-discovery check: breaches "
            "are spread evenly.")
else:
    ui.show(C.fig_hotspots(sel, hot_sla, top=12), key="p4_hotspots")
    top = sel.sort_values("excess_breaches", ascending=False).head(12)
    tbl = top[["combination", "n", "breach_rate", "breach_rate_lo", "breach_rate_hi", "excess_breaches", "q_value",
               "significant_fdr5"]].copy()
    tbl[["breach_rate", "breach_rate_lo", "breach_rate_hi"]] *= 100
    st.dataframe(tbl, hide_index=True, height=38 + 35 * len(tbl), column_config={      # all rows, no inner scroll
        "combination": st.column_config.TextColumn("Combination", width=320),
        "n": st.column_config.NumberColumn("Tickets", format="%d", width=65),
        "breach_rate": st.column_config.NumberColumn("Breach rate", format="%.1f%%", width=85),
        "breach_rate_lo": st.column_config.NumberColumn("95% CI low", format="%.1f%%", width=85),
        "breach_rate_hi": st.column_config.NumberColumn("95% CI high", format="%.1f%%", width=85),
        "excess_breaches": st.column_config.NumberColumn(
            "Excess breaches", format="%.1f", width=105,
            help="Breaches above what the overall breach rate predicts for this many tickets"),
        "q_value": st.column_config.NumberColumn("FDR q-value", format="%.3f", width=90,
                                                 help="p-value adjusted for the number of combinations tested"),
        "significant_fdr5": st.column_config.CheckboxColumn("Survives check", width=115,
                                                            help="q-value below 0.05"),
    })
st.caption(f"{len(sel):,} of {n_all:,} {hot_sla} combinations pass the filters; the chart and table show the top "
           f"{min(12, len(sel))} by excess breaches. q-values were computed once over all {n_all:,} combinations; "
           "filtering here changes what is displayed, not the q-values."
           + (" Switch to Response to see the one finding: Phone and its sub-segments." if hot_sla == "resolution"
              else ""))

# ---------------------------------------------------------------------------------------------
st.subheader("Agents")
a1, _ = st.columns([1, 2])
agent_sla = a1.radio("SLA", list(SLAS), index=1, format_func=SLAS.get, horizontal=True, key="p4_agent_sla")
ui.show(C.fig_agent_scorecard(ui.load("kpi_agent_scorecard"), agent_sla), key="p4_agents")
p_agent = float(het.loc[(het["dimension"] == "agent_name") & (het["sla"] == agent_sla), "p_value"].iloc[0])
st.caption("Agent = the ticket's current owner, not everyone who worked on it: use this for coaching conversations, "
           f"not ratings. Chi-square test across agents: {p_text(p_agent)}, not significant"
           + (" once the number of tests is accounted for" if p_agent < 0.05 else "")
           + f". Resolution SLA declined from H1 to H2 for {k['agents_declined_h1_to_h2']} of {k['real_agents']} "
           "agents: the slowdown is team-wide.")

# ---------------------------------------------------------------------------------------------
st.subheader("Response breaches: slow pickup or missed tickets?")
ui.show(C.fig_breach_lateness(fct), key="p4_breach_lateness")
st.caption(f"Median minutes past target: chat {k['late_chat_breach_median_min_late']:.1f}, phone "
           f"{k['late_phone_breach_median_min_late']:.1f}, email {k['late_email_breach_median_min_late']:.0f}. Only "
           f"{P(k['email_breach_near_miss_share'], 0)} of email breaches are near-misses (60 minutes late or less): a "
           "late email has usually been missed for hours, not queued. The chart shows breaches that were eventually "
           f"answered; {k['email_breach_never_answered']} of the {k['email_breaches']} email breaches never got a first "
           "reply.")

ui.how_to_read(f"""
- **95% interval (Wilson).** Every rate here is measured on a limited number of tickets, so it carries sampling
  noise. The line or shaded band around a dot is the range the true rate plausibly lies in. The Wilson method keeps
  that range sensible for small groups and for rates near 0% or 100%. If two segments' intervals overlap a lot, the
  difference may be noise.
- **Why a false-discovery check.** The hotspot search tests {k['hotspots_tested_per_sla']:,} combinations per SLA
  (single attributes, pairs and triples of channel, priority, topic, tier, product, weekday and time of day). At the
  usual 5% threshold about {0.05 * k['hotspots_tested_per_sla']:.0f} would look "significant" by luck alone. The
  Benjamini-Hochberg correction turns each p-value into a q-value that allows for how many tests were run; only
  orange points (q < 0.05) count as findings. **Excess breaches** = actual breaches minus what the overall rate
  predicts for that many tickets, so big segments with a modest excess rank above tiny ones.
- **Why no "Monday + billing + high priority" hotspot.** The highest raw resolution breach rates come from small
  cells, and none survives the correction; reporting one would present noise as a finding. For response the only
  finding is Phone ({k['response_target_min_chat_phone']}-minute target) and its sub-segments.
- **Lateness chart.** Each dot is one response breach; the x-axis is minutes past the target on a log scale, where
  each step multiplies, so 2 minutes and 4 hours fit on one chart. Chat and phone breaches cluster at a couple of
  minutes (slow pickup); email breaches sit hours late (missed tickets). Neither looks like a queue.
""")
