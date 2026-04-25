-- ============================================================
-- Query: Session Depth Distribution by Device Type
-- Business Question: How do session length distributions
--   differ across device tiers, and where is the UX breaking?
-- SQL Techniques: CASE WHEN bucketing, conditional aggregation,
--   window functions for % within group, histogram construction
-- Redshift Notes: Identical. On Redshift, CASE WHEN bucketing
--   is standard, consider WIDTH_BUCKET() for auto-generated bins.
-- Expected Output: 20 rows × 8 cols (5 buckets × 4 device types)
-- Product Decision This Informs: Engineering prioritises APK
--   size and cold-start time for Android-Low, content team
--   knows that short-session users on low-end Android need
--   faster-loading formats (images over video)
-- ============================================================

WITH
-- Assign each session to a depth bucket
session_bucketed AS (
    SELECT
        s.session_id,
        s.user_id,
        s.device_type,
        s.session_duration_sec,
        s.posts_viewed,
        -- Depth bucket by time
        CASE
            WHEN s.session_duration_sec < 60    THEN '1. Under 1 min'
            WHEN s.session_duration_sec < 300   THEN '2. 1-5 min'
            WHEN s.session_duration_sec < 900   THEN '3. 5-15 min'
            WHEN s.session_duration_sec < 1800  THEN '4. 15-30 min'
            ELSE                                     '5. 30+ min'
        END AS duration_bucket,
        -- Depth bucket by posts viewed
        CASE
            WHEN s.posts_viewed <= 5   THEN 'shallow (≤5 posts)'
            WHEN s.posts_viewed <= 20  THEN 'medium (6-20 posts)'
            ELSE                            'deep (20+ posts)'
        END AS depth_bucket
    FROM fact_sessions s
    WHERE s.session_end >= s.session_start
      AND s.session_duration_sec > 0
      AND s.user_id NOT LIKE 'TEST_%'
),

-- Count within each device × time-bucket combination
device_bucket_counts AS (
    SELECT
        device_type,
        duration_bucket,
        COUNT(*)                            AS session_count,
        AVG(session_duration_sec)           AS avg_dur_in_bucket,
        AVG(posts_viewed)                   AS avg_posts_viewed,
        -- % of very-short sessions (<60s) as crash/bail proxy
        SUM(CASE WHEN session_duration_sec < 10 THEN 1 ELSE 0 END)
                                            AS crash_proxy_count
    FROM session_bucketed
    GROUP BY 1, 2
),

-- Totals per device type for percentage calculation
device_totals AS (
    SELECT device_type, COUNT(*) AS total_sessions
    FROM session_bucketed
    GROUP BY 1
)

SELECT
    dc.device_type,
    dc.duration_bucket,
    dc.session_count,
    ROUND(dc.session_count * 100.0 / dt.total_sessions, 2)  AS pct_of_device_sessions,
    ROUND(dc.avg_dur_in_bucket, 0)                           AS avg_dur_sec,
    ROUND(dc.avg_posts_viewed, 1)                            AS avg_posts_viewed,
    dc.crash_proxy_count,
    dt.total_sessions                                        AS device_total_sessions
FROM device_bucket_counts dc
JOIN device_totals         dt ON dc.device_type = dt.device_type
ORDER BY
    CASE dc.device_type
        WHEN 'Android-Low'  THEN 1
        WHEN 'Android-Mid'  THEN 2
        WHEN 'Android-High' THEN 3
        WHEN 'iOS'          THEN 4
    END,
    dc.duration_bucket;
