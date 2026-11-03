import components as ui
import pandas as pd
import streamlit as st

from support_ops import charts as C
from support_ops import interactive

# Staffing Model (SYNTHETIC 20x scale-up + ASSUMPTIONS). What-if: the hourly requirement (Erlang C + occupancy cap +
# shrinkage) and the cheapest demand-shaped roster are recomputed for the chosen assumptions and compared with one
# hypothesis for today's roster. Below: the static base-case simulation, sensitivity, growth and an Erlang C explainer.

ui.page_header("Staffing Model",
               "How many agents do we need in each hour of the week, and how does today's roster compare?",
               "SYNTHETIC", "ASSUMPTION")

k = ui.key_numbers()
scale = k["synth_scale_factor"]
cfg = ui.config()
stf = cfg["staffing"]
goal = cfg["sla"]["goal_attainment"]

TODAY = {"by_day": "Weekday-weighted (base)", "flat": "Flat 24/7", "business_hours": "Day-weighted"}


@st.cache_data(show_spinner=False, max_entries=512)
def whatif(sl_goal: float, live_target_min: int, max_occupancy: float, shrinkage: float, aht_factor: float,
           volume_factor: float, today: str) -> dict:
    """Requirement + re-optimised roster for these assumptions vs one hypothesis for today's roster (held fixed)."""
    cov = ui.load("staff_coverage")
    return interactive.staffing_whatif(ui.load("staff_demand"), ui.config()["staffing"],
                                       cov[f"scheduled_{today}"].to_numpy(), sl_goal=sl_goal,
                                       max_occupancy=max_occupancy, shrinkage=shrinkage, aht_factor=aht_factor,
                                       volume_factor=volume_factor, live_target_min=live_target_min)


ui.takeaway(
    f"In the {scale}x planning scenario a desk needs about <b>{k['staff_fte_current']} FTE</b> with whole people in "
    f"every hour ({k['staff_fte_continuous']:.1f} in pure workload maths). Today's roster, assumed weekday-weighted, "
    f"is short in {k['staff_hours_under_today_by_day']} of 168 hours, all at weekends; re-rostering the same people "
    f"lifts simulated response SLA from {ui.pct(k['staff_sl_today_by_day'])} to "
    f"<b>{ui.pct(k['staff_sl_proposed'])}</b> "
    f"(optimistic rule) or {ui.pct(k['staff_sl_sum_today_by_day'])} to {ui.pct(k['staff_sl_sum_proposed'])} "
    "(conservative). That holds only if today's roster really is weekday-weighted and weekend follow-ups are done when "
    f"they arise; if they wait until Monday, the gain is {k['deferred_gain_pp_vs_by_day_sum']:+.1f} to "
    f"{k['deferred_gain_pp_vs_by_day']:+.1f} points.")
st.caption("This model says how many people a desk like this needs per hour and how to spread them. It cannot say "
           "whether today's real team is short: the roster and headcount are not in the data. The real-data tests on "
           "the Backlog Diagnosis page are the evidence on that, and they show no capacity signal.")

# ---------------------------------------------------------------------------------------------------------
st.subheader("What-if: hourly requirement and roster under your assumptions")
r1 = st.columns(4)
with r1[0]:
    sl_goal = st.slider("Live SLA goal (% within target)", 80, 95, round(100 * stf["sl_goal"]), 5,
                        format="%d%%", key="p6_sl_goal",
                        help="Share of chat/phone contacts that must be answered within the live target (Erlang C).")
with r1[1]:
    live_target = st.slider("Live answer target (minutes)", 1, 5, int(stf["live_target_min"]), 1, format="%d min",
                            key="p6_live_target",
                            help=f"Response target for chat and phone: {k['response_target_min_chat_phone']} minutes "
                                 "in the data.")
with r1[2]:
    max_occ = st.slider("Max occupancy (% of available time)", 75, 95, round(100 * stf["max_occupancy"]), 5,
                        format="%d%%", key="p6_max_occupancy",
                        help="Cap on the share of available time agents spend handling work.")
