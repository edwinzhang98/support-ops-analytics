-- =============================================================================
-- 09_load_vs_sla.sql  ·  Do busy days have worse SLA? (capacity signal test)
-- -----------------------------------------------------------------------------
-- Input : fct_tickets (variable `fct_tickets_path`)
-- Output: one row per day with tickets created and the response / resolution
--         breach rate of that day's tickets, and the number of tickets already
--         open at the start of the day (carried-in workload).
--         If the team were short of capacity, days with more arrivals (or more
--         carried-in work) should show higher breach rates.
-- Run: python -m support_ops.sql sql/09_load_vs_sla.sql
-- =============================================================================
WITH f AS (
    SELECT * FROM read_parquet(coalesce(getvariable('fct_tickets_path'), 'data/processed/fct_tickets.parquet'))
),
daily AS (
    SELECT created_date AS day,
           any_value(is_weekend)                    AS is_weekend,
           count(*)                                 AS tickets,
           avg((NOT response_sla_met)::INT)         AS response_breach_rate,
           avg((NOT resolution_sla_met)::INT)       AS resolution_breach_rate
    FROM f GROUP BY created_date
),
carried AS (   -- active tickets open at 00:00 (excluding never-resolved, which no one is working)
    SELECT d.day,
           count(f.ticket_id) AS open_at_start_active
    FROM daily d
    LEFT JOIN f
      ON f.created_at < CAST(d.day AS TIMESTAMP)
     AND f.resolved_at > CAST(d.day AS TIMESTAMP)
    GROUP BY d.day
)
SELECT d.*, c.open_at_start_active
FROM daily d JOIN carried c USING (day)
ORDER BY day
