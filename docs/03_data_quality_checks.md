# 03 — Data-quality checks (sanity-check log)

**Bottom line.** The export is usable as the real data for this analysis. All 2,330 rows reconcile from file to
model with nothing dropped, ticket IDs are unique, and missing values follow the ticket lifecycle exactly. Of 31 checks,
17 pass, 7 are flagged and 7 are informational. Every flag has a documented rule, and none changes a headline
conclusion. The flag that matters most: the export's own SLA flags contradict its timestamps on 15 tickets, so every
SLA metric is recomputed from timestamps. Using the raw response flag would have shown a false dip in February
(76.1% instead of 84.8%). Separately, several patterns look generated rather than operational (flat 24-hour
arrivals, CSAT unrelated to breaches, resolution times capped near 6 days, evenly spread response times). We treat the
export as real but do not lean on relationships between fields.

All numbers in this document are **[REAL]**. They come from `reports/key_numbers.json`, from `dq_checks.parquet`, or
from queries on `fct_tickets.parquet` written for this document.

---

## Method

| Item | Detail |
|---|---|
| Checks 1–30 | [`sql/90_data_quality_checks.sql`](../sql/90_data_quality_checks.sql). Reads the raw CSV (variable `raw_csv_path`) and `fct_tickets` (variable `fct_tickets_path`). |
| Check 0 | `data.run_quality_checks()` in [`src/support_ops/data.py`](../src/support_ops/data.py). It counts the data lines of the CSV file as bytes in Python, independently of DuckDB's parser. |
| Output | `data/processed/dq_checks.parquet`, 31 rows: `check_id`, `area`, `check_name`, `observed`, `expected`, `status`, `action_taken`. Shown in the report (section 3) and on the dashboard page "Data & Sanity Checks". |
| Status rule | **PASS**: observed = expected. **FLAG**: observed ≠ expected; a decision is recorded in `action_taken` and below. **INFO**: there is no expected value; the number is context. |
| Re-run | `python -m support_ops.sql sql/90_data_quality_checks.sql` prints checks 1–30. `python run.py` rebuilds all 31 and writes the parquet. The raw path comes from `config.yaml` or the `SUPPORT_TICKETS_CSV` variable (`.env`). |
| Detail queries | Example ticket IDs, breakdowns and impact estimates below come from `fct_tickets.parquet`. |

## All checks

