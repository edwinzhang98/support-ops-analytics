# Assumptions log

**What this is.** Every input the analysis needs that the export does not contain: its value, why it was chosen,
where the code uses it, how far it was stress-tested, and what that does to the answer. Numeric parameters live in
[`config.yaml`](../config.yaml) unless the row names a code constant; modelling choices live in the code named under
"Used in". Change a value and re-run `python run.py` (or `make all`) to regenerate every table, chart and key number.

**Bottom line.**
- **Real-data findings depend on none of the synthetic-model assumptions.** The resolution SLA decline, the root
  cause, flat volume, the hotspot results and the stale backlog use only definitions (A4, A27, A28 below); the 90%
  goal (A3) only sets the reference line.
- **Apart from the volume scenario itself (A1), the FTE requirement is driven by four assumptions:** handle time
  (16–28 FTE for ±30%), pool design (37 FTE with two separate teams), the meaning of "agent interactions" (19 FTE) and
  shrinkage (19–26 FTE). The service-level goal does not matter, because total workload sets the requirement in 158 of
  168 hours; the occupancy cap moves it by at most one FTE.
- **The re-roster result depends on two assumptions:** today's real roster (A21) and weekend follow-up work being
  done when it arises (A13). If weekend follow-ups wait until Monday, the gain swings between −2.1 and +2.3 points,
  so it is not robust. Both must be checked before shifts are moved.

Tags: **[REAL]** = the 2023 export; **[SYNTHETIC]** = the 20× planning year ([04](04_synthetic_data.md));
**[ASSUMPTION]** = this log. Numbers come from `reports/key_numbers.json` or from the named table in `data/processed/`.

---

## The log

### Scenario, definitions and calendar

