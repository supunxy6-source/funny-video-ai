"""
Stateside Smiles — Script Writer

LLM-powered script generation with multi-provider
support (OpenAI, Anthropic, Google) and automatic fallback.
Supports both entertainment (comedy/meme) and news content modes.
"""

import json
import logging
import re
from datetime import datetime, timezone
from typing import Optional

from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession

from app.core.config import settings
from app.db.session import async_session_factory
from app.models.article import NewsArticle
from app.models.script import Script
from app.models.scene import Scene
from app.services.scriptwriter.prompts import (
    SCRIPT_SYSTEM_PROMPT,
    SCRIPT_GENERATION_PROMPT,
    FACT_CHECK_PROMPT,
)

logger = logging.getLogger(__name__)


class LLMClient:
    """Unified LLM client supporting OpenAI, Anthropic, and Google."""

    def __init__(self, provider: str = None):
        self.provider = provider or settings.llm_primary_provider
        self._client = None

    async def generate(
        self,
        prompt: str,
        system_prompt: str = "",
        max_tokens: int = 4096,
        temperature: float = 0.7,
    ) -> str:
        """Generate text using the configured LLM provider."""
        providers = [self.provider] + [
            p for p in ["openai", "anthropic", "google"] if p != self.provider
        ]

        for provider in providers:
            try:
                return await self._call_provider(
                    provider, prompt, system_prompt, max_tokens, temperature
                )
            except Exception as e:
                logger.warning(f"LLM provider '{provider}' failed: {e}")
                continue

        logger.warning("All LLM providers failed.")
        raise RuntimeError("All LLM providers failed to generate a response.")

    def _generate_fallback_script(self, story: dict = None) -> str:
        """Generate a structured fallback news script when external LLM APIs are unavailable.
        
        Uses actual article data from the story when available to create
        unique daily content instead of generic placeholder text.
        """
        if story and story.get("articles"):
            return self._generate_fallback_from_story(story)

        # Ultimate fallback with date-based uniqueness for Shorts
        today = datetime.now(timezone.utc).strftime("%B %d, %Y")
        return json.dumps({
            "title": f"Top News Update — {today} #Shorts",
            "scenes": [
                {
                    "order": 1,
                    "scene_type": "hook",
                    "title": "Immediate Hook",
                    "text": f"Here is what is making global headlines today, {today}.",
                    "visual_prompt": "Editorial news photography showing major global event coverage, vertical 9:16 aspect ratio",
                    "visual_type": "image"
                },
                {
                    "order": 2,
                    "scene_type": "narration",
                    "title": "Verified Developments",
                    "text": "Multiple international agencies are actively covering key breaking developments across the globe. Field correspondents report verified updates with ongoing assessments.",
                    "visual_prompt": "World map and news briefing with highlighted hotspots, vertical 9:16 composition",
                    "visual_type": "image"
                },
                {
                    "order": 3,
                    "scene_type": "impact",
                    "title": "Why It Matters",
                    "text": "Officials continue to evaluate the full impact as investigations and relief operations progress.",
                    "visual_prompt": "Press conference and ground updates visual, vertical 9:16 aspect ratio",
                    "visual_type": "image"
                },
                {
                    "order": 4,
                    "scene_type": "cta",
                    "title": "Quick Outro",
                    "text": "Subscribe for daily 60-second news updates.",
                    "visual_prompt": "Clean vertical news graphic with subscribe prompt",
                    "visual_type": "image"
                }
            ]
        })

    def _generate_fallback_from_story(self, story: dict) -> str:
        """Generate a compact YouTube Shorts fallback script using real article data."""
        articles = story.get("articles", [])
        today = datetime.now(timezone.utc).strftime("%B %d, %Y")

        # Extract the best headline for the title
        top_headline = story.get("top_headline", "")
        if not top_headline and articles:
            top_headline = articles[0].get("headline", "")
        
        # Clean the title and append #Shorts
        title = sanitize_title(top_headline) if top_headline else f"Global News Report — {today}"
        if not title.lower().endswith("#shorts"):
            safe_title = title[:42].rsplit(" ", 1)[0] if len(title) > 42 else title
            title = f"{safe_title} #Shorts"

        # Build intro from top headline (Hook)
        if top_headline:
            intro_text = f"Breaking news today: {top_headline}."
        else:
            intro_text = "Here is the top verified global news update right now."

        # Build main narration from the most relevant article (concise for Shorts: 40-50 words)
        main_summary = ""
        if articles:
            first_art = articles[0]
            summary = first_art.get("summary", "") or ""
            if summary:
                main_summary = summary[:160].rsplit(" ", 1)[0] if len(summary) > 160 else summary
        
        main_text = main_summary if main_summary else (
            "Verified reports from international agencies confirm key developments with emergency and government teams on the ground."
        )

        # Context (concise for Shorts: 20-30 words)
        context_parts = []
        for article in articles[1:3]:
            headline = article.get("headline", "")
            if headline:
                context_parts.append(headline[:80])
        
        context_text = "Officials confirm: " + ". ".join(context_parts) + "." if context_parts else (
            "Authorities are closely monitoring the situation as further verified details emerge."
        )

        scenes = [
            {
                "order": 1,
                "scene_type": "hook",
                "title": top_headline[:50] if top_headline else "Top Story",
                "text": intro_text,
                "visual_prompt": f"Editorial news photo coverage of {top_headline[:70]}, vertical 9:16 aspect ratio, dramatic journalistic photo",
                "visual_type": "image"
            },
            {
                "order": 2,
                "scene_type": "narration",
                "title": "Verified Facts",
                "text": main_text,
                "visual_prompt": "News photography with on-the-ground coverage, vertical 9:16 composition",
                "visual_type": "image"
            },
            {
                "order": 3,
                "scene_type": "impact",
                "title": "Impact & Context",
                "text": context_text,
                "visual_prompt": "Map and data visualization showing area of impact, vertical 9:16 framing",
                "visual_type": "image"
            },
            {
                "order": 4,
                "scene_type": "cta",
                "title": "Subscribe",
                "text": "Subscribe for daily 60-second verified news.",
                "visual_prompt": "Clean vertical news broadcast graphic with subscribe prompt",
                "visual_type": "image"
            }
        ]

        return json.dumps({"title": title, "scenes": scenes})

    async def _call_provider(
        self,
        provider: str,
        prompt: str,
        system_prompt: str,
        max_tokens: int,
        temperature: float,
    ) -> str:
        """Call a specific LLM provider."""
        if provider == "openai":
            return await self._call_openai(prompt, system_prompt, max_tokens, temperature)
        elif provider == "anthropic":
            return await self._call_anthropic(prompt, system_prompt, max_tokens, temperature)
        elif provider == "google":
            return await self._call_google(prompt, system_prompt, max_tokens, temperature)
        else:
            raise ValueError(f"Unknown LLM provider: {provider}")

    async def _call_openai(
        self, prompt: str, system_prompt: str, max_tokens: int, temperature: float
    ) -> str:
        from openai import AsyncOpenAI

        client = AsyncOpenAI(api_key=settings.openai_api_key)
        messages = []
        if system_prompt:
            messages.append({"role": "system", "content": system_prompt})
        messages.append({"role": "user", "content": prompt})

        response = await client.chat.completions.create(
            model=settings.openai_model,
            messages=messages,
            max_tokens=max_tokens,
            temperature=temperature,
        )
        return response.choices[0].message.content

    async def _call_anthropic(
        self, prompt: str, system_prompt: str, max_tokens: int, temperature: float
    ) -> str:
        from anthropic import AsyncAnthropic

        client = AsyncAnthropic(api_key=settings.anthropic_api_key)
        response = await client.messages.create(
            model=settings.anthropic_model,
            max_tokens=max_tokens,
            temperature=temperature,
            system=system_prompt or "You are a helpful assistant.",
            messages=[{"role": "user", "content": prompt}],
        )
        return response.content[0].text

    async def _call_google(
        self, prompt: str, system_prompt: str, max_tokens: int, temperature: float
    ) -> str:
        from google import genai
        from google.genai import types

        client = genai.Client(api_key=settings.google_ai_api_key)
        full_prompt = f"{system_prompt}\n\n{prompt}" if system_prompt else prompt

        response = await client.aio.models.generate_content(
            model=settings.google_ai_model,
            contents=full_prompt,
            config=types.GenerateContentConfig(
                max_output_tokens=max_tokens,
                temperature=temperature,
            ),
        )
        return response.text


