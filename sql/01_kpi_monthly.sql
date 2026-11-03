-- =============================================================================
-- 01_kpi_monthly.sql  ·  Monthly operations KPI table (cohort = month created)
-- -----------------------------------------------------------------------------
-- Input : fct_tickets (variable `fct_tickets_path`, default data/processed/fct_tickets.parquet)
-- Output: one row per created month with volume, response / resolution SLA
--         attainment (+ Wilson 95% CI), breach composition, speed percentiles, CSAT
-- Definitions: docs/02_metric_definitions.md
-- Run: python -m support_ops.sql sql/01_kpi_monthly.sql
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
m AS (
    SELECT
        created_month,
        count(*)                                                     AS tickets,
        count(*) / count(DISTINCT created_date)                      AS tickets_per_active_day,
        -- response SLA
        count(response_sla_met)                                      AS response_evaluable,
        count_if(response_sla_met)                                   AS response_met,
        -- resolution SLA
        count(resolution_sla_met)                                    AS resolution_evaluable,
        count_if(resolution_sla_met)                                 AS resolution_met,
        count_if(resolution_outcome = 'Resolved late')               AS resolved_late,
        count_if(resolution_outcome = 'Unresolved, overdue')         AS unresolved_overdue,
        count_if(is_resolved)                                        AS resolved,
        -- speed
        median(frt_min) FILTER (WHERE channel_group = 'Live (chat/phone)') AS frt_median_min_live,
        median(frt_min) FILTER (WHERE channel_group = 'Async (email)')     AS frt_median_min_email,
        quantile_cont(frt_min, 0.9) FILTER (WHERE channel_group = 'Async (email)') AS frt_p90_min_email,
        median(resolution_h)                                         AS resolution_median_h,
        quantile_cont(resolution_h, 0.9)                             AS resolution_p90_h,
        avg(CASE WHEN is_resolved THEN (resolution_h > 48)::INT END) AS share_resolved_over_48h,
        -- satisfaction (closed tickets only)
        avg(csat_score)                                              AS csat_avg,
        avg(csat_positive::INT)                                      AS csat_positive_share,
        count(csat_score)                                            AS csat_responses
    FROM f
    GROUP BY created_month
)
SELECT
    created_month,
    tickets,
    round(tickets_per_active_day, 2)                                 AS tickets_per_active_day,
    response_evaluable,
    response_met,
    response_met / response_evaluable                                AS response_attainment,
    wilson_lo(response_met, response_evaluable)                      AS response_attainment_lo,
    wilson_hi(response_met, response_evaluable)                      AS response_attainment_hi,
    resolution_evaluable,
    resolution_met,
    resolution_met / resolution_evaluable                            AS resolution_attainment,
    wilson_lo(resolution_met, resolution_evaluable)                  AS resolution_attainment_lo,
    wilson_hi(resolution_met, resolution_evaluable)                  AS resolution_attainment_hi,
    resolved,
    resolved_late,
    unresolved_overdue,
    resolved_late / resolved                                         AS breach_rate_among_resolved,
    unresolved_overdue / tickets                                     AS unresolved_share,
    frt_median_min_live,
    frt_median_min_email,
    frt_p90_min_email,
    resolution_median_h,
    resolution_p90_h,
    share_resolved_over_48h,
    csat_avg,
    csat_positive_share,
    csat_responses
FROM m
ORDER BY created_month
