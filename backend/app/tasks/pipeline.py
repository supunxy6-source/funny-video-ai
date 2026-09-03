"""
AI News Studio — Pipeline Tasks

Celery tasks for each step of the video production pipeline.
The master pipeline chains Steps 1-10 with comprehensive error handling.
"""

import asyncio
import logging
import time
import uuid
from datetime import datetime, timezone, timedelta

from celery import chain, chord, group
from sqlalchemy import select, update

from app.tasks.celery_app import celery_app
from app.db.session import async_session_factory
from app.models.job import Job
from app.models.log import Log

logger = logging.getLogger(__name__)

# Pipeline step definitions
PIPELINE_STEPS = [
    ("discovery", 1),
    ("analysis", 2),
    ("scriptwriting", 3),
    ("visuals", 4),
    ("narration", 5),
    ("editing", 6),
    ("thumbnail", 7),
    ("seo", 8),
    ("upload", 9),
    ("notification", 10),
]


def _run_async(coro):
    """Helper to run async functions from sync Celery tasks safely."""
    import app.db.base
    import asyncio
    
    async def wrapped_coro():
        try:
            return await coro
        finally:
            # Dispose and reset the engine so the next task gets a fresh one.
            # Without resetting to None, get_engine() would return a disposed engine.
            if app.db.base._engine:
                await app.db.base._engine.dispose()
                app.db.base._engine = None
            # Also reset the session factory so it picks up the new engine.
            from app.db.session import reset_session_factory
            reset_session_factory()
                
    return asyncio.run(wrapped_coro())


async def _create_job(pipeline_run_id: str, step_name: str, step_order: int, task_id: str = None):
    """Create a job record in the database."""
    async with async_session_factory() as db:
        job = Job(
            pipeline_run_id=pipeline_run_id,
            step_name=step_name,
            step_order=step_order,
            status="running",
            celery_task_id=task_id,
            started_at=datetime.now(timezone.utc),
        )
        db.add(job)
        await db.commit()
        return job.id


async def _complete_job(job_id: int, status: str = "completed", error: str = None):
    """Update job status on completion."""
    async with async_session_factory() as db:
        job = await db.get(Job, job_id)
        if job:
            job.status = status
            job.completed_at = datetime.now(timezone.utc)
            if job.started_at:
                job.duration_seconds = (job.completed_at - job.started_at).total_seconds()
            if error:
                job.error_message = error
            await db.commit()


async def _log(pipeline_run_id: str, level: str, message: str, module: str = None, job_id: int = None):
    """Write a log entry."""
    async with async_session_factory() as db:
        log = Log(
            pipeline_run_id=pipeline_run_id,
            job_id=job_id,
            level=level,
            message=message,
            module=module,
            timestamp=datetime.now(timezone.utc),
        )
        db.add(log)
        await db.commit()


# ── Step 1: News Discovery ────────────────────────────
@celery_app.task(bind=True, name="app.tasks.pipeline.task_discover_news", max_retries=3)
def task_discover_news(self, pipeline_run_id: str):
    """Discover and collect news articles from all sources."""
    async def _execute():
        step = "discovery"
        job_id = await _create_job(pipeline_run_id, step, 1, self.request.id if self.request else None)
        try:
            await _log(pipeline_run_id, "INFO", "Starting news discovery", step, job_id)
            from app.services.discovery.collector import run_discovery
            articles = await run_discovery()
            await _complete_job(job_id, "completed")
            await _log(pipeline_run_id, "INFO", f"Discovery complete: {len(articles)} articles", step, job_id)
            return {"pipeline_run_id": pipeline_run_id, "articles_count": len(articles)}
        except Exception as exc:
            await _complete_job(job_id, "failed", str(exc))
            await _log(pipeline_run_id, "ERROR", f"Discovery failed: {exc}", step, job_id)
            raise exc

    try:
        return _run_async(_execute())
    except Exception as exc:
        raise self.retry(exc=exc, countdown=120)


