-- =============================================================================
-- 07_topic_pareto.sql  ·  Pareto of ticket categories
-- -----------------------------------------------------------------------------
-- Input : fct_tickets (variable `fct_tickets_path`)
-- Output: two levels in one long table:
--         level = 'topic'           (7 categories)
--         level = 'topic x product' (topic x product group, 24 non-empty cells)
--         with tickets, share, cumulative share, rank and rank percentile
--         (rank_pct <= 0.20 = "top 20% of categories").
-- Run: python -m support_ops.sql sql/07_topic_pareto.sql
-- =============================================================================
WITH f AS (
    SELECT * FROM read_parquet(coalesce(getvariable('fct_tickets_path'), 'data/processed/fct_tickets.parquet'))
),
cats AS (
    SELECT 'topic' AS level, topic AS category, count(*) AS tickets,
           median(agent_interactions) AS interactions_median,
           avg((agent_group = '2nd line support')::INT) AS tier2_share
    FROM f GROUP BY topic
    UNION ALL
    SELECT 'topic x product', topic || ' | ' || product_group, count(*),
           median(agent_interactions), avg((agent_group = '2nd line support')::INT)
    FROM f GROUP BY topic, product_group
),
ranked AS (
    SELECT *,
        row_number() OVER (PARTITION BY level ORDER BY tickets DESC, category) AS rank,
        count(*)     OVER (PARTITION BY level)                                 AS n_categories,
        tickets / sum(tickets) OVER (PARTITION BY level)                       AS share
    FROM cats
)
SELECT
    level, category, tickets, share,
    sum(share) OVER (PARTITION BY level ORDER BY rank ROWS UNBOUNDED PRECEDING) AS cum_share,
    rank, n_categories,
    rank / n_categories                                                         AS rank_pct,
    interactions_median, tier2_share
FROM ranked
ORDER BY level, rank
