"""
Stateside Smiles — Multi-Engine Image Generator

Generates high-quality news visuals using:
1. Free AI Image Generation (Pollinations AI — FLUX.1 & Turbo)
2. Authentic Editorial News Photo Retrieval (Wikimedia Commons)
3. Direct Article Source Images (scraped from news outlets)
4. Premium AI Providers (Replicate FLUX/SDXL, OpenAI DALL-E 3 when configured)
5. Statistical Chart & Map Visualizations (Matplotlib)
6. Broadcast-Grade Editorial Graphic Cards (PIL offline fallback)
"""

import io
import json
import logging
import os
import random
import re
import urllib.parse
import uuid
from pathlib import Path
from typing import Optional

import httpx
from PIL import Image, ImageDraw, ImageFont
from sqlalchemy import select

from app.core.config import settings
from app.db.session import async_session_factory
from app.models.article import NewsArticle
from app.models.scene import Scene
from app.models.script import Script
from app.services.visuals.chart_generator import ChartGenerator

logger = logging.getLogger(__name__)


def _clean_search_keywords(prompt_or_title: str) -> str:
    """Extract clean search keywords from a prompt or title by stripping boilerplate."""
    text = prompt_or_title
    # Strip common AI prompt boilerplate
    boilerplate = [
        r"(?i)editorial news photo coverage of",
        r"(?i)editorial photography of",
        r"(?i)photorealistic news broadcast quality",
        r"(?i)high resolution dramatic journalistic photo",
        r"(?i)professional editorial photography",
        r"(?i)photorealistic",
        r"(?i)news photography with",
        r"(?i)dramatic cinematic composition",
        r"(?i)16:9 aspect ratio",
        r"(?i)4k resolution",
        r"(?i)8k quality",
        r"(?i)sharp focus",
        r"(?i)natural lighting",
        r"(?i)urgent mood",
        r"(?i)clean composition",
    ]
    for pattern in boilerplate:
        text = re.sub(pattern, "", text)

    # Clean whitespace and punctuation
    text = re.sub(r"[,\.\-:;]+", " ", text)
    text = re.sub(r"\s+", " ", text).strip()
    return text[:100]


