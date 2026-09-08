"""
Stateside Smiles — Application Configuration

Centralized settings management using pydantic-settings.
All configuration is loaded from environment variables with sensible defaults.
"""

from pathlib import Path
from typing import Literal

from pydantic import field_validator
from pydantic_settings import BaseSettings, SettingsConfigDict


class Settings(BaseSettings):
    """Application settings loaded from environment variables."""

    model_config = SettingsConfigDict(
        env_file=".env",
        env_file_encoding="utf-8",
        case_sensitive=False,
        extra="ignore",
    )

    # ── Application ────────────────────────────────────
    app_name: str = "Stateside Smiles"
    app_env: Literal["development", "staging", "production"] = "development"
    debug: bool = False
    secret_key: str = "change-me-to-a-random-64-char-string"
    api_v1_prefix: str = "/api/v1"

    # ── Content Mode ──────────────────────────────────
    content_mode: str = "entertainment"  # entertainment | news
    meme_style: str = "story"  # story | compilation | voiceover | mixed
    reddit_subreddits: str = "tifu,pettyrevenge,confession,MaliciousCompliance,AskReddit,dadjokes,jokes,funny,memes,wholesomememes,MadeMeSmile"

    # ── Database ───────────────────────────────────────
    postgres_host: str = "localhost"
    postgres_port: int = 5432
    postgres_db: str = "stateside_smiles"
    postgres_user: str = "ainews"
    postgres_password: str = "changeme"

    @property
    def database_url(self) -> str:
        return (
            f"postgresql+asyncpg://{self.postgres_user}:{self.postgres_password}"
            f"@{self.postgres_host}:{self.postgres_port}/{self.postgres_db}"
        )

    @property
    def database_url_sync(self) -> str:
        return (
            f"postgresql+psycopg://{self.postgres_user}:{self.postgres_password}"
            f"@{self.postgres_host}:{self.postgres_port}/{self.postgres_db}"
        )

    # ── Redis ──────────────────────────────────────────
    redis_host: str = "localhost"
    redis_port: int = 6379
    redis_url: str = "redis://localhost:6379/0"
    celery_broker_url: str = "redis://localhost:6379/1"
    celery_result_backend: str = "redis://localhost:6379/2"

    # ── LLM Providers ─────────────────────────────────
    llm_primary_provider: Literal["openai", "anthropic", "google"] = "openai"

    openai_api_key: str = ""
    openai_model: str = "gpt-4o"

    anthropic_api_key: str = ""
    anthropic_model: str = "claude-sonnet-4-20250514"

    google_ai_api_key: str = ""
    google_ai_model: str = "gemini-2.0-flash"

    # ── Image Generation ──────────────────────────────
    replicate_api_token: str = ""
    image_model: str = "black-forest-labs/flux-1.1-pro"
    image_fallback_model: str = "stability-ai/sdxl"

    # ── Video Generation ──────────────────────────────
    video_model: str = "wan-ai/wan2.2-t2v-14b"
    video_fallback_model: str = "tencent/hunyuan-video"

    # ── Stock Video (Pexels — Free) ──────────────────
    pexels_api_key: str = ""

    # ── Voice / TTS ────────────────────────────────────
    elevenlabs_api_key: str = ""
    elevenlabs_voice_id: str = "pNInz6obpgDQG4ZlmEQk"  # Adam (Viral Comedy Narrator)
    elevenlabs_model: str = "eleven_multilingual_v2"
    edge_tts_voice: str = "en-US-ChristopherNeural"  # Expressive comedy narrator

    # ── Video Format (Dual: Shorts 9:16 + Regular 16:9) ─
    video_format: str = "shorts"
    video_format_shorts: bool = True
    video_format_regular: bool = True
    shorts_duration_mode: Literal["micro", "standard"] = "micro"  # micro (18-25s, 90%+ retention) | standard (35-50s)
    video_width: int = 1080
    video_height: int = 1920
    video_aspect_ratio: str = "9:16"
    regular_video_width: int = 1920
    regular_video_height: int = 1080

    # ── YouTube ────────────────────────────────────────
    youtube_client_secrets_file: str = "config/client_secrets.json"
    youtube_token_file: str = "config/youtube_token.json"
    youtube_playlist_id: str = ""
    youtube_category_id: str = "23"  # Comedy
    youtube_auto_publish: bool = True  # Automatically publish generated videos to YouTube
    youtube_default_privacy: str = "public"  # public | unlisted | private

    # ── Facebook ──────────────────────────────────────
    facebook_page_id: str = ""
    facebook_page_access_token: str = ""
    facebook_auto_publish: bool = True

    # ── TikTok ────────────────────────────────────────
    tiktok_client_key: str = ""
    tiktok_client_secret: str = ""
    tiktok_access_token: str = ""
    tiktok_auto_publish: bool = True
    tiktok_post_mode: str = "direct"  # direct | inbox

    # ── Whisper ────────────────────────────────────────
    whisper_model: str = "base"
    whisper_device: str = "cpu"

    # ── Scheduling & Production Target ────────────────
    daily_video_count: int = 3  # Target videos per day (3 to 5)
    stagger_uploads_hours: int = 1  # Hours between scheduled uploads
    pipeline_schedule_hour: int = 8
    pipeline_schedule_minute: int = 0
    pipeline_schedule_hours: str = "8,12,16,20"  # Comma-separated hours for daily multi-slot schedule
    pipeline_timezone: str = "UTC"
    content_discovery_interval_minutes: int = 120

    # ── Notifications ──────────────────────────────────
    smtp_host: str = "smtp.gmail.com"
    smtp_port: int = 587
    smtp_user: str = ""
    smtp_password: str = ""
    smtp_from: str = "noreply@statesidesmiles.com"
    notification_email: str = ""
    slack_webhook_url: str = ""

    # ── File Storage ───────────────────────────────────
    media_root: str = "/app/media"
    generated_dir: str = "/app/media/generated"

    @property
    def media_path(self) -> Path:
        path = Path(self.media_root)
        path.mkdir(parents=True, exist_ok=True)
        return path

    @property
    def generated_path(self) -> Path:
        path = Path(self.generated_dir)
        path.mkdir(parents=True, exist_ok=True)
        return path

    # ── Admin ──────────────────────────────────────────
    admin_email: str = "admin@statesidesmiles.com"
    admin_password: str = "changeme"

    # ── JWT ────────────────────────────────────────────
    jwt_algorithm: str = "HS256"
    jwt_access_token_expire_minutes: int = 60
    jwt_refresh_token_expire_days: int = 7


# Singleton settings instance
settings = Settings()
