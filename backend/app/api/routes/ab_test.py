from fastapi import APIRouter
from app.core.database import query
import math

router = APIRouter(prefix="/ab-test", tags=["ab-test"])


@router.get("/results")
def get_ab_results():
    rows = query("""
        SELECT u.experiment_group,
               COUNT(DISTINCT s.user_id) as users,
               ROUND(AVG(s.session_duration_sec)/60.0, 2) as avg_session_min,
               ROUND(AVG(s.posts_viewed), 2) as avg_posts_viewed,
               ROUND(AVG(s.posts_liked * 1.0 / NULLIF(s.posts_viewed, 0)) * 100, 2) as like_rate,
               ROUND(AVG(s.posts_shared * 1.0 / NULLIF(s.posts_viewed, 0)) * 100, 2) as share_rate
        FROM fact_sessions s
        JOIN dim_users u ON s.user_id = u.user_id
        WHERE u.experiment_group IN ('control', 'treatment')
        GROUP BY u.experiment_group
    """)
    return rows


@router.get("/segment-breakdown")
def get_segment_breakdown():
    rows = query("""
        SELECT u.experiment_group,
               u.city_tier,
               COUNT(DISTINCT s.user_id) as users,
               ROUND(AVG(s.session_duration_sec)/60.0, 2) as avg_session_min
        FROM fact_sessions s
        JOIN dim_users u ON s.user_id = u.user_id
        WHERE u.experiment_group IN ('control', 'treatment')
        GROUP BY u.experiment_group, u.city_tier
        ORDER BY u.city_tier, u.experiment_group
    """)
    return rows


@router.get("/daily-trend")
def get_ab_daily_trend():
    rows = query("""
        SELECT date(s.session_start) as date,
               u.experiment_group,
               ROUND(AVG(s.session_duration_sec)/60.0, 2) as avg_session_min
        FROM fact_sessions s
        JOIN dim_users u ON s.user_id = u.user_id
        WHERE u.experiment_group IN ('control', 'treatment')
        GROUP BY date(s.session_start), u.experiment_group
        ORDER BY date, u.experiment_group
    """)
    return rows
