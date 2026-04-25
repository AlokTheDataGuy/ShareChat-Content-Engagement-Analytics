-- ============================================================
-- Query: RFM-Style User Segmentation
-- Business Question: Which users are Champions vs. At Risk
--   vs. Lost, and what does each segment look like?
-- SQL Techniques: NTILE(5) for quantile bucketing, CASE WHEN
--   for segment labelling, multi-CTE pattern, LAG/window
-- Redshift Notes: Identical, NTILE is ANSI standard.
--   On Redshift, add DISTKEY(user_id) to the intermediate
--   CTE materialisation to avoid data shuffling.
-- Expected Output: 7 rows × 9 cols (one per segment)
-- Product Decision This Informs: Retention team targets At-Risk
--   and Promising users for win-back campaigns, Champions get
--   creator program invitations, Hibernating get re-engagement push
-- ============================================================

WITH
-- Recency: days since last session (lower = better for R score)
-- Frequency: distinct session days in last 30 days
-- Monetary: total watch time (minutes) in last 30 days
user_rfm_raw AS (
    SELECT
        s.user_id,
        u.signup_language,
        u.city_tier,
        u.device_type,
        u.experiment_group,
        -- Recency: days since last session
        CAST(julianday('now') - julianday(MAX(DATE(s.session_start))) AS INTEGER)
            AS recency_days,
        -- Frequency: distinct days with ≥1 session in last 30 days
        COUNT(DISTINCT CASE
            WHEN s.session_start >= DATE('now', '-30 days')
            THEN DATE(s.session_start)
        END)                                                             AS frequency_days,
        -- Monetary: total session minutes in last 30 days
        SUM(CASE
            WHEN s.session_start >= DATE('now', '-30 days')
            THEN s.session_duration_sec / 60.0
            ELSE 0
        END)                                                             AS total_watch_min
    FROM fact_sessions s
    JOIN dim_users u ON s.user_id = u.user_id
    WHERE s.session_end >= s.session_start
      AND s.user_id NOT LIKE 'TEST_%'
    GROUP BY 1, 2, 3, 4, 5
),

-- RFM scores: NTILE(5) within each dimension
rfm_scored AS (
    SELECT
        *,
        -- R score: 5 = most recent (1 day ago), 1 = oldest
        NTILE(5) OVER (ORDER BY recency_days  ASC)   AS r_score,
        -- F score: 5 = most frequent
        NTILE(5) OVER (ORDER BY frequency_days DESC) AS f_score,
        -- M score: 5 = highest watch time
        NTILE(5) OVER (ORDER BY total_watch_min DESC) AS m_score
    FROM user_rfm_raw
),

-- Assign named segment based on R+F combination
segmented AS (
    SELECT
        *,
        (r_score + f_score + m_score) AS rfm_total,
        CASE
            WHEN r_score >= 4 AND f_score >= 4                       THEN 'Champions'
            WHEN r_score >= 3 AND f_score >= 3 AND m_score >= 3      THEN 'Loyal Users'
            WHEN r_score >= 4 AND f_score <= 2                       THEN 'Recent Users'
            WHEN r_score BETWEEN 2 AND 3 AND f_score >= 3            THEN 'Promising'
            WHEN r_score <= 2 AND f_score >= 3                       THEN 'At Risk'
            WHEN r_score <= 2 AND f_score BETWEEN 2 AND 3            THEN 'Hibernating'
            ELSE                                                           'Lost'
        END AS segment
    FROM rfm_scored
)

-- Segment summary (the deliverable for the PM)
SELECT
    segment,
    COUNT(*)                                        AS user_count,
    ROUND(COUNT(*) * 100.0 / SUM(COUNT(*)) OVER (), 1) AS pct_of_users,
    ROUND(AVG(recency_days), 1)                     AS avg_recency_days,
    ROUND(AVG(frequency_days), 1)                   AS avg_active_days_30d,
    ROUND(AVG(total_watch_min), 0)                  AS avg_watch_min_30d,
    ROUND(AVG(rfm_total), 2)                        AS avg_rfm_score,
    -- City tier breakdown within segment
    ROUND(SUM(CASE WHEN city_tier = 'Tier-1' THEN 1.0 ELSE 0 END)
          / COUNT(*) * 100, 1)                      AS pct_tier1,
    ROUND(SUM(CASE WHEN city_tier IN ('Tier-3','Tier-4') THEN 1.0 ELSE 0 END)
          / COUNT(*) * 100, 1)                      AS pct_tier3_4
FROM segmented
GROUP BY segment
ORDER BY avg_rfm_score DESC;
