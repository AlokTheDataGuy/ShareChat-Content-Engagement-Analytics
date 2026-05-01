from fastapi import APIRouter
from app.core.database import query
from app.core.cache import cached

router = APIRouter(prefix="/users", tags=["users"])


@router.get("/segments")
@cached
def get_user_segments():
    rows = query("""
        SELECT u.city_tier, u.device_type,
               COUNT(DISTINCT s.user_id) as users,
               ROUND(AVG(s.session_duration_sec)/60.0, 2) as avg_session_min,
               ROUND(AVG(s.posts_viewed), 1) as avg_posts_viewed
        FROM fact_sessions s
        JOIN dim_users u ON s.user_id = u.user_id
        GROUP BY u.city_tier, u.device_type
        ORDER BY u.city_tier, u.device_type
    """)
    return rows


@router.get("/session-by-hour")
@cached
def get_sessions_by_hour():
    rows = query("""
        SELECT strftime('%H', session_start) as hour,
               COUNT(*) as sessions,
               ROUND(AVG(session_duration_sec)/60.0, 2) as avg_duration_min
        FROM fact_sessions
        GROUP BY hour
        ORDER BY hour
    """)
    return rows


@router.get("/retention-curve")
@cached
def get_retention_curve():
    rows = query("""
        WITH first_session AS (
            SELECT user_id, MIN(date(session_start)) as cohort_date
            FROM fact_sessions
            GROUP BY user_id
        ),
        activity AS (
            SELECT s.user_id,
                   julianday(date(s.session_start)) - julianday(f.cohort_date) as day_num
            FROM fact_sessions s
            JOIN first_session f ON s.user_id = f.user_id
        )
        SELECT CAST(day_num AS INT) as day,
               COUNT(DISTINCT user_id) as retained_users
        FROM activity
        WHERE day_num BETWEEN 0 AND 30
        GROUP BY day_num
        ORDER BY day_num
    """)
    if rows:
        d0 = next((r["retained_users"] for r in rows if r["day"] == 0), 1)
        for r in rows:
            r["retention_rate"] = round(r["retained_users"] / d0 * 100, 2)
    return rows


@router.get("/tier-breakdown")
@cached
def get_tier_breakdown():
    rows = query("""
        SELECT u.city_tier,
               COUNT(DISTINCT u.user_id) as total_users,
               ROUND(AVG(s.session_duration_sec)/60.0, 2) as avg_session_min
        FROM dim_users u
        LEFT JOIN fact_sessions s ON u.user_id = s.user_id
        GROUP BY u.city_tier
        ORDER BY u.city_tier
    """)
    return rows
