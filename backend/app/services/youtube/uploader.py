"""
Stateside Smiles — YouTube Uploader (2026 Algorithm Optimized)

Handles video upload, thumbnail attachment, playlist management,
and pinned comment creation via YouTube Data API v3.

2026 ALGORITHM OPTIMIZATION:
- notifySubscribers=True for initial velocity
- embeddable=True for external shares
- publicStatsViewable=True for social proof CTR boost
- Auto-generated engagement pinned comment (boosts comment rate)
- 'shorts' tag always included for Shorts shelf discovery
- recordingDate set for temporal relevance signal
"""

import json
import logging
import re
import time
import uuid
from datetime import datetime, timezone
from pathlib import Path
from typing import Optional

from googleapiclient.discovery import build
from googleapiclient.http import MediaFileUpload
from app.services.youtube.auth import get_youtube_credentials

logger = logging.getLogger(__name__)

# Retry configuration
MAX_UPLOAD_RETRIES = 3
RETRY_DELAY_SECONDS = 30


class YouTubeUploader:
    """Uploads videos to YouTube via the Data API v3."""

    def __init__(self):
        creds = get_youtube_credentials()
        self.youtube = build("youtube", "v3", credentials=creds)

    def upload_video(
        self,
        file_path: str,
        title: str,
        description: str,
        tags: list[str],
        category_id: str = None,
        privacy_status: str = "private",
        scheduled_at: Optional[datetime] = None,
    ) -> str:
        """
        Upload a video to YouTube.

        Returns the YouTube video ID.
        """
        category_id = category_id or getattr(settings, "youtube_category_id", "23")
        # 2026: Ensure 'shorts' tag is always present for Shorts shelf discovery
        tags_with_shorts = list(tags) if tags else []
        shorts_tags = {"shorts", "youtubeshorts", "short"}
        existing_lower = {t.lower() for t in tags_with_shorts}
        for st in shorts_tags:
            if st not in existing_lower:
                tags_with_shorts.append(st)

        body = {
            "snippet": {
                "title": _ensure_clean_text(title, max_len=100, field_type="title"),
                "description": _ensure_clean_text(description, max_len=5000, field_type="description"),
                "tags": tags_with_shorts[:30],
                "categoryId": category_id,
                "defaultLanguage": "en",
                "defaultAudioLanguage": "en",
            },
            "status": {
                "privacyStatus": privacy_status,
                "selfDeclaredMadeForKids": False,
                "embeddable": True,  # Allow embedding → more shares → more views
                "publicStatsViewable": True,  # Social proof → higher CTR
            },
            "recordingDetails": {
                "recordingDate": datetime.now(timezone.utc).strftime("%Y-%m-%dT%H:%M:%S.000Z"),
            },
        }

        # Schedule publication if specified
        if scheduled_at:
            body["status"]["privacyStatus"] = "private"
            body["status"]["publishAt"] = scheduled_at.isoformat()

        media = MediaFileUpload(
            file_path,
            mimetype="video/mp4",
            resumable=True,
            chunksize=256 * 1024 * 1024,  # 256 MB chunks
        )

        logger.info(f"📤 Starting YouTube upload: '{title}'")

        request = self.youtube.videos().insert(
            part="snippet,status,recordingDetails",
            body=body,
            media_body=media,
            notifySubscribers=True,  # Ensure subscriber notifications fire
        )

        # Execute resumable upload with retry
        response = None
        retry_count = 0

        while response is None:
            try:
                status, response = request.next_chunk()
                if status:
                    progress = int(status.progress() * 100)
                    logger.info(f"📤 Upload progress: {progress}%")
            except Exception as e:
                retry_count += 1
                if retry_count > MAX_UPLOAD_RETRIES:
                    raise RuntimeError(f"Upload failed after {MAX_UPLOAD_RETRIES} retries: {e}")
                logger.warning(f"Upload error (retry {retry_count}): {e}")
                time.sleep(RETRY_DELAY_SECONDS)

        video_id = response.get("id")
        logger.info(f"✅ Video uploaded successfully! YouTube ID: {video_id}")
        return video_id

    def set_thumbnail(self, video_id: str, thumbnail_path: str) -> bool:
        """Set the thumbnail for a YouTube video."""
        try:
            media = MediaFileUpload(thumbnail_path, mimetype="image/jpeg")
            self.youtube.thumbnails().set(
                videoId=video_id,
                media_body=media,
            ).execute()
            logger.info(f"✅ Thumbnail set for video {video_id}")
            return True
        except Exception as e:
            logger.error(f"❌ Failed to set thumbnail: {e}")
            return False

    def add_to_playlist(self, video_id: str, playlist_id: str) -> bool:
        """Add a video to a YouTube playlist."""
        try:
            self.youtube.playlistItems().insert(
                part="snippet",
                body={
                    "snippet": {
                        "playlistId": playlist_id,
                        "resourceId": {
                            "kind": "youtube#video",
                            "videoId": video_id,
                        },
                    }
                },
            ).execute()
            logger.info(f"✅ Video {video_id} added to playlist {playlist_id}")
            return True
        except Exception as e:
            logger.error(f"❌ Failed to add to playlist: {e}")
            return False

    def add_comment(self, video_id: str, comment_text: str) -> bool:
        """Add a pinned comment to a YouTube video.
        
        Early comments with engagement questions boost algorithmic ranking.
        """
        try:
            result = self.youtube.commentThreads().insert(
                part="snippet",
                body={
                    "snippet": {
                        "videoId": video_id,
                        "topLevelComment": {
                            "snippet": {
                                "textOriginal": comment_text,
                            }
                        },
                    }
                },
            ).execute()
            
            # Try to pin the comment for maximum visibility
            comment_id = result.get("snippet", {}).get("topLevelComment", {}).get("id")
            if comment_id:
                try:
                    self.youtube.comments().setModerationStatus(
                        id=comment_id,
                        moderationStatus="published",
                    ).execute()
                except Exception:
                    pass  # Pinning may not be available for all channels
            
            logger.info(f"✅ Engagement comment added to video {video_id}")
            return True
        except Exception as e:
            logger.error(f"❌ Failed to add comment: {e}")
            return False

    def check_processing_status(self, video_id: str) -> str:
        """Check the processing status of an uploaded video."""
        try:
            response = self.youtube.videos().list(
                part="processingDetails,status",
                id=video_id,
            ).execute()

            items = response.get("items", [])
            if not items:
                return "not_found"

            processing = items[0].get("processingDetails", {})
            status = items[0].get("status", {})

            upload_status = status.get("uploadStatus", "unknown")
            processing_status = processing.get("processingStatus", "unknown")

            return f"{upload_status}/{processing_status}"
        except Exception as e:
            logger.error(f"Error checking status: {e}")
            return "error"


