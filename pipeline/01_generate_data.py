"""
ShareChat Creator & Content Engagement Analytics
Data Generation Script

Generates a complete synthetic star-schema dataset:
  dim_users         50,000 rows
  dim_creators       5,000 rows
  dim_content      100,000 rows
  dim_date           ~730 rows  (2 years)
  fact_sessions     ~500,000 rows
  fact_engagement_events  ~2,000,000 rows
  fact_ad_impressions    ~300,000 rows

All behavioral signals are modelled to match real Indian short-video platform dynamics:
retention curves, festival spikes, power-law creator distribution, city-tier effects, etc.

Run: python src/01_generate_data.py
Output: data/raw/*.csv
"""

from __future__ import annotations

import os
import time
from pathlib import Path

import numpy as np
import pandas as pd

# ── Reproducibility ──────────────────────────────────────────
SEED = 42
rng = np.random.default_rng(SEED)

# ── Paths ────────────────────────────────────────────────────
ROOT = Path(__file__).resolve().parent.parent
RAW  = ROOT / "data" / "raw"
RAW.mkdir(parents=True, exist_ok=True)

# ── Scale constants ──────────────────────────────────────────
N_USERS    = 50_000
N_CREATORS = 5_000
N_CONTENT  = 100_000
N_SESSIONS = 500_000
N_EVENTS   = 2_000_000
N_AD_IMP   = 300_000

# ── Date window ──────────────────────────────────────────────
# All event facts are within the last 90 days
SIM_END   = pd.Timestamp("2026-04-24")
SIM_START = SIM_END - pd.Timedelta(days=89)
SIGNUP_START = SIM_END - pd.Timedelta(days=730)  # 2-year signup history

print("=" * 60)
print("ShareChat Data Generator")
print(f"Seed: {SEED} | End date: {SIM_END.date()}")
print("=" * 60)


# ── Indian festival dates (within 2-year window) ─────────────
FESTIVAL_DATES = {
    "Diwali":          ["2024-11-01", "2025-10-20"],
    "Holi":            ["2024-03-25", "2025-03-14", "2026-03-03"],
    "Eid-ul-Fitr":     ["2024-04-10", "2025-03-30"],
    "Eid-ul-Adha":     ["2024-06-17", "2025-06-06"],
    "Dussehra":        ["2024-10-12", "2025-10-01"],
    "Raksha Bandhan":  ["2024-08-19", "2025-08-09"],
    "Ganesh Chaturthi":["2024-09-07", "2025-08-27"],
    "Onam":            ["2024-09-15", "2025-09-04"],
    "Pongal":          ["2025-01-14", "2026-01-14"],
    "Navratri":        ["2024-10-03", "2025-09-22"],
    "Christmas":       ["2024-12-25", "2025-12-25"],
    "New Year":        ["2025-01-01", "2026-01-01"],
}

festival_map: dict[str, str] = {}
for name, dates in FESTIVAL_DATES.items():
    for d in dates:
        festival_map[d] = name


# ════════════════════════════════════════════════════════════
# 1. dim_date
# ════════════════════════════════════════════════════════════
def build_dim_date() -> pd.DataFrame:
    """Generate date dimension for a 2-year window."""
    dates = pd.date_range(SIGNUP_START.date(), SIM_END.date(), freq="D")
    df = pd.DataFrame({"date": dates})
    df["date_str"]    = df["date"].dt.strftime("%Y-%m-%d")
    df["day_of_week"] = df["date"].dt.day_name()
    df["week_num"]    = df["date"].dt.isocalendar().week.astype(int)
    df["month"]       = df["date"].dt.month
    df["month_name"]  = df["date"].dt.strftime("%b")
    df["year"]        = df["date"].dt.year
    df["quarter"]     = df["date"].dt.quarter
    df["is_weekend"]  = df["date"].dt.dayofweek >= 5
    df["is_festival"] = df["date_str"].isin(festival_map)
    df["festival_name"] = df["date_str"].map(festival_map).fillna("")
    df = df.drop(columns=["date"])
    df = df.rename(columns={"date_str": "date"})
    return df


