import components as ui
import pandas as pd
import streamlit as st

from support_ops import charts as C
from support_ops import interactive

# Automation Opportunities. REAL topic volumes and complexity proxies; ASSUMED deflection rates per topic
# (presets low / base / high from config.yaml, adjustable per topic); SYNTHETIC workload (20x) for agent-hours and
# FTE, re-run through the same Erlang C requirement and shift optimisation as the Staffing Model page.

ui.page_header("Automation Opportunities",
               "Which ticket types could self-service or routing take off agents' plates, and how much work would "
               "that save?",
               "REAL", "ASSUMPTION", "SYNTHETIC")

k = ui.key_numbers()
scale = k["synth_scale_factor"]
prof = ui.load("topic_profile")
TOPICS = prof["topic"].tolist()
PRESETS = ["low", "base", "high"]


def slider_key(topic: str) -> str:
    return "p7_rate_" + topic.lower().replace(" ", "_")


def preset_rates(level: str) -> dict[str, int]:
    """Deflection rates of one preset, in whole percent (the sliders' unit)."""
    return {t: round(100 * r) for t, r in zip(prof["topic"], prof[f"deflection_{level}"])}


def apply_preset() -> None:
    """Callback (runs before the rerun): reset every topic slider to the selected preset."""
    for t, v in preset_rates(st.session_state["p7_preset"]).items():
        st.session_state[slider_key(t)] = v


@st.cache_data(show_spinner=False)
def work_by_topic() -> pd.Series:
    """Agent-hours per week by topic in the synthetic year (all touches: first replies and follow-ups)."""
    items = ui.load("synth_work_items")
    return items.groupby("topic")["service_s"].sum() / 3600 / (365 / 7)


@st.cache_data(show_spinner=False, max_entries=512)
def deflection(rates: tuple[tuple[str, float], ...]) -> dict:
    return interactive.deflection_whatif(ui.load("topic_profile"), work_by_topic(), ui.load("staff_demand"),
                                         ui.config()["staffing"], dict(rates))


ui.takeaway(
    f"With the base-case assumptions, self-service and routing would take <b>{ui.pct(k['auto_deflected_share_base'])} "
    f"of tickets</b> off agents: about <b>{k['auto_hours_saved_week_base']:.0f} agent-hours a week</b> at {scale}x "
    "volume, "
    f"or <b>{k['auto_fte_freed_base']} FTE</b> of capacity (range {k['auto_fte_freed_low']}-"
    f"{k['auto_fte_freed_high']} FTE for the low and high assumptions). Treat it as capacity to redeploy to the "
    "stale-ticket sweep and resolution work, not as a saving; the deflection rates are assumptions to pilot first.")

# ---------------------------------------------------------------------------------------------------------
st.subheader("Where to start")
ui.show(C.fig_automation_matrix(prof), key="p7_automation_matrix")
st.caption("REAL topic volumes and complexity proxies; bubble size = ASSUMED base-case deflection rate. Complexity "
           "differs little between topics in this export, so the ranking rests mainly on volume and on whether the "
           "request is informational or transactional (pricing, invoices, feature requests) rather than "
           "troubleshooting.")

# ---------------------------------------------------------------------------------------------------------
st.subheader("What-if: deflection rate by topic")
c1, _ = st.columns([2, 3])
with c1:
    preset = st.radio("Start from a preset (config.yaml)", PRESETS, index=1, horizontal=True, key="p7_preset",
                      on_change=apply_preset, format_func=str.capitalize,
                      help="Choosing a preset resets every topic slider to that preset.")
defaults = preset_rates(preset)
for t, v in defaults.items():        # first visit (or after visiting another page): start from the preset
    st.session_state.setdefault(slider_key(t), v)
lever = dict(zip(prof["topic"], prof["lever"]))
with st.expander("Adjust deflection by topic"):
    cols = st.columns(4)
    rates_pct = {}
    for i, t in enumerate(TOPICS):
        with cols[i % 4]:
            rates_pct[t] = st.slider(f"{t} (%)", 0, 80, step=5, format="%d%%", key=slider_key(t),
                                     help=f"Share of {t.lower()} tickets deflected. Lever: {lever[t]}")
    st.button("Reset sliders to the preset", key="p7_reset", on_click=apply_preset)
changed = [t for t in TOPICS if rates_pct[t] != defaults[t]]
if changed:
    st.caption(f"Custom rates: {len(changed)} topic(s) differ from the {preset} preset ({', '.join(changed)}).")

res = deflection(tuple((t, rates_pct[t] / 100) for t in TOPICS))
bt = res["by_topic"]
m = st.columns(4)
m[0].metric("Tickets deflected (%)", ui.pct(res["deflected_share"]),
            help=f"Share of all tickets: {bt['tickets_deflected_2023'].sum():.0f} of the {k['real_tickets']:,} "
                 "tickets in the 2023 export (REAL topic mix x ASSUMED rates).")
