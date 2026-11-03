# 04 — Synthetic data: the 20× planning year

**Bottom line.** The staffing model runs on one synthetic year of tickets: **46,598 tickets, 20 times the export's
volume**, generated in [`src/support_ops/synth.py`](../src/support_ops/synth.py). Arrival rates come from the export.
Every ticket's attributes, interactions, resolution outcome and first-response delay are copied from a real ticket
created in the same month. Handle times and the timing of follow-up work are assumptions. The synthetic year matches
the export's mix to within 0.51 points and its resolution SLA to within 0.02 points. Its pickups run about half a
point faster than the export's (process ceiling 87.8% vs a real response SLA of 87.2%, a favourable draw), so
absolute synthetic SLA levels are slightly optimistic; comparisons between rosters are not affected. It is used
**only** for hourly staffing, roster comparison, simulation, growth headroom and FTE/cost maths. Every finding about
what happened in 2023 comes from the real export.

Tags: **[REAL]** = the export, **[SYNTHETIC]** = generated, **[ASSUMPTION]** = an input not in the data
([assumptions.md](assumptions.md)). Numbers come from `reports/key_numbers.json` or from the named table in
`data/processed/`.

---

## Why a scale-up is needed

- The export averages 6.42 tickets per calendar day **[REAL]**, about 0.27 per hour. Every one of the 168
  hour-of-week slots averages less than one ticket a week; the busiest averages 0.52 (`kpi_volume_heatmap`).
- At that volume no queue ever forms, so real response times measure how quickly agents pick tickets up, not how long
  tickets wait for a free agent. Erlang C and a queue simulation need a stable arrival rate in every hour.
- At 20× the volume, each hour of the week receives 2.2–8.0 new tickets on average (`staff_demand`) **[SYNTHETIC]**.
  That is enough for interval staffing, and it is a plausible mid-size B2B desk (about 47k tickets a year). The scale
  factor is a scenario parameter, not a fact (`config.yaml` → `scenario.scale_factor`; tested at 10× and 40×).

## What is produced

| Table (`data/processed/`) | Rows | Content |
|---|---:|---|
| `synth_tickets` | 46,598 | One row per synthetic ticket: `ticket_id` (100001 …), `seed_ticket_id` (the real ticket it copies), creation time, copied attributes, `pickup_delay_min`, `resolved_at`, `resolution_sla_met`. |
| `synth_work_items` | 202,172 | One row per unit of agent work: `kind` (`live_first`, `email_first`, `follow_up`), `pool` (live / async), `arrival_s` and `service_s` (seconds; arrival counted from 2023-01-01 00:00), plus pickup delay and target for first touches. |
| `synth_fct_tickets` | 46,598 | The synthetic tickets in the `fct_tickets` column layout, so the same KPI SQL can run on them (validation only). |
| `kpi_monthly_synth`, `kpi_by_dimension_synth`, `kpi_volume_heatmap_synth` | 12, 38, 168 | `sql/01`, `sql/02` and `sql/06` run on `synth_fct_tickets`. |

---

## Generation, step by step

### Step 1 — Calibrate from the export (`synth.calibration_summary`)

**Arrival rate by weekday** (`synth.daily_rate_by_weekday`). Average tickets per day for each ISO weekday, over the
export window 2023-01-02 to 2023-12-30. Holidays are excluded from the average; days with zero tickets that are not
holidays count as 0. Values **[REAL]** (computed from `fct_tickets` with the same function):

| Mon | Tue | Wed | Thu | Fri | Sat | Sun |
|---:|---:|---:|---:|---:|---:|---:|
| 8.04 | 7.39 | 8.44 | 7.10 | 7.38 | 3.17 | 3.72 |

That is 7.67 tickets per weekday and 3.45 per weekend day on average (`real_weekday_tickets_per_day`,
`real_weekend_tickets_per_day`).

**Hour-of-day profile** (`synth.hourly_profile`). Ticket counts by `created_hour`, pooled over all days, are smoothed
circularly with weights `[0.25, 0.5, 0.25]` (`config.yaml` → `scenario.hourly_smoothing_weights`) and normalised to
sum to 1.
- Why pool over weekdays: the weekday × hour pattern of the export is independent (χ² p = 0.90), so one profile
  serves every day.
- Why smooth: each hour of the day holds only about 97 real tickets, so single-hour shares are noisy. The smoothing
  narrows the raw range of 3.1–5.8% per hour to 3.5–4.8% (a flat curve gives 4.17%).

