from fastapi import APIRouter
from app.core.database import query
from app.core.cache import cached

router = APIRouter(prefix="/language", tags=["language"])


@router.get("/cross-analysis")
@cached
def get_cross_analysis():
    rows = query("""
        SELECT c.language,
               COUNT(DISTINCT e.user_id) as unique_users,
               COUNT(e.event_id) as total_events,
               ROUND(100.0 * COUNT(CASE WHEN e.event_type='like' THEN 1 END) / COUNT(*), 2) as like_rate,
               ROUND(100.0 * COUNT(CASE WHEN e.event_type='share' THEN 1 END) / COUNT(*), 2) as share_rate,
               ROUND(100.0 * COUNT(CASE WHEN e.event_type='comment' THEN 1 END) / COUNT(*), 2) as comment_rate,
               ROUND(AVG(e.watch_duration_sec), 1) as avg_watch_sec
        FROM fact_engagement_events e
        JOIN dim_content c ON e.post_id = c.post_id
        GROUP BY c.language
        ORDER BY total_events DESC
    """)
    return rows


@router.get("/user-language-match")
@cached
def get_user_language_match():
    rows = query("""
        SELECT
            CASE WHEN u.signup_language = c.language THEN 'Native' ELSE 'Cross-Language' END as match_type,
            COUNT(e.event_id) as events,
            ROUND(100.0 * COUNT(CASE WHEN e.event_type IN ('like','share','comment') THEN 1 END) / COUNT(*), 2) as eng_rate
        FROM fact_engagement_events e
        JOIN dim_users u ON e.user_id = u.user_id
        JOIN dim_content c ON e.post_id = c.post_id
        GROUP BY match_type
    """)
    return rows
