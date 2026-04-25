# Data Dictionary — ShareChat Analytics Warehouse

Every field in every table. Source: `src/01_generate_data.py`.

---

## dim_date

| Column | Type | Description | Valid Values | Source |
|--------|------|-------------|--------------|--------|
| date | TEXT (YYYY-MM-DD) | Calendar date, primary key | 2024-04-25 to 2026-04-24 | Generated |
| day_of_week | TEXT | Full day name | Monday … Sunday | Derived from date |
| week_num | INTEGER | ISO week number | 1–53 | Derived from date |
| month | INTEGER | Calendar month | 1–12 | Derived from date |
| month_name | TEXT | Abbreviated month | Jan … Dec | Derived from date |
| year | INTEGER | Calendar year | 2024, 2025, 2026 | Derived from date |
| quarter | INTEGER | Quarter | 1–4 | Derived from date |
| is_weekend | INTEGER (bool) | 1 if Saturday or Sunday | 0, 1 | Derived from date |
| is_festival | INTEGER (bool) | 1 if a major Indian festival | 0, 1 | Mapped from festival list |
| festival_name | TEXT | Name of festival if applicable | Empty string or festival name | Mapped from festival list |

**Note:** Festival dates tagged: Diwali, Holi, Eid-ul-Fitr, Eid-ul-Adha, Dussehra, Raksha Bandhan, Ganesh Chaturthi, Onam, Pongal, Navratri, Christmas, New Year (both 2024 and 2025 occurrences where applicable).

---

## dim_users

| Column | Type | Description | Valid Values | Source |
|--------|------|-------------|--------------|--------|
| user_id | TEXT | Unique user identifier | U_0000001 – U_0050000; 20 TEST_ users | Generated (padded int) |
| signup_date | TEXT (YYYY-MM-DD) | Date user registered | 2024-04-25 to 2026-04-24 | Generated (exponential decay, more recent users) |
| signup_language | TEXT | Primary language at signup | Hindi, Telugu, Tamil, Bhojpuri, Marathi, Bengali, Kannada, Malayalam, Gujarati, Punjabi, Odia, Assamese | Generated (weighted: Hindi 35%) |
| city_tier | TEXT | City tier classification | Tier-1, Tier-2, Tier-3, Tier-4 | Generated (15/25/35/25 split) |
| age_bucket | TEXT | Age group | 13-17, 18-24, 25-34, 35-44, 45+ | Generated (skewed young: 18-34 = 68%) |
| gender | TEXT | Gender identity | M, F, Other | Generated (58/39/3 split) |
| device_type | TEXT | Device classification | Android-Low, Android-Mid, Android-High, iOS | Generated (60/25/10/5 split) |
| acquisition_channel | TEXT | How user was acquired | Organic, Paid, Referral, Preinstall | Generated (45/25/20/10 split) |
| experiment_group | TEXT | A/B test assignment | control, variant | Generated (50/50 random split) |

**DQ Issue:** 20 users have `user_id` starting with `TEST_` — filter with `WHERE user_id NOT LIKE 'TEST_%'` in all production queries.

---

## dim_creators

| Column | Type | Description | Valid Values | Source |
|--------|------|-------------|--------------|--------|
| creator_id | TEXT | Unique creator identifier | C_000001 – C_005000 | Generated |
| creator_signup_date | TEXT (YYYY-MM-DD) | Date creator registered | 2024-04-25 to 2026-04-24 | Generated |
| primary_language | TEXT | Creator's content language | Same 12 as dim_users | Generated (same weights) |
| follower_count | INTEGER | Current follower count | 100 – 10,000,000 | Generated (Pareto distribution, a=1.5) |
| creator_tier | TEXT | Tier derived from follower_count | Nano, Micro, Mid, Macro, Mega | Derived: Nano<1K, Micro<10K, Mid<100K, Macro<1M, Mega≥1M |
| content_category | TEXT | Primary content vertical | Comedy, Devotional, News, Music, Dance, Education, Lifestyle, Gaming, Regional-Drama | Generated (weighted) |
| is_verified | INTEGER (bool) | Platform-verified creator | 0, 1 | Generated (~3% verified) |

---

## dim_content

| Column | Type | Description | Valid Values | Source |
|--------|------|-------------|--------------|--------|
| post_id | TEXT | Unique post identifier | P_00000001 – P_00100000 | Generated |
| creator_id | TEXT (FK) | Creator who posted | References dim_creators.creator_id | Generated (weighted by tier — bigger creators post more) |
| post_date | TEXT (YYYY-MM-DD) | Date posted | Last 90 days from 2026-04-24 | Generated |
| content_type | TEXT | Format of content | ShortVideo, Image, Text, LiveStream | Generated (65/20/10/5 split) |
| language | TEXT | Language of content | Inherited from creator's primary_language | Derived from creator |
| duration_seconds | INTEGER | Duration for video/livestream; 0 for others | 15–90 for ShortVideo; 0 for Image/Text | Generated |
| has_music | INTEGER (bool) | Whether post has music | 0, 1 | Generated (~55% have music) |
| hashtag_count | INTEGER | Number of hashtags | 0–15 | Generated (uniform) |

