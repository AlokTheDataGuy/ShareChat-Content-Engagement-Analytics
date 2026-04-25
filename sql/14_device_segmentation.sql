-- ============================================================
-- Query: Device Tier Behaviour — Crash Proxy, App Version,
--   Engagement Rate per Device Tier
-- Business Question: Are low-end Android users experiencing
--   meaningfully worse product outcomes? Should we ship a
--   lite version?
-- SQL Techniques: Conditional aggregation, window functions,
--   multi-table join, percentage computation
-- Redshift Notes: Identical. On Redshift, pre-materialise the
--   user_device_sessions CTE as a temp table for large fact scans.
-- Expected Output: 4 rows × 12 cols (one per device tier)
-- Product Decision This Informs: Whether a "ShareChat Lite"
--   investment is justified, Android-Low app optimization
--   priority on engineering roadmap
-- ============================================================

WITH
-- Session-level device metrics
device_sessions AS (
    SELECT
        s.device_type,
        s.app_version,
        s.session_duration_sec,
        s.posts_viewed,
        s.posts_liked,
        s.posts_shared,
        -- "Crash proxy": sessions < 10 seconds (app likely crashed / user quit instantly)
        CASE WHEN s.session_duration_sec < 10 THEN 1 ELSE 0 END AS is_crash_proxy,
        -- "Meaningful session": >60 seconds
        CASE WHEN s.session_duration_sec >= 60 THEN 1 ELSE 0 END AS is_meaningful
    FROM fact_sessions s
    WHERE s.session_end >= s.session_start
      AND s.user_id NOT LIKE 'TEST_%'
),

-- Most common app version per device type
app_version_rank AS (
    SELECT
        device_type,
        app_version,
        COUNT(*) AS version_count,
        ROW_NUMBER() OVER (PARTITION BY device_type ORDER BY COUNT(*) DESC) AS rn
    FROM device_sessions
    GROUP BY 1, 2
),

-- Engagement events per device type (via user join)
device_engagement AS (
    SELECT
        s.device_type,
        COUNT(*)                                                    AS total_events,
        SUM(CASE WHEN fe.event_type = 'view'  THEN 1 ELSE 0 END)   AS views,
        SUM(CASE WHEN fe.event_type = 'like'  THEN 1 ELSE 0 END)   AS likes,
        SUM(CASE WHEN fe.event_type = 'share' THEN 1 ELSE 0 END)   AS shares
    FROM fact_engagement_events fe
    JOIN fact_sessions s
      ON fe.user_id = s.user_id
     AND DATE(fe.event_timestamp) = DATE(s.session_start)
    WHERE fe.user_id NOT LIKE 'TEST_%'
    GROUP BY 1
),

-- Summary by device type
device_summary AS (
    SELECT
        device_type,
        COUNT(*)                                        AS total_sessions,
        SUM(is_crash_proxy)                             AS crash_proxy_sessions,
        SUM(is_meaningful)                              AS meaningful_sessions,
        ROUND(AVG(session_duration_sec), 0)             AS avg_session_sec,
        ROUND(AVG(posts_viewed), 1)                     AS avg_posts_viewed,
        ROUND(AVG(CAST(posts_liked AS REAL)
                  / NULLIF(posts_viewed, 0)) * 100, 3) AS in_session_like_rate_pct
    FROM device_sessions
    GROUP BY 1
)

SELECT
    ds.device_type,
    ds.total_sessions,
    ds.crash_proxy_sessions,
    ROUND(ds.crash_proxy_sessions * 100.0 / ds.total_sessions, 2) AS crash_proxy_pct,
    ds.meaningful_sessions,
    ROUND(ds.meaningful_sessions * 100.0 / ds.total_sessions, 2)  AS meaningful_session_pct,
    ds.avg_session_sec,
    ds.avg_posts_viewed,
    ds.in_session_like_rate_pct,
    COALESCE(av.app_version, 'unknown')                            AS most_common_app_version,
    -- Engagement rate from event log
    ROUND(CAST(de.likes + de.shares AS REAL)
          / NULLIF(de.views, 0) * 100, 3)                         AS event_engagement_rate_pct,
    -- Index vs best-performing device (iOS = 100)
    ROUND(
        ds.avg_session_sec * 100.0
        / MAX(ds.avg_session_sec) OVER (),
    1)                                                             AS session_dur_index
FROM device_summary    ds
LEFT JOIN app_version_rank av ON ds.device_type = av.device_type AND av.rn = 1
LEFT JOIN device_engagement de ON ds.device_type = de.device_type
ORDER BY
    CASE ds.device_type
        WHEN 'Android-Low'  THEN 1
        WHEN 'Android-Mid'  THEN 2
        WHEN 'Android-High' THEN 3
        WHEN 'iOS'          THEN 4
    END;
