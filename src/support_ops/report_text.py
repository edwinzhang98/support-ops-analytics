"""Narrative of reports/report.html. Every number is pulled from reports/key_numbers.json
(argument `k`), so the text cannot drift from the analysis.

Block types: ("html", markup) · ("fig", figure_name, reading) · ("table", table_name)
"""
from __future__ import annotations


def P(x, d=1):
    return f"{100 * x:.{d}f}%"


def R(text):  # real-data badge
    return f"<span class='badge b-real'>REAL</span>{text}"


def S(text):  # synthetic badge
    return f"<span class='badge b-syn'>SYNTHETIC</span>{text}"


def A(text):  # assumption badge
    return f"<span class='badge b-asm'>ASSUMPTION</span>{text}"


def recommendations(k: dict) -> list[tuple[str, str, str, str, str]]:
    """(recommendation, owner, expected impact, how we measure, risk) - the canonical list."""
    return [
        ("1. Stale-ticket sweep, then a standing policy for tickets open more than 7 days",
         "Support team leads",
         f"{k['stale_never_resolved']} tickets ({P(k['stale_share_of_tickets'])}) were never resolved; they are "
         f"{P(k['stale_share_of_resolution_breaches'], 0)} of all resolution breaches [REAL]. Working the genuine ones "
         "fixes customers; closing abandoned ones with an outcome code fixes reporting.",
         "Never-resolved share of each month's tickets (target < 5%); tickets open > 7 days (target near zero)",
         "Closing without resolving games the metric: require an outcome code and audit a sample of 50 first"),
        ("2. Find and reverse the resolution slow path that appeared in spring 2023",
         "Support Director + tier-2 lead, with Ops Analytics",
         f"Tickets resolved late rose from {P(k['rca_late_share_h1'])} to {P(k['rca_late_share_h2'])} of all tickets "
         f"in every segment [REAL]. Returning to the H1 rate would put on-time resolution near "
         f"{P(k['rca_on_time_h2_if_late_back_to_h1'], 0)} (a target, not a forecast).",
         "Time in each status (waiting on customer / engineering / tier 2) from the ticket audit log; "
         "resolved-late share back to <= 10%; 90th-percentile resolution time <= 48 h",
         "The cause may sit outside support (a release, tooling, a dependency); needs status-history data"),
        ("3. No headcount request this quarter; revisit at a defined trigger",
         "Support Director",
         "The 2023 data shows a process change, not a capacity shortfall [REAL]; hiring would mainly buy response "
         f"SLA, which is not the SLA that fell. Avoids ~€{k['bc_hire_first_year_eur'] / 1000:,.0f}k in year one "
         "for the hire option in the planning scenario [SYNTHETIC].",
         f"Weekly volume vs 2023: early warning above +{k['growth_sl_within_1pt_no_deflection'] * 100:.0f}% "
         f"(~{k['volume_weekly_trigger_early']} tickets/week vs {k['volume_weekly_mean']:.0f}) for four weeks - re-run this "
         f"capacity model; hard trigger above +{k['growth_holds_until_no_deflection'] * 100:.0f}% "
         f"(~{k['volume_weekly_trigger_hard']}/week). Also: < 90% of contacts reaching an agent within target, "
         "utilisation > 85%",
         "Volume grows faster than expected; mitigated by the trigger and by deflection headroom"),
        ("4. Re-roster toward workload: more weekend cover, fewer weekday overlaps - after checking today's real roster",
         "WFM / scheduling + team leads",
         f"[SYNTHETIC] Same headcount, simulated response SLA {P(k['staff_sl_today_by_day'])} → "
         f"{P(k['staff_sl_proposed'])} under the optimistic rule (+{k['rep_gain_pp_vs_by_day_min']:.1f} to "
         f"+{k['rep_gain_pp_vs_by_day_max']:.1f} points over 5 simulated years; +{k['rep_gain_pp_vs_by_day_sum_min']:.1f} to "
         f"+{k['rep_gain_pp_vs_by_day_sum_max']:.1f} under the conservative rule). Only if today's roster is "
         "weekday-weighted and weekend follow-up work is done when it arises.",
         "Response SLA and queue wait by hour of week; weekend vs weekday response SLA",
         "The real roster is not in the data; staff preferences on weekend shifts"),
        ("5. Pilot the pickup fixes: a 45-minute 'unanswered email' alert and push routing for chat/phone",
         "Team leads + support-tooling owner",
         f"[REAL] Email breaches are a median {k['late_email_breach_median_min_late'] / 60:.1f} hours late - "
         f"missed, not queued. If the alert caught half of them, response SLA would rise by "
         f"~{k['email_alert_uplift_pp_base']:.1f} points (illustration; the catch rate is unknown until piloted).",
         "Share of emails answered within 60 min; alerts fired vs answered within 15 min",
         f"Only {P(k['email_breach_near_miss_share'], 0)} of email breaches are near-misses; alert fatigue"),
        ("6. Pilot self-service for pricing/licensing and invoicing (plus setup guides and a training catalogue); "
         "route feature requests to a feedback portal",
         "Self-service / knowledge owner",
         f"[ASSUMPTION x SYNTHETIC] Base case deflects {P(k['auto_deflected_share_base'], 0)} of tickets, "
         f"~{k['auto_hours_saved_week_base']:.0f} agent-hours/week, ~{k['auto_fte_freed_base']} FTE of capacity "
         f"(range {k['auto_fte_freed_low']}-{k['auto_fte_freed_high']}) to redeploy to actions 1-2 or to absorb growth.",
         "Tickets per topic per week vs 2023 baseline; self-service success rate; CSAT on deflected topics",
         "Deflection rates are assumptions; weak content sends contacts back to agents"),
    ]