| # | Area | Check | Observed | Expected | Status | Action taken |
|---:|---|---|---:|---:|---|---|
| 0 | Reconciliation | Data lines in the CSV file (excluding header) | 2,330 | 2,330 | PASS | File lines reconcile with rows parsed by DuckDB |
| 1 | Reconciliation | Rows in raw export | 2,330 | 2,330 | PASS | Matches the dataset documentation (2,330 tickets) |
| 2 | Reconciliation | Rows in fct_tickets minus rows in raw (no rows dropped or duplicated) | 0 | 0 | PASS | None needed |
| 3 | Primary key | Duplicate Ticket IDs | 0 | 0 | PASS | None needed |
| 4 | Primary key | Null Ticket IDs | 0 | 0 | PASS | None needed |
| 5 | Primary key | Share of IDs present in the ID range (min..max) | 0.78 |  | INFO | INFO: 22% of IDs in range are absent - export may be a subset of all tickets |
| 6 | Time range | Tickets created outside calendar 2023 | 0 | 0 | PASS | None needed |
| 7 | Time range | Calendar days in 2023 with zero tickets | 9 |  | INFO | INFO: consistent with Poisson arrivals at ~3.4/day on weekends |
| 8 | Time range | Hours from last ticket created to snapshot (latest timestamp) | 105.8 |  | INFO | INFO: snapshot = 2024-01-04 05:39; used to decide if open tickets are overdue |
| 9 | Nulls by status | First response missing on a ticket that is not Open | 0 | 0 | PASS | None needed |
| 10 | Nulls by status | Resolution time missing on Resolved/Closed, or present on Open/In progress | 0 | 0 | PASS | None needed |
| 11 | Nulls by status | Close time present iff status = Closed (violations) | 0 | 0 | PASS | None needed |
| 12 | Nulls by status | CSAT survey present on a ticket that is not Closed | 0 | 0 | PASS | None needed |
| 13 | Durations | First response before ticket creation | 2 | 0 | **FLAG** | Excluded from response-time metrics and response SLA (2 Phone tickets) |
| 14 | Durations | Resolved before first response | 18 | 0 | **FLAG** | Kept: resolution metrics still valid; flagged as process/data-entry anomaly |
| 15 | Durations | Closed before resolved | 42 | 0 | **FLAG** | Kept: close time is not used in any SLA metric |
| 16 | Durations | Max resolution time observed (days) | 6.12 |  | INFO | INFO: hard ceiling ~6.1 days; basis for 7-day aged-backlog threshold |
| 17 | SLA policy | Distinct response targets (minutes) by channel - combinations | 3 | 3 | PASS | Policy inferred: Email 60 min, Chat 2 min, Phone 2 min |
| 18 | SLA policy | Distinct resolution targets (hours) by channel - combinations | 3 | 3 | PASS | Policy inferred: Chat 24 h, Email 48 h, Phone 48 h |
| 19 | SLA policy | Distinct response targets within a channel across priorities (should be 1 if priority-independent) | 1 | 1 | PASS | INFO: targets do not depend on priority |
| 20 | SLA flags | Raw response flag contradicts timestamps | 14 | 0 | **FLAG** | Recomputed from timestamps; all 14 on 2023-02-18..20 (flagged violated but met) |
| 21 | SLA flags | Raw resolution flag contradicts timestamps + snapshot | 1 | 0 | **FLAG** | Recomputed: ticket 3986 is unresolved and past due at snapshot -> breached |
| 22 | Categories | Topic labels that differ only by letter case | 1 | 0 | **FLAG** | "Pricing and Licensing" (68 rows, 6 months only) merged into "Pricing and licensing" |
| 23 | Categories | Agents assigned to more than one agent group | 0 | 0 | PASS | None needed |
| 24 | Categories | Tickets where support level and agent group disagree (Tier 1 <-> 1st line) | 0 | 0 | PASS | None needed: Support Level is the agent group, not ticket difficulty |
| 25 | Categories | Countries with more than one coordinate pair | 0 | 0 | PASS | Lat/long are country centroids; dropped (country kept) |
| 26 | Ranges | Agent interactions = 60 (outside the 1-10 range of all other tickets) | 45 | 0 | **FLAG** | Treated as sentinel -> NULL (all 45 are Chat); excluded from handle-time calibration |
| 27 | Ranges | Agent interactions missing | 18 |  | INFO | INFO: the 18 Open tickets (no agent touch yet) |
| 28 | Ranges | CSAT outside 1-5 | 0 | 0 | PASS | None needed |
| 29 | Cross-check | Response SLA met per raw flag (export as delivered) | 2,019 |  | INFO | INFO: 2,019 raw vs 2,031 recomputed (+14 mis-flags, -2 invalid) |
| 30 | Cross-check | Resolution SLA met per raw flag (export as delivered) | 1,547 |  | INFO | INFO: 1,547 raw vs 1,546 recomputed |

---

## Flagged checks in detail

### Check 13 — First response logged before the ticket was created (2 tickets)
- **What.** `first_response_at < created_at`, i.e. a negative first-response time.
- **Tickets.**

  | Ticket | Channel | Priority | Status | Created | First response logged | Gap |
  |---|---|---|---|---|---|---|
  | 1288 | Phone | Medium | Closed | 2023-02-01 19:56 | 2023-02-01 01:10 | 18.8 h earlier |
  | 2135 | Phone | Low | Resolved | 2023-05-18 05:54 | 2023-05-17 20:19 | 9.6 h earlier |

  The raw flag says "Within SLA" on both.
- **Decision.** `frt_invalid = TRUE`, `frt_min = NULL`, `response_sla_met = NULL`. Both are excluded from FRT
  statistics and from the response SLA numerator and denominator, which leaves 2,328 evaluable tickets. Their
  resolution data is kept, since both were resolved. When the synthetic generator bootstraps one of them, it redraws a
  valid phone FRT ([04](04_synthetic_data.md)).
- **Impact.** None material. Counting both as met would move 2023 response attainment from 87.24% to 87.25%.

