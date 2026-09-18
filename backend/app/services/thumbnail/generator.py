"""
Stateside Smiles — Thumbnail Generator (Views-Optimized Edition)

Generates multiple YouTube thumbnail variants using FLUX/SDXL,
composites aggressive text overlays with Pillow, scores predicted CTR
with an enhanced multi-signal heuristic, and selects the best one.

VIEWS OPTIMIZATION: Red BREAKING badges, emoji overlays, larger bolder text,
higher contrast, and improved CTR prediction scoring.
"""

import json
import logging
import math
import uuid
from pathlib import Path
from typing import Optional

from PIL import Image, ImageDraw, ImageFont
from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession

from app.core.config import settings
from app.db.session import async_session_factory
from app.models.script import Script
from app.models.video import Video
from app.models.thumbnail import Thumbnail
from app.services.visuals.image_generator import ImageGenerator
from app.services.scriptwriter.prompts import THUMBNAIL_PROMPT_TEMPLATE

logger = logging.getLogger(__name__)

# Thumbnail specs (YouTube Shorts 9:16)
THUMB_WIDTH = 1080
THUMB_HEIGHT = 1920
NUM_VARIANTS = 3

# Badge styles — comedy-focused for entertainment channel
BADGE_STYLES = [
    {"text": "😂 SO FUNNY", "bg": (236, 72, 153), "border": (244, 114, 182)},     # Hot pink
    {"text": "💀 I'M DONE", "bg": (124, 58, 237), "border": (167, 139, 250)},      # Purple
    {"text": "🤣 NO WAY", "bg": (245, 158, 11), "border": (251, 191, 36)},         # Amber
]


