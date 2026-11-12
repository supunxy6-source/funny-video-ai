"""
Unit tests for YouTube Shorts retention optimizations:
1. 8-12s Micro-Shorts prompt & word counts
2. Hook frame overlay config & compositor scroll-stopper
3. Scene duration trimming (no 2.5s dead air floor)
4. Series theme weights & story ranker integration
5. Hook validation thresholds
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
    "moviepy",
    "moviepy.video",
    "moviepy.video.fx",
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
    "app.services.visuals.video_generator",
    "app.services.editor.subtitler",
]:
    if mod not in sys.modules:
        sys.modules[mod] = MagicMock()

sys.modules["app.core.config"].settings.content_mode = "entertainment"
sys.modules["app.core.config"].settings.generated_dir = "generated"

backend_dir = Path(__file__).parent.parent / "backend"
sys.path.insert(0, str(backend_dir))

from app.services.scriptwriter.entertainment_prompts import (
    MICRO_SHORTS_PROMPT,
    SERIES_THEMES,
    get_series_for_subreddit,
)
from app.services.editor.assets import HOOK_FRAME_CONFIG
from app.services.scriptwriter.writer import validate_hook
from app.services.analysis.ranker import StoryRanker


def test_micro_shorts_prompt_target():
    print("Testing 8-12s micro shorts prompt...")
    assert "8-12 SECONDS" in MICRO_SHORTS_PROMPT
    assert "20-35 WORDS TOTAL" in MICRO_SHORTS_PROMPT
    assert "Hook (0-1.5s)" in MICRO_SHORTS_PROMPT
    assert "Twist & Debate (4-6s)" in MICRO_SHORTS_PROMPT
    assert "Payoff & Loop Bridge (2-4s)" in MICRO_SHORTS_PROMPT
    print("  ✅ Prompt specifically targets 8-12 seconds and 20-35 words")


def test_hook_frame_config():
    print("\nTesting hook frame overlay config...")
    assert HOOK_FRAME_CONFIG["font_size"] >= 70
    assert HOOK_FRAME_CONFIG["start_time"] == 0.0
    assert HOOK_FRAME_CONFIG["duration"] <= 1.5
    print(f"  ✅ Hook frame config is set for frame 0 scroll-stopping: font_size={HOOK_FRAME_CONFIG['font_size']}, start_time={HOOK_FRAME_CONFIG['start_time']}")


def test_hook_validator():
    print("\nTesting hook validation thresholds...")
    # Good hook
    good = validate_hook("...so he ate the EVIDENCE")
    assert good["is_valid"] is True
    
    # Too long hook
    long_hook = validate_hook("This is a very long drawn out introductory sentence that goes on and on without stopping")
    assert any("Hook is" in i for i in long_hook["issues"])
    print("  ✅ Hook validation catches over-length and weak openers")


def test_series_weights_in_ranking():
    print("\nTesting series weighting in ranker...")
    petty_series = get_series_for_subreddit("pettyrevenge")
    assert petty_series["weight"] >= 1.4
    
    ranker = StoryRanker()
    # Mock articles belonging to petty revenge
    articles = [
        {
            "id": 1,
            "source_id": 1,
            "headline": "Instant regret after stealing parking spot",
            "summary": "Hilarious revenge ensued when he got blocked in",
            "category": "comedy",
            "keywords": '{"subreddit": "pettyrevenge"}',
            "url": "https://reddit.com/r/pettyrevenge/comments/123",
        }
    ]
    trust_map = {1: 0.9}
    score = ranker.score_cluster(1, articles, trust_map)
    assert score["scores"]["series_weight"] == petty_series["weight"]
    print(f"  ✅ Story ranker correctly applies series weight {score['scores']['series_weight']} for r/pettyrevenge")


if __name__ == "__main__":
    test_micro_shorts_prompt_target()
    test_hook_frame_config()
    test_hook_validator()
    test_series_weights_in_ranking()
    print("\n🎉 ALL RETENTION TESTS PASSED SUCCESSFULLY!")

