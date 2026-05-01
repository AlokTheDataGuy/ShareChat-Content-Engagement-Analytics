from fastapi import APIRouter
from app.core.database import query
from app.core.cache import cached

router = APIRouter(prefix="/monetisation", tags=["monetisation"])


@router.get("/kpis")
@cached
def get_monetisation_kpis():
    rows = query("""
        SELECT
            ROUND(SUM(revenue_inr), 2) as total_revenue,
            ROUND(SUM(revenue_inr) / COUNT(DISTINCT user_id), 2) as arpu,
            ROUND(100.0 * SUM(was_clicked) / COUNT(*), 2) as ctr,
            ROUND(100.0 * SUM(was_converted) / NULLIF(SUM(was_clicked), 0), 2) as cvr,
            COUNT(*) as total_impressions,
            SUM(was_clicked) as total_clicks
        FROM fact_ad_impressions
    """)
    return rows[0]


@router.get("/arpu-by-tier")
@cached
def get_arpu_by_tier():
    rows = query("""
        SELECT u.city_tier,
               COUNT(DISTINCT a.user_id) as users,
               ROUND(SUM(a.revenue_inr), 2) as total_revenue,
               ROUND(SUM(a.revenue_inr) / COUNT(DISTINCT a.user_id), 2) as arpu,
               ROUND(100.0 * SUM(a.was_clicked) / COUNT(*), 2) as ctr
        FROM fact_ad_impressions a
        JOIN dim_users u ON a.user_id = u.user_id
        GROUP BY u.city_tier
        ORDER BY u.city_tier
    """)
    return rows


@router.get("/revenue-trend")
@cached
def get_revenue_trend():
    rows = query("""
        SELECT date(impression_timestamp) as date,
               ROUND(SUM(revenue_inr), 2) as daily_revenue,
               COUNT(*) as impressions,
               SUM(was_clicked) as clicks
        FROM fact_ad_impressions
        GROUP BY date(impression_timestamp)
        ORDER BY date
        LIMIT 90
    """)
    return rows


@router.get("/device-monetisation")
@cached
def get_device_monetisation():
    rows = query("""
        SELECT u.device_type,
               ROUND(SUM(a.revenue_inr) / COUNT(DISTINCT a.user_id), 2) as arpu,
               ROUND(100.0 * SUM(a.was_clicked) / COUNT(*), 2) as ctr
        FROM fact_ad_impressions a
        JOIN dim_users u ON a.user_id = u.user_id
        GROUP BY u.device_type
        ORDER BY arpu DESC
    """)
    return rows