**Holidays** (`synth.HOLIDAYS_2023`): 1 Jan, 24 Dec, 25 Dec, 26 Dec, 31 Dec. The export has zero tickets on these
days ([03](03_data_quality_checks.md#holidays-and-zero-ticket-days)). The synthetic year gives them zero volume too.

### Step 2 — Arrivals: a non-homogeneous Poisson process (`synth.generate_tickets`, part 1)

For each of the 8,760 hours h of calendar 2023:

```
λ_h = scale_factor × rate(weekday of h) × share(hour of h)     (λ_h = 0 on the five holidays)
N_h ~ Poisson(λ_h)                                              new tickets in hour h
created_at = start of hour h + Uniform(0, 3,600 s)              one draw per ticket, then sorted
```

With `scale_factor = 20` the expected total is 46,600 (20 × the export's 2,330). The draw gives 46,598 tickets, 127.7
a day **[SYNTHETIC]**. There is no month-level seasonality: each month's volume follows its number of each weekday
and its holidays, because the export shows no trend or seasonality that could be calibrated.

### Step 3 — Ticket attributes: a month-level bootstrap (`synth.generate_tickets`, part 2)

Each synthetic ticket copies one real ticket, drawn uniformly at random (with replacement) from the real tickets
created in the **same calendar month**. Copied fields: `channel`, `priority`, `topic`, `product_group`,
`agent_group`, `support_level`, `country`, `agent_interactions`, `resolution_outcome`, `resolution_h`, `frt_min`,
`csat_score`, `response_target_min`, `resolution_target_h`. The seed's `ticket_id` is kept as `seed_ticket_id`. Every
real ticket was drawn between 7 and 38 times (20 on average; `synth_tickets`).

- **Why copy whole tickets.** It keeps the real joint mix. Channel, topic, priority and tier come together from one
  real ticket, so no correlation is invented or lost.
- **Why the same month.** It keeps the real month-by-month resolution trend. The resolution slowdown of 2023 is
  carried by the seeds; it is not modelled.
- **Not copied.** `agent_name`, status and close time. Arrival times within a month are independent of attributes,
  so topics and channels are spread evenly over the week and the day.

### Step 4 — Repair seed fields that are invalid in the export

| Seed problem ([03](03_data_quality_checks.md)) | Seeds affected **[REAL]** | Repair |
|---|---|---|
| Interactions = 60 (sentinel, set to NULL) | 45 chat tickets | Draw a valid interaction count at random from real tickets of the same channel. |
| Never touched: no first response | 18 Open tickets | Interactions set to 0. The ticket creates no work and counts as a response breach (pickup delay missing). |
| First response logged before creation | 2 phone tickets | Draw a valid first-response time at random from real phone tickets. |

### Step 5 — Derived fields (`synth.generate_tickets`, part 3)

| Field | Rule |
|---|---|
| `pickup_delay_min` | The seed's first-response time (`frt_min`); missing = never answered. At the export's volume nobody queues, so this measures how fast agents pick work up: the **process** component of response time. |
| `resolved_at` | `created_at + resolution_h` when the seed's outcome is "Resolved within SLA" or "Resolved late"; otherwise missing (never resolved). |
| `resolution_sla_met` | The seed's outcome = "Resolved within SLA". Resolution is copied, not simulated: no roster changes it. |
| `ticket_id` | 100001, 100002, … in creation order. |
| Calendar fields | `created_date`, `created_month`, `created_dow` (1 = Mon), `created_hour`, `channel_group`. |

### Step 6 — Work items: the agent workload each ticket creates (`synth.build_work_items`)

Only touched tickets (interactions > 0) create work.

| Item | Pool | Arrival | Mean handle time **[ASSUMPTION]** |
|---|---|---|---|
| First touch, chat / phone (`live_first`) | live | at ticket creation (the customer is waiting) | 12 min chat, 10 min phone |
| First reply, email (`email_first`) | async | at ticket creation | 8 min |
| Follow-up touch (`follow_up`) | async | uniform between creation + 1 h and the end of the ticket's life | 6 min |

- **Number of follow-ups** (`synth.follow_up_touches`). Base reading `touches`: interactions − 1. Sensitivity
  readings: `half_agent`, ceil(interactions / 2) − 1 (half the interactions are the customer's); `chat_in_session`,
  0 for chat (interactions are messages inside one live session) and interactions − 1 otherwise. All are floored at 0.
- **Ticket life.** The seed's `resolution_h` for resolved tickets; 144 h (6 days) for never-resolved tickets; at least 2 h.
- **Weekend timing.** In the base case (`follow_up_timing="anytime"`), follow-up work is done when it arises,
  weekends included. Stress test `"weekdays"`: follow-ups landing on a Saturday move 2 days and on a Sunday 1 day, to
  Monday at the same time of day.
- **Handle time draws.** Each item's handle time = mean × a lognormal draw with mean 1 and coefficient of variation
  0.8 (`synth._lognormal`) × `aht_multiplier`. The pipeline leaves `aht_multiplier` at 1.0; its ±30% handle-time
  sensitivity scales AHT inside the staffing requirement instead (`aht_factor`, [assumptions.md](assumptions.md) A7).
- **Result [SYNTHETIC]** (`synth_work_items`). 202,172 items: 21,594 live first touches, 24,632 email first replies and
  155,946 follow-ups. On average that is 29.7 agent-minutes per ticket (`synth_workload_min_per_ticket`).
  Follow-ups carry 68% of the workload, live first touches 18% and email first replies 14%.
- **Simplifications.** Never-resolved tickets have no end date, so their follow-ups are squeezed into 6 days. They
  supply 17.9% of follow-up items, 12% of all workload. A ticket resolved in under 2 hours can receive follow-ups up to
  2 hours after creation, slightly after its recorded resolution.

### Step 7 — Validation view (`pipeline.synth_fct_view`)

`synth_fct_tickets` puts the synthetic tickets into the `fct_tickets` layout. `frt_min` and `response_sla_met` are
the simulated response under today's assumed (weekday-weighted) roster, optimistic rule. Interactions of 0 become NULL
(as for real Open tickets). The pipeline then runs `sql/01`, `sql/02` and `sql/06` on it unchanged, so real and
synthetic KPIs come from identical code.

---

## What is calibrated and what is assumed

| Element | Taken from the export **[REAL]** | Assumed **[ASSUMPTION]** |
|---|---|---|
| Daily volume | 7 weekday rates | × 20 scale factor |
| Hour-of-day shape | pooled hourly shares | 3-hour circular smoothing |
| Holidays | zero-ticket days 1 Jan, 24–26 Dec, 31 Dec | that these, and only these, are holidays |
| Arrival process | — | Poisson counts per hour; uniform times within the hour; attributes independent of time within a month |
| Channel, priority, topic, product, tier, country | joint bootstrap within the month | — |
| Interactions per ticket | bootstrapped; invalid values redrawn within the channel | what an interaction means (one agent touch) |
| Resolution outcome and time | bootstrapped, including the 2023 trend | that staffing does not change resolution |
| First-response delay | bootstrapped real FRT | that it is pickup behaviour, and how it combines with queue wait (two rules) |
| CSAT | bootstrapped | not used by the staffing model |
| Handle time per touch | — | 12 / 10 / 8 / 6 min, lognormal with CV 0.8 |
| Follow-up timing | the ticket's real life span | uniform within the life; 6 days for never-resolved tickets; weekend work done when it arises |
| Agents and roster | — | not generated; rosters are separate hypotheses ([assumptions.md](assumptions.md)) |

---

## Validation results

Real values come from `kpi_*`; synthetic values from `kpi_*_synth`. Both are produced by the same SQL.

| Check | Real **[REAL]** | Synthetic **[SYNTHETIC]** | Gap | Reading |
|---|---|---|---|---|
| Ticket count | 2,330 × 20 = 46,600 | 46,598 | −2 tickets | Poisson noise only. |
| Share of tickets by channel, topic, priority | — | — | max 0.51 points (`synth_max_mix_gap_pp`; High priority 17.9% real vs 18.4% synthetic) | The bootstrap reproduces the mix. |
| Share of tickets by product group, agent group | — | — | max 0.15 points | Same. |
| Share of tickets by weekday | Mon 17.6% … Sat 7.1% | Mon 17.6% … Sat 7.1% | max 0.28 points (Wed) | Weekday rates reproduced. |
| Share of tickets by hour of day | raw, 3.1–5.8% per hour | smoothed, 3.5–4.7% | max 1.07 points | Difference is the intended smoothing. |
| Share of tickets by quarter | Q3 24.0% | Q3 25.3% | max 1.28 points (Q3) | The real Q3 was a little quieter; synthetic months carry no month-level volume noise. |
| Resolution SLA, 2023 | 66.35% | 66.33% (`synth_resolution_sla`) | −0.02 points | Outcomes reproduced. |
| Resolution SLA by month | Jan 76.3% → Dec 59.7% | Jan 76.7% → Dec 59.2% | max 1.6 points (Oct) | The 2023 decline is carried into the synthetic year. |
| Pickup within target (process ceiling) | 87.2% (real response SLA; no queue forms at the export's volume, so it measures pickup) | 87.8% (`staff_process_ceiling`) | +0.5 points | Sampling luck: the base year (seed 42) draws slightly faster pickups than the export. The five replications give 87.1–87.3% (`staff_replications`); a one-off check of generator seeds 0–299 (not in the pipeline) gave a mean of 87.2% (sd 0.15), with seed 42 the 2nd highest. Absolute synthetic SLA levels are therefore about 0.5 points optimistic; roster gains are unaffected. |
| Response SLA | 87.2% | 85.8% | — | **Not a calibration target.** The synthetic value is a model output: real pickup delays plus simulated queueing under the assumed roster (optimistic rule). It is lowest at weekends (75.6% vs 86.6% real), where that roster is short. |

The unit test `tests/test_roster_synth.py::test_synthetic_mix_matches_real` regenerates the year with a different
seed (1). It checks that the ratio of synthetic to real tickets is within 0.5 of 20, that channel / topic / priority
shares are within 2 points, that no ticket falls on a holiday, and that interactions stay within 0–10.

---

## What the synthetic data must NOT be used for

1. **Statements about the real team.** It does not say how many people the real desk has or needs, whether the real
   team is short-staffed, or what today's roster is. Write "a 23-FTE desk in the 20× planning scenario", never "the
   team has 23 FTE". Only the real-data tests speak to the real team, and they show no capacity signal.
2. **Root cause, trends or seasonality.** Resolution outcomes, the slow path and the stale backlog are copied from the
   seeds, not generated by the model. Monthly volume is flat by construction.
3. **Intraday shape.** The hourly profile is the export's flat curve, smoothed. The model cannot reveal a daytime
   peak that the export lacks.
4. **Response SLA as an observation.** Synthetic response SLA depends on assumed handle times, the assumed roster
   and the response rule. Compare rosters with it; do not quote it as the desk's actual SLA.
5. **Agent-level, CSAT or field-relationship analysis.** Agent names are not carried. CSAT is copied. Within a month
   the attributes are independent of time, so any time-of-day or weekday effect in synthetic attributes is noise.
6. **Adding synthetic and real counts together.** The 46,598 tickets are a scenario, not additional volume.

---

## How to regenerate

- **Everything:** `python run.py` (or `make data` for data only; `make all` adds the report and notebooks). This
  rebuilds `synth_tickets`, `synth_work_items`, `synth_fct_tickets`, every `staff_*` table and `key_numbers.json`.
- **Change the scenario:** edit `config.yaml` (`scenario.scale_factor`, `scenario.hourly_smoothing_weights`,
  `staffing.handle_time_min`, `staffing.handle_time_cv`) and re-run. The holiday list is fixed in code
  (`synth.HOLIDAYS_2023`).
- **In Python** (reproduces the cached tables exactly; checked for this document):

  ```python
  import numpy as np
  from support_ops import synth
  from support_ops.config import load_config
  from support_ops.data import load_tickets

  cfg = load_config()
  fct = load_tickets()                                     # real tickets (fct_tickets.parquet)
  seed = cfg["random_seed"]                                # 42
  tickets = synth.generate_tickets(fct, cfg, np.random.default_rng(seed))
  items = synth.build_work_items(tickets, cfg, np.random.default_rng(seed + 1))
  # alternatives: semantics="half_agent" / "chat_in_session", follow_up_timing="weekdays", aht_multiplier=1.3
  ```

## Seeds and random streams

All randomness comes from seeded NumPy generators derived from `config.yaml` → `random_seed: 42`, so two runs give
identical data.

| Use | Generator seed | Code |
|---|---|---|
| Synthetic tickets (arrivals, bootstrap, repairs) | 42 | `pipeline.run` → `synth.generate_tickets` |
| Work items (follow-up timing, handle times) | 43 | `staffing.capacity_plan`, `staffing.sensitivity` → `synth.build_work_items` |
| Simulation of each roster (staffing noise) | 142–148, one per roster in the order proposed, flat, by_day, business_hours, hire_flat, hire_by_day, hire_business_hours | `staffing.capacity_plan` → `simulate_roster` |
| Deflection draws, low / base / high | 92 / 93 / 94 | `automation.automation_impact`, `automation.deflected_items` |
| Options C and B + C simulations | 443 / 444 | `business_case.options` |
| Growth curve | tickets 42, items 43, simulation 142 at every volume factor (base deflection 93) | `business_case.simulate_growth` |
| Five independent replications, r = 1…5 | base = 42 + 10,000 × r: tickets base, items base + 1, rosters base + 100 + j | `business_case.replicate_rosters` |
| Weekend stress test | same tickets (42), items (43) and roster simulation seeds (142–148); follow-ups moved to Monday after drawing | `staffing.capacity_plan(..., follow_up_timing="weekdays")` |
| Tie-breaking in the real-data load test | 0 | `rca.load_vs_sla` |
