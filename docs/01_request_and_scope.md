# 01 — Request and scope

## The request (verbatim, as received from the Support Director)

> 「SLA 达成率在掉，团队说人不够。下季度要向上申请 headcount，我需要数据支撑：到底是来量涨了还是效率掉了？每个时段要几个人？有没有不加人就能解决的办法？」

English translation:

> "Our SLA attainment is falling and the team says we don't have enough people. I have to put in a headcount request for next quarter and I need data to back it up. Is it that volume went up, or that efficiency went down? How many people do we need in each time slot? Is there a way to fix this without adding people?"

The standard outputs for this kind of request are an operations KPI view, a root cause analysis, a capacity plan, a headcount business case and process-improvement recommendations.

## Clarified analysis questions

| # | Director's words | Analysis question (testable) | Answered with |
|---|---|---|---|
| Q1 | "SLA attainment is falling" | Which SLA is falling — **response** (time to first reply) or **resolution** (time to solve)? By how much, from when, and is the decline larger than noise? | Monthly attainment computed from timestamps, with Wilson 95% CIs **[REAL]** |
| Q2 | "Did volume go up?" | Did ticket volume (or the mix of channels and topics, since SLA targets differ by channel) change enough to explain the decline? | Volume trend, mix-vs-rate decomposition **[REAL]** |
| Q3 | "Did efficiency go down?" | Did handling speed fall? Is it everywhere, or concentrated in specific channels, topics, priorities, tiers, agents or time slots? | Breakdowns, breach hotspots, agent scorecard **[REAL]** |
| Q4 | "The team says we're short-staffed" | Is there evidence that load drives breaches? Do busy days and hours show worse SLA? Does the backlog build from arrival spikes or from low throughput? | Load-vs-breach correlation, backlog flow analysis **[REAL]**; hourly queue simulation **[SYNTHETIC]** |
| Q5 | "How many people per time slot?" | For each hour of the week, how many agents are needed to hit the SLA goal, given arrivals and handle time? How does that compare with the current roster? | Erlang C requirement vs roster **[SYNTHETIC]** |
| Q6 | "Can we fix it without adding people?" | (a) How much SLA does a re-roster of the same headcount buy? (b) How many tickets could self-service or automation deflect, and how many hours would that save? (c) Which process fixes target the actual root cause? | Roster optimization + simulation **[SYNTHETIC]**; deflection sizing on real topic mix **[REAL mix × assumptions]** |
| Q7 | "Headcount request" | What does each option cost (hire / re-roster / automate) and what SLA does it buy? Which do we recommend for next quarter? | Business case **[SYNTHETIC FTE math]** |

## Decision maker, decision and timing

- **Decision maker:** Support Director, who presents to the VP of Customer Experience in the quarterly planning cycle.
- **Decisions this analysis feeds:**
  1. **Headcount:** request N additional FTE for next quarter (Q2 2024), or not.
  2. **Roster:** change shift coverage from next quarter's roster cycle.
  3. **Process / automation:** fund self-service content and routing changes; set a stale-ticket policy.
- **Timing:** the export runs to 2024-01-04. Output is needed for the Q1 planning cycle, so the next-quarter plan uses the 2023 demand profile as the forecast.

## What would change the decision (agreed up front)

| If the data shows… | …then the recommendation leans to |
|---|---|
| Volume grew materially (> ~10%) and breaches rise with load | **Hire** (the capacity gap is real and growing) |
| Volume flat, but demand and roster are misaligned by hour/day | **Re-roster** before hiring |
| Volume flat, breaches spread across all segments, not load-driven | **Process fixes** (find what changed); headcount won't fix it |
| A few high-volume, low-complexity topics dominate | **Automation / self-service** |

## Scope

**In scope:** 2023 ticket export; response and resolution SLA; volume, efficiency, backlog; hour-of-week staffing for a scaled scenario; roster comparison; deflection sizing; cost comparison.

**Out of scope (and why):**
- **CSAT impact modelling.** In this export CSAT shows no relationship with SLA breach (3.6 vs 3.5), so we can't put a number on the customer cost of breaches.
- **Agent-level performance management.** The `Agent Name` field is the *current* owner of the ticket, not necessarily who did the work.
- **Multi-year forecasting.** One year of data, no trend.
- **Hiring lead time and ramp-up modelling.** Stated as a risk in the business case instead.

**Stakeholders:** Support Director (decision), Support Team Leads (roster owners, implementation), WFM / scheduling (roster build), Knowledge / Self-service owner (deflection content), Finance business partner (FTE cost assumptions).
