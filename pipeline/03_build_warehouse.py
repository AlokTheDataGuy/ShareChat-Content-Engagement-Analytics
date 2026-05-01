"""
ShareChat Creator & Content Engagement Analytics
Warehouse Builder Script

Loads all CSVs from data/raw/ into a SQLite star-schema database at
data/warehouse/sharechat_warehouse.db.

REDSHIFT EQUIVALENT DESIGN NOTES
─────────────────────────────────
In a real Redshift deployment, this script would instead run via:
  COPY dim_users FROM 's3://sharechat-datalake/dim_users/'
  IAM_ROLE 'arn:aws:iam::...'
  FORMAT AS PARQUET;

Key Redshift-specific design decisions that would differ from SQLite:

1. DISTKEY choices
   - fact_engagement_events: DISTKEY(user_id) — the most common join column;
     distributes rows evenly across slices because user_id has high cardinality
   - fact_sessions:          DISTKEY(user_id) — same rationale; collocates with dim_users
   - dim_users:              DISTSTYLE ALL — small dimension table; replicate to all slices
     to avoid redistribution on every join
   - dim_creators:           DISTSTYLE ALL — same reasoning (5K rows is tiny)

2. SORTKEY choices
   - fact_engagement_events: SORTKEY(event_timestamp) — range-scan on date ranges is the
     most common filter; zone maps make these reads very fast
   - fact_sessions:          SORTKEY(session_start) — same pattern
   - fact_ad_impressions:    SORTKEY(impression_timestamp)

3. ENCODE (compression) choices
   - event_type:   ENCODE bytedict   — low-cardinality string column
   - city_tier:    ENCODE bytedict
   - creator_tier: ENCODE bytedict
   - Timestamps:   ENCODE az64       — best for date/timestamp
   - IDs:          ENCODE lzo        — good for high-cardinality strings
   - Booleans:     ENCODE raw        — already 1 byte; no compression benefit

4. VACUUM and ANALYZE
   - After bulk loads, run VACUUM SORT ONLY and ANALYZE to keep query plans accurate
   - In SQLite the equivalent is ANALYZE (updates statistics)

5. Late-arriving data
   - Redshift: use MERGE statement (available since 2022) to upsert events
   - SQLite: INSERT OR REPLACE simulates this

Run: python src/03_build_warehouse.py
Output: data/warehouse/sharechat_warehouse.db
"""

from __future__ import annotations

import sqlite3
import time
from pathlib import Path

import pandas as pd

# ── Paths ────────────────────────────────────────────────────
ROOT      = Path(__file__).resolve().parent.parent
RAW       = ROOT / "data" / "raw"
WAREHOUSE = ROOT / "data" / "warehouse"
DB_PATH   = WAREHOUSE / "sharechat_warehouse.db"

WAREHOUSE.mkdir(parents=True, exist_ok=True)


