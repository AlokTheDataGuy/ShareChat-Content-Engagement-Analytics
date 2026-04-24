# ShareChat Analytics Intelligence Platform

A professional product analytics dashboard built for the **ShareChat Product Analyst Internship** interview.

---

## What's Inside

```
sharechat-analytics/
├── app.py                     ← Main Streamlit dashboard (6 pages)
├── requirements.txt           ← Python dependencies
├── sql/
│   └── analysis_queries.sql   ← 11 Redshift-compatible SQL queries
├── docs/
│   └── interview_prep.md      ← Full interview prep guide & Q&A
└── README.md
```

---

## Quick Start

```bash
# 1. Install dependencies
pip install -r requirements.txt

# 2. Launch the dashboard
streamlit run app.py
```

The dashboard opens at `http://localhost:8501`.

---

## Dashboard Pages

| Page | What It Shows |
|---|---|
| **Overview** | Executive KPIs, 12-month revenue & MAU trends, platform share |
| **User Analytics** | Demographics (age, gender, device), language & region breakdown, session behaviour |
| **Content Performance** | Engagement by format, category market map, top content table |
| **Monetization** | Revenue waterfall, eCPM trends, ad format performance, ARPU by platform |
| **Retention** | Cohort heatmap (12 months), DAU trends (90 days), retention curve |
| **Language Analytics** | 15-language MAU, engagement, revenue, and creator metrics |

---

## Data

All data is **synthetic**, generated with `numpy` random seeds for reproducibility. The numbers are calibrated to match ShareChat's public metrics:

- **200M MMU** across ShareChat, Moj, and QuickTV
- **₹1,000 Cr ARR** at current run-rate
- **28% YoY revenue growth** trajectory
- **15 regional languages** with realistic language-share distributions
- **12-month cohort retention** modelled on social media industry benchmarks

---

## SQL Queries Included

1. DAU / MAU ratio calculation
2. Monthly cohort retention matrix
3. Content engagement funnel
4. Monthly revenue with YoY comparison
5. User RFM segmentation
6. Top creators by language & platform
7. 7-day and 30-day retention rates
8. Content virality score
9. Language-level monetisation efficiency
10. Feed quality / personalisation scoring
11. Week-over-week acquisition funnel

All queries are written for **Amazon Redshift** (PostgreSQL-compatible).

---

## Brand

Colours and design follow ShareChat's visual identity:
- Primary orange `#FF6B2C`
- Dark navy sidebar `#1A1A2E / #16213E`
- Inter typeface
- Indian market framing (₹, regional languages, Indian geography)
