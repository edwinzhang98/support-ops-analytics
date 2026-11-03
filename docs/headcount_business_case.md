# Headcount business case: Customer Support, Q2 2024

**To:** VP Customer Experience · **Via:** Support Director · **From:** Operations Analyst, Customer Support · **Date:** 2024-01-08
**Decision requested:** approve **no additional support headcount for Q2 2024**, with defined triggers for revisiting it; approve a re-roster within existing headcount, conditional on WFM confirming today's roster; fund two low-cost pilots; and make the stale-ticket sweep and the resolution-stage investigation the first priorities.

Labels: **[REAL]** 2023 export, 2,330 tickets · **[SYNTHETIC]** 20× planning scenario · **[ASSUMPTION]** input not in the data. Sources: [`reports/key_numbers.json`](../reports/key_numbers.json); evidence in [root_cause_analysis.md](root_cause_analysis.md) and [capacity_plan.md](capacity_plan.md); full report [`reports/report.html`](../reports/report.html).

## 1. The situation [REAL]

The SLA that fell in 2023 is **resolution** (tickets solved on time): 73.5% in Q1 → 60.6% in Q4 (95% CI 56.6–64.5%). **Response** SLA (first reply on time) held at 87.2% and improved in H2 (85.4% → 89.1%). Volume was flat (H2 −2.7% vs H1) and the mix did not move. Breach rates do not rise when the desk is busier, the active backlog stayed flat at about 15 tickets, and the slowdown appears in every channel, priority, topic, tier and agent. The data shows a **process change, not a capacity shortfall**: tickets resolved late rose from 9.8% to 21.8% of all tickets, gradually from March to October, and 418 tickets (17.9%) were never resolved — 53% of all resolution breaches. A capacity change outside the ticket data (time diverted to other work, tooling) cannot be excluded; the roster and time data that would settle it are requested below.

## 2. Options [SYNTHETIC FTE and SLA × ASSUMED costs]

All options start from the same planning scenario: a 23-FTE desk at 20× the export's volume, on an assumed weekday-weighted roster. Response SLA for each option comes from replaying the same synthetic year under that option, shown under two rules because how queue wait and slow pickup combine is unknown: **optimistic** (they overlap) and **conservative** (they add). Costs are assumptions to confirm with Finance: €60k per FTE per year fully loaded; €5k per hire one-off; self-service €40k to build plus €25k a year. Remember that the SLA these options move is *response*, not the one that fell (`business_options`).

| Option | What changes | FTE | One-off | Recurring / year | Year-1 cost | Response SLA, optimistic / conservative | Pros | Cons and risks |
|---|---|---|---|---|---|---|---|---|
| 0. Status quo | Today's roster (assumed weekday-weighted) | 23 | €0 | €0 | €0 | 85.8% / 82.6% | — | Below requirement in 30 of 168 hours, all at weekends, if the roster is weekday-weighted; resolution problem untouched |
| A. Hire | Keep today's roster, add 7 weekend shifts = 1.4 FTE (2 whole hires) | 24.4 | €10k | €84k | **€94k** | 87.6% / 85.5% | Closes the weekend gaps without moving anyone; the most robust option if weekend follow-ups are in fact deferred to Monday (stress test: 87.6% / 86.1% against 81.4% / 74.6% for re-rostering), although the desk then needs 24 FTE and the gap moves to Mondays, so the hire becomes 9 extra Monday shifts = 1.8 FTE rather than 7 weekend shifts = 1.4 | Buys response SLA, not resolution; at most +0.1–0.2 (optimistic) / +1.1–1.4 points (conservative) more than B; the gap it closes is unconfirmed; hiring lead time and ramp-up not modelled; two full-time hires rather than 1.4 FTE would cost about €130k in year one |
| B. Re-roster | Move 7 shifts a week from Mon–Wed to Sat–Sun (workload-matched, near-flat roster) | 23 | €0 | €0 | **€0** | 87.6% / 84.7% | The same simulated result as A under the optimistic rule (about one point less under the conservative rule), for nothing; +1.5 to +2.0 points over the status quo across five simulated years (optimistic; +1.3 to +1.9 conservative); one roster cycle; all but removes queueing (99.8% of contacts reach an agent within target) | Needs weekend rota changes and staff agreement; gain holds only if today's roster is weekday-weighted and weekend follow-ups are done when they arise (stress test: +2.3 points optimistic, −2.1 conservative) |
| C. Automate | Self-service and routing deflect about 20% of tickets; roster unchanged | 23 | €40k | €25k | €65k | 87.7% / 86.3% | Workload −19%; frees about 4 FTE of capacity (range 3–7), worth about €240k a year at the assumed FTE cost; with it the roster still meets its staffing goal at +50% volume, the top of the range tested | Deflection rates are assumptions; weak content sends contacts back to agents; takes a quarter to build |
| B + C | Re-roster now, add deflection over the quarter | 23 | €40k | €25k | €65k | 87.9% / 86.8% | Best SLA of the set; freed capacity goes to the stale sweep and resolution work | Both sets of conditions above; the ceiling differs slightly because deflection changes the ticket population |

