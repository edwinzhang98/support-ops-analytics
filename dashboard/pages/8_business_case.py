import components as ui
import pandas as pd
import streamlit as st

from support_ops import charts as C
from support_ops import interactive
from support_ops.report_text import recommendations

# Headcount Business Case. SYNTHETIC: response SLA of each option from simulating the same synthetic year (20x).
# ASSUMPTION: every cost (adjustable below). The email-alert pilot uses REAL 2023 breaches x an ASSUMED catch rate
# and is deliberately kept out of the options.

ui.page_header("Headcount Business Case",
               "Hire, re-roster or automate: what does each option cost and what service level does it buy?",
               "SYNTHETIC", "ASSUMPTION")

k = ui.key_numbers()
scale = k["synth_scale_factor"]
cfg = ui.config()
cost = cfg["cost"]
goal = cfg["sla"]["goal_attainment"]
trigger = f"+{k['growth_holds_until_no_deflection']:.0%}"


@st.cache_data(show_spinner=False, max_entries=512)
def costed(fte_annual_eur: int, hire_one_off_eur: int, automation_one_off_eur: int,
           automation_annual_eur: int) -> pd.DataFrame:
    """Re-price the options (the SLA of each option comes from the simulation and does not change)."""
    return interactive.costed_options(ui.load("business_options"), fte_annual_eur, hire_one_off_eur,
                                      automation_one_off_eur, automation_annual_eur)


@st.cache_data(show_spinner=False, max_entries=64)
def alert_sl(now: float, email_breaches: int, evaluable: int, catch_rate: float) -> float:
    """Response SLA if the alert turned `catch_rate` of the real 2023 email breaches into on-time replies."""
    return interactive.email_alert_sl(now, email_breaches, evaluable, catch_rate)


ui.takeaway(
    "No headcount request this quarter: hiring would mainly buy response SLA, which is not the SLA that fell. In the "
    "planning scenario, re-rostering the same people lifts simulated response SLA from "
    f"{ui.pct(k['bc_status_quo_sl'])} "
    f"to <b>{ui.pct(k['bc_reroster_sl'])}</b> at no cost; hiring {k['staff_hire_extra_fte_equiv_by_day']:.1f} FTE of "
    f"weekend shifts reaches {ui.pct(k['bc_hire_sl'])} for ~€{k['bc_hire_first_year_eur'] / 1000:,.0f}k in year one, "
    f"only +{k['rep_hire_minus_reroster_pp_min']:.1f} to +{k['rep_hire_minus_reroster_pp_max']:.1f} points more "
    f"(optimistic rule) or +{k['rep_hire_minus_reroster_pp_sum_min']:.1f} to "
    f"+{k['rep_hire_minus_reroster_pp_sum_max']:.1f} (conservative).")

recs = recommendations(k)
with st.container(border=True):
    st.markdown("**Recommendation: no headcount request this quarter.** The 2023 data shows a process change, not a "
                "capacity shortfall. Instead:\n\n" + "\n".join(r[0] for r in recs) +
                f"\n\n**Trigger to revisit headcount:** weekly volume more than {trigger} above 2023 for a month, "
                f"fewer than {cfg['staffing']['sl_goal']:.0%} of contacts reaching an agent within target, or agent "
                f"utilisation "
                f"above {cfg['staffing']['max_occupancy']:.0%}.")
    with st.expander("Owner, expected impact, how we measure, risk"):
        for title, owner, impact, measure, risk in recs:
            st.markdown(f"**{title}**  \nOwner: {owner}  \nExpected impact: {impact}  \nHow we measure: {measure}  \n"
                        f"Risk: {risk}")

# ---------------------------------------------------------------------------------------------------------
st.subheader("Hire, re-roster or automate")
c = st.columns(4)
with c[0]:
    fte_k = st.slider("FTE cost (€k per year, fully loaded)", 40, 90, cost["fte_annual_eur"] // 1000, 5,
                      format="€%dk", key="p8_fte_annual")
with c[1]:
    hire_k = st.slider("Hiring one-off (€k per hire)", 0, 15, cost["hire_one_off_eur"] // 1000, 1, format="€%dk",
                       key="p8_hire_one_off", help="Recruiting and onboarding, per whole person hired.")
with c[2]:
    auto_k = st.slider("Automation build, one-off (€k)", 0, 100, cost["automation_one_off_eur"] // 1000, 5,
                       format="€%dk", key="p8_automation_one_off",
                       help="Self-service content, portal and routing configuration.")
