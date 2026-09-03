"""
AI News Studio — API v1 Router

Aggregates all endpoint modules into a single router.
"""

from fastapi import APIRouter

from app.api.v1.endpoints import (
    auth,
    dashboard,
    jobs,
    articles,
    scripts,
    videos,
    uploads,
    analytics,
    settings as settings_ep,
    logs,
)

api_router = APIRouter()

api_router.include_router(auth.router, prefix="/auth", tags=["Authentication"])
api_router.include_router(dashboard.router, prefix="/dashboard", tags=["Dashboard"])
api_router.include_router(jobs.router, prefix="/jobs", tags=["Jobs"])
api_router.include_router(articles.router, prefix="/articles", tags=["Articles"])
api_router.include_router(scripts.router, prefix="/scripts", tags=["Scripts"])
api_router.include_router(videos.router, prefix="/videos", tags=["Videos"])
api_router.include_router(uploads.router, prefix="/uploads", tags=["Uploads"])
api_router.include_router(analytics.router, prefix="/analytics", tags=["Analytics"])
api_router.include_router(settings_ep.router, prefix="/settings", tags=["Settings"])
api_router.include_router(logs.router, prefix="/logs", tags=["Logs"])
