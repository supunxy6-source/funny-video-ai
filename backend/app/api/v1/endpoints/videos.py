"""Videos endpoints — manage generated videos."""

from fastapi import APIRouter, Depends, HTTPException, Query
from sqlalchemy import select, func, desc
from sqlalchemy.ext.asyncio import AsyncSession

from app.api.deps import get_current_user
from app.db.session import get_db
from app.models.video import Video
from app.models.upload import Upload
from app.schemas import VideoResponse, VideoListResponse

router = APIRouter()


@router.get("", response_model=VideoListResponse)
async def list_videos(
    page: int = Query(1, ge=1),
    page_size: int = Query(20, ge=1, le=100),
    status: str = Query(None),
    db: AsyncSession = Depends(get_db),
    _=Depends(get_current_user),
):
    """List generated videos with their YouTube status."""
    query = select(Video)
    count_query = select(func.count(Video.id))

    if status:
        query = query.where(Video.status == status)
        count_query = count_query.where(Video.status == status)

    total = (await db.execute(count_query)).scalar() or 0
    result = await db.execute(
        query.order_by(desc(Video.created_at))
        .offset((page - 1) * page_size).limit(page_size)
    )
    videos = result.scalars().all()

    items = []
    for v in videos:
        # Find latest upload for this video
        up_res = await db.execute(select(Upload).where(Upload.video_id == v.id).order_by(desc(Upload.id)))
        latest_up = up_res.scalars().first()
        v_dict = {
            "id": v.id,
            "script_id": v.script_id,
            "file_path": v.file_path,
            "subtitle_path": v.subtitle_path,
            "duration": v.duration,
            "resolution": v.resolution,
            "fps": v.fps,
            "file_size": v.file_size,
            "codec": v.codec,
            "status": v.status,
            "created_at": v.created_at,
            "youtube_video_id": latest_up.youtube_video_id if latest_up else None,
            "upload_status": latest_up.status if latest_up else None,
        }
        items.append(VideoResponse.model_validate(v_dict))

    return VideoListResponse(items=items, total=total, page=page, page_size=page_size)


@router.get("/{video_id}", response_model=VideoResponse)
async def get_video(video_id: int, db: AsyncSession = Depends(get_db), _=Depends(get_current_user)):
    """Get a specific video with its YouTube status."""
    video = await db.get(Video, video_id)
    if not video:
        raise HTTPException(status_code=404, detail="Video not found")

    up_res = await db.execute(select(Upload).where(Upload.video_id == video.id).order_by(desc(Upload.id)))
    latest_up = up_res.scalars().first()
    v_dict = {
        "id": video.id,
        "script_id": video.script_id,
        "file_path": video.file_path,
        "subtitle_path": video.subtitle_path,
        "duration": video.duration,
        "resolution": video.resolution,
        "fps": video.fps,
        "file_size": video.file_size,
        "codec": video.codec,
        "status": video.status,
        "created_at": video.created_at,
        "youtube_video_id": latest_up.youtube_video_id if latest_up else None,
        "upload_status": latest_up.status if latest_up else None,
    }
    return VideoResponse.model_validate(v_dict)