# ── Step 2: AI Analysis ───────────────────────────────
@celery_app.task(bind=True, name="app.tasks.pipeline.task_analyze_stories", max_retries=3)
def task_analyze_stories(self, prev_result: dict):
    """Cluster, rank, and verify news stories."""
    pipeline_run_id = prev_result["pipeline_run_id"]

    async def _execute():
        step = "analysis"
        job_id = await _create_job(pipeline_run_id, step, 2, self.request.id if self.request else None)
        try:
            await _log(pipeline_run_id, "INFO", "Starting story analysis", step, job_id)

            from app.services.analysis.clusterer import run_clustering
            from app.services.analysis.ranker import rank_stories
            from app.services.analysis.verifier import verify_top_stories

            await run_clustering()
            ranked = await rank_stories()
            verified = await verify_top_stories(ranked)

            if not verified:
                await _complete_job(job_id, "completed")
                await _log(pipeline_run_id, "WARNING", "No verified stories found", step, job_id)
                return {"pipeline_run_id": pipeline_run_id, "story": None, "skip": True}

            top_story = verified[0]
            await _complete_job(job_id, "completed")
            await _log(pipeline_run_id, "INFO", f"Top story: {top_story.get('top_headline', '')[:80]}", step, job_id)

            return {"pipeline_run_id": pipeline_run_id, "story": top_story, "skip": False}
        except Exception as exc:
            await _complete_job(job_id, "failed", str(exc))
            await _log(pipeline_run_id, "ERROR", f"Analysis failed: {exc}", step, job_id)
            raise exc

    try:
        return _run_async(_execute())
    except Exception as exc:
        raise self.retry(exc=exc, countdown=120)


# ── Step 3: Script Writing ─────────────────────────────
@celery_app.task(bind=True, name="app.tasks.pipeline.task_generate_script", max_retries=3)
def task_generate_script(self, prev_result: dict):
    """Generate a professional news script."""
    pipeline_run_id = prev_result["pipeline_run_id"]
    if prev_result.get("skip"):
        return {**prev_result, "script_id": None}

    async def _execute():
        step = "scriptwriting"
        job_id = await _create_job(pipeline_run_id, step, 3, self.request.id if self.request else None)
        try:
            await _log(pipeline_run_id, "INFO", "Generating script", step, job_id)
            from app.services.scriptwriter.writer import generate_script_for_story
            script_id = await generate_script_for_story(prev_result["story"])
            await _complete_job(job_id, "completed")
            await _log(pipeline_run_id, "INFO", f"Script generated: ID={script_id}", step, job_id)
            return {"pipeline_run_id": pipeline_run_id, "script_id": script_id, "skip": False}
        except Exception as exc:
            await _complete_job(job_id, "failed", str(exc))
            raise exc

    try:
        return _run_async(_execute())
    except Exception as exc:
        raise self.retry(exc=exc, countdown=120)


# ── Step 4: Visual Generation ──────────────────────────
@celery_app.task(bind=True, name="app.tasks.pipeline.task_generate_visuals", max_retries=3)
def task_generate_visuals(self, prev_result: dict):
    """Generate visual assets for all scenes."""
    pipeline_run_id = prev_result["pipeline_run_id"]
    if prev_result.get("skip") or not prev_result.get("script_id"):
        return prev_result

    async def _execute():
        step = "visuals"
        job_id = await _create_job(pipeline_run_id, step, 4, self.request.id if self.request else None)
        try:
            await _log(pipeline_run_id, "INFO", "Generating dynamic scene visuals & video clips", step, job_id)
            from app.services.visuals.video_generator import generate_scene_visuals

            script_id = prev_result["script_id"]
            visuals = await generate_scene_visuals(script_id)
            await _complete_job(job_id, "completed")
            await _log(pipeline_run_id, "INFO", f"Generated {len(visuals)} dynamic scene video clips", step, job_id)
            return {**prev_result}
        except Exception as exc:
            await _complete_job(job_id, "failed", str(exc))
            raise exc

    try:
        return _run_async(_execute())
    except Exception as exc:
        raise self.retry(exc=exc, countdown=120)


