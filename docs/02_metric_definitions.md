# 02 — Metric definitions

**What this is.** The exact definition of every metric in the report, dashboard and docs: what it means, the formula
(numerator, denominator, inclusion rules, time anchor), the unit, where the code computes it, and its caveats. The
definitions were agreed before the analysis ([00_plan.md](00_plan.md)) and describe what the code in [`sql/`](../sql)
and [`src/support_ops/`](../src/support_ops) actually does. Where the export's own fields disagree with our
definitions, ours are used; section 9 shows each difference and why.

**Source tags.** **[REAL]** = the 2023 export (2,330 tickets). **[SYNTHETIC]** = the 20× scale-up used only for
staffing ([04_synthetic_data.md](04_synthetic_data.md)). **[ASSUMPTION]** = an input that is not in the data
([assumptions.md](assumptions.md)). Sections 1–5 and 8 use only the real export. Section 6 is synthetic plus
assumptions. Section 7 combines real topic counts with assumed deflection rates and synthetic workload. Example values
come from `reports/key_numbers.json`. Where a value comes from a processed table instead, the table in
`data/processed/` is named next to it.

---

## 0. Rules that apply to every metric

| Rule | What it means |
|---|---|
| **Grain** | One row per ticket in `fct_tickets`, built by [`sql/00_fct_tickets.sql`](../sql/00_fct_tickets.sql). No row is dropped or duplicated. Invalid field values are set to NULL in place. |
| **Cohort time anchor** | Attainment, speed and CSAT metrics are cohort metrics. A ticket belongs to the month, quarter, half, weekday and hour of its **created time**. Its outcome is judged **as of the snapshot**. A ticket created on 30 Dec and resolved on 2 Jan counts in December. |
| **Point-in-time metrics** | Backlog and flow metrics count tickets open, created or resolved on each calendar day (section 4). |
| **Clock** | Durations and targets are calendar time (24/7), computed from timestamps. The export has no business-hours clock: a target is 24 h or 48 h whether the ticket arrives on a Friday night or a Tuesday morning. |
| **Time zone** | Timestamps carry no time zone. They are used as given (assumed to be desk local time). |
| **Evaluable** | A ticket enters an SLA denominator only if its outcome is known at the snapshot (rules in 2.3 and 3.3). |
| **Formatting** | SLA percentages to one decimal (87.2%). Differences in percentage points ("pp", "points"). |

## Quick reference

| Metric | Unit | Tag | Computed in (file → column or function) |
|---|---|---|---|
| Ticket | row | REAL | `sql/00` → `fct_tickets` |
| Created time + calendar fields | timestamp, labels | REAL | `sql/00` → `created_at`, `created_month`, `created_dow`, `hour_band`, … |
| Snapshot | timestamp | REAL | `sql/00` → `snapshot_at` |
| First response time (FRT) | minutes | REAL | `sql/00` → `frt_min` |
| Response target | minutes | REAL | `sql/00` → `response_target_min` |
| Response SLA met | TRUE / FALSE / NULL | REAL | `sql/00` → `response_sla_met` |
| Response SLA attainment | % of evaluable tickets | REAL | `sql/01`, `sql/02`, `sql/05` → `response_attainment` |
| Resolution time | hours | REAL | `sql/00` → `resolution_h` |
| Resolution target | hours | REAL | `sql/00` → `resolution_target_h` |
| Resolution SLA met | TRUE / FALSE / NULL | REAL | `sql/00` → `resolution_sla_met` |
| Resolution SLA attainment | % of evaluable tickets | REAL | `sql/01`, `sql/02`, `sql/05` → `resolution_attainment` |
| Resolution outcome class, late share, never-resolved share | class; % of tickets | REAL | `sql/00` → `resolution_outcome`; `rca.resolution_composition`, `rca.recovery_scenario` |
| Volume, arrivals, resolutions, net flow | tickets per day | REAL | `sql/04` → `arrivals`, `resolutions`, `net_flow` |
| Open backlog, active vs aged | tickets | REAL | `sql/04` → `open_total`, `open_active`, `open_aged` |
| Breach rate | % | REAL | `sql/03` → `breach_rate`; `rca.load_vs_sla` |
| Wilson 95% CI | % | REAL | `wilson_lo` / `wilson_hi` macros in `sql/01`–`05`; `rca._wilson` |
| Excess breaches, lift | tickets; ratio | REAL | `sql/03` → `excess_breaches`, `lift` |
| Hotspot p-value, FDR q-value | probability | REAL | `kpis.add_hotspot_significance`, `kpis.benjamini_hochberg` |
| Mix effect, rate effect | attainment points | REAL | `sql/08` → `mix_effect`, `rate_effect` |
| Load at arrival, trend test | tickets; p-value | REAL | `rca.workload_at_creation`, `rca.load_vs_sla`, `rca.cochran_armitage` |
| Handle time per touch / per ticket | minutes | ASSUMPTION | `config.yaml` → `staffing.handle_time_min`; `synth.build_work_items` |
| Work item | row | SYNTHETIC | `synth.build_work_items` → `synth_work_items` |
| Traffic intensity | Erlangs | SYNTHETIC | `staffing.demand_by_how` → `staff_demand.erlangs_*` |
| Service level (Erlang C) | % | SYNTHETIC | `erlang.service_level`, `erlang.required_agents` |
| Occupancy, shrinkage | % | ASSUMPTION (caps), SYNTHETIC (achieved) | `staffing.requirement` → `occupancy_at_requirement` |
| Productive vs scheduled agents | agents per hour | SYNTHETIC | `staffing.requirement` → `productive_required`, `scheduled_required` |
| FTE, weekly shifts | FTE; shifts | SYNTHETIC | `staffing.min_fte_for_requirement`, `roster.fte_from_shifts`, `staffing.continuous_fte` |
| Queue on-time | % | SYNTHETIC | `simulation.summarize_response` → `queue_met`; `staff_sim_summary.queue_sl` |
| Process ceiling | % | SYNTHETIC (from real pickup delays) | `simulation.summarize_response` → `process_met`; `staff_sim_summary.process_sl` |
| End-to-end response, two rules | minutes; % | SYNTHETIC | `simulation.summarize_response` → `response_met`, `response_met_sum` |
| Utilisation | % | SYNTHETIC | `simulation.run_roster` → `staff_sim_summary.utilisation` |
| Deflection rate | % of a topic's tickets | ASSUMPTION | `config.yaml` → `automation.topics` |
| Agent-hours saved, FTE freed | hours per week; FTE | SYNTHETIC × ASSUMPTION | `automation.automation_impact` → `automation_summary` |
| CSAT | score 1–5; % positive | REAL | `sql/00` → `csat_score`, `csat_positive` |

