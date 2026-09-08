"""
Stateside Smiles — TikTok Video Uploader

Handles video upload to TikTok via the Content Posting API v2.
Supports both Direct Post and Upload to Inbox (drafts) modes.

Upload flow:
1. Init  — POST /v2/post/publish/video/init/ → get upload_url + publish_id
2. Upload — PUT video binary to upload_url (chunked for large files)
3. Check  — Poll /v2/post/publish/status/fetch/ until published
"""

import json
import logging
import os
import time
from datetime import datetime, timezone
from pathlib import Path
from typing import Optional

import requests

from app.services.tiktok.auth import get_tiktok_credentials, get_tiktok_user_info

logger = logging.getLogger(__name__)

# TikTok Content Posting API endpoints
TIKTOK_API_BASE = "https://open.tiktokapis.com/v2"
INIT_VIDEO_URL = f"{TIKTOK_API_BASE}/post/publish/video/init/"
INBOX_VIDEO_URL = f"{TIKTOK_API_BASE}/post/publish/inbox/video/init/"
PUBLISH_STATUS_URL = f"{TIKTOK_API_BASE}/post/publish/status/fetch/"
CREATOR_INFO_URL = f"{TIKTOK_API_BASE}/post/publish/creator_info/query/"

# Retry / polling configuration
MAX_UPLOAD_RETRIES = 3
RETRY_DELAY_SECONDS = 30
PUBLISH_POLL_INTERVAL = 5  # seconds
PUBLISH_POLL_MAX_ATTEMPTS = 60  # 5 min max wait

# TikTok chunk size constraints (5MB min, 64MB max per chunk)
MIN_CHUNK_SIZE = 5 * 1024 * 1024  # 5 MB
MAX_CHUNK_SIZE = 64 * 1024 * 1024  # 64 MB
# Files under 64MB can be uploaded in a single PUT
SINGLE_UPLOAD_MAX = 64 * 1024 * 1024