# ── Step 5: Narration ─────────────────────────────────
@celery_app.task(bind=True, name="app.tasks.pipeline.task_generate_narration", max_retries=3)
def task_generate_narration(self, prev_result: dict):
    """Generate voice narration for all scenes."""
    pipeline_run_id = prev_result["pipeline_run_id"]
    if prev_result.get("skip") or not prev_result.get("script_id"):
        return prev_result

    async def _execute():
        step = "narration"
        job_id = await _create_job(pipeline_run_id, step, 5, self.request.id if self.request else None)
        try:
            await _log(pipeline_run_id, "INFO", "Generating narration", step, job_id)
            from app.services.voice.narrator import generate_narration
            audios = await generate_narration(prev_result["script_id"])
            await _complete_job(job_id, "completed")
            await _log(pipeline_run_id, "INFO", f"Generated {len(audios)} audio segments", step, job_id)
            return {**prev_result}
        except Exception as exc:
            await _complete_job(job_id, "failed", str(exc))
            raise exc

    try:
        return _run_async(_execute())
    except Exception as exc:
        raise self.retry(exc=exc, countdown=120)


# ── Step 6: Video Editing ──────────────────────────────
@celery_app.task(bind=True, name="app.tasks.pipeline.task_compose_video", max_retries=2)
def task_compose_video(self, prev_result: dict):
    """Compose the final video from all assets."""
    pipeline_run_id = prev_result["pipeline_run_id"]
    if prev_result.get("skip") or not prev_result.get("script_id"):
        return prev_result

    async def _execute():
        step = "editing"
        job_id = await _create_job(pipeline_run_id, step, 6, self.request.id if self.request else None)
        try:
            await _log(pipeline_run_id, "INFO", "Composing video", step, job_id)
            from app.services.editor.compositor import compose_video
            video_id = await compose_video(prev_result["script_id"])
            await _complete_job(job_id, "completed")
            await _log(pipeline_run_id, "INFO", f"Video composed: ID={video_id}", step, job_id)
            return {**prev_result, "video_id": video_id}
        except Exception as exc:
            await _complete_job(job_id, "failed", str(exc))
            raise exc

    try:
        return _run_async(_execute())
    except Exception as exc:
        raise self.retry(exc=exc, countdown=300)


# ── Step 7: Thumbnail ─────────────────────────────────
@celery_app.task(bind=True, name="app.tasks.pipeline.task_generate_thumbnails", max_retries=3)
def task_generate_thumbnails(self, prev_result: dict):
    """Generate and score thumbnail variants."""
    pipeline_run_id = prev_result["pipeline_run_id"]
    if prev_result.get("skip") or not prev_result.get("video_id"):
        return prev_result

    async def _execute():
        step = "thumbnail"
        job_id = await _create_job(pipeline_run_id, step, 7, self.request.id if self.request else None)
        try:
            await _log(pipeline_run_id, "INFO", "Generating thumbnails", step, job_id)
            from app.services.thumbnail.generator import generate_thumbnails
            thumb_id = await generate_thumbnails(prev_result["video_id"])
            await _complete_job(job_id, "completed")
            return {**prev_result, "thumbnail_id": thumb_id}
        except Exception as exc:
            await _complete_job(job_id, "failed", str(exc))
            raise exc

    try:
        return _run_async(_execute())
    except Exception as exc:
        raise self.retry(exc=exc, countdown=120)


