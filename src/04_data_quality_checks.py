"""
ShareChat Creator & Content Engagement Analytics
Data Quality Checks Script

Runs systematic data quality checks against the SQLite warehouse and prints a report.
Checks performed:
  1. Row counts (sanity vs expected scale)
  2. Null / missing value rates per column
  3. Referential integrity (FK violations)
  4. Date range validity (no future dates, no impossible sessions)
  5. Duplicate detection
  6. Schema validation (required columns present)
  7. Domain validation (valid enum values)
  8. Flags intentional DQ issues planted in 01_generate_data.py

Run: python src/04_data_quality_checks.py
Output: console + data/warehouse/data_quality_report.txt
"""

from __future__ import annotations

import sqlite3
from datetime import datetime
from pathlib import Path

# ── Paths ────────────────────────────────────────────────────
ROOT    = Path(__file__).resolve().parent.parent
DB_PATH = ROOT / "data" / "warehouse" / "sharechat_warehouse.db"
REPORT  = ROOT / "data" / "warehouse" / "data_quality_report.txt"

# ── Expected scale ───────────────────────────────────────────
EXPECTED_ROWS = {
    "dim_date":               730,
    "dim_users":            50_000,
    "dim_creators":          5_000,
    "dim_content":         100_000,
    "fact_sessions":       500_000,
    "fact_engagement_events": 2_000_000,
    "fact_ad_impressions":  300_000,
}
TOLERANCE = 0.05   # ±5% tolerance for stochastic row counts

LINES: list[str] = []


def out(msg: str = "") -> None:
    """Print to console and accumulate for file output."""
    print(msg)
    LINES.append(msg)


def section(title: str) -> None:
    out()
    out("─" * 60)
    out(f"  {title}")
    out("─" * 60)


