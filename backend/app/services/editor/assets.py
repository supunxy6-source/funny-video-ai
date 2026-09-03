"""
AI News Studio — Video Editor Assets (2026 Algorithm Optimized)

Manages branding assets, colors, fonts, and templates
used throughout the video editing pipeline.

2026 OPTIMIZATION:
- Zero intro/outro duration (every second is content)
- 60fps for smoother mobile playback (less swipe-worthy)
- CRF 15 for sharper quality on high-DPI mobile screens
- Caption styling for burned-in kinetic captions
- Text overlay hook configuration
"""

from pathlib import Path

from app.core.config import settings

# ── Paths ──────────────────────────────────────────────
MEDIA_ROOT = Path(settings.media_root)
INTRO_DIR = MEDIA_ROOT / "intro"
OUTRO_DIR = MEDIA_ROOT / "outro"
FONTS_DIR = MEDIA_ROOT / "fonts"
LOGOS_DIR = MEDIA_ROOT / "logos"

# ── Brand Colors ───────────────────────────────────────
COLORS = {
    "primary": "#0A1628",       # Deep navy background
    "secondary": "#1E3A5F",     # Dark blue accent
    "accent": "#4FC3F7",        # Bright blue highlight
    "accent_alt": "#81C784",    # Green highlight
    "warning": "#FFB74D",       # Orange/amber
    "danger": "#E57373",        # Red
    "text_primary": "#FFFFFF",  # White text
    "text_secondary": "#B0BEC5",# Light gray text
    "lower_third_bg": "#0A1628CC",  # Semi-transparent navy
    "caption_bg": "#000000AA",  # Semi-transparent black
    "caption_highlight": "#FFD700",  # Gold for emphasized caption words
    "text_overlay_bg": "#000000CC",  # Semi-transparent for text hooks
}

# ── Typography ─────────────────────────────────────────
FONTS = {
    "title": "DejaVuSans-Bold.ttf",      # Scene titles
    "body": "DejaVuSans.ttf",            # Body text / captions
    "lower_third": "DejaVuSans-Bold.ttf", # Lower third text
    "stat": "DejaVuSans-Bold.ttf",       # Statistics overlay
    "caption": "DejaVuSans-Bold.ttf",    # Burned-in captions
}

# Default font size (scaled for 1080x1920 vertical canvas)
FONT_SIZES = {
    "title": 64,
    "subtitle": 42,
    "body": 34,
    "caption": 65,              # Large for mobile readability (2026 standard)
    "caption_min": 55,          # Minimum caption size
    "lower_third_name": 34,
    "lower_third_title": 26,
    "watermark": 22,
    "text_overlay": 48,         # Text overlay hooks ("Wait for it...")
}

# ── Video Settings (YouTube Shorts 9:16 Vertical — 2026 Optimized) ──
VIDEO_CONFIG = {
    "width": getattr(settings, "video_width", 1080),
    "height": getattr(settings, "video_height", 1920),
    "fps": 60,                  # 60fps for smoother mobile playback — less "swipe-worthy"
    "codec": "libx264",
    "audio_codec": "aac",
    "audio_bitrate": "192k",
    "video_bitrate": "15M",     # Higher bitrate for 60fps
    "pixel_format": "yuv420p",
    "preset": "medium",
    "crf": 15,                  # Sharper quality for high-DPI mobile screens
}

# ── Transition Settings ────────────────────────────────
TRANSITIONS = {
    "default": "crossfade",
    "crossfade_duration": 0.2,   # Faster transitions for pacing
    "fade_in_duration": 0.0,     # No fade in — start instantly
    "fade_out_duration": 0.0,    # No fade out — loop seamlessly
}

# ── Lower Third Settings (Vertical Safe Zone) ─────────
LOWER_THIRD = {
    "position_x": 40,           # pixels from left (centered margin)
    "position_y": 1320,         # vertical safe zone (above mobile UI bar)
    "padding": 20,
    "bar_height": 6,            # accent bar height
    "bar_color": COLORS["accent"],
    "bg_color": "#070F1ECC",    # High contrast semi-transparent deep navy
    "text_color": COLORS["text_primary"],
    "duration": 4.0,            # seconds to show
    "fade_duration": 0.3,
}

# ── Caption Settings (Burned-in Kinetic Captions — 2026 Standard) ──
CAPTION_CONFIG = {
    "font_size": 65,            # Large for mobile readability
    "font_color": "#FFFFFF",    # White text
    "highlight_color": "#FFD700",  # Gold for emphasized words
    "stroke_color": "#000000",  # Black stroke for contrast
    "stroke_width": 4,          # Thick stroke for readability over any background
    "bg_color": None,           # No background box (stroke-only style is 2026 trend)
    "position_y": 960,          # Center of screen (safe zone)
    "max_words_per_line": 4,    # Short lines for readability
    "animation": "word_by_word", # Kinetic: reveal word by word
    "shadow_offset": 3,         # Drop shadow for depth
}

# ── Text Overlay Hook Settings ─────────────────────────
TEXT_OVERLAY_CONFIG = {
    "font_size": 48,
    "font_color": "#FFFFFF",
    "bg_color": "#000000AA",    # Semi-transparent black pill
    "border_radius": 16,
    "position_y": 480,          # Upper third of screen
    "padding_x": 32,
    "padding_y": 16,
    "duration": 2.0,            # Show for 2 seconds
    "fade_in": 0.15,            # Quick pop-in
}

# ── Intro/Outro (REMOVED — 2026 Algorithm: every second is content) ──
INTRO_DURATION = 0.0   # NO INTRO — jump straight into hook
OUTRO_DURATION = 0.0   # NO OUTRO — loop seamlessly back to start
