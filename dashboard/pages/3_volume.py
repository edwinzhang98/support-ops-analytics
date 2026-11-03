import components as ui
import pandas as pd
import streamlit as st

from support_ops import charts as C
from support_ops import interactive, rca

# Volume Patterns [REAL]: did demand grow, when does it arrive (weekday x hour), what is it about.

ui.page_header("Volume Patterns", "Did ticket volume grow, and when does the work arrive?", "REAL")

k = ui.key_numbers()
P = ui.pct
pareto = ui.load("kpi_topic_pareto")
n_topics = int(pareto.loc[pareto["level"] == "topic", "n_categories"].iloc[0])
weekday_ratio = k["real_weekday_tickets_per_day"] / k["real_weekend_tickets_per_day"]


@st.cache_data(show_spinner=False)
def heatmap_slice(channels: tuple[str, ...], topics: tuple[str, ...]) -> pd.DataFrame:
    """Weekday x hour tickets per week for the selected channels and topics (real export)."""
    return interactive.heatmap_filtered(ui.load("fct_tickets"), list(channels), list(topics))


@st.cache_data(show_spinner=False)
def weekday_rates() -> dict:
    return rca.weekend_workload(ui.load("fct_tickets"))


ui.takeaway(
    f"Volume did not grow: H2 was {abs(100 * k['volume_change_h2_vs_h1']):.1f}% "
    f"{'below' if k['volume_change_h2_vs_h1'] < 0 else 'above'} H1, and month-to-month variation around the "
    f"{k['real_tickets_per_day']:.1f}-a-day average is no larger than chance (p = "
    f"{k['volume_month_seasonality_p']:.2f}). Weekdays get about {weekday_ratio:.1f}x the "
    "weekend volume, arrivals are flat across the hours of the day, and demand is spread across topics (the top "
    f"{k['pareto_top20pct_topics_n']} of {n_topics} topics are {P(k['pareto_top20pct_topics_share'], 0)} of "
    "tickets).")

c1, c2, c3, c4 = st.columns(4)
c1.metric("Volume, 2023 (tickets/day)", f"{k['real_tickets_per_day']:.1f}",
          help=f"{k['real_tickets']:,} tickets created {k['real_first_created']} to {k['real_last_created']} "
               f"({k['real_days_in_window']} days). Monthly totals range from {k['volume_monthly_min']} to "
               f"{k['volume_monthly_max']}.")
c2.metric("Weekday vs weekend (tickets/day)",     # no help icon: the label needs the room
          f"{k['real_weekday_tickets_per_day']:.1f} vs {k['real_weekend_tickets_per_day']:.1f}",
          f"{weekday_ratio:.1f}x as many on weekdays", delta_color="off", delta_arrow="off")
c3.metric("Top topic (% of tickets)", P(k["top_topic_share"]), k["top_topic"], delta_color="off",
          delta_arrow="off", help=f"Largest of the {n_topics} topics in the export, by tickets created in 2023.")
c4.metric("Top 20% of topics (%)", P(k["pareto_top20pct_topics_share"]),
          f"{k['pareto_top20pct_topics_n']} of {n_topics} topics", delta_color="off", delta_arrow="off",
          help=f"Share of all tickets in the {k['pareto_top20pct_topics_n']} largest of {n_topics} topics. At topic "
               f"x product level the top {k['pareto_top20pct_combos_n']} of {k['pareto_combos_total']} combinations "
               f"hold {P(k['pareto_top20pct_combos_share'], 0)}. In a classic 80/20 pattern the top fifth would hold "
               "about 80%.")

# ---------------------------------------------------------------------------------------------
st.subheader("Did volume grow?")
ui.show(C.fig_monthly_volume(ui.load("kpi_monthly")), key="p3_monthly_volume")

# ---------------------------------------------------------------------------------------------
st.subheader("When does the work arrive?")
fct_counts = ui.load("fct_tickets")[["channel", "topic"]]
channel_opts = fct_counts["channel"].value_counts().index.tolist()
topic_opts = fct_counts["topic"].value_counts().index.tolist()
f1, f2 = st.columns([1, 2])
channels = f1.pills("Channel", channel_opts, selection_mode="multi", default=channel_opts, key="p3_channels")
topics = f2.pills("Topic", topic_opts, selection_mode="multi", default=topic_opts, key="p3_topics")
if not channels or not topics:
    st.info("Select at least one channel and one topic to draw the heatmap.")
else:
    heat = heatmap_slice(tuple(channels), tuple(topics))
    n_slice = int(heat["tickets"].sum())
    st.caption(f"Slice: {n_slice:,} of {k['real_tickets']:,} tickets ({n_slice / k['real_tickets']:.0%}). The chart "
               "subtitle describes the full export; check whether the slice follows the same pattern.")
    ui.show(C.fig_volume_heatmap(heat), key="p3_heatmap")

st.subheader("Weekend arrivals vs weekend workload")
ui.show(C.fig_weekday_workload(weekday_rates()), key="p3_weekday_workload")
st.caption("New tickets are counted on the day they are created, resolutions on the day they happen (resolution "
           "timestamp).")

# ---------------------------------------------------------------------------------------------
st.subheader("What are the tickets about?")
LEVELS = {"topic": "Topic", "topic x product": "Topic x product"}
p1, _ = st.columns([1, 2])
level = p1.radio("Level", list(LEVELS), format_func=LEVELS.get, horizontal=True, key="p3_pareto_level")
ui.show(C.fig_topic_pareto(pareto, level), key="p3_pareto")

st.subheader("Did the channel mix change?")
ui.show(C.fig_channel_mix(ui.load("kpi_channel_mix")), key="p3_channel_mix")

ui.how_to_read(f"""
- **Monthly bars** show tickets per calendar day, so short and long months compare fairly. The whiskers are each
  month's 95% Poisson confidence interval: the range its true daily rate plausibly lies in. Most intervals include
  the yearly average, and a test across all twelve months finds no more variation than chance
  (p = {k['volume_month_seasonality_p']:.2f}), so there was no growth and no seasonality to plan for.
- **Heatmap.** Rows are weekdays, columns the hour the ticket was created; darker means more tickets. Each cell is
  "tickets per week" in that slot: the 2023 count for, say, Monday 09:00 divided by the number of Mondays in the
  data. A cell of 0.5 means one ticket every other week in that hour. Use the filters to check one channel or topic
  on its own.
- **Weekend arrivals vs weekend workload.** New tickets drop at weekends ({P(k['weekend_to_weekday_volume'], 0)} of a
  weekday) but resolutions drop much less ({P(k['weekend_to_weekday_resolutions'], 0)}): work created during the
  week is still being finished on Saturday and Sunday. A roster sized on new-ticket counts alone would under-staff
  weekends, which is the starting point of the roster analysis. Treat it as indicative: resolution clocks in this
  export ignore the calendar.
- **Pareto.** Categories sorted by volume (bars) with the running total (line). "Top 20% of categories" is the
  biggest fifth of the categories; in a classic 80/20 pattern they would carry about 80% of tickets. Here they carry
  about half, so no single fix removes most of the volume.
- **Channel mix.** Each month's tickets split by channel. SLA targets depend on the channel, so a mix shift could
  move SLA without anyone working slower. The mix did not shift.
""")