def run_checks() -> None:
    if not DB_PATH.exists():
        out(f"ERROR: Database not found at {DB_PATH}")
        out("Run src/03_build_warehouse.py first.")
        return

    conn = sqlite3.connect(DB_PATH)
    conn.row_factory = sqlite3.Row

    out("=" * 60)
    out("  ShareChat Data Quality Report")
    out(f"  Generated: {datetime.now().strftime('%Y-%m-%d %H:%M:%S')}")
    out(f"  Database:  {DB_PATH}")
    out("=" * 60)

    # ── 1. Row Counts ────────────────────────────────────────
    section("1. ROW COUNTS (expected vs actual)")
    all_pass = True
    for table, expected in EXPECTED_ROWS.items():
        try:
            actual = conn.execute(f"SELECT COUNT(*) FROM {table}").fetchone()[0]
            lo = expected * (1 - TOLERANCE)
            hi = expected * (1 + TOLERANCE) * 1.02   # +2% for dupe injection
            status = "PASS" if lo <= actual <= hi else "WARN"
            if status == "WARN":
                all_pass = False
            out(f"  {status}  {table:<35}  expected ~{expected:>9,}  actual {actual:>9,}")
        except sqlite3.OperationalError as e:
            out(f"  FAIL  {table}: {e}")
            all_pass = False
    out(f"\n  Overall: {'ALL PASS' if all_pass else 'WARNINGS PRESENT — see above'}")

    # ── 2. Null Rates ────────────────────────────────────────
    section("2. NULL / MISSING VALUE RATES")

    nullable_checks = [
        ("dim_users",              "signup_language",     0.0),
        ("dim_users",              "city_tier",           0.0),
        ("dim_users",              "experiment_group",    0.0),
        ("dim_creators",           "follower_count",      0.0),
        ("dim_content",            "creator_id",          0.0),
        ("fact_sessions",          "user_id",             0.0),
        ("fact_sessions",          "session_duration_sec",0.0),
        ("fact_engagement_events", "event_type",          0.0),
        ("fact_engagement_events", "user_id",             0.0),
        # watch_duration_sec on views: ~1% expected null (instrumentation gap)
        ("fact_ad_impressions",    "user_id",             0.0),
        ("fact_ad_impressions",    "revenue_inr",         None),  # None = skip threshold
    ]

    for table, col, max_null_rate in nullable_checks:
        try:
            total = conn.execute(f"SELECT COUNT(*) FROM {table}").fetchone()[0]
            nulls = conn.execute(
                f"SELECT COUNT(*) FROM {table} WHERE {col} IS NULL"
            ).fetchone()[0]
            rate = nulls / total if total else 0
            if max_null_rate is None:
                status = "INFO"
            elif rate <= max_null_rate:
                status = "PASS"
            else:
                status = "WARN"
            out(f"  {status}  {table}.{col:<35}  null_rate={rate*100:.3f}%  ({nulls:,} nulls)")
        except sqlite3.OperationalError as e:
            out(f"  FAIL  {table}.{col}: {e}")

    # Special check: null watch_duration on view events (planted DQ issue)
    try:
        result = conn.execute("""
            SELECT
                COUNT(*) AS total_views,
                SUM(CASE WHEN watch_duration_sec IS NULL THEN 1 ELSE 0 END) AS null_dur,
                ROUND(100.0 * SUM(CASE WHEN watch_duration_sec IS NULL THEN 1 ELSE 0 END)
                      / COUNT(*), 3) AS null_pct
            FROM fact_engagement_events
            WHERE event_type = 'view'
        """).fetchone()
        out(f"\n  NOTE  fact_engagement_events.watch_duration_sec WHERE event_type='view'")
        out(f"        Total views: {result['total_views']:,}  |  Null duration: {result['null_dur']:,}  |  {result['null_pct']:.2f}%")
        out("        ~1% null rate is intentional (instrumentation gap — real-world pattern)")
    except Exception as e:
        out(f"  FAIL  watch_duration check: {e}")

    # ── 3. Referential Integrity ─────────────────────────────
    section("3. REFERENTIAL INTEGRITY (FK violations)")

    fk_checks = [
        ("fact_sessions",          "user_id",    "dim_users",    "user_id"),
        ("fact_engagement_events", "user_id",    "dim_users",    "user_id"),
        ("fact_engagement_events", "post_id",    "dim_content",  "post_id"),
        ("fact_engagement_events", "creator_id", "dim_creators", "creator_id"),
        ("fact_ad_impressions",    "user_id",    "dim_users",    "user_id"),
        ("dim_content",            "creator_id", "dim_creators", "creator_id"),
    ]

    for fact_table, fk_col, dim_table, pk_col in fk_checks:
        try:
            violations = conn.execute(f"""
                SELECT COUNT(*)
                FROM {fact_table} f
                WHERE f.{fk_col} NOT IN (SELECT {pk_col} FROM {dim_table})
                  AND f.{fk_col} IS NOT NULL
            """).fetchone()[0]
            status = "PASS" if violations == 0 else "WARN"
            out(f"  {status}  {fact_table}.{fk_col} → {dim_table}.{pk_col}  "
                f"violations: {violations:,}")
        except sqlite3.OperationalError as e:
            out(f"  FAIL  {e}")

    # ── 4. Date Validity ─────────────────────────────────────
    section("4. DATE / TIME VALIDITY")

    today = datetime.now().strftime("%Y-%m-%d")

    # Future signup dates
    future_signups = conn.execute(
        f"SELECT COUNT(*) FROM dim_users WHERE signup_date > '{today}'"
    ).fetchone()[0]
    out(f"  {'PASS' if future_signups == 0 else 'WARN'}  Future signup dates: {future_signups:,}")

    # Sessions with negative duration (planted DQ issue)
    bad_sessions = conn.execute("""
        SELECT COUNT(*)
        FROM fact_sessions
        WHERE session_end < session_start
    """).fetchone()[0]
    out(f"  {'WARN' if bad_sessions > 0 else 'PASS'}  Sessions with end < start (planted DQ): {bad_sessions:,}")
    if bad_sessions > 0:
        out("        ACTION: Filter WHERE session_end >= session_start in all session queries")

    # Sessions with 0 or negative duration
    zero_dur = conn.execute(
        "SELECT COUNT(*) FROM fact_sessions WHERE session_duration_sec <= 0"
    ).fetchone()[0]
    out(f"  {'WARN' if zero_dur > 0 else 'PASS'}  Sessions with duration <= 0s: {zero_dur:,}")

    # Events with future timestamps
    future_events = conn.execute(
        f"SELECT COUNT(*) FROM fact_engagement_events WHERE event_timestamp > '{today} 23:59:59'"
    ).fetchone()[0]
    out(f"  {'PASS' if future_events == 0 else 'WARN'}  Future event timestamps: {future_events:,}")

    # ── 5. Duplicate Detection ───────────────────────────────
    section("5. DUPLICATE DETECTION (planted: ~0.5% in engagement events)")

    dup_checks = [
        ("dim_users",              "user_id"),
        ("dim_creators",           "creator_id"),
        ("dim_content",            "post_id"),
        ("fact_sessions",          "session_id"),
        ("fact_engagement_events", "event_id"),
        ("fact_ad_impressions",    "impression_id"),
    ]

    for table, pk_col in dup_checks:
        try:
            total  = conn.execute(f"SELECT COUNT(*) FROM {table}").fetchone()[0]
            unique = conn.execute(
                f"SELECT COUNT(DISTINCT {pk_col}) FROM {table}"
            ).fetchone()[0]
            dupes  = total - unique
            rate   = dupes / total * 100 if total else 0
            status = "PASS" if dupes == 0 else "WARN"
            out(f"  {status}  {table:<35}  dupes: {dupes:>8,}  ({rate:.3f}%)")
        except sqlite3.OperationalError as e:
            out(f"  FAIL  {table}: {e}")

    out("\n  NOTE: fact_engagement_events intentionally has ~0.5% duplicates.")
    out("        These were removed by 02_simulate_api_fetch.py deduplication step.")
    out("        If duplicates remain here, re-run 02 then 03.")

    # ── 6. TEST_ User IDs ────────────────────────────────────
    section("6. TEST / INTERNAL USER IDs (planted DQ issue)")

    test_users = conn.execute(
        "SELECT COUNT(*) FROM dim_users WHERE user_id LIKE 'TEST_%'"
    ).fetchone()[0]
    test_events = conn.execute(
        "SELECT COUNT(*) FROM fact_engagement_events WHERE user_id LIKE 'TEST_%'"
    ).fetchone()[0]
    out(f"  WARN  TEST_ user IDs in dim_users:              {test_users:>6,}")
    out(f"  WARN  Events from TEST_ users:                  {test_events:>6,}")
    out("        ACTION: Add WHERE user_id NOT LIKE 'TEST_%' to all production queries")

    # ── 7. Domain / Enum Validation ──────────────────────────
    section("7. DOMAIN / ENUM VALIDATION")

    enum_checks = [
        ("dim_users",    "city_tier",         ["Tier-1","Tier-2","Tier-3","Tier-4"]),
        ("dim_users",    "experiment_group",  ["control","variant"]),
        ("dim_creators", "creator_tier",      ["Nano","Micro","Mid","Macro","Mega"]),
        ("dim_content",  "content_type",      ["ShortVideo","Image","Text","LiveStream"]),
        ("fact_engagement_events", "event_type",
            ["view","like","share","comment","follow","skip","report"]),
    ]

    for table, col, valid_values in enum_checks:
        placeholders = ",".join(f"'{v}'" for v in valid_values)
        try:
            invalid = conn.execute(
                f"SELECT COUNT(*) FROM {table} WHERE {col} NOT IN ({placeholders})"
            ).fetchone()[0]
            status = "PASS" if invalid == 0 else "WARN"
            out(f"  {status}  {table}.{col:<35}  invalid values: {invalid:,}")
        except sqlite3.OperationalError as e:
            out(f"  FAIL  {table}.{col}: {e}")

    # ── 8. Distribution Sanity Checks ───────────────────────
    section("8. DISTRIBUTION SANITY CHECKS")

    # A/B test split
    ab = conn.execute(
        "SELECT experiment_group, COUNT(*) AS n FROM dim_users GROUP BY 1"
    ).fetchall()
    out("  A/B test split in dim_users:")
    for row in ab:
        out(f"    {row['experiment_group']}: {row['n']:,}")

    # Creator tier distribution
    tiers = conn.execute(
        "SELECT creator_tier, COUNT(*) AS n FROM dim_creators GROUP BY 1 ORDER BY n DESC"
    ).fetchall()
    out("  Creator tier distribution:")
    for row in tiers:
        out(f"    {row['creator_tier']:<8}: {row['n']:,}")

    # Top language
    top_lang = conn.execute(
        "SELECT signup_language, COUNT(*) AS n FROM dim_users GROUP BY 1 ORDER BY n DESC LIMIT 3"
    ).fetchall()
    out("  Top 3 signup languages:")
    for row in top_lang:
        out(f"    {row['signup_language']}: {row['n']:,}")

    # ── Summary ──────────────────────────────────────────────
    section("SUMMARY")
    out("  Known planted DQ issues (all expected):")
    out("  ├── ~0.5% duplicate event_ids in fact_engagement_events (removed by API fetch)")
    out("  ├── ~0.1% sessions with session_end < session_start (impossible duration)")
    out("  ├── ~1% null watch_duration_sec on view events (instrumentation gap)")
    out("  └── 20 TEST_ user_ids (internal accounts to filter from analysis)")
    out()
    out("  Recommended query filters for clean analysis:")
    out("  ├── WHERE user_id NOT LIKE 'TEST_%'")
    out("  ├── WHERE session_end >= session_start")
    out("  └── WHERE watch_duration_sec IS NOT NULL  (for video metrics)")

    conn.close()


def main() -> None:
    run_checks()

    # Write report to file
    REPORT.parent.mkdir(parents=True, exist_ok=True)
    with open(REPORT, "w", encoding="utf-8") as f:
        f.write("\n".join(LINES))
    print(f"\nReport saved → {REPORT}")


if __name__ == "__main__":
    main()
