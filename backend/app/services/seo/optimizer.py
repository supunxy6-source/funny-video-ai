"""
Stateside Smiles — SEO Optimizer (Views-Optimized Edition)

Generates SEO-optimized titles, descriptions, tags, chapters,
and pinned comments for YouTube videos using LLM-powered optimization.

Supports both entertainment (comedy) and news content modes.
VIEWS OPTIMIZATION: Multi-variant title scoring, power-word CTR heuristics,
trend-aligned tags, and engagement-bait pinned comments.
"""

import json
import logging
import random
import re
from datetime import datetime, timezone
from typing import Optional

from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession

from app.core.config import settings
from app.db.session import async_session_factory
from app.models.script import Script
from app.models.scene import Scene
from app.models.video import Video
from app.models.upload import Upload
from app.services.scriptwriter.writer import LLMClient
from app.services.scriptwriter.prompts import (
    SEO_TITLE_PROMPT,
    SEO_DESCRIPTION_PROMPT,
    SEO_TAGS_PROMPT,
)
from app.services.scriptwriter.entertainment_prompts import (
    ENTERTAINMENT_SEO_TITLE_PROMPT,
    ENTERTAINMENT_SEO_DESCRIPTION_PROMPT,
    ENTERTAINMENT_SEO_TAGS_PROMPT,
)

logger = logging.getLogger(__name__)

# Power words that boost CTR — used for title scoring
# Mode-aware: entertainment uses comedy words, news uses urgency words
NEWS_POWER_WORDS = {
    "tier1": [
        "shocking", "exposed", "urgent", "breaking", "warning", "banned",
        "insane", "unbelievable", "massive", "emergency", "critical",
        "catastrophic", "explosive", "devastating",
    ],
    "tier2": [
        "secret", "hidden", "revealed", "truth", "actually", "real",
        "caught", "leaked", "discovered", "confirmed", "impossible",
        "terrifying", "incredible", "dramatic",
    ],
    "tier3": [
        "just", "now", "today", "update", "live", "alert", "new",
        "first", "latest", "official", "major", "huge", "wild",
    ],
}

ENTERTAINMENT_POWER_WORDS = {
    "tier1": [  # Highest impact — comedy & viral
        "funniest", "hilarious", "impossible", "insane", "epic",
        "unbelievable", "craziest", "wildest", "best", "worst",
        "cursed", "blessed", "iconic", "legendary",
    ],
    "tier2": [  # High impact — engagement
        "fail", "wins", "wholesome", "relatable", "accurate",
        "actually", "lowkey", "deadass", "fr", "caught",
        "exposed", "real", "valid", "goated",
    ],
    "tier3": [  # Medium impact — trends
        "today", "daily", "new", "latest", "trending",
        "viral", "memes", "compilation", "review", "challenge",
        "pov", "reaction", "tier",
    ],
}


def _get_power_words() -> dict:
    """Get content-mode-appropriate power words."""
    from app.core.config import settings
    if getattr(settings, "content_mode", "entertainment") == "entertainment":
        return ENTERTAINMENT_POWER_WORDS
    return NEWS_POWER_WORDS


POWER_WORDS = _get_power_words()