def recommendations_table(k: dict) -> str:
    head = "<tr><th>Recommendation</th><th>Owner</th><th>Expected impact</th><th>How we measure</th><th>Risk</th></tr>"
    body = "".join(f"<tr>{''.join(f'<td>{c}</td>' for c in r)}</tr>" for r in recommendations(k))
    return f"<table class='tbl'>{head}{body}</table>"


def _summary(k):
    return [("html", f"""
<div class="summary"><b>Bottom line.</b> The SLA that fell in 2023 is <b>resolution</b>, not response. The data
shows a <b>process change, not a capacity shortfall</b>: volume was flat, breaches do not rise when the desk is busy,
and the slowdown came from a subset of tickets taking a new slow path from spring 2023, plus a pile of tickets that are
never closed. We recommend <b>no headcount request this quarter</b>. Instead: clear and police stale tickets, find the
resolution slow path, and pilot the pickup and self-service fixes. Re-rostering toward weekend workload is worth doing
once today's real roster has been checked.
<ol>
<li>{R(f"<b>Resolution SLA fell from {P(k['resolution_sla_q1'])} in Q1 to {P(k['resolution_sla_q4'])} in Q4</b> "
f"(95% CI {P(k['resolution_sla_q4_lo'], 0)}-{P(k['resolution_sla_q4_hi'], 0)}); response SLA held at "
f"{P(k['response_sla_2023'])} and improved in H2 ({P(k['response_sla_h1'])} → {P(k['response_sla_h2'])}). Volume was "
f"flat (H2 {k['volume_change_h2_vs_h1'] * 100:+.1f}% vs H1). Of the "
f"{k['rca_mix_effect_q1_q4_channel_pp'] + k['rca_rate_effect_q1_q4_channel_pp']:+.1f}-point change, shifts in channel "
f"mix explain {k['rca_mix_effect_q1_q4_channel_pp']:+.1f}; the rest is slower handling within every channel.")}</li>
<li>{R(f"<b>What changed: a new slow path and a stale backlog.</b> Tickets resolved late went from "
f"{P(k['rca_late_share_h1'])} to {P(k['rca_late_share_h2'])} of all tickets, rising gradually from March to October. "
f"The median resolution time barely moved ({k['resolution_median_h_h1']:.0f} → {k['resolution_median_h_h2']:.0f} h), "
f"but the 90th percentile doubled ({k['resolution_p90_h_jan']:.0f} → {k['resolution_p90_h_dec']:.0f} h). It happened "
f"in every channel, priority, topic, tier and agent: none of {k['hotspots_tested_per_sla']:,} segment combinations stands "
f"out for resolution after a multiple-testing check, and breach rates do not rise with workload. Separately, "
f"{k['stale_never_resolved']} tickets ({P(k['stale_share_of_tickets'])}) were never resolved; they are "
f"{P(k['stale_share_of_resolution_breaches'], 0)} of all resolution breaches.")}</li>
<li>{S(f"<b>Capacity and roster (planning scenario at 20x volume):</b> a desk this size needs about "
f"{k['staff_fte_current']} FTE ({k['staff_fte_continuous']:.0f} in pure workload maths; "
f"{k['sens_fte_aht_low']}-{k['sens_fte_aht_high']} if handle times are 30% lower or higher). Spreading the same "
f"people by workload rather than by new-ticket counts moves cover from weekdays to weekends and lifts simulated "
f"response SLA by ~2 points. Hiring {k['staff_hire_extra_fte_equiv_by_day']:.1f} FTE of weekend shifts instead costs "
f"~€{k['bc_hire_first_year_eur'] / 1000:,.0f}k in year one and buys +{k['rep_hire_minus_reroster_pp_min']:.1f} to "
f"+{k['rep_hire_minus_reroster_pp_max']:.1f} points more under the optimistic rule (+{k['rep_hire_minus_reroster_pp_sum_min']:.1f} "
f"to +{k['rep_hire_minus_reroster_pp_sum_max']:.1f} under the conservative rule). No roster beats the "
f"{P(k['staff_process_ceiling'])} ceiling set by slow and missed pickups.")}</li>
</ol></div>
<div class="callout"><b>Roster headline</b> {S("")} Same {k['staff_fte_current']}-FTE desk (20x scenario; today's roster
assumed weekday-weighted): workload-matched roster → simulated <b>response SLA {P(k['staff_sl_today_by_day'])} →
{P(k['staff_sl_proposed'])}</b> under the optimistic rule ({P(k['staff_sl_sum_today_by_day'])} →
{P(k['staff_sl_sum_proposed'])} under the conservative rule). Across 5 simulated years the gain is
+{k['rep_gain_pp_vs_by_day_min']:.1f} to +{k['rep_gain_pp_vs_by_day_max']:.1f} points (optimistic rule;
+{k['rep_gain_pp_vs_by_day_sum_min']:.1f} to +{k['rep_gain_pp_vs_by_day_sum_max']:.1f} conservative). The gain depends on today's real
roster (+{min(k['staff_gain_pp_vs_flat'], k['staff_gain_pp_vs_by_day']):.1f} to +{k['staff_gain_pp_vs_business_hours']:.1f} points across three plausible versions, optimistic rule) and on weekend
follow-up work being done when it arises. The SLA that actually fell, resolution, is not moved by any roster.</div>
"""), ("fig", "sla_trend", "The headline problem, from the real export: resolution SLA (orange) falls through the year; "
       "response SLA (blue) does not."),
        ("fig", "roster_sl", "The planning model: each pair of bars is the same synthetic year under one roster. The dark "
         "bar uses the optimistic rule (queue wait and slow pickup overlap); the light bar the conservative rule (they "
         "add up). The orange line is the best any roster can do with today's pickup behaviour.")]


