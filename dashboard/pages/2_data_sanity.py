import components as ui
import pandas as pd
import streamlit as st

from support_ops import charts as C

# Data & Sanity Checks: what the export contains, the data-quality log, the inferred SLA policy,
# known limitations, and how the synthetic scale-up was built and validated.

ui.page_header("Data & Sanity Checks", "Can we trust these numbers, and how was the scaled-up data built?",
               "REAL", "SYNTHETIC")

k = ui.key_numbers()
P = ui.pct
scale = k["synth_scale_factor"]
dq = ui.load("dq_checks")
flags_fixed = k["dq_response_flag_mismatches"] + k["dq_resolution_flag_mismatches"]

ui.takeaway(
    f"Yes, within known limits: the {k['real_tickets']:,}-ticket export reconciles row for row, and the "
    f"{k['dq_checks_flagged']} of {k['dq_checks_total']} checks that flagged a problem were all handled, including "
    f"{flags_fixed} raw SLA flags that contradict the timestamps, which is why every SLA here is recomputed from "
    f"timestamps. Only the staffing and cost numbers use the {scale}x synthetic scale-up, which matches the real "
    f"ticket mix within {k['synth_max_mix_gap_pp']:.1f} points.")

first, last = pd.Timestamp(k["real_first_created"]), pd.Timestamp(k["real_last_created"])
c1, c2, c3, c4 = st.columns(4)
c1.metric("Export size (tickets)", f"{k['real_tickets']:,}",
          help=f"One row per ticket, {k['real_agents']} named agents. Rows reconcile with the line count of the CSV "
               "file and ticket IDs are unique.")
c2.metric(f"Date range, {last:%Y} (days)", f"{k['real_days_in_window']}",
          f"{first.day} {first:%b} to {last.day} {last:%b}", delta_color="off", delta_arrow="off",
          help=f"Tickets created {k['real_first_created']} to {k['real_last_created']}. Snapshot (latest timestamp in "
               f"the file): {k['real_snapshot']}; it decides whether an open ticket is already overdue.")
c3.metric("Checks run / flagged", f"{k['dq_checks_total']} / {k['dq_checks_flagged']}",
          help="FLAG = a rule was broken; the fix is in 'Action taken'. INFO = context with no pass/fail rule.")
c4.metric("SLA flags fixed (tickets)", f"{flags_fixed}",
          help=f"{k['dq_response_flag_mismatches']} response and {k['dq_resolution_flag_mismatches']} resolution "
               "flags shipped in the export contradict its own timestamps. Every SLA metric in this app is "
               "recomputed from timestamps.")

# ---------------------------------------------------------------------------------------------
# Data-quality log
# ---------------------------------------------------------------------------------------------
st.subheader("Sanity checks on the export")
statuses = ["PASS", "FLAG", "INFO"]
f1, _ = st.columns([1, 2])
picked = f1.multiselect("Show checks with status", statuses, default=statuses, key="p2_status")
view = dq[dq["status"].isin(picked)][["area", "check_name", "observed", "expected", "status", "action_taken"]]
if view.empty:
    st.info("Select at least one status to list the checks.")
else:
    order = {"FLAG": 0, "INFO": 1, "PASS": 2}
    view = view.sort_values("status", key=lambda s: s.map(order), kind="stable")     # flagged checks first
    st.dataframe(view, hide_index=True, row_height=66, height=min(38 + 66 * len(view), 900), placeholder="–",
                 column_config={
        "area": st.column_config.TextColumn("Area", width=105),
        "check_name": st.column_config.TextColumn("Check", width=300),
        "observed": st.column_config.NumberColumn("Observed", format="localized", width=75),
        "expected": st.column_config.NumberColumn("Expected", format="localized", width=75),
        "status": st.column_config.TextColumn("Status", width=60),
        "action_taken": st.column_config.TextColumn("Action taken", width=420),
    })
