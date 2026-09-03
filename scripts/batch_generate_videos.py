"""
AI News Studio — Batch Video Generation & Publishing CLI

Produce 3 to 5 distinct news videos in a single batch and publish them to YouTube.

Usage:
    python scripts/batch_generate_videos.py --count 3
    python scripts/batch_generate_videos.py --count 5 --no-publish
"""

import sys
import argparse
import asyncio
from pathlib import Path

# Add backend directory to sys.path
backend_dir = Path(__file__).parent.parent / "backend"
sys.path.insert(0, str(backend_dir))

from app.services.youtube.auth import get_channel_info


async def run_batch(count: int = 3, publish: bool = True):
    """Run batch video generation for N stories."""
    from app.core.config import settings
    from app.tasks.pipeline import run_batch_pipeline

    if not publish:
        settings.youtube_auto_publish = False

    print(f"\n=======================================================")
    print(f"🎬 AI NEWS STUDIO — BATCH PRODUCTION ({count} VIDEOS)")
    print(f"=======================================================")
    
    channel_info = get_channel_info()
    if channel_info.get("authenticated"):
        print(f"📺 YouTube Target: {channel_info.get('title')} ({'Auto-Publish Active' if publish else 'Local Render Only'})")
    else:
        print(f"⚠️ YouTube Target: Bypassed / Local Render")

    print(f"🎯 Target Video Count: {count} videos")
    print(f"📐 Video Format: {getattr(settings, 'video_format', 'shorts')} (9:16 vertical 1080x1920)")
    print(f"🗣️ TTS Voice: {getattr(settings, 'edge_tts_voice', 'en-US-AriaNeural')}")
    print(f"-------------------------------------------------------\n")

    from app.tasks.pipeline import run_batch_pipeline
    task_result = run_batch_pipeline(video_count=count)
    print(f"\n=======================================================")
    print(f"🎉 Batch Production Completed!")
    print(f"=======================================================")
    print(f"Pipeline Run ID: {task_result.get('pipeline_run_id')}")
    print(f"Videos Produced: {task_result.get('videos_created')}")
    for res in task_result.get("results", []):
        story_idx = res.get("story_index")
        video_id = res.get("video_id")
        yt_id = res.get("youtube_video_id")
        status = res.get("status")
        yt_link = f"https://youtube.com/watch?v={yt_id}" if yt_id and not str(yt_id).startswith("local_") else "Local render"
        print(f"  • Video #{video_id} (Story {story_idx}): {status} -> {yt_link}")
    print(f"=======================================================\n")


def main():
    parser = argparse.ArgumentParser(description="Batch generate 3 to 5 news videos and publish to YouTube")
    parser.add_argument("--count", type=int, default=3, choices=[1, 2, 3, 4, 5], help="Number of videos to produce (1-5)")
    parser.add_argument("--no-publish", action="store_true", help="Disable automatic YouTube publishing")

    args = parser.parse_args()
    asyncio.run(run_batch(count=args.count, publish=not args.no_publish))


if __name__ == "__main__":
    main()
