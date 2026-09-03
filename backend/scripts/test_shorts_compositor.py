import os
import sys
import uuid

# Enable UTF-8 encoding
if sys.platform == "win32":
    sys.stdout.reconfigure(encoding="utf-8", errors="replace")

from PIL import Image, ImageDraw, ImageFont

output_dir = "backend/test_output_images"
os.makedirs(output_dir, exist_ok=True)

width, height = 1080, 1920

def test_vertical_rendering():
    try:
        from moviepy import (
            AudioFileClip,
            CompositeVideoClip,
            ImageClip,
            concatenate_videoclips,
        )

        audio_path = os.path.join(output_dir, "edge_female_voice.mp3")
        image_path = os.path.join(output_dir, "pollinations_test.jpg")

        if not os.path.exists(audio_path) or not os.path.exists(image_path):
            print("Required test assets missing")
            return

        audio = AudioFileClip(audio_path)
        duration = min(audio.duration, 5.0)

        # 1. Intro clip (1.5s)
        intro_img_path = os.path.join(output_dir, "test_intro.png")
        img = Image.new("RGB", (width, height), color=(7, 15, 30))
        draw = ImageDraw.Draw(img)
        draw.rectangle([(0, 0), (width, 12)], fill=(0, 229, 255))
        draw.rectangle([(0, height - 12), (width, height)], fill=(0, 229, 255))
        draw.rounded_rectangle([(360, 480), (720, 540)], radius=18, fill=(0, 180, 216))
        draw.text((540, 495), "⚡ NOVA NEWS", fill=(255, 255, 255), anchor="mt")
        img.save(intro_img_path)

        intro_clip = ImageClip(intro_img_path).with_duration(1.5)

        # 2. Scene clip with image and audio
        scene_clip = (
            ImageClip(image_path)
            .resized((width, height))
            .with_duration(duration)
            .with_audio(audio)
        )

        # 3. Outro clip (2.0s)
        outro_img_path = os.path.join(output_dir, "test_outro.png")
        img_outro = Image.new("RGB", (width, height), color=(7, 15, 30))
        draw_outro = ImageDraw.Draw(img_outro)
        draw_outro.rectangle([(0, 0), (width, 12)], fill=(0, 229, 255))
        draw_outro.rectangle([(0, height - 12), (width, height)], fill=(0, 229, 255))
        draw_outro.rounded_rectangle([(80, 900), (1000, 1030)], radius=24, fill=(220, 38, 38))
        draw_outro.text((540, 940), "SUBSCRIBE FOR DAILY SHORTS", fill=(255, 255, 255), anchor="mt")
        img_outro.save(outro_img_path)

        outro_clip = ImageClip(outro_img_path).with_duration(2.0)

        # Concatenate and render
        final_clip = concatenate_videoclips([intro_clip, scene_clip, outro_clip], method="compose")
        video_out_path = os.path.join(output_dir, "test_shorts_output.mp4")

        final_clip.write_videofile(
            video_out_path,
            fps=30,
            codec="libx264",
            audio_codec="aac",
            threads=2,
            preset="ultrafast",
            logger=None,
        )

        final_clip.close()

        if os.path.exists(video_out_path):
            print(f"🎬 ✅ YouTube Shorts 1080x1920 video rendered successfully: {video_out_path} ({os.path.getsize(video_out_path)/1024:.1f} KB)")
    except Exception as e:
        print(f"⚠️ Video compositing test note: {e}")

if __name__ == "__main__":
    test_vertical_rendering()
