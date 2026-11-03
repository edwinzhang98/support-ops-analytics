import components as ui
import pandas as pd
import streamlit as st

from support_ops import charts as C
from support_ops.report_text import recommendations

# Overview: the bottom line for the Support Director. Headline KPIs (real export vs planning scenario),
# the three findings, the recommendation, the two headline charts and a map of the other pages.
# Every number comes from reports/key_numbers.json.

ui.page_header("Overview",
               "What is happening to our SLA, why, and what should we do about headcount next quarter?",
               "REAL", "SYNTHETIC")

k = ui.key_numbers()
P = ui.pct
goal = k["sla_goal"]
scale = k["synth_scale_factor"]
aht_pct = k.get("sens_aht_factor_pct", 30)   # handle-time sensitivity behind sens_fte_aht_low/high


def tag(kind: str) -> str:
    """Short inline version of the header badge (same colours), to label a paragraph."""
    bg, fg, _ = ui.BADGES[kind]
    # margin override: the header badge's bottom margin would make the first text line taller than the rest
    return f"<span class='badge' style='background:{bg};color:{fg};margin:0 6px 0 0'>{kind}</span>"


ui.takeaway(
    f"The SLA that fell in 2023 is <b>resolution</b> ({P(k['resolution_sla_q1'])} of tickets solved on time in Q1, "
    f"{P(k['resolution_sla_q4'])} in Q4), not response, and the data shows a <b>process change, not a capacity "
    "shortfall</b>. Recommendation: <b>no headcount request this quarter</b>; instead sweep stale tickets, find the "
    "resolution slow path, pilot the pickup and self-service fixes, and re-roster toward weekend workload once "
    "today's real roster has been checked.")

# ---------------------------------------------------------------------------------------------
# KPI row 1: what happened in 2023 (real export)
# ---------------------------------------------------------------------------------------------
ui.badges("REAL")
c1, c2, c3, c4 = st.columns(4)
c1.metric("Resolution SLA, Q4 (%)", P(k["resolution_sla_q4"]),
          ui.pp(100 * (k["resolution_sla_q4"] - k["resolution_sla_q1"])), delta_color="normal",
          delta_description="vs Q1",
          help=f"Share of tickets solved within target (chat {k['resolution_target_h_chat']} h, email/phone "
               f"{k['resolution_target_h_email_phone']} h). Q1 {P(k['resolution_sla_q1'])}; Q4 95% CI "
               f"{P(k['resolution_sla_q4_lo'])} to {P(k['resolution_sla_q4_hi'])}.")
c2.metric("Response SLA, 2023 (%)", P(k["response_sla_2023"]),
          ui.pp(100 * (k["response_sla_h2"] - k["response_sla_h1"])), delta_color="normal",
          delta_description="H2 vs H1",
          help=f"Share of tickets with a first reply within target (email {k['response_target_min_email']} min, "
               f"chat/phone {k['response_target_min_chat_phone']} min). H1 {P(k['response_sla_h1'])}, H2 "
               f"{P(k['response_sla_h2'])}: response did not fall.")
c3.metric("Volume, H2 vs H1 (%)", f"{100 * k['volume_change_h2_vs_h1']:+.1f}%",
          help=f"{k['volume_h1']:,} tickets created in H1, {k['volume_h2']:,} in H2. Every month is within chance "
               f"variation of the {k['real_tickets_per_day']:.1f} tickets/day average.")
c4.metric("Never resolved (tickets)", f"{k['stale_never_resolved']:,}",
          help=f"{P(k['stale_share_of_tickets'])} of all 2023 tickets were still open at the snapshot (median age "
               f"{k['stale_median_age_days']:.0f} days). They are {P(k['stale_share_of_resolution_breaches'], 0)} "
               "of all resolution breaches.")