st.caption(f"Showing {len(view)} of {len(dq)} checks. PASS = the rule holds; FLAG = the rule is broken and the fix "
           "is in 'Action taken'; INFO = context, no pass/fail rule; – = no expected value. Click a cell to read long "
           "text. Source: sql/90_data_quality_checks.sql.")

# ---------------------------------------------------------------------------------------------
# SLA policy inferred from the export's own deadlines
# ---------------------------------------------------------------------------------------------
st.subheader("SLA policy, inferred from the export's deadlines")
policy = pd.DataFrame({
    "Channel": ["Email", "Chat", "Phone"],
    "first_response": [k["response_target_min_email"], k["response_target_min_chat_phone"],
                       k["response_target_min_chat_phone"]],
    "resolution": [k["resolution_target_h_email_phone"], k["resolution_target_h_chat"],
                   k["resolution_target_h_email_phone"]],
})
t1, t2 = st.columns([1, 1], vertical_alignment="center")
t1.dataframe(policy, hide_index=True, width="stretch", column_config={
    "Channel": st.column_config.TextColumn("Channel"),
    "first_response": st.column_config.NumberColumn("First reply within", format="%d min"),
    "resolution": st.column_config.NumberColumn("Solved within", format="%d h"),
})
t2.markdown("Every ticket carries its own response and resolution deadlines; they vary only by channel. "
            f"**Priority does not change any target**: a high-priority email has the same "
            f"{k['response_target_min_email']}-minute and {k['resolution_target_h_email_phone']}-hour clock as a "
            "low-priority one.")

max_res_days = float(dq.loc[dq["check_name"].str.startswith("Max resolution time"), "observed"].iloc[0])
with st.expander("Known limitations of the export"):
    st.markdown(f"""
- **Provenance.** A public Kaggle dataset described as a data-challenge scenario; how it was produced is not
  documented. We treat it as the real export but do not lean on relationships between fields.
- **Flat 24-hour arrivals.** Tickets arrive at almost the same rate at night as in the afternoon, which is unusual
  for a European B2B desk. It is why the staffing model has no intraday peak.
- **CSAT unrelated to breaches.** Tickets that breached resolution SLA average {k['csat_breached']:.2f} on the
  1-5 scale vs {k['csat_met']:.2f} for tickets that met it, so CSAT is not used as an outcome.
- **"Agent interactions" is ambiguous.** Documented as the number of agent interactions per ticket, but its
  distribution differs by channel and {k['dq_interactions_sentinel_rows']} chat tickets carry a placeholder value of
  60. The Staffing Model page tests other readings.
- **Agent = current owner.** The agent field is the ticket's current owner, not everyone who worked on it, so
  agent comparisons are for coaching conversations, not performance ratings.
- **Other unusual patterns:** resolution times stop at about {max_res_days:.1f} days, on-time response times are
  spread evenly inside the target window, and resolution clocks ignore weekends.
""")

# ---------------------------------------------------------------------------------------------
# Synthetic scale-up
# ---------------------------------------------------------------------------------------------
st.subheader("The synthetic scale-up")
ui.badges("SYNTHETIC")
st.markdown(f"""
**Why.** The export averages about {k['real_tickets_per_day'] / 24:.1f} tickets an hour, so most hours of the week
see 0-1 tickets, no queue ever forms and no hour has a stable arrival rate. Erlang C and the queue simulation need
one, so we generated one synthetic year at **{scale}x the export's volume** ({k['synth_tickets']:,} tickets, about
{k['synth_tickets_per_day']:.0f} a day).

**How.**
- *Arrivals:* random (Poisson) arrivals at {scale}x the export's rate for each weekday, spread over the day with the
  export's hour-of-day profile (lightly smoothed), and none on the holidays where the export has none.
- *Ticket attributes:* each synthetic ticket copies a real ticket created in the same month: channel, priority,
  topic, product, tier, interactions, resolution outcome and time, CSAT, and the real first-response delay, which
  becomes its "pickup delay".
- *Work items:* each ticket becomes a first touch plus follow-up touches spread over its life
  ({k['synth_work_items']:,} items). Handle time per touch is an assumption (config.yaml).
- *Reproducible:* one fixed random seed, so every run gives the same data.

**Where it is used.** Only staffing, roster, growth and cost numbers: the planning-scenario row on Overview, the
queue simulation on Backlog Diagnosis, the Staffing Model, the agent-hours on Automation Opportunities and the
Headcount Business Case. Everything else is the real export.
""")

