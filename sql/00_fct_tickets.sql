-- =============================================================================
-- 00_fct_tickets.sql  ·  Clean the raw export into one row per ticket
-- -----------------------------------------------------------------------------
-- Input : raw CSV export, path in DuckDB variable `raw_csv_path`
--         (pipeline sets it from config.yaml / .env)
-- Output: fct_tickets, one row per Ticket ID, snake_case, with SLA outcomes
--         recomputed from timestamps (the raw flags disagree on 15 tickets;
--         see docs/03_data_quality_checks.md)
-- Grain : ticket
-- Run standalone (from repo root, DuckDB CLI):
--   duckdb -c "SET VARIABLE raw_csv_path='/path/Technical Support Dataset.csv'" \
--          -c ".read sql/00_fct_tickets.sql"
-- or: python -m support_ops.sql sql/00_fct_tickets.sql
-- Rules applied (each documented in docs/02_metric_definitions.md):
--   * Topic labels normalised to sentence case ("Pricing and Licensing" -> "Pricing and licensing")
--   * agent_interactions = 60 treated as invalid (sentinel) -> NULL; raw value kept
--   * First response before creation (2 tickets) -> frt invalid -> response SLA not evaluated
--   * Snapshot = latest timestamp anywhere in the export; open tickets past due at snapshot = breached
-- =============================================================================
WITH raw AS (
    SELECT *
    FROM read_csv(getvariable('raw_csv_path'), header = true)
),

snapshot AS (
    SELECT greatest(
               max("Created time"), max("First response time"),
               max("Resolution time"), max("Close time")
           ) AS snapshot_at
    FROM raw
),

stg AS (
    SELECT
        "Ticket ID"::BIGINT                                     AS ticket_id,
        "Status"                                                AS status,
        "Priority"                                              AS priority,
        "Source"                                                AS channel,
        -- sentence case: first letter upper, rest lower
        upper(left(trim("Topic"), 1)) || lower(substr(trim("Topic"), 2)) AS topic,
        trim("Topic")                                           AS topic_raw,
        "Product group"                                         AS product_group,
        "Support Level"                                         AS support_level,
        "Agent Group"                                           AS agent_group,
        "Agent Name"                                            AS agent_name,
        "Country"                                               AS country,
        "Created time"                                          AS created_at,
        "Expected SLA to first response"                        AS response_due_at,
        "First response time"                                   AS first_response_at,
        "Expected SLA to resolve"                               AS resolution_due_at,
        "Resolution time"                                       AS resolved_at,
        "Close time"                                            AS closed_at,
        "SLA For first response"                                AS response_sla_flag_raw,
        "SLA For Resolution"                                    AS resolution_sla_flag_raw,
        "Agent interactions"::INTEGER                           AS agent_interactions_raw,
        CASE WHEN "Agent interactions" = 60 THEN NULL
             ELSE "Agent interactions"::INTEGER END             AS agent_interactions,
        "Survey results"::INTEGER                               AS csat_score
    FROM raw
),

durations AS (
    SELECT
        s.*,
        n.snapshot_at,
        date_diff('second', created_at, response_due_at) / 60.0       AS response_target_min,
        date_diff('second', created_at, resolution_due_at) / 3600.0   AS resolution_target_h,
        date_diff('millisecond', created_at, first_response_at) / 60000.0     AS frt_min_raw,
        date_diff('millisecond', created_at, resolved_at) / 3600000.0         AS resolution_h,
        date_diff('millisecond', created_at, closed_at) / 3600000.0           AS close_h,
        date_diff('millisecond', created_at, n.snapshot_at) / 86400000.0      AS age_at_snapshot_days
    FROM stg s CROSS JOIN snapshot n
)