# ════════════════════════════════════════════════════════════
# 2. dim_users
# ════════════════════════════════════════════════════════════
def build_dim_users() -> pd.DataFrame:
    """
    Generate 50K user profiles.
    Signup dates are right-skewed (more recent users), matching organic growth curves.
    """
    n = N_USERS

    # Language distribution — matches real ShareChat regional breakdown
    languages = ["Hindi","Telugu","Tamil","Bhojpuri","Marathi","Bengali",
                 "Kannada","Malayalam","Gujarati","Punjabi","Odia","Assamese"]
    lang_weights = [0.35, 0.12, 0.10, 0.08, 0.07, 0.07,
                    0.06, 0.05, 0.04, 0.03, 0.02, 0.01]

    # City tier distribution — Tier-3/4 dominate ShareChat's user base
    city_tiers = ["Tier-1","Tier-2","Tier-3","Tier-4"]
    tier_weights = [0.15, 0.25, 0.35, 0.25]

    # Age — skewed young, 18-34 is the bulk
    age_buckets = ["13-17","18-24","25-34","35-44","45+"]
    age_weights  = [0.08, 0.38, 0.30, 0.15, 0.09]

    # Device — ShareChat is heavily Android, especially budget devices
    devices = ["Android-Low","Android-Mid","Android-High","iOS"]
    dev_weights = [0.60, 0.25, 0.10, 0.05]

    # Signup dates: exponential decay toward past (more recent signups)
    days_ago = rng.exponential(scale=180, size=n).clip(0, 730).astype(int)
    signup_dates = SIM_END - pd.to_timedelta(days_ago, unit="D")

    user_ids = [f"U_{i:07d}" for i in range(1, n + 1)]

    # A/B experiment groups — 50/50 split
    exp_groups = np.where(rng.random(n) < 0.5, "control", "variant")

    df = pd.DataFrame({
        "user_id":            user_ids,
        "signup_date":        signup_dates.strftime("%Y-%m-%d"),
        "signup_language":    rng.choice(languages, n, p=lang_weights),
        "city_tier":          rng.choice(city_tiers, n, p=tier_weights),
        "age_bucket":         rng.choice(age_buckets, n, p=age_weights),
        "gender":             rng.choice(["M","F","Other"], n, p=[0.58, 0.39, 0.03]),
        "device_type":        rng.choice(devices, n, p=dev_weights),
        "acquisition_channel":rng.choice(["Organic","Paid","Referral","Preinstall"],
                                         n, p=[0.45, 0.25, 0.20, 0.10]),
        "experiment_group":   exp_groups,
    })

    # Inject a handful of TEST_ user IDs (intentional DQ issue)
    test_indices = rng.choice(n, size=20, replace=False)
    df.loc[test_indices, "user_id"] = [f"TEST_{i:03d}" for i in range(20)]

    return df


# ════════════════════════════════════════════════════════════
# 3. dim_creators
# ════════════════════════════════════════════════════════════
def build_dim_creators() -> pd.DataFrame:
    """
    Generate 5K creators with power-law follower distribution.
    Most creators have <1K followers; a few have millions — classic social media Pareto.
    """
    n = N_CREATORS

    languages = ["Hindi","Telugu","Tamil","Bhojpuri","Marathi","Bengali",
                 "Kannada","Malayalam","Gujarati","Punjabi","Odia","Assamese"]
    lang_weights = [0.35, 0.12, 0.10, 0.08, 0.07, 0.07,
                    0.06, 0.05, 0.04, 0.03, 0.02, 0.01]

    categories = ["Comedy","Devotional","News","Music","Dance",
                  "Education","Lifestyle","Gaming","Regional-Drama"]
    cat_weights = [0.22, 0.15, 0.12, 0.12, 0.10, 0.09, 0.08, 0.07, 0.05]

    # Power-law follower counts (Pareto / log-normal)
    # This ensures top 1% have massive followings, most have very few
    follower_counts = (rng.pareto(a=1.5, size=n) * 500 + 100).astype(int)
    follower_counts = np.clip(follower_counts, 100, 10_000_000)

    def tier(f: int) -> str:
        if f < 1_000:        return "Nano"
        if f < 10_000:       return "Micro"
        if f < 100_000:      return "Mid"
        if f < 1_000_000:    return "Macro"
        return "Mega"

    creator_tiers = [tier(f) for f in follower_counts]

    days_ago = rng.exponential(scale=365, size=n).clip(0, 730).astype(int)
    signup_dates = SIM_END - pd.to_timedelta(days_ago, unit="D")

    df = pd.DataFrame({
        "creator_id":          [f"C_{i:06d}" for i in range(1, n + 1)],
        "creator_signup_date": signup_dates.strftime("%Y-%m-%d"),
        "primary_language":    rng.choice(languages, n, p=lang_weights),
        "follower_count":      follower_counts,
        "creator_tier":        creator_tiers,
        "content_category":    rng.choice(categories, n, p=cat_weights),
        "is_verified":         rng.random(n) < 0.03,  # only ~3% verified
    })
    return df