def _request(k):
    return [("html", """
<p><b>The request (Support Director):</b> "SLA attainment is falling and the team says we don't have enough people.
I have to request headcount for next quarter and need data: did volume go up, or did efficiency go down? How many
people do we need in each time slot? Is there a way to fix it without adding people?"</p>
<p>We turned this into seven testable questions (full version in <code>docs/01_request_and_scope.md</code>):</p>
<table class='tbl'><tr><th>Question</th><th>Answered with</th></tr>
<tr><td>Which SLA is falling - response or resolution - by how much, since when?</td><td>Monthly attainment from timestamps, Wilson 95% CIs [REAL]</td></tr>
<tr><td>Did volume or the channel/topic mix change enough to explain it?</td><td>Volume trend, mix-vs-rate decomposition [REAL]</td></tr>
<tr><td>Did efficiency fall everywhere or in specific segments?</td><td>Breakdowns, breach hotspots with a false-discovery check, agent scorecard [REAL]</td></tr>
<tr><td>Is there evidence of a capacity shortage?</td><td>Breach rate vs workload at arrival, backlog flows [REAL]; hourly queue simulation [SYNTHETIC]</td></tr>
<tr><td>How many agents per hour, vs today's roster?</td><td>Erlang C requirement + roster comparison [SYNTHETIC]</td></tr>
<tr><td>Can we fix it without adding people?</td><td>Re-roster simulation [SYNTHETIC]; pickup and deflection levers [REAL mix x assumptions]</td></tr>
<tr><td>What does each option cost and buy?</td><td>Business case [SYNTHETIC FTE x assumed costs]</td></tr></table>
""")]


def _data(k):
    return [("html", f"""
<p>{R("")}The export has <b>{k['real_tickets']:,} tickets</b> created {k['real_first_created']} to
{k['real_last_created']} ({k['real_tickets_per_day']} per calendar day), handled by {k['real_agents']} named agents. It
includes creation, first-response, resolution and close timestamps, per-ticket SLA deadlines and flags, channel,
priority, topic, tier, interactions and CSAT. It is a public Kaggle dataset described as a data-challenge scenario. Its
provenance is not documented, so we treat it as the real export but do not lean on relationships between fields.</p>
<p><b>SLA policy, inferred from the deadlines:</b> first response within {k['response_target_min_email']} min for email
and {k['response_target_min_chat_phone']} min for chat/phone; resolution within {k['resolution_target_h_chat']} h for
chat and {k['resolution_target_h_email_phone']} h for email/phone. Priority does not change any target.</p>
<p><b>Sanity checks:</b> {k['dq_checks_total']} checks, {k['dq_checks_flagged']} flagged, all handled. Rows reconcile to the
file and keys are unique. The raw SLA flags contradict the timestamps on {k['dq_response_flag_mismatches']} response and
{k['dq_resolution_flag_mismatches']} resolution tickets, so every SLA metric is recomputed from timestamps. Topic labels
have a casing duplicate ({k['dq_topic_case_duplicates_rows']} rows), and {k['dq_interactions_sentinel_rows']} chat tickets
carry a sentinel value of 60 interactions. Full log: <code>docs/03_data_quality_checks.md</code>.</p>
"""), ("table", "dq"),
        ("html", f"""<h3>Why a synthetic scale-up, and how it was checked</h3>
<p>At about 0.3 tickets per hour, most hours of the week see 0-1 tickets and no queue ever forms, so the export cannot
support an hourly staffing model. {S("")}We generated one synthetic year at <b>{k['synth_scale_factor']}x volume</b>
({k['synth_tickets']:,} tickets, ~{k['synth_tickets_per_day']:.0f}/day). It uses the export's arrival rate by weekday and
hour, and bootstraps real tickets created in the same month: mix, interactions, resolution outcome and the real
first-response delay. Only the staffing, roster and business-case numbers use it; everything else is real. Generation
logic: <code>docs/04_synthetic_data.md</code>.</p>"""),
        ("fig", "synth_validation", f"Real vs synthetic share of tickets by channel, topic and priority. The largest gap is "
         f"{k['synth_max_mix_gap_pp']:.1f} points; resolution SLA is {P(k['resolution_sla_2023'])} real vs "
         f"{P(k['synth_resolution_sla'])} synthetic.")]