with r1[3]:
    shrinkage = st.slider("Shrinkage (% of paid time)", 15, 45, round(100 * stf["shrinkage"]), 5,
                          format="%d%%", key="p6_shrinkage",
                          help="Breaks, meetings, training and absence: scheduled time that is not available.")
r2 = st.columns(4)
with r2[0]:
    ht = stf["handle_time_min"]
    aht = st.slider("Handle-time multiplier (x base)", 0.6, 1.5, 1.0, 0.1, format="%.1fx", key="p6_aht_factor",
                    help=f"Handle time per touch is not in the data: {ht['chat_first']}/{ht['phone_first']}/"
                         f"{ht['email_first']} min for a first chat/phone/email touch, {ht['follow_up']} min per "
                         "follow-up, scaled by this factor.")
with r2[1]:
    volume = st.slider("Volume multiplier (x 2023)", 0.8, 1.5, 1.0, 0.05, format="%.2fx",
                       key="p6_volume_factor", help="Scales the synthetic 2023 arrivals in every hour of the week.")
with r2[2]:
    today = st.selectbox("Today's roster (hypothesis)", list(TODAY), format_func=TODAY.get, key="p6_today_roster",
                         help="The real roster is not in the data; three plausible versions, all with the same "
                              "headcount.")

res = whatif(sl_goal / 100, live_target, max_occ / 100, shrinkage / 100, round(aht, 2), round(volume, 2), today)
base = whatif(stf["sl_goal"], int(stf["live_target_min"]), stf["max_occupancy"], stf["shrinkage"], 1.0, 1.0, today)


def delta(now: float, ref: float, unit: str, fmt: str = "+.0f") -> str | None:
    return None if round(now - ref, 6) == 0 else f"{now - ref:{fmt}} {unit} vs base case"


m = st.columns(4)
m[0].metric("FTE needed, proposed roster", f"{res['fte_needed']}",
            delta=delta(res["fte_needed"], base["fte_needed"], "FTE"), delta_color="inverse",
            help=f"Fewest 8-hour shifts that cover every hour: {res['weekly_shifts']} a week; divided by "
                 f"{stf['shifts_per_fte_week']} shifts per FTE and rounded up. Base case {k['staff_fte_current']} FTE.")
m[1].metric("Agents per hour, peak / low", f"{res['peak_required']} / {res['min_required']}",
            help="People on shift: highest and lowest hourly requirement across the 168 hours of the week.")
m[2].metric("Hours short, today (of 168 h)", f"{res['hours_today_short']}",
            delta=delta(res["hours_today_short"], base["hours_today_short"], "h"), delta_color="inverse",
            help="Hours of the week where the chosen hypothesis for today's roster has fewer people than required.")
m[3].metric("Agent-hours short per week (h)", f"{res['agent_hours_short_today']:.0f}",
            delta=delta(res["agent_hours_short_today"], base["agent_hours_short_today"], "h"), delta_color="inverse",
            help="Sum over the week of (required - scheduled) in the hours that are short.")

req = res["requirement"].rename(columns={"scheduled_today": f"scheduled_{today}"})
ui.show(C.fig_requirement_vs_roster(req, rosters=(today, "proposed")), key="p6_requirement_vs_roster")
ui.show(C.fig_gap_heatmap(req, today), key="p6_gap_heatmap")
today_hours = float(ui.load("staff_coverage")[f"scheduled_{today}"].sum())
today_fte = today_hours / (stf["shift_length_h"] * stf["shifts_per_fte_week"])
st.caption(f"SYNTHETIC + ASSUMPTION. The hypothesis for today's roster stays at the base-case scenario's "
           f"{today_fte:.0f} FTE ({today_hours / stf['shift_length_h']:.0f} eight-hour shifts a week) when you move "
           "the sliders; the proposed roster is re-optimised each time (fewest shifts that cover every hour, starts at "
           f"{', '.join(f'{s:02d}' for s in stf['shift_starts'])}h).")

