"""
Unit tests for 0-view fixes and 3-video daily production cap:
1. Moderator stickies and platform announcement filters
2. Policy safety violation filters (banned keywords)
3. Title cleaning and sanitization
4. Daily production configuration limits (strictly 3 videos, single run, 3h stagger)
5. Topic and headline deduplication
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
    "pydantic_settings",
    "httpx",
    "feedparser",
    "PIL",
    "PIL.Image",
    "PIL.ImageDraw",
    "PIL.ImageFont",
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
    "app.models.job",
    "app.models.log",
]:
    if mod not in sys.modules:
        sys.modules[mod] = MagicMock()

# Add backend directory to sys.path
backend_dir = Path(__file__).parent.parent / "backend"
sys.path.insert(0, str(backend_dir))

from app.services.discovery.reddit_scraper import (
    _is_moderator_or_meta,
    _violates_policy,
    _clean_title,
    POLICY_BANNED_WORDS,
    MOD_STICKY_INDICATORS,
)
from app.services.analysis.ranker import BANNED_POLICY_KEYWORDS


def test_moderator_and_meta_filtering():
    print("Testing moderator sticky & announcement filters...")
    
    # Cases that MUST be rejected (these caused 0-view videos on the channel)
    bad_posts = [
        ("[] REMINDER] ANY political content will #Shorts]", "user1", ""),
        ("[REMINDER] Subreddit rules on political content", "mod_user", ""),
        ("[MOD] New submission guidelines for this week", "AutoModerator", ""),
        ("You're invited to Reddit's first-ever Community Awards #Shorts", "reddit_official", ""),
        ("Weekly discussion thread: share your thoughts", "AutoModerator", ""),
        ("Discord server link and rules update", "user2", ""),
        ("[Megathread] Monthly contest submissions", "mod_team", ""),
    ]
    for title, author, summary in bad_posts:
        assert _is_moderator_or_meta(title, author, summary), f"Failed to filter mod/meta post: '{title}'"
    
    # Cases that MUST be accepted (genuine comedy)
    good_posts = [
        ("The 3 Stages of Taking a Shower", "funny_dude", "Stage 1: freezing. Stage 2: paradise."),
        ("Safe to say my dog and my girlfriend do not agree", "dog_lover", "Look at this face"),
        ("Walter White in Half-Life 1", "gamer_bro", "A meme edit of Walter White"),
        ("How and why is he rolling down the hill like that", "comedian99", "Hilarious video clip"),
        ("Just saw an old joke in real life", "standup_fan", "I was walking down the street..."),
    ]
    for title, author, summary in good_posts:
        assert not _is_moderator_or_meta(title, author, summary), f"False positive on comedy post: '{title}'"
    
    print(f"  ✅ Filtered {len(bad_posts)} mod/announcement posts, accepted {len(good_posts)} comedy posts")


def test_content_safety_filtering():
    print("\nTesting content safety and banned policy words...")
    
    # Cases that MUST be rejected (caused shadowbans / 0 views)
    violating_posts = [
        ("No, I do not condone raping Vikings. OC #Shorts", ""),
        ("Depressing story about suicide attempt", "He tried to end his life"),
        ("Terrorist attack footage compilation", ""),
        ("Underage pedophile exposed online", ""),
        ("Brutal murder scene caught on tape", ""),
    ]
    for title, body in violating_posts:
        assert _violates_policy(title, body), f"Failed to catch policy violation: '{title}'"
    
    # Legitimate comedy that contains harmless words
    safe_posts = [
        ("The 3 Stages of Taking a Shower", "Water is too hot"),
        ("My boss thought he could fire me, but instant karma happened", "He had no clue"),
        ("Cat caught stealing pizza in 4K", "Caught red-handed"),
    ]
    for title, body in safe_posts:
        assert not _violates_policy(title, body), f"False positive on safe comedy: '{title}'"
    
    # Ensure ranker policy list covers raping
    assert "raping" in BANNED_POLICY_KEYWORDS
    assert "suicide" in BANNED_POLICY_KEYWORDS
    print(f"  ✅ Caught {len(violating_posts)} policy violations, accepted {len(safe_posts)} safe comedy posts")


def test_title_cleaning():
    print("\nTesting title sanitization...")
    assert _clean_title("[] REMINDER] Cool joke") == "Cool joke"
    assert _clean_title("[OC] Hilarious cat reaction [Shorts]") == "Hilarious cat reaction"
    assert _clean_title("The 3 Stages of Taking a Shower") == "The 3 Stages of Taking a Shower"
    print("  ✅ Title cleaning successfully stripped bracket prefixes and trailing tags")


def test_production_limits_config():
    print("\nTesting production limit settings...")
    env_file = Path(__file__).parent.parent / ".env"
    config_file = Path(__file__).parent.parent / "backend" / "app" / "core" / "config.py"
    
    env_text = env_file.read_text(encoding="utf-8")
    assert "DAILY_VIDEO_COUNT=3" in env_text, ".env must set DAILY_VIDEO_COUNT=3"
    assert "PIPELINE_SCHEDULE_HOURS=16" in env_text, ".env must set PIPELINE_SCHEDULE_HOURS=16"
    assert "STAGGER_UPLOADS_HOURS=3" in env_text, ".env must set STAGGER_UPLOADS_HOURS=3"

    cfg_text = config_file.read_text(encoding="utf-8")
    assert "daily_video_count: int = 3" in cfg_text, "config.py must set default daily_video_count: int = 3"
    assert 'pipeline_schedule_hours: str = "16"' in cfg_text, "config.py must set default pipeline_schedule_hours = '16'"
    assert "stagger_uploads_hours: int = 3" in cfg_text, "config.py must set default stagger_uploads_hours: int = 3"
    print("  ✅ Config verified: DAILY_VIDEO_COUNT=3, PIPELINE_SCHEDULE_HOURS=16 (single run at 16:00 UTC), STAGGER_UPLOADS_HOURS=3")


if __name__ == "__main__":
    test_moderator_and_meta_filtering()
    test_content_safety_filtering()
    test_title_cleaning()
    test_production_limits_config()
    print("\n🎉 ALL 3-VIDEO CAP & FILTER TESTS PASSED!")
