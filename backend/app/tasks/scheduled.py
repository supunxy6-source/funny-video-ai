"""
AI News Studio — Scheduled Tasks

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
    # Automated daily batch video production pipeline (produces 3 to 5 videos per day & publishes to YouTube)
    "daily-pipeline": {
        "task": "app.tasks.pipeline.run_full_pipeline",
        "schedule": crontab(
            hour=_get_schedule_hours(),
            minute=settings.pipeline_schedule_minute,
        ),
        "options": {"queue": "default"},
    },

    # Hourly news discovery
    "hourly-discovery": {
        "task": "app.tasks.pipeline.task_discover_news",
        "schedule": crontab(minute=0),  # Every hour at :00
        "args": ["hourly_discovery"],
        "options": {"queue": "discovery"},
    },

    # Daily cleanup of old temp files (2 AM)
    "daily-cleanup": {
        "task": "app.tasks.scheduled.cleanup_temp_files",
        "schedule": crontab(hour=2, minute=0),
        "options": {"queue": "default"},
    },
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
