-- =============================================================================
-- 08_rca_decomposition.sql  ·  Did the SLA fall because the MIX changed or the RATE?
-- -----------------------------------------------------------------------------
-- Input : fct_tickets (variable `fct_tickets_path`)
-- Output: shift-share decomposition of the change in attainment between
--         two periods (H1 -> H2 and Q1 -> Q4), for response and resolution SLA,
--         by segment dimension (channel, topic, priority, agent_group):
--           mix_effect  = (w2 - w1) * (a1 + a2) / 2   (segment got bigger/smaller)
--           rate_effect = (a2 - a1) * (w1 + w2) / 2   (segment got better/worse)
--         Summed over segments, mix + rate = total change exactly.
-- Run: python -m support_ops.sql sql/08_rca_decomposition.sql
-- =============================================================================
WITH f AS (
    SELECT * FROM read_parquet(coalesce(getvariable('fct_tickets_path'), 'data/processed/fct_tickets.parquet'))
),
tagged AS (   -- each ticket can belong to both comparisons
    SELECT 'H1 -> H2' AS comparison, CASE WHEN created_half = 'H1' THEN 1 ELSE 2 END AS period, * FROM f
    UNION ALL
    SELECT 'Q1 -> Q4', CASE WHEN created_quarter = 'Q1' THEN 1 ELSE 2 END, * FROM f
    WHERE created_quarter IN ('Q1', 'Q4')
),
sla AS (
    SELECT 'response' AS sla_type, comparison, period, channel, topic, priority, agent_group,
           response_sla_met::INT AS met
    FROM tagged WHERE response_sla_met IS NOT NULL
    UNION ALL
    SELECT 'resolution', comparison, period, channel, topic, priority, agent_group,
           resolution_sla_met::INT
    FROM tagged WHERE resolution_sla_met IS NOT NULL
),
seg AS (
    SELECT sla_type, comparison, 'channel' AS dimension, channel AS segment, period, count(*) AS n, avg(met) AS a FROM sla GROUP BY ALL
    UNION ALL
    SELECT sla_type, comparison, 'topic', topic, period, count(*), avg(met) FROM sla GROUP BY ALL
    UNION ALL
    SELECT sla_type, comparison, 'priority', priority, period, count(*), avg(met) FROM sla GROUP BY ALL
    UNION ALL
    SELECT sla_type, comparison, 'agent_group', agent_group, period, count(*), avg(met) FROM sla GROUP BY ALL
),
wide AS (
    SELECT sla_type, comparison, dimension, segment,
        max(n) FILTER (WHERE period = 1) AS n1,
        max(n) FILTER (WHERE period = 2) AS n2,
        max(a) FILTER (WHERE period = 1) AS a1,
        max(a) FILTER (WHERE period = 2) AS a2
    FROM seg GROUP BY ALL
),
weighted AS (
    SELECT *,
        n1 / sum(n1) OVER (PARTITION BY sla_type, comparison, dimension) AS w1,
        n2 / sum(n2) OVER (PARTITION BY sla_type, comparison, dimension) AS w2
    FROM wide
)
SELECT
    sla_type, comparison, dimension, segment,
    n1, n2, w1, w2, a1, a2,
    (w2 - w1) * (a1 + a2) / 2  AS mix_effect,
    (a2 - a1) * (w1 + w2) / 2  AS rate_effect
FROM weighted
ORDER BY sla_type, comparison, dimension, segment
