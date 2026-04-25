# Interview Preparation Guide — ShareChat Product Analyst Intern

---

## 1. About ShareChat (Know This Cold)

| Fact | Detail |
|------|--------|
| Full name | Mohalla Tech Pvt Ltd |
| Founded | 2015 (Varanasi, IIT Kanpur alumni team) |
| Platforms | ShareChat (social), Moj (short video), QuickTV (micro drama) |
| Languages | 15 regional languages — only major platform doing this at scale |
| MMU | 200M+ Monthly Monetizable Users |
| Revenue | ₹1,000 Crore+ ARR, 28% YoY growth (Q2 FY26) |
| Profitability | Only Indian social media company to achieve profitability |
| QuickTV | 10M downloads in 3 months of launch |
| Key thesis | India has ~600M internet users; only ~150M comfortable with English — ShareChat owns the other 450M ("Bharat" internet) |

**Why ShareChat matters to a product analyst:**
The 15-language strategy means no single feature decision is platform-universal. Every A/B test, every funnel analysis, every retention cohort needs to be cut by language. This is what makes the PM job harder and more interesting than a single-language app.

---

## 2. Project Narrative (Memorise This Paragraph)

> "I built a full-stack product analytics project to demonstrate the kind of work a Product Analyst does at ShareChat day-to-day. The project generates a realistic synthetic dataset — 50,000 users, 5,000 creators, 2 million engagement events — models it as a Redshift-style star schema, and builds 15 SQL queries covering retention cohorts, funnel analysis, creator power-law, A/B testing, anomaly detection, and cohort LTV. I deliberately scoped this as product analytics without ML — because the questions a PM needs answered (who's churning, where's the funnel drop-off, does this feature work) are better answered by well-written SQL and clear metric definitions than by a black-box model. The keystone deliverable is a product memo that uses real numbers from the data to make three specific product recommendations: ship the feed redesign variant, prioritise Tier-3/4 monetisation, and fix Android-Low crash rates."

---

## 3. STAR Answers

### "Walk me through this project."
**Situation:** Wanted to build a portfolio piece that demonstrates product analytics skills for a ShareChat-style role.
**Task:** Build an end-to-end product analytics system — data pipeline, warehouse, SQL analysis, A/B testing, dashboard.
**Action:** Generated 2M events in a star schema. Wrote 15 SQL queries in Redshift-compatible syntax. Built a Streamlit dashboard with 8 pages including a live SQL workbench. Wrote a product memo with specific recommendations grounded in real numbers.
**Result:** A complete, interview-ready project that demonstrates SQL depth, product thinking, and statistical rigour — without any ML.

### "Why did you scope it without ML?"
Product analysts answer product questions, not research questions. The questions in this project — "who is churning?", "does this feature work?", "which creators are at risk?" — have precise answers in SQL and statistics. An RFM segmentation in SQL runs in seconds, produces interpretable segments, and can be explained to a non-technical PM in one sentence. A gradient boosted classifier for the same problem takes a week to build, requires feature engineering, and produces segments nobody can act on. The right tool for the right question.

### "Hardest part?"
The trickiest piece was ensuring the synthetic data's behavioral signals are detectable by the SQL queries. The A/B test signal (+6.2% session lift) needs to be statistically significant at n=25K per group. The festival impact needs to clear a 2-sigma threshold. Getting all of these to work together while maintaining realistic distributions required careful parameterisation of the data generator.

### "How would you scale this to real ShareChat volume?"
Three changes: (1) Point `02_simulate_api_fetch.py` at the real internal API — the pagination/retry/dedup logic is production-ready. (2) Swap SQLite for Redshift — the SQL is already Redshift-compatible; add DISTKEY on user_id for fact tables and DISTSTYLE ALL for dimension tables. (3) Wrap the four src/ scripts in an Airflow DAG for daily incremental loads.

---

## 4. Product Analytics Technical Prep

### Metric Definitions (from reports/metrics_definitions.md)

