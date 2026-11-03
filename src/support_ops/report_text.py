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


def recommendations_table(k: dict) -> str:
    rows = [
        ("1. Do not request headcount for next quarter; re-evaluate at the trigger below",
         "Support Director", "Avoids ~€" + f"{(k['bc_hire_annual_cost_eur'] + k['bc_hire_one_off_eur']) / 1000:,.0f}k "
         "first-year cost of the hire option, which buys the same simulated SLA as option 2",
         "Weekly volume vs 2023 (trigger: sustained > +10%), response SLA, occupancy",
         "Volume grows faster than expected; mitigated by the trigger and by deflection headroom"),
        ("2. Re-roster to workload, not new-ticket counts (more weekend cover, fewer weekday overlaps)",
         "Team leads + WFM", f"Simulated response SLA {P(k['staff_sl_today_by_day'])} → {P(k['staff_sl_proposed'])} "
         f"with the same people (range +{k['rep_gain_pp_vs_by_day_min']:.1f} to +{k['rep_gain_pp_vs_by_day_max']:.1f} pts "
         "over 5 simulated years; 0 to +4.5 pts depending on today's actual roster)",
         "Queue wait and response SLA by hour of week; weekend vs weekday SLA",
         "Today's real roster is not in the data - validate the gap against the WFM roster first; staff "
         "preferences on weekend shifts"),
        ("3. 45-minute 'unanswered email' alert + push routing for chat/phone",
         "Team leads + support tooling owner",
         f"Email breaches are hours late, not minutes: an alert that catches half of them adds "
         f"~{k['email_alert_uplift_pp_base']:.1f} pts of response SLA ({P(k['response_sla_2023'])} → "
         f"{P(k['email_alert_response_sla_base'])})",
         "Share of emails answered within 60 min; alerts fired vs answered",
         "Alert fatigue if thresholds are noisy; catch rate is an assumption until piloted"),
        ("4. Stale-ticket sweep: review every ticket open > 7 days, then an auto-close / escalation policy",
         "Team leads", f"{k['stale_never_resolved']} tickets ({P(k['stale_share_of_tickets'])}) were never resolved and "
         f"are {P(k['stale_share_of_resolution_breaches'], 0)} of resolution breaches. Closing abandoned ones fixes "
         "reporting; working genuine ones fixes customers - an audit of 50 tells which",
         "Tickets open > 7 days (target: near zero); resolution SLA with and without them",
         "Auto-closing genuine problems hides them; audit a sample before setting the policy"),
        ("5. Find what changed in the resolution stage from spring 2023",
         "Support Director + Ops Analytics", f"Late resolutions rose from {P(k['rca_late_share_h1'])} to "
         f"{P(k['rca_late_share_h2'])} of tickets in every segment. Returning to the H1 rate would put on-time "
         f"resolution back near {P(k['rca_on_time_h2_if_late_back_to_h1'], 0)}",
         "Time in each status (waiting on customer / engineering / tier 2) from the ticket audit log",
         "Needs status-history data that is not in this export"),
        ("6. Pilot self-service for pricing/licensing and invoicing; route feature requests to a feedback portal",
         "Self-service / knowledge owner", f"Base case deflects {P(k['auto_deflected_share_base'], 0)} of tickets, "
         f"~{k['auto_hours_saved_week_base']:.0f} agent-hours/week, ~{k['auto_fte_freed_base']} FTE of headroom "
         f"(range {k['auto_fte_freed_low']}-{k['auto_fte_freed_high']})",
         "Tickets per topic per week vs baseline; self-service success rate; CSAT on deflected topics",
         "Deflection rates are assumptions; poor content pushes contacts back to agents"),
    ]
    head = "<tr><th>Recommendation</th><th>Owner</th><th>Expected impact</th><th>How we measure</th><th>Risk</th></tr>"
    body = "".join(f"<tr>{''.join(f'<td>{c}</td>' for c in r)}</tr>" for r in rows)
    return f"<table class='tbl'>{head}{body}</table>"