class TikTokUploader:
    """Uploads videos to TikTok via the Content Posting API v2."""

    def __init__(self, post_mode: str = "direct"):
        """
        Args:
            post_mode: 'direct' for immediate publish, 'inbox' for creator review.
        """
        creds = get_tiktok_credentials()
        self.access_token = creds["access_token"]
        self.open_id = creds.get("open_id", "")
        self.post_mode = post_mode

    def _headers(self) -> dict:
        """Standard authorization headers for TikTok API."""
        return {
            "Authorization": f"Bearer {self.access_token}",
            "Content-Type": "application/json; charset=UTF-8",
        }

    def _check_creator_info(self) -> dict:
        """
        Query creator info to verify the account supports direct posting.
        Returns creator capabilities and privacy level options.
        """
        response = requests.post(
            CREATOR_INFO_URL,
            headers=self._headers(),
            timeout=15,
        )
        result = response.json()

        if result.get("error", {}).get("code") != "ok":
            error_msg = result.get("error", {}).get("message", "Unknown error")
            logger.warning(f"TikTok creator info check: {error_msg}")

        return result.get("data", {})

    def upload_video(
        self,
        file_path: str,
        title: str,
        description: str = "",
        hashtags: str = "",
    ) -> str:
        """
        Upload a video to TikTok.

        TikTok uses the video description as the post caption.
        Title and hashtags are appended to form the caption.

        Returns the TikTok publish_id.
        """
        video_path = Path(file_path)
        if not video_path.exists():
            raise FileNotFoundError(f"Video file not found: {file_path}")

        file_size = video_path.stat().st_size

        # Build the TikTok caption (title + description + hashtags)
        caption = self._build_caption(title, description, hashtags)

        logger.info(
            f"📤 Starting TikTok upload ({self.post_mode}): "
            f"'{title[:50]}' ({file_size / 1024 / 1024:.1f} MB)"
        )

        # ── Phase 1: Initialize Upload ──────────────────────
        init_url = INBOX_VIDEO_URL if self.post_mode == "inbox" else INIT_VIDEO_URL

        init_body = {
            "post_info": {
                "title": caption[:2200],  # TikTok caption limit
                "privacy_level": "SELF_ONLY",  # Default to private; TikTok may override based on account
                "disable_duet": False,
                "disable_comment": False,
                "disable_stitch": False,
            },
            "source_info": {
                "source": "FILE_UPLOAD",
                "video_size": file_size,
                "chunk_size": min(file_size, MAX_CHUNK_SIZE),
                "total_chunk_count": self._calculate_chunk_count(file_size),
            },
        }

        init_response = self._request_with_retry(
            "POST", init_url, json_data=init_body, phase="init"
        )

        publish_id = init_response.get("data", {}).get("publish_id", "")
        upload_url = init_response.get("data", {}).get("upload_url", "")

        if not upload_url:
            raise RuntimeError(f"TikTok upload init failed: {init_response}")

        logger.info(f"📤 TikTok upload session created: {publish_id}")

        # ── Phase 2: Upload Video Binary ────────────────────
        self._upload_video_file(video_path, upload_url, file_size)

        logger.info("📤 TikTok video upload complete, waiting for processing...")

        # ── Phase 3: Poll Publish Status ────────────────────
        if self.post_mode == "inbox":
            logger.info(
                f"📥 Video sent to TikTok inbox for creator review. "
                f"Publish ID: {publish_id}"
            )
            return publish_id

        final_status = self._poll_publish_status(publish_id)
        logger.info(f"✅ TikTok video published! Publish ID: {publish_id}")

        return publish_id

    def _build_caption(self, title: str, description: str, hashtags: str) -> str:
        """
        Build TikTok caption from title + hashtags.
        TikTok doesn't have separate title/description fields — everything is the caption.
        """
        parts = []
        if title:
            parts.append(title.strip())
        if description and description.strip() != title.strip():
            # Only add description if it differs from title
            desc_short = description.strip()[:500]
            parts.append(desc_short)
        if hashtags:
            parts.append(hashtags.strip())

        caption = "\n\n".join(parts)
        return caption[:2200]  # TikTok max caption length

    def _calculate_chunk_count(self, file_size: int) -> int:
        """Calculate the number of chunks for upload."""
        if file_size <= SINGLE_UPLOAD_MAX:
            return 1
        chunk_size = MAX_CHUNK_SIZE
        return (file_size + chunk_size - 1) // chunk_size

    def _upload_video_file(self, video_path: Path, upload_url: str, file_size: int) -> None:
        """Upload the video binary to TikTok's upload URL."""
        if file_size <= SINGLE_UPLOAD_MAX:
            # Single-part upload
            self._upload_single(video_path, upload_url, file_size)
        else:
            # Chunked upload
            self._upload_chunked(video_path, upload_url, file_size)

    def _upload_single(self, video_path: Path, upload_url: str, file_size: int) -> None:
        """Upload entire video in a single PUT request."""
        with open(video_path, "rb") as f:
            video_data = f.read()

        headers = {
            "Content-Range": f"bytes 0-{file_size - 1}/{file_size}",
            "Content-Type": "video/mp4",
        }

        for attempt in range(1, MAX_UPLOAD_RETRIES + 1):
            try:
                response = requests.put(
                    upload_url,
                    headers=headers,
                    data=video_data,
                    timeout=300,
                )
                if response.status_code in (200, 201):
                    logger.info("📤 TikTok single-part upload complete")
                    return
                raise RuntimeError(
                    f"TikTok upload returned status {response.status_code}: {response.text[:200]}"
                )
            except (requests.exceptions.RequestException, RuntimeError) as e:
                if attempt >= MAX_UPLOAD_RETRIES:
                    raise RuntimeError(
                        f"TikTok upload failed after {MAX_UPLOAD_RETRIES} retries: {e}"
                    )
                logger.warning(
                    f"TikTok upload error (attempt {attempt}/{MAX_UPLOAD_RETRIES}): {e}"
                )
                time.sleep(RETRY_DELAY_SECONDS * attempt)

    def _upload_chunked(self, video_path: Path, upload_url: str, file_size: int) -> None:
        """Upload video in multiple chunks."""
        chunk_size = MAX_CHUNK_SIZE
        chunk_count = 0

        with open(video_path, "rb") as f:
            offset = 0
            while offset < file_size:
                chunk_data = f.read(chunk_size)
                actual_chunk_size = len(chunk_data)
                chunk_count += 1
                end_byte = offset + actual_chunk_size - 1

                progress = int((offset / file_size) * 100)
                logger.info(f"📤 TikTok upload chunk #{chunk_count}: {progress}%")

                headers = {
                    "Content-Range": f"bytes {offset}-{end_byte}/{file_size}",
                    "Content-Type": "video/mp4",
                }

                for attempt in range(1, MAX_UPLOAD_RETRIES + 1):
                    try:
                        response = requests.put(
                            upload_url,
                            headers=headers,
                            data=chunk_data,
                            timeout=120,
                        )
                        if response.status_code in (200, 201, 206):
                            break
                        raise RuntimeError(
                            f"Chunk upload status {response.status_code}: {response.text[:200]}"
                        )
                    except (requests.exceptions.RequestException, RuntimeError) as e:
                        if attempt >= MAX_UPLOAD_RETRIES:
                            raise RuntimeError(
                                f"TikTok chunk upload failed after {MAX_UPLOAD_RETRIES} retries: {e}"
                            )
                        logger.warning(f"Chunk upload error (attempt {attempt}): {e}")
                        time.sleep(RETRY_DELAY_SECONDS * attempt)

                offset += actual_chunk_size

        logger.info(f"📤 TikTok chunked upload complete ({chunk_count} chunks)")

    def _poll_publish_status(self, publish_id: str) -> dict:
        """
        Poll TikTok for the publish status until the video is processed.
        Returns the final status response.
        """
        for attempt in range(1, PUBLISH_POLL_MAX_ATTEMPTS + 1):
            time.sleep(PUBLISH_POLL_INTERVAL)

            try:
                response = requests.post(
                    PUBLISH_STATUS_URL,
                    headers=self._headers(),
                    json={"publish_id": publish_id},
                    timeout=15,
                )
                result = response.json()

                status = result.get("data", {}).get("status", "PROCESSING_UPLOAD")

                if status == "PUBLISH_COMPLETE":
                    logger.info(f"✅ TikTok publish complete for {publish_id}")
                    return result

                if status in ("FAILED", "PUBLISH_CANCELLED"):
                    fail_reason = result.get("data", {}).get("fail_reason", "Unknown")
                    raise RuntimeError(
                        f"TikTok publish failed (status={status}): {fail_reason}"
                    )

                # Still processing
                if attempt % 6 == 0:  # Log every 30 seconds
                    logger.info(
                        f"📤 TikTok processing... ({attempt * PUBLISH_POLL_INTERVAL}s elapsed, "
                        f"status={status})"
                    )

            except requests.exceptions.RequestException as e:
                logger.warning(f"TikTok status poll error: {e}")

        # Timeout — treat as success since the upload itself completed
        logger.warning(
            f"TikTok publish status polling timed out after "
            f"{PUBLISH_POLL_MAX_ATTEMPTS * PUBLISH_POLL_INTERVAL}s. "
            f"Video was uploaded; it may still be processing."
        )
        return {"data": {"status": "PROCESSING_UPLOAD", "publish_id": publish_id}}

    def _request_with_retry(
        self,
        method: str,
        url: str,
        json_data: dict = None,
        phase: str = "",
    ) -> dict:
        """Execute an HTTP request with retry logic."""
        for attempt in range(1, MAX_UPLOAD_RETRIES + 1):
            try:
                response = requests.request(
                    method,
                    url,
                    headers=self._headers(),
                    json=json_data,
                    timeout=30,
                )
                result = response.json()

                error = result.get("error", {})
                if error and error.get("code") != "ok":
                    error_msg = error.get("message", str(error))
                    error_code = error.get("code", "unknown")
                    raise RuntimeError(
                        f"TikTok API error (code={error_code}): {error_msg}"
                    )

                return result

            except (requests.exceptions.RequestException, RuntimeError) as e:
                if attempt >= MAX_UPLOAD_RETRIES:
                    raise RuntimeError(
                        f"TikTok {phase} failed after {MAX_UPLOAD_RETRIES} retries: {e}"
                    )
                logger.warning(
                    f"TikTok {phase} error (attempt {attempt}/{MAX_UPLOAD_RETRIES}): {e}"
                )
                time.sleep(RETRY_DELAY_SECONDS * attempt)

        raise RuntimeError(f"TikTok {phase} failed unexpectedly")