# ---------------------------------------------------------------------------------------------
# KPI row 2: planning scenario (synthetic 20x desk)
# ---------------------------------------------------------------------------------------------
ui.badges("SYNTHETIC")
c1, c2, c3, c4 = st.columns(4)
c1.metric("Workload-matched roster (FTE)", f"{k['staff_fte_current']}",
          help=f"FTE needed with a workload-matched roster. At {scale}x the export's volume the cheapest cover is "
               f"{k['staff_min_shifts']} eight-hour shifts a week with whole people in every hour, i.e. "
               f"{k['staff_fte_current']} FTE (a {k['staff_weekly_shifts']}-shift budget). Pure workload "
               f"maths without rounding gives {k['staff_fte_continuous']:.1f} FTE; handle time {aht_pct}% lower or "
               f"higher gives {k['sens_fte_aht_low']} to {k['sens_fte_aht_high']}. A planning scenario, not a count of "
               "today's team.")
c2.metric("Response SLA, proposed (%, optimistic rule)", P(k["staff_sl_proposed"]),
          ui.pp(round(100 * k["staff_sl_proposed"], 1) - round(100 * k["staff_sl_today_by_day"], 1)),
          delta_color="normal", delta_description=f"vs {P(k['staff_sl_today_by_day'])} today",
          help="Simulated response SLA, today's assumed weekday-weighted roster → proposed workload-matched roster, "
               f"same {k['staff_fte_current']} FTE: {P(k['staff_sl_today_by_day'])} → {P(k['staff_sl_proposed'])} "
               "under the optimistic rule (queue wait and pickup delay overlap), "
               f"{P(k['staff_sl_sum_today_by_day'])} → {P(k['staff_sl_sum_proposed'])} under the conservative rule "
               f"(they add up). Over {k['rep_n']} simulated years the gain is +{k['rep_gain_pp_vs_by_day_min']:.1f} "
               f"to +{k['rep_gain_pp_vs_by_day_max']:.1f} points (optimistic) or +{k['rep_gain_pp_vs_by_day_sum_min']:.1f} "
               f"to +{k['rep_gain_pp_vs_by_day_sum_max']:.1f} (conservative). Holds only if today's roster really is "
               "weekday-weighted and weekend follow-ups are done when they arise.")
c3.metric("Hire alternative (FTE)", f"+{k['staff_hire_extra_fte_equiv_by_day']:.1f}",
          f"€{k['bc_hire_first_year_eur'] / 1000:,.0f}k in year 1", delta_color="off", delta_arrow="off",
          help=f"Keep today's assumed roster and add {k['staff_hire_extra_shifts_by_day']} weekend shifts a week "
               f"({k['staff_hire_extra_fte_equiv_by_day']:.1f} FTE, {k['staff_hire_extra_fte_by_day']} whole "
               f"hires). It buys +{k['rep_hire_minus_reroster_pp_min']:.1f} to "
               f"+{k['rep_hire_minus_reroster_pp_max']:.1f} points (optimistic) or "
               f"+{k['rep_hire_minus_reroster_pp_sum_min']:.1f} to +{k['rep_hire_minus_reroster_pp_sum_max']:.1f} "
               f"(conservative) more than re-rostering. Cost assumes €{k['cost_fte_annual_eur']:,} per FTE per year.")
c4.metric("Process ceiling (%)", P(k["staff_process_ceiling"]),
          help="The best response SLA any roster can reach with today's real pickup behaviour, i.e. with no "
               "queueing at all. Only faster pickup (email alert, push routing) moves it.")
st.caption(f"Planning scenario: a desk at {scale}x the export's volume, same headcount in every roster except "
           "'Hire'. Today's real roster and headcount are not in the data; the baseline is an assumed "
           "weekday-weighted roster.")

# ---------------------------------------------------------------------------------------------
# The two headline charts
# ---------------------------------------------------------------------------------------------
st.subheader("The two charts behind the headline")
ui.show(C.fig_sla_trend(ui.load("kpi_monthly"), goal), key="p1_sla_trend")
ui.show(C.fig_roster_sl(ui.load("staff_sim_summary"), goal), key="p1_roster_sl")

