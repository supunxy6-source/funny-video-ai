"""Dashboard endpoints — aggregate statistics."""

from datetime import datetime, timezone, timedelta

from fastapi import APIRouter, Depends
from sqlalchemy import select, func
from sqlalchemy.ext.asyncio import AsyncSession

from app.api.deps import get_current_user
from app.db.session import get_db
from app.models.article import NewsArticle
from app.models.video import Video
from app.models.job import Job
from app.models.upload import Upload
from app.schemas import DashboardStats

router = APIRouter()


@router.get("/stats", response_model=DashboardStats)
async def get_dashboard_stats(db: AsyncSession = Depends(get_db), _=Depends(get_current_user)):
    """Get aggregate dashboard statistics."""
    now = datetime.now(timezone.utc)
    today_start = now.replace(hour=0, minute=0, second=0, microsecond=0)

    total_videos = (await db.execute(select(func.count(Video.id)))).scalar() or 0
    total_articles = (await db.execute(select(func.count(NewsArticle.id)))).scalar() or 0
    videos_today = (await db.execute(
        select(func.count(Video.id)).where(Video.created_at >= today_start)
    )).scalar() or 0
    articles_today = (await db.execute(
        select(func.count(NewsArticle.id)).where(NewsArticle.created_at >= today_start)
    )).scalar() or 0
    active_jobs = (await db.execute(
        select(func.count(Job.id)).where(Job.status.in_(["pending", "running"]))
    )).scalar() or 0
    total_uploads = (await db.execute(
        select(func.count(Upload.id)).where(Upload.status == "published")
    )).scalar() or 0

    total_jobs = (await db.execute(select(func.count(Job.id)))).scalar() or 1
    success_jobs = (await db.execute(
        select(func.count(Job.id)).where(Job.status == "completed")
    )).scalar() or 0
    success_rate = success_jobs / total_jobs if total_jobs > 0 else 0.0

    last_run = (await db.execute(
        select(Job.started_at).order_by(Job.started_at.desc()).limit(1)
    )).scalar()

    return DashboardStats(
        total_videos=total_videos,
        total_articles=total_articles,
        videos_today=videos_today,
        articles_today=articles_today,
        active_jobs=active_jobs,
        total_uploads=total_uploads,
        success_rate=round(success_rate, 3),
        last_pipeline_run=last_run,
    )