m[1].metric("Agent-hours saved (h/week)", f"{res['hours_saved_week']:.0f}",
            help=f"Per week at the {scale}x synthetic scale.")
m[2].metric("Workload removed (%)", ui.pct(res["workload_reduction"]),
            help="Share of all agent-hours in the synthetic year.")
freed = res["fte_before"] - res["fte_after"]
m[3].metric("FTE needed, before → after", f"{res['fte_before']} → {res['fte_after']}",
            delta=f"{freed} FTE of capacity to redeploy" if freed else None, delta_color="off", delta_arrow="off",
            help="Same Erlang C requirement and shift optimisation as the Staffing Model page, with every hour's "
                 "demand reduced by the workload removed. FTE moves in whole steps.")
ui.show(C.fig_deflection_whatif(bt), key="p7_deflection_whatif")
st.caption(f"SYNTHETIC workload ({scale}x volume) x ASSUMED deflection rates. Hours count every agent touch on a "
           "deflected "
           "ticket: the first reply and its follow-ups.")

# ---------------------------------------------------------------------------------------------------------
st.subheader("Topic detail")
tbl = prof[["topic", "tickets", "share", "lever", "interactions_mean", "tier2_share", "complexity_index"]].merge(
    bt[["topic", "deflection_rate", "tickets_deflected_2023", "agent_hours_saved_week"]], on="topic")
for c in ["share", "tier2_share", "deflection_rate"]:
    tbl[c] = 100 * tbl[c]
st.dataframe(tbl, hide_index=True, width="stretch", column_config={
    "topic": st.column_config.TextColumn("Topic"),
    "tickets": st.column_config.NumberColumn("Tickets", format="%,d", help="Tickets in the 2023 export"),
    "share": st.column_config.NumberColumn("Share", format="%.1f%%", help="Share of 2023 tickets"),
    "lever": st.column_config.TextColumn("Lever", width="medium", help="Self-service or routing lever (assumption)"),
    "interactions_mean": st.column_config.NumberColumn("Interactions", format="%.1f",
                                                       help="Mean agent interactions per ticket"),
    "tier2_share": st.column_config.NumberColumn("Tier 2", format="%.0f%%", help="Share handled by 2nd line"),
    "complexity_index": st.column_config.NumberColumn("Complexity", format="%.2f",
                                                      help="Complexity index, 0 = simplest topic, 1 = most complex"),
    "deflection_rate": st.column_config.NumberColumn("Deflection", format="%.0f%%",
                                                     help="Deflection rate chosen above (assumption)"),
    "tickets_deflected_2023": st.column_config.NumberColumn("Deflected", format="%.0f",
                                                            help="2023 tickets that would have been deflected"),
    "agent_hours_saved_week": st.column_config.NumberColumn("Hours saved/wk", format="%.1f",
                                                            help=f"Agent-hours saved per week at the {scale}x scale")})
st.caption("REAL: tickets, share, interactions, tier-2 share, complexity. ASSUMPTION: lever and deflection rate. "
           f"SYNTHETIC: agent-hours saved ({scale}x scale).")

bug = prof.set_index("topic").loc["Bug report"]
ui.how_to_read(f"""
- **Deflection** is the share of a topic's tickets that never reach an agent: the customer solves it through
  self-service (FAQ, licence or billing portal, guided setup), or the request is routed elsewhere (feature requests
  to a product feedback portal).
- **The rates are assumptions**, not measurements. Low / base / high are judgement calls in config.yaml. Pilot one
  topic, measure how many customers really self-serve and how many come back to an agent, and only then put the
  number into a plan.
- **Reading the matrix.** Across = share of 2023 tickets; up = complexity index. The index averages each topic's
  rank on three real proxies: interactions per ticket, share escalated to tier 2, and median resolution time
  (0 = simplest, 1 = most complex). Bottom-right, big and simple, is where to start. Topics differ little in
  complexity in this export, so volume and the type of request matter most.
- **Why bug reports are not candidates.** A bug needs investigation and a fix, which self-service cannot provide.
  A status page only absorbs repeat contacts about known issues, so the rate stays at
  {bug['deflection_low']:.0%}-{bug['deflection_high']:.0%}.
- **From hours to FTE.** Agent-hours saved = each topic's synthetic workload ({scale}x volume) x its deflection
  rate.
  Removing that share of the work lowers demand in every hour, and the same Erlang C requirement and shift
  optimisation as on the Staffing Model page is re-run. People are whole and every hour needs cover, so FTE falls
  in steps, not smoothly.
- **Capacity, not savings.** Freed FTE is time to redeploy to the stale-ticket sweep, resolution work or growth.
""")