def _volume(k):
    return [
        ("fig", "monthly_volume", "Each bar is tickets per calendar day in that month, so short months are comparable. "
         "Error bars show where a month would land by chance alone."),
        ("fig", "volume_heatmap", f"Darker = more tickets in that weekday-hour, averaged over the year. Weekdays average "
         f"{k['real_weekday_tickets_per_day']} tickets a day vs {k['real_weekend_tickets_per_day']} at weekends. The hourly "
         "curve is flat, which is unusual for a European B2B desk; we flag it as a data limitation."),
        ("fig", "weekday_workload", "Resolutions keep happening at weekends. In this export the resolution clock ignores "
         "the calendar, so this is indicative only. It does mean planning on new-ticket counts alone would understate "
         "weekend work if follow-ups really are done when they arise."),
        ("fig", "pareto_topic", f"Top 20% of topics ({k['pareto_top20pct_topics_n']} of 7) = "
         f"{P(k['pareto_top20pct_topics_share'], 0)} of tickets. At topic x product level, the top "
         f"{k['pareto_top20pct_combos_n']} of {k['pareto_combos_total']} = {P(k['pareto_top20pct_combos_share'], 0)}. Demand is "
         "spread out, so no single fix removes most of the volume."),
        ("fig", "channel_mix", "The mix behind the SLA targets did not change, so a mix shift cannot explain the decline."),
    ]


def _efficiency(k):
    return [
        ("fig", "resolution_composition", f"Every ticket ends in one of three states. 'Resolved late' grew from "
         f"{P(k['rca_late_share_h1'])} (H1) to {P(k['rca_late_share_h2'])} (H2) of tickets, while 'never resolved' fell "
         f"slightly ({P(k['rca_never_share_h1'])} → {P(k['rca_never_share_h2'])}). Part of the late rise may therefore be "
         "tickets that would previously have gone stale and now close late."),
        ("fig", "resolution_hist", f"Most tickets still close within two days; median resolution moved only "
         f"{k['resolution_median_h_h1']} h → {k['resolution_median_h_h2']} h. The change is a flat 48-144 h tail: the 90th "
         f"percentile went from {k['resolution_p90_h_jan']:.0f} h in January to {k['resolution_p90_h_dec']:.0f} h in "
         "December. A capacity shortfall would slow everything; here only a subset of tickets got slower."),
        ("fig", "breakdown_channel", f"Response SLA differs by channel because the targets do: phone "
         f"{P(k['response_sla_phone'])} and chat {P(k['response_sla_chat'])} (2-minute target) vs email "
         f"{P(k['response_sla_email'])} (60 minutes)."),
        ("fig", "breakdown_topic", f"Resolution SLA by topic: the intervals overlap (chi-square p = "
         f"{k['rca_topic_p_resolution']}). Priority has no effect either (p = {k['rca_priority_p_resolution']}) - "
         "high-priority tickets are not handled faster, and the SLA targets ignore priority."),
        ("fig", "hotspots_response", "Each row is a combination of up to three dimensions with at least 30 tickets. Orange "
         f"= survives a false-discovery-rate correction across all {k['hotspots_tested_per_sla']:,} combinations tested. "
         "This is one finding: Phone and its sub-segments."),
        ("fig", "hotspots_resolution", "No combination survives. The highest raw breach rates are small cells consistent "
         "with chance - which is why we do not report a 'Monday morning + billing + high priority' style hotspot."),
        ("fig", "agent_scorecard", f"Agent attainment ranges {P(k['agent_resolution_sla_min'], 0)}-"
         f"{P(k['agent_resolution_sla_max'], 0)} with overlapping intervals (p = {k['rca_agent_p_resolution']}, not "
         f"significant once the number of tests is accounted for). {k['agents_declined_h1_to_h2']} of 8 agents declined "
         "from H1 to H2: the slowdown is team-wide."),
        ("fig", "breach_lateness", f"Median lateness: chat {k['late_chat_breach_median_min_late']} min, phone "
         f"{k['late_phone_breach_median_min_late']} min, email {k['late_email_breach_median_min_late']:.0f} min. Email breaches "
         "are tickets missed for hours - an alerting problem, not a queue."),
    ]