with c[3]:
    auto_run_k = st.slider("Automation running (€k per year)", 0, 60, cost["automation_annual_eur"] // 1000, 5,
                           format="€%dk", key="p8_automation_annual", help="Tooling licences and content upkeep.")
opts = costed(fte_k * 1000, hire_k * 1000, auto_k * 1000, auto_run_k * 1000)
ui.show(C.fig_options(opts), key="p8_options")

status_quo = opts.loc[opts["option"] == "0. Status quo", "response_sl"].iloc[0]
gain = 100 * (opts["response_sl"] - status_quo)
year1 = opts["first_year_cost_eur"].round()
tbl = pd.DataFrame({
    "option": opts["option"], "what_changes": opts["what_changes"], "fte": opts["fte"],
    "one_off": opts["one_off_cost_eur"].round().astype("int64"),
    "recurring": opts["annual_cost_change_eur"].round().astype("int64"),
    "year1": year1.astype("int64"),
    "sl_opt": 100 * opts["response_sl"], "sl_cons": 100 * opts["response_sl_sum"],
    "per_point": [f"€{c_ / g:,.0f}" if g > 1e-9 else "n/a" for c_, g in zip(year1, gain)]})
st.dataframe(tbl, hide_index=True, width="stretch", column_config={
    "option": st.column_config.TextColumn("Option"),
    "what_changes": st.column_config.TextColumn("What changes", width=270),
    "fte": st.column_config.NumberColumn("FTE", format="%.1f"),
    "one_off": st.column_config.NumberColumn("One-off", format="€%,d", help="One-off cost (€)"),
    "recurring": st.column_config.NumberColumn("Per year", format="€%,d",
                                               help="Recurring cost change (€ per year)"),
    "year1": st.column_config.NumberColumn("Year 1", format="€%,d",
                                           help="One-off + first year's recurring cost (€)"),
    "sl_opt": st.column_config.NumberColumn("SLA opt.", format="%.1f%%",
                                            help="Simulated response SLA, optimistic rule (%)"),
    "sl_cons": st.column_config.NumberColumn("SLA cons.", format="%.1f%%",
                                             help="Simulated response SLA, conservative rule (%)"),
    "per_point": st.column_config.TextColumn(
        "€ per point", help="Year-1 cost / points of response SLA gained over the status quo (optimistic rule). "
                            "n/a = no gain.")})
st.caption(f"SYNTHETIC SLA x ASSUMED costs (€). SLA opt. / cons. = simulated response SLA under the optimistic / "
           f"conservative rule. Every option replays the same synthetic year ({scale}x volume); only the roster "
           f"or the ticket population changes. Hiring is costed in FTE-equivalents of the shifts needed "
           f"({k['staff_hire_extra_shifts_by_day']} weekend shifts = "
           f"{k['staff_hire_extra_fte_equiv_by_day']:.1f} FTE), "
           f"with the one-off cost per whole hire ({k['staff_hire_extra_fte_by_day']}). B + C's process ceiling "
           "differs slightly because deflection changes the ticket population.")

# ---------------------------------------------------------------------------------------------------------
st.subheader("Pilot the pickup fix, outside the options")
ui.badges("REAL", "ASSUMPTION")
c1, _ = st.columns([2, 3])
with c1:
    catch = st.slider("Share of late emails the alert catches (catch rate)", 0, 100, 50, 5, format="%d%%",
                      key="p8_catch_rate", help="Unknown until measured in a pilot. 50% is an illustration.")
sl = alert_sl(k["response_sla_2023"], k["email_breaches"], k["response_evaluable"], catch / 100)
m = st.columns(3)
m[0].metric("Response SLA today (%, real 2023 tickets)", ui.pct(k["response_sla_2023"]))
m[1].metric("Response SLA with the alert (%)", ui.pct(sl),
            delta=ui.pp(100 * (sl - k["response_sla_2023"])) if catch else None)
m[2].metric("Email breaches avoided (tickets, 2023)",
            f"{k['email_breaches'] * catch / 100:.0f} of {k['email_breaches']}")
ui.show(C.fig_email_alert(ui.load("rca_email_alert"), k["response_sla_2023"], goal), key="p8_email_alert")
st.caption(f"REAL breaches x ASSUMED catch rate. Email breaches are a median "
           f"{k['late_email_breach_median_min_late'] / 60:.1f} hours late and only "
           f"{ui.pct(k['email_breach_near_miss_share'], 0)} are near-misses (at most 60 minutes late), so the alert "
           "targets emails nobody picked up. The catch rate must be measured in a pilot; until then this is not added "
           "to the options above.")

