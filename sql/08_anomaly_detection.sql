-- ============================================================
-- Query: DAU Anomaly Detection (Trailing 14-Day Z-Score)
-- Business Question: Which days had abnormal user activity
--   that we can't explain by normal festival spikes?
-- SQL Techniques: AVG() OVER, window frame (ROWS BETWEEN),
--   LAG, CASE for classification, join with dim_date
-- Redshift Notes: AVG OVER with ROWS frame is identical.
--   STDDEV() is available in both SQLite (via custom aggregate
--   in Python) and Redshift (native).
-- Expected Output: ~90 rows × 9 cols, anomaly days flagged
-- Product Decision This Informs: Engineering alerts on real
--   anomalies (bug, outage, competitor launch), product team
--   interprets festival spikes vs. organic growth
-- ============================================================

WITH
-- Daily active users
daily_dau AS (
    SELECT
        DATE(session_start)     AS activity_date,
        COUNT(DISTINCT user_id) AS dau,
        COUNT(*)                AS total_sessions,
        AVG(session_duration_sec) AS avg_session_sec
    FROM fact_sessions
    WHERE session_end >= session_start
      AND user_id NOT LIKE 'TEST_%'
    GROUP BY 1
),

-- 14-day trailing window statistics
-- Note: SQLite does not have a native STDDEV window function.
-- We compute variance manually: E[X^2] - E[X]^2
windowed AS (
    SELECT
        activity_date,
        dau,
        total_sessions,
        avg_session_sec,
        -- Trailing 14-day mean (excluding current day)
        AVG(dau) OVER (
            ORDER BY activity_date
            ROWS BETWEEN 14 PRECEDING AND 1 PRECEDING
        )                           AS trailing_14d_mean,
        -- Trailing 14-day variance via E[X^2]-E[X]^2
        AVG(dau * dau) OVER (
            ORDER BY activity_date
            ROWS BETWEEN 14 PRECEDING AND 1 PRECEDING
        ) - POWER(
            AVG(dau) OVER (
                ORDER BY activity_date
                ROWS BETWEEN 14 PRECEDING AND 1 PRECEDING
            ), 2
        )                           AS trailing_14d_variance
        -- Redshift alternative: STDDEV(dau) OVER (ORDER BY activity_date
        --   ROWS BETWEEN 14 PRECEDING AND 1 PRECEDING)
    FROM daily_dau
),

-- Compute z-score and classify
anomalies AS (
    SELECT
        w.activity_date,
        w.dau,
        w.total_sessions,
        ROUND(w.avg_session_sec, 0)                                AS avg_session_sec,
        ROUND(w.trailing_14d_mean, 0)                              AS trailing_14d_mean,
        ROUND(SQRT(CASE WHEN w.trailing_14d_variance > 0 THEN w.trailing_14d_variance ELSE 0 END), 1) AS trailing_14d_stddev,
        -- Z-score: how many std devs from trailing mean
        CASE
            WHEN w.trailing_14d_variance > 0
            THEN ROUND(
                (w.dau - w.trailing_14d_mean)
                / NULLIF(SQRT(w.trailing_14d_variance), 0),
            2)
            ELSE NULL
        END                                                        AS z_score
    FROM windowed w
)

SELECT
    a.activity_date,
    a.dau,
    a.total_sessions,
    a.avg_session_sec,
    a.trailing_14d_mean,
    a.trailing_14d_stddev,
    a.z_score,
    -- Tag as anomaly only if z > 2 AND not explained by a festival
    CASE
        WHEN a.z_score IS NULL THEN 'insufficient_history'
        WHEN ABS(a.z_score) > 2 AND d.is_festival = 1
            THEN 'expected_festival_spike'
        WHEN a.z_score > 2
            THEN 'ANOMALY_HIGH — investigate'
        WHEN a.z_score < -2
            THEN 'ANOMALY_LOW  — investigate'
        ELSE 'normal'
    END                                                            AS anomaly_flag,
    COALESCE(d.festival_name, '')                                  AS festival_name
FROM anomalies         a
LEFT JOIN dim_date     d ON a.activity_date = d.date
ORDER BY a.activity_date;
