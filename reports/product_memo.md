# Product Memo: Tier-3/4 Monetisation Gap & A/B Test Readout

**From:** Product Analytics  
**To:** Product & Monetisation Teams  
**Date:** April 2026  
**Status:** Final — For Review

---

## TL;DR

- Tier-3/4 users spend **20% more time** on platform than Tier-1 (26.1 min vs 21.6 min avg session) but generate only **19% of Tier-1's ad revenue per user** (₹2.66 vs ₹13.92 ARPU).
- Android-Low users — **60% of the user base** — experience a **7.92% crash-proxy rate** (sessions under 10 seconds) vs. 0% on all other device tiers.
- A tested feed redesign **(variant)** lifts session duration **+6.2%** (1,503s vs 1,416s, p < 0.001) — recommendation is to ship.

---

## Context

ShareChat's user base skews heavily toward Tier-3 and Tier-4 cities and Android-Low devices — the same segments that drive the highest session engagement but the lowest ad monetisation. This analysis quantifies that gap using 90 days of synthetic event data (2M engagement events, 500K sessions, 300K ad impressions) structured as a star-schema warehouse.

Three questions drove this work:
1. How large is the monetisation-engagement gap between city tiers, and where is revenue being left on the table?
2. Is there a meaningful product experience gap on Android-Low that's suppressing engagement?
3. Should we ship the current feed redesign variant?

---

## Approach

Data modelled in a star schema: `dim_users`, `dim_creators`, `dim_content`, `dim_date` as dimensions; `fact_sessions`, `fact_engagement_events`, `fact_ad_impressions` as facts. All analysis run in SQL against a local SQLite warehouse (queries designed for Redshift production equivalents). A/B test significance assessed via Welch's two-sample t-test.

---

## Key Findings

### Finding 1 — The Monetisation-Engagement Inversion

**Tier-3/4 users are 20% more engaged but generate 6x less revenue per minute of attention.**

| City Tier | Avg Session | Ad CTR | ARPU (₹) | Revenue/min (₹) |
|-----------|-------------|--------|-----------|-----------------|
| Tier-1    | 21.6 min    | 4.91%  | ₹13.92    | ₹0.64           |
| Tier-2    | 21.8 min    | 3.51%  | ₹6.78     | ₹0.31           |
| Tier-3    | 26.1 min    | 2.13%  | ₹2.66     | ₹0.10           |
| Tier-4    | 26.1 min    | 1.80%  | ₹1.65     | ₹0.06           |

Tier-3/4 users collectively contribute the majority of platform watch time (longer sessions + higher user count in 35%/25% Tier-3/4 split), yet their revenue-per-minute-of-attention is **6–10x lower** than Tier-1. This is the clearest monetisation opportunity in the dataset.

**Why this happens:** Tier-3/4 users receive the same ad inventory mix as Tier-1, but ad demand (and CPMs) from brand advertisers is concentrated on Tier-1 audiences. The ad quality, relevance, and price are lower for Tier-3/4 inventory.

**Source:** `sql/07_monetization_analysis.sql` — Revenue/CTR by city_tier × acquisition_channel.

---

### Finding 2 — Android-Low Has a Measurable Experience Deficit

**7.92% of Android-Low sessions are under 10 seconds — 8x higher than any other device tier.**

| Device        | Crash Proxy Rate | Avg Session |
|---------------|-----------------|-------------|
| Android-Low   | **7.92%**       | 23.5 min    |
| Android-Mid   | 0.00%           | 25.6 min    |
| Android-High  | 0.00%           | 25.4 min    |
| iOS           | 0.00%           | 25.6 min    |

Android-Low users also have sessions **2.1 minutes shorter** on average than Android-Mid/High. Given that 60% of users are on Android-Low devices, fixing this segment's experience is a platform-wide engagement lever.

The crash-proxy rate (< 10 second sessions) is a conservative proxy. The true cold-start failure rate could be higher — this metric only captures users who opened the app and immediately bailed, not users who never opened a fresh install.

**Source:** `sql/14_device_segmentation.sql` — Device tier × crash proxy × session depth.

---

### Finding 3 — Creator Concentration Risk

**The top 1% of creators (50 creators) drive 3.1% of total platform engagement; the top 10% drive ~30%.**