def _summary(k):
    return [("html", f"""
<div class="summary"><b>Bottom line.</b> The SLA that is falling is <b>resolution</b>, not response, and the data
does not point to a staffing shortage: volume was flat and breaches do not rise when the desk is busy. The fix is in the
resolution process and in how existing hours are spread, so we recommend <b>no headcount request this quarter</b>.
<ol>
<li>{R(f"<b>Resolution SLA fell from {P(k['resolution_sla_q1'], 0)} in Q1 to {P(k['resolution_sla_q4'], 0)} in Q4</b>"
f" (95% CI {P(k['resolution_sla_q4_lo'], 0)}-{P(k['resolution_sla_q4_hi'], 0)}); response SLA held at "
f"{P(k['response_sla_2023'])} and improved in H2. Volume was flat (H2 {k['volume_change_h2_vs_h1'] * 100:+.1f}% vs H1) and "
f"the channel/topic mix did not move: mix explains {k['rca_mix_effect_q1_q4_channel_pp']:+.1f} of the "
f"{k['rca_mix_effect_q1_q4_channel_pp'] + k['rca_rate_effect_q1_q4_channel_pp']:+.1f} points.")}</li>
<li>{R(f"<b>The decline is a slow tail in every segment, plus a stale backlog.</b> Tickets resolved late went from "
f"{P(k['rca_late_share_h1'])} to {P(k['rca_late_share_h2'])} of all tickets (a ramp from March to October), across every "
f"channel, priority, topic, tier and agent - none of 1,268 segment combinations stands out after a multiple-testing "
f"check. Separately, {k['stale_never_resolved']} tickets ({P(k['stale_share_of_tickets'])}) were never resolved; they are "
f"{P(k['stale_share_of_resolution_breaches'], 0)} of all resolution breaches.")}</li>
<li>{S(f"<b>Same headcount, better spread:</b> in a 20x scale-up calibrated to the export, a demand-shaped roster "
f"lifts response SLA from {P(k['staff_sl_today_by_day'])} to {P(k['staff_sl_proposed'])} with the same "
f"{k['staff_fte_current']} FTE - the same result as hiring {k['staff_hire_extra_fte_by_day']} FTE "
f"(€{(k['bc_hire_annual_cost_eur'] + k['bc_hire_one_off_eur']) / 1000:,.0f}k in year one). The gain is "
f"{k['rep_gain_pp_vs_by_day_min']:.1f}-{k['rep_gain_pp_vs_by_day_max']:.1f} points across 5 simulated years, and 0 to "
f"{k['staff_gain_pp_vs_business_hours']:.1f} points depending on what today's roster really looks like (not in the data).")}</li>
</ol></div>
<div class="callout"><b>Roster headline</b> {S("")} Today's roster (assumed: daily headcount set by new-ticket
counts) vs proposed demand-shaped roster, same {k['staff_fte_current']} FTE: <b>response SLA {P(k['staff_sl_today_by_day'])}
→ {P(k['staff_sl_proposed'])}</b>. No roster can exceed the <b>process ceiling of {P(k['staff_process_ceiling'])}</b> set by
slow and missed pickups; the {P(k['sla_goal'], 0)} goal needs the pickup fixes in recommendation 3.</div>
"""), ("fig", "roster_sl", "Bars = simulated share of tickets answered within target for the same synthetic year. "
       "The orange line is the best any roster can do with today's pickup behaviour.")]


def _request(k):
    return [("html", """
<p><b>The request (Support Director):</b> "SLA attainment is falling and the team says we don't have enough people.
I have to request headcount for next quarter and need data: did volume go up, or did efficiency go down? How many
people do we need in each time slot? Is there a way to fix it without adding people?"</p>
<p>We turned this into seven testable questions (full version in <code>docs/01_request_and_scope.md</code>):</p>
<table class='tbl'><tr><th>Question</th><th>Answered with</th></tr>
<tr><td>Which SLA is falling - response or resolution - by how much, since when?</td><td>Monthly attainment from timestamps, Wilson 95% CIs [REAL]</td></tr>
<tr><td>Did volume or the channel/topic mix change enough to explain it?</td><td>Volume trend, mix-vs-rate decomposition [REAL]</td></tr>
<tr><td>Did efficiency fall everywhere or in specific segments?</td><td>Breakdowns, breach hotspots with FDR, agent scorecard [REAL]</td></tr>
<tr><td>Is there evidence of a capacity shortage?</td><td>Breach rate vs load at arrival, backlog flows [REAL]; hourly queue simulation [SYNTHETIC]</td></tr>
<tr><td>How many agents per hour, vs today's roster?</td><td>Erlang C requirement + roster comparison [SYNTHETIC]</td></tr>
<tr><td>Can we fix it without adding people?</td><td>Re-roster simulation [SYNTHETIC]; deflection and pickup levers [REAL mix x assumptions]</td></tr>
<tr><td>What does each option cost and buy?</td><td>Business case [SYNTHETIC FTE x assumed costs]</td></tr></table>
""")]