def _rootcause(k):
    return [
        ("html", "<h3>Is it volume?</h3>" + R(
            f"No. Volume was flat (H2 {k['volume_change_h2_vs_h1'] * 100:+.1f}% vs H1, every month within chance "
            "variation), and the mix did not shift. A shift-share decomposition of the Q1 → Q4 change in resolution SLA "
            f"attributes {k['rca_mix_effect_q1_q4_channel_pp']:+.2f} points to channel mix and "
            f"{k['rca_rate_effect_q1_q4_channel_pp']:+.2f} to performance within channels (by topic: "
            f"{k['rca_mix_effect_q1_q4_topic_pp']:+.2f} vs {k['rca_rate_effect_q1_q4_topic_pp']:+.2f}).")),
        ("table", "decomposition"),
        ("html", "<h3>Is it a capacity shortfall?</h3>" + R(
            "Not that the data can see. If agents were overloaded, tickets arriving when more work is in progress should "
            f"breach more often. They don't: across workload quintiles the breach rate is flat (trend-test p = "
            f"{k['rca_load_trend_p_min']}-{k['rca_load_trend_p_max']}). Breaches do not differ by hour of day (p = "
            f"{k['rca_hour_of_day_p_response']}), day of week (p = {k['rca_day_of_week_p_response']}) or weekday vs weekend "
            f"(p = {k['rca_weekend_p_response']}). All 8 named agents were active every month. A shortfall would also "
            "slow every ticket and grow the active backlog. Instead the median barely moved, the active backlog stayed "
            "flat, and the never-resolved share fell. Caveat: a capacity change outside the ticket data, such as time "
            "diverted to other work, cannot be excluded.")),
        ("fig", "load_vs_breach", "Each point is a fifth of all tickets, grouped by how many tickets were already in "
         "progress when they arrived. Flat lines = no workload effect."),
        ("html", "<h3>Is it the backlog?</h3>" + R(
            f"The open backlog grows all year only because {k['stale_never_resolved']} tickets are never closed "
            f"({k['stale_in_progress']} 'In progress', {k['stale_open_no_response']} never answered; median age "
            f"{k['stale_median_age_days']:.0f} days at snapshot). Active work stays at ~{k['active_backlog_mean']:.0f} "
            f"tickets (max {k['active_backlog_max']}), which matches arrivals x time in system (Little's law: "
            f"{k['active_backlog_littles_law']:.0f}). Weekly resolutions track arrivals; there are no arrival spikes.")),
        ("fig", "backlog", "Stacked: active tickets (blue) and tickets open more than 7 days (grey) at the end of each day."),
        ("fig", "weekly_flow", "When the lines track each other, throughput is keeping up; the steady gap is the stale tickets."),
        ("fig", "sim_queue", "In the synthetic scale-up the same diagnostic separates the two causes: arrivals are flat, so "
         "a queue that builds every weekend under the assumed roster is a staffing gap, not a volume spike."),
        ("html", "<h3>So what did change?</h3>" + R(
            f"Tickets resolved late rose gradually from March to October, from {P(k['rca_late_share_before_step'])} to "
            f"{P(k['rca_late_share_after_step'])} of tickets (the largest single step is around "
            f"{k['rca_step_month_late_share']}). It hit every segment equally. That points to something system-wide in the "
            "resolution stage - a process, policy, tooling or dependency change, for example tickets waiting on "
            "engineering or on customers - rather than any team or person. The export has no status history, so it "
            "cannot say which. The next step is to pull time-in-status from the ticket audit log."))]


