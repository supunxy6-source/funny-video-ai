"""Analytics endpoints — YouTube channel and video analytics."""

from fastapi import APIRouter, Depends
from app.api.deps import get_current_user
from app.schemas import AnalyticsOverview

router = APIRouter()


@router.get("/overview", response_model=AnalyticsOverview)
async def get_analytics_overview(_=Depends(get_current_user)):
    """Get channel analytics overview. Placeholder — connect to YouTube Analytics API."""
    return AnalyticsOverview(
        total_views=0,
        total_subscribers=0,
        estimated_revenue=0.0,
        avg_view_duration=0.0,
        videos_this_week=0,
        views_this_week=0,
    )
