"""Uploads endpoints — YouTube, Facebook, and TikTok upload status and manual publish."""

from fastapi import APIRouter, Depends, HTTPException, Query
from sqlalchemy import select, func, desc
from sqlalchemy.ext.asyncio import AsyncSession

from app.api.deps import get_current_user
from app.db.session import get_db
from app.models.upload import Upload
from app.models.video import Video
from app.schemas import UploadResponse, UploadCreateRequest, UploadPublishRequest
from app.services.youtube.auth import get_channel_info

router = APIRouter()


@router.get("/youtube/channel")
async def get_youtube_channel_status(_=Depends(get_current_user)):
    """Get authenticated YouTube channel information and status."""
    return get_channel_info()


@router.get("/facebook/page")
async def get_facebook_page_status(_=Depends(get_current_user)):
    """Get connected Facebook Page information and status."""
    from app.services.facebook.uploader import get_facebook_page_info
    return get_facebook_page_info()


@router.get("/tiktok/account")
async def get_tiktok_account_status(_=Depends(get_current_user)):
    """Get connected TikTok account information and status."""
    from app.services.tiktok.uploader import get_tiktok_account_info
    return get_tiktok_account_info()


@router.get("")
async def list_uploads(
    page: int = Query(1, ge=1),
    page_size: int = Query(20, ge=1, le=100),
    status: str = Query(None),
    db: AsyncSession = Depends(get_db),
    _=Depends(get_current_user),
):
    """List YouTube and Facebook uploads."""
    query = select(Upload)
    count_query = select(func.count(Upload.id))
    if status:
        query = query.where(Upload.status == status)
        count_query = count_query.where(Upload.status == status)

    total = (await db.execute(count_query)).scalar() or 0
    result = await db.execute(
        query.order_by(desc(Upload.created_at))
        .offset((page - 1) * page_size).limit(page_size)
    )

    return {
        "items": [UploadResponse.model_validate(u) for u in result.scalars().all()],
        "total": total, "page": page, "page_size": page_size,
    }


@router.post("")
async def create_and_publish_upload(
    data: UploadCreateRequest,
    db: AsyncSession = Depends(get_db),
    _=Depends(get_current_user),
):
    """Trigger YouTube and Facebook publishing for a video by video ID."""
    video = await db.get(Video, data.video_id)
    if not video:
        raise HTTPException(status_code=404, detail=f"Video #{data.video_id} not found")

    # Find existing upload or generate SEO & upload record
    result = await db.execute(select(Upload).where(Upload.video_id == data.video_id).order_by(desc(Upload.id)))
    upload = result.scalars().first()

    if not upload:
        from app.services.seo.optimizer import optimize_seo
        upload_id = await optimize_seo(data.video_id)
        upload = await db.get(Upload, upload_id)

    upload.privacy_status = data.privacy_status
    if data.scheduled_at:
        upload.scheduled_at = data.scheduled_at
    upload.status = "pending"
    await db.commit()

    pipeline_run_id = f"manual_upload_{video.id}"
    task_payload = {
        "pipeline_run_id": pipeline_run_id,
        "upload_id": upload.id,
        "video_id": upload.video_id,
    }

    # Trigger YouTube upload
    from app.tasks.pipeline import task_upload_youtube
    task_upload_youtube.delay(task_payload)

    # Trigger Facebook upload
    from app.tasks.pipeline import task_upload_facebook
    task_upload_facebook.delay(task_payload)

    # Trigger TikTok upload
    from app.tasks.pipeline import task_upload_tiktok
    task_upload_tiktok.delay(task_payload)

    return {
        "message": f"Publishing video #{video.id} to YouTube, Facebook, and TikTok as '{data.privacy_status}'",
        "upload_id": upload.id,
        "privacy_status": upload.privacy_status,
        "status": "upload_triggered",
    }


@router.post("/{upload_id}/publish")
async def publish_upload(
    upload_id: int,
    data: UploadPublishRequest,
    db: AsyncSession = Depends(get_db),
    _=Depends(get_current_user),
):
    """Manually trigger YouTube and Facebook upload for a pending upload record."""
    upload = await db.get(Upload, upload_id)
    if not upload:
        raise HTTPException(status_code=404, detail="Upload not found")
    if upload.status not in ("pending", "failed", "local_render_complete"):
        raise HTTPException(status_code=400, detail=f"Cannot publish upload with status '{upload.status}'")

    upload.privacy_status = data.privacy_status
    upload.scheduled_at = data.scheduled_at
    upload.status = "pending"
    await db.commit()

    task_payload = {
        "pipeline_run_id": "manual",
        "upload_id": upload_id,
        "video_id": upload.video_id,
    }

    # Trigger YouTube upload
    from app.tasks.pipeline import task_upload_youtube
    task_upload_youtube.delay(task_payload)

    # Trigger Facebook upload
    from app.tasks.pipeline import task_upload_facebook
    task_upload_facebook.delay(task_payload)

    # Trigger TikTok upload
    from app.tasks.pipeline import task_upload_tiktok
    task_upload_tiktok.delay(task_payload)

    return {"message": "Upload triggered to YouTube, Facebook, and TikTok", "upload_id": upload_id}