class ThumbnailGenerator:
    """Generates and scores YouTube thumbnail/cover variants for Shorts."""

    def __init__(self):
        self.image_gen = ImageGenerator()
        self.output_dir = Path(settings.generated_dir) / "thumbnails"
        self.output_dir.mkdir(parents=True, exist_ok=True)

    async def generate_variants(
        self, topic: str, title: str, num_variants: int = NUM_VARIANTS, video_format: str = "shorts"
    ) -> list[dict]:
        """Generate multiple thumbnail variants and score them."""
        variants = []
        target_aspect = "16:9" if video_format == "regular" else "9:16"

        for i in range(num_variants):
            prompt_suffix = [
                "Hilarious expressive close-up with vivid vibrant colors and comical disbelief",
                "Wide-angle chaotic funny scene with clear comedic action and high contrast",
                "Priceless funny reaction with exaggerated facial expression and bright punchy lighting",
            ]
            prompt = THUMBNAIL_PROMPT_TEMPLATE.format(topic=topic)
            if i < len(prompt_suffix):
                prompt += f"\nStyle variation: {prompt_suffix[i]}"

            # Generate base image with format-appropriate aspect ratio
            image_path = await self.image_gen.generate_image(
                prompt=prompt,
                aspect_ratio=target_aspect,
                title=title,
                search_keywords=topic,
            )

            if image_path:
                # Select badge style based on variant
                badge_style = BADGE_STYLES[i % len(BADGE_STYLES)]
                
                # Add aggressive text overlay with badges
                final_path = self._add_text_overlay(image_path, title, badge_style, video_format=video_format)
                if final_path:
                    # Score the thumbnail with enhanced heuristic
                    score = self._predict_ctr(title, i, badge_style)
                    variants.append({
                        "file_path": final_path,
                        "prompt": prompt[:500],
                        "predicted_ctr": score,
                    })

        # Sort by predicted CTR
        variants.sort(key=lambda x: x["predicted_ctr"], reverse=True)

        logger.info(
            f"🖼️ Generated {len(variants)} thumbnail variants ({target_aspect}) "
            f"(best CTR: {variants[0]['predicted_ctr']:.3f})"
            if variants else "No thumbnails generated"
        )

        return variants

    def _add_text_overlay(
        self, image_path: str, title: str, badge_style: dict = None, video_format: str = "shorts"
    ) -> Optional[str]:
        """Add high-CTR text overlay with urgency badges to thumbnail image."""
        try:
            import textwrap

            is_regular = video_format == "regular"
            thumb_w = 1920 if is_regular else THUMB_WIDTH
            thumb_h = 1080 if is_regular else THUMB_HEIGHT

            img = Image.open(image_path).convert("RGB")
            img = img.resize((thumb_w, thumb_h), Image.LANCZOS)

            # Use a bold system font (fallback to default)
            font_names = [
                "arialbd.ttf",
                "DejaVuSans-Bold.ttf",
                "/usr/share/fonts/truetype/dejavu/DejaVuSans-Bold.ttf",
                "C:\\Windows\\Fonts\\arialbd.ttf",
            ]
            font = None
            font_badge = None
            font_small = None
            for fn in font_names:
                try:
                    font = ImageFont.truetype(fn, 96)  # Larger title text
                    font_badge = ImageFont.truetype(fn, 40)  # Badge text
                    font_small = ImageFont.truetype(fn, 34)
                    break
                except Exception:
                    continue
            if font is None:
                font = ImageFont.load_default()
                font_badge = font
                font_small = font

            # === DARK VIGNETTE OVERLAY (draws eye to center) ===
            vignette = Image.new("RGBA", (thumb_w, thumb_h), (0, 0, 0, 0))
            vignette_draw = ImageDraw.Draw(vignette)
            # Top vignette
            top_vig = 180 if is_regular else 300
            for y in range(0, top_vig):
                alpha = int(120 * (1 - y / top_vig))
                vignette_draw.line([(0, y), (thumb_w, y)], fill=(0, 0, 0, alpha))
            # Bottom heavy gradient overlay
            gradient_start = thumb_h - (450 if is_regular else 750)
            for y in range(gradient_start, thumb_h):
                alpha = int(230 * (y - gradient_start) / (thumb_h - gradient_start))
                vignette_draw.line([(0, y), (thumb_w, y)], fill=(0, 0, 0, alpha))

            img = img.convert("RGBA")
            img = Image.alpha_composite(img, vignette)
            draw = ImageDraw.Draw(img)

            # === RED URGENCY BADGE (top area) ===
            if badge_style:
                badge_text = badge_style["text"]
                badge_bg = badge_style["bg"]
                badge_border = badge_style["border"]
                badge_y = 40 if is_regular else 120
                badge_w = 420
                badge_h = 65
                badge_x = (thumb_w - badge_w) // 2
                
                # Badge shadow
                draw.rounded_rectangle(
                    [(badge_x + 3, badge_y + 3), (badge_x + badge_w + 3, badge_y + badge_h + 3)],
                    radius=16, fill=(0, 0, 0, 160)
                )
                # Badge background
                draw.rounded_rectangle(
                    [(badge_x, badge_y), (badge_x + badge_w, badge_y + badge_h)],
                    radius=16, fill=(*badge_bg, 245), outline=(*badge_border, 255), width=3
                )
                # Badge text
                draw.text(
                    (thumb_w // 2, badge_y + 14),
                    badge_text, font=font_badge, fill=(255, 255, 255, 255), anchor="mt"
                )

            # === MAIN TITLE TEXT (large, bold, with heavy stroke) ===
            clean_title = title.strip() or "Funniest Thing Today"
            # Remove #Shorts from thumbnail text (visual noise)
            clean_title = clean_title.replace("#Shorts", "").replace("#shorts", "").strip()
            
            wrap_width = 28 if is_regular else 16
            lines = textwrap.wrap(clean_title, width=wrap_width)[:(3 if is_regular else 4)]
            start_y = thumb_h - (320 if is_regular else 520)
            line_spacing = 95 if is_regular else 120
            for i, line in enumerate(lines):
                cur_y = start_y + i * line_spacing
                # Heavy text stroke outline for readability
                draw.text(
                    (thumb_w // 2, cur_y),
                    line,
                    font=font,
                    fill=(255, 255, 255, 255),
                    stroke_width=8,
                    stroke_fill=(0, 0, 0, 255),
                    anchor="mt",
                )

            # === BOTTOM ENGAGEMENT BAR ===
            bar_y = thumb_h - (70 if is_regular else 100)
            bar_h = 45 if is_regular else 55
            draw.rounded_rectangle(
                [(40, bar_y), (thumb_w - 40, bar_y + bar_h)],
                radius=12, fill=(0, 0, 0, 180)
            )
            draw.text(
                (thumb_w // 2, bar_y + 8),
                "😂 STATESIDE SMILES • DAILY LAUGHS",
                font=font_small, fill=(255, 255, 255, 220), anchor="mt"
            )

            # Save
            file_name = f"thumb_{uuid.uuid4().hex}.jpg"
            file_path = self.output_dir / file_name
            img = img.convert("RGB")
            img.save(str(file_path), "JPEG", quality=95)

            return str(file_path)

        except Exception as e:
            logger.error(f"Thumbnail text overlay failed: {e}")
            return image_path  # Return original image as fallback

    def _predict_ctr(
        self, title: str, variant_idx: int, badge_style: dict = None
    ) -> float:
        """
        Predict click-through rate for a thumbnail variant.
        Enhanced multi-signal heuristic scoring for YouTube Shorts.
        """
        score = 0.5
        title_lower = title.lower()

        # Title length scoring (under 40 chars optimal for Shorts)
        title_len = len(title)
        if title_len < 40:
            score += 0.15
        elif title_len < 55:
            score += 0.05
        elif title_len > 70:
            score -= 0.10

        # Reward high-impact comedy power words (tiered)
        high_impact = [
            "funniest", "hilarious", "insane", "epic", "unbelievable",
            "craziest", "wildest", "legendary", "impossible", "cursed",
        ]
        medium_impact = [
            "fail", "wholesome", "relatable", "accurate", "caught",
            "exposed", "real", "valid", "goated", "incredible",
        ]
        low_impact = [
            "viral", "trending", "new", "memes", "funny", "comedy", "latest",
        ]
        
        if any(word in title_lower for word in high_impact):
            score += 0.15
        elif any(word in title_lower for word in medium_impact):
            score += 0.10
        elif any(word in title_lower for word in low_impact):
            score += 0.05

        # Variant composition bonus (close-up > wide > emotional)
        variant_bonus = [0.12, 0.06, 0.09]  # Close-up, wide, emotional
        if variant_idx < len(variant_bonus):
            score += variant_bonus[variant_idx]

        # Numbers in title (proven CTR boost)
        if any(c.isdigit() for c in title):
            score += 0.10

        # Question mark (curiosity gap)
        if "?" in title:
            score += 0.08

        # Badge style impact (comedy badges)
        if badge_style:
            if "SO FUNNY" in badge_style.get("text", ""):
                score += 0.08  # Hot pink comedy badge is highest CTR
            elif "I'M DONE" in badge_style.get("text", ""):
                score += 0.07
            else:
                score += 0.05

        # Penalty for generic/boring words
        boring_words = ["daily", "briefing", "report", "summary", "weekly"]
        if any(word in title_lower for word in boring_words):
            score -= 0.08

        return min(max(score, 0.1), 1.0)


async def generate_thumbnails(video_id: int) -> int:
    """
    Main thumbnail generation entry point called by Celery task.
    Generates variants, scores them, and saves to DB.

    Returns the selected thumbnail ID.
    """
    generator = ThumbnailGenerator()

    async with async_session_factory() as db:
        video = await db.get(Video, video_id)
        if not video:
            raise ValueError(f"Video {video_id} not found")

        script = await db.get(Script, video.script_id)
        if not script:
            raise ValueError(f"Script {video.script_id} not found")

        video_format = getattr(script, "video_format", "shorts") or "shorts"

        variants = await generator.generate_variants(
            topic=script.topic_summary,
            title=script.title,
            video_format=video_format,
        )

        if not variants:
            logger.error(f"No thumbnails generated for video {video_id}")
            return -1

        selected_id = None
        for i, variant in enumerate(variants):
            is_best = i == 0  # First is highest CTR
            thumb = Thumbnail(
                video_id=video_id,
                file_path=variant["file_path"],
                prompt=variant.get("prompt"),
                predicted_ctr=variant["predicted_ctr"],
                is_selected=is_best,
            )
            db.add(thumb)
            await db.flush()
            if is_best:
                selected_id = thumb.id

        await db.commit()
        logger.info(
            f"💾 Saved {len(variants)} thumbnails for video {video_id} "
            f"(selected: #{selected_id})"
        )

        return selected_id
