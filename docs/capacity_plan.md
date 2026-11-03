# Capacity plan: next quarter (Q2 2024)

**To:** Support Director, WFM / scheduling, support team leads · **From:** Operations Analyst, Customer Support · **Date:** 2024-01-08
**Scope:** how many agents each hour of the week needs, how to spread them, what that buys, and at what point to revisit headcount.
**Status:** planning scenario, pending three inputs (below). The export runs at about 0.3 tickets per hour, which is too thin for hourly staffing, so the model runs on a 20× synthetic year calibrated to it: 46,598 tickets, about 128 a day **[SYNTHETIC]**. Handle time, shrinkage, occupancy and today's roster shape are **[ASSUMPTION]**s (full log: [assumptions.md](assumptions.md); generation and validation: [04_synthetic_data.md](04_synthetic_data.md)). Every number is from [`reports/key_numbers.json`](../reports/key_numbers.json) or the processed table named in the text.

What this plan can say: how many people a desk like this needs per hour and how to spread them. What it cannot say: whether today's real team is short. Only the real-data tests in [root_cause_analysis.md](root_cause_analysis.md) speak to that, and they show no capacity signal. The 23 FTE below is the size of the scenario desk, not a statement about the real team, whose headcount is not in the data.

## What I need from WFM and ticketing to make this final

| Input | From | Why it matters | Until then |
|---|---|---|---|
| Actual roster (people per shift per day) and headcount | WFM | The re-roster gain depends on where today's people are | Three hypotheses: weekday-weighted (baseline), flat 24/7, day-weighted |
| Handle time per touch, from activity logs | Support tooling | Every FTE figure scales with it: ±30% moves the need from 16 to 28 FTE | 12 / 10 / 8 min for a first chat / phone / email touch, 6 min per follow-up |
| How weekend follow-up work is handled today (when it arises, or on Monday) | Team leads | Decides whether the weekend gap exists | Done when it arises (base); "waits until Monday" run as a stress test |
| Ticket status history | Ticketing admin | Timing of follow-up touches; the resolution slow path | Follow-ups spread over each ticket's life |
| Actual shrinkage (absence, meetings, training) | WFM | 20–40% moves the need from 19 to 26 FTE | 30% |

Once these arrive, the whole pipeline re-runs in about ten seconds (`make all`) and this document's tables update.

## 1. Demand by hour of week [SYNTHETIC]

An average non-holiday week in the scenario (`staff_demand`): about 905 tickets, 419 live contacts (chat and phone first contacts, 2-minute target), 3,496 async items (email first replies plus follow-up touches, 60-minute target) and about 446 agent-hours of handling work — roughly 30 minutes per ticket [ASSUMPTION on handle time].

| Day type | 4-hour band | Tickets per hour | Live contacts per hour | Async items per hour | Handling work (agent-hours per hour) |
|---|---|---|---|---|---|
| Weekday | 00–04 | 6.7 | 3.1 | 22.2 | 2.9 |
| Weekday | 04–08 | 6.4 | 3.0 | 22.8 | 3.0 |
| Weekday | 08–12 | 6.3 | 2.9 | 22.9 | 3.0 |
| Weekday | 12–16 | 6.1 | 2.8 | 22.8 | 2.9 |
| Weekday | 16–20 | 6.6 | 3.1 | 23.3 | 3.0 |
| Weekday | 20–24 | 6.2 | 2.9 | 23.4 | 3.0 |
| Weekend | 00–04 | 3.0 | 1.3 | 17.8 | 2.1 |
| Weekend | 04–08 | 3.0 | 1.4 | 16.5 | 2.0 |
| Weekend | 08–12 | 2.9 | 1.3 | 15.7 | 1.9 |
| Weekend | 12–16 | 2.8 | 1.4 | 15.0 | 1.8 |
| Weekend | 16–20 | 3.0 | 1.5 | 14.5 | 1.8 |
| Weekend | 20–24 | 2.7 | 1.3 | 13.8 | 1.7 |

Tickets per day: Mon 161, Tue 149, Wed 166, Thu 143, Fri 146, Sat 64, Sun 75.

