"""
Stateside Smiles — Facebook Page Uploader

Handles video upload to Facebook Pages via the Meta Graph Video API.
Supports resumable chunked upload for large video files.
"""

import json
import logging
import os
import time
import uuid
from datetime import datetime, timezone
from pathlib import Path
from typing import Optional

import requests

logger = logging.getLogger(__name__)

# Retry configuration
MAX_UPLOAD_RETRIES = 3
RETRY_DELAY_SECONDS = 30


class FacebookUploader:
    """Uploads videos to a Facebook Page via the Meta Graph Video API."""

    def __init__(
        self,
        page_id: Optional[str] = None,
        access_token: Optional[str] = None,
        api_version: str = "v20.0",
    ):
        from app.core.config import settings

        self.page_id = page_id or getattr(settings, "facebook_page_id", "") or os.getenv("FACEBOOK_PAGE_ID", "")
        self.access_token = (
            access_token
            or getattr(settings, "facebook_page_access_token", "")
            or os.getenv("FACEBOOK_PAGE_ACCESS_TOKEN", "")
        )
        self.api_version = api_version
        # Meta uses a separate host for video payloads
        self.base_url = f"https://graph-video.facebook.com/{self.api_version}"
        self.graph_url = f"https://graph.facebook.com/{self.api_version}"

    def _validate_credentials(self) -> None:
        """Raise if credentials are missing."""
        if not self.page_id:
            raise ValueError(
                "FACEBOOK_PAGE_ID is not configured. "
                "Set it in .env or pass it to FacebookUploader()."
            )
        if not self.access_token:
            raise ValueError(
                "FACEBOOK_PAGE_ACCESS_TOKEN is not configured. "
                "Set it in .env or pass it to FacebookUploader()."
            )

    def _get_effective_page_token(self) -> str:
        """
        Ensure we use a valid Page Access Token.
        If the provided token is a User Access Token, automatically resolve
        the Page Access Token for self.page_id via /me/accounts.
        """
        token = self.access_token
        try:
            accounts_url = f"{self.graph_url}/me/accounts?access_token={token}&fields=id,access_token"
            res = requests.get(accounts_url, timeout=10).json()
            for account in res.get("data", []):
                if str(account.get("id")) == str(self.page_id):
                    page_token = account.get("access_token")
                    if page_token:
                        logger.info(f"🔑 Auto-resolved Page Access Token for Page ID {self.page_id}")
                        self.access_token = page_token
                        return page_token
        except Exception as e:
            logger.debug(f"Page token auto-resolution skipped: {e}")
        return token

    def upload_video(
        self,
        file_path: str,
        title: str,
        description: str,
        published: bool = True,
        scheduled_publish_time: Optional[int] = None,
    ) -> str:
        """
        Upload a video to the Facebook Page using resumable chunked upload.

        Three-phase protocol:
        1. Start  — reserve session, get upload_session_id
        2. Transfer — stream binary chunks
        3. Finish — publish with title/description

        Returns the Facebook video ID.
        """
        self._validate_credentials()
        effective_token = self._get_effective_page_token()

        video_path = Path(file_path)
        if not video_path.exists():
            raise FileNotFoundError(f"Video file not found: {file_path}")

        file_size = video_path.stat().st_size
        endpoint = f"{self.base_url}/{self.page_id}/videos"

        logger.info(f"📤 Starting Facebook upload: '{title}' ({file_size / 1024 / 1024:.1f} MB)")

        # ── Phase 1: Start ──────────────────────────────────
        init_response = self._request_with_retry(
            "POST",
            endpoint,
            data={
                "access_token": effective_token,
                "upload_phase": "start",
                "file_size": file_size,
            },
            phase="start",
        )


        if "upload_session_id" not in init_response:
            raise RuntimeError(f"Facebook upload init failed: {init_response}")

        session_id = init_response["upload_session_id"]
        start_offset = int(init_response["start_offset"])
        end_offset = int(init_response["end_offset"])

        logger.info(f"📤 Facebook upload session created: {session_id}")

        # ── Phase 2: Transfer ───────────────────────────────
        with open(file_path, "rb") as f:
            chunk_count = 0
            while start_offset < file_size:
                f.seek(start_offset)
                chunk_len = end_offset - start_offset
                chunk_data = f.read(chunk_len)
                chunk_count += 1

                progress = int((start_offset / file_size) * 100)
                logger.info(f"📤 Facebook upload chunk #{chunk_count}: {progress}%")

                transfer_response = self._request_with_retry(
                    "POST",
                    endpoint,
                    data={
                        "access_token": self.access_token,
                        "upload_phase": "transfer",
                        "upload_session_id": session_id,
                        "start_offset": start_offset,
                    },
                    files={"video_file_chunk": chunk_data},
                    phase="transfer",
                )

                start_offset = int(transfer_response["start_offset"])
                end_offset = int(transfer_response["end_offset"])

        logger.info("📤 Facebook upload transfer complete, finalizing...")

        # ── Phase 3: Finish ─────────────────────────────────
        finish_payload = {
            "access_token": self.access_token,
            "upload_phase": "finish",
            "upload_session_id": session_id,
            "title": title[:255],  # Facebook title limit
            "description": description,
            "published": str(published).lower(),
        }

        if scheduled_publish_time:
            finish_payload["scheduled_publish_time"] = str(scheduled_publish_time)
            finish_payload["published"] = "false"

        finish_response = self._request_with_retry(
            "POST", endpoint, data=finish_payload, phase="finish"
        )

        if not finish_response.get("success", False) and "id" not in finish_response:
            raise RuntimeError(f"Facebook upload finish failed: {finish_response}")

        video_id = finish_response.get("id") or init_response.get("video_id")
        logger.info(f"✅ Facebook video uploaded! ID: {video_id}")
        return video_id

    def _request_with_retry(
        self,
        method: str,
        url: str,
        data: dict = None,
        files: dict = None,
        phase: str = "",
    ) -> dict:
        """Execute an HTTP request with retry logic."""
        for attempt in range(1, MAX_UPLOAD_RETRIES + 1):
            try:
                response = requests.request(
                    method,
                    url,
                    data=data,
                    files=files,
                    timeout=120 if phase == "transfer" else 30,
                )
                result = response.json()

                if "error" in result:
                    error_msg = result["error"].get("message", str(result["error"]))
                    error_code = result["error"].get("code", "unknown")
                    raise RuntimeError(
                        f"Facebook API error (code={error_code}): {error_msg}"
                    )

                return result

            except (requests.exceptions.RequestException, RuntimeError) as e:
                if attempt >= MAX_UPLOAD_RETRIES:
                    raise RuntimeError(
                        f"Facebook upload {phase} failed after {MAX_UPLOAD_RETRIES} retries: {e}"
                    )
                logger.warning(
                    f"Facebook upload {phase} error (attempt {attempt}/{MAX_UPLOAD_RETRIES}): {e}"
                )
                time.sleep(RETRY_DELAY_SECONDS * attempt)

        # Should never reach here
        raise RuntimeError(f"Facebook upload {phase} failed unexpectedly")


