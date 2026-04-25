-- ============================================================
-- Query: Creator Power-Law Analysis (Pareto / Lorenz Curve)
-- Business Question: What % of total engagement is captured
--   by the top X% of creators? How concentrated is engagement?
-- SQL Techniques: NTILE(100), cumulative SUM() OVER,
--   window functions for running totals, rank-based aggregation
-- Redshift Notes: Identical, Redshift's NTILE is ANSI standard.
--   For very large fact tables, consider pre-aggregating to a
--   creator-level summary table first to avoid full scans.
-- Expected Output: 100 rows × 5 cols (one per percentile bucket)
-- Product Decision This Informs: Creator monetisation strategy.
--   If top 1% drive 40%+ of engagement, their churn is
--   existential — priority for creator fund / revenue share
-- ============================================================

WITH
-- Step 1: total engagement events per creator
creator_engagement AS (
    SELECT
        creator_id,
        COUNT(*)                                          AS total_events,
        SUM(CASE WHEN event_type = 'view'    THEN 1 ELSE 0 END) AS views,
        SUM(CASE WHEN event_type = 'like'    THEN 1 ELSE 0 END) AS likes,
        SUM(CASE WHEN event_type = 'share'   THEN 1 ELSE 0 END) AS shares,
        SUM(CASE WHEN event_type = 'comment' THEN 1 ELSE 0 END) AS comments,
        COUNT(DISTINCT user_id)                           AS unique_viewers
    FROM fact_engagement_events
    WHERE user_id NOT LIKE 'TEST_%'
    GROUP BY 1
),

-- Step 2: join with creator dimension for tier info
creator_stats AS (
    SELECT
        ce.creator_id,
        cr.creator_tier,
        cr.follower_count,
        ce.total_events,
        ce.views,
        ce.likes + ce.shares + ce.comments                AS engagements,
        ce.unique_viewers
    FROM creator_engagement  ce
    JOIN dim_creators         cr ON ce.creator_id = cr.creator_id
),

-- Step 3: assign each creator to a percentile bucket (1=bottom, 100=top)
percentiled AS (
    SELECT
        *,
        NTILE(100) OVER (ORDER BY total_events ASC)  AS engagement_percentile
    FROM creator_stats
),

-- Step 4: aggregate by percentile bucket
bucket_agg AS (
    SELECT
        engagement_percentile,
        COUNT(*)                    AS creator_count,
        SUM(total_events)           AS bucket_events,
        SUM(engagements)            AS bucket_engagements,
        AVG(follower_count)         AS avg_followers
    FROM percentiled
    GROUP BY 1
),

-- Step 5: compute running totals for Lorenz curve
grand_total AS (
    SELECT SUM(bucket_events) AS total_events_all FROM bucket_agg
)

SELECT
    b.engagement_percentile,
    b.creator_count,
    b.bucket_events,
    ROUND(b.bucket_events * 100.0 / g.total_events_all, 3)        AS pct_of_total_events,
    -- Running (cumulative) share of events from top X% of creators
    -- Use (101 - percentile) to read as "top X%": percentile 100 = top 1%
    SUM(b.bucket_events) OVER (
        ORDER BY b.engagement_percentile DESC
        ROWS BETWEEN UNBOUNDED PRECEDING AND CURRENT ROW
    ) * 100.0 / g.total_events_all                                 AS cumulative_pct_top_x,
    ROUND(b.avg_followers, 0)                                      AS avg_followers_in_bucket
FROM bucket_agg b
CROSS JOIN grand_total g
ORDER BY b.engagement_percentile DESC;

-- ── Tier summary (simpler Pareto view) ──────────────────────
-- Uncomment to see engagement % by creator tier directly:
/*
SELECT
    creator_tier,
    COUNT(DISTINCT c.creator_id)                AS creator_count,
    SUM(fe.total_events)                        AS total_events,
    ROUND(SUM(fe.total_events) * 100.0
          / SUM(SUM(fe.total_events)) OVER (), 2) AS pct_of_total
FROM creator_engagement fe
JOIN dim_creators c ON fe.creator_id = c.creator_id
GROUP BY 1
ORDER BY total_events DESC;
*/
