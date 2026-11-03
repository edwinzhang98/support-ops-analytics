# SLA decline: root cause analysis

**To:** Support Director · **From:** Operations Analyst, Customer Support · **Date:** 2024-01-08
**Data:** 2023 ticket export — 2,330 tickets created 2023-01-02 to 2023-12-30, snapshot 2024-01-04 05:39, 8 named agents **[REAL]**.
**Status:** final for the Q1 planning cycle. Every number comes from [`reports/key_numbers.json`](../reports/key_numbers.json) or from the processed table named in the text. Metric definitions: [02_metric_definitions.md](02_metric_definitions.md). Data checks: [03_data_quality_checks.md](03_data_quality_checks.md). Charts: [`reports/report.html`](../reports/report.html), sections 5–6.

Labels: **[REAL]** computed from the 2023 export · **[SYNTHETIC]** 20× planning scenario · **[ASSUMPTION]** input not in the data.

## Summary

- **The SLA that fell is resolution (solved on time), not response (first reply on time)** [REAL]. On-time resolution went from 73.6% in Q1 to 60.6% in Q4 2023 (95% CI 56.6–64.5%). Response SLA held at 87.2% for the year and improved in H2 (85.4% → 89.1%).
- **The data shows a process change plus a stale backlog, not volume, mix or a capacity shortfall** [REAL]. Volume was flat (H2 −2.7% vs H1); shifts in channel or topic mix explain −0.3 of the −12.9 points; breach rates do not rise when the desk is busier; the slowdown appears in every channel, priority, topic, tier and agent at once. Separately, 418 tickets (17.9%) were never resolved and account for 53% of all resolution breaches. A capacity change outside the ticket data (time diverted, tooling) cannot be excluded.
- **What changed is the slow tail** [REAL]. Tickets resolved late rose from 9.8% to 21.8% of all tickets, gradually from March to October. The median resolution time barely moved (20.3 → 23.4 h) while the 90th percentile doubled (46.5 → 104.0 h). The export has no status history, so the cause — waiting on customers, engineering or tier 2, a tooling or policy change — cannot be identified from this data. The next step is to pull time-in-status from the ticket audit log.

## 1. The decline, quantified [REAL]

*Response SLA attainment* = share of tickets whose first reply came within target (email 60 min; chat and phone 2 min). *Resolution SLA attainment* = share of tickets resolved within target (chat 24 h; email and phone 48 h); a ticket still unresolved and past its deadline at the snapshot counts as a breach. Both are recomputed from timestamps because the export's own flags contradict the timestamps on 14 response and 1 resolution tickets. Intervals are 95% Wilson intervals on the share (source: `kpi_by_dimension`, `kpi_monthly`).

| Quarter (ticket created) | Tickets | Resolution SLA (95% CI) | Response SLA (95% CI) |
|---|---|---|---|
| Q1 2023 | 586 | **73.6%** (69.8–77.0) | 86.3% (83.3–88.9) |
| Q2 2023 | 595 | 67.7% (63.9–71.4) | 84.5% (81.4–87.2) |
| Q3 2023 | 560 | 63.4% (59.3–67.3) | 89.1% (86.3–91.4) |
| Q4 2023 | 589 | **60.6%** (56.6–64.5) | 89.1% (86.4–91.4) |

The Q1 → Q4 change in resolution SLA is −12.9 points; the Q1 and Q4 intervals do not overlap. Monthly, January was 76.3% and December 59.7%. Response SLA moved the other way (H1 85.4% → H2 89.1%). A general loss of capacity would slow both clocks; only one slowed.

**Timing.** The share of each month's tickets that was resolved late fits a gradual ramp from March to October (R² 0.965) better than a single step (R² 0.872; the best single step is at July 2023, with 9.8% before and 21.8% after). We therefore describe the change as a drift that began in spring and had settled by autumn, not as one event.

| Half-year comparison | H1 2023 | H2 2023 |
|---|---|---|
| Tickets | 1,181 | 1,149 |
| Resolved within target | 70.6% | 62.0% |
| Resolved late, as a share of all tickets | 9.8% | 21.8% |
| Never resolved (overdue at snapshot) | 19.6% | 16.3% |
| Median resolution time (resolved tickets) | 20.3 h | 23.4 h |
| Resolved tickets taking more than 48 h | 11.2% | 23.3% |
| 90th-percentile resolution time | 46.5 h (January) | 104.0 h (December) |

## 2. Hypotheses tested