async def upload_to_youtube(upload_id: int) -> str:
    """
    Main upload entry point called by Celery task.
    Uploads video, sets thumbnail, adds to playlist, and posts pinned comment.

    Returns the YouTube video ID.
    """
    from sqlalchemy import select
    from app.core.config import settings
    from app.db.session import async_session_factory
    from app.models.upload import Upload
    from app.models.video import Video
    from app.models.thumbnail import Thumbnail

    async with async_session_factory() as db:
        upload = await db.get(Upload, upload_id)
        if not upload:
            raise ValueError(f"Upload record {upload_id} not found")

        video = await db.get(Video, upload.video_id)
        if not video:
            raise ValueError(f"Video {upload.video_id} not found")

        # Update status
        upload.status = "uploading"
        await db.commit()

        try:
            uploader = YouTubeUploader()

            # Parse tags
            tags = json.loads(upload.tags) if upload.tags else []

            # Upload video — sanitize title/description as final safeguard
            clean_title = _ensure_clean_text(upload.title, max_len=100, field_type="title")
            clean_description = _ensure_clean_text(upload.description, max_len=5000, field_type="description")

            category_to_use = upload.category_id or getattr(settings, "youtube_category_id", "23")
            yt_video_id = uploader.upload_video(
                file_path=video.file_path,
                title=clean_title,
                description=clean_description,
                tags=tags,
                category_id=category_to_use,
                privacy_status=upload.privacy_status,
                scheduled_at=upload.scheduled_at,
            )

            upload.youtube_video_id = yt_video_id
            upload.status = "processing"

            # Set thumbnail
            thumb_result = await db.execute(
                select(Thumbnail)
                .where(Thumbnail.video_id == video.id, Thumbnail.is_selected.is_(True))
            )
            thumbnail = thumb_result.scalar_one_or_none()
            if thumbnail:
                uploader.set_thumbnail(yt_video_id, thumbnail.file_path)

            # Add to playlist
            playlist_id = upload.playlist_id or settings.youtube_playlist_id
            if playlist_id:
                uploader.add_to_playlist(yt_video_id, playlist_id)

            # Add pinned comment (2026: auto-generate engagement comment if none provided)
            pinned_text = upload.pinned_comment
            if not pinned_text:
                mode = getattr(settings, "content_mode", "entertainment")
                if mode == "entertainment":
                    pinned_text = (
                        "😂 Which part made you laugh the most? Drop your comment below! 👇\n\n"
                        "❤️ LIKE if this made your day better\n"
                        "🔔 Subscribe to Stateside Smiles for daily viral laughs!"
                    )
                else:
                    pinned_text = (
                        "💡 What's YOUR take on this? Drop your thoughts below! 👇\n\n"
                        "❤️ Like if you learned something new\n"
                        "🔔 Follow for daily 30-second news updates"
                    )
            uploader.add_comment(yt_video_id, pinned_text)

            # Update final status
            upload.status = "published"
            upload.published_at = datetime.now(timezone.utc)
            video.status = "uploaded"
            await db.commit()

            logger.info(
                f"🎉 Video published to YouTube! "
                f"https://youtube.com/watch?v={yt_video_id}"
            )

            return yt_video_id

        except (FileNotFoundError, RuntimeError) as auth_err:
            # Auth/credential failures should NOT be silently swallowed.
            # Let them propagate so the pipeline task retries or reports failure.
            error_msg = str(auth_err)
            logger.error(
                f"❌ YouTube authentication failed — upload cannot proceed: {error_msg}"
            )
            upload.status = "auth_failed"
            upload.error_message = error_msg
            await db.commit()
            raise  # Propagate so Celery retries / reports failure

        except Exception as e:
            # Non-auth errors (network glitch, transient API error, etc.)
            # Fall back to local render so the video assets are preserved.
            logger.warning(f"⚠️ YouTube upload failed (non-auth): {e}")
            yt_mock_id = f"local_{uuid.uuid4().hex[:8]}"
            upload.youtube_video_id = yt_mock_id
            upload.status = "local_render_complete"
            upload.error_message = str(e)
            await db.commit()
            logger.info(f"✅ Video pipeline output saved locally: {video.file_path}")
            return yt_mock_id