Two things to read off. (1) There is no intraday peak: the export's arrival curve is flat around the clock (a data limitation, unusual for a European B2B desk), so the shape of the *week* is the only lever. (2) Weekend handling work (1.7–2.1 agent-hours per hour) is roughly two-thirds of weekday, although weekend new tickets are only 45% of weekday, because follow-ups on tickets opened in the week keep arriving at the weekend. In the real export, weekend resolutions run at 0.81× the weekday rate while arrivals run at 0.45× [REAL, indicative].

## 2. Requirement method [SYNTHETIC × ASSUMPTION]

For each of the 168 hours of the week, people needed on duty = the largest of:

1. agents for 90% of live contacts to be answered within 2 minutes (Erlang C; live work may interrupt email work, so it sees the whole pool);
2. total handling work ÷ 85% maximum occupancy;
3. one agent (24/7 cover);

grossed up for 30% shrinkage and rounded up once to whole people. Workload (rule 2) sets the number in 158 of 168 hours; the 2-minute live target in 10; the 24/7 minimum in none. Changing the live goal from 80% to 95% changes nothing, because workload binds first.

| Result | Value |
|---|---|
| People on duty per hour | 5–6 on weekdays, 3–5 at weekends (peak 6, minimum 3) |
| Required agent-hours per week | 837 (Mon 124, Tue 129, Wed 144, Thu 133, Fri 130, Sat 95, Sun 82) |
| Cheapest set of 8-hour shifts covering every hour | 114 shifts per week = 22.8 FTE, rounded up to **23 FTE** at 5 shifts per FTE = a 115-shift budget, which the proposed roster spends in full |
| Pure workload maths, no rounding | 18.8 FTE = 750 agent-hours a week. The gap is three roundings: whole people in every hour (→ 837), 8-hour shift blocks (→ 912 = 114 shifts) and whole FTE (→ 920 = 115 shifts); the 24/7 minimum never binds |
| Scheduled agent-hours at 115 shifts | 920 (83 above requirement); simulated utilisation 67% |

## 3. Required vs scheduled, by day and shift block [SYNTHETIC]

People on duty per hour (`staff_coverage`, aggregated to 8-hour blocks; a range means the requirement or the roster changes inside the block). "Today" is the baseline hypothesis: daily headcount set by new-ticket counts, three equal shifts.

| Day | 00–08: required / today / proposed | 08–16: required / today / proposed | 16–24: required / today / proposed |
|---|---|---|---|
| Mon | 5 / 7 / 6 | 5–6 / 7 / 5–6 | 5–6 / 7 / 6–7 |
| Tue | 5–6 / 7 / 6 | 5–6 / 6 / 5–6 | 5–6 / 6 / 6–7 |
| Wed | 6 / 7 / 6 | 6 / 7 / 6 | 6 / 7 / 6 |
| Thu | 5–6 / 6 / 6 | 5–6 / 6 / 6 | 5–6 / 6 / 6 |
| Fri | 5–6 / 6 / 6 | 5–6 / 6 / 6 | 5–6 / 6 / 6 |
| Sat | 4–5 / **3** / 5 | 4 / **3** / 4–5 | 3–4 / **3** / 3–4 |
| Sun | 3–4 / **3** / 4 | 3–4 / **3** / 4 | 3–4 / **3** / 4 |

| Agent-hours per day | Mon | Tue | Wed | Thu | Fri | Sat | Sun | Week |
|---|---|---|---|---|---|---|---|---|
| Required | 124 | 129 | 144 | 133 | 130 | 95 | 82 | 837 |
| Today (assumed weekday-weighted) | 168 | 152 | 168 | 144 | 144 | **72** | **72** | 920 |
| Proposed (workload-matched) | 144 | 144 | 144 | 144 | 144 | 104 | 96 | 920 |

Under the baseline hypothesis the desk is below requirement in **30 of 168 hours, all at weekends** (33 agent-hours short: Saturday 20 hours, Sunday 10), and carries 116 spare agent-hours on weekdays. The proposed roster is below requirement in no hour.

## 4. Today's roster: three hypotheses and their gaps [SYNTHETIC]