# ── Step 8: SEO Optimization ──────────────────────────
@celery_app.task(bind=True, name="app.tasks.pipeline.task_optimize_seo", max_retries=3)
def task_optimize_seo(self, prev_result: dict):
    """Generate SEO-optimized metadata."""
    pipeline_run_id = prev_result["pipeline_run_id"]
    if prev_result.get("skip") or not prev_result.get("video_id"):
        return prev_result

    async def _execute():
        step = "seo"
        job_id = await _create_job(pipeline_run_id, step, 8, self.request.id if self.request else None)
        try:
            await _log(pipeline_run_id, "INFO", "Optimizing SEO", step, job_id)
            from app.services.seo.optimizer import optimize_seo
            upload_id = await optimize_seo(prev_result["video_id"])
            await _complete_job(job_id, "completed")
            return {**prev_result, "upload_id": upload_id}
        except Exception as exc:
            await _complete_job(job_id, "failed", str(exc))
            raise exc

    try:
        return _run_async(_execute())
    except Exception as exc:
        raise self.retry(exc=exc, countdown=120)


# ── Step 9: YouTube Upload ─────────────────────────────
@celery_app.task(bind=True, name="app.tasks.pipeline.task_upload_youtube", max_retries=2)
def task_upload_youtube(self, prev_result: dict):
    """Upload video to YouTube (if auto-publish enabled)."""
    pipeline_run_id = prev_result["pipeline_run_id"]
    if prev_result.get("skip") or not prev_result.get("upload_id"):
        return prev_result

    async def _execute():
        step = "upload"
        job_id = await _create_job(pipeline_run_id, step, 9, self.request.id if self.request else None)
        try:
            from app.core.config import settings
            if not getattr(settings, "youtube_auto_publish", True):
                await _log(pipeline_run_id, "INFO", "YouTube auto-publish disabled in settings — keeping video ready locally", step, job_id)
                await _complete_job(job_id, "completed")
                return {**prev_result, "youtube_video_id": None}

            await _log(pipeline_run_id, "INFO", "Uploading to YouTube (Nova Horizon)", step, job_id)
            from app.services.youtube.uploader import upload_to_youtube
            yt_id = await upload_to_youtube(prev_result["upload_id"])
            await _complete_job(job_id, "completed")
            await _log(pipeline_run_id, "INFO", f"YouTube upload complete: {yt_id}", step, job_id)
            return {**prev_result, "youtube_video_id": yt_id}
        except Exception as exc:
            await _complete_job(job_id, "failed", str(exc))
            raise exc

    try:
        return _run_async(_execute())
    except Exception as exc:
        raise self.retry(exc=exc, countdown=300)


# ── Step 9b: Facebook Upload ───────────────────────────
@celery_app.task(bind=True, name="app.tasks.pipeline.task_upload_facebook", max_retries=2)
def task_upload_facebook(self, prev_result: dict):
    """Upload video to Facebook Page (if auto-publish enabled)."""
    pipeline_run_id = prev_result["pipeline_run_id"]
    if prev_result.get("skip") or not prev_result.get("upload_id"):
        return prev_result

    async def _execute():
        step = "facebook_upload"
        job_id = await _create_job(pipeline_run_id, step, 9, self.request.id if self.request else None)
        try:
            from app.core.config import settings
            if not getattr(settings, "facebook_auto_publish", True):
                await _log(pipeline_run_id, "INFO", "Facebook auto-publish disabled in settings", step, job_id)
                await _complete_job(job_id, "completed")
                return {**prev_result, "facebook_video_id": None}

            fb_page_id = getattr(settings, "facebook_page_id", "")
            fb_token = getattr(settings, "facebook_page_access_token", "")
            if not fb_page_id or not fb_token:
                await _log(pipeline_run_id, "INFO", "Facebook credentials not configured — skipping", step, job_id)
                await _complete_job(job_id, "completed")
                return {**prev_result, "facebook_video_id": None}

            await _log(pipeline_run_id, "INFO", "Uploading to Facebook Page", step, job_id)
            from app.services.facebook.uploader import upload_to_facebook
            fb_id = await upload_to_facebook(prev_result["upload_id"])
            await _complete_job(job_id, "completed")
            await _log(pipeline_run_id, "INFO", f"Facebook upload complete: {fb_id}", step, job_id)
            return {**prev_result, "facebook_video_id": fb_id}
        except Exception as exc:
            await _complete_job(job_id, "failed", str(exc))
            await _log(pipeline_run_id, "WARNING", f"Facebook upload failed (non-blocking): {exc}", step, job_id)
            # Facebook failure is non-blocking — return prev_result so pipeline continues
            return {**prev_result, "facebook_video_id": None}

    try:
        return _run_async(_execute())
    except Exception as exc:
        # Even retries exhausted — don't block the pipeline
        logger.warning(f"Facebook upload task failed after retries: {exc}")
        return {**prev_result, "facebook_video_id": None}


