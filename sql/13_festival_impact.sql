-- ============================================================
-- Query: Festival Impact Analysis — DAU, Session Duration,
--   Engagement Rate on Festival Days vs. Non-Festival Days
-- Business Question: How much do major Indian festivals
--   lift platform activity, and is the lift statistically
--   significant?
-- SQL Techniques: CTEs, JOIN with dim_date, conditional
--   aggregation, basic t-test logic (variance, pooled SE)
-- Redshift Notes: Identical except replace julianday() with
--   DATEDIFF('day',...) and DATE() with ::DATE casting.
-- Expected Output: 2 rows (festival vs non-festival) + per-festival rows
-- Product Decision This Informs: Content team pre-produces
--   festival content packs, ad ops reserves premium inventory
--   for festival periods, engineering pre-scales servers
-- ============================================================

WITH
-- Daily metrics joined with festival flag
daily_metrics AS (
    SELECT
        DATE(s.session_start)        AS activity_date,
        d.is_festival,
        d.festival_name,
        COUNT(DISTINCT s.user_id)    AS dau,
        COUNT(*)                     AS total_sessions,
        AVG(s.session_duration_sec)  AS avg_session_sec,
        SUM(s.posts_liked) * 1.0
            / NULLIF(SUM(s.posts_viewed), 0) AS like_rate
    FROM fact_sessions s
    JOIN dim_date      d ON DATE(s.session_start) = d.date
    WHERE s.session_end >= s.session_start
      AND s.user_id NOT LIKE 'TEST_%'
    GROUP BY 1, 2, 3
),

-- Compute grand mean and variance for festival vs non-festival
group_stats AS (
    SELECT
        CASE WHEN is_festival = 1 THEN 'Festival Day' ELSE 'Normal Day' END AS day_type,
        COUNT(*)                                    AS day_count,
        AVG(dau)                                    AS mean_dau,
        AVG(dau * dau) - POWER(AVG(dau), 2)         AS var_dau,
        AVG(avg_session_sec)                        AS mean_session_sec,
        AVG(avg_session_sec * avg_session_sec)
            - POWER(AVG(avg_session_sec), 2)        AS var_session,
        AVG(like_rate)                              AS mean_like_rate,
        MIN(dau)                                    AS min_dau,
        MAX(dau)                                    AS max_dau
    FROM daily_metrics
    GROUP BY 1
),

-- Pivot for t-test calculation
pivoted AS (
    SELECT
        MAX(CASE WHEN day_type = 'Festival Day' THEN day_count    END) AS n_f,
        MAX(CASE WHEN day_type = 'Normal Day'   THEN day_count    END) AS n_n,
        MAX(CASE WHEN day_type = 'Festival Day' THEN mean_dau     END) AS mean_dau_f,
        MAX(CASE WHEN day_type = 'Normal Day'   THEN mean_dau     END) AS mean_dau_n,
        MAX(CASE WHEN day_type = 'Festival Day' THEN var_dau      END) AS var_dau_f,
        MAX(CASE WHEN day_type = 'Normal Day'   THEN var_dau      END) AS var_dau_n,
        MAX(CASE WHEN day_type = 'Festival Day' THEN mean_session_sec END) AS mean_sess_f,
        MAX(CASE WHEN day_type = 'Normal Day'   THEN mean_session_sec END) AS mean_sess_n
    FROM group_stats
)

-- Main comparison table
SELECT
    gs.day_type,
    gs.day_count,
    ROUND(gs.mean_dau, 0)              AS avg_dau,
    ROUND(gs.mean_session_sec, 0)      AS avg_session_sec,
    ROUND(gs.mean_like_rate * 100, 3)  AS avg_like_rate_pct,
    gs.min_dau,
    gs.max_dau,
    -- Festival lift vs normal baseline
    ROUND(
        (gs.mean_dau
         - MAX(CASE WHEN gs2.day_type = 'Normal Day' THEN gs2.mean_dau END))
        * 100.0
        / NULLIF(MAX(CASE WHEN gs2.day_type = 'Normal Day' THEN gs2.mean_dau END), 0),
    2)                                 AS dau_lift_pct,
    -- T-statistic (Welch's)
    ROUND(
        (p.mean_dau_f - p.mean_dau_n)
        / NULLIF(SQRT(p.var_dau_f / NULLIF(p.n_f, 0)
                    + p.var_dau_n / NULLIF(p.n_n, 0)), 0),
    2)                                 AS t_stat_dau,
    CASE
        WHEN ABS((p.mean_dau_f - p.mean_dau_n)
             / NULLIF(SQRT(p.var_dau_f / NULLIF(p.n_f, 0)
                         + p.var_dau_n / NULLIF(p.n_n, 0)), 0)) > 1.96
        THEN 'Significant (p<0.05)'
        ELSE 'Not significant'
    END                                AS significance
FROM group_stats gs
CROSS JOIN group_stats gs2
CROSS JOIN pivoted p
GROUP BY gs.day_type, gs.day_count, gs.mean_dau, gs.mean_session_sec,
         gs.mean_like_rate, gs.min_dau, gs.max_dau,
         p.mean_dau_f, p.mean_dau_n, p.var_dau_f, p.var_dau_n, p.n_f, p.n_n
ORDER BY gs.day_type;
