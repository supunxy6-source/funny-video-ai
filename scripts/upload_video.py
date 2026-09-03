"""
AI News Studio — Direct YouTube Video Uploader CLI

Uploads any local MP4 video file directly to your authenticated YouTube channel.
Usage:
    python scripts/upload_video.py <video_file.mp4> --title "My Title" --description "My Description" --privacy private

Example:
    python scripts/upload_video.py test.mp4 --title "AI Breakthrough 2026"
"""

import sys
import argparse
from pathlib import Path

# Add backend directory to path
backend_dir = Path(__file__).parent.parent / "backend"
sys.path.insert(0, str(backend_dir))

from app.services.youtube.uploader import YouTubeUploader


def upload_file(
    file_path: str,
    title: str = "AI News Studio Video",
    description: str = "Autonomous AI-generated news video.",
    tags: list = None,
    privacy_status: str = "private",
):
    path = Path(file_path)
    if not path.exists():
        print(f"❌ Error: File not found at '{file_path}'")
        return None

    tags = tags or ["AI", "News", "Technology", "Automation"]

    print(f"🚀 Uploading '{path.name}' to YouTube...")
    print(f"   Title: {title}")
    print(f"   Privacy Status: {privacy_status}\n")

    uploader = YouTubeUploader()
    video_id = uploader.upload_video(
        file_path=str(path),
        title=title,
        description=description,
        tags=tags,
        privacy_status=privacy_status,
    )

    url = f"https://youtube.com/watch?v={video_id}"
    print(f"\n🎉 Video uploaded successfully!")
    print(f"📺 YouTube Video ID: {video_id}")
    print(f"🔗 Watch URL: {url}")
    return video_id


if __name__ == "__main__":
    parser = argparse.ArgumentParser(description="Upload a video to YouTube")
    parser.add_argument("file_path", help="Path to local MP4 video file")
    parser.add_argument("--title", default="AI News Studio Broadcast", help="Video title")
    parser.add_argument("--description", default="Daily news briefing.", help="Video description")
    parser.add_argument("--privacy", default="private", choices=["private", "unlisted", "public"], help="Privacy status")

    args = parser.parse_args()
    upload_file(args.file_path, args.title, args.description, privacy_status=args.privacy)