# ---------------------------------------------------------------------------------------------
# Findings and recommendation (mirror the report's executive summary)
# ---------------------------------------------------------------------------------------------
st.subheader("Three findings")
change_pp = k["rca_mix_effect_q1_q4_channel_pp"] + k["rca_rate_effect_q1_q4_channel_pp"]
st.markdown(
    tag("REAL") + f"<b>Resolution SLA fell from {P(k['resolution_sla_q1'])} in Q1 to {P(k['resolution_sla_q4'])} in "
    f"Q4</b> (95% CI {P(k['resolution_sla_q4_lo'], 0)} to {P(k['resolution_sla_q4_hi'], 0)}); response SLA held at "
    f"{P(k['response_sla_2023'])} and improved in H2 ({P(k['response_sla_h1'])} → {P(k['response_sla_h2'])}). Volume "
    f"was flat (H2 {100 * k['volume_change_h2_vs_h1']:+.1f}% vs H1). Of the {change_pp:+.1f}-point change, shifts in "
    f"channel mix explain {k['rca_mix_effect_q1_q4_channel_pp']:+.1f}; the rest is slower handling within every "
    "channel.", unsafe_allow_html=True)

ramp_from = pd.Timestamp(k["rca_ramp_start"]).strftime("%B")
ramp_to = pd.Timestamp(k["rca_ramp_end"]).strftime("%B")
st.markdown(
    tag("REAL") + f"<b>What changed: a new slow path and a stale backlog.</b> Tickets resolved late rose from "
    f"{P(k['rca_late_share_h1'])} to {P(k['rca_late_share_h2'])} of all tickets, gradually from {ramp_from} to "
    f"{ramp_to}. The median resolution time barely moved ({k['resolution_median_h_h1']:.0f} → "
    f"{k['resolution_median_h_h2']:.0f} h) but the 90th percentile doubled ({k['resolution_p90_h_jan']:.0f} → "
    f"{k['resolution_p90_h_dec']:.0f} h), in every channel, priority, topic, tier and agent. Breach rates do not rise "
    "when the desk is busy and the active backlog stayed flat, so the data shows a process change, not a capacity "
    "shortfall (a capacity change outside the ticket data, such as time diverted to other work, cannot be "
    f"excluded). Separately, {k['stale_never_resolved']} tickets ({P(k['stale_share_of_tickets'])}) were never "
    f"resolved; they are {P(k['stale_share_of_resolution_breaches'], 0)} of all resolution breaches.",
    unsafe_allow_html=True)

st.markdown(
    tag("SYNTHETIC") + f"<b>Capacity and roster (planning scenario at {scale}x volume).</b> A desk this size needs "
    f"about {k['staff_fte_current']} FTE ({k['staff_fte_continuous']:.1f} in pure workload maths; "
    f"{k['sens_fte_aht_low']} to {k['sens_fte_aht_high']} if handle times are {aht_pct}% lower or higher). Spreading "
    "the same people by workload rather than by new-ticket counts moves cover from weekdays to weekends and lifts "
    f"simulated response SLA from {P(k['staff_sl_today_by_day'])} to {P(k['staff_sl_proposed'])} (optimistic rule; "
    f"{P(k['staff_sl_sum_today_by_day'])} → {P(k['staff_sl_sum_proposed'])} under the conservative rule), provided "
    "today's roster really is weekday-weighted and weekend follow-ups are done when they arise. Hiring "
    f"{k['staff_hire_extra_fte_equiv_by_day']:.1f} FTE of weekend shifts instead costs about "
    f"€{k['bc_hire_first_year_eur'] / 1000:,.0f}k in year one and buys +{k['rep_hire_minus_reroster_pp_min']:.1f} to "
    f"+{k['rep_hire_minus_reroster_pp_max']:.1f} points more (optimistic rule; +{k['rep_hire_minus_reroster_pp_sum_min']:.1f} "
    f"to +{k['rep_hire_minus_reroster_pp_sum_max']:.1f} conservative). No roster beats "
    f"the {P(k['staff_process_ceiling'])} ceiling set by slow and missed pickups.", unsafe_allow_html=True)

