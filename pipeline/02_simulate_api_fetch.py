"""
ShareChat Creator & Content Engagement Analytics
Simulated API Fetch Script

Simulates fetching engagement events from an internal analytics API endpoint.
In production, this pattern would extend to real ShareChat API endpoints with:
  - Bearer token / OAuth 2.0 authentication headers
  - Real pagination via cursor tokens or offset/limit
  - Retry logic with exponential backoff on 429 / 5xx responses
  - Rate limiting to respect API quotas
  - Checkpointing so restarts don't re-fetch already-processed pages

This script demonstrates the "scripting to fetch/modify data from API endpoints"
skill explicitly listed in the ShareChat Product Analyst JD.

Run: python src/02_simulate_api_fetch.py
Output: data/raw/fact_engagement_events.csv  (refreshed / deduplicated)
"""

from __future__ import annotations

import logging
import time
import random
from pathlib import Path
from typing import Iterator

import pandas as pd

# ── Logging setup ────────────────────────────────────────────
logging.basicConfig(
    level=logging.INFO,
    format="%(asctime)s  %(levelname)-8s  %(message)s",
    datefmt="%H:%M:%S",
)
log = logging.getLogger(__name__)

# ── Paths ────────────────────────────────────────────────────
ROOT    = Path(__file__).resolve().parent.parent
RAW     = ROOT / "data" / "raw"
SRC_CSV = RAW / "fact_engagement_events.csv"
OUT_CSV = RAW / "fact_engagement_events.csv"  # overwrite in-place after refresh

# ── Simulated API config ─────────────────────────────────────
API_BASE_URL   = "https://internal-api.sharechat.internal/v2/engagement-events"
PAGE_SIZE      = 10_000   # rows per page (typical for analytics APIs)
MAX_RETRIES    = 3
RETRY_BACKOFF  = [1.0, 2.0, 4.0]   # seconds between retries (exponential)
RATE_LIMIT_RPS = 5                  # requests per second ceiling
SIMULATED_FAIL_RATE = 0.05          # 5% of requests "fail" to test retry logic


class SimulatedAPIClient:
    """
    Simulates a paginated internal API client.

    In production this would wrap something like:
        import requests
        session = requests.Session()
        session.headers.update({"Authorization": f"Bearer {token}"})
        resp = session.get(url, params=params, timeout=30)
        resp.raise_for_status()
        return resp.json()
    """

    def __init__(self, base_url: str, page_size: int = PAGE_SIZE) -> None:
        self.base_url  = base_url
        self.page_size = page_size
        self._data: pd.DataFrame | None = None  # simulated backing store

    def _load_backing_store(self) -> pd.DataFrame:
        """Load the local CSV as the simulated backing store (mimics DB behind API)."""
        if self._data is None:
            log.info("Loading local backing store from %s", SRC_CSV)
            self._data = pd.read_csv(SRC_CSV, dtype=str)
        return self._data

    def _simulate_request(self, page: int, offset: int) -> dict:
        """
        Simulate an HTTP GET request to the engagement events endpoint.

        Real signature would be:
            GET /v2/engagement-events?page={page}&limit={page_size}&after_cursor={cursor}
        """
        # Simulate network latency
        time.sleep(random.uniform(0.005, 0.02))

        # Simulate intermittent failures (5xx / rate-limit errors)
        if random.random() < SIMULATED_FAIL_RATE:
            raise ConnectionError(f"Simulated API failure on page {page} (5xx / timeout)")

        data = self._load_backing_store()
        chunk = data.iloc[offset : offset + self.page_size]

        return {
            "status":      "ok",
            "page":        page,
            "total_rows":  len(data),
            "rows":        chunk.to_dict(orient="records"),
            "has_more":    (offset + self.page_size) < len(data),
            "next_cursor": offset + self.page_size,
        }

    def paginated_fetch(self, start_cursor: int = 0) -> Iterator[pd.DataFrame]:
        """
        Yield DataFrames page-by-page from the simulated API.
        Implements retry with exponential backoff on failures.
        """
        cursor = start_cursor
        page   = 1
        _rate_limiter_ts = 0.0

        while True:
            # ── Rate limiting ────────────────────────────────
            elapsed = time.time() - _rate_limiter_ts
            min_gap = 1.0 / RATE_LIMIT_RPS
            if elapsed < min_gap:
                time.sleep(min_gap - elapsed)
            _rate_limiter_ts = time.time()

            # ── Retry loop ───────────────────────────────────
            for attempt in range(1, MAX_RETRIES + 1):
                try:
                    response = self._simulate_request(page, cursor)
                    break
                except ConnectionError as exc:
                    if attempt == MAX_RETRIES:
                        log.error("Max retries exceeded on page %d: %s", page, exc)
                        raise
                    wait = RETRY_BACKOFF[attempt - 1]
                    log.warning("Retry %d/%d for page %d in %.1fs — %s",
                                attempt, MAX_RETRIES, page, wait, exc)
                    time.sleep(wait)

            rows = response["rows"]
            if not rows:
                break

            yield pd.DataFrame(rows)

            log.info("  Page %3d | cursor %-9d | rows this page: %5d | total fetched: ~%d",
                     page, cursor, len(rows),
                     cursor + len(rows))

            if not response["has_more"]:
                break

            cursor = response["next_cursor"]
            page  += 1


def fetch_and_refresh() -> None:
    """
    Full refresh of the engagement events table.
    Steps:
      1. Paginate through the API endpoint
      2. Concatenate all pages
      3. Deduplicate (the raw data intentionally contains ~0.5% dupes)
      4. Write refreshed CSV back to data/raw/
    """
    if not SRC_CSV.exists():
        log.error("Source file not found: %s — run 01_generate_data.py first.", SRC_CSV)
        return

    log.info("=" * 60)
    log.info("ShareChat Engagement Events — API Refresh")
    log.info("Endpoint:  %s", API_BASE_URL)
    log.info("Page size: %d rows", PAGE_SIZE)
    log.info("=" * 60)

    client = SimulatedAPIClient(base_url=API_BASE_URL, page_size=PAGE_SIZE)

    t0     = time.time()
    pages  = []
    total  = 0

    for page_df in client.paginated_fetch():
        pages.append(page_df)
        total += len(page_df)

    log.info("Fetch complete. Pages: %d | Raw rows: %d", len(pages), total)

    # ── Concatenate ──────────────────────────────────────────
    raw_df = pd.concat(pages, ignore_index=True)
    log.info("Rows before dedup: %d", len(raw_df))

    # ── Deduplication ────────────────────────────────────────
    # In a real pipeline you'd dedup on (event_id) or a composite key.
    before = len(raw_df)
    raw_df = raw_df.drop_duplicates(subset=["event_id"])
    after  = len(raw_df)
    log.info("Duplicates removed: %d (%.2f%%)", before - after, (before - after) / before * 100)

    # ── Write output ─────────────────────────────────────────
    raw_df.to_csv(OUT_CSV, index=False)
    size_mb = OUT_CSV.stat().st_size / 1_048_576
    elapsed = time.time() - t0
    log.info("Written → %s  (%d rows | %.1f MB | %.1fs)",
             OUT_CSV, len(raw_df), size_mb, elapsed)

    # ── Summary stats ────────────────────────────────────────
    log.info("")
    log.info("── Post-fetch Summary ──────────────────────────────")
    log.info("Event type distribution:")
    for etype, cnt in raw_df["event_type"].value_counts().items():
        log.info("  %-10s %7d  (%.1f%%)", etype, cnt, cnt / len(raw_df) * 100)


if __name__ == "__main__":
    fetch_and_refresh()