### Check 14 — Resolved before the first response (18 tickets)
- **What.** `resolved_at < first_response_at`.
- **How many.** 18 tickets: 17 email, 1 chat; 9 Resolved, 9 Closed. The first response is logged 0.5–387 minutes
  after the resolution (median 40).
- **Examples.**

  | Ticket | Channel | Resolved after | First response logged after |
  |---|---|---|---|
  | 1221 | Email | 1.4 h | 470 min |
  | 1645 | Email | 52.5 min | 56.3 min |
  | 2722 | Chat | 4.0 min | 4.5 min |
  | 3542 | Email | 1.2 min | 47.0 min |

- **Decision.** Kept as recorded. Each timestamp is plausible on its own. The order suggests the reply was logged
  after the fix (data entry), or that "first response" sometimes records a later message.
- **Impact.** Resolution metrics are unaffected: all 18 were resolved within SLA. By their logged first response, 11
  of the 18 are response breaches. If the resolution time were taken as the first reply instead, only 2 of those 11
  (tickets 1861 and 3230) would meet the 60-minute email target. That is at most +0.09 points on 2023 response attainment.

### Check 15 — Closed before resolved (42 tickets)
- **What.** `closed_at < resolved_at`.
- **How many.** 42 tickets, all with status Closed (26 email, 8 phone, 8 chat). They were closed 0.2–24.7 h (median
  11.1 h) before the resolution timestamp.
- **Examples.** 1082, 1340, 1379, 1435, 1552.
- **Decision.** Kept. Close time feeds no metric: `closed_at` and `close_h` appear only in `fct_tickets` and in checks
  11 and 15. Resolution metrics use `Resolution time`.
- **Impact.** None on any KPI.

### Check 20 — Raw response flag contradicts the timestamps (14 tickets)
- **What.** `SLA For first response` = "SLA Violated", but `first_response_at ≤ response_due_at`.
- **Tickets.** All 14 were created between 2023-02-18 and 2023-02-20: 1412, 1413, 1420, 1421, 1424, 1425, 1426, 1427,
  1428, 1429, 1430, 1432, 1433, 1434 (11 email, 2 phone, 1 chat). Their FRTs are 0.02–56.6 minutes, all inside the
  target. Three consecutive days point to a batch mis-flag.
- **Decision.** Response SLA is recomputed from timestamps for every ticket (`response_sla_met`). The raw flag is kept
  in `response_sla_flag_raw` and the disagreement in `response_flag_mismatch` for audit. The mismatch column only
  compares tickets with a valid first response, so the 2 tickets of check 13 are not counted in it.
- **Impact.** With the raw flags, February response attainment would read 76.1% instead of 84.8%: a false dip of 8.7
  points. The 2023 total would read 86.7% instead of 87.2%.

### Check 21 — Raw resolution flag contradicts the timestamps and snapshot (1 ticket)
- **Ticket 3986.** Email, In progress, created 2023-12-29 21:52, resolution due 2023-12-31 21:52. Not resolved by the
  snapshot (2024-01-04 05:39, ticket age 5.3 days). The raw flag says "Within SLA".
- **Decision.** Unresolved and past due at the snapshot counts as a breach (`resolution_sla_met = FALSE`, outcome
  "Unresolved, overdue"). The raw flag was probably set before the deadline passed.
- **Impact.** December resolution attainment is 59.7% instead of 60.2% with the raw flag. The 2023 total is 66.35%
  instead of 66.39%.

### Check 22 — Topic labels that differ only by letter case (68 rows)
- **What.** "Pricing and Licensing" (68 rows) next to "Pricing and licensing" (457 rows). The capitalised variant
  appears in six months only: February 11, April 7, June 16, August 13, September 12, November 9. That looks like a
  second entry form or import path.
- **Examples.** 1300, 1321, 1341, 1392, 1393.
- **Decision.** `topic` = the trimmed label in sentence case
  (`upper(left(trim(Topic), 1)) || lower(substr(trim(Topic), 2))` in `sql/00`). The original is kept in `topic_raw`.
  This leaves seven topics.