| # | Hypothesis | Verdict | Key evidence |
|---|---|---|---|
| H1 | Volume grew | Rejected | H2 −2.7% vs H1; every month within chance variation |
| H2 | Mix shifted toward harder channels or topics | Rejected | Shift-share: mix −0.3 pts, within-segment rate −12.7 pts |
| H3 | Capacity shortfall / understaffing | Not supported | Breach rate flat across workload levels (trend p 0.28–0.90); no time-slot effect; all 8 agents active every month; active backlog flat at the level Little's law predicts. Caveat: off-ticket capacity changes are not observable |
| H4 | A specific segment, agent or time slot | Not supported | 0 of 1,268 resolution segment combinations significant after a false-discovery correction; agents, priorities, topics within chance |
| H5 | Schedule (roster) mismatch | Not visible at this volume | ~0.3 tickets/hour: no queue forms, so a roster gap cannot show up as breaches. Modelled in the synthetic scenario instead |
| H6 | Stale backlog | Confirmed — a constant drag | 418 never-resolved tickets = 53% of resolution breaches, present in every month |
| H7 | Resolution-stage slow path | Confirmed as the trend; cause not identifiable | Late share 9.8% → 21.8%; p90 doubled; same in every segment |

### H1 — Volume growth: rejected [REAL]

- 1,181 tickets in H1, 1,149 in H2 (−2.7%). Monthly totals ran 159–224; tickets per active day 5.5–7.5 (`kpi_monthly`). Each month sits inside the range expected from random variation around 6.4 tickets/day; no month is an outlier.
- Weekly resolutions track weekly arrivals all year (`kpi_backlog_daily`); there are no arrival spikes.
- The months with the lowest resolution SLA (October–December, 59.7–61.5%) had ordinary volume (176–213 tickets).

### H2 — Mix shift: rejected [REAL]

A shift-share decomposition splits the Q1 → Q4 change into a *mix effect* (segments with worse attainment got more volume) and a *rate effect* (attainment fell inside segments). By channel: mix −0.28 points, rate −12.65 points. By topic: mix +0.10, rate −13.04. Channel shares were stable all year (email 53.0%, chat 36.5%, phone 10.6%; `kpi_channel_mix`). Within every channel attainment fell: chat 72.7% → 55.5%, email 74.3% → 63.3%, phone 72.3% → 67.3% (`kpi_rca_decomposition`). A mix shift cannot produce a decline inside every segment.

### H3 — Capacity shortfall: not supported [REAL]

What a shortfall looks like in ticket data: tickets that arrive when more work is in progress breach more often; busy hours and days are worse; the whole distribution shifts (median up); the active backlog grows; throughput falls behind arrivals. What the data shows:

- **Load at arrival.** Tickets grouped into fifths by the number of tickets already in progress when they arrived: resolution breach rates 34.5%, 32.6%, 32.0%, 35.6%, 33.5% (trend p = 0.90); response 14.6%, 13.9%, 10.3%, 12.0%, 12.9% (p = 0.28). Grouped by same-day volume: p = 0.37 (resolution) and 0.40 (response) (`rca_load_vs_sla`). Across the four trend tests p runs 0.28–0.90: no load effect.
- **Time slots.** Response breaches do not differ by hour of day (p = 0.42), day of week (p = 0.30) or weekday vs weekend (p = 0.77); resolution: p = 0.33 / 0.46 / 0.75. The one lower value, response by 6-hour band (p = 0.08), is the afternoon band being slightly *better* (90.1%), not a bad slot (`rca_time_slots`, `kpi_by_dimension`).
- **Agents.** All 8 named agents handled tickets every month, and 7 of 8 declined from H1 to H2: the decline is shared, not a gap left by someone.
- **Backlog.** Active backlog (open 7 days or less) averaged 15.1 tickets, maximum 26, flat all year. Little's law (arrivals per day × average time a ticket stays active) predicts 15.7. The desk keeps up with arrivals.
- **Distribution.** The median moved 20.3 → 23.4 h. The change is in the tail. A shortfall slows everyone.

Caveat, to be stated with every use of this finding: the export records ticket events, not agent time. A capacity change outside the ticket data — time diverted to projects or training, a tooling change that slowed every touch, higher absence — would not be visible here. The data shows a process change, not a capacity shortfall; it does not prove that capacity was unchanged. The roster and handle-time data in section 4 would settle this.

### H4 — A specific segment, agent or time slot: not supported [REAL]