# ── Step 10: Notification ──────────────────────────────
@celery_app.task(bind=True, name="app.tasks.pipeline.task_notify", max_retries=1)
def task_notify(self, prev_result: dict):
    """Send success/failure notifications."""
    pipeline_run_id = prev_result["pipeline_run_id"]

    async def _execute():
        step = "notification"
        job_id = await _create_job(pipeline_run_id, step, 10, self.request.id if self.request else None)
        try:
            from app.services.notifications.notifier import notifier

            if prev_result.get("skip"):
                await notifier.notify_failure(
                    step_name="analysis",
                    error_message="No verified stories found today",
                    pipeline_run_id=pipeline_run_id,
                )
            elif prev_result.get("youtube_video_id") or prev_result.get("facebook_video_id"):
                yt_id = prev_result.get("youtube_video_id")
                fb_id = prev_result.get("facebook_video_id")
                yt_url = (
                    f"https://youtube.com/watch?v={yt_id}"
                    if yt_id and not str(yt_id).startswith("local_")
                    else "Local Render (YouTube upload bypassed)"
                )
                fb_url = (
                    f"https://facebook.com/{fb_id}"
                    if fb_id
                    else None
                )
                await notifier.notify_success(
                    title=f"Video {yt_id or fb_id}",
                    youtube_url=yt_url,
                    duration=0,
                    processing_time=0,
                    facebook_url=fb_url,
                )
            await _complete_job(job_id, "completed")
        except Exception as exc:
            await _complete_job(job_id, "failed", str(exc))
            logger.error(f"Notification failed: {exc}")
            raise exc

    try:
        _run_async(_execute())
        return prev_result
    except Exception as exc:
        raise self.retry(exc=exc, countdown=60)