class ImageGenerator:
    """Multi-engine news image generator with automatic seamless fallbacks."""

    def __init__(self):
        self.output_dir = Path(settings.generated_dir) / "images"
        self.output_dir.mkdir(parents=True, exist_ok=True)
        self.chart_gen = ChartGenerator()

        # Replicate client setup if token is provided
        self.replicate_token = (settings.replicate_api_token or "").strip()
        self.replicate_client = None
        if self.replicate_token and len(self.replicate_token) > 10 and not self.replicate_token.startswith("change"):
            try:
                import replicate
                os.environ["REPLICATE_API_TOKEN"] = self.replicate_token
                self.replicate_client = replicate.Client(api_token=self.replicate_token)
            except Exception as e:
                logger.debug(f"Replicate client init skipped: {e}")

    async def generate_image(
        self,
        prompt: str,
        aspect_ratio: str = "9:16",
        model: str = None,
        title: str = "",
        search_keywords: str = "",
        visual_type: str = "image",
        text_context: str = "",
        article_image_url: str = None,
    ) -> str:
        """
        Generate or fetch a relevant news visual using multi-engine pipeline for YouTube Shorts (9:16).

        Returns local file path of the verified image.
        """
        # 1. If visual type is a chart or data visualization, try ChartGenerator
        if visual_type == "chart" or "chart" in prompt.lower() or "statistics" in prompt.lower():
            chart_path = await self._try_chart(title or prompt, text_context)
            if chart_path:
                return chart_path

        # 2. If an authentic news article image URL is provided, try downloading it
        if article_image_url and article_image_url.startswith(("http://", "https://")):
            art_path = await self._download_article_image(article_image_url)
            if art_path:
                return art_path

        # 3. Try Free AI Image Generation via Pollinations AI (FLUX / Turbo)
        clean_prompt = self._enhance_news_prompt(prompt, title)
        pollinations_path = await self._try_pollinations(clean_prompt)
        if pollinations_path:
            return pollinations_path

        # 4. Try Authentic News Photo Retrieval via Wikimedia Commons
        search_query = search_keywords or _clean_search_keywords(title or prompt)
        if search_query:
            wiki_path = await self._try_wikimedia_image(search_query)
            if wiki_path:
                return wiki_path

        # 5. Try Replicate AI if valid token exists
        if self.replicate_client:
            replicate_path = await self._try_replicate(clean_prompt, aspect_ratio, model)
            if replicate_path:
                return replicate_path

        # 6. Try OpenAI DALL-E if valid OpenAI key exists
        if settings.openai_api_key and settings.openai_api_key.startswith("sk-") and len(settings.openai_api_key) > 20:
            openai_path = await self._try_openai(clean_prompt)
            if openai_path:
                return openai_path

        # 7. Final bulletproof fallback: Broadcast-grade editorial graphic card
        logger.info(f"🎨 Generating editorial news visual card for: {title or prompt[:60]}")
        return self._generate_editorial_graphic_card(title or search_query, prompt)

    def _enhance_news_prompt(self, base_prompt: str, title: str = "") -> str:
        """Create a vivid, photojournalistic prompt optimized for vertical 9:16 AI image models."""
        core = base_prompt.strip()
        if not core or len(core) < 10:
            core = f"Breaking news photojournalism coverage of {title.strip()}"

        # Ensure photojournalism style tags
        if "photo" not in core.lower() and "journalism" not in core.lower():
            core = f"Authentic editorial photojournalism coverage of {core}"

        return (
            f"{core}, award-winning press photograph, natural lighting, "
            f"sharp focus, vertical 9:16 YouTube Shorts composition, 4k quality"
        )

    async def _try_pollinations(self, prompt: str) -> Optional[str]:
        """Generate high-res AI news image using Pollinations AI in vertical 9:16 format."""
        models = ["flux", "turbo"]
        seed = random.randint(1000, 999999)

        for model_name in models:
            try:
                encoded = urllib.parse.quote(prompt[:350])
                url = (
                    f"https://image.pollinations.ai/prompt/{encoded}"
                    f"?width=1080&height=1920&model={model_name}&nologo=true&seed={seed}"
                )
                logger.info(f"🎨 Generating AI image via Pollinations ({model_name} 1080x1920)...")

                async with httpx.AsyncClient(timeout=45.0, follow_redirects=True) as http:
                    response = await http.get(
                        url,
                        headers={"User-Agent": "Mozilla/5.0 (Windows NT 10.0; Win64; x64) Chrome/122.0.0.0"},
                    )

                    if response.status_code == 200 and len(response.content) > 5000:
                        # Verify image validity with Pillow
                        img = Image.open(io.BytesIO(response.content))
                        img.verify()

                        # Re-open and save as 1080x1920 JPEG
                        img = Image.open(io.BytesIO(response.content)).convert("RGB")
                        if img.size != (1080, 1920):
                            img = img.resize((1080, 1920), Image.LANCZOS)

                        file_name = f"ai_news_{uuid.uuid4().hex}.jpg"
                        file_path = self.output_dir / file_name
                        img.save(str(file_path), "JPEG", quality=92)

                        logger.info(f"✅ AI News Image generated successfully: {file_path}")
                        return str(file_path)

            except Exception as e:
                logger.warning(f"Pollinations ({model_name}) generation attempt failed: {e}")
                continue

        return None

    async def _try_wikimedia_image(self, query: str) -> Optional[str]:
        """Search Wikimedia Commons for authentic editorial news photos matching query."""
        try:
            clean_q = _clean_search_keywords(query)
            if not clean_q or len(clean_q) < 3:
                return None

            logger.info(f"🔍 Searching Wikimedia Commons for news photo: '{clean_q}'")
            api_url = (
                "https://commons.wikimedia.org/w/api.php"
                "?action=query&generator=search"
                f"&gsrsearch={urllib.parse.quote(clean_q)}"
                "&gsrnamespace=6&format=json&prop=imageinfo"
                "&iiprop=url|size|mime&gsrlimit=6"
            )

            async with httpx.AsyncClient(timeout=15.0, follow_redirects=True) as http:
                resp = await http.get(
                    api_url,
                    headers={"User-Agent": "AINewsStudio/2.0 (contact@ainewsstudio.com)"},
                )
                if resp.status_code != 200:
                    return None

                data = resp.json()
                pages = data.get("query", {}).get("pages", {})

                for _, pinfo in pages.items():
                    imageinfo = pinfo.get("imageinfo", [])
                    if not imageinfo:
                        continue

                    img_meta = imageinfo[0]
                    mime = img_meta.get("mime", "")
                    if "jpeg" not in mime and "png" not in mime and "jpg" not in mime:
                        continue

                    img_url = img_meta.get("url")
                    if not img_url:
                        continue

                    # Download candidate image
                    img_resp = await http.get(img_url, timeout=20.0)
                    if img_resp.status_code == 200 and len(img_resp.content) > 15000:
                        img = Image.open(io.BytesIO(img_resp.content)).convert("RGB")
                        w, h = img.size
                        if w < 400 or h < 300:
                            continue

                        # Crop and resize to 9:16 (1080x1920)
                        target_ratio = 9 / 16
                        current_ratio = w / h
                        if current_ratio > target_ratio:
                            # Too wide: crop sides
                            new_w = int(h * target_ratio)
                            offset = (w - new_w) // 2
                            img = img.crop((offset, 0, offset + new_w, h))
                        else:
                            # Too tall: crop top/bottom
                            new_h = int(w / target_ratio)
                            offset = (h - new_h) // 2
                            img = img.crop((0, offset, w, offset + new_h))

                        img = img.resize((1080, 1920), Image.LANCZOS)

                        file_name = f"editorial_{uuid.uuid4().hex}.jpg"
                        file_path = self.output_dir / file_name
                        img.save(str(file_path), "JPEG", quality=92)

                        logger.info(f"✅ Authentic news photo retrieved: {file_path}")
                        return str(file_path)

        except Exception as e:
            logger.warning(f"Wikimedia news photo search failed for '{query}': {e}")

        return None

    async def _download_article_image(self, image_url: str) -> Optional[str]:
        """Download and prepare an image from the source article."""
        try:
            async with httpx.AsyncClient(timeout=20.0, follow_redirects=True) as http:
                resp = await http.get(
                    image_url,
                    headers={"User-Agent": "Mozilla/5.0 (Windows NT 10.0; Win64; x64) Chrome/122.0.0.0"},
                )
                if resp.status_code == 200 and len(resp.content) > 10000:
                    img = Image.open(io.BytesIO(resp.content)).convert("RGB")
                    w, h = img.size
                    if w >= 300 and h >= 300:
                        # Crop to 9:16 and resize
                        target_ratio = 9 / 16
                        current_ratio = w / h
                        if current_ratio > target_ratio:
                            new_w = int(h * target_ratio)
                            offset = (w - new_w) // 2
                            img = img.crop((offset, 0, offset + new_w, h))
                        else:
                            new_h = int(w / target_ratio)
                            offset = (h - new_h) // 2
                            img = img.crop((0, offset, w, offset + new_h))

                        img = img.resize((1080, 1920), Image.LANCZOS)
                        file_name = f"article_img_{uuid.uuid4().hex}.jpg"
                        file_path = self.output_dir / file_name
                        img.save(str(file_path), "JPEG", quality=92)
                        logger.info(f"✅ Source article image downloaded: {file_path}")
                        return str(file_path)

        except Exception as e:
            logger.debug(f"Article image download failed: {e}")

        return None

    async def _try_replicate(self, prompt: str, aspect_ratio: str = "16:9", model: str = None) -> Optional[str]:
        """Generate image via Replicate API if configured."""
        if not self.replicate_client:
            return None

        model = model or settings.image_model
        try:
            logger.info(f"🎨 Replicate generating image with {model}...")
            output = self.replicate_client.run(
                model,
                input={
                    "prompt": prompt,
                    "aspect_ratio": aspect_ratio,
                    "output_format": "jpg",
                    "output_quality": 90,
                    "num_outputs": 1,
                },
            )

            image_url = None
            if isinstance(output, list) and len(output) > 0:
                image_url = str(output[0])
            elif isinstance(output, str):
                image_url = output
            elif hasattr(output, "url"):
                image_url = output.url

            if image_url:
                async with httpx.AsyncClient(timeout=45.0) as http:
                    resp = await http.get(image_url)
                    if resp.status_code == 200:
                        file_name = f"replicate_{uuid.uuid4().hex}.jpg"
                        file_path = self.output_dir / file_name
                        file_path.write_bytes(resp.content)
                        logger.info(f"✅ Replicate image saved: {file_path}")
                        return str(file_path)

        except Exception as e:
            logger.warning(f"Replicate image generation failed: {e}")

        return None

    async def _try_openai(self, prompt: str) -> Optional[str]:
        """Generate image via OpenAI DALL-E 3 if configured."""
        try:
            from openai import AsyncOpenAI
            client = AsyncOpenAI(api_key=settings.openai_api_key)
            response = await client.images.generate(
                model="dall-e-3",
                prompt=prompt[:950],
                size="1792x1024",
                quality="standard",
                n=1,
            )
            img_url = response.data[0].url
            if img_url:
                async with httpx.AsyncClient(timeout=45.0) as http:
                    resp = await http.get(img_url)
                    if resp.status_code == 200:
                        file_name = f"dalle_{uuid.uuid4().hex}.jpg"
                        file_path = self.output_dir / file_name
                        file_path.write_bytes(resp.content)
                        logger.info(f"✅ OpenAI DALL-E image saved: {file_path}")
                        return str(file_path)
        except Exception as e:
            logger.warning(f"OpenAI DALL-E image generation failed: {e}")

        return None

    async def _try_chart(self, title: str, text: str) -> Optional[str]:
        """Generate a statistical chart visualization for data-heavy scenes."""
        try:
            # Extract any numbers or percentages from the text
            numbers = re.findall(r"\b\d+(?:[\.,]\d+)?%?\b", text)
            clean_title = title.strip()[:60] if title else "Key Statistics & Data"

            if numbers and len(numbers) >= 2:
                # Generate a bar chart
                labels = [f"Metric {i+1}" for i in range(min(4, len(numbers)))]
                values = []
                for n in numbers[:4]:
                    raw_val = n.replace("%", "").replace(",", "")
                    try:
                        values.append(float(raw_val))
                    except ValueError:
                        values.append(10.0)

                chart_path = self.chart_gen.generate_bar_chart(
                    title=clean_title,
                    labels=labels,
                    values=values,
                    ylabel="Reported Figures",
                )
                if chart_path:
                    return chart_path
            else:
                # Generate a prominent stat card
                stat_val = numbers[0] if numbers else "LIVE"
                stat_path = self.chart_gen.generate_stat_card(
                    title=clean_title,
                    value=stat_val,
                    subtitle="Verified Data Analysis",
                )
                if stat_path:
                    return stat_path

        except Exception as e:
            logger.warning(f"Chart generation failed: {e}")

        return None

    def _generate_editorial_graphic_card(self, title: str, prompt: str = "") -> str:
        """
        Generate a broadcast-grade visual infographic news graphic (PIL offline fallback).
        Never dumps raw prompt text. Displays polished headline typography and news visual motifs.
        """
        file_name = f"editorial_card_{uuid.uuid4().hex}.jpg"
        file_path = self.output_dir / file_name

        width, height = 1080, 1920
        img = Image.new("RGB", (width, height), color=(6, 12, 24))
        draw = ImageDraw.Draw(img)

        # 1. Dark Broadcast Studio Gradient Background
        for y in range(height):
            ratio = y / height
            r = int(6 + ratio * 14)
            g = int(12 + ratio * 20)
            b = int(24 + ratio * 36)
            draw.line([(0, y), (width, y)], fill=(r, g, b))

        # 2. Subtle Geometric Grid / Global Mesh pattern
        for x in range(60, width, 100):
            draw.line([(x, 0), (x, height)], fill=(15, 30, 55, 100), width=1)
        for y in range(60, height, 100):
            draw.line([(0, y), (width, y)], fill=(15, 30, 55, 100), width=1)

        # 3. Top & Bottom Neon Broadcast Accent lines
        draw.rectangle([(0, 0), (width, 10)], fill=(0, 229, 255))
        draw.rectangle([(0, height - 10), (width, height)], fill=(0, 229, 255))

        # 4. Central Visual Studio Card (Vertical 9:16 proportion)
        card_x1, card_y1 = 60, 280
        card_x2, card_y2 = width - 60, height - 400
        draw.rounded_rectangle(
            [(card_x1, card_y1), (card_x2, card_y2)],
            radius=24,
            fill=(12, 24, 46),
            outline=(0, 180, 216),
            width=2,
        )
        draw.rectangle([(card_x1, card_y1), (card_x2, card_y1 + 10)], fill=(0, 229, 255))

        # Helper font loader
        def _get_font(sz, bold=True):
            names = [
                "arialbd.ttf" if bold else "arial.ttf",
                "DejaVuSans-Bold.ttf" if bold else "DejaVuSans.ttf",
                "/usr/share/fonts/truetype/dejavu/DejaVuSans-Bold.ttf" if bold else "/usr/share/fonts/truetype/dejavu/DejaVuSans.ttf",
                "C:\\Windows\\Fonts\\arialbd.ttf" if bold else "C:\\Windows\\Fonts\\arial.ttf",
                "C:\\Windows\\Fonts\\segoeuib.ttf" if bold else "C:\\Windows\\Fonts\\segoeui.ttf",
            ]
            for n in names:
                try:
                    return ImageFont.truetype(n, sz)
                except Exception:
                    continue
            return ImageFont.load_default()

        # 5. Badge: "SPECIAL NEWS REPORT"
        draw.rounded_rectangle([(card_x1 + 40, card_y1 + 50), (card_x1 + 340, card_y1 + 110)], radius=12, fill=(0, 180, 216))
        draw.text((card_x1 + 60, card_y1 + 64), "SPECIAL REPORT", font=_get_font(28, bold=True), fill=(255, 255, 255))

        # 6. Headline Typography (Clean, readable topic title for vertical display)
        display_title = title.strip() if title and title.strip() else _clean_search_keywords(prompt)
        if not display_title:
            display_title = "Global News In-Depth Report"

        font_headline = _get_font(52, bold=True)
        import textwrap
        wrapped_lines = textwrap.wrap(display_title, width=26)[:4]

        for idx, line in enumerate(wrapped_lines):
            draw.text(
                (card_x1 + 40, card_y1 + 160 + idx * 75),
                line,
                font=font_headline,
                fill=(255, 255, 255),
            )

        # 7. Decorative Visual Audio Wave / Live Monitor Graphic
        import math
        wave_y = card_y2 - 60
        for x_step in range(card_x1 + 40, card_x2 - 40, 14):
            bar_h = int(16 + 26 * math.sin((x_step - card_x1) * 0.04))
            draw.line([(x_step, wave_y - bar_h), (x_step, wave_y + bar_h)], fill=(0, 229, 255), width=5)

        # 8. Live Status Pill
        font_status = _get_font(22, bold=False)
        mode = getattr(settings, "content_mode", "entertainment")
        status_text = "😄 STATESIDE SMILES • VIRAL COMEDY & MEMES" if mode == "entertainment" else "● VERIFIED JOURNALISTIC COVERAGE & FIELD REPORTS"
        draw.text(
            (card_x1 + 40, card_y2 - 130),
            status_text,
            font=font_status,
            fill=(245, 158, 11) if mode == "entertainment" else (176, 190, 197),
        )

        img.save(str(file_path), "JPEG", quality=92)
        logger.info(f"🖼️ Saved broadcast graphic card: {file_path}")
        return str(file_path)


