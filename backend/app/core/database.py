import sqlite3
from pathlib import Path

DB_PATH = Path(__file__).resolve().parents[3] / "data" / "warehouse" / "sharechat_warehouse.db"


def get_connection():
    conn = sqlite3.connect(DB_PATH)
    conn.row_factory = sqlite3.Row
    conn.execute("PRAGMA journal_mode=WAL")
    conn.execute("PRAGMA cache_size=-65536")   # 64 MB page cache
    conn.execute("PRAGMA temp_store=MEMORY")
    conn.execute("PRAGMA synchronous=NORMAL")
    conn.execute("PRAGMA mmap_size=268435456") # 256 MB memory-mapped I/O
    return conn


def query(sql: str, params: tuple = ()):
    with get_connection() as conn:
        cursor = conn.execute(sql, params)
        rows = cursor.fetchall()
        return [dict(row) for row in rows]
