"""
AI News Studio — Pydantic Schemas

Request/response validation models for all API endpoints.
"""

from datetime import datetime
from typing import Optional

from pydantic import BaseModel, EmailStr, Field


# ── User Schemas ───────────────────────────────────────

class UserBase(BaseModel):
    email: EmailStr
    full_name: str = ""
    role: str = "admin"

class UserCreate(UserBase):
    password: str = Field(..., min_length=8)

class UserLogin(BaseModel):
    email: EmailStr
    password: str

class UserResponse(UserBase):
    id: int
    is_active: bool
    created_at: datetime

    model_config = {"from_attributes": True}


# ── Article Schemas ────────────────────────────────────

class ArticleResponse(BaseModel):
    id: int
    source_id: int
    headline: str
    summary: Optional[str] = None
    url: str
    image_url: Optional[str] = None
    author: Optional[str] = None
    published_at: Optional[datetime] = None
    category: str
    cluster_id: Optional[int] = None
    credibility_score: float
    is_verified: bool
    created_at: datetime

    model_config = {"from_attributes": True}

class ArticleListResponse(BaseModel):
    items: list[ArticleResponse]
    total: int
    page: int
    page_size: int


# ── Script Schemas ─────────────────────────────────────

class ScriptResponse(BaseModel):
    id: int
    title: str
    topic_summary: str
    content: str
    content_json: Optional[str] = None
    article_ids: str
    word_count: int
    duration_estimate: float
    llm_provider: str
    llm_model: str
    status: str
    created_at: datetime

    model_config = {"from_attributes": True}

class ScriptUpdate(BaseModel):
    title: Optional[str] = None
    content: Optional[str] = None
    status: Optional[str] = None


# ── Scene Schemas ──────────────────────────────────────

class SceneResponse(BaseModel):
    id: int
    script_id: int
    order: int
    scene_type: str
    title: str
    text: str
    visual_prompt: Optional[str] = None
    visual_type: str
    image_url: Optional[str] = None
    video_url: Optional[str] = None
    audio_url: Optional[str] = None
    duration: float
    word_count: int

    model_config = {"from_attributes": True}


# ── Video Schemas ──────────────────────────────────────

class VideoResponse(BaseModel):
    id: int
    script_id: int
    file_path: str
    subtitle_path: Optional[str] = None
    duration: float
    resolution: str
    fps: int
    file_size: int
    codec: str
    status: str
    youtube_video_id: Optional[str] = None
    upload_status: Optional[str] = None
    created_at: datetime

    model_config = {"from_attributes": True}

class VideoListResponse(BaseModel):
    items: list[VideoResponse]
    total: int
    page: int
    page_size: int


# ── Thumbnail Schemas ──────────────────────────────────

class ThumbnailResponse(BaseModel):
    id: int
    video_id: int
    file_path: str
    prompt: Optional[str] = None
    predicted_ctr: float
    is_selected: bool

    model_config = {"from_attributes": True}


# ── Upload Schemas ─────────────────────────────────────

class UploadResponse(BaseModel):
    id: int
    video_id: int
    youtube_video_id: Optional[str] = None
    facebook_video_id: Optional[str] = None
    title: str
    description: str
    tags: str
    privacy_status: str
    status: str
    scheduled_at: Optional[datetime] = None
    published_at: Optional[datetime] = None
    created_at: datetime

    model_config = {"from_attributes": True}

class UploadCreateRequest(BaseModel):
    video_id: int
    privacy_status: str = "public"
    scheduled_at: Optional[datetime] = None

class UploadPublishRequest(BaseModel):
    privacy_status: str = "public"
    scheduled_at: Optional[datetime] = None


# ── Job Schemas ────────────────────────────────────────

class TriggerPipelineRequest(BaseModel):
    video_count: Optional[int] = Field(None, ge=1, le=5, description="Number of videos to generate (1 to 5)")

class JobResponse(BaseModel):
    id: int
    pipeline_run_id: str
    step_name: str
    step_order: int
    status: str
    started_at: Optional[datetime] = None
    completed_at: Optional[datetime] = None
    duration_seconds: Optional[float] = None
    error_message: Optional[str] = None
    retry_count: int
    created_at: datetime

    model_config = {"from_attributes": True}

class JobListResponse(BaseModel):
    items: list[JobResponse]
    total: int
    page: int
    page_size: int


# ── Log Schemas ────────────────────────────────────────

class LogResponse(BaseModel):
    id: int
    job_id: Optional[int] = None
    pipeline_run_id: Optional[str] = None
    level: str
    message: str
    module: Optional[str] = None
    timestamp: datetime

    model_config = {"from_attributes": True}

class LogListResponse(BaseModel):
    items: list[LogResponse]
    total: int
    page: int
    page_size: int


# ── Dashboard Schemas ──────────────────────────────────

class DashboardStats(BaseModel):
    total_videos: int
    total_articles: int
    videos_today: int
    articles_today: int
    active_jobs: int
    total_uploads: int
    success_rate: float
    last_pipeline_run: Optional[datetime] = None

class PipelineStatusResponse(BaseModel):
    pipeline_run_id: str
    steps: list[JobResponse]
    overall_status: str
    started_at: Optional[datetime] = None
    completed_at: Optional[datetime] = None


# ── Analytics Schemas ──────────────────────────────────

class AnalyticsOverview(BaseModel):
    total_views: int = 0
    total_subscribers: int = 0
    estimated_revenue: float = 0.0
    avg_view_duration: float = 0.0
    videos_this_week: int = 0
    views_this_week: int = 0

class VideoAnalytics(BaseModel):
    video_id: int
    youtube_video_id: Optional[str] = None
    title: str
    views: int = 0
    likes: int = 0
    comments: int = 0
    avg_view_duration: float = 0.0
    click_through_rate: float = 0.0


# ── Settings Schemas ───────────────────────────────────

class SettingsResponse(BaseModel):
    llm_primary_provider: str
    daily_video_count: int = 3
    pipeline_schedule_hour: int
    pipeline_schedule_minute: int
    pipeline_schedule_hours: str = "8,12,16,20"
    pipeline_timezone: str
    news_discovery_interval_minutes: int
    elevenlabs_voice_id: str
    edge_tts_voice: str = "en-US-AriaNeural"
    video_format: str = "shorts"
    youtube_category_id: str
    youtube_playlist_id: str
    youtube_auto_publish: bool = True
    youtube_default_privacy: str = "public"
    youtube_channel_info: Optional[dict] = None
    facebook_auto_publish: bool = True
    facebook_page_info: Optional[dict] = None

class SettingsUpdate(BaseModel):
    llm_primary_provider: Optional[str] = None
    daily_video_count: Optional[int] = None
    pipeline_schedule_hour: Optional[int] = None
    pipeline_schedule_minute: Optional[int] = None
    pipeline_schedule_hours: Optional[str] = None
    pipeline_timezone: Optional[str] = None
    news_discovery_interval_minutes: Optional[int] = None
    elevenlabs_voice_id: Optional[str] = None
    edge_tts_voice: Optional[str] = None
    video_format: Optional[str] = None
    youtube_category_id: Optional[str] = None
    youtube_playlist_id: Optional[str] = None
    youtube_auto_publish: Optional[bool] = None
    youtube_default_privacy: Optional[str] = None
    facebook_auto_publish: Optional[bool] = None

