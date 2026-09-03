"""
Stateside Smiles — Video Editor Assets (2026 Algorithm Optimized)

Manages branding assets, colors, fonts, and templates
used throughout the video editing pipeline.

Supports dual format: YouTube Shorts (9:16) + Regular (16:9).

2026 OPTIMIZATION:
- Zero intro/outro duration (every second is content)
- 60fps for smoother mobile playback
- CRF 15 for sharper quality on high-DPI mobile screens
- Comedy caption styling with vibrant colors
- Meme-style text overlay configuration
"""

from pathlib import Path

from app.core.config import settings

# ── Paths ──────────────────────────────────────────────
MEDIA_ROOT = Path(settings.media_root)
INTRO_DIR = MEDIA_ROOT / "intro"
OUTRO_DIR = MEDIA_ROOT / "outro"
FONTS_DIR = MEDIA_ROOT / "fonts"
LOGOS_DIR = MEDIA_ROOT / "logos"

# ── Brand Colors (Vibrant Comedy Palette) ──────────────
COLORS = {
    "primary": "#1A1A2E",        # Deep dark background
    "secondary": "#16213E",      # Dark blue
    "accent": "#F59E0B",         # Bright amber/gold
    "accent_alt": "#EC4899",     # Hot pink
    "accent_teal": "#14B8A6",    # Teal
    "accent_purple": "#A855F7",  # Purple
    "warning": "#F97316",        # Orange
    "danger": "#EF4444",         # Red
    "success": "#10B981",        # Emerald green
    "text_primary": "#FFFFFF",   # White text
    "text_secondary": "#D1D5DB", # Light gray text
    "lower_third_bg": "#1A1A2ECC",   # Semi-transparent dark
    "caption_bg": "#000000AA",   # Semi-transparent black
    "caption_highlight": "#FFD700",  # Gold for emphasized words
    "meme_text": "#FFFFFF",      # White meme text
    "meme_outline": "#000000",   # Black meme text outline
    "text_overlay_bg": "#000000CC",  # Semi-transparent for text hooks
    "gradient_start": "#A855F7", # Purple gradient start
    "gradient_end": "#EC4899",   # Pink gradient end
}

# ── Typography ─────────────────────────────────────────
FONTS = {
    "title": "DejaVuSans-Bold.ttf",       # Scene titles
    "body": "DejaVuSans.ttf",             # Body text
    "lower_third": "DejaVuSans-Bold.ttf",  # Lower third text
    "stat": "DejaVuSans-Bold.ttf",        # Statistics overlay
    "caption": "DejaVuSans-Bold.ttf",     # Burned-in captions
    "meme": "DejaVuSans-Bold.ttf",        # Meme text (Impact preferred)
}

# Default font sizes (scaled for vertical canvas)
FONT_SIZES = {
    "title": 64,
    "subtitle": 42,
    "body": 34,
    "caption": 65,              # Large for mobile readability
    "caption_min": 55,
    "lower_third_name": 34,
    "lower_third_title": 26,
    "watermark": 22,
    "text_overlay": 48,         # Text overlay hooks
    "meme_top": 72,             # Meme top text
    "meme_bottom": 72,          # Meme bottom text
}

# ── Video Settings (YouTube Shorts 9:16 — Primary) ──────
VIDEO_CONFIG = {
    "width": getattr(settings, "video_width", 1080),
    "height": getattr(settings, "video_height", 1920),
    "fps": 60,                  # 60fps for smoother mobile playback
    "codec": "libx264",
    "audio_codec": "aac",
    "audio_bitrate": "192k",
    "video_bitrate": "15M",
    "pixel_format": "yuv420p",
    "preset": "medium",
    "crf": 15,
}

# ── Regular Video Settings (16:9 Landscape) ─────────────
REGULAR_VIDEO_CONFIG = {
    "width": getattr(settings, "regular_video_width", 1920),
    "height": getattr(settings, "regular_video_height", 1080),
    "fps": 30,                  # 30fps is fine for regular videos
    "codec": "libx264",
    "audio_codec": "aac",
    "audio_bitrate": "192k",
    "video_bitrate": "12M",
    "pixel_format": "yuv420p",
    "preset": "medium",
    "crf": 18,
}

# ── Transition Settings ────────────────────────────────
TRANSITIONS = {
    "default": "crossfade",
    "crossfade_duration": 0.2,   # Fast transitions for comedy pacing
    "fade_in_duration": 0.0,     # No fade in — start instantly
    "fade_out_duration": 0.0,    # No fade out — loop seamlessly
}

# ── Lower Third Settings (Stateside Smiles Branding) ──
LOWER_THIRD = {
    "position_x": 40,
    "position_y": 1320,
    "padding": 20,
    "bar_height": 6,
    "bar_color": COLORS["accent"],      # Amber/Gold accent bar
    "bg_color": "#1A1A2ECC",
    "text_color": COLORS["text_primary"],
    "duration": 4.0,
    "fade_duration": 0.3,
    "channel_name": "Stateside Smiles",
}

# ── Caption Settings (Burned-in Kinetic Captions) ──────
CAPTION_CONFIG = {
    "font_size": 65,
    "font_color": "#FFFFFF",
    "highlight_color": "#FFD700",   # Gold highlight
    "stroke_color": "#000000",
    "stroke_width": 4,
    "bg_color": None,               # Stroke-only style
    "position_y": 960,
    "max_words_per_line": 4,
    "animation": "word_by_word",
    "shadow_offset": 3,
}

# ── Text Overlay Hook Settings ─────────────────────────
TEXT_OVERLAY_CONFIG = {
    "font_size": 48,
    "font_color": "#FFFFFF",
    "bg_color": "#000000AA",
    "border_radius": 16,
    "position_y": 480,
    "padding_x": 32,
    "padding_y": 16,
    "duration": 2.0,
    "fade_in": 0.15,
}

# ── Meme Overlay Settings ──────────────────────────────
MEME_OVERLAY_CONFIG = {
    "top_text_size": 72,
    "bottom_text_size": 72,
    "font_color": "#FFFFFF",
    "outline_color": "#000000",
    "outline_width": 4,
    "top_margin": 30,
    "bottom_margin": 50,
}

# ── Intro/Outro (REMOVED — every second is content) ───
INTRO_DURATION = 0.0
OUTRO_DURATION = 0.0