# ---------------------------------------------------------------------------------------------------------
st.subheader("Base case: same headcount, different rosters")
ui.badges("SYNTHETIC")
ui.show(C.fig_roster_sl(ui.load("staff_sim_summary"), goal), key="p6_roster_sl")
st.caption(f"SYNTHETIC. One synthetic year replayed ticket by ticket under each roster, same {k['staff_fte_current']} "
           f"FTE except 'Hire' (+{k['staff_hire_extra_shifts_by_day']} weekend shifts = "
           f"{k['staff_hire_extra_fte_equiv_by_day']:.1f} FTE). Stress test: if weekend follow-ups wait until Monday, "
           f"the re-roster gain is {k['deferred_gain_pp_vs_by_day_sum']:+.1f} to "
           f"{k['deferred_gain_pp_vs_by_day']:+.1f} points, so check the real roster and how weekend follow-ups are "
           "handled before moving shifts.")
c1, c2 = st.columns(2)
shift_col = {"shift": st.column_config.TextColumn("Shift")}
with c1:
    st.markdown("**Proposed roster: people starting each shift**")
    st.dataframe(ui.load("staff_roster_table_proposed"), hide_index=True, width="stretch", column_config=shift_col)
with c2:
    st.markdown("**Today's roster, as assumed (weekday-weighted)**")
    st.dataframe(ui.load("staff_roster_table_by_day"), hide_index=True, width="stretch", column_config=shift_col)
st.caption(f"Both rosters use {k['staff_weekly_shifts']} eight-hour shifts a week: the same headcount, spread "
           "differently (the what-if above shows the cheapest roster instead). The export has no intraday peak, so the "
           "proposed roster is close to flat across the day; what changes is the weekday/weekend balance.")

st.markdown(f"**Robustness: {k['rep_n']} independent synthetic years**")
r = ui.load("staff_replications")
opt = r.pivot(index="replication", columns="roster", values="response_sl")
cons = r.pivot(index="replication", columns="roster", values="response_sl_sum")
reps = (100 * pd.DataFrame({"today_opt": opt["by_day"], "proposed_opt": opt["proposed"],
                            "gain_opt": opt["proposed"] - opt["by_day"], "today_cons": cons["by_day"],
                            "proposed_cons": cons["proposed"], "gain_cons": cons["proposed"] - cons["by_day"]})
        ).reset_index()
pct_col = {"format": "%.1f%%"}
st.dataframe(reps, hide_index=True, width="stretch", column_config={
    "replication": st.column_config.NumberColumn("Year", format="%d", help="Independent synthetic year"),
    "today_opt": st.column_config.NumberColumn("Today, opt. (%)", help="Today's assumed roster, optimistic rule",
                                               **pct_col),
    "proposed_opt": st.column_config.NumberColumn("Proposed, opt. (%)", help="Proposed roster, optimistic rule",
                                                  **pct_col),
    "gain_opt": st.column_config.NumberColumn("Gain, opt. (pts)", format="%+.1f"),
    "today_cons": st.column_config.NumberColumn("Today, cons. (%)", help="Today's assumed roster, conservative rule",
                                                **pct_col),
    "proposed_cons": st.column_config.NumberColumn("Proposed, cons. (%)", help="Proposed roster, conservative rule",
                                                   **pct_col),
    "gain_cons": st.column_config.NumberColumn("Gain, cons. (pts)", format="%+.1f")})
stable = k["rep_ranking_stable"] and k["rep_ranking_stable_sum"]
st.caption(f"SYNTHETIC. Simulated response SLA; opt. = optimistic rule, cons. = conservative rule. Re-rostering "
           f"gains +{k['rep_gain_pp_vs_by_day_min']:.1f} to +{k['rep_gain_pp_vs_by_day_max']:.1f} points "
           f"(optimistic) and +{k['rep_gain_pp_vs_by_day_sum_min']:.1f} to "
           f"+{k['rep_gain_pp_vs_by_day_sum_max']:.1f} (conservative); the ranking of rosters is "
           f"{'the same in every year' if stable else 'not the same in every year'}. Hiring instead adds "
           f"+{k['rep_hire_minus_reroster_pp_min']:.1f} to +{k['rep_hire_minus_reroster_pp_max']:.1f} points more "
           f"(optimistic) or +{k['rep_hire_minus_reroster_pp_sum_min']:.1f} to "
           f"+{k['rep_hire_minus_reroster_pp_sum_max']:.1f} (conservative).")

