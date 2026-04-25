-- ============================================================
-- Query: Revenue per User, CTR, Conversion Rate
--   Pivoted by City Tier × Acquisition Channel
-- Business Question: Which user segments are most valuable
--   for ad monetisation? Where is revenue being left on the table?
-- SQL Techniques: CTEs, SUM(CASE WHEN) pivot, conditional
--   aggregation, division with NULLIF guard
-- Redshift Notes: Identical syntax. For Redshift, consider
--   PIVOT clause (available since 2022) as a cleaner alternative.
-- Expected Output: ~16 rows × 10 cols (4 tiers × 4 channels)
-- Product Decision This Informs: Ad ops team prioritises
--   inventory fill for Tier-1 users, growth team targets
--   acquisition channels with best monetisation ROI
-- ============================================================

WITH
-- User-level impression and revenue summary
user_ad_stats AS (
    SELECT
        ai.user_id,
        u.city_tier,
        u.acquisition_channel,
        COUNT(*)                                                  AS impressions,
        SUM(CASE WHEN ai.was_clicked    THEN 1 ELSE 0 END)       AS clicks,
        SUM(CASE WHEN ai.was_converted  THEN 1 ELSE 0 END)       AS conversions,
        SUM(CASE WHEN ai.was_clicked    THEN COALESCE(ai.revenue_inr, 0) ELSE 0 END) AS revenue_inr
    FROM fact_ad_impressions ai
    JOIN dim_users u ON ai.user_id = u.user_id
    WHERE ai.user_id NOT LIKE 'TEST_%'
    GROUP BY 1, 2, 3
),

-- Segment-level aggregation
segment_stats AS (
    SELECT
        city_tier,
        acquisition_channel,
        COUNT(DISTINCT user_id)                                   AS users_with_impressions,
        SUM(impressions)                                          AS total_impressions,
        SUM(clicks)                                               AS total_clicks,
        SUM(conversions)                                          AS total_conversions,
        SUM(revenue_inr)                                          AS total_revenue_inr,
        ROUND(SUM(clicks)       * 100.0 / NULLIF(SUM(impressions),  0), 3) AS ctr_pct,
        ROUND(SUM(conversions)  * 100.0 / NULLIF(SUM(clicks),       0), 2) AS cvr_pct,
        ROUND(SUM(revenue_inr)  / NULLIF(COUNT(DISTINCT user_id), 0), 2)   AS arpu_inr,
        ROUND(SUM(revenue_inr)  / NULLIF(SUM(impressions), 0) * 1000, 2)   AS ecpm_inr
    FROM user_ad_stats
    GROUP BY 1, 2
)

SELECT
    city_tier,
    acquisition_channel,
    users_with_impressions,
    total_impressions,
    total_clicks,
    total_conversions,
    ROUND(total_revenue_inr, 0)   AS total_revenue_inr,
    ctr_pct,
    cvr_pct,
    arpu_inr,
    ecpm_inr,
    -- Revenue index vs overall mean (shows relative performance)
    ROUND(
        arpu_inr / AVG(arpu_inr) OVER () * 100,
    1)                            AS arpu_index
FROM segment_stats
ORDER BY
    CASE city_tier
        WHEN 'Tier-1' THEN 1 WHEN 'Tier-2' THEN 2
        WHEN 'Tier-3' THEN 3 WHEN 'Tier-4' THEN 4
    END,
    arpu_inr DESC;

-- ── Tier-only summary pivot ──────────────────────────────────
-- Uncomment for a cleaner tier-only view:
/*
SELECT
    city_tier,
    SUM(total_revenue_inr)                      AS revenue_inr,
    AVG(ctr_pct)                                AS avg_ctr_pct,
    AVG(cvr_pct)                                AS avg_cvr_pct,
    AVG(arpu_inr)                               AS avg_arpu_inr,
    -- Tier-1 ARPU as an index reference
    AVG(arpu_inr) / MAX(AVG(arpu_inr)) OVER ()  AS arpu_vs_best
FROM segment_stats
GROUP BY 1
ORDER BY revenue_inr DESC;
*/
