-- =============================================================================
-- 03_breach_hotspots.sql  ·  Where are SLA breaches concentrated?
-- -----------------------------------------------------------------------------
-- Input : fct_tickets (variable `fct_tickets_path`)
-- Output: one row per (sla_type, 1-, 2- or 3-way combination of dimensions) with
--         n >= 30 tickets: breach rate, Wilson 95% CI, overall rate, lift and
--         "excess breaches" = breaches above what the overall rate predicts.
--         Multiple-testing correction (Benjamini-Hochberg) is applied in Python
--         (support_ops/kpis.py) because it needs a sorted rank of p-values.
-- Dimensions: day_of_week, hour_band, channel, priority, topic, agent_group, product_group
-- Run: python -m support_ops.sql sql/03_breach_hotspots.sql
-- =============================================================================
CREATE OR REPLACE TEMP MACRO wilson_lo(x, n) AS (
    CASE WHEN n > 0 THEN ((x::DOUBLE / n) + 1.96 ^ 2 / (2 * n)
        - 1.96 * sqrt((x::DOUBLE / n) * (1 - x::DOUBLE / n) / n + 1.96 ^ 2 / (4 * n * n))) / (1 + 1.96 ^ 2 / n) END);
CREATE OR REPLACE TEMP MACRO wilson_hi(x, n) AS (
    CASE WHEN n > 0 THEN ((x::DOUBLE / n) + 1.96 ^ 2 / (2 * n)
        + 1.96 * sqrt((x::DOUBLE / n) * (1 - x::DOUBLE / n) / n + 1.96 ^ 2 / (4 * n * n))) / (1 + 1.96 ^ 2 / n) END);

WITH f AS (
    SELECT created_dow_name AS day_of_week, hour_band, channel, priority, topic, agent_group, product_group,
           response_sla_met, resolution_sla_met
    FROM read_parquet(coalesce(getvariable('fct_tickets_path'), 'data/processed/fct_tickets.parquet'))
),
sla AS (
    SELECT 'response' AS sla_type, *, NOT response_sla_met AS breached FROM f WHERE response_sla_met IS NOT NULL
    UNION ALL
    SELECT 'resolution', *, NOT resolution_sla_met FROM f WHERE resolution_sla_met IS NOT NULL
),
overall AS (
    SELECT sla_type, avg(breached::INT) AS overall_rate FROM sla GROUP BY sla_type
),
cube AS (
    SELECT
        sla_type, day_of_week, hour_band, channel, priority, topic, agent_group, product_group,
        GROUPING(day_of_week, hour_band, channel, priority, topic, agent_group, product_group) AS gid,
        count(*)            AS n,
        count_if(breached)  AS breaches
    FROM sla
    GROUP BY sla_type, CUBE (day_of_week, hour_band, channel, priority, topic, agent_group, product_group)
),
labelled AS (
    SELECT *,
        -- number of dimensions in the combination = 7 - bits set in the grouping id
        7 - bit_count(gid::INTEGER)                                AS n_dims,
        concat_ws(' + ',
            day_of_week, hour_band, channel, priority || ' priority',
            CASE WHEN topic = 'Other' THEN 'Other topic' ELSE topic END, agent_group,
            CASE WHEN product_group = 'Other' THEN 'Other product' ELSE product_group END) AS combination
    FROM cube
)
SELECT
    l.sla_type, l.n_dims, l.combination,
    l.day_of_week, l.hour_band, l.channel, l.priority, l.topic, l.agent_group, l.product_group,
    l.n, l.breaches,
    l.breaches / l.n                                     AS breach_rate,
    wilson_lo(l.breaches, l.n)                           AS breach_rate_lo,
    wilson_hi(l.breaches, l.n)                           AS breach_rate_hi,
    o.overall_rate,
    (l.breaches / l.n) / o.overall_rate                  AS lift,
    l.breaches - l.n * o.overall_rate                    AS excess_breaches
FROM labelled l
JOIN overall o USING (sla_type)
WHERE l.n_dims BETWEEN 1 AND 3
  AND l.n >= 30
ORDER BY l.sla_type, excess_breaches DESC, l.combination