SELECT
    ticket_id,
    status,
    priority,
    channel,
    CASE WHEN channel IN ('Chat', 'Phone') THEN 'Live (chat/phone)' ELSE 'Async (email)' END AS channel_group,
    topic,
    topic_raw,
    product_group,
    support_level,
    agent_group,
    agent_name,
    country,

    -- timestamps
    created_at,
    response_due_at,
    first_response_at,
    resolution_due_at,
    resolved_at,
    closed_at,
    snapshot_at,

    -- calendar attributes of creation time
    CAST(created_at AS DATE)                                  AS created_date,
    CAST(date_trunc('month', created_at) AS DATE)             AS created_month,
    'Q' || quarter(created_at)                                AS created_quarter,
    CASE WHEN month(created_at) <= 6 THEN 'H1' ELSE 'H2' END  AS created_half,
    isodow(created_at)                                        AS created_dow,      -- 1 = Mon ... 7 = Sun
    strftime(created_at, '%a')                                AS created_dow_name,
    hour(created_at)                                          AS created_hour,
    CASE WHEN hour(created_at) < 6  THEN '00-06 Night'
         WHEN hour(created_at) < 12 THEN '06-12 Morning'
         WHEN hour(created_at) < 18 THEN '12-18 Afternoon'
         ELSE '18-24 Evening' END                             AS hour_band,
    isodow(created_at) >= 6                                   AS is_weekend,

    -- targets (policy observed in the data: depend on channel only)
    response_target_min,
    resolution_target_h,

    -- durations
    CASE WHEN frt_min_raw >= 0 THEN frt_min_raw END           AS frt_min,
    frt_min_raw < 0                                           AS frt_invalid,
    resolution_h,
    close_h,
    age_at_snapshot_days,
    resolved_at IS NOT NULL                                   AS is_resolved,

    -- RESPONSE SLA (recomputed). NULL = not evaluable (invalid timestamp or not yet due)
    CASE
        WHEN first_response_at IS NULL AND response_due_at <= snapshot_at THEN FALSE
        WHEN first_response_at IS NULL THEN NULL
        WHEN frt_min_raw < 0 THEN NULL
        ELSE first_response_at <= response_due_at
    END                                                       AS response_sla_met,

    -- RESOLUTION SLA (recomputed). Unresolved and past due at snapshot = breached
    CASE
        WHEN resolved_at IS NULL AND resolution_due_at <= snapshot_at THEN FALSE
        WHEN resolved_at IS NULL THEN NULL
        ELSE resolved_at <= resolution_due_at
    END                                                       AS resolution_sla_met,

    CASE
        WHEN resolved_at IS NOT NULL AND resolved_at <= resolution_due_at THEN 'Resolved within SLA'
        WHEN resolved_at IS NOT NULL THEN 'Resolved late'
        WHEN resolution_due_at <= snapshot_at THEN 'Unresolved, overdue'
        ELSE 'Unresolved, not yet due'
    END                                                       AS resolution_outcome,

    -- raw flags kept for reconciliation
    response_sla_flag_raw,
    resolution_sla_flag_raw,
    (response_sla_flag_raw = 'Within SLA') IS DISTINCT FROM (
        CASE WHEN first_response_at IS NULL AND response_due_at <= snapshot_at THEN FALSE
             WHEN first_response_at IS NULL OR frt_min_raw < 0 THEN NULL
             ELSE first_response_at <= response_due_at END
    ) AND frt_min_raw >= 0                                    AS response_flag_mismatch,
    (resolution_sla_flag_raw = 'Within SLA') IS DISTINCT FROM (
        CASE WHEN resolved_at IS NULL AND resolution_due_at <= snapshot_at THEN FALSE
             WHEN resolved_at IS NULL THEN NULL
             ELSE resolved_at <= resolution_due_at END
    )                                                         AS resolution_flag_mismatch,

    -- workload and satisfaction
    agent_interactions,
    agent_interactions_raw,
    csat_score,
    csat_score >= 4                                           AS csat_positive,

    -- timestamp sanity flags
    resolved_at < first_response_at                           AS resolved_before_first_response,
    closed_at < resolved_at                                   AS closed_before_resolved
FROM durations
ORDER BY ticket_id
