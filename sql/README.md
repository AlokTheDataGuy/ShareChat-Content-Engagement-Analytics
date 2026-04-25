# SQL Query Library — ShareChat Product Analytics

All 15 queries run against `data/warehouse/sharechat_warehouse.db` (SQLite).
Redshift equivalents noted inline in each file.

To run any query:
```bash
python - <<EOF
import sqlite3, math
conn = sqlite3.connect("data/warehouse/sharechat_warehouse.db")
conn.create_function("SQRT", 1, lambda x: __import__("math").sqrt(max(x,0)) if x else None)
conn.create_function("POWER", 2, lambda x,y: x**y if x and y else None)
with open("sql/01_engagement_metrics.sql") as f:
    print(conn.execute(f.read()).fetchmany(5))
EOF
```

---

## Query Index

### 01 · Engagement Metrics (DAU/WAU/MAU + Stickiness)
**Business question:** How sticky is the platform day-to-day?

**SQL techniques:** CTEs, `LAG()`, `AVG() OVER` rolling window, self-join for WAU/MAU windows

**Plain English:** Computes daily active users, 7-day rolling average, 28-day MAU, weekly AU, and a stickiness ratio (DAU/MAU%). Day-over-day change flags growth vs. churn events.

**Product decision:** Triggers investigation when DAU/MAU falls; baseline for A/B test guardrails.

**Redshift difference:** Replace `DATE(session_start)` with `session_start::DATE`; `DATE('now', '-90 days')` with `CURRENT_DATE - 90`.

---

### 02 · Retention Cohorts (D1/D7/D14/D30)
**Business question:** Of users who signed up in a given week, what % came back?

**SQL techniques:** CTEs, self-join on user activity, `julianday()` date arithmetic, conditional aggregation across 4 retention windows

**Plain English:** Groups users by signup week and counts how many had a session on Day 1, 7, 14, and 30. Shows the classic social-app retention funnel.

**Product decision:** Identifies which acquisition cohorts have weak early retention (D1 < 35%), triggering onboarding A/B tests.

**Redshift difference:** Replace `julianday()` with `DATEDIFF('day', ...)`.

---

### 03 · Content Performance (Language × Category ER)
**Business question:** Which content category-language combos have the highest engagement rate?

**SQL techniques:** CTEs, `PERCENT_RANK()` and `NTILE(3)` window functions, multi-column GROUP BY, division with NULLIF guard

**Plain English:** For every language × content-category combination, calculates engagement rate (likes + shares + comments / views) and ranks categories within each language. Comedy in Hindi vs. Devotional in Tamil, etc.

**Product decision:** Content team prioritises creator incentives for high-engagement categories; feed algorithm gets per-language tuning signals.

**Redshift difference:** Identical — `PERCENT_RANK()` is ANSI SQL.

---

### 04 · Creator Analytics (Power-Law / Pareto)
**Business question:** What % of engagement comes from the top X% of creators?

**SQL techniques:** `NTILE(100)`, cumulative `SUM() OVER` with `ROWS UNBOUNDED PRECEDING`, running-total Lorenz curve

**Plain English:** Assigns each creator to an engagement percentile bucket, then shows how much of total engagement each bucket drives. Reveals the Pareto concentration — whether top 1% drive 40%+ of events.

**Product decision:** If top 1% drive >40% of engagement, their churn is existential — priority for creator monetisation / revenue share programs.

**Redshift difference:** Add `DISTKEY(creator_id)` to fact_engagement_events for this query pattern.

---

### 05 · Funnel Analysis (View → Like → Share → Follow)
**Business question:** Where do users drop off in the engagement funnel, and does this differ by city tier?

**SQL techniques:** CTEs, `MAX(CASE WHEN)` to find deepest funnel stage per user-post pair, conditional aggregation, CASE-based tier ordering

**Plain English:** For every user-post interaction, finds the deepest action taken (view = 1, like = 2, share = 3, follow = 4). Aggregates by city tier to show conversion rates at each stage.

