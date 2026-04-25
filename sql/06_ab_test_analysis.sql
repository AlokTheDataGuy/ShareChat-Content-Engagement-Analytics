-- ============================================================
-- Query: A/B Test Readout — Session Duration Lift
-- Business Question: Does the variant experience produce
--   statistically significantly longer sessions vs. control?
-- SQL Techniques: CTEs, conditional aggregation, variance
--   computation (E[X²] - E[X]²), z-statistic calculation
-- Statistical Logic:
--   z = (mean_variant - mean_control)
--       / sqrt(var_v/n_v + var_c/n_c)
--   For large n (both groups have 25K+ users), z ≈ t.
--   p-value approximated: z > 1.96 → p < 0.05 (two-tailed)
-- Redshift Notes: Identical, SQRT() and POWER() are ANSI.
-- Expected Output: 1 row × 12 cols (experiment summary)
-- Product Decision This Informs: Ship/hold/iterate on the
--   variant feature. This readout is what a PM needs in the
--   weekly product review meeting.
-- ============================================================

WITH
-- Aggregate session stats per user per group
user_sessions_agg AS (
    SELECT
        s.user_id,
        u.experiment_group,
        COUNT(*)                                AS session_count,
        AVG(s.session_duration_sec)             AS avg_dur,
        -- Need E[X^2] to compute variance: Var(X) = E[X^2] - E[X]^2
        AVG(s.session_duration_sec * s.session_duration_sec) AS avg_dur_sq
    FROM fact_sessions s
    JOIN dim_users u ON s.user_id = u.user_id
    WHERE s.session_end >= s.session_start
      AND s.user_id NOT LIKE 'TEST_%'
    GROUP BY 1, 2
),

-- Group-level statistics
group_stats AS (
    SELECT
        experiment_group,
        COUNT(DISTINCT user_id)                 AS n_users,
        SUM(session_count)                      AS total_sessions,
        -- Mean of per-user average duration
        AVG(avg_dur)                            AS mean_dur_sec,
        -- Population variance across users: Var = E[X^2] - E[X]^2
        AVG(avg_dur_sq) - POWER(AVG(avg_dur), 2) AS variance_dur
    FROM user_sessions_agg
    GROUP BY 1
),

-- Pivot into one row for z-test calculation
pivoted AS (
    SELECT
        MAX(CASE WHEN experiment_group = 'control' THEN n_users      END) AS n_c,
        MAX(CASE WHEN experiment_group = 'variant' THEN n_users      END) AS n_v,
        MAX(CASE WHEN experiment_group = 'control' THEN total_sessions END) AS sessions_c,
        MAX(CASE WHEN experiment_group = 'variant' THEN total_sessions END) AS sessions_v,
        MAX(CASE WHEN experiment_group = 'control' THEN mean_dur_sec END) AS mean_c,
        MAX(CASE WHEN experiment_group = 'variant' THEN mean_dur_sec END) AS mean_v,
        MAX(CASE WHEN experiment_group = 'control' THEN variance_dur END) AS var_c,
        MAX(CASE WHEN experiment_group = 'variant' THEN variance_dur END) AS var_v
    FROM group_stats
)

SELECT
    n_c                                                       AS control_users,
    n_v                                                       AS variant_users,
    sessions_c                                                AS control_sessions,
    sessions_v                                                AS variant_sessions,
    ROUND(mean_c, 1)                                          AS control_avg_dur_sec,
    ROUND(mean_v, 1)                                          AS variant_avg_dur_sec,
    ROUND(mean_v - mean_c, 1)                                 AS absolute_lift_sec,
    ROUND((mean_v - mean_c) / NULLIF(mean_c, 0) * 100, 2)    AS relative_lift_pct,
    -- Standard error of the difference
    ROUND(SQRT(var_v / NULLIF(n_v, 0) + var_c / NULLIF(n_c, 0)), 3) AS std_error,
    -- Z-statistic
    ROUND(
        (mean_v - mean_c)
        / NULLIF(SQRT(var_v / NULLIF(n_v, 0) + var_c / NULLIF(n_c, 0)), 0),
    3)                                                        AS z_statistic,
    -- 95% confidence interval bounds for the difference
    ROUND((mean_v - mean_c)
          - 1.96 * SQRT(var_v / NULLIF(n_v, 0) + var_c / NULLIF(n_c, 0)), 1) AS ci_lower_95,
    ROUND((mean_v - mean_c)
          + 1.96 * SQRT(var_v / NULLIF(n_v, 0) + var_c / NULLIF(n_c, 0)), 1) AS ci_upper_95,
    -- Significance flag (z > 1.96 → p < 0.05 two-tailed)
    CASE
        WHEN ABS((mean_v - mean_c)
             / NULLIF(SQRT(var_v / NULLIF(n_v, 0) + var_c / NULLIF(n_c, 0)), 0)) > 2.576
        THEN 'p < 0.01 — HIGHLY SIGNIFICANT'
        WHEN ABS((mean_v - mean_c)
             / NULLIF(SQRT(var_v / NULLIF(n_v, 0) + var_c / NULLIF(n_c, 0)), 0)) > 1.96
        THEN 'p < 0.05 — SIGNIFICANT'
        ELSE 'NOT SIGNIFICANT at 0.05'
    END                                                       AS significance
FROM pivoted;
