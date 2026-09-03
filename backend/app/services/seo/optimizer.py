"""
AI News Studio — SEO Optimizer (Views-Optimized Edition)

Generates SEO-optimized titles, descriptions, tags, chapters,
and pinned comments for YouTube videos using LLM-powered optimization.

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

logger = logging.getLogger(__name__)

# Power words that boost CTR — used for title scoring
POWER_WORDS = {
    "tier1": [  # Highest impact — urgency & shock
        "shocking", "exposed", "urgent", "breaking", "warning", "banned",
        "insane", "unbelievable", "massive", "emergency", "critical",
        "catastrophic", "explosive", "devastating",
    ],
    "tier2": [  # High impact — curiosity & emotion
        "secret", "hidden", "revealed", "truth", "actually", "real",
        "caught", "leaked", "discovered", "confirmed", "impossible",
        "terrifying", "incredible", "dramatic",
    ],
    "tier3": [  # Medium impact — engagement
        "just", "now", "today", "update", "live", "alert", "new",
        "first", "latest", "official", "major", "huge", "wild",
    ],
}


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
        category = script.get("category", "News")

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
        shorts_tags = [
            "shorts", "youtubeshorts", "ytshorts", "short",
            "viral shorts", "trending shorts", "news shorts", "breaking news",
        ]
        for st in reversed(shorts_tags):
            if st not in tags:
                tags.insert(0, st)

        # Add time-based trending tags for temporal relevance
        now = datetime.now(timezone.utc)
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
        base_hashtags = [
            "#Shorts", "#News", "#Trending", "#BreakingNews",
            "#WorldNews", "#NewsToday", "#ViralNews",
        ]
        # Generate niche hashtags from topic keywords for better discoverability
        topic_words = [w.strip() for w in topic.split() if len(w.strip()) >= 4]
        niche_hashtags = []
        for word in topic_words[:3]:
            # Create clean hashtags from topic keywords
            clean_word = re.sub(r'[^a-zA-Z0-9]', '', word).capitalize()
            if clean_word and len(clean_word) >= 4:
                niche_hashtags.append(f"#{clean_word}")
                niche_hashtags.append(f"#{clean_word}News")
        extra_hashtags = [
            f"#{tag.replace(' ', '')}"
            for tag in tags if tag not in shorts_tags and not tag.startswith("#")
        ][:5]
        hashtags = list(dict.fromkeys(base_hashtags + niche_hashtags + extra_hashtags))

        # Generate engagement-optimized pinned comment
        pinned_comment = self._generate_pinned_comment(topic, seo_title)

        # Ensure #Shorts tag in title
        clean_title = _sanitize_seo_title(seo_title)
        if not clean_title.lower().endswith("#shorts"):
            clean_title = f"{clean_title[:85]} #Shorts"

        result = {
            "title": clean_title[:100],  # YouTube 100 char limit
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
        try:
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
            
            # Final sanitization
            best_title = _sanitize_seo_title(best_title)
            return best_title[:100]
        except Exception as e:
            logger.warning(f"Title generation failed: {e}")
            # Fallback: use script_title but sanitize it first
            clean = _sanitize_seo_title(script_title)
            return clean[:100]

    async def _generate_description(
        self,
        title: str,
        topic: str,
        scene_titles: list[str],
        chapters: str,
    ) -> str:
        """Generate a YouTube video description."""
        try:
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
        try:
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
            return [t.strip() for t in tags if t.strip()][:30]

        except Exception as e:
            logger.warning(f"Tag generation failed: {e}")
            # Enhanced fallback tags with Shorts discovery and topic keywords
            words = topic.split()[:10]
            now = datetime.now(timezone.utc)
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

    def _generate_pinned_comment(self, topic: str, title: str) -> str:
        """Generate an engagement-optimized pinned comment.
        
        Designed to maximize comment replies and engagement signals,
        which directly boost YouTube's algorithmic ranking.
        
        Uses topic-specific debate questions instead of generic templates
        to drive genuine conversation and higher engagement rates.
        """
        # Extract key topic phrases for specific debate questions
        clean_topic = topic[:100].strip() if topic else "this story"
        
        # Generate topic-specific debate angle
        debate_questions = [
            f"Do you think this will get better or worse? 🤔",
            f"Who do you think is really responsible for this?",
            f"How will this affect ordinary people like us?",
            f"Is this being covered fairly by the media? 🧐",
            f"What would YOU do in this situation?",
            f"Did you see this coming or is this a total surprise?",
            f"Which side are you on? Drop 1 or 2 below 👇",
            f"How do you think this will play out in the next 30 days?",
        ]
        debate_q = random.choice(debate_questions)
        
        return (
            f"🔥 {debate_q}\n\n"
            f"📌 Topic: {clean_topic}\n\n"
            f"💬 Reply with your HONEST opinion — no wrong answers!\n"
            f"❤️ LIKE if this is the first you're hearing of this\n"
            f"🔔 FOLLOW for daily 60-second news that matters\n"
            f"📤 TAG someone who needs to see this!\n\n"
            f"⚠️ All information sourced from verified news outlets. "
            f"Sources in description."
        )


def _score_title_ctr(title: str) -> float:
    """Score a title for predicted click-through rate.
    
    Uses a multi-signal heuristic based on YouTube Shorts best practices:
    - Power words presence and tier
    - Title length (shorter = better for Shorts)
    - Number presence (boosts CTR ~30%)
    - Question marks (curiosity gap)
    - Emotional triggers
    - #Shorts tag presence
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
    
    # Title length — sweet spot is 25-40 chars for Shorts
    title_len = len(title)
    if 25 <= title_len <= 40:
        score += 0.15  # Optimal length
    elif title_len < 25:
        score += 0.10  # Too short but still decent
    elif title_len <= 55:
        score += 0.05  # Acceptable
    else:
        score -= 0.10  # Too long
    
    # Number presence (e.g., "47 people", "$2 billion")
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