---

## fact_sessions

| Column | Type | Description | Valid Values | Source |
|--------|------|-------------|--------------|--------|
| session_id | TEXT | Unique session identifier | S_000000001 – S_000500000 | Generated |
| user_id | TEXT (FK) | User who had the session | References dim_users.user_id | Generated |
| session_start | TEXT (YYYY-MM-DD HH:MM:SS) | Session start timestamp | Within last 90 days | Generated |
| session_end | TEXT (YYYY-MM-DD HH:MM:SS) | Session end timestamp | ≥ session_start (mostly) | Generated |
| session_duration_sec | INTEGER | Duration in seconds | 1 – ~7200 | Generated (log-normal, mean ~1100s) |
| posts_viewed | INTEGER | Posts viewed in session | 1 – 500 | Generated (proportional to duration) |
| posts_liked | INTEGER | Posts liked in session | 0 – posts_viewed | Generated |
| posts_shared | INTEGER | Posts shared in session | 0 – posts_viewed | Generated |
| posts_commented | INTEGER | Posts commented on | 0 – posts_viewed | Generated |
| device_type | TEXT | Device used | Android-Low, Android-Mid, Android-High, iOS | Inherited from dim_users |
| app_version | TEXT | App version | 14.5.0, 14.4.2, 14.3.1, 14.2.0, 13.9.0 | Generated (weighted toward recent) |

**Behavioral signals embedded:**
- Weekend sessions 30% longer (Sat/Sun multiplier)
- Tier-3/4 sessions 20% longer (leisure time effect)
- Variant group sessions 6% longer (A/B test signal)
- Android-Low has 7.92% crash-proxy sessions (< 10s)

**DQ Issue:** 523 sessions (~0.1%) have `session_end < session_start`. Filter with `WHERE session_end >= session_start`.

---

## fact_engagement_events

| Column | Type | Description | Valid Values | Source |
|--------|------|-------------|--------------|--------|
| event_id | TEXT | Unique event identifier | E_0000000001 – E_0020000000 | Generated |
| user_id | TEXT (FK) | User who triggered the event | References dim_users.user_id | Generated |
| post_id | TEXT (FK) | Post involved in the event | References dim_content.post_id | Generated |
| creator_id | TEXT (FK, DENORM) | Creator of the post — denormalised for query performance | References dim_creators.creator_id | Derived from dim_content |
| event_type | TEXT | Type of engagement | view, like, share, comment, follow, skip, report | Generated (62/15/7/5/4/6/1 split) |
| event_timestamp | TEXT (YYYY-MM-DD HH:MM:SS) | When the event occurred | Within last 90 days | Generated |
| watch_duration_sec | REAL | Seconds watched (video views only) | 3–90 for views; NULL for all other types | Generated |
| scroll_velocity | REAL | Scroll speed proxy (higher = faster scroll, lower engagement) | 0.5–5.0 | Generated |

**DQ Issues:**
- ~0.5% duplicate event_ids in the raw CSV (removed by `src/02_simulate_api_fetch.py` deduplication)
- ~1% of view events have null `watch_duration_sec` (instrumentation gap — expected in production)

---

## fact_ad_impressions

| Column | Type | Description | Valid Values | Source |
|--------|------|-------------|--------------|--------|
| impression_id | TEXT | Unique impression identifier | I_000000001 – I_000300000 | Generated |
| user_id | TEXT (FK) | User who saw the ad | References dim_users.user_id | Generated |
| ad_id | TEXT | Ad creative identifier | AD_00001 – AD_00500 | Generated (500 synthetic ads) |
| impression_timestamp | TEXT (YYYY-MM-DD HH:MM:SS) | When impression served | Within last 90 days | Generated |
| ad_category | TEXT | Advertiser category | Ecommerce, Gaming, Fintech, FMCG, Travel, Education | Generated (30/20/18/15/10/7 split) |
| was_clicked | INTEGER (bool) | 1 if user clicked | 0, 1 | Generated (tier-dependent CTR: 5% Tier-1 → 1.8% Tier-4) |
| was_converted | INTEGER (bool) | 1 if click led to conversion | 0, 1 | Generated (~10% of clicks convert) |
| revenue_inr | REAL | Revenue from this impression (₹) | 2–90 for clicks; NULL for non-clicks | Generated (higher for Tier-1) |

**Note:** ~97.2% of `revenue_inr` values are NULL (non-clicked impressions generate no direct revenue in this model). This is correct — only clicked impressions have revenue attached.
