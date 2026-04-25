-- ============================================================
-- Query: Daily / Weekly / Monthly Active Users + Stickiness
-- Business Question: What is our DAU, WAU, MAU and how sticky
--   is the platform week-over-week?
-- SQL Techniques: CTEs, window functions (LAG, AVG OVER),
--   subqueries, date arithmetic
-- Redshift Notes: Replace julianday() with DATEDIFF('day',...)
--   Replace strftime() with TO_CHAR() or DATE_TRUNC()
-- Expected Output: ~90 rows × 8 cols (one per active day)
-- Product Decision This Informs: Whether platform growth is
--   healthy, flag days needing investigation (DAU drops),
--   input to retention deep-dives
-- ============================================================

WITH
-- Distinct active users per calendar day
daily_active AS (
    SELECT
        DATE(session_start)              AS activity_date,
        COUNT(DISTINCT user_id)          AS dau
    FROM fact_sessions
    WHERE session_start >= DATE('now', '-90 days')
      AND session_end >= session_start          -- exclude bad-duration rows
      AND user_id NOT LIKE 'TEST_%'
    GROUP BY 1
),

-- MAU window: rolling 28-day unique users ending on each day
-- SQLite: use julianday arithmetic, Redshift: use DATEDIFF + window frame
monthly_active AS (
    SELECT
        d1.activity_date,
        COUNT(DISTINCT s.user_id) AS mau
    FROM daily_active d1
    JOIN fact_sessions s
      ON DATE(s.session_start) BETWEEN DATE(d1.activity_date, '-27 days')
                                    AND d1.activity_date
     AND s.user_id NOT LIKE 'TEST_%'
    GROUP BY 1
),

-- WAU window: rolling 7-day unique users
weekly_active AS (
    SELECT
        d1.activity_date,
        COUNT(DISTINCT s.user_id) AS wau
    FROM daily_active d1
    JOIN fact_sessions s
      ON DATE(s.session_start) BETWEEN DATE(d1.activity_date, '-6 days')
                                    AND d1.activity_date
     AND s.user_id NOT LIKE 'TEST_%'
    GROUP BY 1
),

-- 7-day rolling average of DAU
rolling_dau AS (
    SELECT
        activity_date,
        dau,
        AVG(dau) OVER (
            ORDER BY activity_date
            ROWS BETWEEN 6 PRECEDING AND CURRENT ROW
        ) AS dau_7d_avg
    FROM daily_active
)

SELECT
    r.activity_date,
    r.dau,
    ROUND(r.dau_7d_avg, 0)                                   AS dau_7d_rolling_avg,
    w.wau,
    m.mau,
    -- Stickiness: what % of monthly users come back daily
    ROUND(CAST(r.dau AS REAL) / NULLIF(m.mau, 0) * 100, 2)  AS stickiness_pct,
    -- DAU day-over-day change
    LAG(r.dau) OVER (ORDER BY r.activity_date)               AS prev_day_dau,
    ROUND(
        (r.dau - LAG(r.dau) OVER (ORDER BY r.activity_date)) * 100.0
        / NULLIF(LAG(r.dau) OVER (ORDER BY r.activity_date), 0),
    2)                                                        AS dau_dod_pct_change
FROM rolling_dau      r
JOIN weekly_active    w ON r.activity_date = w.activity_date
JOIN monthly_active   m ON r.activity_date = m.activity_date
ORDER BY r.activity_date;
