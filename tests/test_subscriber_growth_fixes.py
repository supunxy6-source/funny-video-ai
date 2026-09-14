"""
Unit tests for subscriber growth fixes:
1. Thumbnail badges & CTR scoring
2. Subscribe CTA overlay config
3. SEO optimizer subscribe links & pinned comments
4. Entertainment script prompts retention triggers
"""

import sys
from pathlib import Path
from unittest.mock import MagicMock

# Mock out heavy database and environment dependencies
for mod in [
    "sqlalchemy",
    "sqlalchemy.orm",
    "sqlalchemy.ext.asyncio",
    "pydantic",
    "PIL",
    "PIL.Image",
    "PIL.ImageDraw",
    "PIL.ImageFont",
    "app.core.config",
    "app.db",
    "app.db.base",
    "app.db.session",
    "app.models",
    "app.models.user",
    "app.models.article",
    "app.models.source",
    "app.models.script",
    "app.models.scene",
    "app.models.video",
    "app.models.upload",
    "app.models.thumbnail",
    "app.services.visuals.image_generator",
]:
    if mod not in sys.modules:
        sys.modules[mod] = MagicMock()

sys.modules["app.core.config"].settings.content_mode = "entertainment"
sys.modules["app.core.config"].settings.generated_dir = "generated"

# Add backend directory to sys.path
backend_dir = Path(__file__).parent.parent / "backend"
sys.path.insert(0, str(backend_dir))

from app.services.thumbnail.generator import BADGE_STYLES, ThumbnailGenerator
from app.services.editor.assets import SUBSCRIBE_OVERLAY_CONFIG
from app.services.scriptwriter.prompts import THUMBNAIL_PROMPT_TEMPLATE
from app.services.scriptwriter.entertainment_prompts import (
    STORY_SYSTEM_PROMPT,
    MICRO_SHORTS_PROMPT,
    ENTERTAINMENT_SEO_DESCRIPTION_PROMPT,
)
from app.services.youtube.uploader import _extract_from_json_text


def test_thumbnail_comedy_badges():
    print("Testing thumbnail comedy badges...")
    for badge in BADGE_STYLES:
        text = badge["text"]
        assert not any(bad in text for bad in ["BREAKING", "ALERT", "URGENT"]), (
            f"Found news badge: {text}"
        )
    print(f"  ✅ All {len(BADGE_STYLES)} badges are comedy-focused: {[b['text'] for b in BADGE_STYLES]}")


def test_ctr_scoring():
    print("\nTesting CTR prediction with comedy keywords...")
    gen = ThumbnailGenerator()
    score_comedy = gen._predict_ctr("Funniest reaction fail caught on camera? 💀", 0, BADGE_STYLES[0])
    score_boring = gen._predict_ctr("Daily briefing summary report", 1, None)
    assert score_comedy > score_boring, f"Comedy score {score_comedy} should exceed boring score {score_boring}"
    print(f"  ✅ Comedy title scored {score_comedy:.2f} vs boring title {score_boring:.2f}")


def test_subscribe_overlay_config():
    print("\nTesting subscribe CTA overlay config...")
    assert "text" in SUBSCRIBE_OVERLAY_CONFIG
    assert "Stateside Smiles" in SUBSCRIBE_OVERLAY_CONFIG["text"]
    assert SUBSCRIBE_OVERLAY_CONFIG["duration"] >= 2.0
    print(f"  ✅ Subscribe overlay config valid: text='{SUBSCRIBE_OVERLAY_CONFIG['text']}', duration={SUBSCRIBE_OVERLAY_CONFIG['duration']}s")


def test_subscribe_urls_handle():
    print("\nTesting YouTube handle in subscribe URLs...")
    # Check entertainment SEO description prompt
    assert "@Smiles-x4g" in ENTERTAINMENT_SEO_DESCRIPTION_PROMPT, "Missing @Smiles-x4g in description prompt"
    assert "@StatesideSmiles" not in ENTERTAINMENT_SEO_DESCRIPTION_PROMPT, "Old handle found in description prompt"

    # Check thumbnail prompt template
    assert "comedy" in THUMBNAIL_PROMPT_TEMPLATE.lower(), "Thumbnail prompt template missing comedy keyword"
    assert "news" not in THUMBNAIL_PROMPT_TEMPLATE.lower(), "Thumbnail prompt template contains news keyword"

    # Check uploader fallback
    fallback_desc = _extract_from_json_text("", "description")
    assert "@Smiles-x4g" in fallback_desc, f"Uploader fallback description missing @Smiles-x4g: {fallback_desc}"
    assert "sub_confirmation=1" in fallback_desc, "Uploader fallback missing sub_confirmation=1"
    print("  ✅ All subscribe URLs correctly point to @Smiles-x4g?sub_confirmation=1")


def test_retention_prompts():
    print("\nTesting 9-second retention triggers in prompts...")
    assert "9-SECOND" in STORY_SYSTEM_PROMPT or "9-second" in STORY_SYSTEM_PROMPT.lower()
    assert "second 5-7" in STORY_SYSTEM_PROMPT.lower() or "5-7 second" in STORY_SYSTEM_PROMPT.lower()
    assert "NO generic" in MICRO_SHORTS_PROMPT or "no generic" in MICRO_SHORTS_PROMPT.lower()
    print("  ✅ Retention guidelines and visual prompts explicitly target the 9-second drop-off")


if __name__ == "__main__":
    test_thumbnail_comedy_badges()
    test_ctr_scoring()
    test_subscribe_overlay_config()
    test_subscribe_urls_handle()
    test_retention_prompts()
    print("\n🎉 ALL SUBSCRIBER GROWTH FIX TESTS PASSED!")
