# Metrics Definitions — ShareChat Product Analytics

Single source of truth for every metric used in this project.  
A crisp metric definition is itself a product-analyst deliverable — it prevents measurement disagreements between teams.

---

## User Engagement Metrics

### DAU — Daily Active Users
**Definition:** Count of distinct `user_id`s with at least one valid session on a given calendar day.

**Formula:**
```
DAU(date) = COUNT(DISTINCT user_id)
            FROM fact_sessions
            WHERE DATE(session_start) = date
              AND session_end >= session_start
```

**SQL:**
```sql
SELECT DATE(session_start) AS dt, COUNT(DISTINCT user_id) AS dau
FROM fact_sessions
WHERE session_end >= session_start AND user_id NOT LIKE 'TEST_%'
GROUP BY 1;
```

**Pitfalls:**
- Does NOT count users who opened the app but left before a session was logged (cold-start crashes).
- "Active" means any session start, not meaningful engagement — a 1-second session counts.
- Filter `session_end >= session_start` to exclude bad-duration rows.

**Related:** WAU, MAU, Stickiness (DAU/MAU)

---

### WAU — Weekly Active Users
**Definition:** Count of distinct `user_id`s with at least one valid session in a rolling 7-day window ending on a given date.

**Formula:**
```
WAU(date) = COUNT(DISTINCT user_id)
            FROM fact_sessions
            WHERE DATE(session_start) BETWEEN date - 6 AND date
```

**Pitfall:** WAU is a rolling metric — comparing two WAU values requires ensuring both windows are full 7-day periods. Partial weeks at the start of data collection understate WAU.

---

### MAU — Monthly Active Users
**Definition:** Count of distinct `user_id`s with at least one valid session in a rolling 28-day window ending on a given date.

**Formula:**
```
MAU(date) = COUNT(DISTINCT user_id)
            FROM fact_sessions
            WHERE DATE(session_start) BETWEEN date - 27 AND date
```

**Pitfall:** 28-day rolling MAU is preferred over calendar-month MAU because it removes the artificial jump between a 31-day month and a 28-day month. Always specify which definition you are using.

---

### Stickiness (DAU/MAU)
**Definition:** Ratio of daily active users to monthly active users. Measures how often monthly users return on a daily basis.

**Formula:**
```
Stickiness = DAU / MAU
```

**Interpretation:**
- 20% = typical consumer app (users come back ~1 in 5 days)
- 40%+ = strong social/entertainment product (users come back almost daily)
- ShareChat target: > 45%

**Pitfall:** Stickiness is computed on the same day's DAU and the trailing 28-day MAU, so the denominator always ≥ numerator. Values > 1.0 are impossible.

---

### D1 / D7 / D30 Retention
**Definition:** For a cohort of users who first used the product on day 0, what percentage returned on day N (within a ±1 day tolerance window).

**Formula:**
```
D7 Retention = (users from cohort with session on day 6-8) / cohort_size
```

**SQL:**
```sql
-- D7: returned 6-8 days after signup
ROUND(COUNT(DISTINCT CASE WHEN day_offset BETWEEN 6 AND 8 THEN user_id END)
      * 100.0 / cohort_size, 2) AS d7_retention_pct
```

**Industry benchmarks (social media):**
- D1: 25-40% (good); > 40% (excellent)
- D7: 15-25% (good); > 25% (excellent)
- D30: 5-15% (good); > 15% (excellent)

**Pitfall:** D7 retention requires the user to have been on the platform at least 7 days. Cohorts signed up within the last 7 days cannot have a D7 value — always check the data freshness of your retention matrix.

---

### Session Duration
**Definition:** Time elapsed between `session_start` and `session_end` for a single session.

**Formula:**
```
session_duration_sec = julianday(session_end) - julianday(session_start)) * 86400
```
(In SQLite; in Redshift: `DATEDIFF('second', session_start, session_end)`)

**Pitfall:**
- Sessions with `session_end < session_start` are data quality issues — filter them out.
- Sessions over 3 hours are likely background app activity (user left the app open) — consider capping or flagging sessions > 2 hours.
- Mean vs. median: session duration is log-normally distributed. Report median for operational decisions, mean for revenue forecasting (total watch time).

---

### Session Depth
**Definition:** Number of content items viewed (or liked/shared/commented) within a single session.

**SQL:**
```sql
SELECT session_id, posts_viewed, posts_liked, posts_shared, posts_commented
FROM fact_sessions;
```

**Related buckets:**
- Shallow: 1–5 posts
- Medium: 6–20 posts
- Deep: 20+ posts

**Pitfall:** Session depth from `fact_sessions` counts interactions logged at the session level. It may differ from a per-event count in `fact_engagement_events` because the session aggregation happens server-side and may miss rapid scroll-views.

---

## Content Performance Metrics

### Engagement Rate (ER)
**Definition:** Sum of active engagements (likes + shares + comments) divided by total views, expressed as a percentage.

**Formula:**
```
ER = (likes + shares + comments) / views × 100
```

**SQL:**
```sql
ROUND(
  SUM(CASE WHEN event_type IN ('like','share','comment') THEN 1.0 ELSE 0 END)
  / NULLIF(SUM(CASE WHEN event_type = 'view' THEN 1.0 ELSE 0 END), 0) * 100,
3) AS engagement_rate_pct
```

**Pitfall:**
- Views without watch duration (instrumentation gap ~1%) lower ER if the denominator includes them.
- ER varies significantly by content type: short videos (8-10%) > images (4-6%) > text posts (2-4%).
- Never compare raw ER between platforms without normalising for content mix.

