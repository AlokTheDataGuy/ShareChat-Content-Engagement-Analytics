-- ============================================================
-- Query: Cohort-Based LTV Proxy — Cumulative Watch Time
--   and Ad Revenue at 30/60/90 Day Windows
-- Business Question: Which signup-month cohorts are generating
--   the most long-term value? Is new-user monetisation improving?
-- SQL Techniques: Chain of 4 CTEs, date arithmetic for
--   cohort windows, conditional aggregation for time windows,
--   window functions for cohort comparison
-- Redshift Notes: Replace julianday() with DATEDIFF('day',...).
--   DATE_TRUNC('month', ...) replaces strftime('%Y-%m',...).
-- Expected Output: ~18 rows × 12 cols (one per signup month)
-- Product Decision This Informs: Whether to increase new-user
--   onboarding investment for high-LTV cohorts, signals whether
--   product improvements are generating better-quality users
-- ============================================================

WITH
-- CTE 1: tag every user with their signup-month cohort
user_cohort AS (
    SELECT
        user_id,
        signup_date,
        -- Cohort = first day of signup month
        strftime('%Y-%m', signup_date) AS cohort_month,
        city_tier,
        signup_language,
        acquisition_channel
        -- Redshift: DATE_TRUNC('month', signup_date::DATE) AS cohort_month
    FROM dim_users
    WHERE user_id NOT LIKE 'TEST_%'
),

-- CTE 2: cumulative session minutes per user at 30/60/90 day marks
user_watch_time AS (
    SELECT
        uc.user_id,
        uc.cohort_month,
        -- Days since signup when this session occurred
        CAST(julianday(DATE(s.session_start)) - julianday(uc.signup_date) AS INTEGER)
            AS days_since_signup,
            -- Redshift: DATEDIFF('day', uc.signup_date::DATE, DATE(s.session_start))
        s.session_duration_sec / 60.0 AS session_min
    FROM user_cohort   uc
    JOIN fact_sessions s ON uc.user_id = s.user_id
    WHERE s.session_end >= s.session_start
      AND s.session_duration_sec > 0
),

-- CTE 3: cumulative ad revenue per user at 30/60/90 day marks
user_ad_revenue AS (
    SELECT
        uc.user_id,
        uc.cohort_month,
        CAST(julianday(DATE(ai.impression_timestamp)) - julianday(uc.signup_date) AS INTEGER)
            AS days_since_signup,
        COALESCE(ai.revenue_inr, 0) AS revenue_inr
    FROM user_cohort          uc
    JOIN fact_ad_impressions  ai ON uc.user_id = ai.user_id
    WHERE ai.was_clicked = 1
),

-- CTE 4: cohort-level aggregation at each LTV window
cohort_ltv AS (
    SELECT
        uc.cohort_month,
        COUNT(DISTINCT uc.user_id)                                    AS cohort_size,
        -- Watch time LTV
        ROUND(SUM(CASE WHEN wt.days_since_signup <= 30
                       THEN wt.session_min ELSE 0 END)
              / NULLIF(COUNT(DISTINCT uc.user_id), 0), 1)             AS watch_min_per_user_d30,
        ROUND(SUM(CASE WHEN wt.days_since_signup <= 60
                       THEN wt.session_min ELSE 0 END)
              / NULLIF(COUNT(DISTINCT uc.user_id), 0), 1)             AS watch_min_per_user_d60,
        ROUND(SUM(CASE WHEN wt.days_since_signup <= 90
                       THEN wt.session_min ELSE 0 END)
              / NULLIF(COUNT(DISTINCT uc.user_id), 0), 1)             AS watch_min_per_user_d90,
        -- Ad revenue LTV
        ROUND(SUM(CASE WHEN ar.days_since_signup <= 30
                       THEN ar.revenue_inr ELSE 0 END)
              / NULLIF(COUNT(DISTINCT uc.user_id), 0), 2)             AS rev_per_user_d30,
        ROUND(SUM(CASE WHEN ar.days_since_signup <= 60
                       THEN ar.revenue_inr ELSE 0 END)
              / NULLIF(COUNT(DISTINCT uc.user_id), 0), 2)             AS rev_per_user_d60,
        ROUND(SUM(CASE WHEN ar.days_since_signup <= 90
                       THEN ar.revenue_inr ELSE 0 END)
              / NULLIF(COUNT(DISTINCT uc.user_id), 0), 2)             AS rev_per_user_d90
    FROM user_cohort       uc
    LEFT JOIN user_watch_time wt ON uc.user_id = wt.user_id
    LEFT JOIN user_ad_revenue ar ON uc.user_id = ar.user_id
    GROUP BY 1
)

SELECT
    cohort_month,
    cohort_size,
    watch_min_per_user_d30,
    watch_min_per_user_d60,
    watch_min_per_user_d90,
    rev_per_user_d30,
    rev_per_user_d60,
    rev_per_user_d90,
    -- D30→D90 watch time growth multiple
    ROUND(watch_min_per_user_d90
          / NULLIF(watch_min_per_user_d30, 0), 2)                     AS d30_to_d90_watch_mult,
    -- D30→D90 revenue growth multiple
    ROUND(rev_per_user_d90
          / NULLIF(rev_per_user_d30, 0), 2)                           AS d30_to_d90_rev_mult,
    -- Cohort quality index: revenue rank vs average (100 = avg cohort)
    ROUND(rev_per_user_d90
          / NULLIF(AVG(rev_per_user_d90) OVER (), 0) * 100, 1)        AS cohort_quality_index
FROM cohort_ltv
ORDER BY cohort_month;