No roster data exists, so three plausible versions of today's roster are run with the same 115 shifts per week (`staff_hire_options`, `staff_sim_summary`).

| Hypothesis | Hours below requirement (of 168) | Where | Simulated response SLA, optimistic / conservative rule | Hire needed to close the gaps |
|---|---|---|---|---|
| Weekday-weighted (baseline): daily headcount by new-ticket counts, 3 equal shifts | 30 | All at weekends | 85.8% / 82.6% | 7 shifts = 1.4 FTE (2 whole hires) |
| Flat 24/7: same headcount every shift, every day | 17 | Thursday and Friday, scattered through the day | 86.8% / 82.7% | 5 shifts = 1.0 FTE (1 hire) |
| Day-weighted: 47% of each day's shifts on 08–16 | 47 | Weekend nights and evenings; weekday nights and evenings | 82.7% / 78.0% | 14 shifts = 2.8 FTE (3 hires) |

The kickoff plan ([00_plan.md](00_plan.md)) assumed a flat roster. The final baseline is weekday-weighted because setting daily headcount by ticket counts is the most common way a desk staffs itself without intraday data; flat and day-weighted bracket it. The re-roster gain across the three is +0.8 (flat), +1.8 (weekday-weighted) and +4.9 points (day-weighted) under the optimistic rule, and +2.0, +2.1 and +6.7 under the conservative rule.

## 5. Proposed roster [SYNTHETIC]

People starting each shift (`staff_roster_table_proposed`, `staff_roster_table_by_day`).

| Proposed: workload-matched | Mon | Tue | Wed | Thu | Fri | Sat | Sun |
|---|---|---|---|---|---|---|---|
| 00:00–08:00 | 6 | 6 | 6 | 6 | 6 | 5 | 4 |
| 08:00–16:00 | 5 | 5 | 6 | 6 | 6 | 4 | 4 |
| 12:00–20:00 | 1 | 1 | 0 | 0 | 0 | 1 | 0 |
| 16:00–00:00 | 6 | 6 | 6 | 6 | 6 | 3 | 4 |
| **Total shifts** | **18** | **18** | **18** | **18** | **18** | **13** | **12** |

| Today, as assumed (weekday-weighted) | Mon | Tue | Wed | Thu | Fri | Sat | Sun |
|---|---|---|---|---|---|---|---|
| 00:00–08:00 | 7 | 7 | 7 | 6 | 6 | 3 | 3 |
| 08:00–16:00 | 7 | 6 | 7 | 6 | 6 | 3 | 3 |
| 16:00–00:00 | 7 | 6 | 7 | 6 | 6 | 3 | 3 |
| **Total shifts** | **21** | **19** | **21** | **18** | **18** | **9** | **9** |

What changes versus today's assumed roster:

- **7 shifts a week move from Monday–Wednesday to the weekend** (Mon −3, Tue −1, Wed −3; Sat +4, Sun +3). Same 115 shifts, same 23 FTE, no change in headcount or total hours.
- Weekend cover rises from 3 people on duty in every weekend hour to 3–5; weekday cover falls from 6–7 to 5–7. Thursday and Friday are unchanged.
- Three single-person 12:00–20:00 shifts (Mon, Tue, Sat) are the optimiser's tie-break placing spare capacity where volume is. If a fourth start time is impractical, WFM can fold them into the 08:00 or 16:00 starts and re-run the model to confirm the effect.
- No intraday reshaping is proposed: the data has no intraday peak to follow.

## 6. Expected SLA, simulated [SYNTHETIC]

A customer's response time combines queue wait (which staffing controls) with the real pickup delay observed in the export (which staffing does not). How the two combine is unknown, so every result is shown under two rules: **optimistic** = the later of the two (they overlap); **conservative** = their sum. No roster can beat the **process ceiling of 87.8%**, the response SLA achievable with zero queueing given real pickup behaviour. Every roster replays the same synthetic year ticket by ticket (`staff_sim_summary`).