def _staffing(k):
    return [
        ("html", f"""<p>{S("")}{A("")}<b>What this part can and cannot say.</b> The model answers "how many people per
hour does a desk like this need, and how should they be spread?". It cannot say whether today's team is short: we
do not have the real roster or headcount. The real-data tests above are the evidence on that, and they show no capacity
signal. All numbers here are for a {k['synth_scale_factor']}x-volume version of the export.</p>
<p><b>Method.</b> For each of the 168 hours of the week we compute the work arriving and the people needed. Work
arriving means live chat/phone contacts, plus email first replies and follow-up touches. The people needed is the
largest of three numbers:</p>
<ul>
<li>enough agents for {P(k['sla_goal'], 0)} of live contacts to be answered within 2 minutes (Erlang C; live work may interrupt
email work, so it sees the whole team);</li>
<li>enough that agents are busy no more than 85% of the time;</li>
<li>at least one person on duty.</li>
</ul>
<p>That is grossed up for 30% shrinkage (breaks, meetings, absence) and rounded once to whole people. An integer
program then turns the hourly need into 8-hour shifts, and a discrete-event simulation replays the synthetic year
ticket by ticket under each roster.</p>
<p><b>Handle time is not in the export.</b> We assume 12/10/8 minutes for a first chat/phone/email touch and 6 minutes
per follow-up, about {k['synth_workload_min_per_ticket']:.0f} agent-minutes per ticket. Follow-ups are spread over each
ticket's life. The meaning of "agent interactions" is uncertain, so it gets its own sensitivity row.</p>
<p><b>How response time is built.</b> A customer's response time combines (a) waiting for a free agent, which staffing
controls, and (b) the real pickup delay observed in the export, which staffing does not. We do not know exactly how the
two combine, so every result is shown twice. The <b>optimistic rule</b> takes the later of the two (they overlap); the
<b>conservative rule</b> adds them up.</p>"""),
        ("fig", "erlang_curve", "Why staffing has diminishing returns: each extra agent buys less service level than the last."),
        ("fig", "requirement_vs_roster", f"Required people per hour: {k['staff_weekday_scheduled_min']}-"
         f"{k['staff_weekday_scheduled_max']} on weekdays and {k['staff_weekend_scheduled_min']}-"
         f"{k['staff_weekend_scheduled_max']} at weekends. Total workload, not the 2-minute "
         f"live target, sets the number in {k['staff_hours_binding_workload']} of 168 hours. The export has no intraday "
         "shape, so the workload-matched roster is close to flat; what changes is the weekday/weekend balance."),
        ("fig", "gap_heatmap", f"Today's assumed roster (headcount set by new-ticket counts) is short in "
         f"{k['staff_hours_under_today_by_day']} hours, all at weekends, and carries spare people on weekdays."),
        ("html", f"<p><b>Headcount.</b> The cheapest roster covering every hour uses {k['staff_min_shifts']} eight-hour "
                 f"shifts a week, i.e. <b>{k['staff_fte_current']} FTE</b> at five shifts per person (a "
                 f"{k['staff_weekly_shifts']}-shift budget once rounded to whole FTE). Pure workload maths with no rounding "
                 f"gives {k['staff_fte_continuous']:.1f} FTE; the difference is the cost of whole people in every hour, "
                 "8-hour shift blocks and 24/7 minimum cover. The simulated roster has headroom: "
                 f"{P(k['staff_queue_sl_proposed'])} of contacts reach an agent within target, against a 90% goal.</p>"
                 "<h3>Proposed roster (people starting each shift)</h3>"),
        ("table", "roster_proposed"),
        ("html", "<h3>Today's roster, as assumed</h3>"), ("table", "roster_today"),
        ("fig", "roster_sl", f"Same {k['staff_fte_current']} FTE, optimistic / conservative rule: weekday-weighted "
         f"{P(k['staff_sl_today_by_day'])} / {P(k['staff_sl_sum_today_by_day'])}, flat {P(k['staff_sl_today_flat'])} / "
         f"{P(k['staff_sl_sum_today_flat'])}, day-weighted {P(k['staff_sl_today_business_hours'])} / "
         f"{P(k['staff_sl_sum_today_business_hours'])}, workload-matched {P(k['staff_sl_proposed'])} / "
         f"{P(k['staff_sl_sum_proposed'])}. Hiring {k['staff_hire_extra_fte_equiv_by_day']:.1f} FTE of weekend shifts on "
         f"top of today's roster: {P(k['staff_sl_hire_by_day'])} / {P(k['staff_sl_sum_hire_by_day'])}."),
        ("html", f"""<p><b>Robustness.</b> {S('')} On 5 independent synthetic years, the workload-matched roster beats the
weekday-weighted one by +{k['rep_gain_pp_vs_by_day_min']:.1f} to +{k['rep_gain_pp_vs_by_day_max']:.1f} points
(optimistic) and +{k['rep_gain_pp_vs_by_day_sum_min']:.1f} to +{k['rep_gain_pp_vs_by_day_sum_max']:.1f} (conservative).
The ranking of rosters is the same every time. Hiring instead adds +{k['rep_hire_minus_reroster_pp_min']:.1f} to
+{k['rep_hire_minus_reroster_pp_max']:.1f} points more (optimistic) or +{k['rep_hire_minus_reroster_pp_sum_min']:.1f} to
+{k['rep_hire_minus_reroster_pp_sum_max']:.1f} (conservative). The simulation reproduces Erlang C within a point on
textbook cases.</p>
<p><b>Stress test of the weekend assumption.</b> The weekend gap exists because the model does follow-up work when it
arises, including weekends. If instead every weekend follow-up waited until Monday, Mondays would be overloaded under
every roster. The gain from re-rostering would then swing between {k['deferred_gain_pp_vs_by_day_sum']:+.1f} and
{k['deferred_gain_pp_vs_by_day']:+.1f} points depending on the rule, so it is not robust. Before moving shifts, check the
real roster and how weekend follow-ups are handled today.</p>"""),
        ("table", "replications"),
        ("fig", "sensitivity", f"FTE needed ranges from {k['sens_fte_aht_low']} (handle time -30%) to "
         f"{k['sens_fte_aht_high']} (handle time +30%); narrower readings of 'interactions' give {k['sens_fte_half_agent']}. "
         f"Two separate teams for chat/phone and email would need {k['sens_fte_two_pool']}. At 10x or 40x the export's "
         f"volume the answer is {k['sens_fte_scale_10x']} or {k['sens_fte_scale_40x']}. Changing the live SLA goal from 80% "
         "to 95% changes nothing, because workload binds first."),
        ("table", "sensitivity"),
        ("fig", "growth", f"With the workload-matched roster, simulated response SLA stays within a point of today's level up to "
         f"+{k['growth_sl_within_1pt_no_deflection'] * 100:.0f}% volume and slips after that "
         f"({P(k['growth_sl_at_plus10_no_deflection'])} at +10%, {P(k['growth_sl_at_plus25_no_deflection'])} at +25%). "
         f"The roster still meets the staffing goal itself at +{k['growth_holds_until_no_deflection'] * 100:.0f}% and fails it at "
         f"+{k['growth_staffing_fails_at_no_deflection'] * 100:.0f}%. With "
         f"base-case deflection the team absorbs about +{k['growth_sl_within_1pt_with_deflection'] * 100:.0f}% before "
         "response SLA slips a point. These are the triggers for revisiting headcount."),
    ]


