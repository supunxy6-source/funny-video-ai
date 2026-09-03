"""
AI News Studio — Celery Application

Configures Celery with Redis broker, result backend,
task serialization, and retry policies.
"""

from celery import Celery

from app.core.config import settings

# Create Celery app
celery_app = Celery(
    "ai_news_studio",
    broker=settings.celery_broker_url,
    backend=settings.celery_result_backend,
    include=[
        "app.tasks.pipeline",
        "app.tasks.scheduled",
    ],
)

# Configuration
celery_app.conf.update(
    # Serialization
    task_serializer="json",
    accept_content=["json"],
    result_serializer="json",

    # Timezone
    timezone=settings.pipeline_timezone,
    enable_utc=True,

    # Task execution
    task_acks_late=True,
    task_reject_on_worker_lost=True,
    worker_prefetch_multiplier=1,
    worker_max_tasks_per_child=50,

    # Retry policy
    task_default_retry_delay=60,
    task_max_retries=3,

    # Results
    result_expires=86400,  # 24 hours

    # Task routing
    task_routes={
        "app.tasks.pipeline.run_full_pipeline": {"queue": "default"},
        "app.tasks.pipeline.run_batch_pipeline": {"queue": "default"},
        "app.tasks.pipeline.task_discover_news": {"queue": "discovery"},
        "app.tasks.pipeline.task_analyze_stories": {"queue": "analysis"},
        "app.tasks.pipeline.task_generate_script": {"queue": "production"},
        "app.tasks.pipeline.task_generate_visuals": {"queue": "production"},
        "app.tasks.pipeline.task_generate_narration": {"queue": "production"},
        "app.tasks.pipeline.task_compose_video": {"queue": "production"},
        "app.tasks.pipeline.task_generate_thumbnails": {"queue": "production"},
        "app.tasks.pipeline.task_optimize_seo": {"queue": "production"},
        "app.tasks.pipeline.task_upload_youtube": {"queue": "upload"},
        "app.tasks.pipeline.task_notify": {"queue": "default"},
    },
)

# Import scheduled module to register the beat_schedule immediately.
# This must happen after conf.update so it can override the schedule.
import app.tasks.scheduled  # noqa: F401, E402