# ── Single Story Production Helper ───────────────────────
async def produce_single_story_pipeline(story: dict, pipeline_run_id: str, story_index: int = 1, total_stories: int = 1, scheduled_at: datetime = None) -> dict:
    """
    Produce a complete news video for a single verified story:
    1. Generate Script
    2. Generate Visual Scenes
    3. Generate Voice Narration
    4. Compose Video (vertical Shorts)
    5. Generate Thumbnails
    6. Generate SEO metadata
    7. Publish to YouTube (if enabled)
    8. Send Notification
    """
    from app.core.config import settings
    from app.services.scriptwriter.writer import generate_script_for_story
    from app.services.visuals.video_generator import generate_scene_visuals
    from app.services.voice.narrator import generate_narration
    from app.services.editor.compositor import compose_video
    from app.services.thumbnail.generator import generate_thumbnails
    from app.services.seo.optimizer import optimize_seo
    from app.services.youtube.uploader import upload_to_youtube
    from app.services.notifications.notifier import notifier

    headline = story.get("top_headline", "")[:60]
    await _log(pipeline_run_id, "INFO", f"🎬 [{story_index}/{total_stories}] Starting video production: '{headline}'", "pipeline")

    # Step 3: Scriptwriting
    job_id = await _create_job(pipeline_run_id, f"scriptwriting_{story_index}", 3)
    try:
        script_id = await generate_script_for_story(story)
        await _complete_job(job_id, "completed")
        await _log(pipeline_run_id, "INFO", f"[{story_index}/{total_stories}] Script generated: ID={script_id}", "scriptwriting", job_id)
    except Exception as exc:
        await _complete_job(job_id, "failed", str(exc))
        await _log(pipeline_run_id, "ERROR", f"[{story_index}/{total_stories}] Scriptwriting failed: {exc}", "scriptwriting", job_id)
        raise exc

    # Step 4: Visuals
    job_id = await _create_job(pipeline_run_id, f"visuals_{story_index}", 4)
    try:
        visuals = await generate_scene_visuals(script_id)
        await _complete_job(job_id, "completed")
        await _log(pipeline_run_id, "INFO", f"[{story_index}/{total_stories}] Generated {len(visuals)} scene visuals", "visuals", job_id)
    except Exception as exc:
        await _complete_job(job_id, "failed", str(exc))
        await _log(pipeline_run_id, "ERROR", f"[{story_index}/{total_stories}] Visual generation failed: {exc}", "visuals", job_id)
        raise exc

    # Step 5: Narration
    job_id = await _create_job(pipeline_run_id, f"narration_{story_index}", 5)
    try:
        audios = await generate_narration(script_id)
        await _complete_job(job_id, "completed")
        await _log(pipeline_run_id, "INFO", f"[{story_index}/{total_stories}] Generated {len(audios)} narration clips", "narration", job_id)
    except Exception as exc:
        await _complete_job(job_id, "failed", str(exc))
        await _log(pipeline_run_id, "ERROR", f"[{story_index}/{total_stories}] Narration failed: {exc}", "narration", job_id)
        raise exc

    # Step 6: Video Composition
    job_id = await _create_job(pipeline_run_id, f"editing_{story_index}", 6)
    try:
        video_id = await compose_video(script_id)
        await _complete_job(job_id, "completed")
        await _log(pipeline_run_id, "INFO", f"[{story_index}/{total_stories}] Video composed: ID={video_id}", "editing", job_id)
    except Exception as exc:
        await _complete_job(job_id, "failed", str(exc))
        await _log(pipeline_run_id, "ERROR", f"[{story_index}/{total_stories}] Video composition failed: {exc}", "editing", job_id)
        raise exc

    # Step 7: Thumbnails
    job_id = await _create_job(pipeline_run_id, f"thumbnail_{story_index}", 7)
    try:
        thumb_id = await generate_thumbnails(video_id)
        await _complete_job(job_id, "completed")
        await _log(pipeline_run_id, "INFO", f"[{story_index}/{total_stories}] Thumbnail generated: ID={thumb_id}", "thumbnail", job_id)
    except Exception as exc:
        await _complete_job(job_id, "failed", str(exc))
        await _log(pipeline_run_id, "ERROR", f"[{story_index}/{total_stories}] Thumbnail generation failed: {exc}", "thumbnail", job_id)
        thumb_id = None

    # Step 8: SEO Optimization
    job_id = await _create_job(pipeline_run_id, f"seo_{story_index}", 8)
    try:
        upload_id = await optimize_seo(video_id, scheduled_at=scheduled_at)
        await _complete_job(job_id, "completed")
        await _log(pipeline_run_id, "INFO", f"[{story_index}/{total_stories}] SEO metadata optimized: ID={upload_id}", "seo", job_id)
    except Exception as exc:
        await _complete_job(job_id, "failed", str(exc))
        await _log(pipeline_run_id, "ERROR", f"[{story_index}/{total_stories}] SEO optimization failed: {exc}", "seo", job_id)
        raise exc

    # Step 9: YouTube Upload
    yt_id = None
    if getattr(settings, "youtube_auto_publish", True) and upload_id:
        job_id = await _create_job(pipeline_run_id, f"upload_{story_index}", 9)
        try:
            await _log(pipeline_run_id, "INFO", f"[{story_index}/{total_stories}] Uploading to YouTube channel 'Nova Horizon'", "upload", job_id)
            yt_id = await upload_to_youtube(upload_id)
            await _complete_job(job_id, "completed")
            await _log(pipeline_run_id, "INFO", f"[{story_index}/{total_stories}] 🎉 Published to YouTube: https://youtube.com/watch?v={yt_id}", "upload", job_id)
        except Exception as exc:
            await _complete_job(job_id, "failed", str(exc))
            await _log(pipeline_run_id, "WARNING", f"[{story_index}/{total_stories}] YouTube upload failed: {exc}", "upload", job_id)

    # Step 9b: Facebook Upload (independent of YouTube)
    fb_id = None
    if getattr(settings, "facebook_auto_publish", True) and upload_id:
        fb_page_id = getattr(settings, "facebook_page_id", "")
        fb_token = getattr(settings, "facebook_page_access_token", "")
        if fb_page_id and fb_token:
            job_id = await _create_job(pipeline_run_id, f"facebook_upload_{story_index}", 9)
            try:
                await _log(pipeline_run_id, "INFO", f"[{story_index}/{total_stories}] Uploading to Facebook Page", "facebook_upload", job_id)
                from app.services.facebook.uploader import upload_to_facebook
                fb_id = await upload_to_facebook(upload_id)
                await _complete_job(job_id, "completed")
                await _log(pipeline_run_id, "INFO", f"[{story_index}/{total_stories}] 🎉 Published to Facebook: https://facebook.com/{fb_id}", "facebook_upload", job_id)
            except Exception as exc:
                await _complete_job(job_id, "completed", error=f"Facebook upload warning: {exc}")
                await _log(pipeline_run_id, "WARNING", f"[{story_index}/{total_stories}] Facebook upload failed (non-blocking): {exc}", "facebook_upload", job_id)


    # Step 10: Notification
    job_id = await _create_job(pipeline_run_id, f"notification_{story_index}", 10)
    try:
        yt_url = f"https://youtube.com/watch?v={yt_id}" if yt_id and not str(yt_id).startswith("local_") else "Local Video Rendered"
        fb_url = f"https://facebook.com/{fb_id}" if fb_id else None
        await notifier.notify_success(
            title=f"Video #{video_id} ({headline})",
            youtube_url=yt_url,
            duration=0,
            processing_time=0,
            facebook_url=fb_url,
        )
        await _complete_job(job_id, "completed")
    except Exception as notif_err:
        logger.warning(f"Notification warning: {notif_err}")
        await _complete_job(job_id, "completed", error=str(notif_err))

    return {
        "story_index": story_index,
        "script_id": script_id,
        "video_id": video_id,
        "upload_id": upload_id,
        "youtube_video_id": yt_id,
        "facebook_video_id": fb_id,
        "status": "completed",
    }


