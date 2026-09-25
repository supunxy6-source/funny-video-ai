"""
Stateside Smiles — Scheduled Tasks

Celery Beat schedule configuration for automated daily pipeline
and periodic maintenance tasks.
"""

import logging
import os
import time
from pathlib import Path

from celery.schedules import crontab

from app.core.config import settings
from app.tasks.celery_app import celery_app

logger = logging.getLogger(__name__)

# ── Register Beat Schedule ─────────────────────────────
# Parse scheduled hours for daily video pipeline (e.g. "8,12,16,20" or single hour)
def _get_schedule_hours():
    raw = getattr(settings, "pipeline_schedule_hours", "")
    if raw and raw.strip():
        try:
            return ",".join(str(int(h.strip())) for h in raw.split(",") if h.strip())
        except Exception:
            pass
    return str(settings.pipeline_schedule_hour)

celery_app.conf.beat_schedule = {
    # Automated daily batch video production pipeline (produces 4 comedy videos per batch × 3 batches & publishes to YouTube)
    "daily-pipeline": {
        "task": "app.tasks.pipeline.run_full_pipeline",
        "schedule": crontab(
            hour=_get_schedule_hours(),
            minute=settings.pipeline_schedule_minute,
        ),
        "options": {"queue": "default"},
    },

    # Content discovery (entertainment: every 2h, news: every 1h)
    "periodic-discovery": {
        "task": "app.tasks.pipeline.task_discover_news",
        "schedule": crontab(
            minute=0,
            hour=f"*/{max(1, getattr(settings, 'content_discovery_interval_minutes', 120) // 60)}",
        ),
        "args": ["periodic_discovery"],
        "options": {"queue": "discovery"},
    },

    # Daily cleanup of old temp files (2 AM)
    "daily-cleanup": {
        "task": "app.tasks.scheduled.cleanup_temp_files",
        "schedule": crontab(hour=2, minute=0),
        "options": {"queue": "default"},
    },

    # Catch-up pipeline — runs 2h after each scheduled batch to verify
    # videos were actually published. If upload count is below target,
    # triggers a rescue batch to fill the gap.
    "pipeline-catchup": {
        "task": "app.tasks.pipeline.run_catchup_pipeline",
        "schedule": crontab(hour="3,13,20", minute=0),
        "options": {"queue": "default"},
    },

    # First-hour comment engagement — interact with viewer comments
    # on recently uploaded videos. YouTube's 2026 algorithm heavily
    # weights creator engagement in the first hour after upload.
    # Runs every 30 minutes during US waking hours (7 AM - 11 PM UTC).
    "comment-engagement": {
        "task": "app.tasks.pipeline.engage_recent_uploads",
        "schedule": crontab(minute="*/30", hour="7-23"),
        "options": {"queue": "default"},
    },
}

# ── Conditional: Regular (Long-Form) Video Pipeline ────────
# Adds a separate daily schedule for producing 1 regular 16:9 video
if getattr(settings, "regular_video_enabled", True):
    _regular_hour = getattr(settings, "regular_video_schedule_hour", 10)
    celery_app.conf.beat_schedule["daily-regular-video"] = {
        "task": "app.tasks.pipeline.run_regular_video_pipeline",
        "schedule": crontab(
            hour=_regular_hour,
            minute=0,
        ),
        "options": {"queue": "default"},
    }


@celery_app.task(name="app.tasks.scheduled.cleanup_temp_files")
def cleanup_temp_files():
    """Remove temporary files older than 7 days."""
    import os
    import time
    from pathlib import Path

    temp_dir = Path(settings.media_root) / "temp"
    if not temp_dir.exists():
        return

    cutoff = time.time() - (7 * 86400)  # 7 days
    removed = 0

    for f in temp_dir.rglob("*"):
        if f.is_file() and f.stat().st_mtime < cutoff:
            f.unlink()
            removed += 1

    if removed:
        import logging
        logging.getLogger(__name__).info(f"🧹 Cleaned up {removed} temp files")
