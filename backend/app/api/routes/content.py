from fastapi import APIRouter
from app.core.database import query
from app.core.cache import cached

router = APIRouter(prefix="/content", tags=["content"])


@router.get("/language-performance")
@cached
def get_language_performance():
    rows = query("""
        SELECT c.language,
               COUNT(e.event_id) as total_events,
               ROUND(100.0 * COUNT(CASE WHEN e.event_type='like' THEN 1 END) / COUNT(*), 2) as like_rate,
               ROUND(100.0 * COUNT(CASE WHEN e.event_type='share' THEN 1 END) / COUNT(*), 2) as share_rate,
               ROUND(AVG(e.watch_duration_sec), 1) as avg_watch_sec
        FROM fact_engagement_events e
        JOIN dim_content c ON e.post_id = c.post_id
        GROUP BY c.language
        ORDER BY total_events DESC
        LIMIT 15
    """)
    return rows


@router.get("/content-types")
@cached
def get_content_types():
    rows = query("""
        SELECT c.content_type,
               COUNT(DISTINCT c.post_id) as posts,
               COUNT(e.event_id) as events,
               ROUND(100.0 * COUNT(CASE WHEN e.event_type IN ('like','share','comment') THEN 1 END) / COUNT(*), 2) as eng_rate,
               ROUND(AVG(e.watch_duration_sec), 1) as avg_watch_sec
        FROM dim_content c
        LEFT JOIN fact_engagement_events e ON c.post_id = e.post_id
        GROUP BY c.content_type
        ORDER BY eng_rate DESC
    """)
    return rows


@router.get("/top-creators")
@cached
def get_top_creators():
    rows = query("""
        SELECT cr.creator_id,
               cr.creator_tier,
               cr.follower_count,
               cr.content_category,
               COUNT(e.event_id) as total_engagements,
               ROUND(100.0 * COUNT(CASE WHEN e.event_type IN ('like','share','comment') THEN 1 END) / COUNT(*), 2) as eng_rate
        FROM dim_creators cr
        JOIN fact_engagement_events e ON cr.creator_id = e.creator_id
        GROUP BY cr.creator_id
        ORDER BY total_engagements DESC
        LIMIT 20
    """)
    return rows


@router.get("/creator-tiers")
@cached
def get_creator_tiers():
    rows = query("""
        SELECT cr.creator_tier,
               COUNT(DISTINCT cr.creator_id) as creators,
               SUM(e_count) as total_events,
               ROUND(AVG(eng_rate), 2) as avg_eng_rate
        FROM (
            SELECT e.creator_id,
                   COUNT(*) as e_count,
                   ROUND(100.0 * COUNT(CASE WHEN e.event_type IN ('like','share','comment') THEN 1 END) / COUNT(*), 2) as eng_rate
            FROM fact_engagement_events e
            GROUP BY e.creator_id
        ) sub
        JOIN dim_creators cr ON sub.creator_id = cr.creator_id
        GROUP BY cr.creator_tier
        ORDER BY total_events DESC
    """)
    return rows
