# Project Report — ShareChat Creator & Content Engagement Analytics

**Author:** Product Analyst Internship Portfolio Project  
**Date:** April 2026  
**Tech Stack:** Python · SQLite · SQL (Redshift-compatible) · Streamlit · Plotly · Jupyter

---

## 1. Executive Summary

This project builds a complete product analytics pipeline for a multi-language short-video platform modelled on ShareChat's architecture. It demonstrates the full product analyst workflow: data modelling, SQL-first analysis, A/B test evaluation, user segmentation, and structured findings delivery — without any machine learning.

Three analytical questions frame the work:
1. **Who stays, who churns, and why?** (retention and engagement)
2. **Which content types, languages, and creator tiers drive the platform?** (content analytics)
3. **Which user segments show highest monetisation intent?** (monetisation lens)

Key findings:
- Tier-3/4 users have **20% longer sessions** but generate only **19% of Tier-1's ARPU** — the monetisation gap is the clearest near-term revenue opportunity
- **7.92% of Android-Low sessions** are under 10 seconds (crash-proxy) vs. 0% on all other device tiers — a tractable engineering fix with platform-wide impact
- A tested feed redesign variant delivers a **+6.2% session duration lift** (p < 0.001) — recommendation is to ship

---

## 2. Business Context

ShareChat (Mohalla Tech) is India's only major social media company profitable at scale, serving 15 regional languages across its ShareChat, Moj, and QuickTV platforms. Its strategic advantage is serving the ~450M Indian internet users who are not comfortable consuming English content — a segment ignored by Meta, YouTube, and TikTok India.

Two structural dynamics make product analytics at ShareChat distinctive:

**Regional language fragmentation.** No single language is majority. Hindi at 35% is the largest cohort but is itself fragmented across Hindi-speaking states. Marathi, Bengali, Telugu, and Tamil each represent tens of millions of users with distinct content preferences. A product change that works for Hindi users may actively hurt Bhojpuri engagement — language-level segment cuts are not optional, they are mandatory.

**Android-first, low-end first.** 60% of users are on Android-Low devices (≤ 3GB RAM, budget chipset). Product decisions that are neutral or positive on a flagship device can be actively harmful on the primary device. APK size, cold-start latency, and network tolerance are first-class product metrics, not engineering concerns.

---

## 3. Data Model

The warehouse uses a **star schema** with three fact tables and four dimension tables.

**Dimension tables** (slowly-changing reference data):
- `dim_users` — 50,000 user profiles with signup language, city tier, device, A/B group
- `dim_creators` — 5,000 creators with power-law follower distribution and tier classification
- `dim_content` — 100,000 posts with creator, language, format, and metadata
- `dim_date` — 731 calendar days with festival flags and weekend indicators

**Fact tables** (high-volume event data):
- `fact_sessions` — 500,000 session records with duration, engagement counts, device
- `fact_engagement_events` — 2,000,000 interaction events (view/like/share/comment/follow/skip)
- `fact_ad_impressions` — 300,000 ad impressions with CTR and revenue

**Why star schema?** Star schema optimises analytical query performance by keeping joins simple (one fact, one or two dimensions) and enabling efficient GROUP BY at any dimension granularity. In Redshift production, dimension tables (< 100K rows) would be replicated to all nodes (DISTSTYLE ALL) to eliminate data shuffling on joins with large fact tables.

**Why denormalise `creator_id` into `fact_engagement_events`?** The most common query pattern is filtering or grouping by creator. Without denormalisation, every such query joins `fact_engagement_events` (2M rows) through `dim_content` (100K rows) to reach `dim_creators`. By storing `creator_id` directly on the fact, we trade ~8 bytes per event row for a significant query speedup. This is explicitly documented in the schema as a warehouse best practice.

---

## 4. Methodology

### Data Generation
Synthetic data generated in `src/01_generate_data.py` using NumPy with `seed=42` for reproducibility. All behavioral signals are parameterised:

- **Retention curve:** log-normal session duration with tier and experiment multipliers produces a realistic D1/D7/D30 retention shape
- **Language distribution:** Hindi 35%, followed by Telugu/Tamil/Bhojpuri/Marathi/Bengali in proportions matching ShareChat's reported language split
- **Device distribution:** 60% Android-Low, matching the Bharat internet demographic
- **A/B test signal:** variant group receives a deterministic 6% session duration multiplier, detectable by the SQL z-test query

### API Simulation
`src/02_simulate_api_fetch.py` demonstrates the JD-required "scripting to fetch data from API endpoints" skill. It implements pagination (201 pages × 10K rows), retry with exponential backoff (5% simulated failure rate), rate limiting (5 RPS), and deduplication (removes the ~0.5% duplicate events planted in the raw data). The script is production-extensible: adding real auth headers and endpoint URLs is a configuration change, not a code change.