| Metric | Formula | Key Pitfall |
|--------|---------|-------------|
| DAU | COUNT(DISTINCT user_id) in a day | 1-second sessions count — presence metric, not engagement |
| WAU | DISTINCT users in rolling 7 days | Partial week at data start understates WAU |
| MAU | DISTINCT users in rolling 28 days | Specify 28-day rolling vs. calendar-month |
| Stickiness | DAU / MAU | Can't exceed 1.0; healthy social apps: 40-50% |
| D7 Retention | Users active day 6-8 / cohort size | Recent cohorts are truncated — check data freshness |
| Session Duration | session_end - session_start | Filter session_end < session_start (DQ issue) |
| Engagement Rate | (likes+shares+comments) / views | Varies by content type — normalise before comparing |
| CTR | clicks / impressions | Measures intent, not purchase intent |
| ARPU | Revenue / active users | Always specify denominator |

### How do you measure success of a new feature?
Framework: **North Star + Guardrails + Counters**
1. **North Star:** What single metric proves the feature is working?
2. **Guardrails:** What metrics must NOT deteriorate? (D7 retention, CTR, ad revenue)
3. **Counters:** Supporting metrics that explain the North Star movement

### How do you define a power user?
ShareChat working definition (from `sql/09_power_users.sql`): User meeting ALL three in 30 days:
- **Recency:** Active in last 7 days (R-score ≥ 4)
- **Frequency:** Active on ≥ 15 days out of 30 (F-score ≥ 4)
- **Monetary:** ≥ 500 minutes total watch time (M-score ≥ 4)

### DAU Drop Diagnostic Tree
```
DAU drops unexpectedly
├── All languages or one? → One = regional issue (carrier, OEM-specific crash)
├── All devices or one?   → Android-Low only = new release broke low-end
├── All channels or one?  → Paid only = acquisition campaign paused
├── Festival effect?      → Check dim_date.is_festival
├── Recent release?       → Check app_version distribution in fact_sessions
└── Sessions stable but DAU fell? → Fewer notifications reaching users
```

### A/B Test Setup
1. State causal hypothesis
2. Choose primary metric + guardrails
3. Power analysis (n = 2*(z_α + z_β)² * σ² / δ²)
4. Randomise at user level (not session level) for stable treatment
5. Run ≥ 2 weeks to capture weekly seasonality
6. Welch's t-test for continuous; chi-square for proportions
7. Segment cuts to check Simpson's paradox
8. Pre-commit to decision criteria before running

### Cohort vs. Snapshot
- **Snapshot:** "How many users are in each RFM segment today?" — current-state reporting
- **Cohort:** "Of Jan signups, what % are active in April?" — causal analysis, retention curves

**Simpson's Paradox:** Overall engagement rate falls, but within each language it rises. Composition shifted toward lower-engagement languages — aggregate is misleading.

---

## 5. SQL Deep Dive

### Window Functions vs. Aggregates
```sql
-- Aggregate: collapses to one row per group
SELECT city_tier, AVG(session_duration_sec) FROM fact_sessions GROUP BY 1;

-- Window: adds aggregate alongside each original row
SELECT session_id, city_tier, session_duration_sec,
       AVG(session_duration_sec) OVER (PARTITION BY city_tier) AS tier_avg
FROM fact_sessions;
```

### ROW_NUMBER vs. RANK vs. DENSE_RANK
Values: 100, 90, 90, 80
- `ROW_NUMBER`:  1, 2, 3, 4 — unique, arbitrary tie-breaking
- `RANK`:        1, 2, 2, 4 — ties get same rank, gap after
- `DENSE_RANK`:  1, 2, 2, 3 — ties get same rank, no gap

Use `ROW_NUMBER` for deduplication. Use `DENSE_RANK` for "top N" without gaps.

### CTEs vs. Subqueries
- **CTE:** Readable, reusable, self-documenting. Use for complex/reused logic.
- **Subquery:** Inline, one-off. Use for simple filter in WHERE/FROM.
- **Redshift note:** CTEs may be materialised — for very large CTEs, use explicit `CREATE TEMP TABLE`.

