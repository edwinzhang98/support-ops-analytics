-- =============================================================================
-- 02_kpi_by_dimension.sql  ·  Efficiency and SLA KPIs broken down by dimension
-- -----------------------------------------------------------------------------
-- Input : fct_tickets (variable `fct_tickets_path`)
-- Output: long table: dimension, segment, tickets, share_of_tickets,
--         response / resolution attainment (+ Wilson 95% CI), speed, CSAT.
--         Dimensions: channel, priority, topic, product_group, agent_group,
--         day_of_week, hour_band, day_type, quarter, half
-- Run: python -m support_ops.sql sql/02_kpi_by_dimension.sql
-- =============================================================================
CREATE OR REPLACE TEMP MACRO wilson_lo(x, n) AS (
    CASE WHEN n > 0 THEN ((x::DOUBLE / n) + 1.96 ^ 2 / (2 * n)
        - 1.96 * sqrt((x::DOUBLE / n) * (1 - x::DOUBLE / n) / n + 1.96 ^ 2 / (4 * n * n))) / (1 + 1.96 ^ 2 / n) END);
CREATE OR REPLACE TEMP MACRO wilson_hi(x, n) AS (
    CASE WHEN n > 0 THEN ((x::DOUBLE / n) + 1.96 ^ 2 / (2 * n)
        + 1.96 * sqrt((x::DOUBLE / n) * (1 - x::DOUBLE / n) / n + 1.96 ^ 2 / (4 * n * n))) / (1 + 1.96 ^ 2 / n) END);

WITH f AS (
    SELECT *,
           created_dow || ' ' || created_dow_name          AS day_of_week,
           CASE WHEN is_weekend THEN 'Weekend' ELSE 'Weekday' END AS day_type
    FROM read_parquet(coalesce(getvariable('fct_tickets_path'), 'data/processed/fct_tickets.parquet'))
),
long AS (
    SELECT 'channel'       AS dimension, channel         AS segment, * FROM f UNION ALL
    SELECT 'priority',                   priority,                   * FROM f UNION ALL
    SELECT 'topic',                      topic,                      * FROM f UNION ALL
    SELECT 'product_group',              product_group,              * FROM f UNION ALL
    SELECT 'agent_group',                agent_group,                * FROM f UNION ALL
    SELECT 'day_of_week',                day_of_week,                * FROM f UNION ALL
    SELECT 'hour_band',                  hour_band,                  * FROM f UNION ALL
    SELECT 'day_type',                   day_type,                   * FROM f UNION ALL
    SELECT 'quarter',                    created_quarter,            * FROM f UNION ALL
    SELECT 'half',                       created_half,               * FROM f
),
agg AS (
    SELECT
        dimension, segment,
        count(*)                                       AS tickets,
        count(response_sla_met)                        AS response_evaluable,
        count_if(response_sla_met)                     AS response_met,
        count(resolution_sla_met)                      AS resolution_evaluable,
        count_if(resolution_sla_met)                   AS resolution_met,
        count_if(resolution_outcome = 'Resolved late')       AS resolved_late,
        count_if(resolution_outcome = 'Unresolved, overdue') AS unresolved_overdue,
        median(frt_min)                                AS frt_median_min,
        median(resolution_h)                           AS resolution_median_h,
        quantile_cont(resolution_h, 0.9)               AS resolution_p90_h,
        avg(CASE WHEN is_resolved THEN (resolution_h > 48)::INT END) AS share_resolved_over_48h,
        avg(agent_interactions)                        AS interactions_avg,
        avg(csat_score)                                AS csat_avg,
        count(csat_score)                              AS csat_responses
    FROM long
    GROUP BY dimension, segment
)
SELECT
    dimension, segment, tickets,
    tickets / sum(tickets) OVER (PARTITION BY dimension)          AS share_of_tickets,
    response_met / response_evaluable                             AS response_attainment,
    wilson_lo(response_met, response_evaluable)                   AS response_attainment_lo,
    wilson_hi(response_met, response_evaluable)                   AS response_attainment_hi,
    resolution_met / resolution_evaluable                         AS resolution_attainment,
    wilson_lo(resolution_met, resolution_evaluable)               AS resolution_attainment_lo,
    wilson_hi(resolution_met, resolution_evaluable)               AS resolution_attainment_hi,
    resolved_late, unresolved_overdue,
    frt_median_min, resolution_median_h, resolution_p90_h, share_resolved_over_48h,
    interactions_avg, csat_avg, csat_responses
FROM agg
ORDER BY dimension, segment
