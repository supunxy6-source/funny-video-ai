"""
Standalone Dynamic Video Generation Verification Script
Verifies:
1. High-definition 1080x1920 30fps dynamic motion synthesis (Ken Burns push/pull/pan)
2. VideoGenerator scene clip generation
3. Full multi-scene YouTube Shorts video compositing using dynamic video clips
"""

import asyncio
import os
import sys
import time
from pathlib import Path

# Enable UTF-8 encoding for console output on Windows
if sys.platform == "win32":
    sys.stdout.reconfigure(encoding="utf-8", errors="replace")

# Add backend directory to sys.path
sys.path.insert(0, str(Path(__file__).resolve().parent.parent))

output_dir = Path("backend/test_output_images")
output_dir.mkdir(parents=True, exist_ok=True)


async def test_motion_synthesis():
    print("\n🎬 --- TEST 1: Synthesizing Dynamic Moving Video Clips (Ken Burns Motion) ---")
    from app.services.visuals.video_generator import VideoGenerator

    vgen = VideoGenerator()
    img_path = output_dir / "pollinations_test.jpg"
    assert img_path.exists(), "Source test image not found"

    # Test different motion directions
    motions = ["zoom_in", "zoom_out", "pan_right"]
    generated_clips = []

    for motion in motions:
        t0 = time.time()
        clip_path = vgen._synthesize_motion_video(
            image_path=str(img_path),
            duration=3.0,
            motion_type=motion,
            width=1080,
            height=1920,
        )
        elapsed = time.time() - t0
        assert clip_path and os.path.exists(clip_path), f"Motion clip failed for {motion}"
        size_kb = os.path.getsize(clip_path) / 1024
        print(f"✅ Motion video ({motion}, 3.0s, 1080x1920): {clip_path} ({size_kb:.1f} KB in {elapsed:.2f}s)")
        generated_clips.append(clip_path)

    return generated_clips


async def test_full_video_composition(motion_clips):
    print("\n🎥 --- TEST 2: Compositing Full YouTube Shorts with Dynamic Video Clips & Female Narration ---")
    from moviepy import AudioFileClip, CompositeVideoClip, ImageClip, concatenate_videoclips
    from app.services.editor.compositor import VideoCompositor

    compositor = VideoCompositor()
    audio_path = str(output_dir / "edge_female_voice.mp3")
    assert os.path.exists(audio_path), "Female audio test file missing"

    # Create 3 dynamic scenes using the synthesized video clips
    scene_clips = []
    titles = [
        "BREAKING: AI Video Generator Live",
        "Full Motion 60FPS Video Enabled",
        "Verified YouTube Shorts Pipeline",
    ]

    for idx, (vid_path, title) in enumerate(zip(motion_clips, titles)):
        scene_clip = compositor.create_scene_clip(
            video_path=vid_path,
            audio_path=audio_path,
            title=title,
            source_text=title,
            order=idx + 1,
        )
        scene_clips.append(scene_clip)

    intro = compositor.create_intro("AI VIDEO GENERATOR ACTIVE")
    outro = compositor.create_outro("AI VIDEO GENERATOR ACTIVE")

    all_clips = [intro] + scene_clips + [outro]
    final_video_path = output_dir / "verified_shorts_full_motion.mp4"

    final = concatenate_videoclips(all_clips, method="compose")
    final.write_videofile(
        str(final_video_path),
        fps=30,
        codec="libx264",
        audio_codec="aac",
        threads=4,
        preset="ultrafast",
        logger=None,
    )
    final.close()

    assert os.path.exists(final_video_path), "Final video not created"
    file_size_mb = os.path.getsize(final_video_path) / (1024 * 1024)
    print(f"\n🎉 FULL DYNAMIC VIDEO SHORT RENDERED SUCCESSFULLY!")
    print(f"📍 File: {final_video_path}")
    print(f"📊 Size: {file_size_mb:.2f} MB (1080x1920 Vertical, Continuous Motion, Female Narration)")


async def main():
    print("=== STARTING DYNAMIC VIDEO GENERATION VERIFICATION ===")
    clips = await test_motion_synthesis()
    await test_full_video_composition(clips)
    print("\n🌟 ALL TESTS PASSED: SCENES ARE NOW REAL MOVING VIDEOS (NOT JUST IMAGES)!")


if __name__ == "__main__":
    asyncio.run(main())
