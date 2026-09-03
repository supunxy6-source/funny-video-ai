"""Settings endpoints — system configuration."""

from fastapi import APIRouter, Depends
from app.api.deps import require_admin
from app.core.config import settings
from app.schemas import SettingsResponse, SettingsUpdate
from app.services.youtube.auth import get_channel_info

router = APIRouter()


def _build_settings_response() -> SettingsResponse:
    """Build SettingsResponse with YouTube and Facebook connection info."""
    channel_info = get_channel_info()

    # Fetch Facebook page info (lazy import to avoid circular deps)
    try:
        from app.services.facebook.uploader import get_facebook_page_info
        fb_page_info = get_facebook_page_info()
    except Exception:
        fb_page_info = None

    return SettingsResponse(
        llm_primary_provider=settings.llm_primary_provider,
        daily_video_count=getattr(settings, "daily_video_count", 3),
        pipeline_schedule_hour=settings.pipeline_schedule_hour,
        pipeline_schedule_minute=settings.pipeline_schedule_minute,
        pipeline_schedule_hours=getattr(settings, "pipeline_schedule_hours", "8,12,16,20"),
        pipeline_timezone=settings.pipeline_timezone,
        news_discovery_interval_minutes=settings.news_discovery_interval_minutes,
        elevenlabs_voice_id=settings.elevenlabs_voice_id,
        edge_tts_voice=getattr(settings, "edge_tts_voice", "en-US-AriaNeural"),
        video_format=getattr(settings, "video_format", "shorts"),
        youtube_category_id=settings.youtube_category_id,
        youtube_playlist_id=settings.youtube_playlist_id,
        youtube_auto_publish=getattr(settings, "youtube_auto_publish", True),
        youtube_default_privacy=getattr(settings, "youtube_default_privacy", "public"),
        youtube_channel_info=channel_info if channel_info.get("authenticated") else None,
        facebook_auto_publish=getattr(settings, "facebook_auto_publish", True),
        facebook_page_info=fb_page_info if fb_page_info and fb_page_info.get("connected") else None,
    )


@router.get("", response_model=SettingsResponse)
async def get_settings(_=Depends(require_admin)):
    """Get current system settings."""
    return _build_settings_response()


@router.put("", response_model=SettingsResponse)
async def update_settings(data: SettingsUpdate, _=Depends(require_admin)):
    """Update system settings."""
    if data.daily_video_count is not None:
        settings.daily_video_count = data.daily_video_count
    if data.youtube_auto_publish is not None:
        settings.youtube_auto_publish = data.youtube_auto_publish
    if data.youtube_default_privacy is not None:
        settings.youtube_default_privacy = data.youtube_default_privacy
    if data.pipeline_schedule_hours is not None:
        settings.pipeline_schedule_hours = data.pipeline_schedule_hours
    if data.pipeline_schedule_hour is not None:
        settings.pipeline_schedule_hour = data.pipeline_schedule_hour
    if data.llm_primary_provider is not None:
        settings.llm_primary_provider = data.llm_primary_provider
    if data.elevenlabs_voice_id is not None:
        settings.elevenlabs_voice_id = data.elevenlabs_voice_id
    if data.edge_tts_voice is not None:
        settings.edge_tts_voice = data.edge_tts_voice
    if data.video_format is not None:
        settings.video_format = data.video_format
    if data.youtube_category_id is not None:
        settings.youtube_category_id = data.youtube_category_id
    if data.youtube_playlist_id is not None:
        settings.youtube_playlist_id = data.youtube_playlist_id
    if data.facebook_auto_publish is not None:
        settings.facebook_auto_publish = data.facebook_auto_publish

    return _build_settings_response()

