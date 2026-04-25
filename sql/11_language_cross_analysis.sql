-- ============================================================
-- Query: Cross-Language Content Consumption Matrix
-- Business Question: Do users consume content in languages
--   other than their signup language? Which language pairs
--   show the most cross-language consumption?
-- SQL Techniques: Self-join, pivot (CASE aggregation),
--   matrix construction, percentage computation
-- Redshift Notes: Identical. For a fully dynamic pivot,
--   use Redshift's PIVOT clause or generate SQL dynamically
--   in Python. The CASE-based approach shown here works in both.
-- Expected Output: 12 rows × 14 cols (user_lang × content_lang)
-- Product Decision This Informs: Content recommendation team
--   understands cross-language affinities, feed algorithm can
--   serve Bhojpuri content to Hindi users at higher weight
-- ============================================================

WITH
-- User's primary language and the language of content they engaged with
user_content_lang AS (
    SELECT
        u.signup_language          AS user_language,
        c.language                 AS content_language,
        COUNT(*)                   AS event_count
    FROM fact_engagement_events fe
    JOIN dim_users    u ON fe.user_id  = u.user_id
    JOIN dim_content  c ON fe.post_id  = c.post_id
    WHERE fe.event_type IN ('view', 'like', 'share')
      AND fe.user_id NOT LIKE 'TEST_%'
    GROUP BY 1, 2
),

-- Total events per user language (for % computation)
user_lang_totals AS (
    SELECT user_language, SUM(event_count) AS total_events
    FROM user_content_lang
    GROUP BY 1
)

-- Pivot: rows = user language, columns = content language
SELECT
    ucl.user_language                                                  AS user_language,
    ut.total_events                                                   AS total_events,
    -- Each column = % of this user-lang's events on that content language
    ROUND(SUM(CASE WHEN content_language = 'Hindi'    THEN event_count ELSE 0 END)
          * 100.0 / ut.total_events, 2)                               AS hindi_pct,
    ROUND(SUM(CASE WHEN content_language = 'Telugu'   THEN event_count ELSE 0 END)
          * 100.0 / ut.total_events, 2)                               AS telugu_pct,
    ROUND(SUM(CASE WHEN content_language = 'Tamil'    THEN event_count ELSE 0 END)
          * 100.0 / ut.total_events, 2)                               AS tamil_pct,
    ROUND(SUM(CASE WHEN content_language = 'Bhojpuri' THEN event_count ELSE 0 END)
          * 100.0 / ut.total_events, 2)                               AS bhojpuri_pct,
    ROUND(SUM(CASE WHEN content_language = 'Marathi'  THEN event_count ELSE 0 END)
          * 100.0 / ut.total_events, 2)                               AS marathi_pct,
    ROUND(SUM(CASE WHEN content_language = 'Bengali'  THEN event_count ELSE 0 END)
          * 100.0 / ut.total_events, 2)                               AS bengali_pct,
    ROUND(SUM(CASE WHEN content_language = 'Kannada'  THEN event_count ELSE 0 END)
          * 100.0 / ut.total_events, 2)                               AS kannada_pct,
    ROUND(SUM(CASE WHEN content_language = 'Malayalam' THEN event_count ELSE 0 END)
          * 100.0 / ut.total_events, 2)                               AS malayalam_pct,
    ROUND(SUM(CASE WHEN content_language = 'Gujarati' THEN event_count ELSE 0 END)
          * 100.0 / ut.total_events, 2)                               AS gujarati_pct,
    ROUND(SUM(CASE WHEN content_language = 'Punjabi'  THEN event_count ELSE 0 END)
          * 100.0 / ut.total_events, 2)                               AS punjabi_pct,
    ROUND(SUM(CASE WHEN content_language = 'Odia'     THEN event_count ELSE 0 END)
          * 100.0 / ut.total_events, 2)                               AS odia_pct,
    ROUND(SUM(CASE WHEN content_language = 'Assamese' THEN event_count ELSE 0 END)
          * 100.0 / ut.total_events, 2)                               AS assamese_pct,
    -- % consuming content in their OWN language vs. cross-language
    ROUND(SUM(CASE WHEN content_language = ucl.user_language THEN event_count ELSE 0 END)
          * 100.0 / ut.total_events, 2)                               AS same_language_pct,
    ROUND(SUM(CASE WHEN content_language != ucl.user_language THEN event_count ELSE 0 END)
          * 100.0 / ut.total_events, 2)                               AS cross_language_pct
FROM user_content_lang ucl
JOIN user_lang_totals  ut ON ucl.user_language = ut.user_language
GROUP BY 1, 2
ORDER BY 2 DESC;