Two notes. First, the 45-minute unanswered-email alert is **not** stacked into any option: it is a pilot whose effect depends on an unmeasured catch rate (section 5). Second, no option passes its **process ceiling** (87.8%; 87.9% for the deflection options, whose ticket population differs) set by slow and missed pickups; only the pickup fixes move that ceiling.

## 3. Why not hire now

1. **Hiring would buy the wrong SLA.** In the model, extra people remove weekend queueing and lift *response* SLA by two to three points (+1.8 optimistic, +2.9 conservative). The SLA that fell is *resolution*, and no roster or headcount moves it: the slow tail (90th percentile 46.5 → 104.0 h) and the 418 never-resolved tickets are a process problem [REAL].
2. **The real data shows no capacity signal.** Breach rates are flat across workload levels (trend p 0.28–0.90), there is no bad hour, day or weekend, all 8 agents were active every month, the median resolution time barely moved and the active backlog sits where steady throughput puts it [REAL].
3. **Re-rostering gets the same simulated result as hiring under the optimistic rule, for nothing.** A: 87.6% / 85.5% (optimistic / conservative) for €94k in year one; B: 87.6% / 84.7% for €0. Across five simulated years hiring adds +0.1–0.2 points under the optimistic rule and about one point more (+1.1–1.4) under the conservative rule [SYNTHETIC].
4. **The gap hiring would close is unconfirmed.** It exists only under the assumption that today's roster is weekday-weighted; under a flat roster it is half the size and in different hours. Approving headcount against an assumed roster is not defensible; checking the real roster costs nothing.
5. **The cost of waiting is bounded.** If a headcount trigger below fires, 1–2 hires take one quarter to add; in the meantime, with deflection, the planning roster still meets its staffing goal at +50% volume (the top of the range tested), and the 23-FTE scenario desk runs at 67% simulated utilisation at 2023 volume [SYNTHETIC]. The cost of hiring unnecessarily is €84k a year, recurring (€94k in year one with the one-off costs; about €130k in year one as two whole hires).

## 4. What would trigger a headcount request later

Reviewed monthly. The volume early warning means re-running the capacity model; any one of the hard triggers means a headcount request.

- **Volume, early warning:** weekly tickets more than +5% above 2023 (about 48 a week; full weeks averaged 45) for four consecutive weeks [REAL baseline, computed from `fct_tickets`]: re-run the capacity model, because simulated response SLA slips by more than a point from there (86.1% at +10%, 79.9% at +25%, optimistic rule) [SYNTHETIC].
- **Volume, hard trigger:** more than +25% above 2023 (about 57 a week) for four consecutive weeks. The planning roster still meets its staffing goal at +25% and fails it at +30% [SYNTHETIC]. With base-case deflection, response SLA stays within a point up to +30% and the staffing goal is still met at +50%, the top of the range tested.
- **Queueing:** fewer than 90% of contacts reaching an agent within target, once WFM reports it.
- **Utilisation:** above 85% for a month.
- **Evidence from the requested data:** WFM roster and time logs show a real off-ticket capacity loss, or the status history shows the slow path is a tier-2 queue. In that case the request would be for the specific role, with evidence.

## 5. Process fixes not in the cost table, and recommended first