def get_llm_client(provider: str = None) -> LLMClient:
    """Factory function for LLM client."""
    return LLMClient(provider)


class ScriptWriter:
    """Generates scripts from verified story clusters or entertainment content."""

    def __init__(self, provider: str = None):
        self.llm = LLMClient(provider)
        self.content_mode = getattr(settings, "content_mode", "entertainment")

    async def generate_script(self, story: dict) -> dict:
        """
        Generate a complete video script.
        Routes to entertainment or news script generation based on content_mode.

        Args:
            story: Dict containing content data (articles, memes, jokes, etc.)

        Returns:
            Dict with script data ready for database insertion
        """
        if self.content_mode == "entertainment":
            return await self._generate_entertainment_script(story)
        return await self._generate_news_script(story)

    async def _generate_entertainment_script(self, story: dict) -> dict:
        """
        Generate a comedy/entertainment script from trending content.
        """
        from app.services.scriptwriter.entertainment_prompts import (
            STORY_SYSTEM_PROMPT,
            MICRO_SHORTS_PROMPT,
            STORY_SHORTS_PROMPT,
            STORY_REGULAR_PROMPT,
            ENTERTAINMENT_SYSTEM_PROMPT,
            SHORTS_ENTERTAINMENT_PROMPT,
            REGULAR_VIDEO_PROMPT,
            MEME_COMPILATION_PROMPT,
        )

        articles = story.get("articles", [])
        if not articles:
            raise ValueError("No content provided for script generation")

        # Build content text for the prompt
        content_text = self._format_entertainment_content(articles)
        content_type = self._determine_content_type(articles)

        # Determine video format (Shorts vs Regular)
        video_format = story.get("video_format", "shorts")

        # Select prompt and system persona based on style & content
        meme_style = getattr(settings, "meme_style", "story")
        shorts_duration_mode = getattr(settings, "shorts_duration_mode", "micro")
        is_story_mode = (meme_style == "story" or content_type == "story")

        if is_story_mode:
            system_prompt = STORY_SYSTEM_PROMPT
            if video_format == "regular":
                prompt = STORY_REGULAR_PROMPT.format(content_text=content_text)
            elif shorts_duration_mode == "micro":
                prompt = MICRO_SHORTS_PROMPT.format(
                    content_text=content_text,
                    content_type=content_type,
                )
            else:
                prompt = STORY_SHORTS_PROMPT.format(
                    content_text=content_text,
                    content_type=content_type,
                )
        elif video_format == "regular":
            system_prompt = ENTERTAINMENT_SYSTEM_PROMPT
            prompt = REGULAR_VIDEO_PROMPT.format(content_text=content_text)
        elif content_type == "meme":
            system_prompt = ENTERTAINMENT_SYSTEM_PROMPT
            prompt = MEME_COMPILATION_PROMPT.format(
                content_text=content_text,
                video_format=video_format,
            )
        elif shorts_duration_mode == "micro":
            system_prompt = ENTERTAINMENT_SYSTEM_PROMPT
            prompt = MICRO_SHORTS_PROMPT.format(
                content_text=content_text,
                content_type=content_type,
            )
        else:
            system_prompt = ENTERTAINMENT_SYSTEM_PROMPT
            prompt = SHORTS_ENTERTAINMENT_PROMPT.format(
                content_text=content_text,
                content_type=content_type,
            )

        topic_summary = story.get("top_headline", "") or articles[0].get("headline", "Funny Content")
        mode_label = f"story-micro" if (is_story_mode and shorts_duration_mode == "micro") else ("story" if is_story_mode else "comedy")
        logger.info(f"😂 Generating {video_format} ({mode_label}) script for: {topic_summary[:80]}...")

        try:
            response = await self.llm.generate(
                prompt=prompt,
                system_prompt=system_prompt,
                max_tokens=4096,
                temperature=0.8,  # Slightly higher for comedy creativity
            )
        except Exception as e:
            logger.warning(f"Failed to generate script via LLM: {e}. Using fallback.")
            response = self._generate_entertainment_fallback(story)

        # Parse the structured response
        script_data = self._parse_script_response(response)

        # Calculate metrics
        full_text = " ".join(s["text"] for s in script_data.get("scenes", []))
        word_count = len(full_text.split())
        duration_estimate = word_count / 150.0  # ~150 WPM

        article_ids = [a.get("id") for a in articles if a.get("id")]

        raw_title = script_data.get("title", topic_summary[:100])
        clean_title = sanitize_title(raw_title)

        result = {
            "title": clean_title,
            "topic_summary": topic_summary,
            "content": full_text,
            "content_json": json.dumps(script_data),
            "article_ids": json.dumps(article_ids),
            "word_count": word_count,
            "duration_estimate": round(duration_estimate, 1),
            "llm_provider": self.llm.provider,
            "llm_model": self._get_model_name(),
            "scenes": script_data.get("scenes", []),
        }

        logger.info(
            f"✅ {mode_label.capitalize()} script generated: '{result['title']}' "
            f"({word_count} words, ~{result['duration_estimate']} min)"
        )

        return result

    def _format_entertainment_content(self, articles: list[dict]) -> str:
        """Format entertainment content items for the LLM prompt."""
        parts = []
        for i, item in enumerate(articles[:10], 1):
            source = item.get("source", "reddit")
            content_type = item.get("content_type", "post")
            body_text = item.get("selftext") or item.get("summary") or ""
            parts.append(
                f"[Item {i} — {source}/{content_type}]\n"
                f"Title: {item.get('headline', item.get('title', 'N/A'))}\n"
                f"Content: {body_text[:1800]}\n"
                f"Category: {item.get('category', 'entertainment')}\n"
                f"Virality: {item.get('virality_score', 'N/A')}\n"
            )
        return "\n---\n".join(parts)

    def _determine_content_type(self, articles: list[dict]) -> str:
        """Determine the dominant content type from articles."""
        type_counts = {}
        for a in articles:
            ct = a.get("content_type", a.get("category", "general"))
            type_counts[ct] = type_counts.get(ct, 0) + 1
        if type_counts:
            return max(type_counts, key=type_counts.get)
        return "mixed"

    def _generate_entertainment_fallback(self, story: dict) -> str:
        """Generate fallback natural story script when LLM fails."""
        articles = story.get("articles", [])
        title = "He Really Thought He Was Safe 💀"
        if articles:
            first_title = articles[0].get("headline", articles[0].get("title", ""))
            if first_title:
                clean = sanitize_title(first_title)
                title = clean[:42].rsplit(" ", 1)[0] if len(clean) > 42 else clean

        shorts_duration_mode = getattr(settings, "shorts_duration_mode", "micro")
        if shorts_duration_mode == "micro":
            scenes = [
                {
                    "order": 1,
                    "scene_type": "micro_hook",
                    "title": "Hook",
                    "text": "...nobody warned him what happens when you step right here.",
                    "visual_prompt": "Shocked expression reaction video, vertical 9:16",
                    "visual_type": "video",
                    "text_overlay": "Wait for it... 💀"
                },
                {
                    "order": 2,
                    "scene_type": "micro_escalation",
                    "title": "The Twist & Debate",
                    "text": "He took one confident step onto the floor before realizing his mistake. Would you have walked across this for ten thousand dollars?",
                    "visual_prompt": "Everyday situational comedic video, vertical 9:16",
                    "visual_type": "video",
                    "text_overlay": "It gets worse... 😭"
                },
                {
                    "order": 3,
                    "scene_type": "micro_payoff_loop",
                    "title": "Payoff & Loop",
                    "text": "He instantly regretted every life decision, and that is the exact reason why...",
                    "visual_prompt": "Laughing reaction reveal video, vertical 9:16",
                    "visual_type": "video",
                    "text_overlay": ""
                },
            ]
        else:
            scenes = [
                {
                    "order": 1,
                    "scene_type": "story_hook",
                    "title": "Hook",
                    "text": "Nobody warned him about what was about to happen next.",
                    "visual_prompt": "Shocked expression reaction video, vertical 9:16",
                    "visual_type": "video",
                    "text_overlay": "Wait for it... 💀"
                },
                {
                    "order": 2,
                    "scene_type": "story_setup",
                    "title": "Setup",
                    "text": "Everything seemed completely normal at first, until someone decided to take matters into their own hands.",
                    "visual_prompt": "Everyday situational comedic video, vertical 9:16",
                    "visual_type": "video",
                    "text_overlay": ""
                },
                {
                    "order": 3,
                    "scene_type": "story_escalation",
                    "title": "The Twist",
                    "text": "Normal people would apologize and walk away. But nope... they doubled down, and that sparked a massive debate.",
                    "visual_prompt": "Chaotic funny situation video, vertical 9:16",
                    "visual_type": "video",
                    "text_overlay": "It gets worse... 😭"
                },
                {
                    "order": 4,
                    "scene_type": "story_payoff_loop",
                    "title": "Punchline",
                    "text": "And to this day, they still swear it was totally worth it. Which honestly makes you wonder...",
                    "visual_prompt": "Laughing reaction reveal video, vertical 9:16",
                    "visual_type": "video",
                    "text_overlay": ""
                },
            ]

        return json.dumps({"title": title, "scenes": scenes})

    async def _generate_news_script(self, story: dict) -> dict:
        """
        Generate a complete video script from a verified story cluster.

        Args:
            story: Dict containing 'articles' list and 'verification' info

        Returns:
            Dict with script data ready for database insertion
        """
        articles = story.get("articles", [])
        if not articles:
            raise ValueError("No articles provided for script generation")

        # Build article context for the prompt
        articles_text = self._format_articles(articles)
        topic_summary = self._summarize_topic(articles)

        # Generate the script
        prompt = SCRIPT_GENERATION_PROMPT.format(
            topic_summary=topic_summary,
            articles_text=articles_text,
        )

        logger.info(f"🖊️ Generating script for: {topic_summary[:80]}...")
        try:
            response = await self.llm.generate(
                prompt=prompt,
                system_prompt=SCRIPT_SYSTEM_PROMPT,
                max_tokens=4096,
                temperature=0.7,
            )
        except Exception as e:
            logger.warning(f"Failed to generate script via LLM: {e}. Falling back to local script generator.")
            response = self.llm._generate_fallback_script(story)

        # Parse the structured response
        script_data = self._parse_script_response(response)

        # Calculate metrics
        full_text = " ".join(s["text"] for s in script_data.get("scenes", []))
        word_count = len(full_text.split())
        duration_estimate = word_count / 150.0  # ~150 WPM

        article_ids = [a.get("id") for a in articles if a.get("id")]

        # Sanitize the title — never allow raw JSON through
        raw_title = script_data.get("title", topic_summary[:100])
        clean_title = sanitize_title(raw_title)

        result = {
            "title": clean_title,
            "topic_summary": topic_summary,
            "content": full_text,
            "content_json": json.dumps(script_data),
            "article_ids": json.dumps(article_ids),
            "word_count": word_count,
            "duration_estimate": round(duration_estimate, 1),
            "llm_provider": self.llm.provider,
            "llm_model": self._get_model_name(),
            "scenes": script_data.get("scenes", []),
        }

        logger.info(
            f"✅ Script generated: '{result['title']}' "
            f"({word_count} words, ~{result['duration_estimate']} min)"
        )

        return result

    def _format_articles(self, articles: list[dict]) -> str:
        """Format articles into text for the LLM prompt."""
        parts = []
        for i, article in enumerate(articles[:8], 1):
            source_name = f"Source {article.get('source_id', i)}"
            parts.append(
                f"[Article {i} — {source_name}]\n"
                f"Headline: {article.get('headline', 'N/A')}\n"
                f"Summary: {article.get('summary', 'N/A')}\n"
                f"Body: {(article.get('body', '') or '')[:1500]}\n"
                f"URL: {article.get('url', 'N/A')}\n"
            )
        return "\n---\n".join(parts)

    def _summarize_topic(self, articles: list[dict]) -> str:
        """Create a topic summary from article headlines."""
        headlines = [a.get("headline", "") for a in articles[:5]]
        # Use the most common keywords from headlines
        return headlines[0] if headlines else "Breaking News"

    def _parse_script_response(self, response: str) -> dict:
        """Parse the LLM response into structured script data."""
        # Clean response (remove markdown code blocks if present)
        text = response.strip()
        if text.startswith("```"):
            text = text.split("\n", 1)[1] if "\n" in text else text[3:]
        if text.endswith("```"):
            text = text[:-3]
        text = text.strip()

        # Remove json language tag if present
        if text.startswith("json"):
            text = text[4:].strip()

        try:
            return json.loads(text)
        except json.JSONDecodeError as e:
            logger.warning(f"Failed to parse script JSON: {e}")
            # Fallback: create a simple structure
            return {
                "title": "Breaking News Report",
                "scenes": [
                    {
                        "order": 1,
                        "scene_type": "narration",
                        "title": "Full Report",
                        "text": response,
                        "visual_prompt": "News broadcast studio with anchor desk",
                        "visual_type": "image",
                    }
                ],
            }

    def _get_model_name(self) -> str:
        """Get the model name for the current provider."""
        if not self.llm or not self.llm.provider:
            return "fallback"
        if self.llm.provider == "openai":
            return settings.openai_model
        elif self.llm.provider == "anthropic":
            return settings.anthropic_model
        elif self.llm.provider == "google":
            return settings.google_ai_model
        return "unknown"


