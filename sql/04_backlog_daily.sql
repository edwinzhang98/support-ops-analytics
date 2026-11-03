-- =============================================================================
-- 04_backlog_daily.sql  ·  Daily open backlog (end of day), split by age
-- -----------------------------------------------------------------------------
-- Input : fct_tickets (variable `fct_tickets_path`);
--         aged threshold in days (variable `aged_backlog_days`, default 7)
-- Output: one row per calendar day 2023-01-02 .. snapshot date:
--         arrivals, resolutions, open backlog at 23:59:59 split into
--         0-2 days old / 2 days-threshold / aged (> threshold), and how many of the
--         open tickets are never resolved by the snapshot.
-- A ticket is open at time t if created_at <= t and (resolved_at > t or never resolved).
-- Run: python -m support_ops.sql sql/04_backlog_daily.sql
-- =============================================================================
WITH f AS (
    SELECT * FROM read_parquet(coalesce(getvariable('fct_tickets_path'), 'data/processed/fct_tickets.parquet'))
),
params AS (
    SELECT coalesce(getvariable('aged_backlog_days')::DOUBLE, 7.0) AS aged_days
),
days AS (
    SELECT CAST(d AS DATE) AS day,
           CAST(d AS TIMESTAMP) + INTERVAL 1 DAY - INTERVAL 1 MICROSECOND AS day_end
    FROM generate_series(
        (SELECT min(created_date) FROM f),
        (SELECT CAST(max(snapshot_at) AS DATE) FROM f),
        INTERVAL 1 DAY) AS t(d)
),
flows AS (
    SELECT d.day,
        (SELECT count(*) FROM f WHERE f.created_date = d.day)                      AS arrivals,
        (SELECT count(*) FROM f WHERE CAST(f.resolved_at AS DATE) = d.day)         AS resolutions
    FROM days d
),
open_at_day_end AS (
    SELECT
        d.day,
        count(f.ticket_id)                                                          AS open_total,
        count_if(date_diff('second', f.created_at, d.day_end) / 86400.0 <= 2)       AS open_0_2d,
        count_if(date_diff('second', f.created_at, d.day_end) / 86400.0 > 2
             AND date_diff('second', f.created_at, d.day_end) / 86400.0 <= p.aged_days) AS open_2d_to_threshold,
        count_if(date_diff('second', f.created_at, d.day_end) / 86400.0 > p.aged_days)  AS open_aged,
        count_if(f.resolved_at IS NULL)                                             AS open_never_resolved
    FROM days d
    CROSS JOIN params p
    LEFT JOIN f
      ON f.created_at <= d.day_end
     AND (f.resolved_at IS NULL OR f.resolved_at > d.day_end)
    GROUP BY d.day
)
SELECT
    o.day,
    fl.arrivals,
    fl.resolutions,
    fl.arrivals - fl.resolutions                AS net_flow,
    o.open_total,
    o.open_0_2d,
    o.open_2d_to_threshold,
    o.open_aged,
    o.open_never_resolved,
    o.open_total - o.open_aged                  AS open_active
FROM open_at_day_end o
JOIN flows fl USING (day)
ORDER BY o.day
