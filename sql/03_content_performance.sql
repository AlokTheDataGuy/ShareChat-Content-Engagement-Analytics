-- ============================================================
-- Query: Engagement Rate by Language × Content Category
-- Business Question: Which content categories over- or
--   under-perform in each language, and how do they rank
--   within their language cohort?
-- SQL Techniques: CTEs, PERCENT_RANK() window function,
--   NTILE(), conditional aggregation, multi-dimensional GROUP BY
-- Redshift Notes: Identical syntax — PERCENT_RANK() is ANSI SQL
--   and supported natively in Redshift
-- Expected Output: ~48 rows × 9 cols (12 languages × 9 categories,
--   sparse where combinations don't exist)
-- Product Decision This Informs: Content team knows which
--   category-language combos to invest creator incentives in,
--   PM can prioritise feed algorithm tuning per language
-- ============================================================

WITH
-- Count events by type per post
post_events AS (
    SELECT
        post_id,
        COUNT(*)                                                   AS total_events,
        SUM(CASE WHEN event_type = 'view'    THEN 1 ELSE 0 END)   AS views,
        SUM(CASE WHEN event_type = 'like'    THEN 1 ELSE 0 END)   AS likes,
        SUM(CASE WHEN event_type = 'share'   THEN 1 ELSE 0 END)   AS shares,
        SUM(CASE WHEN event_type = 'comment' THEN 1 ELSE 0 END)   AS comments,
        SUM(CASE WHEN event_type = 'follow'  THEN 1 ELSE 0 END)   AS follows
    FROM fact_engagement_events
    WHERE user_id NOT LIKE 'TEST_%'
    GROUP BY 1
),

-- Join with content metadata
content_stats AS (
    SELECT
        c.language,
        cr.content_category,
        COUNT(DISTINCT c.post_id)                       AS post_count,
        SUM(pe.views)                                   AS total_views,
        SUM(pe.likes + pe.shares + pe.comments)         AS total_engagements,
        -- Engagement rate: (likes + shares + comments) / views
        ROUND(
            CAST(SUM(pe.likes + pe.shares + pe.comments) AS REAL)
            / NULLIF(SUM(pe.views), 0) * 100, 3
        )                                               AS engagement_rate_pct,
        ROUND(AVG(pe.views), 0)                         AS avg_views_per_post,
        -- Share rate specifically (virality proxy)
        ROUND(
            CAST(SUM(pe.shares) AS REAL)
            / NULLIF(SUM(pe.views), 0) * 100, 3
        )                                               AS share_rate_pct
    FROM dim_content       c
    JOIN dim_creators      cr ON c.creator_id  = cr.creator_id
    JOIN post_events       pe ON c.post_id     = pe.post_id
    WHERE pe.views > 0
    GROUP BY 1, 2
),

-- Rank categories WITHIN each language by engagement rate
ranked AS (
    SELECT
        *,
        -- PERCENT_RANK: 1.0 = top category in this language, 0.0 = bottom
        PERCENT_RANK() OVER (
            PARTITION BY language
            ORDER BY engagement_rate_pct
        )                                               AS er_percent_rank,
        -- NTILE: split into 3 tiers within each language
        NTILE(3) OVER (
            PARTITION BY language
            ORDER BY engagement_rate_pct
        )                                               AS er_tier   -- 3=top, 1=bottom
    FROM content_stats
    WHERE post_count >= 5   -- filter low-volume noise
)

SELECT
    language,
    content_category,
    post_count,
    total_views,
    total_engagements,
    engagement_rate_pct,
    share_rate_pct,
    avg_views_per_post,
    ROUND(er_percent_rank, 3)  AS er_percent_rank,
    er_tier
FROM ranked
ORDER BY language, engagement_rate_pct DESC;