def get_tiktok_account_info() -> dict:
    """
    Fetch TikTok account information using the configured credentials.
    Returns account name, follower count, and connection status.
    Used by the settings dashboard sidebar.
    """
    return get_tiktok_user_info()


async def upload_to_tiktok(upload_id: int) -> str:
    """
    Main upload entry point called by Celery task.
    Uploads video to TikTok via the Content Posting API.

    Returns the TikTok publish_id.
    """
    from sqlalchemy import select
    from app.core.config import settings
    from app.db.session import async_session_factory
    from app.models.upload import Upload
    from app.models.video import Video

    async with async_session_factory() as db:
        upload = await db.get(Upload, upload_id)
        if not upload:
            raise ValueError(f"Upload record {upload_id} not found")

        video = await db.get(Video, upload.video_id)
        if not video:
            raise ValueError(f"Video {upload.video_id} not found")

        try:
            post_mode = getattr(settings, "tiktok_post_mode", "direct")
            uploader = TikTokUploader(post_mode=post_mode)

            # Build description for TikTok caption
            description = upload.description or ""
            hashtags = upload.hashtags or ""

            tt_publish_id = uploader.upload_video(
                file_path=video.file_path,
                title=upload.title,
                description=description,
                hashtags=hashtags,
            )

            upload.tiktok_video_id = tt_publish_id
            await db.commit()

            logger.info(
                f"🎉 Video published to TikTok! "
                f"Publish ID: {tt_publish_id}"
            )

            return tt_publish_id

        except (ValueError, FileNotFoundError) as config_err:
            error_msg = str(config_err)
            logger.error(
                f"❌ TikTok configuration error — upload cannot proceed: {error_msg}"
            )
            raise

        except Exception as e:
            logger.warning(f"⚠️ TikTok upload failed: {e}")
            raise