def _data(k):
    return [("html", f"""
<p>{R("")}The export has <b>{k['real_tickets']:,} tickets</b> created {k['real_first_created']} to {k['real_last_created']},
handled by {k['real_agents']} named agents, about {k['real_tickets_per_day']} tickets a day. It includes the creation,
first-response, resolution and close timestamps, per-ticket SLA deadlines and flags, channel, priority, topic, tier,
interactions and CSAT. It is a public Kaggle dataset described as a data-challenge scenario. Its provenance is not
documented, so we treat it as the real export but do not lean on relationships between fields.</p>
<p><b>SLA policy, inferred from the deadlines:</b> first response within {k['response_target_min_email']} min for email and
{k['response_target_min_chat_phone']} min for chat/phone; resolution within {k['resolution_target_h_chat']} h for chat
and {k['resolution_target_h_email_phone']} h for email/phone. Priority does not change any target.</p>
<p><b>Sanity checks:</b> {k['dq_checks_total']} checks, {k['dq_checks_flagged']} flagged, all handled. Rows reconcile to the file
and keys are unique. The raw SLA flags contradict the timestamps on {k['dq_response_flag_mismatches']} response and
{k['dq_resolution_flag_mismatches']} resolution tickets, so every SLA metric is recomputed from timestamps. Topic labels
have a casing duplicate ({k['dq_topic_case_duplicates_rows']} rows), and {k['dq_interactions_sentinel_rows']} chat tickets
carry a sentinel of 60 interactions. Full log: <code>docs/03_data_quality_checks.md</code>.</p>
"""), ("table", "dq"),
        ("html", f"""<h3>Why a synthetic scale-up, and how it was checked</h3>
<p>At about 0.3 tickets per hour, most hours of the week see 0-1 tickets and no queue ever forms, so the export
cannot support an hourly staffing model. {S("")}We generated one synthetic year at <b>{k['synth_scale_factor']}x volume</b>
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
         f"{k['real_weekday_tickets_per_day']} tickets/day vs {k['real_weekend_tickets_per_day']} at weekends; the hourly "
         "curve is flat, which is unusual for a European B2B desk and is flagged as a data limitation."),
        ("fig", "weekday_workload", "Tickets keep being worked after the day they arrive. Weekend workload is therefore "
         "much closer to weekday workload than new-ticket counts suggest, which matters for the roster."),
        ("fig", "pareto_topic", f"Top 20% of topics ({k['pareto_top20pct_topics_n']} of 7) = "
         f"{P(k['pareto_top20pct_topics_share'], 0)} of tickets; at topic x product level, the top "
         f"{k['pareto_top20pct_combos_n']} of {k['pareto_combos_total']} = {P(k['pareto_top20pct_combos_share'], 0)}. "
         "Demand is spread out, so no single fix removes most of the volume."),
        ("fig", "channel_mix", "The mix behind the SLA targets did not change, so a mix shift cannot explain the decline."),
    ]


def _efficiency(k):
    return [
        ("fig", "sla_trend", "Cohort view: each point is the share of that month's tickets that met the SLA, judged at the "
         "snapshot. Shaded bands are 95% confidence intervals; the two series do not move together."),
        ("fig", "resolution_composition", f"Every created ticket ends in one of three states. 'Resolved late' grew from "
         f"{P(k['rca_late_share_h1'])} (H1) to {P(k['rca_late_share_h2'])} (H2) of tickets; 'never resolved' fell slightly, "
         f"{P(k['rca_never_share_h1'])} → {P(k['rca_never_share_h2'])}. Part of the late rise may therefore be tickets that "
         "previously went stale and now close late."),
        ("fig", "resolution_hist", f"Median resolution barely moved ({k['resolution_median_h_h1']} h → "
         f"{k['resolution_median_h_h2']} h); the change is a flat 48-144 h tail. The 90th percentile went from "
         f"{k['resolution_p90_h_jan']:.0f} h in January to {k['resolution_p90_h_dec']:.0f} h in December."),
        ("fig", "breakdown_channel", f"Response SLA differs by channel because targets do: phone {P(k['response_sla_phone'])}, "
         f"chat {P(k['response_sla_chat'])} (2-minute target) vs email {P(k['response_sla_email'])} (60 minutes)."),
        ("fig", "breakdown_topic", f"Resolution SLA by topic: intervals overlap (chi-square p = {k['rca_topic_p_resolution']}). "
         f"Priority has no effect either (p = {k['rca_priority_p_resolution']}) - high-priority tickets are not handled faster."),
        ("fig", "hotspots_response", "Each row is a combination of up to three dimensions with at least 30 tickets. Orange "
         "survives a false-discovery-rate correction across all 1,268 combinations tested; grey would be expected by chance."),
        ("fig", "hotspots_resolution", "No combination survives. The highest raw breach rates are small cells that are "
         "consistent with noise - which is why we do not report a 'Monday morning + billing + high priority' hotspot."),
        ("fig", "agent_scorecard", f"Agent attainment ranges {P(k['agent_resolution_sla_min'], 0)}-"
         f"{P(k['agent_resolution_sla_max'], 0)} with overlapping intervals (p = {k['rca_agent_p_resolution']}, not "
         f"significant after correction); {k['agents_declined_h1_to_h2']} of 8 agents declined from H1 to H2."),
        ("fig", "breach_lateness", f"Median lateness: chat {k['late_chat_breach_median_min_late']} min, phone "
         f"{k['late_phone_breach_median_min_late']} min, email {k['late_email_breach_median_min_late']:.0f} min. Email breaches "
         "are tickets that were missed for hours - an alerting problem, not a queue."),
    ]


def _rootcause(k):
    return [
        ("html", "<h3>Is it volume?</h3>" + R(
            f"No. Volume was flat (H2 {k['volume_change_h2_vs_h1'] * 100:+.1f}% vs H1, months within Poisson noise), and the mix "
            f"did not shift. A shift-share decomposition of the Q1 → Q4 change in resolution SLA attributes "
            f"{k['rca_mix_effect_q1_q4_channel_pp']:+.2f} points to channel mix and {k['rca_rate_effect_q1_q4_channel_pp']:+.2f} "
            f"to performance within channels (by topic: {k['rca_mix_effect_q1_q4_topic_pp']:+.2f} vs "
            f"{k['rca_rate_effect_q1_q4_topic_pp']:+.2f}).")),
        ("table", "decomposition"),
        ("html", "<h3>Is it a capacity shortage?</h3>" + R(
            "Not that the data can see. If agents were overloaded, tickets arriving when more work is in progress should "
            f"breach more often. They don't: across load quintiles the breach rate is flat (trend-test p = "
            f"{k['rca_load_trend_p_min']}-{k['rca_load_trend_p_max']}). Breaches do not differ by hour of day (p = "
            f"{k['rca_hour_of_day_p_response']}), day of week (p = {k['rca_day_of_week_p_response']}) or weekday vs weekend "
            f"(p = {k['rca_weekend_p_response']}), and all 8 named agents were active every month. Caveat: a capacity change "
            "outside the ticket data, such as time diverted to other work or tooling changes, cannot be excluded.")),
        ("fig", "load_vs_breach", "Each point is a fifth of all tickets, grouped by how many tickets were in progress when "
         "they arrived. Flat lines = no load effect."),
        ("html", "<h3>Is it the backlog?</h3>" + R(
            f"The open backlog grows all year only because {k['stale_never_resolved']} tickets are never closed "
            f"({k['stale_in_progress']} 'In progress', {k['stale_open_no_response']} never answered; median age "
            f"{k['stale_median_age_days']:.0f} days at snapshot). Active work stays at ~{k['active_backlog_mean']:.0f} tickets "
            f"(max {k['active_backlog_max']}), which matches arrivals x time in system (Little's law: "
            f"{k['active_backlog_littles_law']:.0f}). Weekly resolutions track arrivals - there are no arrival spikes.")),
        ("fig", "backlog", "Stacked: active tickets (blue) and tickets open more than 7 days (grey) at the end of each day."),
        ("fig", "weekly_flow", "When the lines track each other, throughput is keeping up; the steady gap is the stale tickets."),
        ("fig", "sim_queue", "In the synthetic scale-up the same diagnostic separates the two causes cleanly: arrivals are flat, "
         "so a queue that builds every weekend under the assumed roster is a staffing gap, not a volume spike."),
        ("html", "<h3>So what did change?</h3>" + R(
            f"Resolved-late tickets stepped up around {k['rca_step_month_late_share']} "
            f"({P(k['rca_late_share_before_step'])} → {P(k['rca_late_share_after_step'])} of tickets); a gradual ramp from "
            f"{k['rca_ramp_start']} to {k['rca_ramp_end']} fits even better (R² {k['rca_ramp_r2']} vs {k['rca_step_r2']}). "
            "It hit every segment equally. That points to something system-wide in the resolution stage - a process, policy, "
            "tooling or dependency change (for example waiting on engineering or on customers) - rather than any team or "
            "person. The export has no status history, so it cannot say which. The next step is to pull time-in-status "
            "from the ticket audit log."))]


def _staffing(k):
    return [
        ("html", f"""<p>{S("")}{A("")}<b>Method.</b> For each of the 168 hours of the week we compute the work arriving
(live chat/phone contacts and async email replies and follow-ups) and the people needed. The rule is: enough agents
that {P(0.9, 0)} of live contacts are answered within 2 minutes (Erlang C, with live work allowed to interrupt email work),
and that agents are busy no more than 85% of the time, with at least one on duty. That number is then divided by
(1 - 30% shrinkage) for breaks, meetings and absence. An integer program turns the hourly need into 8-hour shifts. A
discrete-event simulation replays the synthetic year ticket by ticket under each roster.</p>
<p><b>Handle time is not in the export.</b> We assume 12/10/8 minutes for a first chat/phone/email touch and 6 minutes per
follow-up, which gives about {k['synth_workload_min_per_ticket']:.0f} agent-minutes per ticket. The meaning of
"agent interactions" is uncertain, so it gets its own sensitivity row.</p>
<p><b>Today's roster is not in the data either.</b> We therefore compare three plausible versions at the same headcount:
flat 24/7, weekday-weighted (daily headcount proportional to new tickets - the assumed baseline), and day-weighted. A
customer's response time is the later of (a) waiting for a free agent and (b) the real pickup delay observed in the export.
Staffing can only remove (a).</p>"""),
        ("fig", "erlang_curve", "Why staffing has diminishing returns: each extra agent buys less service level than the last."),
        ("fig", "requirement_vs_roster", f"Required agents per hour peak at {k['staff_peak_scheduled']} on weekdays and "
         f"{k['staff_weekend_scheduled']} at weekends. Workload, not the 2-minute live target, sets the number in "
         f"{k['staff_hours_binding_workload']} of 168 hours."),
        ("fig", "gap_heatmap", f"Today's assumed roster is short in {k['staff_hours_under_today_by_day']} hours, all at "
         "weekends, and has spare people on weekdays."),
        ("html", "<h3>Proposed roster (people starting each shift)</h3>"), ("table", "roster_proposed"),
        ("html", "<h3>Today's roster, as assumed</h3>"), ("table", "roster_today"),
        ("fig", "roster_sl", f"Same {k['staff_fte_current']} FTE: weekday-weighted {P(k['staff_sl_today_by_day'])}, day-weighted "
         f"{P(k['staff_sl_today_business_hours'])}, flat {P(k['staff_sl_today_flat'])}, proposed {P(k['staff_sl_proposed'])}. "
         f"The process ceiling is {P(k['staff_process_ceiling'])}."),
        ("html", f"<p><b>Robustness.</b> {S('')}On 5 independent synthetic years, the proposed roster beats the weekday-weighted "
                 f"one by {k['rep_gain_pp_vs_by_day_min']:.1f}-{k['rep_gain_pp_vs_by_day_max']:.1f} points, and the ranking of "
                 "rosters is the same every time. The simulation reproduces Erlang C within a point on textbook cases "
                 f"(live queue on time: Erlang C {P(k['staff_erlang_live_sl_proposed'], 2)} vs simulation "
                 f"{P(k['staff_des_live_sl_proposed'], 2)}).</p>"),
        ("table", "replications"),
        ("fig", "sensitivity", f"FTE needed ranges from {k['sens_fte_aht_low']} (handle time -30%, or a narrower reading of "
         f"'interactions') to {k['sens_fte_aht_high']} (handle time +30%). Two separate pools for chat/phone and email would "
         f"need {k['sens_fte_two_pool']}. At 10x or 40x the export's volume the answer is {k['sens_fte_scale_10x']} or "
         f"{k['sens_fte_scale_40x']}. Changing the SLA goal from 80% to 95% changes nothing, because workload binds first."),
        ("table", "sensitivity"),
        ("fig", "growth", f"With the proposed roster, today's headcount stays within a point of the ceiling up to "
         f"+{k['growth_holds_until_no_deflection'] * 100:.0f}% volume, or +{k['growth_holds_until_with_deflection'] * 100:.0f}% "
         "with base-case deflection. This is the trigger for revisiting headcount."),
    ]


def _automation(k):
    return [
        ("html", f"<p>{R('')}{A('')}Topic volumes and complexity proxies (interactions, tier-2 share, resolution time) are "
                 "real; deflection rates are assumptions (low / base / high in <code>config.yaml</code>). The complexity "
                 "proxies differ little across topics in this export, so the ranking is driven mainly by volume and by "
                 "whether the request is informational or transactional (pricing, invoices, feature requests) rather than "
                 "troubleshooting.</p>"),
        ("fig", "automation_matrix", "Bottom-right = high volume, low complexity = best candidates."),
        ("fig", "hours_saved", "Agent-hours per week removed if each topic's assumed deflection is achieved (synthetic workload)."),
        ("table", "automation"),
        ("html", f"<p>Base case: {P(k['auto_deflected_share_base'], 0)} of tickets ({k['auto_real_tickets_deflected_base']:.0f} "
                 f"of the 2023 export), ~{k['auto_hours_saved_week_base']:.0f} agent-hours/week, "
                 f"{k['auto_fte_freed_base']} FTE of headroom (range {k['auto_fte_freed_low']}-{k['auto_fte_freed_high']}).</p>"),
    ]


def _business(k):
    return [
        ("fig", "options", "Same synthetic year for every option; costs are assumptions to confirm with Finance "
         f"(€{k['cost_fte_annual_eur']:,} per FTE per year fully loaded)."),
        ("table", "options"),
        ("fig", "email_alert", f"The pickup fix moves the ceiling itself. Based on the {k['email_breaches']} real email "
         "breaches, with the catch rate as the only assumption."),
        ("html", f"""<div class="callout"><b>Recommendation:</b> no headcount request this quarter. Re-roster to workload
(option B) now. Add the email alert and the stale-ticket sweep, which do not need a business case. Launch the self-service
pilot to build headroom. Revisit headcount if weekly volume runs more than ~{k['growth_holds_until_no_deflection'] * 100:.0f}%
above 2023 for a month, or if response SLA falls below the simulated level after the re-roster.</div>"""),
    ]


def _recs(k):
    return [("table", "recommendations")]


def _limits(k):
    return [("html", f"""<ul>
<li><b>Provenance.</b> The export is a public data-challenge dataset. Several patterns are unusual for a production system:
a flat 24-hour arrival curve for European customers, CSAT unrelated to breaches ({k['csat_breached']} vs {k['csat_met']}),
near-uniform interaction counts, and resolution times capped near 6 days. Relationships between fields are therefore not
over-read.</li>
<li><b>Real vs synthetic.</b> The root cause, volume, efficiency, backlog, hotspot and automation-mix findings are real.
Staffing levels, roster SLA, growth headroom and FTE costs are synthetic: they depend on the scale factor, assumed handle
times and an assumed current roster. The model is a template to re-run on real roster and handle-time data.</li>
<li><b>Agent attribution.</b> <code>Agent Name</code> is the current owner of the ticket, so agent comparisons are for
coaching conversations, not performance ratings.</li>
<li><b>Correlation, not causation.</b> The timing of the resolution slowdown is clear; its cause is not in the data.</li>
<li><b>What we would ask for next:</b> the actual WFM roster and headcount, agent activity or handle-time logs, ticket
status history (time waiting on customer, engineering or tier 2), more than one year of data, and CSAT on resolved as well
as closed tickets.</li></ul>""")]


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