| Fix | Owner | Evidence [REAL] | Expected effect | Cost |
|---|---|---|---|---|
| Stale-ticket sweep, then a standing policy for tickets open more than 7 days | Support team leads | 418 tickets (17.9%) never resolved; 53% of resolution breaches; median age 202 days | Working the genuine ones fixes customers; closing abandoned ones with an outcome code fixes reporting. Target: never-resolved share below 5% of each month's tickets | Agent time (about 13 tickets per agent per week for four weeks); no spend |
| Find and reverse the resolution slow path that appeared in spring 2023 | Support Director + tier-2 lead, with Ops Analytics | Late share 9.8% → 21.8%; 90th percentile doubled; same in every segment | Returning to the H1 late rate would put on-time resolution near 74% — a target, not a forecast. Needs status-history data; the cause may sit outside support (a release, tooling, a dependency) | Analyst time; data access |
| Pilot a 45-minute "unanswered email" alert | Team leads + support-tooling owner | Email breaches are a median 3.5 h late — missed, not queued; 103 breaches in 2023, 14 never answered | +1.1 / +2.2 / +3.3 points of response SLA if the alert catches 25 / 50 / 75% of them [ASSUMPTION on catch rate]. No SLA credit until the catch rate is measured; only 9.7% of email breaches are near-misses, so alert fatigue is a risk | Configuration only |
| Pilot push routing for chat and phone | Team leads + support-tooling owner | Chat and phone breaches are 2.1 and 1.8 minutes late on a 2-minute target; Phone is the one segment that stands out (24.2% breach rate) | Fewer missed pickups on the live channels | Configuration only |

## 6. Assumptions and their effect on the answer

| Assumption | Value used | Effect if it is wrong (from `staff_sensitivity`, `staff_replications`, `staff_growth`) |
|---|---|---|
| Scale of the planning scenario | 20× the export | 13 FTE at 10×, 42 at 40×; the shape of the conclusions (weekend gap, re-roster first) is unchanged |
| Handle time per touch | 12 / 10 / 8 min first touch, 6 min follow-up | ±30% → 16–28 FTE; the hire option scales with it |
| Meaning of "agent interactions" | each one is an agent touch | Narrower readings → 19 FTE |
| Shrinkage | 30% | 20–40% → 19–26 FTE |
| Maximum occupancy | 85% | 80–90% → 22–23 FTE |
| Live service-level goal | 90% within 2 min | 80–95% → no change (workload binds) |
| Today's roster shape | weekday-weighted | Re-roster gain +0.8 (flat), +1.8 (weekday-weighted), +4.9 points (day-weighted) under the optimistic rule (+2.0 / +2.1 / +6.7 conservative) |
| Weekend follow-up timing | done when it arises | If deferred to Monday: 24 FTE needed; gain +2.3 points (optimistic) but −2.1 (conservative) — not robust |
| Response-time rule | both shown | Levels differ by 1–3 points between rules; the ranking of options does not change |
| FTE cost | €60k fully loaded | Linear: at €70k the hire option is about €108k in year one |
| Self-service cost | €40k build + €25k a year | Linear |
| Deflection rates | base 15–40% by topic (0 for bug reports and Other) | Low case: 10% of tickets, 3 FTE freed; high case: 31%, 7 FTE |
| Email-alert catch rate | 25 / 50 / 75% | +1.1 / +2.2 / +3.3 points; pilot measures it |

## 7. The ask

1. **No headcount request for Q2 2024.** Re-assess at the end of Q2 against the triggers in section 4, with the real roster and handle-time data in hand.
2. **Approve the re-roster in principle**, to be built into the Q2 roster cycle only if WFM confirms today's roster is weekday-weighted and weekend follow-up work is done when it arises. No spend.
3. **Fund the self-service pilot** (about €40k one-off and €25k a year, assumed) for pricing/licensing and invoicing content (plus setup guides and a training catalogue), and route feature requests to the product feedback portal. Treat freed capacity as capacity to redeploy to the stale sweep and resolution work, not as a saving.
4. **Sponsor the stale-ticket sweep and the 7-day policy** (team leads, four weeks) and **the resolution-stage investigation** (status history and the March–October 2023 change log).
5. **Data access:** WFM roster and headcount by month, agent activity logs, ticket status history. These turn the planning scenario into a plan.

Dated actions, owners and the weekly scorecard are in [../reports/action_plan.md](../reports/action_plan.md).