- **Impact.** Without the merge, "Pricing and licensing" would be 19.6% of tickets instead of 22.5%. An eighth topic
  would appear in the Pareto, the hotspot scan and the automation sizing, and the variant's on/off months would look
  like a mix shift.

### Check 26 — Agent interactions = 60 (45 tickets)
- **What.** Every other ticket has 1–10 interactions. All 45 are chat tickets, spread across all 12 months (1–8 a
  month). Statuses: Closed 19, Resolved 16, In progress 10.
- **Examples.** 1024, 1029, 1062, 1101, 1134.
- **Decision.** `agent_interactions = NULL`; the raw value is kept in `agent_interactions_raw`. These tickets are left
  out of interaction averages (`interactions_avg`, topic complexity). When the synthetic generator bootstraps one of
  them, it draws a valid interaction count from real tickets of the same channel ([04](04_synthetic_data.md)).
- **Impact.** Keeping 60 would raise the chat average from 5.2 to 8.1 interactions. It would also add roughly 6
  agent-minutes of phantom follow-up work per synthetic ticket, about +21% workload (estimate for this document:
  45/2,330 of seeds × (60 − 5.2) extra touches × 6 min).

---

## Row-count reconciliation

| Step | Rows | Check |
|---|---:|---|
| Data lines in the CSV file, excluding the header | 2,330 | 0 |
| Rows parsed by DuckDB | 2,330 | 1 |
| Rows in `fct_tickets` (difference vs raw = 0) | 2,330 | 2 |
| Tickets in every volume and resolution KPI | 2,330 | — |
| Tickets evaluable for response SLA (2 with first response before creation excluded) | 2,328 | 13 |

By status: Closed 1,173 · Resolved 739 · In progress 400 · Open 18.

## Primary key

- `Ticket ID` is unique (check 3) and never NULL (check 4).
- **Ticket ID gaps: 78% of IDs present** (check 5). IDs run from 1012 to 3999, so 2,988 values are possible. 2,330
  are present (78.0%) and 658 are missing. IDs rise with creation time (Spearman 0.99999 between ID and created time).
  The gaps are spread across the year: in eleven months, 73–83% of the month's ID range is present; December is
  lowest at 67%. 2,142 of the 2,329 steps between consecutive IDs are +1, and the largest jump is 35.
- **What it means.** The missing IDs could be deleted, merged or spam tickets, tickets from another queue, or a sample
  of a larger export; the data cannot tell. If they are missing at random, rates (SLA attainment, shares) are
  unaffected but volume is understated. All volume statements therefore refer to "tickets in this export".

## Nulls by status

Missing values follow the ticket lifecycle exactly (checks 9–12 all pass):

| Status | Tickets | First response | Resolution time | Close time | CSAT | Interactions (raw) |
|---|---:|---:|---:|---:|---:|---:|
| Closed | 1,173 | 1,173 | 1,173 | 1,173 | 1,173 | 1,173 |
| Resolved | 739 | 739 | 739 | 0 | 0 | 739 |
| In progress | 400 | 400 | 0 | 0 | 0 | 400 |
| Open | 18 | 0 | 0 | 0 | 0 | 0 |

- Only Open tickets lack a first response; the 18 Open tickets are also the 18 with missing interactions (check 27).
- A resolution time exists exactly for Resolved and Closed tickets. A close time and a CSAT score exist exactly for
  Closed tickets, and every Closed ticket has a score.
- NULLs we create: `frt_min` is NULL on 20 tickets (18 unanswered + 2 negative), `agent_interactions` on 63 (18 Open
  + 45 sentinel), `response_sla_met` on 2.

## Outliers and ranges

| Field | Observed **[REAL]** | Decision |
|---|---|---|
| Resolution time | 0.02 h to 146.8 h (6.12 days); one ticket above 144 h, 76 above 120 h; none negative | Kept. The cap is a provenance signal (below) and the basis for the 7-day aged threshold. |
| First response time, email | median 32.2 min; 99th percentile 405.9 min; maximum 1,672.7 min (27.9 h) | Kept. These are real breaches (missed emails), not errors. |
| First response time, chat / phone | medians 1.25 / 1.23 min; 99th percentiles 5.8 / 6.0 min; maxima 277.9 / 813.4 min | Kept, same reason. |
| Agent interactions | 1–10, plus 45 values of 60 | 60 → NULL (check 26). |
| CSAT | 1–5 on all 1,173 responses (check 28) | None needed. |
| Close time | 4.7–191.0 h after creation | Not used in any metric. |
| Latitude / longitude | one pair per country (check 25) | Dropped; `country` kept. |

