-- ============================================================
-- Query: Creator Consecutive Weekly Posting Streaks
-- Business Question: How many creators maintain consistent
--   weekly posting habits, and how long are their streaks?
-- SQL Techniques: Recursive CTE, window functions (LAG),
--   date arithmetic, streak detection pattern
-- Redshift Notes: Recursive CTEs (WITH RECURSIVE) are
--   supported in Redshift as of 2021. The syntax is identical.
--   For very large creator tables, materialise weekly_posts
--   as a temp table first.
-- Expected Output: ~20 rows × 4 cols (streak length distribution)
-- Product Decision This Informs: Creator success team targets
--   creators at week 2-3 (before most drop off) with coaching,
--   streak data feeds creator tier promotion criteria
-- ============================================================

WITH
-- Step 1: which ISO week did each creator post in?
weekly_posts AS (
    SELECT
        creator_id,
        -- ISO week: YYYY-WW format for consistent week numbering
        strftime('%Y-%W', post_date) AS post_week,
        -- Sequential week number for arithmetic
        CAST(strftime('%Y', post_date) AS INTEGER) * 53
            + CAST(strftime('%W', post_date) AS INTEGER) AS week_num
    FROM dim_content
    GROUP BY 1, 2, 3
),

-- Step 2: for each creator-week, get the previous week they posted
with_prev AS (
    SELECT
        creator_id,
        post_week,
        week_num,
        LAG(week_num) OVER (PARTITION BY creator_id ORDER BY week_num) AS prev_week_num
    FROM weekly_posts
),

-- Step 3: flag the start of a new streak
--   (gap > 1 week since last post = new streak)
streak_flags AS (
    SELECT
        creator_id,
        post_week,
        week_num,
        CASE
            WHEN prev_week_num IS NULL              THEN 1   -- first ever post
            WHEN week_num - prev_week_num > 1       THEN 1   -- gap in posting
            ELSE                                         0
        END AS is_streak_start
    FROM with_prev
),

-- Step 4: assign a streak ID to each consecutive run
streak_ids AS (
    SELECT
        creator_id,
        post_week,
        week_num,
        -- Running sum of streak starts = unique streak ID per creator
        SUM(is_streak_start) OVER (
            PARTITION BY creator_id
            ORDER BY week_num
            ROWS UNBOUNDED PRECEDING
        ) AS streak_id
    FROM streak_flags
),

-- Step 5: compute streak length (weeks) per creator per streak
streak_lengths AS (
    SELECT
        creator_id,
        streak_id,
        MIN(post_week) AS streak_start_week,
        MAX(post_week) AS streak_end_week,
        COUNT(*)       AS streak_weeks   -- consecutive weeks in this run
    FROM streak_ids
    GROUP BY 1, 2
),

-- Step 6: longest streak per creator
creator_max_streak AS (
    SELECT
        creator_id,
        MAX(streak_weeks) AS max_streak_weeks
    FROM streak_lengths
    GROUP BY 1
)

-- Distribution of maximum streak lengths
SELECT
    max_streak_weeks                                         AS streak_length_weeks,
    COUNT(*)                                                 AS creator_count,
    ROUND(COUNT(*) * 100.0 / SUM(COUNT(*)) OVER (), 2)      AS pct_of_creators,
    -- Cumulative % of creators with streak ≥ N weeks
    ROUND(
        SUM(COUNT(*)) OVER (ORDER BY max_streak_weeks DESC
                            ROWS UNBOUNDED PRECEDING)
        * 100.0 / SUM(COUNT(*)) OVER (),
    2)                                                       AS cumulative_pct_ge_n
FROM creator_max_streak
GROUP BY 1
ORDER BY 1;