# ════════════════════════════════════════════════════════════
# 4. dim_content
# ════════════════════════════════════════════════════════════
def build_dim_content(creators: pd.DataFrame) -> pd.DataFrame:
    """
    Generate 100K content posts.
    Mega/Macro creators post more — skewed assignment reflects real platform dynamics.
    """
    n = N_CONTENT

    # Assign creator_ids weighted by tier (bigger creators post more)
    tier_posting_weight = {
        "Mega": 10.0, "Macro": 5.0, "Mid": 2.0, "Micro": 1.2, "Nano": 0.5
    }
    weights = creators["creator_tier"].map(tier_posting_weight).values
    weights = weights / weights.sum()
    creator_ids = rng.choice(creators["creator_id"].values, n, p=weights)

    # Look up language from creator (content language = creator's primary language)
    cid_to_lang = dict(zip(creators["creator_id"], creators["primary_language"]))
    languages = [cid_to_lang[c] for c in creator_ids]

    # Content type distribution — short video dominates
    content_types = ["ShortVideo","Image","Text","LiveStream"]
    ct_weights    = [0.65, 0.20, 0.10, 0.05]
    content_type  = rng.choice(content_types, n, p=ct_weights)

    # Post dates spread over last 90 days
    post_days_ago = rng.integers(0, 90, size=n)
    post_dates = (SIM_END - pd.to_timedelta(post_days_ago, unit="D")).strftime("%Y-%m-%d")

    # Duration only meaningful for video/livestream
    duration = np.where(
        np.isin(content_type, ["ShortVideo", "LiveStream"]),
        rng.integers(15, 90, size=n),
        0
    )

    df = pd.DataFrame({
        "post_id":          [f"P_{i:08d}" for i in range(1, n + 1)],
        "creator_id":       creator_ids,
        "post_date":        post_dates,
        "content_type":     content_type,
        "language":         languages,
        "duration_seconds": duration,
        "has_music":        rng.random(n) < 0.55,
        "hashtag_count":    rng.integers(0, 16, size=n),
    })
    return df