**Product decision:** If Tier-3/4 drop sharply at the "share" step, the share UX has friction (data cost, app permission flow). If Tier-1 drops at "like", content relevance is the problem.

**Redshift difference:** Identical.

---

### 06 · A/B Test Analysis (Session Duration Lift)
**Business question:** Does the variant produce statistically significantly longer sessions?

**SQL techniques:** CTEs, variance computation via `E[X²] - E[X]²`, z-statistic formula, 95% confidence interval bounds, `CASE WHEN ABS(z) > 1.96` significance flag

**Plain English:** Computes per-group mean, variance, standard error, and z-statistic for session duration. One row output shows control vs. variant comparison with CI bounds and a significance verdict.

**Product decision:** The PM decision artifact — "ship / don't ship / iterate" on the tested feature.

**Redshift difference:** Replace `SQRT`/`POWER` with native math (Redshift supports both natively).

---

### 07 · Monetisation Analysis (Revenue by City Tier × Channel)
**Business question:** Which user segments are most valuable for ad monetisation?

**SQL techniques:** CTEs, `SUM(CASE WHEN)` pivot, CTR and CVR computation, `AVG() OVER` for revenue index

**Plain English:** Groups users by city tier and acquisition channel, computes impressions, clicks, conversions, CTR, CVR, ARPU, and eCPM. Shows which segments are monetisable vs. which are engagement-only.

**Product decision:** Ad ops prioritises fill rate for Tier-1 users; growth team targets acquisition channels with the best revenue-per-acquired-user.

**Redshift difference:** Redshift's `PIVOT` clause (2022+) is a cleaner alternative to `SUM(CASE WHEN)`.

---

### 08 · Anomaly Detection (14-Day Trailing Z-Score)
**Business question:** Which days had abnormal DAU, separating real anomalies from festival spikes?

**SQL techniques:** `AVG() OVER` and manual variance via `E[X²]-E[X]²` window functions (SQLite lacks native `STDDEV OVER`), `CASE` for classification, LEFT JOIN with `dim_date`

**Plain English:** Computes a z-score for each day's DAU against its trailing 14-day mean. Days with |z| > 2 are flagged as anomalies — except when it's a known festival day (expected spike vs. real alert).

**Product decision:** Engineering uses the non-festival ANOMALY flags to triage incidents; PM uses festival flags to attribute growth to content events.

**Redshift difference:** Use native `STDDEV() OVER` instead of the manual variance computation.

---

### 09 · Power Users (RFM Segmentation)
**Business question:** Who are our Champions, Loyal Users, and At-Risk users?

**SQL techniques:** `NTILE(5)` on Recency, Frequency, Monetary dimensions; combined score; `CASE WHEN` named segments; window function for % within group

**Plain English:** Scores each user on Recency (days since last session), Frequency (active days in 30d), and Monetary (watch minutes in 30d). Combines into 5 named segments from Champions to Lost.

**Product decision:** Retention team activates win-back campaigns for At-Risk; Champions get creator program invitations; Hibernating users get re-engagement push notifications.

**Redshift difference:** Add `DISTKEY(user_id)` to the session fact for this user-level aggregation pattern.

---

### 10 · Creator Retention (Weekly Posting Streaks)
**Business question:** How many creators maintain consistent weekly posting habits?

**SQL techniques:** `LAG()` to find previous posting week, `SUM(is_streak_start) OVER` to assign streak IDs (gap-and-island pattern), `MAX()` per creator for longest streak, distribution aggregation

**Plain English:** Detects consecutive-week posting runs for each creator. Shows distribution of max streak lengths — how many creators have ever posted 4+ consecutive weeks.

**Product decision:** Creator success team targets creators at their "2-week cliff" (week 2-3 is where most lapse) with coaching nudges; streaks feed creator-tier promotion criteria.

