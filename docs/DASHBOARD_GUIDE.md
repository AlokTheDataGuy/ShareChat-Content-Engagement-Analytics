# Dashboard Demo Guide — 5-Minute Interview Script

How to demo `dashboard/app.py` in a ShareChat product analyst interview.  
Launch: `streamlit run dashboard/app.py` from the project root.

---

## Before You Start

Have these numbers memorised (from the actual data):
- Session lift A/B test: **+6.2%** (variant vs. control)
- Tier-1 vs. Tier-3 ARPU: **₹13.92 vs ₹2.66** (5.2x gap)
- Android-Low crash proxy: **7.92%**

---

## Decision Tree — Which Demo Path to Take

```
Interviewer asks technical depth?
├── YES → Start on OVERVIEW (30s) → SQL WORKBENCH (2.5min) → A/B TEST (2min)
└── NO  → Start on OVERVIEW (1min) → MONETIZATION (1.5min) → USER ANALYTICS (1.5min) → A/B TEST (1min)
```

---

## Page-by-Page Script

### OVERVIEW Tab (30–60 seconds)
> "This is the weekly product review view. The top five KPI tiles show network-level health — MAU, revenue, stickiness, session duration, and new user volume.

> The dual-axis chart below shows revenue bars with the DAU/MAU stickiness line. I track both together because revenue can grow while engagement declines — a warning sign that you're monetising a shrinking base.

> The insight box at the bottom has one concrete observation. In an interview context, I'd always end a dashboard with a specific recommendation, not just a data summary."

**What to say if asked about the numbers:**  
"These are 12 months of synthetic data built with realistic ShareChat-scale parameters — 200M+ MMU range, regional language split matching the JD context."

---

### USER ANALYTICS Tab (60 seconds)
> "This page answers the question: who is our user? The language chart is the most important — ShareChat's entire strategic advantage is serving the 15 regional languages that English-first platforms ignore.

> The device distribution pie is a product decision input. 60% of users are on Android-Low devices. Any feature I ship has to work on a 2GB RAM budget phone with a slow connection — that's not a nice-to-have constraint, it's the primary user."

---

### MONETIZATION Tab (60 seconds)
> "This is the page I'd present to the Head of Revenue. The stacked bar shows revenue by platform, the waterfall shows QoQ growth attribution, and the ARPU chart by platform is the clearest monetisation health signal.

> The most interesting story here: if I flip to the Tier breakdown [navigate to SQL Workbench → Query 07], Tier-1 ARPU is ₹13.92 versus ₹2.66 for Tier-3. But Tier-3/4 users spend 20% more time on the platform. We're leaving money on the table in Bharat."

---

### A/B TEST Tab (90 seconds)
> "This is my favourite page because it maps directly to a shipping decision. The experiment is a feed redesign.

> [Point to bar chart] Variant session duration: 25.1 minutes. Control: 23.6 minutes. That's a +6.2% lift.

> [Point to z-score / significance box] z-statistic > 5 — highly significant. The 95% confidence interval is entirely above zero, so we're confident the lift is real, not sampling noise.

> [Point to segment cut] I ran a city-tier segment cut to check for Simpson's paradox — making sure the aggregate lift isn't hiding a decline in one segment. It's positive across all four tiers.

> Recommendation box at the bottom: SHIP. With specific guardrails — maintain ≥+5% lift in week 1, monitor D7 retention."

**If asked "How did you set up the test?"**  
> "50/50 random split on `experiment_group` in the user dimension. The assignment was done at registration time — it's a stable treatment assignment, not session-by-session randomisation."

---

### SQL WORKBENCH Tab (2 minutes — strongest technical signal)
> "This page lets me run any of the 15 SQL queries I wrote directly against the warehouse. I'll pull up the A/B test query.

> [Select Query 06 → Run Query]

> The query computes variance via E[X²] - E[X]² without leaving SQL — avoiding the need to pull data into Python just to compute a z-score. All the statistical logic — standard error, z-statistic, confidence intervals, and a significance verdict — is computed entirely in SQL.

> For a Redshift production environment, I'd swap `julianday()` with `DATEDIFF()` and add a DISTKEY on user_id to optimise the join performance on a multi-billion-row fact table."

**If asked "Can you walk me through Query 04?"**  
> [Select Query 04 — Creator Power Law → Run Query]  
> "This uses NTILE(100) to bucket creators by engagement percentile, then SUM() OVER with ROWS UNBOUNDED PRECEDING to build a cumulative share — effectively a Lorenz curve in pure SQL. The result shows exactly how concentrated engagement is across the creator base."

---

### RETENTION Tab (optional, 60 seconds)
> "The heatmap is a cohort retention matrix — each row is a signup month, each column is months since signup. The colour gradient from orange to purple shows retention decay.

> The retention curve below shows the platform average. D1 around 48%, D7 around 35%, D30 around 20%. These numbers are above industry benchmarks for social apps — suggesting the regional-language strategy creates a strong daily habit loop that generic platforms can't replicate."

---

## Common Follow-Up Questions

**"How would you scale this to real ShareChat data?"**
> "The SQL is already written in Redshift syntax — I'd point the connection string at the production Redshift cluster instead of SQLite. The `src/03_build_warehouse.py` comments document the DISTKEY, SORTKEY, and ENCODE choices I'd apply. The biggest change would be turning `02_simulate_api_fetch.py` into a real Airflow DAG that polls the engagement event API on an hourly cadence."

**"What's the biggest limitation of this analysis?"**
> "The behavioral signals are synthetic — I modelled them to match documented ShareChat dynamics, but the actual numbers should be validated against production data. Specifically, the 7.92% Android-Low crash proxy and the 5.2x Tier-1/Tier-3 ARPU gap need production validation before driving budget decisions."

**"Why didn't you build an ML model?"**
> "Deliberate scope decision. A PM asking 'which users will churn?' doesn't need a gradient boosted tree — they need an RFM segment that a campaign manager can act on today. The RFM query in Query 09 produces the same actionable segments in pure SQL, runs in seconds against 2M events, and can be explained to a non-technical stakeholder in one sentence. I can build the ML model; the question is whether it's the right tool for this use case."