DIMS = {"Channel": ("channel",), "Topic": ("topic",), "Priority": ("priority",),
        "All three": ("channel", "topic", "priority")}
v1, _ = st.columns([1, 2])
dim_label = v1.selectbox("Compare the ticket mix by", list(DIMS), index=3, key="p2_synth_dims")
ui.show(C.fig_synth_validation(ui.load("kpi_by_dimension"), ui.load("kpi_by_dimension_synth"),
                               dims=DIMS[dim_label]), key="p2_synth_validation")

st.markdown("**Outcomes, real vs synthetic**")
outcomes = pd.DataFrame([
    ("Resolution SLA attainment", 100 * k["resolution_sla_2023"], 100 * k["synth_resolution_sla"],
     "Copied from real tickets of the same month, so the 2023 decline carries over."),
    ("Response SLA, pickup delay only (no queue)", 100 * k["response_sla_2023"], 100 * k["staff_process_ceiling"],
     "At real volume no queue forms, so real response times measure pickup. Synthetic: the process ceiling. "
     "The 0.6-point gap is sampling noise (about ±1.4 points on 2,328 tickets); other synthetic years give 87.1-87.3%."),
    ("Response SLA incl. simulated queue (today's assumed roster)", None, 100 * k["staff_sl_today_by_day"],
     "Adds the simulated wait for a free agent (optimistic rule), so it sits below the real figure."),
], columns=["metric", "real", "synthetic", "note"])
st.dataframe(outcomes, hide_index=True, placeholder="n/a", row_height=66,     # > 64 px lets long text wrap
             column_config={
                 "metric": st.column_config.TextColumn("Metric", width=290),
                 "real": st.column_config.NumberColumn("Real export", format="%.1f%%", width=90),
                 "synthetic": st.column_config.NumberColumn("Synthetic scale-up", format="%.1f%%", width=130),
                 "note": st.column_config.TextColumn("Note", width=450),
             })
st.caption(f"Tickets per day: {k['real_tickets_per_day']:.1f} real vs {k['synth_tickets_per_day']:.1f} synthetic "
           f"({scale}x by design). n/a = not applicable: the real export has no queue to simulate.")

ui.how_to_read(f"""
- **What a sanity check is.** Before trusting any number we test the export against rules it must obey: row counts
  reconcile with the file, ticket IDs are unique, timestamps are in a possible order, fields are filled as each status
  requires, values are in range. PASS means the rule holds; FLAG means it is broken and "Action taken" says what we
  did (fix, exclude or keep with a note); INFO is context with no pass/fail rule.
- **Why SLA is recomputed from timestamps.** The export ships its own "SLA met / violated" flags, but on
  {flags_fixed} tickets they contradict the export's own timestamps. A metric that a headcount decision rests on must
  be reproducible, so every SLA figure here compares the actual first-reply or resolution time with the ticket's
  deadline. The policy table is inferred the same way: from the deadlines, not from a policy document.
- **What "synthetic, calibrated" means.** The scaled-up tickets are not real, but they are built to behave like the
  export: same weekday and hour pattern, same mix, same resolution behaviour and pickup delays, at {scale}x the volume.
  The chart checks the mix (blue and orange bars should match). The table checks outcomes; synthetic response SLA is
  lower only because it adds a simulated wait for a free agent.
- **Which pages use it.** The planning-scenario row on Overview, the queue simulation on Backlog Diagnosis, Staffing
  Model, the agent-hours on Automation Opportunities and Headcount Business Case. Everything else is the real export.
""")