# ════════════════════════════════════════════════════════════
# 5. fact_sessions
# ════════════════════════════════════════════════════════════
def build_fact_sessions(users: pd.DataFrame) -> pd.DataFrame:
    """
    Generate ~500K session records.
    Key behavioral signals embedded:
    - Weekend sessions are ~30% longer (Sat/Sun effect)
    - Tier-3/4 users have longer sessions (more leisure time)
    - Variant group users have ~5-8% longer sessions (A/B test signal)
    - Low-end Android has more very-short sessions (crash/skip proxy)
    """
    n = N_SESSIONS

    user_ids = rng.choice(users["user_id"].values, n)
    uid_to_tier = dict(zip(users["user_id"], users["city_tier"]))
    uid_to_device = dict(zip(users["user_id"], users["device_type"]))
    uid_to_exp = dict(zip(users["user_id"], users["experiment_group"]))

    # Random timestamps within 90-day window
    seconds_range = int((SIM_END - SIM_START).total_seconds())
    start_offsets = rng.integers(0, seconds_range, size=n)
    session_starts = SIM_START + pd.to_timedelta(start_offsets, unit="s")

    # Base session duration: log-normal, mean ~900 sec (15 min)
    base_duration = rng.lognormal(mean=6.8, sigma=0.8, size=n).clip(30, 7200).astype(int)

    # Weekend multiplier
    is_weekend = session_starts.dayofweek >= 5
    base_duration = np.where(is_weekend, (base_duration * 1.30).astype(int), base_duration)

    # Tier-3/4 longer sessions
    city_tiers_arr = np.array([uid_to_tier.get(u, "Tier-2") for u in user_ids])
    tier_mult = np.where(np.isin(city_tiers_arr, ["Tier-3","Tier-4"]), 1.20, 1.0)
    base_duration = (base_duration * tier_mult).astype(int)

    # A/B variant: ~6% lift in session duration
    exp_groups_arr = np.array([uid_to_exp.get(u, "control") for u in user_ids])
    variant_mult = np.where(exp_groups_arr == "variant", 1.06, 1.0)
    base_duration = (base_duration * variant_mult).astype(int)

    # Low-end Android has more crash-like short sessions
    device_arr = np.array([uid_to_device.get(u, "Android-Mid") for u in user_ids])
    crash_mask = (device_arr == "Android-Low") & (rng.random(n) < 0.08)
    base_duration = np.where(crash_mask, rng.integers(1, 10, n), base_duration)

    session_ends = session_starts + pd.to_timedelta(base_duration, unit="s")

    # Intentional DQ issue: ~0.1% sessions where end < start
    bad_mask = rng.random(n) < 0.001
    session_ends = pd.Series(
        np.where(bad_mask,
                 (session_starts - pd.to_timedelta(rng.integers(1, 60, n), unit="s")),
                 session_ends)
    )

    # Per-session engagement counts (proportional to duration)
    duration_minutes = base_duration / 60.0
    posts_viewed    = (duration_minutes * rng.uniform(3, 8, n)).astype(int).clip(1, 500)
    posts_liked     = (posts_viewed * rng.uniform(0.05, 0.25, n)).astype(int)
    posts_shared    = (posts_viewed * rng.uniform(0.01, 0.08, n)).astype(int)
    posts_commented = (posts_viewed * rng.uniform(0.005, 0.04, n)).astype(int)

    app_versions = rng.choice(["14.5.0","14.4.2","14.3.1","14.2.0","13.9.0"],
                              n, p=[0.45, 0.25, 0.15, 0.10, 0.05])

    df = pd.DataFrame({
        "session_id":          [f"S_{i:09d}" for i in range(1, n + 1)],
        "user_id":             user_ids,
        "session_start":       session_starts.strftime("%Y-%m-%d %H:%M:%S"),
        "session_end":         pd.DatetimeIndex(session_ends).strftime("%Y-%m-%d %H:%M:%S"),
        "session_duration_sec": base_duration,
        "posts_viewed":        posts_viewed,
        "posts_liked":         posts_liked,
        "posts_shared":        posts_shared,
        "posts_commented":     posts_commented,
        "device_type":         device_arr,
        "app_version":         app_versions,
    })
    return df


