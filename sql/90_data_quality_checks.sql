-- =============================================================================
-- 90_data_quality_checks.sql  ·  Sanity checks on the raw export and fct_tickets
-- -----------------------------------------------------------------------------
-- Input : raw CSV (variable `raw_csv_path`) and fct_tickets parquet
--         (variable `fct_tickets_path`, default data/processed/fct_tickets.parquet)
-- Output: one row per check: check_id, area, check_name, observed, expected,
--         status (PASS / FLAG / INFO), action_taken
-- Results are written up in docs/03_data_quality_checks.md
-- Run: python -m support_ops.sql sql/90_data_quality_checks.sql
-- =============================================================================
WITH raw AS (
    SELECT * FROM read_csv(getvariable('raw_csv_path'), header = true)
),
f AS (
    SELECT * FROM read_parquet(coalesce(getvariable('fct_tickets_path'), 'data/processed/fct_tickets.parquet'))
),
checks AS (
    -- 1. Row reconciliation ------------------------------------------------
    SELECT 1 AS check_id, 'Reconciliation' AS area, 'Rows in raw export' AS check_name,
           (SELECT count(*) FROM raw)::DOUBLE AS observed, 2330::DOUBLE AS expected,
           'Matches the dataset documentation (2,330 tickets)' AS action_taken
    UNION ALL
    SELECT 2, 'Reconciliation', 'Rows in fct_tickets minus rows in raw (no rows dropped or duplicated)',
           ((SELECT count(*) FROM f) - (SELECT count(*) FROM raw))::DOUBLE, 0, 'None needed'
    -- 2. Keys --------------------------------------------------------------
    UNION ALL
    SELECT 3, 'Primary key', 'Duplicate Ticket IDs',
           (count(*) - count(DISTINCT "Ticket ID"))::DOUBLE, 0, 'None needed' FROM raw
    UNION ALL
    SELECT 4, 'Primary key', 'Null Ticket IDs', count_if("Ticket ID" IS NULL)::DOUBLE, 0, 'None needed' FROM raw
    UNION ALL
    SELECT 5, 'Primary key', 'Share of IDs present in the ID range (min..max)',
           round(count(*) / (max("Ticket ID") - min("Ticket ID") + 1), 3)::DOUBLE, NULL,
           'INFO: 22% of IDs in range are absent - export may be a subset of all tickets' FROM raw
    -- 3. Time range --------------------------------------------------------
    UNION ALL
    SELECT 6, 'Time range', 'Tickets created outside calendar 2023',
           count_if(year(created_at) <> 2023)::DOUBLE, 0, 'None needed' FROM f
    UNION ALL
    SELECT 7, 'Time range', 'Calendar days in 2023 with zero tickets',
           (365 - count(DISTINCT created_date))::DOUBLE, NULL,
           'INFO: 1 Jan and 31 Dec are outside the export window; 24-26 Dec are holidays; the other 4 (8 Apr, 27 Apr, 27 May, 15 Oct) are low-volume days' FROM f
    UNION ALL
    SELECT 8, 'Time range', 'Hours from last ticket created to snapshot (latest timestamp)',
           round(date_diff('minute', max(created_at), max(snapshot_at)) / 60.0, 1)::DOUBLE, NULL,
           'INFO: snapshot = 2024-01-04 05:39; used to decide if open tickets are overdue' FROM f
    -- 4. Nulls follow the status lifecycle ---------------------------------
    UNION ALL
    SELECT 9, 'Nulls by status', 'First response missing on a ticket that is not Open',
           count_if(first_response_at IS NULL AND status <> 'Open')::DOUBLE, 0, 'None needed' FROM f
    UNION ALL
    SELECT 10, 'Nulls by status', 'Resolution time missing on Resolved/Closed, or present on Open/In progress',
           count_if((resolved_at IS NULL) <> (status IN ('Open', 'In progress')))::DOUBLE, 0, 'None needed' FROM f
    UNION ALL
    SELECT 11, 'Nulls by status', 'Close time present iff status = Closed (violations)',
           count_if((closed_at IS NOT NULL) <> (status = 'Closed'))::DOUBLE, 0, 'None needed' FROM f
    UNION ALL
    SELECT 12, 'Nulls by status', 'CSAT survey present on a ticket that is not Closed',
           count_if(csat_score IS NOT NULL AND status <> 'Closed')::DOUBLE, 0, 'None needed' FROM f
    -- 5. Impossible or suspicious durations -------------------------------
    UNION ALL
    SELECT 13, 'Durations', 'First response before ticket creation',
           count_if(frt_invalid)::DOUBLE, 0,
           'Excluded from response-time metrics and response SLA (2 Phone tickets)' FROM f
    UNION ALL
    SELECT 14, 'Durations', 'Resolved before first response',
           count_if(resolved_before_first_response)::DOUBLE, 0,
           'Kept: resolution metrics still valid; flagged as process/data-entry anomaly' FROM f
    UNION ALL
    SELECT 15, 'Durations', 'Closed before resolved',
           count_if(closed_before_resolved)::DOUBLE, 0,
           'Kept: close time is not used in any SLA metric' FROM f
    UNION ALL
    SELECT 16, 'Durations', 'Max resolution time observed (days)',
           round(max(resolution_h) / 24, 2)::DOUBLE, NULL,
           'INFO: hard ceiling ~6.1 days; basis for 7-day aged-backlog threshold' FROM f
    -- 6. SLA policy and flags ----------------------------------------------
    UNION ALL
    SELECT 17, 'SLA policy', 'Distinct response targets (minutes) by channel - combinations',
           count(DISTINCT channel || '|' || response_target_min)::DOUBLE, 3,
           'Policy inferred: Email 60 min, Chat 2 min, Phone 2 min' FROM f
    UNION ALL
    SELECT 18, 'SLA policy', 'Distinct resolution targets (hours) by channel - combinations',
           count(DISTINCT channel || '|' || resolution_target_h)::DOUBLE, 3,
           'Policy inferred: Chat 24 h, Email 48 h, Phone 48 h' FROM f
    UNION ALL
    SELECT 19, 'SLA policy', 'Distinct response targets within a channel across priorities (should be 1 if priority-independent)',
           max(n)::DOUBLE, 1, 'INFO: targets do not depend on priority' FROM (
               SELECT channel, count(DISTINCT response_target_min) AS n FROM f GROUP BY channel)
    UNION ALL
    SELECT 20, 'SLA flags', 'Raw response flag contradicts timestamps',
           count_if(response_flag_mismatch)::DOUBLE, 0,
           'Recomputed from timestamps; all 14 on 2023-02-18..20 (flagged violated but met)' FROM f
    UNION ALL
    SELECT 21, 'SLA flags', 'Raw resolution flag contradicts timestamps + snapshot',
           count_if(resolution_flag_mismatch)::DOUBLE, 0,
           'Recomputed: ticket 3986 is unresolved and past due at snapshot -> breached' FROM f
    -- 7. Categorical hygiene ----------------------------------------------
    UNION ALL
    SELECT 22, 'Categories', 'Topic labels that differ only by letter case',
           (count(DISTINCT topic_raw) - count(DISTINCT topic))::DOUBLE, 0,
           '"Pricing and Licensing" (68 rows, 6 months only) merged into "Pricing and licensing"' FROM f
    UNION ALL
    SELECT 23, 'Categories', 'Agents assigned to more than one agent group',
           count_if(n > 1)::DOUBLE, 0, 'None needed' FROM (
               SELECT agent_name, count(DISTINCT agent_group) AS n FROM f GROUP BY agent_name)
    UNION ALL
    SELECT 24, 'Categories', 'Tickets where support level and agent group disagree (Tier 1 <-> 1st line)',
           count_if((support_level = 'Tier 1') <> (agent_group = '1st line support'))::DOUBLE, 0,
           'None needed: Support Level is the agent group, not ticket difficulty' FROM f
    UNION ALL
    SELECT 25, 'Categories', 'Countries with more than one coordinate pair',
           count_if(n > 1)::DOUBLE, 0, 'Lat/long are country centroids; dropped (country kept)' FROM (
               SELECT "Country", count(DISTINCT ("Latitude", "Longitude")) AS n FROM raw GROUP BY 1)
    -- 8. Numeric ranges ----------------------------------------------------
    UNION ALL
    SELECT 26, 'Ranges', 'Agent interactions = 60 (outside the 1-10 range of all other tickets)',
           count_if(agent_interactions_raw = 60)::DOUBLE, 0,
           'Treated as sentinel -> NULL (all 45 are Chat); excluded from handle-time calibration' FROM f
    UNION ALL
    SELECT 27, 'Ranges', 'Agent interactions missing',
           count_if(agent_interactions_raw IS NULL)::DOUBLE, NULL, 'INFO: the 18 Open tickets (no agent touch yet)' FROM f
    UNION ALL
    SELECT 28, 'Ranges', 'CSAT outside 1-5',
           count_if(csat_score NOT BETWEEN 1 AND 5)::DOUBLE, 0, 'None needed' FROM f
    -- 9. Known-number cross-checks ----------------------------------------
    UNION ALL
    SELECT 29, 'Cross-check', 'Response SLA met per raw flag (export as delivered)',
           count_if(response_sla_flag_raw = 'Within SLA')::DOUBLE, NULL,
           'INFO: 2,019 raw vs 2,031 recomputed (+14 mis-flags, -2 invalid)' FROM f
    UNION ALL
    SELECT 30, 'Cross-check', 'Resolution SLA met per raw flag (export as delivered)',
           count_if(resolution_sla_flag_raw = 'Within SLA')::DOUBLE, NULL,
           'INFO: 1,547 raw vs 1,546 recomputed' FROM f
)
SELECT
    check_id, area, check_name, observed, expected,
    CASE WHEN expected IS NULL THEN 'INFO'
         WHEN observed = expected THEN 'PASS'
         ELSE 'FLAG' END AS status,
    action_taken
FROM checks
ORDER BY check_id
