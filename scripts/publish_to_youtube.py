"""
AI News Studio — Publish Video to YouTube CLI

Publish any rendered video (by ID or file path) directly to the authenticated YouTube channel.

Usage:
    python scripts/publish_to_youtube.py --video-id 1 --privacy public
    python scripts/publish_to_youtube.py --file path/to/video.mp4 --title "My Title" --privacy public
"""

import sys
import argparse
import asyncio
from pathlib import Path

# Add backend directory to sys.path
backend_dir = Path(__file__).parent.parent / "backend"
sys.path.insert(0, str(backend_dir))

from app.services.youtube.auth import get_channel_info, is_authenticated
from app.services.youtube.uploader import YouTubeUploader


async def publish_db_video(video_id: int, privacy_status: str = "public"):
    """Publish a database video to YouTube."""
    from sqlalchemy import select
    from app.db.session import async_session_factory
    from app.models.video import Video
    from app.models.upload import Upload
    from app.services.seo.optimizer import optimize_seo
    from app.services.youtube.uploader import upload_to_youtube

    print(f"🔍 Looking up Video #{video_id} in database...")

    async with async_session_factory() as db:
        video = await db.get(Video, video_id)
        if not video:
            print(f"❌ Error: Video #{video_id} not found in database.")
            return None

        # Check existing upload or create one
        result = await db.execute(select(Upload).where(Upload.video_id == video_id))
        upload = result.scalars().first()

        if not upload:
            print(f"⚡ Generating SEO metadata and thumbnail for Video #{video_id}...")
            upload_id = await optimize_seo(video_id)
            upload = await db.get(Upload, upload_id)
        else:
            upload_id = upload.id

        upload.privacy_status = privacy_status
        await db.commit()

    print(f"📤 Uploading Video #{video_id} to YouTube as '{privacy_status}'...")
    yt_id = await upload_to_youtube(upload_id)
    print(f"🎉 Published successfully!")
    print(f"📺 YouTube Video ID: {yt_id}")
    print(f"🔗 Watch URL: https://youtube.com/watch?v={yt_id}")
    return yt_id


def publish_local_file(file_path: str, title: str, description: str, privacy_status: str = "public"):
    """Publish a local MP4 file directly to YouTube."""
    path = Path(file_path)
    if not path.exists():
        print(f"❌ Error: File not found at '{file_path}'")
        return None

    print(f"📤 Uploading '{path.name}' to YouTube...")
    print(f"   Title: {title}")
    print(f"   Privacy: {privacy_status}\n")

    uploader = YouTubeUploader()
    yt_id = uploader.upload_video(
        file_path=str(path),
        title=title,
        description=description,
        tags=["Shorts", "News", "AI", "Trending", "BreakingNews"],
        privacy_status=privacy_status,
    )

    print(f"🎉 Upload successful!")
    print(f"📺 YouTube Video ID: {yt_id}")
    print(f"🔗 Watch URL: https://youtube.com/watch?v={yt_id}")
    return yt_id


def main():
    parser = argparse.ArgumentParser(description="Publish video to YouTube")
    parser.add_argument("--video-id", type=int, help="Database Video ID to publish")
    parser.add_argument("--file", type=str, help="Local MP4 file path to publish")
    parser.add_argument("--title", type=str, default="AI News Studio Broadcast #Shorts", help="Video Title")
    parser.add_argument("--description", type=str, default="Daily news briefing. Subscribe for daily updates.", help="Video Description")
    parser.add_argument("--privacy", type=str, choices=["public", "unlisted", "private"], default="public", help="YouTube Privacy Status")
    parser.add_argument("--status", action="store_true", help="Check YouTube channel connection status")

    args = parser.parse_args()

    # Channel status check
    channel_info = get_channel_info()
    if channel_info.get("authenticated"):
        print(f"✅ Connected YouTube Channel: {channel_info.get('title')} (Subscribers: {channel_info.get('subscriber_count')})")
    else:
        print(f"⚠️ YouTube Status: Not connected ({channel_info.get('error')})")

    if args.status:
        return

    if args.video_id:
        asyncio.run(publish_db_video(args.video_id, args.privacy))
    elif args.file:
        publish_local_file(args.file, args.title, args.description, args.privacy)
    else:
        print("Please provide --video-id <ID> or --file <PATH>, or --status.")
        parser.print_help()


if __name__ == "__main__":
    main()
