-- =============================================================================
-- 05_agent_scorecard.sql  ·  Agent-level KPIs with confidence intervals
-- -----------------------------------------------------------------------------
-- Input : fct_tickets (variable `fct_tickets_path`)
-- Output: one row per agent: volume, response / resolution attainment
--         (+ Wilson 95% CI), resolution speed, H1 vs H2 resolution attainment,
--         interactions, CSAT.
-- Caveat: `agent_name` is the agent CURRENTLY assigned to the ticket, not
--         necessarily the one who did the work -> use for coaching
--         conversations, not performance ratings.
-- Run: python -m support_ops.sql sql/05_agent_scorecard.sql
-- =============================================================================
CREATE OR REPLACE TEMP MACRO wilson_lo(x, n) AS (
    CASE WHEN n > 0 THEN ((x::DOUBLE / n) + 1.96 ^ 2 / (2 * n)
        - 1.96 * sqrt((x::DOUBLE / n) * (1 - x::DOUBLE / n) / n + 1.96 ^ 2 / (4 * n * n))) / (1 + 1.96 ^ 2 / n) END);
CREATE OR REPLACE TEMP MACRO wilson_hi(x, n) AS (
    CASE WHEN n > 0 THEN ((x::DOUBLE / n) + 1.96 ^ 2 / (2 * n)
        + 1.96 * sqrt((x::DOUBLE / n) * (1 - x::DOUBLE / n) / n + 1.96 ^ 2 / (4 * n * n))) / (1 + 1.96 ^ 2 / n) END);

WITH f AS (
    SELECT * FROM read_parquet(coalesce(getvariable('fct_tickets_path'), 'data/processed/fct_tickets.parquet'))
),
a AS (
    SELECT
        agent_name, agent_group,
        count(*)                                                     AS tickets,
        count(response_sla_met)                                      AS response_evaluable,
        count_if(response_sla_met)                                   AS response_met,
        count(resolution_sla_met)                                    AS resolution_evaluable,
        count_if(resolution_sla_met)                                 AS resolution_met,
        avg(resolution_sla_met::INT) FILTER (WHERE created_half = 'H1') AS resolution_attainment_h1,
        avg(resolution_sla_met::INT) FILTER (WHERE created_half = 'H2') AS resolution_attainment_h2,
        count_if(resolution_outcome = 'Unresolved, overdue')         AS unresolved_overdue,
        median(frt_min) FILTER (WHERE channel_group = 'Live (chat/phone)') AS frt_median_min_live,
        median(frt_min) FILTER (WHERE channel_group = 'Async (email)')     AS frt_median_min_email,
        median(resolution_h)                                         AS resolution_median_h,
        avg(CASE WHEN is_resolved THEN (resolution_h > 48)::INT END) AS share_resolved_over_48h,
        avg(agent_interactions)                                      AS interactions_avg,
        avg(csat_score)                                              AS csat_avg,
        count(csat_score)                                            AS csat_responses
    FROM f
    GROUP BY agent_name, agent_group
)
SELECT
    agent_name, agent_group, tickets,
    tickets / sum(tickets) OVER ()                                   AS share_of_tickets,
    response_met / response_evaluable                                AS response_attainment,
    wilson_lo(response_met, response_evaluable)                      AS response_attainment_lo,
    wilson_hi(response_met, response_evaluable)                      AS response_attainment_hi,
    resolution_met / resolution_evaluable                            AS resolution_attainment,
    wilson_lo(resolution_met, resolution_evaluable)                  AS resolution_attainment_lo,
    wilson_hi(resolution_met, resolution_evaluable)                  AS resolution_attainment_hi,
    resolution_attainment_h1, resolution_attainment_h2,
    resolution_attainment_h2 - resolution_attainment_h1              AS resolution_attainment_change,
    unresolved_overdue / tickets                                     AS unresolved_share,
    frt_median_min_live, frt_median_min_email, resolution_median_h, share_resolved_over_48h,
    interactions_avg, csat_avg, csat_responses
FROM a
ORDER BY agent_group, tickets DESC