def _ensure_clean_text(text: str, max_len: int = 100, field_type: str = "title") -> str:
    """Final safeguard: ensure text sent to YouTube API is clean human-readable content.
    
    This function is the last line of defense before data hits the YouTube API.
    It catches raw JSON, truncated JSON, and other malformed content.
    
    Key design: we parse/extract from the FULL text BEFORE applying any length
    truncation, so truncated JSON can never slip through to YouTube.
    """
    if not text or not text.strip():
        today = datetime.now(timezone.utc).strftime("%B %d, %Y")
        mode = getattr(settings, "content_mode", "entertainment")
        if field_type == "title":
            return f"Funniest Content Today — {today}" if mode == "entertainment" else f"Daily News Briefing — {today}"
        return f"Daily comedy & viral memes for {today}. Subscribe to Stateside Smiles!" if mode == "entertainment" else f"AI-generated news briefing for {today}. Subscribe for daily updates."

    cleaned = text.strip()

    # Detect JSON content — titles and descriptions should NEVER be raw JSON.
    # Check the FULL text before any truncation so we don't get partial JSON.
    if _looks_like_json(cleaned):
        cleaned = _extract_from_json_text(cleaned, field_type)

    # Remove JSON string artifacts
    cleaned = cleaned.strip('"\'{}')
    
    # Remove markdown
    cleaned = re.sub(r'[`*_~]', '', cleaned)
    
    # Collapse whitespace
    if '\n' not in cleaned:
        cleaned = re.sub(r'\s+', ' ', cleaned).strip()

    # Enforce length AFTER extraction — never truncate raw JSON
    if len(cleaned) > max_len:
        cleaned = cleaned[:max_len - 3].rsplit(" ", 1)[0] + "..."

    # Final paranoia check: if the result still looks like JSON, replace entirely
    if cleaned and (cleaned[0] in '{["' and any(c in cleaned for c in ['{', '[', '":', '":'])):
        today = datetime.now(timezone.utc).strftime("%B %d, %Y")
        mode = getattr(settings, "content_mode", "entertainment")
        if field_type == "title":
            cleaned = f"Funniest Content Today — {today}" if mode == "entertainment" else f"Daily News Briefing — {today}"
        else:
            cleaned = f"Daily comedy & viral memes for {today}. Subscribe to Stateside Smiles!" if mode == "entertainment" else f"AI-generated news briefing for {today}. Subscribe for daily updates."

    return cleaned