| Roster | Shifts / week | FTE | Response SLA, optimistic | Response SLA, conservative | Contacts reaching an agent within target |
|---|---|---|---|---|---|
| Today, assumed weekday-weighted | 115 | 23 | 85.8% | 82.6% | 97.9% |
| Today, alternative: flat 24/7 | 115 | 23 | 86.8% | 82.7% | 98.9% |
| Today, alternative: day-weighted | 115 | 23 | 82.7% | 78.0% | 94.6% |
| **Proposed: workload-matched** | 115 | 23 | **87.6%** | **84.7%** | 99.8% |
| Hire instead: today's roster + 7 weekend shifts | 122 | 24.4 (2 whole hires) | 87.6% | 85.5% | 99.9% |

- **Headline (same headcount):** weekday-weighted → workload-matched lifts simulated response SLA from 85.8% to 87.6% under the optimistic rule (+1.8 points) and from 82.6% to 84.7% under the conservative rule (+2.1). The proposed roster all but removes queueing (99.8% of contacts reach an agent within target, against a 90% goal); what remains is the pickup ceiling.
- **Replication.** On five independent synthetic years the proposed roster scores 86.9–87.1% against 85.0–85.6% for the weekday-weighted one (optimistic rule): a gain of +1.5 to +2.0 points (optimistic) and +1.3 to +1.9 (conservative), with the same ranking of rosters every time (`staff_replications`).
- **Base-year draw.** The base synthetic year also happens to draw slightly faster pickups than the export (process ceiling 87.8% vs a real response SLA of 87.2%; the five replications give 87.1–87.3%), so absolute synthetic SLA levels, including the 85.8% → 87.6% headline, are about half a point optimistic. The roster gains (+1.5 to +2.0 points optimistic, +1.3 to +1.9 conservative) are not affected ([04_synthetic_data.md](04_synthetic_data.md#validation-results)).
- **Hiring instead** gets the same result under the optimistic rule (+0.1 to +0.2 points more than re-rostering) and about one point more under the conservative rule (+1.1 to +1.4), for about €94k in year one: €84k a year for 1.4 FTE at €60k, plus €10k one-off for two hires at €5k each; about €130k in year one if costed as two whole full-time hires. Costs to confirm with Finance [ASSUMPTION].
- **Conditions on the gain:** (1) today's roster really is weekday-weighted; (2) weekend follow-up work is done when it arises. **Stress test:** if every weekend follow-up waited until Monday, Mondays would overload under every roster, the desk would need 24 FTE, and the re-roster gain would swing between +2.3 (optimistic) and −2.1 points (conservative) — not robust. About 18% of follow-up work in the model comes from never-resolved tickets compressed into six days, a modelling simplification. Check the real roster and weekend practice before moving shifts.
- The SLA that actually fell in 2023 — resolution — is not moved by any roster.

## 7. Sensitivity [SYNTHETIC × ASSUMPTION]

FTE needed for the workload-matched roster when one assumption changes (`staff_sensitivity`).

| Assumption | Value | FTE needed | Extra FTE if today's roster is kept and gaps are hired |
|---|---|---|---|
| Base case | — | 23 | 2 |
| Meaning of "agent interactions" | half of them are agent touches | 19 | 0 |
| Meaning of "agent interactions" | chat turns within one session | 19 | 0 |
| Handle time per touch | ×0.7 | 16 | 0 |
| Handle time per touch | ×1.3 | 28 | 6 |
| Shrinkage | 20% | 19 | 1 |
| Shrinkage | 40% | 26 | 3 |
| Maximum occupancy | 80% | 23 | 2 |
| Maximum occupancy | 90% | 22 | 2 |
| Live service-level goal (2 min) | 80% / 85% / 95% | 23 | 2 |
| Volume | 10× the export | 13 | 0 |
| Volume | 40× the export | 42 | 19 |
| Pool design | two separate pools (chat/phone vs email) | 37 | 14 |

Handle time is the assumption to pin down first: it moves the answer by ±5–7 FTE. The pool-design row says that keeping chat/phone and email as separate teams would cost 14 FTE of flexibility; a blended pool with live work taking priority is assumed throughout.

## 8. Growth triggers [SYNTHETIC]

The workload-matched roster held fixed while volume grows; "staffing goal" = at least 90% of contacts reach an agent within target and utilisation stays at or below 85% (`staff_growth`).

| Volume vs 2023 | Contacts within target, no deflection | Utilisation, no deflection | Response SLA (optimistic / conservative), no deflection | Contacts within target, base deflection | Utilisation, base deflection | Response SLA (optimistic / conservative), base deflection |
|---|---|---|---|---|---|---|
| +0% | 99.8% | 67% | 87.6% / 84.7% | 100.0% | 54% | 87.9% / 86.8% |
| +5% | 99.6% | 72% | 87.0% / 83.1% | 99.9% | 57% | 87.4% / 86.1% |
| +10% | 98.7% | 75% | 86.1% / 80.7% | 99.9% | 60% | 87.4% / 85.7% |
| +20% | 94.1% | 82% | 82.1% / 74.6% | 99.8% | 66% | 87.4% / 84.7% |
| +25% | 92.2% | 85% | 79.9% / 71.1% | 99.7% | 68% | 87.0% / 84.0% |
| +30% | 84.9% | 89% | 73.3% / 64.1% | 99.6% | 71% | 87.2% / 83.3% |
| +40% | 58.9% | 95% | 49.3% / 45.9% | 98.6% | 77% | 86.3% / 80.3% |
| +50% | 47.5% | 102% | 38.8% / 38.6% | 95.6% | 82% | 83.6% / 75.3% |

The 23-FTE scenario desk meets the staffing goal up to **+25% volume** without deflection; at +30% it fails on both counts. Response SLA slips sooner: it stays within a point of today's level only up to **+5%** (86.1% at +10%, 79.9% at +25%, optimistic rule). The staffing goal holds to +25% while response SLA is already almost 8 points down there, which is why the early warning sits at +5%. With base-case deflection (an assumption: about 20% of tickets), response SLA stays within a point up to +30% and the desk still meets the staffing goal at +50%, the top of the tested range.

**Triggers for revisiting headcount:**

- *Early warning:* weekly volume more than +5% above 2023 for four consecutive weeks (about 48 a week; full weeks in the real export averaged 45 tickets [REAL, computed from `fct_tickets`]) → re-run this model with current inputs.
- *Hard trigger:* weekly volume more than +25% above 2023 for four consecutive weeks (about 57 a week), *or* fewer than 90% of contacts reaching an agent within target, *or* utilisation above 85%, once WFM reports those two → revisit headcount.

## 9. Implementation steps

| Step | What | Owner | When |
|---|---|---|---|
| 1 | Supply the real roster, headcount, shrinkage and weekend follow-up practice; pull handle-time logs | WFM, team leads, support tooling | Weeks 1–2 (by 19 Jan) |
| 2 | Re-run the model on the real inputs; confirm whether the weekend gap exists and how large it is | Ops Analytics | Week 3 |
| 3 | If confirmed, build the Q2 roster: move the gap's worth of shifts (about 6% of weekly shifts; 7 of 115 in the scenario, +4 Saturday, +3 Sunday) from Monday–Wednesday to the weekend; keep 24/7 cover; no headcount change | WFM + team leads | Weeks 4–6, in time for the Q2 roster cycle |
| 4 | Staff the weekend shifts: volunteer pool first (weekend premium or time off in lieu), then a rotation — moving 6% of weekly shifts means one extra weekend shift per person roughly every three weeks, whatever the team size; publish the rota a quarter ahead | Team leads | With step 3 |
| 5 | Monitor by hour of week: response SLA and queue wait, weekend vs weekday response SLA, emails answered within 60 minutes, utilisation; review after four weeks of the new roster | Ops Analytics + team leads | From go-live |
| 6 | Check the growth triggers (section 8) monthly; revisit this plan at the end of Q2 with real roster and handle-time data | Ops Analytics + Support Director | Monthly |

Related documents: [root_cause_analysis.md](root_cause_analysis.md) (why this is not a capacity problem), [headcount_business_case.md](headcount_business_case.md) (costs and options), [../reports/action_plan.md](../reports/action_plan.md) (dated actions).