### Redshift-Specific
- **DISTKEY:** Distributes rows across nodes on the chosen column — use highest-cardinality JOIN column (`user_id`)
- **SORTKEY:** Physically sorts data for range-scan optimisation — use most-filtered column (`event_timestamp`)
- **DISTSTYLE ALL:** Replicates entire table to every node — use for small dimensions (< 100K rows)
- **VACUUM:** Reclaims space, re-sorts after bulk deletes
- **ANALYZE:** Updates query planner statistics — run after VACUUM

---

## 6. ShareChat Context

### 15 Regional Languages (Approximate Shares)
Hindi 35% · Telugu 12% · Tamil 10% · Bhojpuri 8% · Marathi 7% · Bengali 7% · Kannada 6% · Malayalam 5% · Gujarati 4% · Punjabi 3% · Odia 2% · Assamese 1%

**Dynamics:** Bhojpuri and Hindi cross-consume heavily. South Indian languages (TN/AP/KA/KL) skew higher-income → better monetisation. Small languages have passionate but thin creator ecosystems.

### City Tiers
- **Tier-1 (metros):** High income, high CPMs, already served by global platforms
- **Tier-2 (state capitals, large cities):** Core acquisition cohort
- **Tier-3/4 (smaller towns):** Longest sessions, lowest CPMs, ShareChat's strategic moat

### Android-Heavy User Base
- 95% Android, 60% Android-Low (≤ 3GB RAM)
- APK size, cold-start, battery drain are product metrics — not niceties
- Features requiring persistent background processes can cause app death on low-end devices

### Creator Economy Basics
- Power law: top 1-5% of creators generate disproportionate engagement
- Tier progression: Nano (< 1K) → Micro → Mid → Macro → Mega (> 1M)
- Mid-tier creators churn most: enough reach to feel monetisation limitations, not enough to benefit from creator funds

---

## 7. Numbers to Memorise From This Project

| Metric | Value |
|--------|-------|
| Tier-1 avg session | 21.6 min |
| Tier-3/4 avg session | 26.1 min (20% longer) |
| Tier-1 ARPU | ₹13.92 |
| Tier-3 ARPU | ₹2.66 (5.2x gap) |
| Tier-1 CTR | 4.91% |
| Tier-3 CTR | 2.13% |
| Android-Low crash proxy | 7.92% |
| A/B variant session lift | +6.2% (p < 0.001) |
| A/B control avg session | 1,416s (23.6 min) |
| A/B variant avg session | 1,503s (25.1 min) |
| Total engagement events | 2,000,000 |
| Total session rows | 500,000 |
| Total ad impressions | 300,000 |

---

## 8. Behavioural Questions

**"Tell me about a time you found an insight others missed."**
> The Tier-3/4 monetisation gap: "The instinct is to see Tier-1 as the most valuable users. But when I computed revenue-per-minute-of-attention, Tier-3/4 users are more engaged (20% longer sessions) but generate 6x less revenue per minute. That reframes the question: not 'how do we get more Tier-1 users?' but 'how do we monetise Tier-3/4's existing engagement better?'"

**"How do you prioritise when you have multiple asks?"**
> Impact × Confidence / Effort. Tier-3/4 monetisation: large impact (60% of users), high confidence (we have the data), low-effort first step (ad relevance analysis). Android-Low: large impact (60% of users), high confidence (crash-proxy is unambiguous), medium effort (engineering sprint).

**"Tell me about a time you were wrong."**
> "I initially framed Android-Low analysis as 'shorter sessions = lower engagement.' But the crash-proxy analysis showed 7.92% of sessions under 10 seconds — those aren't unengaged users, they're crashed app instances. The user wanted to engage but the app failed them. Completely different recommendation: engineering fix, not content strategy fix."

---

## 9. Questions to Ask the Interviewer

1. "What does the weekly product review meeting look like — what data does the team pull before it?"
2. "How does the analytics team work with data engineering on new metric definitions?"
3. "What's the biggest measurement challenge the team is wrestling with right now?"
4. "How do you think about defining 'meaningful engagement' for the Bharat user — is watch time the right proxy?"