# ── DDL statements ───────────────────────────────────────────
DDL = {
    "dim_date": """
        CREATE TABLE IF NOT EXISTS dim_date (
            date            TEXT PRIMARY KEY,
            day_of_week     TEXT,
            week_num        INTEGER,
            month           INTEGER,
            month_name      TEXT,
            year            INTEGER,
            quarter         INTEGER,
            is_weekend      INTEGER,   -- 0/1 boolean
            is_festival     INTEGER,   -- 0/1 boolean
            festival_name   TEXT
        )
    """,

    "dim_users": """
        CREATE TABLE IF NOT EXISTS dim_users (
            user_id             TEXT PRIMARY KEY,
            signup_date         TEXT,
            signup_language     TEXT,
            city_tier           TEXT,
            age_bucket          TEXT,
            gender              TEXT,
            device_type         TEXT,
            acquisition_channel TEXT,
            experiment_group    TEXT
        )
    """,

    "dim_creators": """
        CREATE TABLE IF NOT EXISTS dim_creators (
            creator_id          TEXT PRIMARY KEY,
            creator_signup_date TEXT,
            primary_language    TEXT,
            follower_count      INTEGER,
            creator_tier        TEXT,
            content_category    TEXT,
            is_verified         INTEGER   -- 0/1 boolean
        )
    """,

    "dim_content": """
        CREATE TABLE IF NOT EXISTS dim_content (
            post_id           TEXT PRIMARY KEY,
            creator_id        TEXT,
            post_date         TEXT,
            content_type      TEXT,
            language          TEXT,
            duration_seconds  INTEGER,
            has_music         INTEGER,
            hashtag_count     INTEGER,
            FOREIGN KEY (creator_id) REFERENCES dim_creators(creator_id)
        )
    """,

    "fact_sessions": """
        CREATE TABLE IF NOT EXISTS fact_sessions (
            session_id            TEXT PRIMARY KEY,
            user_id               TEXT,
            session_start         TEXT,
            session_end           TEXT,
            session_duration_sec  INTEGER,
            posts_viewed          INTEGER,
            posts_liked           INTEGER,
            posts_shared          INTEGER,
            posts_commented       INTEGER,
            device_type           TEXT,
            app_version           TEXT,
            FOREIGN KEY (user_id) REFERENCES dim_users(user_id)
        )
    """,

    "fact_engagement_events": """
        CREATE TABLE IF NOT EXISTS fact_engagement_events (
            event_id            TEXT PRIMARY KEY,
            user_id             TEXT,
            post_id             TEXT,
            creator_id          TEXT,   -- denormalized: avoids join on every query
            event_type          TEXT,
            event_timestamp     TEXT,
            watch_duration_sec  REAL,
            scroll_velocity     REAL,
            FOREIGN KEY (user_id)    REFERENCES dim_users(user_id),
            FOREIGN KEY (post_id)    REFERENCES dim_content(post_id),
            FOREIGN KEY (creator_id) REFERENCES dim_creators(creator_id)
        )
    """,

    "fact_ad_impressions": """
        CREATE TABLE IF NOT EXISTS fact_ad_impressions (
            impression_id        TEXT PRIMARY KEY,
            user_id              TEXT,
            ad_id                TEXT,
            impression_timestamp TEXT,
            ad_category          TEXT,
            was_clicked          INTEGER,
            was_converted        INTEGER,
            revenue_inr          REAL,
            FOREIGN KEY (user_id) REFERENCES dim_users(user_id)
        )
    """,
}

# ── Index definitions ────────────────────────────────────────
INDEXES = [
    # fact_sessions — most common query patterns
    "CREATE INDEX IF NOT EXISTS idx_sessions_user     ON fact_sessions(user_id)",
    "CREATE INDEX IF NOT EXISTS idx_sessions_start    ON fact_sessions(session_start)",
    "CREATE INDEX IF NOT EXISTS idx_sessions_device   ON fact_sessions(device_type)",

    # fact_engagement_events
    "CREATE INDEX IF NOT EXISTS idx_events_user       ON fact_engagement_events(user_id)",
    "CREATE INDEX IF NOT EXISTS idx_events_post       ON fact_engagement_events(post_id)",
    "CREATE INDEX IF NOT EXISTS idx_events_creator    ON fact_engagement_events(creator_id)",
    "CREATE INDEX IF NOT EXISTS idx_events_type       ON fact_engagement_events(event_type)",
    "CREATE INDEX IF NOT EXISTS idx_events_ts         ON fact_engagement_events(event_timestamp)",

    # fact_ad_impressions
    "CREATE INDEX IF NOT EXISTS idx_ads_user          ON fact_ad_impressions(user_id)",
    "CREATE INDEX IF NOT EXISTS idx_ads_ts            ON fact_ad_impressions(impression_timestamp)",
    "CREATE INDEX IF NOT EXISTS idx_ads_category      ON fact_ad_impressions(ad_category)",

    # dim_content
    "CREATE INDEX IF NOT EXISTS idx_content_creator   ON dim_content(creator_id)",
    "CREATE INDEX IF NOT EXISTS idx_content_date      ON dim_content(post_date)",
    "CREATE INDEX IF NOT EXISTS idx_content_lang      ON dim_content(language)",

    # dim_users
    "CREATE INDEX IF NOT EXISTS idx_users_signup      ON dim_users(signup_date)",
    "CREATE INDEX IF NOT EXISTS idx_users_tier        ON dim_users(city_tier)",
    "CREATE INDEX IF NOT EXISTS idx_users_lang        ON dim_users(signup_language)",
    "CREATE INDEX IF NOT EXISTS idx_users_exp         ON dim_users(experiment_group)",
]

