"""Jobs endpoints — pipeline monitoring and triggering."""

from fastapi import APIRouter, Depends, HTTPException, Query
from sqlalchemy import select, func, desc
from sqlalchemy.ext.asyncio import AsyncSession

from app.api.deps import get_current_user
from app.db.session import get_db
from app.models.job import Job
from app.schemas import JobResponse, JobListResponse, PipelineStatusResponse

router = APIRouter()


@router.get("", response_model=JobListResponse)
async def list_jobs(
    page: int = Query(1, ge=1),
    page_size: int = Query(20, ge=1, le=100),
    status: str = Query(None),
    pipeline_run_id: str = Query(None),
    db: AsyncSession = Depends(get_db),
    _=Depends(get_current_user),
):
    """List pipeline jobs with pagination and filtering."""
    query = select(Job)
    count_query = select(func.count(Job.id))

    if status:
        query = query.where(Job.status == status)
        count_query = count_query.where(Job.status == status)
    if pipeline_run_id:
        query = query.where(Job.pipeline_run_id == pipeline_run_id)
        count_query = count_query.where(Job.pipeline_run_id == pipeline_run_id)

    total = (await db.execute(count_query)).scalar() or 0
    result = await db.execute(
        query.order_by(desc(Job.created_at))
        .offset((page - 1) * page_size)
        .limit(page_size)
    )

    return JobListResponse(
        items=[JobResponse.model_validate(j) for j in result.scalars().all()],
        total=total, page=page, page_size=page_size,
    )


@router.get("/{job_id}", response_model=JobResponse)
async def get_job(job_id: int, db: AsyncSession = Depends(get_db), _=Depends(get_current_user)):
    """Get a specific job by ID."""
    job = await db.get(Job, job_id)
    if not job:
        raise HTTPException(status_code=404, detail="Job not found")
    return JobResponse.model_validate(job)


@router.get("/pipeline/{run_id}", response_model=PipelineStatusResponse)
async def get_pipeline_status(run_id: str, db: AsyncSession = Depends(get_db), _=Depends(get_current_user)):
    """Get the status of all steps in a pipeline run."""
    result = await db.execute(
        select(Job).where(Job.pipeline_run_id == run_id).order_by(Job.step_order)
    )
    jobs = result.scalars().all()
    if not jobs:
        raise HTTPException(status_code=404, detail="Pipeline run not found")

    statuses = [j.status for j in jobs]
    if "failed" in statuses:
        overall = "failed"
    elif all(s == "completed" for s in statuses):
        overall = "completed"
    elif "running" in statuses:
        overall = "running"
    else:
        overall = "pending"

    return PipelineStatusResponse(
        pipeline_run_id=run_id,
        steps=[JobResponse.model_validate(j) for j in jobs],
        overall_status=overall,
        started_at=jobs[0].started_at if jobs else None,
        completed_at=jobs[-1].completed_at if jobs and jobs[-1].completed_at else None,
    )


from typing import Optional
from app.schemas import JobResponse, JobListResponse, PipelineStatusResponse, TriggerPipelineRequest


@router.post("/trigger")
async def trigger_pipeline(
    data: Optional[TriggerPipelineRequest] = None,
    _=Depends(get_current_user),
):
    """Manually trigger a full pipeline run (supports batch generation of 1 to 5 videos)."""
    from app.tasks.pipeline import run_full_pipeline
    video_count = data.video_count if data else None
    task = run_full_pipeline.delay(video_count=video_count)
    return {
        "message": f"Pipeline triggered for {video_count or 'default'} video(s)",
        "task_id": str(task),
        "video_count": video_count,
    }