st.subheader("Recommendation")
recs = recommendations(k)          # the canonical list, shared with the HTML report
with st.container(border=True):
    st.markdown("\n".join(f"{title} <span class='muted'>· {owner}</span>" for title, owner, *_ in recs),
                unsafe_allow_html=True)
    with st.expander("Expected impact, how we measure it, and the main risk"):
        for title, owner, impact, measure, risk in recs:
            # "~" pairs would render as strikethrough in Markdown
            impact, measure, risk = (s.replace("~", "about ") for s in (impact, measure, risk))
            st.markdown(f"**{title}** ({owner})\n- Impact: {impact}\n- Measure: {measure}\n- Risk: {risk}")

# ---------------------------------------------------------------------------------------------
# Story map: which page answers which question
# ---------------------------------------------------------------------------------------------
st.subheader("Story map")
story = pd.DataFrame([
    ("1. Overview", "What is happening to our SLA, why, and what should we do about headcount next quarter?"),
    ("2. Data & Sanity Checks", "Can we trust these numbers, and how was the scaled-up data built?"),
    ("3. Volume Patterns", "Did ticket volume grow, and when does the work arrive?"),
    ("4. Efficiency & SLA", "Which SLA is falling, by how much, and is the problem concentrated anywhere?"),
    ("5. Backlog Diagnosis", "Is work piling up because of volume spikes, or because capacity can't keep up?"),
    ("6. Staffing Model", "How many agents do we need in each hour of the week, and how does today's roster "
     "compare?"),
    ("7. Automation Opportunities", "Which ticket types could self-service or routing take off agents' plates, and "
     "how much work would that save?"),
    ("8. Headcount Business Case", "Hire, re-roster or automate: what does each option cost and what service level "
     "does it buy?"),
], columns=["Page", "Question it answers"])
st.dataframe(story, hide_index=True, column_config={"Page": st.column_config.TextColumn(width=200)})
st.caption("Volume, SLA, backlog and root-cause findings rest on the real export. Staffing, roster, growth and cost "
           f"numbers use the {scale}x synthetic scale-up plus assumptions set in config.yaml. Each page's badges say "
           "which.")

ui.how_to_read(f"""
- **Response vs resolution SLA.** Response SLA is the share of tickets whose first reply came within target (email
  {k['response_target_min_email']} min, chat/phone {k['response_target_min_chat_phone']} min). Resolution SLA is the
  share solved within target (chat {k['resolution_target_h_chat']} h, email/phone
  {k['resolution_target_h_email_phone']} h). "Attainment" means the share of tickets meeting the target. They fail for
  different reasons: response is about picking work up, resolution about how long the whole job takes.
- **REAL vs SYNTHETIC.** Blue badges mark the 2023 export ({k['real_tickets']:,} tickets): volume, SLA trends and
  root cause. Orange badges mark a {scale}x synthetic scale-up calibrated to the export. It is used only for
  hour-by-hour staffing, roster comparison and costs, because at the export's volume no queue ever forms.
- **SLA trend chart.** One line per SLA, by month the ticket was created. The shaded band is the 95% confidence
  interval: where the true rate plausibly lies given that month's sample. The grey line is the
  {P(goal, 0)} goal.
- **Roster chart.** Each pair of bars is the same synthetic year replayed under one roster. The dark bar uses the
  optimistic rule (queue wait and slow pickup overlap, so response time is the later of the two); the light bar uses
  the conservative rule (they add up). The truth is likely in between.
- **Process ceiling.** The best response SLA possible with zero queueing, given the real pickup delays in the export.
  Rostering cannot beat it; only faster pickup can.
- **Why the roster numbers depend on an assumption.** Today's real roster is not in the data. The baseline is a
  hypothesis: daily headcount follows new-ticket counts (weekday-weighted). If today's roster is already flatter,
  the gain from re-rostering shrinks (+{k['staff_gain_pp_vs_flat']:.1f} points against a flat roster). Check the
  real roster before moving shifts.
""")