READ_CHUNK_SIZE   = 200_000   # rows to read from CSV at once
INSERT_BATCH_SIZE =   5_000   # rows per executemany call


def load_table(
    conn: sqlite3.Connection,
    table_name: str,
    csv_path: Path,
) -> None:
    """Load a CSV into SQLite using executemany, replacing any existing data."""
    if not csv_path.exists():
        print(f"  SKIP  {table_name} — CSV not found at {csv_path}")
        return

    t0 = time.time()
    cursor = conn.cursor()
    cursor.execute(f"DELETE FROM {table_name}")

    total = 0
    first_chunk = True

    for chunk in pd.read_csv(csv_path, chunksize=READ_CHUNK_SIZE):
        # Infer column list from first chunk
        if first_chunk:
            cols = list(chunk.columns)
            placeholders = ",".join("?" * len(cols))
            insert_sql = f"INSERT OR REPLACE INTO {table_name} ({','.join(cols)}) VALUES ({placeholders})"
            first_chunk = False

        # Convert booleans → int, NaN → None for SQLite
        for col in chunk.select_dtypes(include="bool").columns:
            chunk[col] = chunk[col].astype(int)
        chunk = chunk.where(chunk.notna(), other=None)

        # Batch executemany inserts
        rows = chunk.values.tolist()
        for i in range(0, len(rows), INSERT_BATCH_SIZE):
            cursor.executemany(insert_sql, rows[i : i + INSERT_BATCH_SIZE])
        conn.commit()

        total += len(chunk)
        print(f"    ... {total:>10,} rows loaded", end="\r")

    elapsed = time.time() - t0
    size_mb = csv_path.stat().st_size / 1_048_576
    print(f"  ✓  {table_name:<30}  {total:>10,} rows  |  {size_mb:.1f} MB  |  {elapsed:.1f}s")


def main() -> None:
    t0 = time.time()

    print("=" * 60)
    print("ShareChat Warehouse Builder")
    print(f"Database → {DB_PATH}")
    print("=" * 60)

    # Remove existing DB so we start fresh
    if DB_PATH.exists():
        DB_PATH.unlink()
        print("Removed existing database.\n")

    conn = sqlite3.connect(DB_PATH)

    # Enable WAL mode for better concurrent read performance
    conn.execute("PRAGMA journal_mode=WAL")
    # Increase cache size to speed up bulk inserts
    conn.execute("PRAGMA cache_size=-65536")   # 64 MB
    conn.execute("PRAGMA synchronous=NORMAL")

    print("Creating tables ...")
    for table_name, ddl in DDL.items():
        conn.execute(ddl)
    conn.commit()
    print("  All tables created.\n")

    print("Loading data ...")
    load_order = [
        "dim_date",
        "dim_users",
        "dim_creators",
        "dim_content",
        "fact_sessions",
        "fact_engagement_events",
        "fact_ad_impressions",
    ]
    for table_name in load_order:
        load_table(conn, table_name, RAW / f"{table_name}.csv")

    print("\nCreating indexes ...")
    for idx_sql in INDEXES:
        conn.execute(idx_sql)
    conn.commit()
    print(f"  {len(INDEXES)} indexes created.")

    # Run ANALYZE to update query planner statistics
    conn.execute("ANALYZE")
    conn.commit()
    print("  ANALYZE complete.")

    # ── Validation ───────────────────────────────────────────
    print("\n── Row counts ──────────────────────────────────────────")
    for table_name in load_order:
        count = conn.execute(f"SELECT COUNT(*) FROM {table_name}").fetchone()[0]
        print(f"  {table_name:<35}  {count:>10,}")

    db_size_mb = DB_PATH.stat().st_size / 1_048_576
    elapsed = time.time() - t0
    print(f"\nDatabase size: {db_size_mb:.0f} MB")
    print(f"Total time:    {elapsed:.1f}s")

    conn.close()
    print(f"\nWarehouse ready at: {DB_PATH}")


if __name__ == "__main__":
    main()