**Related:** Share Rate (shares/views), Comment Rate (comments/views)

---

### Watch Completion Rate
**Definition:** Average percentage of a video's duration that users watch before scrolling away.

**Formula:**
```
watch_completion_pct = AVG(watch_duration_sec / content_duration_sec) × 100
```

**Pitfall:** Only applicable to video content (`ShortVideo`, `LiveStream`). Null `watch_duration_sec` rows (1% of view events) must be excluded.

---

## Monetisation Metrics

### CTR — Click-Through Rate
**Definition:** Percentage of ad impressions where the user clicked.

**Formula:**
```
CTR = clicked_impressions / total_impressions × 100
```

**SQL:**
```sql
ROUND(SUM(CASE WHEN was_clicked = 1 THEN 1.0 ELSE 0 END)
      / COUNT(*) * 100, 3) AS ctr_pct
FROM fact_ad_impressions;
```

**Industry benchmarks:**
- In-feed video ads: 1-3% (good); > 3% (excellent)
- Banner ads: 0.1-0.5% (typical)

**Pitfall:** CTR measures intent signal, not purchase intent. A user clicking on a gaming ad is not the same signal as a Tier-1 user clicking on a fintech ad.

---

### CVR — Conversion Rate
**Definition:** Percentage of ad clicks that result in a measurable conversion (app install, purchase, sign-up).

**Formula:**
```
CVR = conversions / clicks × 100
```

**Pitfall:** In this dataset, "conversion" is modelled as a binary flag (`was_converted`). In production, conversion attribution requires a last-click or multi-touch attribution model that joins back to the advertiser's conversion tracking.

---

### ARPU — Average Revenue Per User
**Definition:** Total ad revenue divided by total active users in a period.

**Formula:**
```
ARPU = total_revenue_inr / active_users_in_period
```

**SQL:**
```sql
ROUND(SUM(CASE WHEN was_clicked = 1 THEN COALESCE(revenue_inr, 0) ELSE 0 END)
      / NULLIF(COUNT(DISTINCT user_id), 0), 2) AS arpu_inr
```

**Pitfall:**
- ARPU computed only on users with impressions overstates vs. total-user ARPU.
- Always specify the denominator: "ARPU on monetisable users" vs. "ARPU on all active users."
- Compare ARPU across segments only when holding constant the impression count per user.

---

### eCPM — Effective Cost Per Mille
**Definition:** Revenue earned per 1,000 impressions, from the publisher's perspective.

**Formula:**
```
eCPM = (total_revenue / total_impressions) × 1000
```

**Pitfall:** eCPM is a blended metric. A rising eCPM could mean better ad quality OR fewer low-CPM ads filling. Always decompose into CTR × CPL (cost per lead) to understand the driver.

---

## Creator Metrics

### Creator Retention
**Definition:** Percentage of creators who post at least once in week N, given that they posted in week 1.

**SQL (streak approach):**
```sql
-- See sql/10_creator_retention.sql for the full streak detection query
```

**Pitfall:** A creator who posts weekly for 10 weeks, takes a 2-week break, then resumes has two separate "streaks." The max streak is 10 weeks, but their overall retention is high. Track both max streak and posting consistency separately.

---

### Creator Tier
**Definition:** Categorical tier based on follower count at a point in time.

| Tier  | Follower Range     |
|-------|--------------------|
| Nano  | < 1,000            |
| Micro | 1,000 – 9,999      |
| Mid   | 10,000 – 99,999    |
| Macro | 100,000 – 999,999  |
| Mega  | ≥ 1,000,000        |

**Pitfall:** Creator tier is a snapshot metric — it changes as follower counts grow or decline. Avoid using tier as a static cohort in long-horizon retention analysis.

---

## Power User Definition

**ShareChat Power User (working definition):**
A user who meets ALL three criteria in a rolling 30-day window:
1. **Recency:** Active in the last 7 days (R-score ≥ 4)
2. **Frequency:** Active on ≥ 15 distinct days in the last 30 days (F-score ≥ 4)
3. **Monetary:** Total watch time ≥ 500 minutes in the last 30 days (M-score ≥ 4)

This maps to the "Champions" segment in `sql/09_power_users.sql`.

**Pitfall:** Power user definitions should be product-specific. An 18-year-old on Android-Low checking the app 20 times a day for 2 minutes each is different from a 25-year-old watching 3 long-form drama episodes per day — both might qualify under the same RFM score but have very different monetisation profiles.

---

## Statistical Metrics

### Z-statistic (two-sample test)
**Formula:**
```
z = (mean_variant - mean_control) / sqrt(var_variant/n_variant + var_control/n_control)
```

**Significance thresholds:**
- |z| > 1.645 → p < 0.10 (90% confidence)
- |z| > 1.960 → p < 0.05 (95% confidence — standard for shipping decisions)
- |z| > 2.576 → p < 0.01 (99% confidence — use for guardrail metrics)

**Pitfall:** A large sample size makes almost any difference statistically significant. Always check practical significance (minimum detectable effect) alongside statistical significance. A +0.1% lift on session duration is statistically significant at n=500K but irrelevant to a product decision.

---

## Metric Relationships Summary

```
DAU → MAU → Stickiness (DAU/MAU)
  ↓
Session Duration → Engagement Rate → Creator Engagement
  ↓
Ad Impressions → CTR → CVR → ARPU → eCPM
```

- More engaged users (higher ER) watch longer → more ad impressions → higher revenue
- Better retention → larger MAU → more impressions at scale
- Creator health → content quality → engagement → retention (circular reinforcement loop)
