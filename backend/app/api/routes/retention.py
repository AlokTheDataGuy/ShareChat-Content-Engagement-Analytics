from fastapi import APIRouter
from app.core.database import query
from app.core.cache import cached

router = APIRouter(prefix="/retention", tags=["retention"])


@router.get("/cohort-matrix")
@cached
def get_cohort_matrix():
    rows = query("""
        WITH cohorts AS (
            SELECT user_id,
                   strftime('%Y-%m', MIN(session_start)) as cohort_month
            FROM fact_sessions
            GROUP BY user_id
        ),
        activity AS (
            SELECT s.user_id,
                   c.cohort_month,
                   strftime('%Y-%m', s.session_start) as activity_month
            FROM fact_sessions s
            JOIN cohorts c ON s.user_id = c.user_id
        ),
        cohort_sizes AS (
            SELECT cohort_month, COUNT(DISTINCT user_id) as cohort_size
            FROM cohorts
            GROUP BY cohort_month
        ),
        monthly_retention AS (
            SELECT a.cohort_month,
                   a.activity_month,
                   COUNT(DISTINCT a.user_id) as retained
            FROM activity a
            GROUP BY a.cohort_month, a.activity_month
        )
        SELECT mr.cohort_month,
               mr.activity_month,
               mr.retained,
               cs.cohort_size,
               ROUND(100.0 * mr.retained / cs.cohort_size, 1) as retention_rate
        FROM monthly_retention mr
        JOIN cohort_sizes cs ON mr.cohort_month = cs.cohort_month
        ORDER BY mr.cohort_month, mr.activity_month
    """)
    return rows


@router.get("/day-retention")
@cached
def get_day_retention():
    rows = query("""
        WITH first_day AS (
            SELECT user_id, MIN(date(session_start)) as day0
            FROM fact_sessions GROUP BY user_id
        )
        SELECT
            CAST(julianday(date(s.session_start)) - julianday(f.day0) AS INT) as day_num,
            COUNT(DISTINCT s.user_id) as users
        FROM fact_sessions s
        JOIN first_day f ON s.user_id = f.user_id
        WHERE julianday(date(s.session_start)) - julianday(f.day0) BETWEEN 0 AND 30
        GROUP BY day_num
        ORDER BY day_num
    """)
    if rows:
        d0 = next((r["users"] for r in rows if r["day_num"] == 0), 1)
        for r in rows:
            r["rate"] = round(r["users"] / d0 * 100, 2)
    return rows
