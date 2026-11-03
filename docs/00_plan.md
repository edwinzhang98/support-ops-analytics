# 00 — Project plan (one page)

**Project:** Support ticket operations analysis and staffing optimization
**Requester:** Support Director · **Analyst:** Operations / Business Analyst, Customer Support
**Data cut:** ticket export covering 2023-01-02 to 2023-12-30, snapshot taken 2024-01-04 · **Plan written:** at kickoff, before analysis

## 1. Data

| Source | What it is | Used for |
|---|---|---|
| **Real export** (`Technical Support Dataset.csv`, 2,330 tickets, 22 fields) | Public Kaggle export (`suvroo/technical-support-dataset`, MIT). It has full timestamps (created, first response, resolution, close), SLA deadlines and flags, channel, priority, topic, tier, agent, interactions and CSAT. | Everything descriptive: volume, efficiency KPIs, SLA breakdowns, root cause, backlog, topic mix for automation sizing |
| **Synthetic scale-up** (about 47k tickets, calendar 2023, generated in `src/support_ops/synth.py`) | Built from the real export: arrival rates by weekday and hour, the joint mix of channel × topic × priority × tier, interactions per ticket, and resolution outcomes by month. Volume is scaled 20×. | Interval-level staffing only (Erlang C, simulation, roster optimization), plus the FTE and cost math in the business case |

Why we scale up: the export averages 6.4 tickets/day, about 0.3 per hour. Most hour-of-week cells hold 0–1 tickets per week, and no queue ever forms at that volume. Erlang C needs a stable hourly arrival rate. Every number in the deliverables is tagged **[REAL]** or **[SYNTHETIC]**.

## 2. Analysis outline (maps to notebooks 01–05)

1. **Volume patterns** — daily and monthly trend; weekday × hour heatmap; channel mix; topic Pareto.
2. **Efficiency and SLA** — first response time, resolution time, and response and resolution SLA attainment, all computed in DuckDB SQL from timestamps rather than the raw flags. Broken down by channel, priority, topic, tier, agent and time slot. Breach hotspots use Wilson intervals and a false-discovery-rate correction.
3. **Backlog and root cause** — daily open backlog split into active and aged tickets; weekly arrivals vs completions; mix-vs-rate decomposition of the SLA decline. The core question: is it volume, efficiency, or schedule mismatch?
4. **Staffing model** — Erlang C per hour-of-week for live work (chat and phone, 2-min target) and async work (email and follow-ups, 60-min target). It applies shrinkage and an occupancy cap. Current roster vs requirement. An integer-programming roster that keeps the same headcount. A discrete-event simulation to check the expected SLA. Sensitivity on handle time, shrinkage, volume, SLA goal and the current-roster assumption.
5. **Automation opportunities and business case** — deflection candidates by topic, with low/base/high deflection assumptions, hours saved and FTE equivalent. Three options compared: hire, re-roster, automate (plus a combined option), each with cost and SLA effect.

## 3. Expected outputs

- Streamlit demo app in 8 pages, ordered as the story, at `dashboard/app.py`. Standalone `reports/report.html` plus the HTML exports of the notebooks.
- Business documents: request and scope, metric definitions, data-quality checks, assumptions log, root cause analysis, capacity plan, headcount business case, readout memo, and a one-page action plan.
- One-command pipeline `make all` (equivalently `python run.py`), fixed random seed, data path set in `config.yaml` or `.env`.

## 4. What we borrow from the references

- **Kaggle notebooks on this dataset** (solitaryalter EDA; remkaynar workload/resource use; devraai). We borrow the standard EDA cuts: volume by time, channel and topic, SLA by agent.
- **pyworkforce** (`ErlangC`). We follow its conventions: build up agents from the traffic intensity until the SLA is met, raise to `A / max_occupancy` when the occupancy cap binds, then apply shrinkage last as `ceil(raw / (1 − shrinkage))`. We use its tutorial example as a unit test for our own implementation. We do not take a dependency on it.
- **Standard call-centre WFM practice**: interval requirement → shift coverage → roster, live-channel vs back-office split, shrinkage and occupancy.

## 5. What we add (what the references don't do)

- Metric definitions written before analysis. SLA recomputed from timestamps, because the raw flags contradict the timestamps on 15 tickets.
- A documented sanity check (row reconciliation, keys, nulls by status, impossible durations, category hygiene, the 60-interactions sentinel).
- A root-cause test that rules out volume and mix with numbers, rather than just describing trends.
- **The loop from analysis to decision:** requirement per hour → roster → simulated SLA → cost of each option → recommendation with owner, KPI and risk. None of the reference notebooks build a staffing model.

## 6. Key decisions taken at kickoff

> **Changed since kickoff:** decision 3 was replaced. The export's response
> breaches are not queue-driven, so headcount is **not** calibrated to the observed SLA. The current roster is instead
> compared under three stated hypotheses at the same headcount (weekday-weighted = baseline, flat 24/7, day-weighted).
> The FTE number is the requirement of a workload-matched roster, never "the current team". Response time combines
> queue wait with the real pickup delay under an optimistic and a conservative rule. The monthly-seasonality test was
> re-run against each month's weekday mix (p = 0.12). Details: `docs/assumptions.md`.

1. **Scale factor = 20×**, giving about 47k tickets/year, about 128/day. That is "tens of thousands of tickets" and a plausible mid-size B2B desk. It is a scenario parameter in `config.yaml`, not a fact.
2. **One synthetic year (2023), not two.** The export shows no volume trend and no significant monthly seasonality (χ² p = 0.14). A second year would have to be invented rather than calibrated.
3. **Current roster is unknown → assumed** to be flat 3-shift, 24/7 coverage. Headcount is calibrated so the simulated response SLA matches the export's observed 2023 level. The re-roster gain depends on this assumption, so it gets its own sensitivity analysis.
4. **SLA goal = 90% attainment** for both response and resolution. The data has per-ticket deadlines but no goal. 90% is adjustable in the dashboard.
5. **Handle time is not in the data** → estimated as first-touch minutes plus follow-up minutes × (interactions − 1), using stated assumptions with ±30% sensitivity.
