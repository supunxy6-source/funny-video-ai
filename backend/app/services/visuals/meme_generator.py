"""
Stateside Smiles — Meme Visual Generator

Creates meme-style visuals for comedy videos:
- Meme images with Impact font text overlays
- Caption cards with funny text on colorful backgrounds
- Downloads and processes Reddit images
- Generates reaction-style visuals

Uses Pillow for text overlay composition.
"""

import logging
import os
import random
import uuid
from io import BytesIO
from pathlib import Path
from typing import Optional

import httpx
from PIL import Image, ImageDraw, ImageFont, ImageFilter

from app.core.config import settings

logger = logging.getLogger(__name__)

# ── Meme Style Constants ─────────────────────────────────────────────

# Vibrant comedy color palettes
MEME_BACKGROUNDS = [
    ["#FF6B6B", "#4ECDC4"],  # Coral → Teal
    ["#A855F7", "#EC4899"],  # Purple → Pink
    ["#F59E0B", "#EF4444"],  # Amber → Red
    ["#10B981", "#3B82F6"],  # Green → Blue
    ["#8B5CF6", "#06B6D4"],  # Violet → Cyan
    ["#F97316", "#DB2777"],  # Orange → Pink
    ["#14B8A6", "#6366F1"],  # Teal → Indigo
    ["#FBBF24", "#F472B6"],  # Yellow → Pink
]

CAPTION_COLORS = [
    "#FFD700",  # Gold
    "#FF6B6B",  # Coral
    "#4ECDC4",  # Teal
    "#A855F7",  # Purple
    "#F59E0B",  # Amber
    "#EC4899",  # Hot Pink
    "#10B981",  # Emerald
    "#3B82F6",  # Blue
]

# Emoji reactions for visual flair
REACTION_EMOJIS = ["😂", "💀", "🤣", "😭", "🔥", "💯", "👀", "⚡", "🤯", "😤"]