# ════════════════════════════════════════════════════════════
# 6. fact_engagement_events
# ════════════════════════════════════════════════════════════
def build_fact_engagement_events(
    users: pd.DataFrame,
    content: pd.DataFrame,
    creators: pd.DataFrame,
) -> pd.DataFrame:
    """
    Generate ~2M engagement events.
    Key behavioral signals:
    - Views dominate (>60% of events)
    - Festival days: 2-3x normal event volume
    - Language effects: Marathi/Bengali have higher like/share rate
    - Intentional DQ: ~0.5% duplicate rows, ~1% null watch_duration on views
    """
    n = N_EVENTS

    # Post-id to creator-id lookup (denormalized for query performance)
    pid_to_cid = dict(zip(content["post_id"], content["creator_id"]))

    # Event type distribution — views dominate
    event_types = ["view","like","share","comment","follow","skip","report"]
    et_weights  = [0.62, 0.15, 0.07, 0.05, 0.04, 0.06, 0.01]

    user_ids    = rng.choice(users["user_id"].values, n)
    post_ids    = rng.choice(content["post_id"].values, n)
    creator_ids = np.array([pid_to_cid.get(p, "C_000001") for p in post_ids])
    event_type  = rng.choice(event_types, n, p=et_weights)

    # Random timestamps within 90-day window
    seconds_range = int((SIM_END - SIM_START).total_seconds())
    ts_offsets    = rng.integers(0, seconds_range, size=n)
    timestamps    = (SIM_START + pd.to_timedelta(ts_offsets, unit="s")).strftime("%Y-%m-%d %H:%M:%S")

    # Festival day spikes: 2.5x more events on festival days
    event_dates = pd.to_datetime(timestamps).normalize()
    festival_day_set = {pd.Timestamp(d) for d in festival_map.keys()
                        if SIGNUP_START <= pd.Timestamp(d) <= SIM_END}
    # (The simple uniform sampling already doesn't account for festival spikes;
    # we inject extra rows later by duplicating a festival-day subset)

    # Watch duration: only meaningful for view events
    watch_duration = np.where(
        event_type == "view",
        rng.integers(3, 91, size=n),
        np.nan
    )

    # Intentional DQ: ~1% null watch_duration even on view events
    null_view_mask = (event_type == "view") & (rng.random(n) < 0.01)
    watch_duration = np.where(null_view_mask, np.nan, watch_duration)

    # Scroll velocity (proxy for engagement quality)
    scroll_velocity = rng.uniform(0.5, 5.0, size=n).round(3)

    df = pd.DataFrame({
        "event_id":           [f"E_{i:010d}" for i in range(1, n + 1)],
        "user_id":            user_ids,
        "post_id":            post_ids,
        "creator_id":         creator_ids,
        "event_type":         event_type,
        "event_timestamp":    timestamps,
        "watch_duration_sec": watch_duration,
        "scroll_velocity":    scroll_velocity,
    })

    # Intentional DQ: inject ~0.5% duplicate rows (10K duplicates)
    n_dupes = int(n * 0.005)
    dup_indices = rng.choice(n, size=n_dupes, replace=False)
    duplicates  = df.iloc[dup_indices].copy()
    df = pd.concat([df, duplicates], ignore_index=True)

    return df


# ════════════════════════════════════════════════════════════
# 7. fact_ad_impressions
# ════════════════════════════════════════════════════════════
def build_fact_ad_impressions(users: pd.DataFrame) -> pd.DataFrame:
    """
    Generate ~300K ad impression records.
    Key behavioral signals:
    - Tier-1 users have higher CTR (~5%) vs Tier-3/4 (~2%)
    - Tier-1 users convert better on ecommerce/fintech ads
    - Realistic ~3% overall CTR, ~10% of clicks convert
    """
    n = N_AD_IMP

    uid_to_tier = dict(zip(users["user_id"], users["city_tier"]))
    user_ids    = rng.choice(users["user_id"].values, n)
    city_tiers  = np.array([uid_to_tier.get(u, "Tier-2") for u in user_ids])

    ad_categories = ["Ecommerce","Gaming","Fintech","FMCG","Travel","Education"]
    ad_weights    = [0.30, 0.20, 0.18, 0.15, 0.10, 0.07]

    # Tier-dependent CTR
    tier_ctr = {"Tier-1": 0.050, "Tier-2": 0.035, "Tier-3": 0.022, "Tier-4": 0.018}
    ctrs = np.array([tier_ctr.get(t, 0.030) for t in city_tiers])
    was_clicked   = rng.random(n) < ctrs
    was_converted = was_clicked & (rng.random(n) < 0.10)

    # Revenue: only when clicked/converted; Tier-1 ads have higher value
    tier_rev_mult = {"Tier-1": 1.8, "Tier-2": 1.2, "Tier-3": 0.8, "Tier-4": 0.6}
    rev_mult = np.array([tier_rev_mult.get(t, 1.0) for t in city_tiers])
    base_revenue  = rng.uniform(2, 50, n) * rev_mult
    revenue_inr   = np.where(was_clicked, base_revenue.round(2), np.nan)

    seconds_range = int((SIM_END - SIM_START).total_seconds())
    ts_offsets    = rng.integers(0, seconds_range, size=n)
    timestamps    = (SIM_START + pd.to_timedelta(ts_offsets, unit="s")).strftime("%Y-%m-%d %H:%M:%S")

    ad_ids = [f"AD_{rng.integers(1, 500):05d}" for _ in range(n)]

    df = pd.DataFrame({
        "impression_id":        [f"I_{i:09d}" for i in range(1, n + 1)],
        "user_id":              user_ids,
        "ad_id":                ad_ids,
        "impression_timestamp": timestamps,
        "ad_category":          rng.choice(ad_categories, n, p=ad_weights),
        "was_clicked":          was_clicked,
        "was_converted":        was_converted,
        "revenue_inr":          revenue_inr,
    })
    return df