# ── Batch Video Pipeline Task ───────────────────────────
@celery_app.task(name="app.tasks.pipeline.run_batch_pipeline")
def run_batch_pipeline(video_count: int = None, pipeline_run_id: str = None):
    """
    Execute batch video production to generate 3 to 5 videos per run from top verified stories.
    Discovers news, clusters & verifies stories, and produces N distinct videos.
    """
    from app.core.config import settings
    count = video_count or getattr(settings, "daily_video_count", 3)
    count = max(1, min(int(count), 5))  # Clamp between 1 and 5 videos

    pipeline_run_id = pipeline_run_id or f"batch_{uuid.uuid4().hex[:10]}"
    logger.info(f"🚀 Starting batch pipeline ({count} videos target): {pipeline_run_id}")

    async def _execute_batch():
        # 1. Discovery
        job_id = await _create_job(pipeline_run_id, "discovery", 1)
        try:
            await _log(pipeline_run_id, "INFO", f"Starting news discovery for {count} videos batch", "discovery", job_id)
            from app.services.discovery.collector import run_discovery
            articles = await run_discovery()
            await _complete_job(job_id, "completed")
            await _log(pipeline_run_id, "INFO", f"Discovery finished: {len(articles)} articles collected", "discovery", job_id)
        except Exception as exc:
            await _complete_job(job_id, "failed", str(exc))
            await _log(pipeline_run_id, "ERROR", f"Discovery failed: {exc}", "discovery", job_id)
            raise exc

        # 2. Analysis & Story Ranking
        job_id = await _create_job(pipeline_run_id, "analysis", 2)
        try:
            await _log(pipeline_run_id, "INFO", "Clustering and ranking top news stories", "analysis", job_id)
            from app.services.analysis.clusterer import run_clustering
            from app.services.analysis.ranker import rank_stories
            from app.services.analysis.verifier import verify_top_stories

            await run_clustering()
            ranked = await rank_stories()
            verified = await verify_top_stories(ranked)

            if not verified:
                await _complete_job(job_id, "completed")
                await _log(pipeline_run_id, "WARNING", "No verified stories found today", "analysis", job_id)
                job_id_notif = await _create_job(pipeline_run_id, "notification", 10)
                await _complete_job(job_id_notif, "completed")
                return {"pipeline_run_id": pipeline_run_id, "videos_created": 0, "results": []}

            # Select top N verified stories
            selected_stories = verified[:count]
            await _complete_job(job_id, "completed")
            await _log(pipeline_run_id, "INFO", f"Selected {len(selected_stories)} verified top stories for video generation", "analysis", job_id)
        except Exception as exc:
            await _complete_job(job_id, "failed", str(exc))
            await _log(pipeline_run_id, "ERROR", f"Analysis failed: {exc}", "analysis", job_id)
            raise exc

        # 3. Produce video for each story
        results = []
        for i, story in enumerate(selected_stories, 1):
            try:
                # Schedule staggered uploads
                if i == 1:
                    scheduled_at = None
                else:
                    stagger_hours = getattr(settings, "stagger_uploads_hours", 1)
                    scheduled_at = datetime.now(timezone.utc) + timedelta(hours=stagger_hours * (i - 1))
                
                res = await produce_single_story_pipeline(
                    story, 
                    pipeline_run_id, 
                    story_index=i, 
                    total_stories=len(selected_stories),
                    scheduled_at=scheduled_at
                )
                results.append(res)
            except Exception as e:
                logger.error(f"Error producing video {i}/{len(selected_stories)}: {e}")
                results.append({"story_index": i, "status": "failed", "error": str(e)})

        # Mark batch completion job
        job_id = await _create_job(pipeline_run_id, "batch_completion", 100)
        await _complete_job(job_id, "completed")

        await _log(pipeline_run_id, "INFO", f"🎉 Batch pipeline completed: {len([r for r in results if r.get('status') == 'completed'])}/{len(selected_stories)} videos produced", "pipeline")
        return {"pipeline_run_id": pipeline_run_id, "videos_created": len(results), "results": results}

    return _run_async(_execute_batch())