---

## 1. Grain and time anchors **[REAL]**

### 1.1 Ticket
- **Definition.** One row of the export, identified by `Ticket ID`. All statuses are included: Closed (1,173),
  Resolved (739), In progress (400), Open (18) (counts from `fct_tickets`).
- **Rule.** `fct_tickets` keeps all 2,330 rows. Data-quality checks 0–4 confirm that file lines, parsed rows and output
  rows reconcile and that `ticket_id` is unique and never NULL ([03_data_quality_checks.md](03_data_quality_checks.md)).
- **Computed in.** [`sql/00_fct_tickets.sql`](../sql/00_fct_tickets.sql) → `data/processed/fct_tickets.parquet`
  (written by `data.build_fct_tickets`).
- **Caveats.** IDs span 1012–3999, but only 78% of that range is present (check 5). The export may be a subset of all
  tickets, so "volume" means tickets in this export.

### 1.2 Created time and calendar fields
- **Definition.** `created_at` = the export's `Created time`. Every cohort field derives from it.
- **Derived fields (`sql/00`).** `created_date`; `created_month` (first day of the month); `created_quarter` (`Q1`–`Q4`);
  `created_half` (`H1` = Jan–Jun, `H2` = Jul–Dec); `created_dow` (ISO weekday, 1 = Mon … 7 = Sun);
  `created_dow_name` (`Mon` …); `created_hour` (0–23); `hour_band` (`00-06 Night`, `06-12 Morning`,
  `12-18 Afternoon`, `18-24 Evening`); `is_weekend` (Sat or Sun); `channel_group` (`Live (chat/phone)` or
  `Async (email)`).
