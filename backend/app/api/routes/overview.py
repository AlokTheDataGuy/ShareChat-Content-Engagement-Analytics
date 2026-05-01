from fastapi import APIRouter
from app.core.database import query, get_connection
from app.core.cache import cached

router = APIRouter(prefix="/overview", tags=["overview"])


@router.get("/kpis")
@cached
def get_kpis():
    with get_connection() as conn:
        def q(sql):
            return dict(conn.execute(sql).fetchone())

        dau         = q("SELECT COUNT(DISTINCT user_id) as dau FROM fact_sessions WHERE date(session_start) = (SELECT MAX(date(session_start)) FROM fact_sessions)")
        wau         = q("SELECT COUNT(DISTINCT user_id) as wau FROM fact_sessions WHERE date(session_start) >= date((SELECT MAX(date(session_start)) FROM fact_sessions), '-7 days')")
        mau         = q("SELECT COUNT(DISTINCT user_id) as mau FROM fact_sessions WHERE date(session_start) >= date((SELECT MAX(date(session_start)) FROM fact_sessions), '-30 days')")
        avg_session = q("SELECT ROUND(AVG(session_duration_sec) / 60.0, 2) as avg_session_minutes FROM fact_sessions WHERE session_duration_sec > 0")
        engagement  = q("SELECT ROUND(100.0 * SUM(CASE WHEN event_type IN ('like','share','comment') THEN 1 ELSE 0 END) / COUNT(*), 2) as engagement_rate FROM fact_engagement_events")
        arpu        = q("SELECT ROUND(SUM(revenue_inr) / COUNT(DISTINCT user_id), 2) as arpu FROM fact_ad_impressions")
        total_events= q("SELECT COUNT(*) as total FROM fact_engagement_events")

    return {
        "dau": dau["dau"],
        "wau": wau["wau"],
        "mau": mau["mau"],
        "stickiness": round(dau["dau"] / mau["mau"] * 100, 1) if mau["mau"] else 0,
        "avg_session_minutes": avg_session["avg_session_minutes"],
        "engagement_rate": engagement["engagement_rate"],
        "arpu": arpu["arpu"],
        "total_events": total_events["total"],
    }


@router.get("/dau-trend")
@cached
def get_dau_trend():
    rows = query("""
        SELECT date(session_start) as date, COUNT(DISTINCT user_id) as dau
        FROM fact_sessions
        GROUP BY date(session_start)
        ORDER BY date
        LIMIT 90
    """)
    return rows


@router.get("/engagement-breakdown")
@cached
def get_engagement_breakdown():
    rows = query("""
        SELECT event_type, COUNT(*) as count
        FROM fact_engagement_events
        GROUP BY event_type
        ORDER BY count DESC
    """)
    return rows


@router.get("/top-content-types")
@cached
def get_top_content_types():
    rows = query("""
        SELECT c.content_type,
               COUNT(e.event_id) as events,
               ROUND(100.0 * COUNT(CASE WHEN e.event_type IN ('like','share','comment') THEN 1 END) / COUNT(*), 2) as eng_rate
        FROM fact_engagement_events e
        JOIN dim_content c ON e.post_id = c.post_id
        GROUP BY c.content_type
        ORDER BY events DESC
    """)
    return rows