- **Hotspot search.** 1,268 combinations per SLA of up to three dimensions (day of week, hour band, channel, priority, topic, tier, product group), each with at least 30 tickets, were tested for excess breaches with a Benjamini–Hochberg false-discovery-rate correction at 5% (`kpi_hotspots`).
  - Resolution SLA: **0 of 1,268 survive.** The highest raw breach rates are small cells consistent with chance. We do not report a "Monday + billing + high priority" style hotspot because none exists once multiple testing is accounted for.
  - Response SLA: 5 survive, and all are Phone or a sub-segment of Phone (Phone; Phone + 1st line; Phone + Low priority; Phone + Feature request; Phone + Feature request + 1st line). Phone breaches 24.2% of the time against 12.8% overall, on a 2-minute target. That is one finding, not five.
- **Whole dimensions (chi-square, resolution SLA).** Topic p = 0.50; priority p = 0.29; product group p = 0.11; tier p = 0.10; agent p = 0.044 — the last is not significant once the 12 tests in this family are accounted for, and `Agent Name` is the ticket's current owner, not necessarily who did the work. Agent attainment runs 61.7–76.3% with overlapping intervals (`rca_heterogeneity`, `kpi_agent_scorecard`).
- **Priority** has no effect on outcomes (high 69.5%, low 66.1%, medium 65.0% on-time resolution), and the SLA targets do not depend on it.

### H5 — Schedule mismatch: not visible in the real data at this volume; modelled instead [REAL + SYNTHETIC]

Why it cannot be tested directly: at about 0.3 tickets per hour, most of the 168 hour-of-week cells see 0–1 tickets a week and no queue ever forms. A roster gap produces breaches only when work queues. The real-data checks that could show one are all null: weekend resolution attainment 67.2% (62.2–71.9) vs weekday 66.2% (64.1–68.2); no day-of-week or hour effect (H3).