class SEOOptimizer:
    """Generates SEO-optimized metadata for YouTube uploads."""

    def __init__(self):
        self.llm = LLMClient()

    async def optimize(self, script: dict, scenes: list[dict]) -> dict:
        """
        Generate complete SEO metadata for a video.

        Returns dict with title, description, tags, hashtags, chapters, pinned_comment.
        """
        topic = script.get("topic_summary", "")
        script_title = script.get("title", "")
        content_mode = getattr(settings, "content_mode", "entertainment")
        category = "Comedy" if content_mode == "entertainment" else script.get("category", "News")

        # Generate SEO title — now generates 3 variants and picks the best
        seo_title = await self._generate_title(topic, script_title)

        # Generate chapters from scenes
        chapters = self._generate_chapters(scenes)

        # Generate description
        scene_titles = [s.get("title", "") for s in scenes]
        description = await self._generate_description(
            seo_title, topic, scene_titles, chapters
        )

        # Generate tags with YouTube Shorts tags prepended
        tags = await self._generate_tags(seo_title, topic, category)

        if content_mode == "entertainment":
            base_tags = [
                "funny", "memes", "comedy", "try not to laugh",
                "funny videos", "meme compilation", "funny memes",
                "viral", "trending",
            ]
        else:
            base_tags = [
                "shorts", "youtubeshorts", "ytshorts", "short",
                "viral shorts", "trending shorts", "news shorts", "breaking news",
            ]
        for st in reversed(base_tags):
            if st not in tags:
                tags.insert(0, st)

        now = datetime.now(timezone.utc)
        if content_mode == "entertainment":
            time_tags = [
                f"memes {now.strftime('%B').lower()} {now.year}",
                f"funny videos {now.year}",
                "memes today",
                "trending memes",
            ]
        else:
            time_tags = [
                f"news {now.strftime('%B').lower()} {now.year}",
                f"news today {now.year}",
                "news today",
                "trending today",
            ]
        for tt in time_tags:
            if tt not in tags:
                tags.append(tt)

        # Generate hashtags — expanded for Shorts discovery with niche tags
        if content_mode == "entertainment":
            base_hashtags = [
                "#Shorts", "#Funny", "#Memes", "#Comedy", "#Viral",
                "#Trending", "#TryNotToLaugh", "#StatesideSmiles",
            ]
        else:
            base_hashtags = [
                "#Shorts", "#News", "#Trending", "#BreakingNews",
                "#WorldNews", "#NewsToday", "#ViralNews",
            ]
        topic_words = [w.strip() for w in topic.split() if len(w.strip()) >= 4]
        niche_hashtags = []
        for word in topic_words[:3]:
            clean_word = re.sub(r'[^a-zA-Z0-9]', '', word).capitalize()
            if clean_word and len(clean_word) >= 4:
                if content_mode == "entertainment" and any(bad in clean_word.lower() for bad in ["news", "breaking"]):
                    continue
                niche_hashtags.append(f"#{clean_word}")

        if content_mode == "entertainment":
            # Sanitize tags: strictly remove any news keywords from entertainment tags
            tags = [
                t for t in tags
                if not any(bad in t.lower() for bad in ["breaking news", "world news", "news shorts", "news today", "news briefing", "breaking"])
            ]
            extra_hashtags = [
                f"#{tag.replace(' ', '')}"
                for tag in tags if tag not in base_tags and not tag.startswith("#")
                and not any(bad in tag.lower() for bad in ["breakingnews", "news", "worldnews", "breaking"])
            ][:5]
            hashtags = [
                h for h in list(dict.fromkeys(base_hashtags + niche_hashtags + extra_hashtags))
                if not any(bad in h.lower() for bad in ["breakingnews", "news", "worldnews", "breaking"])
            ]
        else:
            extra_hashtags = [
                f"#{tag.replace(' ', '')}"
                for tag in tags if tag not in base_tags and not tag.startswith("#")
            ][:5]
            hashtags = list(dict.fromkeys(base_hashtags + niche_hashtags + extra_hashtags))

        # Generate engagement-optimized pinned comment with polarizing debate hooks
        pinned_comment = await self._generate_pinned_comment(topic, seo_title)

        # Ensure clean, mobile-safe #Shorts title without mid-word truncation
        clean_title = format_shorts_title(seo_title, max_base_len=42)

        result = {
            "title": clean_title,  # YouTube 100 char limit (mobile sweet spot 35-48 chars)
            "description": description[:5000],  # YouTube 5000 char limit
            "tags": json.dumps(tags[:30]),  # Max 30 tags
            "hashtags": " ".join(hashtags),
            "chapters": chapters,
            "pinned_comment": pinned_comment,
        }

        # Final validation
        result["description"] = _sanitize_description(result["description"])

        logger.info(f"🔍 SEO optimized (Shorts): '{result['title']}' ({len(tags)} tags)")
        return result

    async def _generate_title(self, topic: str, script_title: str) -> str:
        """Generate an SEO-optimized video title.
        
        Now generates 3 variants and picks the one with the highest CTR score.
        """
        content_mode = getattr(settings, "content_mode", "entertainment")
        try:
            if content_mode == "entertainment":
                prompt = ENTERTAINMENT_SEO_TITLE_PROMPT.format(
                    topic=topic,
                    script_title=script_title,
                )
            else:
                prompt = SEO_TITLE_PROMPT.format(
                    topic=topic,
                    script_title=script_title,
                )
            response = await self.llm.generate(prompt, max_tokens=200, temperature=0.9)
            
            # Parse multiple title variants from the response
            variants = [
                line.strip().strip('"').strip("'").strip()
                for line in response.strip().split("\n")
                if line.strip() and len(line.strip()) > 5
            ]
            
            # Remove numbering prefixes like "1. ", "1) ", "- "
            cleaned_variants = []
            for v in variants:
                v = re.sub(r'^[\d]+[.)]\s*', '', v)
                v = re.sub(r'^[-•]\s*', '', v)
                v = v.strip()
                if v and len(v) > 5:
                    cleaned_variants.append(v)
            
            if not cleaned_variants:
                cleaned_variants = [script_title]
            
            # Score each variant and pick the best
            best_title = cleaned_variants[0]
            best_score = -1
            for variant in cleaned_variants[:5]:  # Cap at 5 to avoid runaway
                score = _score_title_ctr(variant)
                logger.debug(f"Title variant CTR score: {score:.3f} — '{variant[:60]}'")
                if score > best_score:
                    best_score = score
                    best_title = variant
            
            logger.info(f"🏆 Best title (CTR={best_score:.3f}): '{best_title[:60]}'")
            
            # If the LLM accidentally returned JSON, try to parse it
            if best_title.startswith("{"):
                try:
                    title_data = json.loads(best_title)
                    if isinstance(title_data, dict) and "title" in title_data:
                        best_title = str(title_data["title"])
                except Exception:
                    pass
            
            # Final sanitization with word boundary protection
            best_title = _sanitize_seo_title(best_title)
            return _truncate_at_word_boundary(best_title, 80)
        except Exception as e:
            logger.warning(f"Title generation failed: {e}")
            # Fallback: use script_title but sanitize it first
            clean = _sanitize_seo_title(script_title)
            return _truncate_at_word_boundary(clean, 80)

    async def _generate_description(
        self,
        title: str,
        topic: str,
        scene_titles: list[str],
        chapters: str,
    ) -> str:
        """Generate a YouTube video description."""
        content_mode = getattr(settings, "content_mode", "entertainment")
        try:
            if content_mode == "entertainment":
                prompt = ENTERTAINMENT_SEO_DESCRIPTION_PROMPT.format(
                    title=title,
                    topic_summary=topic,
                    scene_titles=", ".join(scene_titles),
                )
            else:
                prompt = SEO_DESCRIPTION_PROMPT.format(
                    title=title,
                    topic_summary=topic,
                    scene_titles=", ".join(scene_titles),
                    source_urls="Sources cited in the video",
                )
            description = await self.llm.generate(prompt, max_tokens=1500, temperature=0.7)
            description = description.strip()
            
            # If the LLM accidentally returned JSON, try to parse it
            if description.startswith("{"):
                try:
                    desc_data = json.loads(description)
                    if isinstance(desc_data, dict) and "description" in desc_data:
                        description = str(desc_data["description"])
                except Exception:
                    pass
            
            # Final sanitization
            description = _sanitize_description(description)
            return description
        except Exception as e:
            logger.warning(f"Description generation failed: {e}")
            # Build a clean fallback description with keyword front-loading
            clean_title = _sanitize_seo_title(title)
            now = datetime.now(timezone.utc)
            if content_mode == "entertainment":
                desc = (
                    f"{clean_title}\n\n"
                    f"{topic}\n\n"
                    f"😂 Daily comedy, viral memes & funny stories!\n\n"
                    f"👉 Subscribe to Stateside Smiles for daily laughs: https://youtube.com/@StatesideSmiles?sub_confirmation=1\n\n"
                    f"💬 Which part made you laugh the hardest? Drop your comment below! 👇\n\n"
                    f"#Shorts #Funny #Memes #Comedy #TryNotToLaugh #StatesideSmiles"
                )
            else:
                desc = (
                    f"{clean_title}\n\n"
                    f"{topic}\n\n"
                    f"📰 Get the latest news in 60 seconds — {now.strftime('%B %Y')}\n\n"
                    f"💬 What do you think? Comment below!\n"
                    f"🔔 Follow for daily news updates\n\n"
                    f"#Shorts #News #Trending #BreakingNews #NewsToday"
                )
            return _sanitize_description(desc)

    async def _generate_tags(self, title: str, topic: str, category: str) -> list[str]:
        """Generate YouTube tags."""
        content_mode = getattr(settings, "content_mode", "entertainment")
        try:
            if content_mode == "entertainment":
                prompt = ENTERTAINMENT_SEO_TAGS_PROMPT.format(
                    title=title,
                    topic_summary=topic,
                )
            else:
                prompt = SEO_TAGS_PROMPT.format(
                    title=title,
                    topic_summary=topic,
                    category=category,
                )
            response = await self.llm.generate(prompt, max_tokens=500, temperature=0.7)

            # Parse JSON array
            text = response.strip()
            if text.startswith("```"):
                text = text.split("\n", 1)[1].rsplit("```", 1)[0]
            tags = json.loads(text)
            if content_mode == "entertainment":
                tags = [t.strip() for t in tags if t.strip() and not any(bad in t.lower() for bad in ["news", "breaking"])][:30]
            else:
                tags = [t.strip() for t in tags if t.strip()][:30]
            return tags

        except Exception as e:
            logger.warning(f"Tag generation failed: {e}")
            # Enhanced fallback tags with Shorts discovery and topic keywords
            words = topic.split()[:10]
            now = datetime.now(timezone.utc)
            if content_mode == "entertainment":
                return [
                    "shorts", "youtubeshorts", "ytshorts", "viral shorts",
                    "funny", "memes", "comedy", "try not to laugh",
                    "funny videos", "meme compilation", "funny memes",
                    f"memes {now.strftime('%B').lower()} {now.year}",
                    "trending memes", "stateside smiles",
                ] + [w.lower() for w in words if len(w) > 3 and not any(bad in w.lower() for bad in ["news", "breaking"])]
            else:
                return [
                    "shorts", "youtubeshorts", "ytshorts", "viral shorts",
                    "news", "breaking news", "world news", "news today",
                    f"news {now.strftime('%B').lower()} {now.year}",
                    "trending", "trending today",
                ] + [w.lower() for w in words if len(w) > 3]

    def _generate_chapters(self, scenes: list[dict]) -> str:
        """Generate timestamp chapters from scenes."""
        if not scenes:
            return ""

        chapters = ["0:00 Introduction"]
        current_time = 0

        for scene in scenes:
            duration = scene.get("duration", 60)
            current_time += duration
            minutes = int(current_time // 60)
            seconds = int(current_time % 60)
            title = scene.get("title", f"Scene {scene.get('order', 0)}")
            chapters.append(f"{minutes}:{seconds:02d} {title}")

        return "\n".join(chapters)

    async def _generate_pinned_comment(self, topic: str, title: str) -> str:
        """Generate an engagement-optimized pinned comment with polarizing debate hooks.
        
        Engineered to spark active discussions and debate in the comments.
        When viewers open the comment section to reply, the Short keeps looping
        in the background, pushing Average Percentage Viewed well past 100%.
        """
        clean_topic = topic[:100].strip() if topic else "this video"
        clean_title = (title or "").lower()
        content_mode = getattr(settings, "content_mode", "entertainment")
        
        # 1. Try dynamic LLM debate question generation
        try:
            prompt = (
                f"Create ONE ultra-engaging, polarizing debate question for a YouTube Short comment section.\n"
                f"Topic: {topic}\n"
                f"Title: {title}\n"
                f"Rules:\n"
                f"- Must be a 50/50 dilemma, moral question, or 'Would you do this' challenge that forces viewers to comment.\n"
                f"- Maximum 15 words.\n"
                f"- Include 1 emoji and point down 👇.\n"
                f"Output ONLY the question text, no quotes, no markdown."
            )
            llm_response = await self.llm.generate(prompt, max_tokens=60, temperature=0.9)
            debate_q = llm_response.strip().strip('"\'')
            if len(debate_q) > 12 and not debate_q.startswith("{"):
                return (
                    f"🔥 {debate_q}\n\n"
                    f"💬 Drop your honest thoughts below — best reply gets pinned! 📌\n"
                    f"❤️ LIKE if this made you smile\n"
                    f"🔔 Subscribe to Stateside Smiles for daily laughs!"
                )
        except Exception as e:
            logger.debug(f"LLM pinned comment generation fallback: {e}")

        # 2. Intelligent topic-matched debate hook fallback
        if content_mode == "entertainment":
            topic_str = f"{clean_title} {clean_topic.lower()}"
            if any(w in topic_str for w in ["revenge", "petty", "karen", "neighbor", "boss", "roommate", "coworker"]):
                debate_hook = "Who was 100% in the wrong here? Drop 1 for OP or 2 for the other person 👇"
            elif any(w in topic_str for w in ["floor", "scary", "fall", "jump", "dare", "heights", "glass", "challenge"]):
                debate_hook = "Be completely honest: would you have done this for $10,000? 💀👇"
            elif any(w in topic_str for w in ["money", "cost", "scam", "job", "fired", "quit", "work", "price"]):
                debate_hook = "Would you have walked out on the spot or taken the deal? Debate below 👇"
            elif any(w in topic_str for w in ["smart", "iq", "genius", "hack", "trick"]):
                debate_hook = "Is this a 200 IQ move or completely unhinged? Debate below 💀👇"
            else:
                debate_hooks = [
                    "Be honest: what would YOU have done in this exact situation? 👇",
                    "Is this totally justified or did they take it way too far? Drop your take 👇",
                    "Would you have survived this without laughing? Be honest 💀👇",
                    "Rate how chaotic this was from 1 to 10 below 👇",
                    "Have you ever experienced something this ridiculous? Best reply gets pinned! 📌👇",
                ]
                debate_hook = random.choice(debate_hooks)
            
            return (
                f"🔥 {debate_hook}\n\n"
                f"💬 Drop your comment below — best one gets pinned! 📌\n"
                f"❤️ LIKE if this made your day better\n"
                f"🔔 Subscribe to Stateside Smiles for daily viral laughs!"
            )
        else:
            news_debates = [
                "Who do you think is really responsible for this? Drop your take 👇",
                "Do you believe this will make things better or worse? Be honest 👇",
                "How would this affect you if it happened in your city? 👇",
                "Which side do you agree with? Vote 1 or 2 below 👇",
            ]
            debate_q = random.choice(news_debates)
            return (
                f"🔥 {debate_q}\n\n"
                f"💬 Reply with your unfiltered opinion — best perspective gets pinned! 📌\n"
                f"❤️ LIKE to boost verified coverage\n"
                f"🔔 Subscribe for daily 30-second news breakdowns"
            )


def _truncate_at_word_boundary(text: str, max_len: int) -> str:
    """Truncate text cleanly at word boundaries to avoid slicing words in half (e.g. 'walk' -> 'wa')."""
    if not text or len(text) <= max_len:
        return text.strip() if text else ""
    truncated = text[:max_len]
    last_space = truncated.rfind(" ")
    if last_space > 0:
        return truncated[:last_space].rstrip(",.-:;?! ")
    return truncated.rstrip(",.-:;?! ")


def format_shorts_title(raw_title: str, max_base_len: int = 42) -> str:
    """Format an ultra-clean YouTube Shorts title that fits on mobile screens without truncation.
    
    YouTube Shorts mobile UI truncates titles around 45-50 characters with ellipsis.
    This ensures clean word-boundary truncation and appends '#Shorts'.
    """
    clean = _sanitize_seo_title(raw_title)
    # Strip any existing #shorts tag (case-insensitive)
    clean_no_tag = re.sub(r'#shorts\b', '', clean, flags=re.IGNORECASE).strip()
    clean_no_tag = clean_no_tag.rstrip(",.-:;?! ")
    
    # Truncate base title at word boundary
    safe_base = _truncate_at_word_boundary(clean_no_tag, max_base_len)
    return f"{safe_base} #Shorts"


def _score_title_ctr(title: str) -> float:
    """Score a title for predicted click-through rate.
    
    Uses a multi-signal heuristic based on YouTube Shorts best practices:
    - Power words presence and tier
    - Title length (sweet spot 28-45 chars for mobile Shorts, never truncated)
    - Number presence (boosts CTR ~30%)
    - Question marks (curiosity gap)
    - Emotional triggers
    - #Shorts tag presence
    - Severe penalty for incomplete/chopped trailing words
    """
    score = 0.5
    title_lower = title.lower()
    
    # Power words — tiered scoring
    for word in POWER_WORDS["tier1"]:
        if word in title_lower:
            score += 0.15
            break  # Only count best tier once
    for word in POWER_WORDS["tier2"]:
        if word in title_lower:
            score += 0.10
            break
    for word in POWER_WORDS["tier3"]:
        if word in title_lower:
            score += 0.05
            break
    
    # Title length — sweet spot is 28-45 chars for Shorts mobile display
    title_len = len(title)
    if 28 <= title_len <= 45:
        score += 0.20  # Optimal mobile length
    elif 20 <= title_len < 28:
        score += 0.12  # Short & punchy
    elif 45 < title_len <= 55:
        score += 0.05  # Acceptable
    else:
        score -= 0.15  # Too long — truncates with '...' on mobile screens
    
    # Number presence (e.g., "47 people", "$2 billion", "200 IQ")
    if re.search(r'\d', title):
        score += 0.10
    
    # Question mark — creates curiosity gap
    if "?" in title:
        score += 0.08
    
    # Exclamation mark — urgency
    if "!" in title:
        score += 0.03
    
    # Emoji presence (moderate boost)
    if any(ord(c) > 0x1F600 for c in title):
        score += 0.03
    
    # #Shorts tag present
    if "#shorts" in title_lower:
        score += 0.05
    
    # Penalty: ALL CAPS (looks spammy)
    caps_ratio = sum(1 for c in title if c.isupper()) / max(len(title), 1)
    if caps_ratio > 0.6:
        score -= 0.10
    
    # Penalty: generic/boring words
    boring_words = ["update", "briefing", "report", "summary", "daily", "weekly"]
    for word in boring_words:
        if word in title_lower:
            score -= 0.05
            break

    # Penalty for truncated/chopped trailing word (e.g., 'wa' instead of 'walk')
    title_without_shorts = re.sub(r'#shorts\b', '', title, flags=re.IGNORECASE).strip()
    words = title_without_shorts.split()
    if words:
        last_word = words[-1].strip(".,!?:;\"'()[]")
        common_short_words = {"a", "i", "in", "on", "to", "at", "no", "he", "it", "so", "up", "do", "my", "we", "by", "is", "or", "an"}
        if len(last_word) <= 2 and last_word.lower() not in common_short_words:
            score -= 0.25  # Severe penalty for truncated word fragment
    
    return min(max(score, 0.1), 1.0)


async def optimize_seo(video_id: int, scheduled_at: datetime = None) -> int:
    """
    Main SEO optimization entry point called by Celery task.
    Generates SEO metadata and creates an upload record.

    Returns the upload record ID.
    """
    optimizer = SEOOptimizer()

    async with async_session_factory() as db:
        video = await db.get(Video, video_id)
        if not video:
            raise ValueError(f"Video {video_id} not found")

        script = await db.get(Script, video.script_id)
        if not script:
            raise ValueError(f"Script not found for video {video_id}")

        # Fetch scenes
        result = await db.execute(
            select(Scene)
            .where(Scene.script_id == script.id)
            .order_by(Scene.order)
        )
        scenes = result.scalars().all()

        script_dict = {
            "title": script.title,
            "topic_summary": script.topic_summary,
            "content": script.content,
        }
        scene_dicts = [
            {
                "order": s.order,
                "title": s.title,
                "scene_type": s.scene_type,
                "duration": s.duration,
            }
            for s in scenes
        ]

        seo_data = await optimizer.optimize(script_dict, scene_dicts)

        # Final safeguard: ensure title and description are never raw JSON
        upload_title = seo_data["title"]
        upload_description = seo_data["description"]

        # If title still looks like JSON, forcefully sanitize
        if upload_title and upload_title.strip()[:1] in ('{', '['):
            logger.warning(f"⚠️ SEO title is JSON — sanitizing: {upload_title[:80]}...")
            upload_title = _sanitize_seo_title(upload_title)
        
        # If description still looks like JSON, forcefully sanitize
        if upload_description and upload_description.strip()[:1] in ('{', '['):
            logger.warning(f"⚠️ SEO description is JSON — sanitizing")
            upload_description = _sanitize_description(upload_description)

        # Create upload record
        upload = Upload(
            video_id=video_id,
            title=upload_title,
            description=upload_description,
            tags=seo_data["tags"],
            hashtags=seo_data.get("hashtags"),
            chapters=seo_data.get("chapters"),
            pinned_comment=seo_data.get("pinned_comment"),
            category_id=settings.youtube_category_id,
            privacy_status=getattr(settings, "youtube_default_privacy", "public"),
            status="pending",
            scheduled_at=scheduled_at,
        )
        db.add(upload)
        await db.flush()
        await db.commit()

        logger.info(f"💾 Upload record created: ID={upload.id}")
        return upload.id


def _sanitize_seo_title(raw_title: str) -> str:
    """Sanitize a title to ensure it's clean human-readable text for YouTube.
    
    Imports the main sanitize_title from scriptwriter if available,
    otherwise uses a local implementation.
    """
    try:
        from app.services.scriptwriter.writer import sanitize_title
        return sanitize_title(raw_title)
    except ImportError:
        pass

    # Local fallback implementation
    if not raw_title or not raw_title.strip():
        today = datetime.now(timezone.utc).strftime("%B %d, %Y")
        return f"Daily News Briefing — {today}"

    title = raw_title.strip()

    # Extract title from JSON if needed
    if title.startswith("{") or title.startswith("["):
        match = re.search(r'"title"\s*:\s*"([^"]+)"', title)
        if match:
            title = match.group(1).strip()
        else:
            today = datetime.now(timezone.utc).strftime("%B %d, %Y")
            title = f"Daily News Briefing — {today}"

    title = title.strip('"\'{}')
    title = re.sub(r'[`*_~]', '', title)
    title = re.sub(r'\s+', ' ', title).strip()

    if len(title) > 100:
        title = title[:97].rsplit(" ", 1)[0] + "..."

    return title


def _sanitize_description(raw_desc: str) -> str:
    """Sanitize a description to ensure it's clean human-readable text for YouTube.
    
    Strips raw JSON structures from descriptions while preserving
    intentional formatting like chapters and bullet points.
    """
    if not raw_desc or not raw_desc.strip():
        return "Daily news briefing covering global stories and verified developments. Subscribe for updates."

    desc = raw_desc.strip()

    # If the entire description is a JSON object, extract useful fields
    if desc.startswith("{"):
        try:
            data = json.loads(desc)
            if isinstance(data, dict):
                # Try to extract a description field
                for field in ["description", "text", "content", "summary"]:
                    val = data.get(field, "")
                    if val and isinstance(val, str) and len(val) > 20:
                        desc = val
                        break
                else:
                    # Build description from title and scenes
                    title = data.get("title", "")
                    scenes = data.get("scenes", [])
                    if scenes and isinstance(scenes, list):
                        texts = []
                        if title:
                            texts.append(title)
                        for scene in scenes:
                            if isinstance(scene, dict) and scene.get("text"):
                                texts.append(scene["text"])
                        desc = "\n\n".join(texts) if texts else desc
        except (json.JSONDecodeError, TypeError):
            # Truncated JSON — try to extract readable parts
            match = re.search(r'"description"\s*:\s*"([^"]+)"', desc)
            if match:
                desc = match.group(1)
            else:
                # Remove JSON-like noise
                desc = re.sub(r'[{}\[\]]', '', desc)
                desc = re.sub(r'"\w+"\s*:', '', desc)
                desc = re.sub(r'\s+', ' ', desc).strip()

    # Clean up artifacts
    desc = desc.strip('"\'{}')
    desc = re.sub(r'\s+', ' ', desc).strip() if '\n' not in desc else desc

    if len(desc) > 5000:
        desc = desc[:4997] + "..."

    return desc