| ID | Assumption | Value | Source / reason | Used in | Sensitivity tested (range) → effect on the answer |
|---|---|---|---|---|---|
| A1 | Scale factor of the synthetic year | 20× the export: 46,598 tickets, ~128 a day | The export (6.42 tickets a day, under 1 ticket per hour-of-week slot per week) cannot support hourly staffing. 20× gives ~47k tickets a year, a plausible mid-size B2B desk. A scenario parameter, not a fact. | `scenario.scale_factor`; `synth.generate_tickets`; every **[SYNTHETIC]** number | 10× → 13 FTE; 40× → 42 FTE (`staff_sensitivity`, volume factor on the requirement). FTE scales roughly with volume. No real-data finding uses it. |
| A2 | One synthetic year | Calendar 2023 only | One year of data with no trend (H2 vs H1 −2.7%) and no significant monthly seasonality (χ² of monthly counts against each month's weekday mix, p ≈ 0.13, computed from `fct_tickets` for this log). A second year would be invented, not calibrated. | `scenario.year`; `synth.generate_tickets` | Five independent synthetic years (`staff_replications`): re-roster gain +1.5 to +2.0 points (optimistic rule), +1.3 to +1.9 (conservative); roster ranking identical every year. Random-draw noise is small next to the gain. |
| A3 | SLA attainment goal | 90%, for both response and resolution attainment; for staffing, 90% of live contacts answered within 2 minutes | Not in the data: the export has deadlines, not a goal. A common target, adjustable. | `sla.goal_attainment` (goal lines on attainment charts); `staffing.sl_goal` (Erlang C requirement, growth trigger) | Staffing goal 80% / 85% / 95% → 23 FTE in every case (`staff_sensitivity`), because workload binds first (158 of 168 hours). On the real data the goal changes only how far below target attainment reads, not any finding. |
| A4 | Aged-backlog threshold | 7 days | Longer than any resolution observed (maximum 6.12 days), so "aged" isolates tickets that are never resolved. | `sla.aged_backlog_days`; `sql/04`; `rca.stale_backlog`; recommendation 1 (> 7-day policy) | 3 / 5 / 10 / 14 days → mean active backlog 9.5 / 12.7 / 18.5 / 23.0 tickets, vs 15.1 at 7 days (`interactive.backlog_with_threshold`, run for this log). The level moves; the 418 never-resolved tickets and the resolution SLA do not. |
| A5 | Holiday list | 1 Jan, 24 Dec, 25 Dec, 26 Dec and 31 Dec carry zero synthetic volume | The export has zero tickets on these days ([03](03_data_quality_checks.md#holidays-and-zero-ticket-days)). | `synth.HOLIDAYS_2023` (code constant); weekday rates; hourly demand averages | Not tested; 5 of 365 days. Excluding them makes the hourly requirement that of a normal open day. Easter Saturday (8 Apr) and Thursday 27 Apr also had zero tickets but are treated as normal days. |
| A6 | Hourly smoothing | Circular weights [0.25, 0.5, 0.25] on the hour-of-day profile | About 97 real tickets per hour of day, so single-hour shares are noisy. Weekday and hour are independent (χ² p = 0.90), so one pooled profile serves every day. | `scenario.hourly_smoothing_weights`; `synth.hourly_profile` | Not in the pipeline's sensitivity table. Smoothing lowers the busiest hour from 5.8% to 4.8% of daily arrivals. A one-off check while writing this log (unsmoothed profile, same seeds) gave the same 23 FTE. |

### Workload (handle time and follow-ups)

| ID | Assumption | Value | Source / reason | Used in | Sensitivity tested (range) → effect on the answer |
|---|---|---|---|---|---|
| A7 | Handle time, first chat touch | 12 min (mean) | Planning assumption: the export has no handle times. To be replaced with agent-activity or chat-platform logs. | `staffing.handle_time_min.chat_first`; `synth.build_work_items` | A7–A10 are varied together by ±30% (`aht_factor` 0.7 / 1.3 on the requirement, `staffing.sensitivity`): 16 / 28 FTE vs 23; extra FTE needed if today's roster is kept, 0 / 6 vs 2. This is the largest single driver of FTE. |
| A8 | Handle time, first phone touch | 10 min | As A7; telephony logs would replace it. | `staffing.handle_time_min.phone_first` | Varied with A7. |
| A9 | Handle time, first email reply | 8 min | As A7. | `staffing.handle_time_min.email_first` | Varied with A7. |
| A10 | Handle time, follow-up touch | 6 min | As A7. Follow-ups carry 68% of synthetic workload (`synth_work_items`), so this value matters most. | `staffing.handle_time_min.follow_up` | Varied with A7. Together A7–A10 give 29.7 agent-minutes per ticket. |
| A11 | Handle-time variability | Lognormal, coefficient of variation 0.8, mean preserved | Real handle times are right-skewed. Erlang C assumes exponential times (CV 1). | `staffing.handle_time_cv`; `synth._lognormal`. Simulation only; the requirement uses mean handle time. | Not varied. With exponential times the simulator matches Erlang C within 1 point (`tests/test_simulation.py`). With CV 0.8, simulated live queue on-time is 99.9% vs 99.8% from Erlang C for the workload-matched roster, consistent with handle times that vary less than Erlang C assumes. |
| A12 | Meaning of "agent interactions" | Every interaction is one agent touch, so follow-ups = interactions − 1 | The dataset's documented definition ("total number of agent interactions per ticket"). Chat never shows 1 and peaks at 6, which suggests messages inside a session, so alternatives are tested. | `synth.follow_up_touches(semantics="touches")` | Half of the interactions are agent touches (`half_agent`): 19 FTE. Chat interactions are messages inside one session (`chat_in_session`): 19 FTE. Both −4 vs base; extra FTE if today's roster is kept falls from 2 to 0 (`staff_sensitivity`). |
| A13 | Follow-up timing | Uniform between creation + 1 h and resolution (6 days for never-resolved tickets; at least 2 h). Weekend follow-ups are done when they arise. | There is no activity log. The export's resolution clock runs through weekends: weekend resolutions are 80.5% of the weekday rate, against 44.8% for new tickets. | `synth.build_work_items(follow_up_timing="anytime")` | Stress test: weekend follow-ups wait until Monday (`staff_sim_summary_deferred`). The requirement becomes 24 FTE, and the re-roster gain becomes +2.26 points (optimistic) but −2.08 (conservative): **not robust**. Separately, about 18% of follow-up work comes from never-resolved tickets squeezed into 6 days. |

### Staffing rules and rosters

| ID | Assumption | Value | Source / reason | Used in | Sensitivity tested (range) → effect on the answer |
|---|---|---|---|---|---|
| A14 | Max occupancy | 85% of productive time | Common planning cap in contact-centre workforce management: above it queues grow quickly and agents tire. | `staffing.max_occupancy`; requirement; growth trigger | 80% → 23 FTE; 90% → 22 FTE. Small effect. |
| A15 | Shrinkage | 30% of scheduled time unavailable (breaks, meetings, training, absence) | Common planning value; the export has no schedule data. | `staffing.shrinkage`; requirement; simulation | 20% → 19 FTE; 40% → 26 FTE. Extra FTE if today's roster is kept: 1 / 3 vs 2. |
| A16 | Minimum staffing | At least 1 productive agent every hour | 24/7 desk: the export has tickets at every hour. | `staffing.min_agents_per_pool`; requirement | Never binds: the 2-minute live target needs at least 2 productive agents in every hour (`staff_requirement.binding`). No effect. |
| A17 | Shift length and start times | 8-hour shifts. The workload-matched roster may start shifts at 00, 08, 12 or 16; the today's-roster hypotheses use 00 / 08 / 16. | A standard three-shift pattern plus one mid shift. | `staffing.shift_length_h`, `staffing.shift_starts`; `roster.optimize_min_shifts`, `roster.optimize_fixed_budget`, `roster.hypothesis_roster` | Not tested. Shift blocks add 75 agent-hours a week above the hourly need: 837 required agent-hours (`staff_requirement`) vs 912 in the 114-shift minimum roster (recomputed for this log). More start times or shorter shifts could recover part of that, at the cost of a more complex rota. |
| A18 | Shifts per FTE | 5 eight-hour shifts a week (40 h); FTE = ceil(shifts / 5) | A standard full-time week. | `staffing.shifts_per_fte_week`; `roster.fte_from_shifts` | Not tested. Leave and sickness sit inside shrinkage (A15), not in this ratio. A team with many part-timers needs more people for the same FTE. |
| A19 | Blended pool with live preemption | One team handles chat, phone and email. A live contact interrupts email or follow-up work, which resumes afterwards. | Typical for a desk of this size; separate teams need far more people at this volume. | `staffing.requirement(model="blended")`; `simulation.simulate_blended` | Two separate pools (`two_pool`): 37 FTE (+14); extra FTE if today's roster is kept, 14. The largest structural assumption. |
| A20 | How queue wait and pickup delay combine | Optimistic rule: response time = the **later** of the queue wait and the real pickup delay (they overlap) | At the export's volume nobody queues, so real FRT is pickup behaviour. How it combines with a queue is unknown. | `simulation.summarize_response` | The conservative rule (the **sum**) is reported next to it everywhere. Workload-matched roster 84.7% vs 87.6%; re-roster gain +2.1 vs +1.8 points; hire minus re-roster +0.82 vs +0.03 points. The roster ranking holds under both rules in all 5 replications; how much more a hire buys depends on the rule. |
| A21 | Today's roster | Unknown. **Baseline hypothesis: weekday-weighted** (daily headcount proportional to daily new tickets, 3 equal 8-hour shifts). Alternatives: **flat 24/7**, and **day-weighted** (47% of each day's shifts on 08–16). All use the same 115 weekly shifts. | The export contains no roster. | `roster.HYPOTHESES`, `roster.hypothesis_roster`; status quo and hire options (`business_case.options`) | Simulated response SLA, optimistic / conservative: weekday-weighted 85.8% / 82.6%, flat 86.8% / 82.7%, day-weighted 82.7% / 78.0%. Workload-matched gain over each: +1.8 / +0.85 / +4.88 points (optimistic). Hours below requirement: 30 / 17 / 47. Whole hires to close the gaps: 2 / 1 / 3. **The re-roster gain depends on the real roster: check it with WFM first.** |

**Changed since kickoff (A21).** The plan ([00_plan.md](00_plan.md), decision 3) assumed a flat roster with headcount
calibrated to the observed response SLA. A design review showed that calibration would be circular: real response
breaches are pickup failures, not queueing, so a queue model fitted to them invents a staffing gain. The model now
sizes headcount from the requirement and compares three roster hypotheses at equal headcount, with weekday-weighted
as the baseline.

### Costs and levers

| ID | Assumption | Value | Source / reason | Used in | Sensitivity tested (range) → effect on the answer |
|---|---|---|---|---|---|
| A22 | FTE cost | €60,000 per FTE per year, fully loaded | Assumption, to be confirmed with Finance. | `cost.fte_annual_eur`; `business_case.options`; `interactive.costed_options` | Linear. The hire option's annual cost = 1.4 FTE-equivalent × FTE cost (€84,000 at base), so each ±€10,000 on the FTE cost moves it by ±€14,000. No SLA result changes. |
| A23 | Hire one-off cost | €5,000 per hire (recruiting and onboarding) | Assumption. | `cost.hire_one_off_eur` | Linear: 2 whole hires = €10,000 of the hire option's €94,000 first-year cost. |
| A24 | Automation costs | €40,000 one-off (self-service content, portal, routing set-up) + €25,000 a year (licences, content upkeep) | Assumption. | `cost.automation_one_off_eur`, `cost.automation_annual_eur`; options C and B + C | Linear: first-year cost €65,000. Not otherwise tested. |
| A25 | Deflection rates by topic | Low / base / high per topic, e.g. feature requests 25 / 40 / 60%, pricing and licensing 10 / 20 / 30%, bug reports 0 / 0 / 5% (full table in [02 §7.1](02_metric_definitions.md#71-deflection-rate-assumption)) | Assumptions by request type: informational and transactional topics deflect more than troubleshooting. Topic volumes are real. | `automation.topics`; `automation.automation_impact`; options C and B + C | Low / base / high: 10.5% / 19.7% / 30.8% of tickets; 45.5 / 85.7 / 134.7 agent-hours a week; 3 / 4 / 7 FTE of capacity. Treated as capacity to redeploy, not a saving. |
| A26 | Email-alert catch rate | A 45-minute "unanswered email" alert gets 25% / 50% / 75% of would-be email breaches answered within 60 minutes | Assumption; only a pilot can measure it. | `rca.email_alert_lever` → `rca_email_alert` | +1.11 / +2.21 / +3.32 points of response SLA, applied to the 103 real email breaches out of 2,328 evaluable tickets **[REAL × ASSUMPTION]**. Shown as a pilot; never stacked into the headline. |

### Data interpretation

| ID | Assumption | Value | Source / reason | Used in | Sensitivity tested (range) → effect on the answer |
|---|---|---|---|---|---|
| A27 | Snapshot definition | The latest timestamp anywhere in the export: 2024-01-04 05:39 | The export states no extraction date. | `sql/00` → `snapshot_at`; overdue rules for unanswered / unresolved tickets | Any snapshot after 2024-01-01 19:49 (the last resolution deadline) gives identical SLA results; only ticket ages and the backlog end date change. |
| A28 | Agent = current owner | `Agent Name` is the agent currently assigned, not necessarily who did the work | The export has no assignment history. | `sql/05` scorecard; `rca.heterogeneity` | Not testable. Agent comparisons are for coaching conversations only. Agent differences are not significant once multiple testing is considered (p = 0.044, one of 20 tests). |
| A29 | Staffing does not change resolution | Synthetic tickets copy their seed's resolution outcome and time | The real-data tests find no capacity signal in resolution; the slowdown is a process change. | `synth.generate_tickets` | Not tested. In the model no roster or hire moves resolution SLA. That is consistent with the real-data finding, but the model cannot prove it. |
| A30 | Arrival process | Poisson counts per hour, uniform times within the hour; ticket attributes independent of arrival time within a month | Zero-ticket weekend days match the Poisson expectation (3.4 expected, 3 observed); weekday and hour are independent. | `synth.generate_tickets`; Erlang C; simulation | Not varied. The five replications (A2) show the spread from random draws. |
| A31 | Time zone | Timestamps are desk local time | The export has no time zone. | All hour-of-day fields | Not testable. The hourly curve is flat, so a shift of a few hours would change nothing visible. |

---

## Sensitivity summary

### 1. FTE requirement, one assumption at a time (`staff_sensitivity`) **[SYNTHETIC]**

The FTE needed by the cheapest workload-matched roster, and the extra FTE needed if today's assumed weekday-weighted
roster (23 FTE, 115 shifts) is kept and only gaps are filled (`staffing.sensitivity`).

| Assumption | Value tested | FTE (workload-matched roster) | Change vs base | Extra FTE if today's roster is kept | Scheduled agents per hour (min–max) |
|---|---|---:|---:|---:|---:|
| Base case | base | 23 | +0 | 2 | 3–6 |
| Meaning of 'agent interactions' (A12) | half_agent | 19 | −4 | 0 | 3–5 |
| Meaning of 'agent interactions' (A12) | chat_in_session | 19 | −4 | 0 | 3–5 |
| Handle time per touch (A7–A10) | ×0.7 | 16 | −7 | 0 | 2–4 |
| Handle time per touch (A7–A10) | ×1.3 | 28 | +5 | 6 | 4–8 |
| Shrinkage (A15) | 20% | 19 | −4 | 1 | 3–5 |
| Shrinkage (A15) | 40% | 26 | +3 | 3 | 4–7 |
| Max occupancy (A14) | 80% | 23 | +0 | 2 | 3–7 |
| Max occupancy (A14) | 90% | 22 | −1 | 2 | 3–6 |
| Service-level goal, live 2 min (A3) | 80% | 23 | +0 | 2 | 3–6 |
| Service-level goal, live 2 min (A3) | 85% | 23 | +0 | 2 | 3–6 |
| Service-level goal, live 2 min (A3) | 95% | 23 | +0 | 2 | 3–6 |
| Volume / scale factor (A1) | 10× export | 13 | −10 | 0 | 2–3 |
| Volume / scale factor (A1) | 40× export | 42 | +19 | 19 | 6–12 |
| Pool design (A19) | two separate pools (chat/phone vs email) | 37 | +14 | 14 | 6–10 |

Reading: the range across all rows is 13–42 FTE (`sens_fte_min`, `sens_fte_max`). Pure workload maths with no
rounding gives 18.8 FTE (`staff_fte_continuous`). The model therefore says "about 23 for a desk at this volume", not
a precise headcount.

### 2. Roster comparison under the response rule, random draws and weekend timing **[SYNTHETIC]**

Simulated response SLA for the same synthetic year under each roster (`staff_sim_summary`), on five independent
synthetic years (`staff_replications`), and with weekend follow-ups deferred to Monday (`staff_sim_summary_deferred`).
Optimistic rule = later of queue wait and pickup delay; conservative rule = their sum (A20).

| Roster (115 weekly shifts unless stated) | Main run: optimistic | Main run: conservative | 5 replications: optimistic | 5 replications: conservative | Weekend follow-ups deferred: optimistic | Deferred: conservative |
|---|---:|---:|---:|---:|---:|---:|
| Workload-matched (proposed) | 87.6% | 84.7% | 86.9%–87.1% | 83.6%–84.0% | 81.4% | 74.6% |
| Today's roster, weekday-weighted (baseline) | 85.8% | 82.6% | 85.0%–85.6% | 81.9%–82.5% | 79.1% | 76.7% |
| Today's roster, flat 24/7 (alt.) | 86.8% | 82.7% | 85.8%–86.1% | 81.2%–81.8% | 71.2% | 68.9% |
| Today's roster, day-weighted (alt.) | 82.7% | 78.0% | 81.3%–82.8% | 76.1%–77.4% | 78.3% | 73.8% |
| Weekday-weighted + hire (7 extra weekend shifts, 122 in total) | 87.6% | 85.5% | 87.0%–87.3% | 84.9%–85.3% | 87.6% | 86.1% |

- **Process ceiling.** No roster can beat 87.8% (`staff_process_ceiling`), the response SLA with zero queueing given
  real pickup behaviour. The workload-matched roster sits 0.2 points below it under the optimistic rule.
- **Response rule (A20).** The ranking workload-matched > weekday-weighted > day-weighted holds under both rules in
  every replication (`rep_ranking_stable`, `rep_ranking_stable_sum`). Flat 24/7 beats weekday-weighted under the
  optimistic rule. Under the conservative rule the two are level in the main run (82.7% vs 82.6%), and flat is lower
  in all five replications. What a hire buys on top of re-rostering: +0.1 to +0.2 points (optimistic) or +1.1 to +1.4
  (conservative) across the replications.
- **Random draws (A2).** Re-roster gain over the weekday-weighted baseline: +1.5 to +2.0 points (optimistic),
  +1.3 to +1.9 (conservative) across five synthetic years.
- **Weekend timing (A13).** If weekend follow-ups wait until Monday, the desk needs 24 FTE (120 shifts). With the
  deferred work landing on Mondays, email queue on-time falls to 67–88% for the four 120-shift rosters
  (`staff_sim_summary_deferred`), and the re-roster gain becomes +2.26 points (optimistic) or −2.08 (conservative).
  Before moving shifts, check how weekend follow-ups are handled today.

### 3. Growth headroom (`staff_growth`) **[SYNTHETIC]**

The workload-matched 23-FTE roster, with the synthetic year regenerated at higher volume (same seeds). The staffing
goal is met while queue on-time is at least 90% and utilisation at most 85%.

| Volume vs 2023 | No deflection: queue on-time | Utilisation | Response SLA (opt. / cons.) | Base deflection: queue on-time | Utilisation | Response SLA (opt. / cons.) |
|---|---:|---:|---:|---:|---:|---:|
| +0% | 99.8% | 67.4% | 87.6% / 84.7% | 100.0% | 54.2% | 87.9% / 86.8% |
| +5% | 99.6% | 71.5% | 87.0% / 83.1% | 99.9% | 57.5% | 87.4% / 86.1% |
| +10% | 98.7% | 74.7% | 86.1% / 80.7% | 99.9% | 59.9% | 87.4% / 85.7% |
| +15% | 97.7% | 78.4% | 85.0% / 78.7% | 99.9% | 63.1% | 87.2% / 84.9% |
| +20% | 94.1% | 81.9% | 82.1% / 74.6% | 99.8% | 65.8% | 87.4% / 84.7% |
| +25% | 92.2% | 84.7% | 79.9% / 71.1% | 99.7% | 68.1% | 87.0% / 84.0% |
| +30% | 84.9% | 88.5% | 73.3% / 64.1% | 99.6% | 70.9% | 87.2% / 83.3% |
| +40% | 58.9% | 95.2% | 49.3% / 45.9% | 98.6% | 76.9% | 86.3% / 80.3% |
| +50% | 47.5% | 102.2% | 38.8% / 38.6% | 95.6% | 82.0% | 83.6% / 75.3% |

Reading: without deflection the goal holds up to **+25%** volume (`growth_holds_until_no_deflection`). At +30% queue
on-time falls below 90% and utilisation passes 85%. With base-case deflection the goal still holds at **+50%**, the top
of the tested range (`growth_holds_until_with_deflection`). This is the headcount trigger: revisit hiring if weekly
volume runs more than 25% above 2023. Utilisation above 100% at +50% is an overload artefact: the simulation
completes all work eventually (agents finish the item in hand after their shift, and the queue left at the end of the
year is cleared), while the denominator counts only rostered productive hours. In overload it therefore reads as
offered workload ÷ capacity.

### 4. Levers and costs

| Lever | Low | Base | High | Source |
|---|---:|---:|---:|---|
| Deflected share of tickets (A25) | 10.5% | 19.7% | 30.8% | `automation_summary` **[REAL counts × ASSUMPTION]** |
| Agent-hours saved per week (A25) | 45.5 | 85.7 | 134.7 | `automation_summary` **[SYNTHETIC × ASSUMPTION]** |
| FTE of capacity freed (A25) | 3 | 4 | 7 | `automation_summary` **[SYNTHETIC × ASSUMPTION]** |
| Email-alert uplift in response SLA, catch rate 25 / 50 / 75% (A26) | +1.11 pts | +2.21 pts | +3.32 pts | `rca_email_alert` **[REAL × ASSUMPTION]** |

Costs (A22–A24) enter linearly. They change the price of an option, never its simulated SLA. The dashboard re-prices
the options with `interactive.costed_options`.

### 5. What none of these assumptions touch

The **[REAL]** findings are computed on the export with the definitions in
[02_metric_definitions.md](02_metric_definitions.md). They do not depend on the scale factor, handle times, occupancy,
shrinkage, rosters, costs or deflection rates:

- resolution SLA fell from 73.6% (Q1) to 60.6% (Q4) while response SLA did not fall;
- volume was flat (H2 vs H1 −2.7%), and the decline is a rate effect, not a mix effect;
- no segment combination survives the false-discovery check for resolution;
- 418 tickets (17.9%) were never resolved, 53.3% of all resolution breaches.

Only three definitional choices touch them: the snapshot (A27, no effect on any SLA result), the 7-day aged threshold
(A4, changes the active-backlog level only), and reading `Agent Name` as the current owner (A28, limits how agent
results may be used).
