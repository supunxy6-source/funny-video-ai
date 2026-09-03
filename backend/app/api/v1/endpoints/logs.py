"""Logs endpoints — pipeline execution logs."""

from fastapi import APIRouter, Depends, Query
from sqlalchemy import select, func, desc
from sqlalchemy.ext.asyncio import AsyncSession

from app.api.deps import get_current_user
from app.db.session import get_db
from app.models.log import Log
from app.schemas import LogResponse, LogListResponse

router = APIRouter()


@router.get("", response_model=LogListResponse)
async def list_logs(
    page: int = Query(1, ge=1),
    page_size: int = Query(50, ge=1, le=200),
    level: str = Query(None),
    pipeline_run_id: str = Query(None),
    db: AsyncSession = Depends(get_db),
    _=Depends(get_current_user),
):
    """List pipeline logs with filtering."""
    query = select(Log)
    count_query = select(func.count(Log.id))

    if level:
        query = query.where(Log.level == level.upper())
        count_query = count_query.where(Log.level == level.upper())
    if pipeline_run_id:
        query = query.where(Log.pipeline_run_id == pipeline_run_id)
        count_query = count_query.where(Log.pipeline_run_id == pipeline_run_id)

    total = (await db.execute(count_query)).scalar() or 0
    result = await db.execute(
        query.order_by(desc(Log.timestamp))
        .offset((page - 1) * page_size).limit(page_size)
    )

    return LogListResponse(
        items=[LogResponse.model_validate(log) for log in result.scalars().all()],
        total=total, page=page, page_size=page_size,
    )