async def generate_script_for_story(story: dict) -> int:
    """
    Main script generation entry point called by Celery task.
    Generates a script and saves it to the database with scenes.

    Returns the script ID.
    """
    writer = ScriptWriter()
    script_data = await writer.generate_script(story)

    async with async_session_factory() as db:
        # Create script record
        script = Script(
            title=script_data["title"],
            topic_summary=script_data["topic_summary"],
            content=script_data["content"],
            content_json=script_data["content_json"],
            article_ids=script_data["article_ids"],
            word_count=script_data["word_count"],
            duration_estimate=script_data["duration_estimate"],
            llm_provider=script_data["llm_provider"],
            llm_model=script_data["llm_model"],
            status="draft",
        )
        db.add(script)
        await db.flush()

        # Create scene records
        for scene_data in script_data.get("scenes", []):
            scene_text = scene_data.get("text", "")
            scene = Scene(
                script_id=script.id,
                order=scene_data.get("order", 0),
                scene_type=scene_data.get("scene_type", "narration"),
                title=scene_data.get("title", ""),
                text=scene_text,
                visual_prompt=scene_data.get("visual_prompt"),
                visual_type=scene_data.get("visual_type", "image"),
                word_count=len(scene_text.split()),
                duration=len(scene_text.split()) / 150.0 * 60,  # seconds
            )
            db.add(scene)

        await db.commit()
        logger.info(f"💾 Script saved: ID={script.id}, '{script.title}'")

        return script.id


