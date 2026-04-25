-- ============================================================
-- Query: D1 / D7 / D14 / D30 Retention Cohort Matrix
-- Business Question: Of users who signed up in a given week,
--   what % returned on Day 1, 7, 14, and 30?
-- SQL Techniques: CTEs, self-join, conditional aggregation,
--   date arithmetic, cohort analysis pattern
-- Redshift Notes: Replace julianday() difference with
--   DATEDIFF('day', signup_date, activity_date)
-- Expected Output: ~52 rows × 7 cols (one per signup week)
-- Product Decision This Informs: Which acquisition cohorts
--   have weakest early retention — target onboarding changes,
--   benchmark against industry D7 ~20-25% for social apps
-- ============================================================

WITH
-- Assign every user to their signup week cohort
user_cohorts AS (
    SELECT
        user_id,
        signup_date,
        -- Week number of signup (truncate to Monday)
        DATE(signup_date, 'weekday 0', '-6 days') AS cohort_week
    FROM dim_users
    WHERE user_id NOT LIKE 'TEST_%'
      AND signup_date >= DATE('now', '-365 days')
),

-- All (user, date) pairs where user had any session
user_activity_dates AS (
    SELECT DISTINCT
        user_id,
        DATE(session_start) AS activity_date
    FROM fact_sessions
    WHERE session_end >= session_start
      AND user_id NOT LIKE 'TEST_%'
),

-- For each user, compute days between signup and each active day
user_day_offsets AS (
    SELECT
        c.cohort_week,
        c.user_id,
        CAST(julianday(a.activity_date) - julianday(c.signup_date) AS INTEGER) AS day_offset
    -- Redshift: DATEDIFF('day', c.signup_date::DATE, a.activity_date::DATE) AS day_offset
    FROM user_cohorts    c
    JOIN user_activity_dates a ON c.user_id = a.user_id
),

-- Cohort sizes
cohort_sizes AS (
    SELECT cohort_week, COUNT(DISTINCT user_id) AS cohort_size
    FROM user_cohorts
    GROUP BY 1
)

SELECT
    uc.cohort_week,
    cs.cohort_size,
    -- D1: returned within 24 hours
    COUNT(DISTINCT CASE WHEN day_offset = 1 THEN ud.user_id END)              AS d1_retained,
    -- D7: returned on day 6-8 window (±1 day tolerance for real platforms)
    COUNT(DISTINCT CASE WHEN day_offset BETWEEN 6 AND 8 THEN ud.user_id END)  AS d7_retained,
    COUNT(DISTINCT CASE WHEN day_offset BETWEEN 13 AND 15 THEN ud.user_id END) AS d14_retained,
    COUNT(DISTINCT CASE WHEN day_offset BETWEEN 28 AND 32 THEN ud.user_id END) AS d30_retained,
    -- Retention rates
    ROUND(COUNT(DISTINCT CASE WHEN day_offset = 1 THEN ud.user_id END)
          * 100.0 / NULLIF(cs.cohort_size, 0), 2)                             AS d1_retention_pct,
    ROUND(COUNT(DISTINCT CASE WHEN day_offset BETWEEN 6 AND 8 THEN ud.user_id END)
          * 100.0 / NULLIF(cs.cohort_size, 0), 2)                             AS d7_retention_pct,
    ROUND(COUNT(DISTINCT CASE WHEN day_offset BETWEEN 13 AND 15 THEN ud.user_id END)
          * 100.0 / NULLIF(cs.cohort_size, 0), 2)                             AS d14_retention_pct,
    ROUND(COUNT(DISTINCT CASE WHEN day_offset BETWEEN 28 AND 32 THEN ud.user_id END)
          * 100.0 / NULLIF(cs.cohort_size, 0), 2)                             AS d30_retention_pct
FROM user_day_offsets ud
JOIN user_cohorts      uc ON ud.user_id = uc.user_id
JOIN cohort_sizes      cs ON uc.cohort_week = cs.cohort_week
GROUP BY uc.cohort_week, cs.cohort_size
ORDER BY uc.cohort_week;