def _automation(k):
    return [
        ("html", f"<p>{R('')}{A('')}Topic volumes and complexity proxies (interactions, tier-2 share, resolution time) are "
                 "real; deflection rates are assumptions (low / base / high in <code>config.yaml</code>). The complexity "
                 "proxies differ little across topics in this export. The ranking is therefore driven mainly by volume and "
                 "by whether the request is informational or transactional (pricing, invoices, feature requests) rather "
                 "than troubleshooting.</p>"),
        ("fig", "automation_matrix", "Bottom-right = high volume, low complexity = best candidates."),
        ("fig", "hours_saved", "Agent-hours per week removed if each topic's assumed deflection is achieved (synthetic workload)."),
        ("table", "automation"),
        ("html", f"<p>Base case: {P(k['auto_deflected_share_base'], 0)} of tickets ({k['auto_real_tickets_deflected_base']:.0f} "
                 f"of the 2023 export), ~{k['auto_hours_saved_week_base']:.0f} agent-hours a week, "
                 f"{k['auto_fte_freed_base']} FTE of capacity (range {k['auto_fte_freed_low']}-{k['auto_fte_freed_high']}; "
                 f"worth ~€{k['bc_automation_capacity_value_eur'] / 1000:,.0f}k a year at the assumed FTE cost). We treat "
                 "this as capacity to redeploy to the stale-ticket sweep and resolution work, or to absorb growth - not as "
                 "a saving.</p>"),
    ]


def _business(k):
    return [
        ("html", f"<p>{S('')}{A('')}All options start from the same planning scenario: a {k['staff_fte_current']}-FTE "
                 "desk at 20x volume with the assumed weekday-weighted roster. Response SLA for each option comes from "
                 "simulating the same synthetic year. Costs are assumptions to confirm with Finance "
                 f"(€{k['cost_fte_annual_eur']:,} per FTE per year fully loaded). Hiring is costed in FTE-equivalents of the "
                 f"{k['staff_hire_extra_shifts_by_day']} weekend shifts actually needed "
                 f"(€{k['bc_hire_first_year_eur'] / 1000:,.0f}k in year one); as {k['staff_hire_extra_fte_by_day']} whole "
                 f"full-time hires it would be ~€{k['bc_hire_first_year_whole_hires_eur'] / 1000:,.0f}k. Remember the SLA these "
                 "options move is response, not resolution.</p>"),
        ("fig", "options", "Optimistic (dark) and conservative (light) rule for each option. Annotations show first-year cost."),
        ("table", "options"),
        ("fig", "email_alert", f"The pickup fix moves the ceiling itself. Based on the {k['email_breaches']} real email "
         "breaches; the catch rate is the unknown, so this is a pilot, not a forecast."),
        ("html", f"""<div class="callout"><b>Recommendation:</b> no headcount request this quarter. The 2023 data shows a
process change, not a capacity shortfall, and hiring would mainly buy response SLA, which is not the SLA that fell.
Clear and police stale tickets. Find the resolution slow path. Pilot the email alert and self-service. Re-roster toward
weekend workload once WFM confirms today's roster. If weekly volume runs more than
+{k['growth_sl_within_1pt_no_deflection'] * 100:.0f}% above 2023 (about {k['volume_weekly_trigger_early']} tickets a week
against {k['volume_weekly_mean']:.0f}) for four weeks, re-run this capacity model. Above
+{k['growth_holds_until_no_deflection'] * 100:.0f}% (about {k['volume_weekly_trigger_hard']} a week), or if fewer than 90% of
contacts reach an agent within target, the choice is hire or deflect: the planning roster still meets its staffing goal at
+{k['growth_holds_until_no_deflection'] * 100:.0f}% and fails it at +{k['growth_staffing_fails_at_no_deflection'] * 100:.0f}%.</div>"""),
    ]


