# Action plan: support SLA recovery, 8 January – 1 March 2024

**For:** support team leads and the support manager · **From:** Operations Analyst, Customer Support · **Issued:** 2024-01-08 · **Horizon:** 8 weeks · **Review:** Fridays, 30 minutes, against the scorecard below.

**Why:** on-time resolution fell from 73.6% (Q1 2023) to 60.6% (Q4) while on-time first reply held at 87.2% [real 2023 data]. Volume was flat and the slowdown hit every segment, so this is a process fix, not a hiring plan. 418 tickets were never closed (53% of resolution breaches); tickets resolved late rose from 9.8% to 21.8% of all tickets. Roster and self-service figures come from the scaled planning model and are conditional [synthetic / assumption]. Numbers: [`key_numbers.json`](key_numbers.json); background: [`../docs/readout.md`](../docs/readout.md).

## Actions

| # | Action | Owner | Start | Done by | Success metric and target | Weekly check |
|---|---|---|---|---|---|---|
| 1 | **Stale sweep.** Week 1: audit 50 of the 418 never-resolved tickets, classify them (abandoned / waiting on customer / waiting on engineering or tier 2 / genuinely open / resolved elsewhere) and agree outcome codes. Weeks 2–5: work or close all 418 with an outcome code (323 with 1st line, 95 with 2nd line: about 13 per agent per week) | Team leads; all agents | Mon 8 Jan | Fri 9 Feb | Tickets open > 7 days: 417 at 4 Jan → fewer than 20; every closure carries an outcome code; a 20-ticket re-audit finds none "closed but unresolved" | Count open > 7 days at Friday close (target −100 a week); outcome-code mix |
| 2 | **Standing 7-day rule.** Any ticket open > 7 days is reviewed by its lead; > 14 days is escalated with a reason code | Support manager | Mon 12 Feb | Ongoing | New never-resolved tickets < 5% of each month's tickets (2023: 17.9%) | List of tickets crossing 7 days |
| 3 | **Find the resolution slow path.** Pull the 2023 status history (time in each status, reassignments) and the March–October change log (releases, tooling, routing rules, policy); compare H1 with H2 | Ops Analytics + 2nd-line lead; Director for the change log | Data request Mon 8 Jan; analysis from Mon 22 Jan | Fri 16 Feb | Named cause(s) with the hours they add, plus a fix proposal; aim: late share ≤ 10%, slowest tenth of tickets ≤ 48 h | Progress note; data-request status |
| 4 | **Email pickup pilot.** 45-minute "unanswered email" alert to the on-shift lead; log each alert and whether the email was answered within 15 minutes of it | 1st-line lead + support-tooling owner | Config Mon 15 Jan; live Mon 22 Jan | Fri 1 Mar (4 weeks of data) | Emails answered within 60 min ≥ 92% (2023: 91.6%); catch rate measured, not assumed; no SLA credit until then | Alerts fired / answered within 15 min; email first-reply SLA |
| 5 | **Push-routing pilot for chat and phone** on one team: each live contact assigned to a named agent instead of a shared queue | 2nd-line lead (pilot team) + tooling | Mon 29 Jan | Fri 1 Mar | Chat replies within 2 min ≥ 87% (2023: 84.1%); phone ≥ 80% (2023: 75.8%) | Chat/phone first-reply SLA; lateness of breaches (2023: about 2 min) |
| 6 | **Confirm the real roster, then draft the Q2 roster.** WFM supplies people per shift per day, headcount and absence; leads confirm how weekend follow-ups are handled; Ops Analytics re-runs the model; if the weekend gap is confirmed, draft a Q2 roster moving about 6% of weekly shifts from Mon–Wed to Sat–Sun, same headcount | WFM + team leads; Ops Analytics | Request Mon 8 Jan; draft from Mon 29 Jan | Fri 23 Feb (Q2 roster cycle) | Q2 roster published with no weekend hour below requirement; weekend first-reply SLA within 2 points of weekday | Roster-draft status; weekend volunteer list |
| 7 | **Self-service pilot.** Pricing/licensing FAQ and licence self-service; invoice download and payment status; feature requests routed to the product feedback portal with an auto-acknowledgement | Knowledge / self-service owner; product owner for the portal | Mon 22 Jan | Content live Fri 1 Mar; measure through Q2 | Weekly tickets in these topics 20% below 2023 (about 10 pricing/licensing, 5 invoicing, 8 feature requests a week); CSAT on those topics not lower | Tickets per topic per week vs 2023 |
| 8 | **Readout.** Scorecard results, headcount-trigger check, decisions on the Q2 roster and on extending the pilots | Support manager + Ops Analytics | Fri 1 Mar | Fri 1 Mar | Decisions recorded; next 8-week plan issued | — |

## Weekly scorecard (Fridays)

Targets are for 1 March; the company goal for both SLAs is 90%. A week is about 45 tickets, so one week's SLA moves by about ±14 points by chance; KPIs 1 and 2 therefore use a 4-week rolling window (about 180 tickets, ±7 points).

| # | KPI | Definition | 2023 baseline [real] | Target by 1 Mar | Amber | Red |
|---|---|---|---|---|---|---|
| 1 | Resolution SLA attainment | Tickets created in the last 4 weeks (matured 7 days) resolved within target; unresolved and overdue = breach | 66.3% (Q4: 60.6%) | ≥ 70% | 60–70% | < 60% |
| 2 | Resolved-late share | Tickets resolved after their deadline, as a share of all tickets created; 4-week rolling | H1 9.8%; H2 21.8% | ≤ 15% | 15–20% | > 20% |
| 3 | Tickets open > 7 days | Count at Friday close | 417 at 4 Jan 2024 | < 20 | 20–50 | > 50, or rising two weeks running |
| 4 | Response SLA attainment | Share of the week's tickets with a first reply within target (email 60 min, chat/phone 2 min); overall and email | 87.2%; email 91.6% | ≥ 88%; email ≥ 92% | 85–88% | < 85% |
| 5 | Weekly ticket volume | Tickets created in the week vs the 2023 average of 45 (range 24–63) | 45 a week | — | > 52 (+15%) | > 56 (+25%) four weeks running = headcount trigger |
| 6 | Queue and utilisation (once WFM reports them) | Contacts reaching an agent within target; share of scheduled time spent handling work | n/a in 2023 data | ≥ 90% / ≤ 85% | 90–92% / 80–85% | < 90% / > 85% |

## Headcount trigger

Raise a headcount request only if KPI 5 stays above +25% for four consecutive weeks; KPI 6 shows fewer than 90% of contacts reaching an agent within target, or utilisation above 85%, for a month; or actions 3 and 6 reveal a real capacity loss (time diverted from tickets, or a tier-2 queue behind the slow path). Otherwise re-assess at the end of Q2 with real roster and handle-time data. In the planning model the same team meets the staffing goal up to +25% volume, and up to +50% with self-service in place [synthetic].