Two real facts matter for planning: (a) weekend arrivals run at 0.45× the weekday rate, but weekend resolutions at 0.81× — follow-up work is being done at weekends (indicative only: the export's resolution clock ignores the calendar); (b) the hourly arrival curve is flat, which is unusual for a European B2B desk, so the export says nothing about intraday peaks.

In the 20× planning scenario [SYNTHETIC], a roster that sets daily headcount by new-ticket counts is short in 30 of 168 hours, all at weekends, and spreading the same people by workload is worth about +1.8 points of simulated response SLA (+1.5 to +2.0 across five synthetic years; +1.3 to +1.9 under the conservative response rule). That is a planning result about *response* SLA under an assumed roster; it says nothing about the 2023 resolution decline. Full treatment: [capacity_plan.md](capacity_plan.md).

### H6 — Stale backlog: confirmed as a constant drag [REAL]

- 418 tickets (17.9% of all) were never resolved: 400 "In progress" and 18 "Open" (never answered). At the snapshot their median age was 202 days (interquartile range 112–280 days; the youngest 5 days). They are 418 of the 784 resolution breaches (53.3%).
- They come from every month (21–45 created per month), every channel (email 222, chat 148, phone 48 — in proportion to volume), both tiers (323 first line, 95 second line) and every topic (`fct_tickets`). Their share of each month's tickets fell slightly from H1 (19.6%) to H2 (16.3%).
- The open backlog grows all year only because of them: 418 tickets open at the snapshot, 417 of them older than 7 days, while active work stayed at about 15.
- What they are, the data cannot say: abandoned by the customer, waiting on someone, or resolved in another system and never updated. A sweep with an outcome code is both a customer fix and a reporting fix (action 1 in the [action plan](../reports/action_plan.md)).

### H7 — Resolution-stage slow path: confirmed as the trend; cause not identifiable [REAL]

- Tickets resolved late: 116 of 1,181 in H1 (9.8%) → 250 of 1,149 in H2 (21.8%). Resolved tickets taking more than 48 h, by quarter: 9.0%, 13.3%, 21.5%, 25.0%. 90th-percentile resolution time by quarter: 47.1, 68.2, 109.0, 102.7 h; median 21.0, 19.8, 22.8, 24.5 h (`fct_tickets`).
- Resolution times stop at about 6.1 days (146.8 h is the longest in the export), so the late tail is a flat 48–144 h band, not a handful of extreme tickets.
- The rise is in every channel, priority, topic, tier and agent: the rate effect is negative in every segment of the decomposition and 7 of 8 agents declined. It is system-wide.
- Consistent with: a change in the resolution stage — process, policy, tooling, or a dependency such as tickets waiting on engineering, tier 2 or customers — or a reporting change (tickets that would previously have gone stale now being closed late; see the competing-risk note). Not consistent with a team or person problem, nor with demand.
- The export has no status history, so it cannot show where the extra 48–96 hours are spent.

### Response-time breaches are pickup failures, not queueing [REAL]

297 response breaches: chat 135, email 103, phone 59. Median lateness: chat 2.1 min, phone 1.8 min, email 209.8 min (3.5 h). 76.7% of email breaches are more than 60 minutes late and 14 were never answered; only 9.7% are near-misses (60 minutes late or less) (`rca_breach_lateness`). A queue produces minutes of lateness; hours of lateness means the email was not seen. Chat and phone breaches are seconds to a couple of minutes late on a 2-minute target. Both signatures point to alerting and routing, which is why the recommended fixes are a 45-minute unanswered-email alert and push routing for chat/phone — as pilots. Illustration only: catching 25 / 50 / 75% of the 103 email breaches would lift response SLA by 1.1 / 2.2 / 3.3 points; the catch rate is unknown until piloted, so no SLA credit is taken.

### Competing-risk note

"Resolved late" and "never resolved" compete for the same tickets. From H1 to H2, on-time fell 8.6 points (70.6% → 62.0%), late rose 12.0 points (9.8% → 21.8%) and never-resolved fell 3.3 points (19.6% → 16.3%). Part of the late rise may therefore be tickets that previously went stale and now close late — better for the customer, still a breach. If H2 had kept H1's late rate, on-time resolution would have been about 73.9%; that is a target to aim at, not a forecast. Status history would separate the two effects.

## 3. What we cannot tell from this data

- **The cause of the slow path.** No status history, no change log.
- **Whether off-ticket capacity changed.** No roster, headcount or time logs. The real-data tests show no capacity signal in the tickets; they cannot see outside them.
- **Whether the real team is short by hour.** Only the scaled scenario models staffing, and it starts from an assumed roster.
- **Why 418 tickets were never resolved.**
- **Customer impact.** CSAT is unrelated to breaches in this export (3.6 on breached tickets vs 3.5 on met) and is recorded only on closed tickets.
- **Provenance.** The export is a public data-challenge dataset with generator-like patterns (flat 24-hour arrivals, near-uniform interaction counts, a resolution cap near 6.1 days, a calendar-blind resolution clock, uniform on-time response times). We therefore read trends and shares but do not over-read relationships between fields. `Agent Name` is the current owner. One year only.

## 4. Next data to pull

| Data | Owner | What it settles |
|---|---|---|
| Ticket status history / audit log: time in each status (waiting on customer, engineering, tier 2), reassignments | Ticketing admin | Where the extra 48–96 h go (H7); how much of the late rise is ex-stale tickets |
| Change log March–October 2023: releases, tooling, routing rules, policies, team changes | Support Director, Engineering | Candidate causes aligned with the ramp |
| WFM roster and headcount by month, 2023 | WFM | Off-ticket capacity (H3 caveat); the real roster shape for the capacity plan |
| Agent activity / handle-time logs | Support tooling | The handle-time assumption (16–28 FTE range in the planning model) |
| Outcomes of the stale-ticket sweep (50-ticket audit first) | Team leads | What the 418 tickets are |
| CSAT on resolved as well as closed tickets; a second year of data | Support tooling | Customer impact; trend |

## Appendix — methods in plain words, and where they run

- **Wilson 95% interval**: the range in which the true share would sit given the number of tickets; narrower with more tickets. SQL in `sql/`, charts in `src/support_ops/charts.py`.
- **Shift-share decomposition**: splits a change in attainment into "segments changed size" (mix) and "segments got worse" (rate). `sql/`, `kpi_rca_decomposition`.
- **Trend test across workload fifths (Cochran–Armitage)** and **chi-square** across slots and segments: p is the chance of seeing a difference this large if there were none; values above 0.05 are read as "no effect found". `src/support_ops/rca.py`.
- **Benjamini–Hochberg false-discovery rate**: with 1,268 tests, about 63 would pass p < 0.05 by chance alone; the correction keeps only results that survive that many looks. `src/support_ops/kpis.py`, `kpi_hotspots`.
- **Changepoint vs ramp**: the best single-step fit and the best flat–ramp–flat fit to the monthly late share, compared by R². `rca.changepoint`.
- **Little's law**: average items in a system = arrival rate × average time in it; used to check that the active backlog is what steady throughput predicts. `rca.stale_backlog`.
