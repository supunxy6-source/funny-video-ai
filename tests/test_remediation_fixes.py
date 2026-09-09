"""
Unit tests to verify deduplication and safety sanitization fixes.
"""

import sys
from pathlib import Path
from unittest.mock import MagicMock

# Mock out heavy database and environment dependencies for unit testing logic
for mod in ["sqlalchemy", "sqlalchemy.orm", "sqlalchemy.ext.asyncio", "pydantic", "app.core.config", "app.db.session", "app.models.article", "app.models.source", "app.models.script", "app.models.scene", "app.models.video", "app.models.upload", "app.services.scriptwriter.writer"]:
    if mod not in sys.modules:
        sys.modules[mod] = MagicMock()

sys.modules["app.services.scriptwriter.writer"].sanitize_title = lambda x: x

# Add backend directory to sys.path
backend_dir = Path(__file__).parent.parent / "backend"
sys.path.insert(0, str(backend_dir))

from app.services.seo.optimizer import format_shorts_title, _sanitize_policy_words
from app.services.analysis.ranker import StoryRanker, BANNED_POLICY_KEYWORDS, COMEDY_VIRAL_KEYWORDS


def test_format_shorts_title():
    print("Testing format_shorts_title...")

    # Test 1: Policy sanitization
    raw1 = "That's incitement to murder #Shorts"
    formatted1 = format_shorts_title(raw1)
    assert "murder" not in formatted1.lower(), f"Failed policy check: {formatted1}"
    print(f"  ✅ Policy sanitize: '{raw1}' -> '{formatted1}'")

    # Test 2: NSFW policy sanitization
    raw2 = "Humping The Rainbow #Shorts"
    formatted2 = format_shorts_title(raw2)
    assert "humping" not in formatted2.lower(), f"Failed NSFW check: {formatted2}"
    print(f"  ✅ NSFW sanitize: '{raw2}' -> '{formatted2}'")

    # Test 3: Truncated ending word avoidance (should not end with dangling preposition/conjunction)
    raw3 = "The sidewalk was replaced and hopscotch is"
    formatted3 = format_shorts_title(raw3, max_base_len=42)
    assert not formatted3.lower().startswith("the sidewalk was replaced and hopscotch is #shorts"), f"Failed ending check: {formatted3}"
    assert not formatted3.endswith("is #Shorts"), f"Ended on 'is': {formatted3}"
    print(f"  ✅ Bad ending removal: '{raw3}' -> '{formatted3}'")

    # Test 4: Length and #Shorts tag
    raw4 = "He really built a car with TWO front ends"
    formatted4 = format_shorts_title(raw4)
    assert formatted4.endswith("#Shorts"), f"Missing #Shorts: {formatted4}"
    print(f"  ✅ Normal format: '{raw4}' -> '{formatted4}'")


def test_ranker_safety_and_keywords():
    print("\nTesting ranker safety and viral scoring...")
    ranker = StoryRanker()

    # Banned cluster test
    banned_articles = [
        {"headline": "Suspect arrested for murder of local official", "summary": "Police investigated the killing."}
    ]
    score_banned = ranker._score_viral_potential(banned_articles)
    assert score_banned == 0.0, f"Expected 0.0 for banned cluster, got {score_banned}"
    print(f"  ✅ Banned cluster rejected with score: {score_banned}")

    # Comedy viral cluster test
    comedy_articles = [
        {"headline": "Hilarious cat fail caught on camera instant regret", "summary": "Try not to laugh at this epic fail."}
    ]
    score_comedy = ranker._score_viral_potential(comedy_articles)
    assert score_comedy > 0.5, f"Expected high score for comedy viral, got {score_comedy}"
    print(f"  ✅ Comedy viral cluster scored high: {score_comedy}")


if __name__ == "__main__":
    test_format_shorts_title()
    test_ranker_safety_and_keywords()
    print("\n🎉 ALL TESTS PASSED SUCCESSFULLY!")