async def generate_scene_images(script_id: int) -> list[str]:
    """
    Main image generation entry point called by Celery task.
    Generates high-quality AI images and visuals for all scenes.

    Returns list of generated image file paths.
    """
    generator = ImageGenerator()
    generated_paths = []

    async with async_session_factory() as db:
        # Load script and associated articles
        script = await db.get(Script, script_id)
        articles = []
        if script and script.article_ids:
            try:
                art_ids = json.loads(script.article_ids)
                if art_ids:
                    art_result = await db.execute(
                        select(NewsArticle).where(NewsArticle.id.in_(art_ids))
                    )
                    articles = art_result.scalars().all()
            except Exception as e:
                logger.debug(f"Could not load script articles: {e}")

        # Load scenes
        result = await db.execute(
            select(Scene)
            .where(Scene.script_id == script_id)
            .where(Scene.scene_type != "cta")
            .order_by(Scene.order)
        )
        scenes = result.scalars().all()

        mode = getattr(settings, "content_mode", "entertainment")
        for idx, scene in enumerate(scenes):
            if mode == "entertainment":
                default_prompt = f"Vibrant hilarious comedy meme visual of {scene.title or (script.title if script else 'funny viral moments')}, colorful and eye-catching"
            else:
                default_prompt = f"Editorial news photography of {scene.title or (script.title if script else 'breaking news')}"
            prompt = scene.visual_prompt or default_prompt
            clean_title = scene.title or (script.title if script else "")

            # Match with an article if available
            article_img = None
            if idx < len(articles) and articles[idx].image_url:
                article_img = articles[idx].image_url

            search_kw = _clean_search_keywords(f"{clean_title} {script.topic_summary if script else ''}")

            logger.info(f"🎬 Processing visual for Scene {scene.order} ({scene.scene_type}): {clean_title[:50]}...")
            image_path = await generator.generate_image(
                prompt=prompt,
                aspect_ratio="16:9",
                title=clean_title,
                search_keywords=search_kw,
                visual_type=scene.visual_type or "image",
                text_context=scene.text or "",
                article_image_url=article_img,
            )

            if image_path:
                scene.image_url = image_path
                generated_paths.append(image_path)
            else:
                logger.warning(f"⚠️ Failed to generate image for scene {scene.id}")

        await db.commit()
        logger.info(
            f"🎨 Generated {len(generated_paths)}/{len(scenes)} scene images "
            f"for script {script_id}"
        )

    return generated_paths