## Time range

- Tickets were created from 2023-01-02 00:58 to 2023-12-30 19:49. None fall outside 2023 (check 6).
- **Snapshot** = the latest timestamp in the export, 2024-01-04 05:39, which is a resolution timestamp. It is 105.8 h
  after the last ticket was created (check 8). Every response and resolution deadline falls before it, so every
  ticket can be classified ([02 §1.3](02_metric_definitions.md#13-snapshot)).
- 9 calendar days of 2023 have no tickets (check 7); see "Holidays and zero-ticket days" below.

## Cross-checks with the raw SLA flags

Reconciliation of the export's flags with our timestamp-based definitions (checks 20, 21, 29, 30):

| Step | Response SLA | Resolution SLA |
|---|---:|---:|
| Met per raw flag (export as delivered) | 2,019 of 2,330 | 1,547 of 2,330 |
| + flagged "Violated" but met per timestamps (check 20) | +14 | 0 |
| − flagged "Within SLA" but first response before creation, so not evaluable (check 13) | −2 | — |
| − flagged "Within SLA" but unresolved and past due at the snapshot (check 21) | — | −1 |
| **= Met per our definition** | **2,031 of 2,328** | **1,546 of 2,330** |
| Attainment: raw flag → ours | 86.7% → 87.2% | 66.4% → 66.4% (66.39% → 66.35%) |

Every other ticket agrees. For response, 2,296 of the 2,310 tickets with a valid first response match the raw flag,
and all 18 unanswered tickets carry "SLA Violated". For resolution, all 366 tickets resolved late and 417 of the 418
never resolved carry "SLA Violated", and all 1,546 resolved within SLA carry "Within SLA".

---

## Provenance and generator-like patterns

The dataset is a public Kaggle export described as a data-challenge scenario. Its provenance is not documented. The
patterns below are not errors to fix, but they look generated rather than operational. Each one limits what the
analysis may conclude, and the report and dashboard state these limits.

| Pattern | Evidence **[REAL]** | How it limits conclusions |
|---|---|---|
| **Flat 24-hour arrivals** | The 12 hours from 08:00 to 19:59 hold 49.8% of tickets; a perfectly flat curve gives 50%. Hourly counts range from 72 (14:00) to 135 (15:00). The lowest and highest hours are neighbours, which points to noise rather than a daily shape. Weekday and hour are independent (χ² p = 0.90). All customers are in 12 European countries, where a business-hours peak would be expected. | No intraday staffing shape can be learned. The workload-matched roster is therefore close to flat, and the only roster lever is the weekday/weekend balance. If the real desk has a daytime peak, the hourly requirement and the roster answer change. |
| **CSAT unrelated to breaches** | Tickets that breached resolution SLA average 3.60, those that met it 3.49 (χ² p = 0.45 on the score distribution). For response SLA: 3.59 vs 3.50 (p = 0.15). The correlation of CSAT with resolution time is 0.03 (Spearman, p = 0.34). | The customer cost of a breach cannot be estimated. CSAT is not used as an outcome or to rank options. |
| **Uniform-ish interactions** | Counts sit in fixed per-channel ranges with no tail: chat 2–9 (never 1), email 1–10, phone 1–7. Averages barely move with tier (4.38 vs 4.42), topic (4.15–5.09) or outcome (4.34–4.49). They are barely related to resolution time, and in the wrong direction (Spearman −0.06). In a real desk, harder tickets take more touches and longer. | Interactions cannot serve as a complexity measure, so topic complexity proxies differ little and the automation ranking rests on volume and request type. Workload in the staffing model depends on how the field is read (19–23 FTE, [assumptions.md](assumptions.md)). |
| **Resolution cap ~6.1 days** | The maximum resolution time is 146.8 h (6.12 days); only one ticket exceeds 144 h. Tickets are either resolved within about 6 days or never (418 never resolved, median age 202 days at the snapshot). | The 7-day aged threshold separates stale from active tickets cleanly only because of this cap; in real data "stale" would blur into "slow". Tail metrics such as the 90th percentile cannot exceed about 6 days. |
| **Within-SLA response times uniform in the target window** | On-time email FRTs have 10th / 25th / 50th / 75th / 90th percentiles of 6.4 / 15.5 / 29.8 / 44.5 / 54.3 min: almost exactly uniform over 0–60 (Kolmogorov–Smirnov p = 0.68). Chat and phone on 0–2 min: p = 0.07 and 0.77. Real response times are usually skewed, with many quick replies and a long tail. | The staffing model uses real FRT as the pickup delay. Under the conservative rule (pickup + queue wait), any wait pushes tickets that were near the deadline over the line, so the two response rules sit far apart. "How close to the deadline" analyses are not meaningful. |
| **Priority has no effect** | Targets are identical across priorities (check 19). Response attainment: High 88.7%, Medium 87.9%, Low 86.3% (p = 0.363). Resolution attainment: 69.5% / 65.0% / 66.1% (p = 0.29). Median resolution time is 21.6–22.7 h for every priority. | Priority-based routing cannot be evaluated or recommended from this data. Priority is either not used in practice or not meaningful in this export. |
| **Calendar-time SLA clock** | Targets are a constant 24 h or 48 h whatever the weekday or hour. Weekends get 44.8% of weekday arrivals but 80.5% of weekday resolutions. | Weekend work may partly be a feature of the generator. The roster result assumes weekend follow-ups are real work done when they arise; a stress test defers them to Monday instead ([assumptions.md](assumptions.md), A13). |

## Holidays and zero-ticket days

Nine calendar days of 2023 have no tickets (check 7):

| Date | Day | Note | In the synthetic year ([04](04_synthetic_data.md)) |
|---|---|---|---|
| 2023-01-01 | Sun | New Year's Day; before the first ticket (2 Jan) | Holiday, zero volume |
| 2023-04-08 | Sat | Easter Saturday. Good Friday (5 tickets), Easter Sunday (6) and Easter Monday (7) all had tickets | Normal Saturday volume |
| 2023-04-27 | Thu | No obvious reason; the only zero weekday outside Christmas | Normal Thursday volume |
| 2023-05-27 | Sat | — | Normal volume |
| 2023-10-15 | Sun | — | Normal volume |
| 2023-12-24 | Sun | Christmas Eve | Holiday, zero volume |
| 2023-12-25 | Mon | Christmas Day | Holiday, zero volume |
| 2023-12-26 | Tue | Boxing Day / St Stephen's Day | Holiday, zero volume |
| 2023-12-31 | Sun | New Year's Eve; after the last ticket (30 Dec) | Holiday, zero volume |

- **Holidays with zero tickets: 1 Jan and 24–26 Dec** (plus 31 Dec, after the last ticket). These five days are
  treated as holidays in the synthetic year (`synth.HOLIDAYS_2023`). They are excluded from the weekday arrival rates
  and from the hourly demand averages.
- **Easter Saturday (8 Apr)** has zero tickets too, but the rest of the Easter weekend had normal volume. Zero
  Saturdays are expected by chance: at 3.2–3.7 tickets per weekend day, about 3.4 of the 102 non-holiday weekend days
  should have no tickets, and exactly three do (8 Apr, 27 May, 15 Oct). It is not treated as a holiday.
- **Thursday 27 April** is unusual. At 7.1–8.4 tickets per weekday, the expected number of zero weekdays in a year is
  0.13, roughly a 1-in-8 chance of seeing at least one. It is kept as observed and not treated as a holiday.

## What these checks cannot cover

- **Duplicates by content.** The export has no customer ID, so the same issue raised twice cannot be found.
- **Reopened tickets and time in each status.** There is no status history, so we cannot see where resolution time is
  spent. This is the main data gap for the root cause ([02 §3.5](02_metric_definitions.md#35-resolution-outcome-classes-late-share-and-never-resolved-share)).
- **Agent schedules, logins and handle times.** None are in the export; the staffing model's inputs for these are
  assumptions ([assumptions.md](assumptions.md)).