# ── Master Pipeline ────────────────────────────────────
@celery_app.task(name="app.tasks.pipeline.run_full_pipeline")
def run_full_pipeline(video_count: int = None, pipeline_run_id: str = None):
    """
    Execute the video production pipeline.
    If daily_video_count >= 2 or video_count is specified, delegates to run_batch_pipeline.
    Otherwise runs the 10-step sequential pipeline chain.
    """
    from app.core.config import settings
    target_count = video_count or getattr(settings, "daily_video_count", 3)

    if target_count > 1:
        # Run batch pipeline for 3 to 5 videos
        pipeline_run_id = pipeline_run_id or f"batch_{uuid.uuid4().hex[:10]}"
        run_batch_pipeline.delay(video_count=target_count, pipeline_run_id=pipeline_run_id)
        return pipeline_run_id

    pipeline_run_id = pipeline_run_id or f"run_{uuid.uuid4().hex[:12]}"
    logger.info(f"🚀 Starting single-video pipeline: {pipeline_run_id}")

    pipeline = chain(
        task_discover_news.s(pipeline_run_id),
        task_analyze_stories.s(),
        task_generate_script.s(),
        task_generate_visuals.s(),
        task_generate_narration.s(),
        task_compose_video.s(),
        task_generate_thumbnails.s(),
        task_optimize_seo.s(),
        task_upload_youtube.s(),
        task_upload_facebook.s(),
        task_notify.s(),
    )

    pipeline.apply_async()
    return pipeline_run_id