def sanitize_title(raw_title: str) -> str:
    """Sanitize a title string to ensure it is clean, human-readable text.
    
    Handles cases where raw JSON, code, or malformed LLM output
    might accidentally be used as a YouTube title or description.
    """
    if not raw_title or not raw_title.strip():
        today = datetime.now(timezone.utc).strftime("%B %d, %Y")
        return f"Funniest Content Today — {today}"

    title = raw_title.strip()

    # If the title looks like JSON, try to extract the actual title field
    if title.startswith("{") or title.startswith("["):
        try:
            data = json.loads(title)
            if isinstance(data, dict):
                extracted = data.get("title", "")
                if extracted and isinstance(extracted, str) and not extracted.startswith("{"):
                    title = extracted.strip()
                else:
                    for field in ["name", "headline", "subject"]:
                        val = data.get(field, "")
                        if val and isinstance(val, str):
                            title = val.strip()
                            break
                    else:
                        today = datetime.now(timezone.utc).strftime("%B %d, %Y")
                        title = f"Funniest Content Today — {today}"
        except (json.JSONDecodeError, TypeError):
            match = re.search(r'"title"\s*:\s*"([^"]+)"', title)
            if match:
                title = match.group(1).strip()
            else:
                today = datetime.now(timezone.utc).strftime("%B %d, %Y")
                title = f"Funniest Content Today — {today}"

    # Remove any remaining JSON artifacts
    title = title.strip('"\'{}')
    
    # Remove markdown formatting
    title = re.sub(r'[`*_~]', '', title)
    
    # Collapse whitespace
    title = re.sub(r'\s+', ' ', title).strip()

    # Final length check (YouTube limit is 100)
    if len(title) > 100:
        title = title[:97].rsplit(" ", 1)[0] + "..."

    return title
