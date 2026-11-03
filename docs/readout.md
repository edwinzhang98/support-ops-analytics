# SLA decline and next quarter's headcount: readout

**To:** Support Director · **From:** Operations Analyst, Customer Support · **Date:** 2024-01-08 · Detail: [root_cause_analysis.md](root_cause_analysis.md), [capacity_plan.md](capacity_plan.md), [headcount_business_case.md](headcount_business_case.md)

## Bottom line

The SLA that fell in 2023 is the **resolution** SLA (tickets solved on time), not the **response** SLA (first reply on time). The 2023 data shows a **process change, not a capacity shortfall**: volume did not grow, breaches are no more common when the desk is busy, and the slowdown hit every channel, topic, priority, tier and agent at once. **I recommend no headcount request this quarter.** The fastest wins are clearing the 418 tickets that were never closed and finding what started slowing resolutions in spring. Re-rostering toward the weekend is worth doing once we have checked the real roster.

## What the 2023 data shows — 2,330 real tickets

- On-time resolution fell from 73.5% in Q1 to 60.6% in Q4 (margin of error about ±4 points). On-time first reply held at 87.2% and improved in the second half (85.4% → 89.1%).
- Volume was flat (second half −2.7% against the first); the mix of channels and topics did not move.
- The typical ticket is barely slower (20 → 23 hours), but one ticket in ten took more than 47 hours in January and more than 104 in December. Tickets solved late rose from 9.8% to 21.8% of all tickets, gradually from March to October, equally everywhere. The data cannot say why: it has no record of time spent waiting on customers, engineering or tier 2.
- 418 tickets (18%) were never resolved: 53% of all resolution breaches, typically open for 202 days.
- Missed first replies are missed, not queued: a late email was typically answered 3.5 hours late; late chats and calls were typically about two minutes late.
- Caveat: a loss of capacity outside the ticket system (time diverted to other work, slower tooling) would not show in this data.

## What the planning model shows — scaled scenario: 20× the volume, a 23-FTE desk, today's roster assumed

- A desk that size needs 5–6 people on duty in every weekday hour and 3–5 at weekends. If today's roster is set by new-ticket counts, it is short in 30 of 168 weekly hours, all at weekends, with spare people on weekdays.
- Moving about 7 shifts a week from Monday–Wednesday to the weekend lifts the model's first-reply SLA from 85.8% to 87.6% on an optimistic reading of how waiting and slow pickup combine (82.6% → 84.7% on a cautious one), with no extra people. Adding 7 weekend shifts instead (1.4 full-time equivalents) costs about €94k in year one and €84k a year after (about €130k as two whole hires), for the same result on the optimistic reading and about one point more on the cautious one. This holds only if today's roster really is weekday-weighted and weekend follow-up work is done when it arises.
- No roster beats 87.8% on first reply: slow and missed pickups set that ceiling. Self-service and routing across five topics could take about 20% of tickets (an assumption; pricing/licensing and invoicing alone about 7%) and free about four people's worth of time.
- If volume grows, first-reply SLA stays within a point of today's only up to about +5% (86% at +10%, 80% at +25%, optimistic reading): re-run the model there. The staffing goal still holds at +25% but not at +30%: revisit headcount there. With self-service, first-reply SLA stays within a point up to +30% and the staffing goal is still met at +50%, the top of the range tested.

## Recommendations

| # | Action | Owner | Expected impact | How we measure | Risk |
|---|---|---|---|---|---|
| 1 | Sweep the 418 stale tickets; then a standing rule for anything open > 7 days | Team leads | Up to 53% of resolution breaches resolved or correctly closed [real] | Never-resolved share of each month's tickets < 5% | Closing without resolving games the metric: outcome codes, audit 50 first |
| 2 | Find and reverse the resolution slow path from spring 2023 | Director + tier-2 lead, Ops Analytics | At the first-half late rate, on-time resolution would be near 74% — a target, not a forecast [real] | Time in each status; late share ≤ 10%; slowest tenth ≤ 48 h | Cause may sit outside support; needs status history |
| 3 | No headcount request this quarter; revisit at a trigger | Director | Avoids about €94k in year one, €84k a year after [planning model] | Early warning: volume > +5% vs 2023 for four weeks → re-run the model. Revisit headcount if volume > +25% for four weeks, or the staffing goal breaks (< 90% of contacts reaching an agent in time, or utilisation > 85%) | Faster growth; covered by the triggers and self-service headroom |
| 4 | Re-roster toward workload: more weekend cover, after checking today's real roster | WFM + team leads | +1.5 to +2.0 points first-reply SLA (optimistic); +1.3 to +1.9 cautious [planning model, conditional] | Response SLA and waiting time by hour of week | Real roster unknown; weekend preferences |
| 5 | Pilot a 45-minute "unanswered email" alert and push routing for chat/phone | Team leads + tooling | +2.2 points if the alert catches half of email breaches — an illustration until measured | Emails answered within 60 min; alerts answered within 15 min | Only 10% of email breaches are near-misses; alert fatigue |
| 6 | Pilot self-service for pricing/licensing and invoicing (plus setup guides and a training catalogue); route feature requests to a feedback portal | Self-service / knowledge owner | About 86 agent-hours a week, roughly 4 people's capacity to redeploy to actions 1–2 [assumed deflection] | Tickets per topic per week vs 2023; self-service success rate; CSAT | Rates are assumptions; weak content bounces back |

## What we need from you

1. **Decision:** no headcount request for Q2, with the triggers in recommendation 3.
2. **Sponsor the stale-ticket sweep** (team leads, four weeks) and the standing 7-day rule.
3. **Access** to the ticket status history and the March–October 2023 change log, to find the slow path.
4. **Ask WFM** for the real roster, headcount and absence figures, so the re-roster can be confirmed for the Q2 roster cycle.
5. **Approve two pilots:** the unanswered-email alert (configuration only) and self-service content (about €40k one-off and €25k a year, assumed, to confirm with Finance).