def get_facebook_page_info() -> dict:
    """
    Fetch Facebook Page information using the configured credentials.
    Returns page name, ID, follower count, and connection status.
    """
    from app.core.config import settings

    page_id = getattr(settings, "facebook_page_id", "") or os.getenv("FACEBOOK_PAGE_ID", "")
    access_token = (
        getattr(settings, "facebook_page_access_token", "")
        or os.getenv("FACEBOOK_PAGE_ACCESS_TOKEN", "")
    )

    if not page_id or not access_token:
        return {"connected": False, "error": "Facebook credentials not configured"}

    try:
        url = (
            f"https://graph.facebook.com/v20.0/{page_id}"
            f"?access_token={access_token}"
            f"&fields=name,id,fan_count,followers_count,category,link"
        )
        response = requests.get(url, timeout=10)
        data = response.json()

        if "error" in data:
            return {
                "connected": False,
                "error": data["error"].get("message", "Unknown error"),
            }

        return {
            "connected": True,
            "page_id": data.get("id"),
            "name": data.get("name", "Unknown Page"),
            "category": data.get("category", ""),
            "fan_count": data.get("fan_count", 0),
            "followers_count": data.get("followers_count", 0),
            "link": data.get("link", f"https://facebook.com/{page_id}"),
        }
    except Exception as e:
        logger.warning(f"Failed to fetch Facebook page info: {e}")
        return {"connected": False, "error": str(e)}


async def upload_to_facebook(upload_id: int) -> str:
    """
    Main upload entry point called by Celery task.
    Uploads video to the configured Facebook Page.

    Returns the Facebook video ID.
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
            uploader = FacebookUploader()

            # Build a clean description for Facebook
            description = upload.description or ""

            # Add hashtags if available
            if upload.hashtags:
                description = f"{description}\n\n{upload.hashtags}"

            fb_video_id = uploader.upload_video(
                file_path=video.file_path,
                title=upload.title,
                description=description,
                published=True,
                scheduled_publish_time=(
                    int(upload.scheduled_at.timestamp())
                    if upload.scheduled_at
                    else None
                ),
            )

            upload.facebook_video_id = fb_video_id
            await db.commit()

            logger.info(
                f"🎉 Video published to Facebook! "
                f"https://facebook.com/{fb_video_id}"
            )

            return fb_video_id

        except (ValueError, FileNotFoundError) as config_err:
            # Config/credential issues — propagate so Celery retries or reports
            error_msg = str(config_err)
            logger.error(
                f"❌ Facebook configuration error — upload cannot proceed: {error_msg}"
            )
            raise

        except Exception as e:
            # Non-critical failures — log but don't block the rest of the pipeline
            logger.warning(f"⚠️ Facebook upload failed: {e}")
            raise