**Redshift difference:** `WITH RECURSIVE` is supported in Redshift as of 2021.

---

### 11 · Language Cross-Analysis (Consumption Matrix)
**Business question:** Do users consume content in languages other than their signup language?

**SQL techniques:** CTEs, `SUM(CASE WHEN)` pivot to build a matrix, percentage normalisation, self-join equivalent via CTE join

**Plain English:** Builds a 12×12 matrix: rows = user's signup language, columns = language of content they engaged with. Each cell = % of that user cohort's events on that content language.

**Product decision:** Feed algorithm team uses cross-language affinity signals — e.g., Hindi users consuming Bhojpuri content → serve Bhojpuri at higher weight for Hindi users.

**Redshift difference:** Redshift's `PIVOT` clause could replace the `SUM(CASE WHEN)` pattern.

---

### 12 · Session Patterns (Depth Distribution by Device)
**Business question:** Are low-end Android users getting meaningfully shorter sessions?

**SQL techniques:** `CASE WHEN` bucketing into 5 duration bins, conditional aggregation, % within device type via window division, crash-proxy count (<10 sec sessions)

**Plain English:** Assigns each session to a duration bucket (<1min, 1-5min, 5-15min, 15-30min, 30+min). Shows the distribution for each device tier. Low-end Android's "under 1 min" spike = crash indicator.

**Product decision:** Engineering prioritises APK size and cold-start time for Android-Low; product decides whether a ShareChat Lite is warranted.

**Redshift difference:** `WIDTH_BUCKET()` is a Redshift-native alternative to `CASE WHEN` bucketing.

---

### 13 · Festival Impact Analysis
**Business question:** How much do Indian festivals lift DAU and session duration?

**SQL techniques:** CTE join with `dim_date`, manual variance for Welch's t-test in SQL, `CROSS JOIN` for pivot arithmetic, percentage lift calculation

**Plain English:** Compares DAU, avg session duration, and like rate on festival days vs. normal days. Includes a t-statistic to test whether the festival lift is statistically significant.

**Product decision:** Content team pre-produces festival packs 2 weeks in advance; engineering pre-scales servers for Diwali/Holi/Eid; ad ops reserves premium inventory for festival windows.

**Redshift difference:** Replace `julianday()` with `DATEDIFF('day', ...)`.

---

### 14 · Device Segmentation (Crash Proxy + Engagement by Tier)
**Business question:** Are low-end Android users getting a worse product experience?

**SQL techniques:** Conditional aggregation for crash proxy, `ROW_NUMBER() OVER (PARTITION BY)` for top app version, multi-CTE JOIN, `MAX() OVER` for index baseline

**Plain English:** For each device tier, shows crash-proxy rate (<10s sessions), meaningful session rate (>60s), average session duration, and engagement rate from the event log.

**Product decision:** The session-duration index column directly compares Android-Low to iOS as a baseline 100. If the index is <70, the case for a lite app is strong.

**Redshift difference:** Add `DISTKEY(device_type)` or materialise device_sessions as a temp table for large scans.

---

### 15 · Cohort LTV (Watch Time + Revenue at 30/60/90 Days)
**Business question:** Which signup cohorts generate the most long-term value?

**SQL techniques:** 4-CTE chain, `strftime('%Y-%m')` cohort bucketing, `CASE WHEN days_since_signup <= N` for window accumulation, `AVG() OVER` for cohort quality index

**Plain English:** For each signup month, computes cumulative watch time per user and ad revenue per user at the 30-, 60-, and 90-day marks. The cohort quality index shows which months produced the most valuable users.

**Product decision:** Growth team increases onboarding investment for high-LTV cohorts; signals whether product improvements (e.g., new onboarding flow) translated into better-quality acquired users.

**Redshift difference:** Replace `julianday()` with `DATEDIFF('day', ...)` and `strftime('%Y-%m')` with `DATE_TRUNC('month', ...)`.