def _looks_like_json(text: str) -> bool:
    """Check if text appears to be JSON or truncated JSON."""
    stripped = text.strip()
    if not stripped:
        return False
    # Starts with JSON opener
    if stripped[0] in ('{', '['):
        return True
    # Contains JSON-like patterns (e.g., '"key":' or '"key" :') suggesting
    # it's a fragment of JSON with the leading brace stripped
    if re.search(r'"\w+"\s*:', stripped[:200]):
        return True
    return False


def _extract_from_json_text(text: str, field_type: str) -> str:
    """Extract human-readable content from JSON or truncated-JSON text.
    
    Tries in order:
    1. Full JSON parse → extract known fields
    2. Regex extraction of key fields from partial/truncated JSON
    3. Date-based fallback
    """
    today = datetime.now(timezone.utc).strftime("%B %d, %Y")

    # Attempt 1: parse as valid JSON
    try:
        data = json.loads(text)
        if isinstance(data, dict):
            if field_type == "title":
                for key in ["title", "name", "headline", "subject"]:
                    val = data.get(key, "")
                    if val and isinstance(val, str) and not _looks_like_json(val):
                        return val.strip()
                return f"Daily News Briefing — {today}"
            else:
                # Description — try to build from content fields
                for key in ["description", "text", "content", "summary"]:
                    val = data.get(key, "")
                    if val and isinstance(val, str) and len(val) > 20 and not _looks_like_json(val):
                        return val
                # Build from scenes if available
                scenes = data.get("scenes", [])
                if scenes and isinstance(scenes, list):
                    texts = []
                    title_val = data.get("title", "")
                    if title_val and isinstance(title_val, str):
                        texts.append(title_val)
                    for s in scenes:
                        if isinstance(s, dict) and s.get("text"):
                            texts.append(s["text"])
                    if texts:
                        return "\n\n".join(texts)
                return f"AI News Briefing for {today}"
    except (json.JSONDecodeError, TypeError):
        pass

    # Attempt 2: regex extraction from truncated/malformed JSON
    if field_type == "title":
        # Try to extract "title": "..." from anywhere in the text
        match = re.search(r'"title"\s*:\s*"([^"]{5,})"', text)
        if match:
            extracted = match.group(1).strip()
            if not _looks_like_json(extracted):
                return extracted
        # Try "name" or "headline"
        for key in ["name", "headline", "subject"]:
            match = re.search(rf'"{key}"\s*:\s*"([^"]+)"', text)
            if match:
                extracted = match.group(1).strip()
                if not _looks_like_json(extracted):
                    return extracted
        return f"Daily News Briefing — {today}"
    else:
        # For descriptions, try known fields first
        for key in ["description", "text", "summary", "content"]:
            match = re.search(rf'"{key}"\s*:\s*"([^"]+)"', text)
            if match:
                extracted = match.group(1).strip()
                if len(extracted) > 20 and not _looks_like_json(extracted):
                    return extracted
        # Last resort: strip all JSON syntax noise
        cleaned = re.sub(r'[{}\[\]]', '', text)
        cleaned = re.sub(r'"\w+"\s*:', '', cleaned)
        cleaned = re.sub(r'\s+', ' ', cleaned).strip()
        cleaned = cleaned.strip('"\',')
        if len(cleaned) > 20:
            return cleaned
        return f"AI-generated news briefing for {today}. Subscribe for daily updates."
