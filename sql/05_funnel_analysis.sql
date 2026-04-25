-- ============================================================
-- Query: View → Like → Share → Follow Funnel by City Tier
-- Business Question: At what stage of the engagement funnel
--   do users drop off, and does this differ by city tier?
-- SQL Techniques: CTEs, conditional aggregation (SUM CASE),
--   window functions (SUM OVER for grand totals), pivoting
-- Redshift Notes: SUM(CASE WHEN ...) pivot is identical.
--   For multi-step funnels on very large tables, consider
--   a pre-aggregated funnel_events staging table.
-- Expected Output: 4 rows × 8 cols (one per city tier)
-- Product Decision This Informs: If Tier-1 users drop off at
--   Like step, the feed quality is a problem, not content volume.
--   If Tier-3/4 drop off at Share, friction in the share UI
--   may be the issue (network sharing, data costs).
-- ============================================================

WITH
-- Get the "deepest" action each user took per post (funnel progression)
-- view=1, like=2, share=3, follow=4 (skip/report don't count positively)
user_post_max_action AS (
    SELECT
        fe.user_id,
        fe.post_id,
        u.city_tier,
        MAX(CASE fe.event_type
            WHEN 'view'    THEN 1
            WHEN 'like'    THEN 2
            WHEN 'share'   THEN 3
            WHEN 'follow'  THEN 4
            ELSE 0
        END) AS max_action_level
    FROM fact_engagement_events fe
    JOIN dim_users u ON fe.user_id = u.user_id
    WHERE fe.user_id NOT LIKE 'TEST_%'
      AND fe.event_type IN ('view','like','share','follow')
    GROUP BY 1, 2, 3
),

-- Count users who reached each stage, grouped by city tier
funnel_by_tier AS (
    SELECT
        city_tier,
        COUNT(*)                                                      AS user_post_pairs,
        COUNT(DISTINCT user_id)                                       AS unique_users,
        SUM(CASE WHEN max_action_level >= 1 THEN 1 ELSE 0 END)       AS reached_view,
        SUM(CASE WHEN max_action_level >= 2 THEN 1 ELSE 0 END)       AS reached_like,
        SUM(CASE WHEN max_action_level >= 3 THEN 1 ELSE 0 END)       AS reached_share,
        SUM(CASE WHEN max_action_level >= 4 THEN 1 ELSE 0 END)       AS reached_follow
    FROM user_post_max_action
    GROUP BY 1
)

SELECT
    city_tier,
    unique_users,
    reached_view,
    reached_like,
    reached_share,
    reached_follow,
    -- Stage conversion rates (each vs the prior stage)
    100.0                                                             AS view_rate_pct,
    ROUND(reached_like  * 100.0 / NULLIF(reached_view,  0), 2)      AS view_to_like_pct,
    ROUND(reached_share * 100.0 / NULLIF(reached_like,  0), 2)      AS like_to_share_pct,
    ROUND(reached_follow* 100.0 / NULLIF(reached_share, 0), 2)      AS share_to_follow_pct,
    -- Overall: view → follow conversion
    ROUND(reached_follow* 100.0 / NULLIF(reached_view,  0), 2)      AS overall_conversion_pct
FROM funnel_by_tier
ORDER BY
    CASE city_tier
        WHEN 'Tier-1' THEN 1
        WHEN 'Tier-2' THEN 2
        WHEN 'Tier-3' THEN 3
        WHEN 'Tier-4' THEN 4
    END;

-- ── Overall (all tiers combined) — append to output ─────────
SELECT
    'ALL TIERS'                                                       AS city_tier,
    COUNT(DISTINCT user_id)                                           AS unique_users,
    SUM(CASE WHEN max_action_level >= 1 THEN 1 ELSE 0 END)           AS reached_view,
    SUM(CASE WHEN max_action_level >= 2 THEN 1 ELSE 0 END)           AS reached_like,
    SUM(CASE WHEN max_action_level >= 3 THEN 1 ELSE 0 END)           AS reached_share,
    SUM(CASE WHEN max_action_level >= 4 THEN 1 ELSE 0 END)           AS reached_follow,
    100.0                                                             AS view_rate_pct,
    ROUND(SUM(CASE WHEN max_action_level >= 2 THEN 1 ELSE 0 END)
          * 100.0 / NULLIF(SUM(CASE WHEN max_action_level >= 1 THEN 1 ELSE 0 END),0), 2) AS view_to_like_pct,
    ROUND(SUM(CASE WHEN max_action_level >= 3 THEN 1 ELSE 0 END)
          * 100.0 / NULLIF(SUM(CASE WHEN max_action_level >= 2 THEN 1 ELSE 0 END),0), 2) AS like_to_share_pct,
    ROUND(SUM(CASE WHEN max_action_level >= 4 THEN 1 ELSE 0 END)
          * 100.0 / NULLIF(SUM(CASE WHEN max_action_level >= 3 THEN 1 ELSE 0 END),0), 2) AS share_to_follow_pct,
    ROUND(SUM(CASE WHEN max_action_level >= 4 THEN 1 ELSE 0 END)
          * 100.0 / NULLIF(SUM(CASE WHEN max_action_level >= 1 THEN 1 ELSE 0 END),0), 2) AS overall_conversion_pct
FROM user_post_max_action;
