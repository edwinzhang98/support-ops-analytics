-- =============================================================================
-- 06_volume_heatmap.sql  ·  Ticket arrivals by day of week x hour of day
-- -----------------------------------------------------------------------------
-- Input : fct_tickets (variable `fct_tickets_path`)
-- Output: 7 x 24 = 168 rows: tickets in 2023, average tickets per week in that
--         slot (tickets / number of that weekday in the export window), share of
--         all tickets, plus channel split.
-- Run: python -m support_ops.sql sql/06_volume_heatmap.sql
-- =============================================================================
WITH f AS (
    SELECT * FROM read_parquet(coalesce(getvariable('fct_tickets_path'), 'data/processed/fct_tickets.parquet'))
),
grid AS (
    SELECT d.dow, h.hour
    FROM range(1, 8) AS d(dow) CROSS JOIN range(0, 24) AS h(hour)
),
weekday_counts AS (   -- how many Mondays, Tuesdays, ... are in the export window
    SELECT isodow(d) AS dow, count(*) AS n_days
    FROM generate_series((SELECT min(created_date) FROM f), (SELECT max(created_date) FROM f), INTERVAL 1 DAY) AS t(d)
    GROUP BY 1
),
cnt AS (
    SELECT created_dow AS dow, created_hour AS hour,
           count(*) AS tickets,
           count_if(channel = 'Email') AS tickets_email,
           count_if(channel = 'Chat')  AS tickets_chat,
           count_if(channel = 'Phone') AS tickets_phone
    FROM f GROUP BY 1, 2
)
SELECT
    g.dow,
    CASE g.dow WHEN 1 THEN 'Mon' WHEN 2 THEN 'Tue' WHEN 3 THEN 'Wed' WHEN 4 THEN 'Thu'
               WHEN 5 THEN 'Fri' WHEN 6 THEN 'Sat' ELSE 'Sun' END     AS dow_name,
    g.hour,
    coalesce(c.tickets, 0)                                           AS tickets,
    coalesce(c.tickets, 0) / w.n_days                                AS tickets_per_week,
    coalesce(c.tickets, 0) / sum(coalesce(c.tickets, 0)) OVER ()     AS share_of_tickets,
    coalesce(c.tickets_email, 0) AS tickets_email,
    coalesce(c.tickets_chat, 0)  AS tickets_chat,
    coalesce(c.tickets_phone, 0) AS tickets_phone
FROM grid g
LEFT JOIN cnt c USING (dow, hour)
JOIN weekday_counts w USING (dow)
ORDER BY g.dow, g.hour