# ---------------------------------------------------------------------------------------------------------
st.subheader("Which assumptions move the headcount most")
ui.show(C.fig_sensitivity(ui.load("staff_sensitivity")), key="p6_sensitivity")
st.caption(f"SYNTHETIC. FTE needed ranges from {k['sens_fte_aht_low']} (handle time -30%) to {k['sens_fte_aht_high']} "
           f"(+30%). A live SLA goal of 80-95% changes nothing, because total workload sets the number in "
           f"{k['staff_hours_binding_workload']} of 168 hours.")

st.subheader("Growth headroom")
ui.show(C.fig_growth(ui.load("staff_growth"), stf["sl_goal"], stf["max_occupancy"]), key="p6_growth")
st.caption(f"SYNTHETIC. The workload-matched roster meets the staffing goal (at least {stf['sl_goal']:.0%} of contacts "
           f"reach an agent within target, utilisation at most {stf['max_occupancy']:.0%}) up to "
           f"+{k['growth_holds_until_no_deflection']:.0%} volume; with base-case deflection it still meets it at "
           f"+{k['growth_max_tested']:.0%}, the end of the tested range.")

# ---------------------------------------------------------------------------------------------------------
with st.expander("How Erlang C works — try it"):
    st.markdown("Erlang C answers: *with this many contacts per hour, this handle time and N agents on duty, what "
                "share of contacts is answered within the target?* The bars add one agent at a time. Blue bars meet "
                "the live SLA goal set above.")
    e = st.columns(3)
    with e[0]:
        lam = st.slider("Contacts per hour", 1.0, 12.0, 3.0, 0.5, format="%.1f", key="p6_erlang_contacts")
    with e[1]:
        aht_min = st.slider("Handle time (minutes)", 4.0, 20.0, 11.5, 0.5, format="%.1f", key="p6_erlang_aht")
    with e[2]:
        target = st.slider("Answer target (minutes)", 1, 5, int(stf["live_target_min"]), 1, key="p6_erlang_target")
    ui.show(C.fig_erlang_curve(lam, aht_min, target, sl_goal / 100), key="p6_erlang_curve")

ui.how_to_read(f"""
- **Requirement chart.** The black line is the number of people needed on shift each hour; the coloured lines are
  the rosters compared. Where a roster dips below the black line, that hour is short (heatmap: red = short).
- **Erlang C** is the standard call-centre formula: from contacts per hour, handle time and agents on duty it gives
  the share of contacts answered within the target. We add agents until the live goal is met (try the expander).
- **Occupancy** is the share of available time spent handling work; the cap leaves slack for uneven arrivals.
  **"Workload binds"** means this cap, not the {k['response_target_min_chat_phone']}-minute live target, sets the
  number: true in
  {k['staff_hours_binding_workload']} of 168 hours, so the SLA-goal slider barely moves the answer.
- **Shrinkage** is paid time when agents are unavailable (breaks, meetings, training, absence). At
  {stf['shrinkage']:.0%}, ten people on shift give {10 * (1 - stf['shrinkage']):.0f} productive agents.
- **Demand-shaped (proposed) roster.** An integer programme picks how many people start a {stf['shift_length_h']}-hour
  shift at each allowed start time on each day, using as few shifts as possible while covering every hour.
  FTE = weekly shifts / {stf['shifts_per_fte_week']}.
- **Three versions of today's roster.** The real roster is not in the data, so we test three plausible ones with the
  same headcount. The re-roster gain depends on which is true; WFM can confirm.
- **Process ceiling** ({ui.pct(k['staff_process_ceiling'])}): the response SLA with zero queueing, given how slowly
  tickets are actually picked up. No roster can beat it; only faster pickup can.
- **What the simulation adds.** Erlang C looks at each hour on average. The simulation replays every synthetic
  ticket with variable handle times, follow-ups and queues that carry over between hours, then adds the real pickup
  delay: the later of the two (optimistic rule) or their sum (conservative).
""")