def _recs(k):
    return [("table", "recommendations")]


def _limits(k):
    return [("html", f"""<ul>
<li><b>Provenance.</b> The export is a public data-challenge dataset. Several patterns are unusual for a production
system:
<ul>
<li>a flat 24-hour arrival curve for European customers;</li>
<li>CSAT unrelated to breaches ({k['csat_breached']} vs {k['csat_met']});</li>
<li>near-uniform interaction counts;</li>
<li>resolution times capped near 6 days;</li>
<li>on-time response times spread evenly inside the target window;</li>
<li>resolution clocks that ignore weekends.</li>
</ul>
Relationships between fields are therefore not over-read.</li>
<li><b>Real vs synthetic.</b> The root cause, volume, efficiency, backlog, hotspot and automation-mix findings are real.
Staffing levels, roster SLA, growth headroom and FTE costs are synthetic. They depend on the scale factor, assumed handle
times, the way follow-ups are timed, and an assumed current roster. The model is a template to re-run on real roster
and handle-time data.</li>
<li><b>Response-time rule.</b> How queue waits and slow pickups combine is unknown, so results are bracketed by an
optimistic and a conservative rule.</li>
<li><b>Agent attribution.</b> <code>Agent Name</code> is the current owner of the ticket, so agent comparisons are for
coaching conversations, not performance ratings.</li>
<li><b>Correlation, not causation.</b> The timing of the resolution slowdown is clear; its cause is not in the data.</li>
<li><b>What we would ask for next:</b>
<ul>
<li>the actual WFM roster and headcount;</li>
<li>agent activity or handle-time logs;</li>
<li>ticket status history (time waiting on customer, engineering or tier 2);</li>
<li>more than one year of data;</li>
<li>CSAT on resolved as well as closed tickets.</li>
</ul></li></ul>""")]


def _appendix(k):
    return [("html", """<ul>
<li>Metric definitions (response / resolution SLA, backlog, handle time, occupancy, shrinkage): <code>docs/02_metric_definitions.md</code></li>
<li>Data-quality log: <code>docs/03_data_quality_checks.md</code> · synthetic data generation: <code>docs/04_synthetic_data.md</code></li>
<li>Assumptions with sources and sensitivity: <code>docs/assumptions.md</code></li>
<li>SQL for every KPI: <code>sql/</code> (each file runs standalone in DuckDB) · model code: <code>src/support_ops/</code></li>
<li>Notebooks with full outputs (HTML in <code>reports/</code>): 01 volume, 02 efficiency, 03 backlog, 04 staffing, 05 automation</li>
<li>Reproduce: <code>make all</code> (or <code>python run.py</code>), fixed random seed 42.</li></ul>""")]


SECTIONS = [
    {"id": "summary", "title": "1. Executive summary", "blocks": _summary},
    {"id": "request", "title": "2. The request and how we framed it", "blocks": _request},
    {"id": "data", "title": "3. Data and sanity checks", "blocks": _data},
    {"id": "volume", "title": "4. Volume patterns: did demand grow?", "blocks": _volume},
    {"id": "efficiency", "title": "5. Efficiency and SLA: what fell, and where", "blocks": _efficiency},
    {"id": "rootcause", "title": "6. Backlog and root cause", "blocks": _rootcause},
    {"id": "staffing", "title": "7. Staffing model: how many people per hour", "blocks": _staffing},
    {"id": "automation", "title": "8. Automation opportunities", "blocks": _automation},
    {"id": "business", "title": "9. Headcount business case", "blocks": _business},
    {"id": "recs", "title": "10. Recommendations", "blocks": _recs},
    {"id": "limits", "title": "11. Limitations and what we would need next", "blocks": _limits},
    {"id": "appendix", "title": "12. Appendix: definitions, assumptions, reproducibility", "blocks": _appendix},
]