### Warehouse Build
`src/03_build_warehouse.py` loads all CSVs into SQLite at `data/warehouse/sharechat_warehouse.db` with proper DDL (primary keys, foreign keys, 18 indexes). The Redshift equivalents (DISTKEY, SORTKEY, ENCODE choices) are documented as comments. Database size: ~547 MB.

### Data Quality
`src/04_data_quality_checks.py` runs eight check categories: row counts, null rates, referential integrity, date validity, duplicates, TEST_ user IDs, domain validation, and distribution sanity. All 7 tables pass with only the three intentionally planted DQ issues flagged.

### SQL Analysis
15 queries written in Redshift-compatible SQL, tested against SQLite. Techniques demonstrated:
- Window functions: LAG, NTILE, PERCENT_RANK, SUM/AVG OVER with ROWS frames
- CTEs: up to 4-CTE chains, recursive pattern for streak detection
- Statistical logic: z-test, t-test, variance via E[X²]-E[X]², confidence intervals
- Pivoting: SUM(CASE WHEN) matrix construction
- Date arithmetic: cohort windows, day offsets, festival joins

---

## 5. Key Findings

### Finding 1: The Monetisation-Engagement Inversion

Tier-3/4 users (60% of the user base) average **26.1 minutes per session** vs. 21.6 minutes for Tier-1. Yet Tier-3 ARPU is ₹2.66 vs. ₹13.92 for Tier-1 — a **5.2x gap**. Per-minute-of-attention revenue is ₹0.10 for Tier-3 vs. ₹0.64 for Tier-1 — a **6.4x efficiency gap**.

This is not surprising (Tier-1 users have higher disposable income and advertiser demand is concentrated there) but it is quantifiable, and the gap is larger than the engagement gap justifies. Three levers to close it: (1) develop demand from Tier-3/4-relevant ad categories (regional FMCG, fintech, education), (2) improve ad relevance for regional-language inventory, (3) test higher ad load for longer sessions.

### Finding 2: Android-Low Experience Deficit

7.92% of Android-Low sessions end in under 10 seconds — a metric we call the "crash proxy." On Android-Mid, High, and iOS, this rate is 0.00%. Android-Low sessions also average 23.5 minutes vs. 25.6 minutes on all other tiers — a 2.1-minute gap.

Given 60% of users are on Android-Low, a 1pp reduction in crash-proxy rate (say, from 7.92% to 6.92%) directly improves ~1,000 user sessions per 10,000 daily sessions. At scale, this translates to meaningful DAU retention improvement. The fix is an engineering investment: APK size reduction, cold-start profiling, network-failure graceful degradation.

### Finding 3: A/B Test — Ship the Feed Redesign

The variant feed produced a statistically significant +6.2% session duration lift (1,503s vs 1,416s, p < 0.001, 95% CI [+5.0%, +7.4%]). The lift is consistent across all four city tiers — no Simpson's paradox. Engagement rate shows marginal positive movement within noise. Recommendation: ship, with Week-1 guardrails on session duration and D7 retention.

---

## 6. Product Recommendations

1. **Ship the variant feed** (Low effort, High impact) — statistically robust, no guardrail failures
2. **Tier-3/4 monetisation program** — develop demand for regional-language, Tier-3/4 ad inventory; A/B test a 20% higher ad load for sessions > 20 minutes in Tier-3/4
3. **Android-Low performance sprint** — target crash-proxy rate < 2% (from 7.92%); prioritise APK size and cold-start
4. **Creator streak incentive** — 4-week posting streak milestone to push creators past the week-3 lapse cliff; low effort, meaningful for mid-tier creator retention

---

## 7. Limitations and Assumptions

- **Synthetic data:** Behavioral signals are designed to match documented ShareChat dynamics but are not validated against production telemetry
- **No ML models:** Deliberate scope — RFM segmentation, funnel analysis, and cohort LTV provide the same actionable outputs as ML classification at a fraction of the complexity
- **Observation window:** 90 days — too short for robust D30/D60/D90 LTV estimation for recent cohorts
- **Ad revenue model:** Simplified (click → revenue); real attribution is multi-touch and requires advertiser-side conversion data
- **Creator power law:** Synthetic creator tier distribution (mostly Nano/Micro) is realistic but compressed vs. a real platform with 1M+ creators

---

## 8. Future Work

- **Real data integration:** Point `src/02_simulate_api_fetch.py` at ShareChat's internal API; the pagination/retry/dedup logic is production-ready
- **Airflow pipeline:** Wrap the four `src/` scripts in a DAG for daily incremental loads
- **Granular creator LTV:** Track revenue attribution per creator (ad revenue on content they created)
- **Personalisation A/B infrastructure:** Extend the A/B test framework to support multi-arm experiments and Bayesian stopping rules
- **Language-level anomaly detection:** Extend Query 08 to detect per-language DAU anomalies (a regional language outage is hidden in aggregate DAU)