# ---------------------------------------------------------------------------------------------------------
st.subheader("When to revisit headcount")
ui.badges("SYNTHETIC")
ui.show(C.fig_growth(ui.load("staff_growth"), cfg["staffing"]["sl_goal"], cfg["staffing"]["max_occupancy"]),
        key="p8_growth")
st.caption(f"SYNTHETIC. The re-rostered team meets the staffing goal up to {trigger} volume; with base-case "
           f"deflection it still meets it at +{k['growth_max_tested']:.0%}, the top of the tested range. Headcount "
           f"trigger: weekly volume more than {trigger} above 2023 for a month, or fewer than "
           f"{cfg['staffing']['sl_goal']:.0%} of contacts reaching an agent within target.")

# ---------------------------------------------------------------------------------------------------------
st.subheader("What would change this recommendation")
n_topics = len(ui.load("topic_profile"))
with st.container(border=True):
    st.markdown(f"""
| If the data shows... | ...the recommendation leans to | What the 2023 data shows |
|---|---|---|
| Volume grows materially (> ~10%) and breaches rise with load | **Hire**: the capacity gap is real and growing | Volume H2 vs H1 {k['volume_change_h2_vs_h1']:+.1%}; breach rates flat across load quintiles (p = {k['rca_load_trend_p_min']:.2f}-{k['rca_load_trend_p_max']:.2f}) [REAL] |
| Volume flat, but demand and roster misaligned by hour or day | **Re-roster** before hiring | Not known: today's roster is not in the data. Weekday-weighted is an assumption for WFM to confirm |
| Volume flat, breaches spread across all segments, not load-driven | **Process fixes**: find what changed | This is the 2023 pattern: resolution SLA fell in every segment and no combination survives the false-discovery check [REAL] |
| A few high-volume, low-complexity topics dominate | **Automation / self-service** | Partly: {k['pareto_top20pct_topics_n']} of {n_topics} topics hold {ui.pct(k['pareto_top20pct_topics_share'], 0)} of tickets; base case deflects {ui.pct(k['auto_deflected_share_base'])} (assumed rates) |

Headcount comes back on the table if volume runs more than {trigger} above 2023 for a month, if fewer than
{cfg['staffing']['sl_goal']:.0%} of contacts reach an agent within target, or if the status history shows the slowdown
comes from capacity diverted outside the ticket data (time on other work, tooling), which the export cannot exclude.
""")

ui.how_to_read(f"""
- **The options.** *Status quo*: today's roster as assumed (weekday-weighted). *A. Hire*: keep it and add
  {k['staff_hire_extra_shifts_by_day']} weekend shifts ({k['staff_hire_extra_fte_equiv_by_day']:.1f} FTE,
  {k['staff_hire_extra_fte_by_day']} whole hires). *B. Re-roster*: move the same shifts from weekdays to weekends.
  *C. Automate*: self-service and routing deflect ~{ui.pct(k['auto_deflected_share_base'], 0)} of tickets, roster
  unchanged. *B + C*: both.
- **Where the SLA comes from.** Every option replays the same synthetic year ticket by ticket; only the roster or the
  ticket population changes, so differences come from the option, not from random demand. Two rules bracket how
  queue wait and pickup delay combine: the later of the two (optimistic) or their sum (conservative).
- **Costs are assumptions** for Finance to confirm. Move the sliders: re-rostering stays free, and hiring scales with
  the FTE cost. Cost per point = year-1 cost / points of response SLA gained over the status quo (optimistic rule).
- **Process ceiling.** Even with no queue at all, response SLA is capped by how slowly some tickets are picked up
  today ({ui.pct(k['staff_process_ceiling'])} in the scenario). Rosters and headcount only shorten the queue, so
  none of them can beat it. The email alert changes the pickup itself, so it raises the ceiling. That is why it is
  shown separately, on the real 2023 tickets, and gets no credit until a pilot measures the catch rate.
- **Growth chart.** How much extra volume the re-rostered team absorbs before fewer than
  {cfg['staffing']['sl_goal']:.0%} of contacts reach an agent within target or utilisation passes
  {cfg['staffing']['max_occupancy']:.0%}. That point is the headcount trigger.
- These options move response SLA. The SLA that fell, resolution, needs the stale-ticket sweep and the slow-path fix.
""")