- **Window [REAL].** First ticket 2023-01-02, last ticket 2023-12-30: 363 calendar days.
- **Caveats.** No time zone. Customers are in 12 European countries, yet the hourly arrival curve is flat
  ([03](03_data_quality_checks.md#provenance-and-generator-like-patterns)), so hour-of-day results should not be over-read.

### 1.3 Snapshot
- **Definition.** The moment the export was taken. The export does not state it, so it is defined as the **latest
  timestamp anywhere in the export**.
- **Formula.** `snapshot_at = greatest(max(Created time), max(First response time), max(Resolution time), max(Close time))`.
  Value **[REAL]**: 2024-01-04 05:39. It is the latest resolution timestamp.
- **Used for.** (a) Deciding whether an unanswered or unresolved ticket is past due (= breach) or not yet due
  (= not evaluable). (b) `age_at_snapshot_days = (snapshot_at − created_at)` in days. (c) The last day of the backlog series.
- **Computed in.** `sql/00`, CTE `snapshot` → column `snapshot_at` (same value on every row).
- **Caveats.** The snapshot is 105.8 h after the last ticket was created (check 8). Every response and resolution
  deadline falls before it; the latest resolution deadline is 2024-01-01 19:49 (from `fct_tickets`). So no ticket is
  "not yet due", and any snapshot after that deadline gives the same SLA results. One thing is right-censored: the
  split between "resolved late" and "never resolved" for tickets created less than 6.1 days (the longest observed
  resolution) before the snapshot. That covers 14 tickets, of which one (ticket 3986) is unresolved.

---

## 2. Response (first reply) **[REAL]**

### 2.1 First response time (FRT)
- **Definition.** Time from ticket creation to the first agent reply.
- **Formula.** `frt_min = (first_response_at − created_at)` in minutes, at millisecond precision. Set to NULL when negative.
- **Inclusion.** NULL for the 18 tickets with no first response (all status Open). NULL for the 2 tickets whose first
  response is logged before creation (`frt_invalid = TRUE`, check 13).
- **Unit.** Minutes. Summaries: `frt_median_min_live`, `frt_median_min_email` and `frt_p90_min_email` in `sql/01`;
  `frt_median_min` in `sql/02`; per-agent medians in `sql/05`.
- **Example [REAL].** Median FRT: email 32.2 min, chat 1.2 min, phone 1.2 min (`kpi_by_dimension`).
- **Caveats.** Medians leave out unanswered tickets, which have no FRT. For SLA questions, use attainment (2.4), which
  counts unanswered tickets as breaches. On-time FRTs are spread evenly across the target window, which is unusual
  ([03](03_data_quality_checks.md#provenance-and-generator-like-patterns)).

### 2.2 Response target
- **Definition.** The maximum FRT allowed for a ticket.
- **Formula.** `response_target_min = (response_due_at − created_at)` in minutes. `response_due_at` is the export's
  `Expected SLA to first response`.
- **Values [REAL].** Email 60 min; Chat 2 min; Phone 2 min. There is one target per channel, and it does not depend
  on priority (checks 17 and 19).
- **Computed in.** `sql/00` → `response_target_min`.
- **Caveats.** The policy is inferred from the deadlines; no policy document exists in the data. The clock is calendar time.

### 2.3 Response SLA met (ticket level)
- **Definition.** Did the first reply arrive by the deadline?
- **Formula** (`sql/00` → `response_sla_met`, first matching rule wins):

  | Condition | Value | Tickets [REAL] |
  |---|---|---|
  | No first response and `response_due_at ≤ snapshot_at` (unanswered and past due) | FALSE (breach) | 18 |
  | No first response and deadline after the snapshot | NULL (not yet evaluable) | 0 |
  | First response before creation (negative FRT) | NULL (excluded) | 2 |
  | Otherwise | `first_response_at ≤ response_due_at` | 2,310 |

  Result: 2,031 met, 297 breached, 2 not evaluable (from `fct_tickets`).
- **Caveats.** The rule compares timestamps directly. That is the same as `frt_min ≤ response_target_min`, because the
  target is defined as deadline minus creation. A reply exactly at the deadline counts as met; there are no such cases.
  The 18 tickets resolved before their logged first response keep the logged response time (check 14).

### 2.4 Response SLA attainment
- **Definition.** The share of evaluable tickets whose first reply met the target.
- **Formula.** `response_attainment = response_met / response_evaluable`, where
  `response_evaluable = count(response_sla_met)` (non-NULL) and `response_met = count_if(response_sla_met)`.
- **Time anchor.** Created month (`sql/01`), segment (`sql/02`: channel, priority, topic, product group, agent group,
  day of week, hour band, day type, quarter, half) or agent (`sql/05`). The 2023 total in `pipeline.key_numbers` is
  `fct["response_sla_met"].mean()`. pandas skips NULL values, so the denominator is the same.
- **Unit.** % of evaluable tickets, with a Wilson 95% CI (`response_attainment_lo`, `response_attainment_hi`).
- **Example [REAL].** 87.2% in 2023 (2,031 of 2,328 evaluable tickets). H1 85.4%, H2 89.1%. By channel: email 91.7%
  (1,131 of 1,234), chat 84.1%, phone 75.8%.
- **Caveats.** It blends a 60-minute target (email) with a 2-minute target (chat/phone), so channel mix moves it. Read it
  by channel too. The raw export flag gives 86.7% (section 9).

---

## 3. Resolution **[REAL]**

### 3.1 Resolution time
- **Definition.** Time from ticket creation to resolution.
- **Formula.** `resolution_h = (resolved_at − created_at)` in hours. `resolved_at` is the export's `Resolution time`,
  not `Close time`. NULL if the ticket is not resolved (418 tickets).
- **Summaries.** `resolution_median_h` = median; `resolution_p90_h` = `quantile_cont(resolution_h, 0.9)`;
  `share_resolved_over_48h` = the share of resolved tickets with `resolution_h > 48`. The 48 h line is the same for
  every channel. All three are in `sql/01`, `sql/02` and `sql/05`, by created cohort.
- **Example [REAL].** Median 20.3 h (H1) → 23.4 h (H2). 90th percentile 46.5 h (January) → 104.0 h (December). Share
  resolved after more than 48 h: 11.2% (H1) → 23.3% (H2).
- **Caveats.** Computed on resolved tickets only. The 418 never-resolved tickets are left out, so true time-to-resolve
  is worse than these numbers. In this export resolution times stop at about 6.1 days (maximum 146.8 h), so the p90
  cannot go higher than that.

### 3.2 Resolution target
- **Formula.** `resolution_target_h = (resolution_due_at − created_at)` in hours. `resolution_due_at` is the export's
  `Expected SLA to resolve`.
- **Values [REAL].** Chat 24 h; Email 48 h; Phone 48 h (check 18). The targets do not depend on priority.
- **Computed in.** `sql/00` → `resolution_target_h`.

### 3.3 Resolution SLA met (ticket level)
- **Formula** (`sql/00` → `resolution_sla_met`, first matching rule wins):

  | Condition | Value | Tickets [REAL] |
  |---|---|---|
  | Not resolved and `resolution_due_at ≤ snapshot_at` (unresolved and past due) | FALSE (breach) | 418 |
  | Not resolved and deadline after the snapshot | NULL (not yet evaluable) | 0 |
  | Otherwise | `resolved_at ≤ resolution_due_at` | 1,912 |

  Result: 1,546 met, 784 breached (366 resolved late + 418 never resolved).

### 3.4 Resolution SLA attainment
- **Formula.** `resolution_attainment = resolution_met / resolution_evaluable` (same pattern as 2.4), with a Wilson CI.
- **Computed in.** `sql/01`, `sql/02`, `sql/05`. Agent H1 vs H2 values: `resolution_attainment_h1`, `_h2` and `_change`
  in `sql/05`.
- **Example [REAL].** 66.4% in 2023 (1,546 of 2,330). Q1 73.5% (95% CI 69.8–77.0%) → Q4 60.6% (56.6–64.5%). January
  76.3% → December 59.7%.
- **Caveats.** Every ticket is past due at the snapshot, so the denominator is all tickets. That makes attainment equal
  to `share_on_time` in `rca_resolution_composition`.

### 3.5 Resolution outcome classes, late share and never-resolved share
- **Ticket-level class** (`sql/00` → `resolution_outcome`):

  | Class | Rule | Tickets [REAL] |
  |---|---|---|
  | Resolved within SLA | resolved and `resolved_at ≤ resolution_due_at` | 1,546 |
  | Resolved late | resolved and `resolved_at > resolution_due_at` | 366 |
  | Unresolved, overdue (called **never resolved** in the docs) | not resolved and deadline ≤ snapshot | 418 |
  | Unresolved, not yet due | not resolved and deadline > snapshot | 0 |

- **Cohort shares** (`rca.resolution_composition` → `rca_resolution_composition`; `rca.recovery_scenario` for H1/H2):
  `share_on_time`, `share_resolved_late` and `share_never_resolved` are each the class count divided by **all tickets**
  created in the period. The three sum to 100%.
- **Late share, the metric used in prose.** Tickets resolved late as a share of all tickets: 9.8% (H1) → 21.8% (H2)
  **[REAL]**. Never-resolved share: 19.6% → 16.3%. On-time share: 70.6% → 62.0%.
- **Breach rate among resolved** (`sql/01` → `breach_rate_among_resolved = resolved_late / resolved`): 8.6% in January,
  28.0% in Q4. It is not used in prose. Its denominator shrinks whenever more tickets go stale, so it mixes two effects.
- **Unresolved share** (`sql/01` → `unresolved_share = unresolved_overdue / tickets`): the monthly never-resolved share.
- **Never-resolved tickets [REAL]** (`rca.stale_backlog`): 418 tickets (17.9% of all tickets), 53.3% of all resolution
  breaches, median age at the snapshot 202 days. Of these, 400 are "In progress" and 18 are "Open" (never answered).
- **Caveats.** The two late outcomes compete. A ticket that would have gone stale in H1 may now close late, so read the
  late share and the never-resolved share together.

---

## 4. Flow and backlog **[REAL]**

### 4.1 Volume, arrivals, resolutions and net flow
- **Formulas** ([`sql/04_backlog_daily.sql`](../sql/04_backlog_daily.sql) → `kpi_backlog_daily`, one row per day from
  2023-01-02 to the snapshot date 2024-01-04, 368 rows):
  - `arrivals(d)` = tickets with `created_date = d`;
  - `resolutions(d)` = tickets with `date(resolved_at) = d`, whatever their creation date;
  - `net_flow(d) = arrivals(d) − resolutions(d)`.
- **Volume.** Tickets per calendar day: 2,330 / 363 = 6.42 in 2023 **[REAL]** (`real_tickets_per_day`). The monthly
  chart (`charts.fig_monthly_volume`) shows tickets / days in the month, with a 95% Poisson interval ±1.96·√n / days.
  `kpi_monthly.tickets_per_active_day` divides by days with at least one ticket instead. The weekly flow chart
  (`charts.fig_weekly_flow`) sums by week and drops the partial first and last weeks.
- **Check.** Over the window, 2,330 arrivals − 1,912 resolutions = +418, exactly the never-resolved tickets.

### 4.2 Open backlog at time t
- **Definition.** A ticket is open at time t if `created_at ≤ t` and (`resolved_at IS NULL` or `resolved_at > t`).
  "Open" ends at resolution, not at close: a resolved ticket waiting to be closed is not backlog.
- **Time anchor.** t = the end of each calendar day (23:59:59.999999).
- **Columns** (age = t − `created_at`, in days): `open_total`; `open_0_2d` (age ≤ 2); `open_2d_to_threshold`
  (2 < age ≤ threshold); `open_aged` (age > threshold); `open_never_resolved` (open at t and never resolved by the
  snapshot); `open_active = open_total − open_aged`.

### 4.3 Active vs aged backlog (7-day threshold)
- **Definition.** Aged = open for more than 7 days (`config.yaml` → `sla.aged_backlog_days: 7`). Active = open for 7 days or less.
- **Why 7 days.** It is longer than any resolution observed (maximum 6.12 days, check 16). In this export, a ticket
  still open after 7 days was never resolved. So "aged" isolates the stale tickets and "active" is genuine work in
  progress. A shorter threshold would put slow but live tickets into "aged". A longer one would count stale tickets as
  active for longer.
- **Example [REAL].** Active backlog: mean 15.1 tickets, maximum 26, flat all year. Aged backlog at the snapshot: 417
  (`kpi_backlog_daily`).
- **Sensitivity.** Mean active backlog at a threshold of 3 / 5 / 7 / 10 / 14 days: 9.5 / 12.7 / 15.1 / 18.5 / 23.0
  tickets (computed for this document with `interactive.backlog_with_threshold`). The level moves with the threshold;
  the 418 never-resolved tickets do not. Re-run with the SQL variable `aged_backlog_days`.

### 4.4 Little's law check on the active backlog
- **Formula** (`rca.stale_backlog` → `active_backlog_littles_law`): expected active backlog L = λ × W, where
  - λ = 2,330 tickets / 363 calendar days = 6.42 per day (`real_tickets_per_day`);
  - W = mean days a ticket counts as active = mean over tickets of `min(resolution_h / 24, 7)` for resolved tickets,
    and 7 for never-resolved tickets = 2.39 days.
- **Result [REAL].** L = 15.4 expected vs 15.1 observed mean. Active work is what steady flow predicts; there is no
  hidden queue.
- **Caveat.** λ uses calendar days. Counting only the 356 days with at least one ticket (λ = 6.54) gives L = 15.7.
  Either way it is close to the observed level.

---

## 5. Statistical measures **[REAL]**

### 5.1 Breach rate
- **Definition.** `breach rate = breaches / evaluable tickets = 1 − attainment`, for one SLA type and one population.
- **Where.** `sql/03` → `breach_rate = breaches / n` per combination. `overall_rate` = the 2023 breach rate of that
  SLA type over all evaluable tickets: 12.8% for response, 33.6% for resolution (= 1 − attainment).
  `rca.load_vs_sla` → `breach_rate` per load quintile. `sql/09` → daily `response_breach_rate` and
  `resolution_breach_rate`. `phone_response_breach_rate` = 24.2% **[REAL]**.
- **Do not confuse with** `breach_rate_among_resolved` (3.5), whose denominator is resolved tickets only.

### 5.2 Wilson 95% confidence interval
- **Formula** (`wilson_lo` / `wilson_hi` SQL macros in `sql/01`, `02`, `03`, `05`; `rca._wilson` in Python):

  ```
  p = x / n,   z = 1.96
  centre     = (p + z²/(2n)) / (1 + z²/n)
  half-width = z · sqrt( p(1 − p)/n + z²/(4n²) ) / (1 + z²/n)
  CI         = centre ± half-width
  ```

- **Applied to.** Every attainment (monthly, by segment, by agent), every hotspot breach rate, every load-quintile breach rate.
- **Why Wilson.** It stays inside 0–100% and remains accurate for small groups (a 30-ticket segment, an agent-month),
  where the usual normal approximation fails.
- **Caveats.** It covers sampling noise only and treats tickets as independent. Overlapping intervals are a quick
  visual check, not a formal test.

### 5.3 Excess breaches and lift
- **Formula** (`sql/03` → `excess_breaches`, `lift`): `excess_breaches = breaches − n × overall_rate`, i.e. breaches
  above what the overall rate predicts for a segment of that size. `lift = breach_rate / overall_rate`.
- **Universe.** Every 1-, 2- and 3-way combination of 7 dimensions: day of week, hour band, channel, priority, topic,
  agent group and product group. Combinations are built with `GROUP BY CUBE` and kept if they have n ≥ 30 evaluable
  tickets. That gives 1,268 combinations per SLA type (30 one-way, 335 two-way, 903 three-way; `kpi_hotspots`).
- **Use.** The hotspot chart ranks by excess breaches, which favours segments that are both large and bad. A tiny
  segment with a high rate cannot top the list.

### 5.4 Hotspot p-value and false-discovery-rate (FDR) q-value
- **p-value** (`kpis.add_hotspot_significance`): one-sided exact binomial test,
  `p = P(X ≥ breaches | n, overall_rate)` (`scipy.stats.binomtest(..., alternative="greater")`).
- **q-value** (`kpis.benjamini_hochberg`, Benjamini–Hochberg, applied separately within each SLA type):

  ```
  sort p ascending: p(1) ≤ … ≤ p(m),   m = 1,268
  q(i) = min over j ≥ i of ( p(j) · m / j ),   capped at 1
  significant_fdr5 = q < 0.05
  ```

  Among the combinations flagged as significant, the expected share of false alarms is at most 5%.
- **Results [REAL].** Response: 5 combinations significant, all Phone (Phone; Phone + 1st line support; Phone + Low
  priority; Phone + Feature request; Phone + Feature request + 1st line support). Resolution: none. The smallest
  resolution q is 0.99 (`kpi_hotspots`).
- **Caveats.** Combinations overlap (Phone + Low priority sits inside Phone), and each is tested against an overall
  rate that includes it, so the p-values are approximate. The FDR step is what stops the scan from reporting noise as
  hotspots.

### 5.5 Mix effect and rate effect (shift-share decomposition)
- **Question.** Did attainment fall because the mix of tickets changed (mix), or because segments got worse (rate)?
- **Formula** ([`sql/08_rca_decomposition.sql`](../sql/08_rca_decomposition.sql) → `kpi_rca_decomposition`). For a
  dimension with segments s, period 1 (earlier) and period 2 (later):

  ```
  w1_s, w2_s = segment share of evaluable tickets in each period (n_s / Σ n)
  a1_s, a2_s = segment attainment in each period
  ΔA      = Σ_s w2_s·a2_s − Σ_s w1_s·a1_s              (total change)
  mix_s   = (w2_s − w1_s) · (a1_s + a2_s) / 2
  rate_s  = (a2_s − a1_s) · (w1_s + w2_s) / 2
  Σ_s mix_s + Σ_s rate_s = ΔA   (exactly)
  ```

- **Scope.** Comparisons H1 → H2 and Q1 → Q4; response and resolution SLA; dimensions channel, topic, priority and
  agent group. The table has one row per segment; sum over a dimension's segments to get the totals.
- **Unit.** Attainment as a fraction in the table. `key_numbers.json` multiplies by 100 to give points.
- **Example [REAL].** Resolution SLA, Q1 → Q4, by channel: mix −0.28 points, rate −12.65 points. By topic: mix +0.10,
  rate −13.04. The decline is a rate effect.
- **Caveats.** It decomposes one dimension at a time. A segment absent from one period would produce NULL; there are none here.

### 5.6 Load at arrival and the trend test (capacity signal)
- **Load measures** (`rca.workload_at_creation`), per ticket:
  - tickets created on the same calendar day;
  - tickets in progress at arrival = tickets created before this one and resolved after its creation. Never-resolved
    tickets are excluded, because nobody is working them.
- **Test** (`rca.load_vs_sla` → `rca_load_vs_sla`). Tickets are ranked by load and split into five equal groups
  (quintiles). Ties are broken by a tiny random jitter (seed 0) rather than by time order. The breach rate per quintile
  gets a Wilson CI. A Cochran–Armitage test (`rca.cochran_armitage`) checks for a linear trend across quintiles:

  ```
  scores s_k = 0..4,  n_k tickets,  x_k breaches
  p̄ = Σx_k / Σn_k,   s̄ = Σ n_k s_k / Σ n_k
  T = Σ x_k (s_k − s̄),   Var(T) = p̄(1 − p̄) Σ n_k (s_k − s̄)²
  two-sided p = 2 · (1 − Φ(|T| / √Var(T)))
  ```

- **Result [REAL].** p = 0.277–0.901 across the 2 load measures × 2 SLA types. There is no workload effect.
- **Why not a daily correlation.** On a low-volume day the breach rate is often 0 by chance, which makes busier days
  look worse even when the risk per ticket is constant. [`sql/09_load_vs_sla.sql`](../sql/09_load_vs_sla.sql)
  (`kpi_load_vs_sla`) keeps the daily view for reference only.

### 5.7 Chi-square tests (segments and time slots)
- **Formula.** A contingency table of segment × (met, not met) on evaluable tickets, tested with
  `scipy.stats.chi2_contingency` (SciPy's default continuity correction applies to 2 × 2 tables).
- **Where.** `rca.heterogeneity` → `rca_heterogeneity` (agent, priority, topic, channel, agent group, product group).
  `rca.time_slot_tests` → `rca_time_slots` (hour of day, day of week, 6-hour band, weekday vs weekend).
- **Examples [REAL].** Priority: p = 0.29 (resolution), 0.363 (response). Agent: p = 0.044 (resolution). Hour of day:
  p = 0.42; day of week: p = 0.299; weekday vs weekend: p = 0.765 (all response).
- **Caveats.** The test detects "some difference", not a direction. It runs 20 tests (12 + 8), so one p-value near
  0.04 is expected by chance. That is why the agent result is not called significant.

### 5.8 Timing of the late-share rise (step and ramp fits)
- **Formula** (`rca.changepoint`, on the monthly `share_resolved_late`). (a) Step: the split month that minimises the
  within-segment sum of squared errors. (b) Flat–ramp–flat: flat at the early mean, a straight line between month a
  and month b, then flat at the late mean, with a and b chosen by least squares. R² = 1 − SSE / SST.
- **Result [REAL].** The best step is at 2023-07 (R² 0.872). The ramp runs from 2023-03 to 2023-10 (R² 0.965). The
  rise was gradual. These fits describe timing only; they do not identify a cause.

---

## 6. Staffing model **[SYNTHETIC + ASSUMPTION]**

Every metric in this section is computed on the synthetic year ([04_synthetic_data.md](04_synthetic_data.md)) using
the assumptions in [`config.yaml`](../config.yaml). Each one describes a desk at 20× the export's volume, never the
real team. Hour of week (`how`) runs from Mon 00:00 = 0 to Sun 23:00 = 167.

### 6.1 Agent interactions (model input)
- **Definition.** `agent_interactions` = the export's `Agent interactions`, documented as "total number of agent
  interactions per ticket". The value 60 is set to NULL (sentinel, 45 chat tickets, check 26). The 18 Open tickets
  have no value. The raw value is kept in `agent_interactions_raw`.
- **Ranges [REAL]** (`fct_tickets`): chat 2–9, email 1–10, phone 1–7.
- **Used in.** Handle time per ticket (6.2); `interactions_avg` in `sql/02` and `sql/05`; the complexity proxy
  `topic_profile.interactions_mean`.

### 6.2 Handle time (AHT) per touch and per ticket **[ASSUMPTION]**
- **Definition.** Agent minutes spent on one touch. It is not in the export. Assumed means
  (`config.yaml` → `staffing.handle_time_min`): first chat touch 12 min, first phone touch 10 min, first email reply
  8 min, each follow-up touch 6 min.
- **Per ticket** (base reading: every interaction is one agent touch):
  `handle_time = first_touch(channel) + 6 × max(agent_interactions − 1, 0)`.
- **Variability.** In the synthetic data each touch is drawn from a lognormal distribution with that mean and a
  coefficient of variation (CV) of 0.8 (`synth._lognormal`): `σ² = ln(1 + CV²)`, `μ = ln(mean) − σ²/2`.
  `build_work_items` also accepts an `aht_multiplier`, which the pipeline leaves at 1.0. The ±30% handle-time
  sensitivity instead scales the pool AHT inside the requirement (`staffing.requirement(..., aht_factor=0.7 / 1.3)`),
  and so does the dashboard's handle-time slider (`interactive.staffing_whatif`).
- **Pool AHT used by Erlang C** (`staff_demand.aht_live_min`, `aht_async_min`): the mean drawn service time of all items
  in that pool over the year. Live: 11.5 min; async: 6.3 min (`staff_demand`).
- **Example [SYNTHETIC].** 29.7 agent-minutes per synthetic ticket on average (`synth_workload_min_per_ticket`).
- **Caveats.** This is the biggest single driver of FTE: handle time ±30% gives 16–28 FTE. The meaning of the
  interactions field is also uncertain. Two narrower readings ("half of the interactions are agent touches";
  "chat interactions are messages inside one live session") each give 19 FTE ([assumptions.md](assumptions.md)).

### 6.3 Work item
- **Definition.** One unit of agent work, with an arrival time (`arrival_s`, seconds from 2023-01-01 00:00) and a
  service time (`service_s`). Built by `synth.build_work_items` → `synth_work_items` (202,172 rows **[SYNTHETIC]**):

  | `kind` | `pool` | Arrives | Count (`synth_work_items`) |
  |---|---|---|---|
  | `live_first` | live | chat/phone first contact, at ticket creation | 21,594 |
  | `email_first` | async | first email reply, at ticket creation | 24,632 |
  | `follow_up` | async | each further touch, uniformly between creation + 1 h and the ticket's resolution (creation + 144 h if never resolved; ticket life at least 2 h) | 155,946 |

- **Inclusion.** Tickets whose seed was never touched (bootstrapped from the 18 Open tickets) create no work. They
  count as response breaches (6.12).

### 6.4 Demand and traffic intensity (Erlangs)
- **Arrival rate** (`staffing.demand_by_how` → `staff_demand`). λ(how, pool) = work items of that pool arriving in that
  hour of the week during 2023 ÷ the number of non-holiday days of that weekday. Arrivals on the five holidays, and
  the few follow-ups that fall in January 2024, are excluded. Output columns: `live_per_hour`, `async_per_hour`, plus
  `tickets_per_hour` for new tickets.
- **Traffic intensity.** `A = λ × AHT / 60`, in Erlangs: the number of agents' worth of work arriving per hour (A = 3.2
  means 3.2 agents busy on average). `erlangs_total = erlangs_live + erlangs_async`.
- **Example [SYNTHETIC]** (`staff_demand`). Mean 2.66 Erlangs per hour, range 1.55–3.36. 446 agent-hours of work per
  week, 82% of it async (email replies and follow-ups).

### 6.5 Service level (Erlang C)
- **Formula** (`erlang.py`):

  ```
  Erlang B (recursive):  B(0) = 1,  B(k) = A·B(k−1) / (k + A·B(k−1))
  P(wait) = C(N, A) = N·B(N) / (N − A·(1 − B(N)))          (1 if N ≤ A)
  SL(N, A, AHT, t) = 1 − C(N, A) · exp(−(N − A) · t / AHT)   (0 if N ≤ A)
  ```

  SL is the share of contacts answered within t minutes when N agents work the queue.
- **Required agents for live contacts** (`erlang.required_agents` → `staff_requirement.agents_live_response`): the
  smallest whole N > A with SL ≥ 90% at t = 2 min. Fractional agents (after shrinkage) are handled by interpolating
  between floor(N) and floor(N) + 1 (`erlang.service_level_fractional`).
- **Model assumptions.** Poisson arrivals, exponential handle times, no abandonment, steady state within each hour,
  first come first served. The simulation (6.10–6.13) relaxes three of these: handle times are lognormal, queues carry
  over from one hour to the next, and live contacts jump ahead of email work.
- **Example [SYNTHETIC].** Live service level at the requirement is at least 96.9% in every hour
  (`staff_requirement.live_sl_at_requirement`).

### 6.6 Occupancy and the occupancy cap
- **Definition.** Occupancy = the share of productive agent time spent handling work = A / productive agents.
- **Cap [ASSUMPTION].** At most 85% (`staffing.max_occupancy`). The workload term of the requirement is
  `A_total / 0.85` productive agents.
- **Achieved at the requirement** (`staff_requirement.occupancy_at_requirement = A_total / (scheduled × (1 − shrinkage))`):
  mean 76%, range 64–85% across the 168 hours.

### 6.7 Shrinkage
- **Definition [ASSUMPTION].** The share of scheduled time not available for tickets (breaks, meetings, training,
  absence): 30% (`staffing.shrinkage`).
- **Use.** `scheduled = ceil(productive / (1 − 0.30))`. In the simulation, productive agents per hour =
  scheduled × 0.7. The fractional part is drawn at random each hour (`simulation.productive_servers`), so availability
  is lumpy but right on average.

### 6.8 Productive vs scheduled agents (hourly requirement)
- **Formula** (`staffing.requirement`, blended model → `staff_requirement`):

  ```
  n_live(h)   = Erlang C agents for live contacts (6.5)            whole number
  n_work(h)   = (A_live(h) + A_async(h)) / 0.85                    fractional
  productive_required(h) = max(n_live, n_work, 1)
  scheduled_required(h)  = ceil(productive_required / (1 − 0.30))  rounded once, after shrinkage
  ```

- **`binding`** names the term that sets the requirement. "Workload / occupancy cap" binds in 158 of 168 hours,
  "live response" in 10, and the 24/7 minimum in none.
- **Example [SYNTHETIC].** 3–6 scheduled agents per hour (`staff_peak_scheduled` 6, `staff_min_scheduled` 3).
- **Caveat.** People are whole, so rounding happens once, at the end. Rounding agents and then people again would
  overstate the requirement.

### 6.9 Weekly shifts and FTE
- **Shift.** 8 hours, starting at 00, 08, 12 or 16 for the workload-matched roster (`staffing.shift_starts`). The
  today's-roster hypotheses use 00 / 08 / 16. Coverage wraps from Sunday night into Monday.
- **Weekly shifts.** The minimum number of shifts such that scheduled agents ≥ `scheduled_required` in all 168 hours.
  This is solved as an integer program (`roster.optimize_min_shifts`, SciPy `milp` / HiGHS). Base case: 114 shifts
  (`staff_min_shifts`), the cheapest cover.
- **FTE.** `FTE = ceil(weekly shifts / 5)` (`roster.fte_from_shifts`; one FTE works 5 shifts = 40 h a week). Base case:
  114 / 5 = 22.8, rounded up to **23 FTE** **[SYNTHETIC]**. The roster budget is FTE × 5 = 115 shifts
  (`staff_weekly_shifts`). The workload-matched roster spreads exactly those 115 shifts to maximise the worst hour's ratio of scheduled to required
  agents, with at most 23 shifts on any day (one per person) and ties broken toward high-volume hours
  (`roster.optimize_fixed_budget`).
- **FTE-equivalent.** Extra shifts / 5, used for costing. Example: 7 extra weekend shifts = 1.4 FTE-equivalent, or 2
  whole hires (`staff_hire_options`).
- **Continuous FTE** (`staffing.continuous_fte`), a lower bound with no rounding:
  `Σ_h A_total(h) / 0.85 / (1 − 0.30) / 40` = 18.8, i.e. 750 agent-hours a week. The gap to 23 FTE comes from three
  roundings (agent-hours per week, from `staff_demand` and `staff_requirement`): whole people in every hour, including
  the 10 hours where the 2-minute live target binds (750 → 837); 8-hour shifts that cannot follow the hourly need
  exactly (→ 912 = 114 shifts); and whole FTE (→ 920 = 115 shifts).
- **Caveat.** This is the requirement of a 20× planning desk. The 23-FTE requirement applies to the 20× planning
  scenario; the real team's headcount is unknown.

### 6.10 Queue on-time ("contacts reaching an agent within target")
- **Definition.** In the simulation, the queue wait of a ticket's first touch is the time from arrival until it first
  reaches an agent. `queue_met = queue_wait_min ≤ response_target_min` (2 min live, 60 min email).
- **Metrics** (`staff_sim_summary`). `queue_sl` = share over all synthetic tickets; never-touched tickets count as met,
  with a wait of 0. `live_queue_sl` and `email_queue_sl` split it by channel group.
- **Analytic counterpart** (`staffing.erlang_check`): `erlang_live_queue_sl` and `erlang_async_queue_sl` apply Erlang C
  hour by hour to a roster, weighted by volume. Async work gets the capacity left over after live work.
- **Example [SYNTHETIC].** 99.8% for the workload-matched roster vs 97.9% for today's roster (assumed weekday-weighted).
- **Used for growth headroom and the hard volume trigger.** The staffing goal is met when `queue_sl` ≥ 90% and utilisation ≤ 85% (6.14).

### 6.11 Process ceiling
- **Definition.** The response SLA achievable with zero queueing, given real pickup behaviour.
- **Formula.** `process_met = pickup_delay_min ≤ response_target_min`. The pickup delay is the real FRT of the real
  ticket that the synthetic ticket was bootstrapped from. Never answered = breach. `process_sl` = share of all
  synthetic tickets.
- **Value.** 87.8% **[SYNTHETIC, built from REAL pickup delays]** (`staff_process_ceiling`). It is the same for every
  roster, because all rosters replay the same tickets. With deflection the ticket population changes, so the ceiling
  shifts slightly (87.9% in options C and B + C).
- **Why.** At the export's volume no queue ever forms. Real FRT therefore measures how quickly agents pick work up
  when they are free, which is process, not staffing.
- **Caveat.** The base synthetic year (seed 42) happens to draw slightly faster pickups than the export: 87.8%
  against a real response SLA of 87.2%. The five independent replications give 87.1–87.3% (`staff_replications`), so
  absolute synthetic SLA levels are about half a point optimistic; roster gains are unaffected
  ([04](04_synthetic_data.md#validation-results)).

### 6.12 End-to-end response time: two rules
- **Optimistic rule** (`response_min`, `response_met`): `response_min = max(pickup delay, queue wait)`; met if
  ≤ target. A ticket is on time only if both the queue and the pickup are within target. This assumes a slow pickup
  and a wait for an agent overlap.
- **Conservative rule** (`response_met_sum`): met if `pickup delay + queue wait ≤ target`. This assumes the two
  delays add up.
- **Metrics.** `response_sl` and `response_sl_sum` = shares over all synthetic tickets (never touched = breach).
- **Example [SYNTHETIC].** The 23-FTE scenario desk: today's roster (assumed weekday-weighted) 85.8% / 82.6% → workload-matched
  87.6% / 84.7% (optimistic / conservative).
- **Caveat.** How the two delays combine is unknown; the truth lies between the two rules, so both are always quoted.
  Because the export's on-time response times are spread evenly up to the target, the sum rule pushes many of them
  just over the line.

### 6.13 Utilisation
- **Formula** (`simulation.run_roster`): total service time of completed work items ÷ total productive agent-hours
  over the simulated horizon (365 + 7 days).
- **Example [SYNTHETIC].** 67.4% for the workload-matched roster.
- **Caveats.** The denominator is productive (post-shrinkage) time. The simulation completes all work eventually: an
  agent whose shift ends finishes the item in hand, and the agents of the last simulated hour keep working until the
  queue is empty. That extra work is in the numerator but not in the denominator. In normal load the effect is
  negligible; in overload utilisation reads as offered workload ÷ capacity and can exceed 100%. It reaches 102% at
  +50% volume without deflection (`staff_growth`).

### 6.14 Growth headroom
- **Definition.** The largest volume increase tested (factors 1.00–1.50) at which the workload-matched roster still
  meets the staffing goal: queue on-time ≥ 90% and utilisation ≤ 85% (`pipeline.key_numbers`, function `holds`, on
  `staff_growth`). Each growth point regenerates the synthetic year at the higher volume with the same random seeds
  (`business_case.simulate_growth`). A second measure, "response SLA within a point" (function `within_1pt`), is the
  largest increase at which simulated response SLA (optimistic rule) stays within 1 point of its no-growth level.
- **Result [SYNTHETIC].** Staffing goal: met up to +25% without deflection (`growth_holds_until_no_deflection`),
  failed at +30% (`growth_staffing_fails_at_no_deflection`). Response SLA slips sooner: it stays within a point of
  today's level only up to +5% (`growth_sl_within_1pt_no_deflection`; 86.1% at +10% and 79.9% at +25% against 87.6%
  at +0%, optimistic rule). With base-case deflection, response SLA stays within a point up to +30%
  (`growth_sl_within_1pt_with_deflection`) and the staffing goal is still met at +50%, the top of the range tested
  (not a limit).
- **Volume triggers built on it.** Baseline: the 2023 mean of full Monday–Sunday weeks, 45.3 tickets
  (`volume_weekly_mean`; full weeks ran 34–63) **[REAL]**. Early warning: weekly volume more than +5% above it (about
  48 a week, `volume_weekly_trigger_early`) for four consecutive weeks → re-run the capacity model. Hard trigger:
  more than +25% (about 57 a week, `volume_weekly_trigger_hard`) for four consecutive weeks → revisit headcount. Once
  WFM reports them, fewer than 90% of contacts reaching an agent within target or utilisation above 85% for a month
  are hard triggers too.

---

## 7. Automation (deflection)

### 7.1 Deflection rate **[ASSUMPTION]**
- **Definition.** The share of a topic's tickets that would be resolved by self-service or routed away from the agent
  queue. Set as low / base / high per topic in `config.yaml` → `automation.topics`:

  | Topic | Low | Base | High |
  |---|---|---|---|
  | Feature request | 25% | 40% | 60% |
  | Training request | 25% | 40% | 60% |
  | Purchasing and invoicing | 15% | 25% | 35% |
  | Pricing and licensing | 10% | 20% | 30% |
  | Product setup | 5% | 15% | 25% |
  | Bug report | 0% | 0% | 5% |
  | Other | 0% | 0% | 5% |

- **Deflected share of tickets** (`automation_summary.deflected_share_of_tickets`): `Σ_topic tickets_2023 × rate /
  2,330`, using real topic counts. Base 19.7% (low 10.5%, high 30.8%) **[REAL counts × ASSUMPTION]**.

### 7.2 Agent-hours saved
- **Formula** (`automation.automation_impact` → `automation_by_topic`, `automation_summary`). Per topic:
  `workload_hours_week = Σ service_s of that topic's synthetic work items / 3600 / (365/7)` and
  `agent_hours_saved_week = workload_hours_week × rate`. Summed over topics. `workload_reduction_share` = hours saved /
  total workload hours.
- **Example [SYNTHETIC × ASSUMPTION].** Base 85.7 agent-hours per week (low 45.5, high 134.7); workload −19.4%.

### 7.3 FTE freed
- **Formula.** `fte_freed = FTE before − FTE after`. The "after" case removes a random `rate` share of each topic's
  synthetic tickets and their work items (seeded), then re-runs the requirement (6.8) and the minimum-shift roster (6.9).
- **Example.** Base 4 FTE (low 3, high 7). It is capacity to redeploy, not a saving.
- **Dashboard what-if.** `interactive.deflection_whatif` approximates the "after" case by scaling every hour's demand
  by (1 − workload reduction). Topics are spread evenly over the week in the synthetic data, so the shortcut is close.
  At the low / base / high rates it gives the same FTE after deflection as the pipeline (20 / 19 / 16; checked for
  this document).

---

## 8. Customer satisfaction (CSAT) **[REAL]**

- **Definition.** `csat_score` = the export's `Survey results`, an integer from 1 to 5.
- **Inclusion.** Present only on Closed tickets: 1,173 responses, and every Closed ticket has one (check 12, `fct_tickets`).
- **Formulas.** `csat_avg = mean(csat_score)`. `csat_positive = csat_score ≥ 4`. `csat_positive_share =
  mean(csat_positive)` over tickets with a score. By created cohort in `sql/01`, `sql/02`, `sql/05`.
- **Example [REAL].** 2023 average 3.51; 56.7% positive (`fct_tickets`). Tickets that breached resolution SLA average
  3.60 vs 3.49 for those that met it (`csat_breached`, `csat_met`).
- **Caveats.** Resolved-but-not-closed and never-resolved tickets have no score, so the survey misses the 418
  never-resolved tickets, where dissatisfaction would be most likely. CSAT shows no relationship to breaches. It is not
  used as an outcome, and the customer cost of breaches is not quantified.

---

## 9. Raw export fields vs our definitions

| Export field | Our field | Difference **[REAL]** | Why ours is used |
|---|---|---|---|
| `SLA For first response` ("Within SLA" / "SLA Violated") | `response_sla_met` | Raw: 2,019 met of 2,330 (86.7%). Ours: 2,031 met of 2,328 evaluable (87.2%). 14 tickets created 18–20 Feb are flagged "Violated" but answered before the deadline. 2 tickets whose response is logged before creation are flagged "Within SLA"; we exclude them. | The timestamps are internally consistent; the flags are not. The raw flags would show a false February dip: 76.1% instead of 84.8% (`fct_tickets`). |
| `SLA For Resolution` | `resolution_sla_met` | Raw: 1,547 met. Ours: 1,546. Ticket 3986 is unresolved and past due at the snapshot but flagged "Within SLA". | Unresolved and past due = breach. The flag was probably set before the deadline passed. |
| `Agent interactions` | `agent_interactions` | 45 values of 60 (all chat) → NULL. | Sentinel value outside the 1–10 range of every other ticket. |
| `Topic` | `topic` | "Pricing and Licensing" (68 rows) merged into "Pricing and licensing". | Same category, different letter case. |
| `Close time` | not used | 42 tickets are closed before their resolution time. | Resolution metrics use `Resolution time`. Close time feeds no metric. |
| `Support Level` (Tier 1 / Tier 2) | `agent_group` used instead | Identical to agent group on every ticket (check 24). | It describes the agent's group, not ticket difficulty. |
| `Latitude`, `Longitude` | dropped | One coordinate pair per country (check 25). | Country centroids add nothing to `country`. |
| `Agent Name` | `agent_name` | None in the data, but it is the **current owner** of the ticket, not necessarily who did the work. | Agent comparisons are for coaching conversations, not performance ratings. |

How each difference was found and what it changes: [03_data_quality_checks.md](03_data_quality_checks.md).