This looks lower than a typical Pareto distribution because the synthetic dataset intentionally models 5,000 creators with a realistic follower-count distribution. Mid-tier creators (10K-100K followers) are the engagement backbone — their content is seen by the broadest audience.

Key risk: if Micro and Mid-tier creators (1K-100K followers) churn at the "week 3 posting cliff", the platform loses its content diversity engine. Most creators in the dataset lapse after 1-2 weeks of consecutive posting — week 2-3 is the critical intervention window.

**Source:** `sql/04_creator_analytics.sql` and `sql/10_creator_retention.sql`.

---

### Finding 4 — A/B Test: Ship the Feed Redesign

**The variant feed produces a statistically significant +6.2% session duration lift (p < 0.001).**

| Group   | Users   | Avg Session | Lift    |
|---------|---------|-------------|---------|
| Control | 24,864  | 1,416s (23.6 min) | —    |
| Variant | 25,136  | 1,503s (25.1 min) | +6.2% |

- **95% CI on the lift:** [+5.0%, +7.4%]
- **z-statistic:** > 5 (highly significant)
- **Segment cuts:** Lift is positive across all city tiers — no Simpson's paradox concern
- **Secondary metric (engagement rate):** Marginal positive movement, within noise

**Source:** `sql/06_ab_test_analysis.sql` — Full z-test readout.

---

## Recommendations

| # | Recommendation | Owner | Effort | Impact |
|---|----------------|-------|--------|--------|
| 1 | **Ship the feed redesign variant** — statistically significant +6.2% session lift with no guardrail failures | Product | Low (flag flip) | High |
| 2 | **Improve Tier-3/4 ad relevance** — Work with ad ops to develop demand for regional-language, tier-3/4 inventory. A 50% lift in Tier-3 ARPU alone would add significant revenue given the user volume | Monetisation | Medium | High |
| 3 | **Android-Low performance sprint** — Fix cold-start latency and APK bloat to reduce the 7.92% crash-proxy rate. Target < 2% (match Android-Mid). Every 1pp improvement on Android-Low (~30K users) directly lifts platform DAU | Engineering | Medium | High |
| 4 | **Creator streak incentive program** — Introduce a 4-week posting streak milestone (badge + 10% revenue share boost) to push creators past the week-3 lapse cliff | Creator Products | Low | Medium |

---

## Risks and Assumptions

- **Synthetic data:** All figures are from a statistically realistic but synthetic dataset. The directional patterns (tier monetisation gap, Android-Low crash rate, A/B lift) are designed to match documented ShareChat platform dynamics, but exact numbers should be re-run against production data.
- **A/B test guardrails:** The recommendation to ship assumes D7 retention and ad CTR are monitored post-launch. If D7 retention drops > 2pp, pause and investigate.
- **Creator power-law interpretation:** The 3.1% figure for top-50 creators is lower than typical because the synthetic data uses a uniform engagement assignment weighted by creator tier, not a pure Pareto. In production, the concentration would likely be higher.
- **ARPU computation:** Computed on users with at least one ad impression in the 90-day window. Non-monetisable users are excluded, which overstates ARPU vs. a total-user denominator.

---

## Appendix

### Queries Used
- Monetisation analysis: `sql/07_monetization_analysis.sql`
- Device segmentation: `sql/14_device_segmentation.sql`
- Creator power law: `sql/04_creator_analytics.sql`
- Creator retention: `sql/10_creator_retention.sql`
- A/B test readout: `sql/06_ab_test_analysis.sql`

### Data Caveats
- 90-day observation window (Jan 25 – Apr 24, 2026 in synthetic data)
- 50,000 users, 5,000 creators, 100,000 posts, 2M engagement events, 300K ad impressions
- Known DQ issues: 523 sessions with impossible duration (filtered); 20 TEST_ user IDs (filtered); ~1% null watch_duration on view events (instrumentation gap)

### Open Questions
1. What is the true cold-start failure rate on Android-Low (beyond the < 10s proxy)?
2. What are the top ad categories served to Tier-3/4 users, and how does demand compare to Tier-1?
3. Is the feed variant lift stable beyond the 90-day observation window, or is it a novelty effect?