class MemeGenerator:
    """Creates meme-style visuals for entertainment videos."""

    def __init__(self):
        self.output_dir = Path(settings.generated_dir) / "visuals" / "memes"
        self.output_dir.mkdir(parents=True, exist_ok=True)

    def _get_font(self, size: int, bold: bool = True) -> ImageFont.FreeTypeFont:
        """Get best available font for meme text."""
        font_names = [
            # Impact (classic meme font)
            "impact.ttf",
            "Impact.ttf",
            "C:\\Windows\\Fonts\\impact.ttf",
            "/usr/share/fonts/truetype/msttcorefonts/Impact.ttf",
            # Bold fallbacks
            "arialbd.ttf" if bold else "arial.ttf",
            "C:\\Windows\\Fonts\\arialbd.ttf" if bold else "C:\\Windows\\Fonts\\arial.ttf",
            "DejaVuSans-Bold.ttf" if bold else "DejaVuSans.ttf",
            "/usr/share/fonts/truetype/dejavu/DejaVuSans-Bold.ttf",
        ]
        for name in font_names:
            try:
                return ImageFont.truetype(name, size)
            except (OSError, IOError):
                continue
        return ImageFont.load_default()

    def create_meme_image(
        self,
        image_path: str,
        top_text: str = "",
        bottom_text: str = "",
        width: int = 1080,
        height: int = 1920,
    ) -> Optional[str]:
        """
        Create a classic meme with top/bottom Impact text overlay on an image.

        Args:
            image_path: Path to base image
            top_text: Text for top of image
            bottom_text: Text for bottom of image
            width: Output width
            height: Output height

        Returns:
            Path to generated meme image
        """
        try:
            img = Image.open(image_path).convert("RGBA")
            img = img.resize((width, height), Image.LANCZOS)

            draw = ImageDraw.Draw(img)
            font_size = max(48, width // 15)
            font = self._get_font(font_size, bold=True)

            # Draw top text (meme style: white with black outline)
            if top_text:
                self._draw_meme_text(draw, top_text, font, width, y_position="top")

            # Draw bottom text
            if bottom_text:
                self._draw_meme_text(draw, bottom_text, font, width, y_position="bottom", img_height=height)

            # Save
            out_path = str(self.output_dir / f"meme_{uuid.uuid4().hex}.png")
            img.convert("RGB").save(out_path, "PNG", quality=95)
            logger.info(f"🃏 Meme image created: {out_path}")
            return out_path

        except Exception as e:
            logger.warning(f"Meme image creation failed: {e}")
            return None

    def _draw_meme_text(
        self,
        draw: ImageDraw.Draw,
        text: str,
        font: ImageFont.FreeTypeFont,
        width: int,
        y_position: str = "top",
        img_height: int = 1920,
    ):
        """Draw Impact-style meme text with outline."""
        text = text.upper()

        # Word wrap
        words = text.split()
        lines = []
        current_line = ""
        for word in words:
            test_line = f"{current_line} {word}".strip()
            bbox = draw.textbbox((0, 0), test_line, font=font)
            if bbox[2] - bbox[0] > width - 60:
                if current_line:
                    lines.append(current_line)
                current_line = word
            else:
                current_line = test_line
        if current_line:
            lines.append(current_line)

        # Calculate total text height
        line_height = font.size + 10
        total_height = len(lines) * line_height

        # Position
        if y_position == "top":
            y_start = 30
        else:
            y_start = img_height - total_height - 50

        # Draw each line with outline
        outline_width = max(3, font.size // 15)
        for i, line in enumerate(lines):
            bbox = draw.textbbox((0, 0), line, font=font)
            text_width = bbox[2] - bbox[0]
            x = (width - text_width) // 2
            y = y_start + (i * line_height)

            # Black outline
            for dx in range(-outline_width, outline_width + 1):
                for dy in range(-outline_width, outline_width + 1):
                    if dx != 0 or dy != 0:
                        draw.text((x + dx, y + dy), line, font=font, fill="black")

            # White fill
            draw.text((x, y), line, font=font, fill="white")

    def create_caption_card(
        self,
        text: str,
        width: int = 1080,
        height: int = 1920,
        style: str = "gradient",
    ) -> Optional[str]:
        """
        Create a text-on-screen caption card with a colorful background.

        Styles: gradient, solid, dark, neon
        """
        try:
            img = Image.new("RGBA", (width, height))
            draw = ImageDraw.Draw(img)

            # Choose background style
            if style == "dark":
                # Dark background with subtle gradient
                for y in range(height):
                    r = int(15 + (y / height) * 20)
                    g = int(10 + (y / height) * 15)
                    b = int(30 + (y / height) * 25)
                    draw.line([(0, y), (width, y)], fill=(r, g, b))
            elif style == "neon":
                # Dark with neon accent
                img = Image.new("RGBA", (width, height), (10, 10, 20, 255))
                draw = ImageDraw.Draw(img)
            else:
                # Gradient background
                colors = random.choice(MEME_BACKGROUNDS)
                c1 = self._hex_to_rgb(colors[0])
                c2 = self._hex_to_rgb(colors[1])
                for y in range(height):
                    ratio = y / height
                    r = int(c1[0] + (c2[0] - c1[0]) * ratio)
                    g = int(c1[1] + (c2[1] - c1[1]) * ratio)
                    b = int(c1[2] + (c2[2] - c1[2]) * ratio)
                    draw.line([(0, y), (width, y)], fill=(r, g, b))

            # Draw main text
            font_size = max(52, width // 12)
            font = self._get_font(font_size, bold=True)

            # Word wrap and center
            lines = self._word_wrap(draw, text, font, width - 100)
            line_height = font_size + 15
            total_text_height = len(lines) * line_height
            y_start = (height - total_text_height) // 2

            text_color = "white"
            shadow_color = (0, 0, 0, 180)

            for i, line in enumerate(lines):
                bbox = draw.textbbox((0, 0), line, font=font)
                text_width = bbox[2] - bbox[0]
                x = (width - text_width) // 2
                y = y_start + (i * line_height)

                # Drop shadow
                draw.text((x + 3, y + 3), line, font=font, fill=shadow_color)
                # Main text
                draw.text((x, y), line, font=font, fill=text_color)

            # Add random emoji decoration
            emoji_text = random.choice(REACTION_EMOJIS)
            emoji_font = self._get_font(80, bold=True)
            try:
                draw.text((width - 120, 60), emoji_text, font=emoji_font, fill="white")
            except Exception:
                pass  # Emoji rendering may not be supported

            # Save
            out_path = str(self.output_dir / f"caption_{uuid.uuid4().hex}.png")
            img.convert("RGB").save(out_path, "PNG", quality=95)
            logger.info(f"💬 Caption card created: {out_path}")
            return out_path

        except Exception as e:
            logger.warning(f"Caption card creation failed: {e}")
            return None

    async def download_reddit_image(self, image_url: str) -> Optional[str]:
        """Download an image from Reddit and save locally."""
        if not image_url or not image_url.startswith("http"):
            return None

        try:
            async with httpx.AsyncClient(
                timeout=15.0,
                follow_redirects=True,
                headers={"User-Agent": "StatesideSmiles/1.0"},
            ) as client:
                resp = await client.get(image_url)
                if resp.status_code != 200:
                    return None

                content_type = resp.headers.get("content-type", "")
                if "image" not in content_type and not image_url.endswith((".jpg", ".png", ".gif", ".webp")):
                    return None

                # Determine extension
                ext = "jpg"
                if "png" in content_type or image_url.endswith(".png"):
                    ext = "png"
                elif "gif" in content_type or image_url.endswith(".gif"):
                    ext = "gif"
                elif "webp" in content_type or image_url.endswith(".webp"):
                    ext = "webp"

                file_path = self.output_dir / f"reddit_{uuid.uuid4().hex}.{ext}"
                file_path.write_bytes(resp.content)

                # Verify it's a valid image
                img = Image.open(str(file_path))
                img.verify()

                logger.info(f"📥 Reddit image downloaded: {file_path}")
                return str(file_path)

        except Exception as e:
            logger.warning(f"Reddit image download failed: {e}")
            return None

    def create_reaction_card(
        self,
        text: str,
        reaction_type: str = "shocked",
        width: int = 1080,
        height: int = 1920,
    ) -> Optional[str]:
        """
        Create a reaction-style card with text and visual elements.

        Reaction types: shocked, laughing, thinking, crying, fire
        """
        # Map reaction types to visual styles
        reaction_styles = {
            "shocked": {"bg": ["#1a1a2e", "#16213e"], "accent": "#e94560", "emoji": "😱"},
            "laughing": {"bg": ["#f093fb", "#f5576c"], "accent": "#ffd700", "emoji": "😂"},
            "thinking": {"bg": ["#4facfe", "#00f2fe"], "accent": "#ffffff", "emoji": "🤔"},
            "crying": {"bg": ["#a18cd1", "#fbc2eb"], "accent": "#ffffff", "emoji": "😭"},
            "fire": {"bg": ["#f12711", "#f5af19"], "accent": "#ffffff", "emoji": "🔥"},
        }

        style = reaction_styles.get(reaction_type, reaction_styles["laughing"])

        try:
            img = Image.new("RGBA", (width, height))
            draw = ImageDraw.Draw(img)

            # Gradient background
            c1 = self._hex_to_rgb(style["bg"][0])
            c2 = self._hex_to_rgb(style["bg"][1])
            for y in range(height):
                ratio = y / height
                r = int(c1[0] + (c2[0] - c1[0]) * ratio)
                g = int(c1[1] + (c2[1] - c1[1]) * ratio)
                b = int(c1[2] + (c2[2] - c1[2]) * ratio)
                draw.line([(0, y), (width, y)], fill=(r, g, b))

            # Large reaction text
            font_size = max(56, width // 10)
            font = self._get_font(font_size, bold=True)
            lines = self._word_wrap(draw, text.upper(), font, width - 80)
            line_height = font_size + 15
            total_height = len(lines) * line_height
            y_start = (height - total_height) // 2

            for i, line in enumerate(lines):
                bbox = draw.textbbox((0, 0), line, font=font)
                text_width = bbox[2] - bbox[0]
                x = (width - text_width) // 2
                y = y_start + (i * line_height)

                # Outline
                for dx in range(-3, 4):
                    for dy in range(-3, 4):
                        if abs(dx) + abs(dy) > 0:
                            draw.text((x + dx, y + dy), line, font=font, fill="black")
                draw.text((x, y), line, font=font, fill=style["accent"])

            out_path = str(self.output_dir / f"reaction_{uuid.uuid4().hex}.png")
            img.convert("RGB").save(out_path, "PNG", quality=95)
            logger.info(f"😲 Reaction card created: {out_path}")
            return out_path

        except Exception as e:
            logger.warning(f"Reaction card creation failed: {e}")
            return None

    def _word_wrap(self, draw: ImageDraw.Draw, text: str, font, max_width: int) -> list[str]:
        """Wrap text into lines that fit within max_width."""
        words = text.split()
        lines = []
        current_line = ""

        for word in words:
            test_line = f"{current_line} {word}".strip()
            bbox = draw.textbbox((0, 0), test_line, font=font)
            if bbox[2] - bbox[0] > max_width:
                if current_line:
                    lines.append(current_line)
                current_line = word
            else:
                current_line = test_line
        if current_line:
            lines.append(current_line)

        return lines

    @staticmethod
    def _hex_to_rgb(hex_color: str) -> tuple:
        """Convert hex color to RGB tuple."""
        hex_color = hex_color.lstrip("#")
        return tuple(int(hex_color[i:i+2], 16) for i in (0, 2, 4))