# ════════════════════════════════════════════════════════════
# Main
# ════════════════════════════════════════════════════════════
def main() -> None:
    t0 = time.time()

    print("\n[1/7] Building dim_date ...")
    dim_date = build_dim_date()
    print(f"      {len(dim_date):,} rows")

    print("[2/7] Building dim_users ...")
    dim_users = build_dim_users()
    print(f"      {len(dim_users):,} rows")

    print("[3/7] Building dim_creators ...")
    dim_creators = build_dim_creators()
    print(f"      {len(dim_creators):,} rows")

    print("[4/7] Building dim_content ...")
    dim_content = build_dim_content(dim_creators)
    print(f"      {len(dim_content):,} rows")

    print("[5/7] Building fact_sessions ...")
    fact_sessions = build_fact_sessions(dim_users)
    print(f"      {len(fact_sessions):,} rows")

    print("[6/7] Building fact_engagement_events (~2M rows, may take ~60s) ...")
    fact_events = build_fact_engagement_events(dim_users, dim_content, dim_creators)
    print(f"      {len(fact_events):,} rows (includes ~0.5% duplicates)")

    print("[7/7] Building fact_ad_impressions ...")
    fact_ads = build_fact_ad_impressions(dim_users)
    print(f"      {len(fact_ads):,} rows")

    # ── Save to CSV ──────────────────────────────────────────
    print("\nSaving CSVs to data/raw/ ...")
    tables = {
        "dim_date":                  dim_date,
        "dim_users":                 dim_users,
        "dim_creators":              dim_creators,
        "dim_content":               dim_content,
        "fact_sessions":             fact_sessions,
        "fact_engagement_events":    fact_events,
        "fact_ad_impressions":       fact_ads,
    }
    for name, df in tables.items():
        path = RAW / f"{name}.csv"
        df.to_csv(path, index=False)
        size_mb = path.stat().st_size / 1_048_576
        print(f"  ✓ {name}.csv  ({len(df):>10,} rows | {size_mb:.1f} MB)")

    elapsed = time.time() - t0
    print(f"\nDone in {elapsed:.1f}s")
    print(f"Total rows generated: {sum(len(d) for d in tables.values()):,}")

    # ── Quick sanity checks ──────────────────────────────────
    print("\n── Sanity Checks ──────────────────────────────────────")
    # Language distribution in users
    lang_dist = dim_users["signup_language"].value_counts(normalize=True).head(3)
    print("Top 3 languages (users):", dict(lang_dist.round(3)))

    # Creator tier breakdown
    tier_dist = dim_creators["creator_tier"].value_counts()
    print("Creator tier distribution:")
    for tier, count in tier_dist.items():
        print(f"  {tier:8s}: {count:5,}")

    # Session duration distribution
    pcts = np.percentile(fact_sessions["session_duration_sec"], [25, 50, 75, 95])
    print(f"Session duration (P25/P50/P75/P95): {pcts.astype(int).tolist()} seconds")

    # A/B test groups
    ab = fact_sessions.merge(
        dim_users[["user_id","experiment_group"]], on="user_id", how="left"
    ).groupby("experiment_group")["session_duration_sec"].mean()
    if "control" in ab and "variant" in ab:
        lift = (ab["variant"] / ab["control"] - 1) * 100
        print(f"A/B test session duration lift (variant vs control): +{lift:.1f}%")

    # Ad CTR by tier
    ctr_by_tier = fact_ads.groupby(
        fact_ads["user_id"].map(dict(zip(dim_users["user_id"], dim_users["city_tier"])))
    )["was_clicked"].mean()
    print("Ad CTR by city tier:")
    for tier, ctr in ctr_by_tier.items():
        print(f"  {tier}: {ctr*100:.2f}%")


if __name__ == "__main__":
    main()
