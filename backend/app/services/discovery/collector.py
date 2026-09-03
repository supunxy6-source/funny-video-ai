"""
Stateside Smiles — Content Collector

Discovers and collects content based on the configured content mode:
- "entertainment": Scrapes Reddit, meme APIs, Google Trends for comedy content
- "news": Legacy RSS news pipeline (preserved for backward compatibility)

Runs periodically via Celery Beat.
"""

import json
import logging
import re
from concurrent.futures import ThreadPoolExecutor, as_completed
from datetime import datetime, timezone, timedelta
from typing import Optional

import feedparser
import httpx
from newspaper import Article as NewspaperArticle
from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession

from app.core.config import settings
from app.db.session import async_session_factory
from app.models.article import NewsArticle
from app.models.source import Source

logger = logging.getLogger(__name__)


def _clean_url(raw: Optional[str], max_len: int = 2000) -> Optional[str]:
    """Strip markdown link formatting and ensure URL is a plain string within length limits."""
    if not raw or not raw.strip():
        return None
    url = raw.strip()
    # Strip markdown link: [text](actual_url) → actual_url
    md_match = re.match(r'\[.*?\]\((.*?)\)', url)
    if md_match:
        url = md_match.group(1)
    # Strip surrounding brackets/parens
    url = url.strip('[]()<> ')
    # Truncate if still too long
    if len(url) > max_len:
        url = url[:max_len]
    return url if url else None

# Timeout for HTTP requests
REQUEST_TIMEOUT = 30

# Maximum articles to collect per source per run
MAX_ARTICLES_PER_SOURCE = 20


class NewsCollector:
    """Collects news articles from RSS feeds and web scraping (legacy news mode)."""

    def __init__(self):
        self.http_client = httpx.Client(
            timeout=REQUEST_TIMEOUT,
            follow_redirects=True,
            headers={
                "User-Agent": (
                    "Mozilla/5.0 (Windows NT 10.0; Win64; x64) "
                    "AppleWebKit/537.36 (KHTML, like Gecko) "
                    "Chrome/120.0.0.0 Safari/537.36"
                )
            },
        )

    def parse_rss_feed(self, source: dict) -> list[dict]:
        """Parse an RSS feed and return a list of article dicts."""
        articles = []
        try:
            feed = feedparser.parse(source["rss_url"])
            if feed.bozo and not feed.entries:
                logger.warning(f"Failed to parse RSS for {source['name']}: {feed.bozo_exception}")
                return articles

            for entry in feed.entries[:MAX_ARTICLES_PER_SOURCE]:
                article = {
                    "source_id": source["id"],
                    "headline": entry.get("title", "").strip(),
                    "summary": entry.get("summary", "").strip()[:2000],
                    "url": _clean_url(entry.get("link", "")),
                    "author": entry.get("author", None),
                    "published_at": self._parse_date(entry),
                    "category": source.get("category", "general"),
                    "image_url": _clean_url(self._extract_image(entry)),
                }
                if article["headline"] and article["url"]:
                    articles.append(article)

            logger.info(f"✅ Collected {len(articles)} articles from {source['name']} RSS")
        except Exception as e:
            logger.error(f"❌ Error parsing RSS for {source['name']}: {e}")

        return articles

    def extract_full_article(self, url: str) -> dict:
        """Use newspaper3k to extract full article content."""
        try:
            article = NewspaperArticle(url)
            article.download()
            article.parse()
            try:
                article.nlp()
            except Exception:
                pass  # NLP is optional

            return {
                "body": article.text[:10000] if article.text else None,
                "image_url": _clean_url(article.top_image),
                "author": ", ".join(article.authors) if article.authors else None,
                "keywords": json.dumps(article.keywords[:20]) if article.keywords else None,
                "summary": article.summary[:2000] if article.summary else None,
            }
        except Exception as e:
            logger.warning(f"Could not extract article from {url}: {e}")
            return {}

    def collect_from_all_sources(self, sources: list[dict]) -> list[dict]:
        """Collect articles from all sources concurrently."""
        all_articles = []

        # Parse RSS feeds in parallel
        with ThreadPoolExecutor(max_workers=8) as executor:
            futures = {
                executor.submit(self.parse_rss_feed, source): source
                for source in sources
                if source.get("rss_url")
            }
            for future in as_completed(futures):
                source = futures[future]
                try:
                    articles = future.result()
                    all_articles.extend(articles)
                except Exception as e:
                    logger.error(f"Error collecting from {source['name']}: {e}")

        logger.info(f"📰 Total articles collected from RSS: {len(all_articles)}")

        # Extract full content for top articles in parallel
        with ThreadPoolExecutor(max_workers=6) as executor:
            futures = {}
            for article in all_articles[:50]:  # Limit full extraction to avoid rate limiting
                future = executor.submit(self.extract_full_article, article["url"])
                futures[future] = article

            for future in as_completed(futures):
                article = futures[future]
                try:
                    extra = future.result()
                    if extra.get("body"):
                        article["body"] = extra["body"]
                    if extra.get("image_url") and not article.get("image_url"):
                        article["image_url"] = extra["image_url"]
                    if extra.get("author") and not article.get("author"):
                        article["author"] = extra["author"]
                    if extra.get("keywords"):
                        article["keywords"] = extra["keywords"]
                    if extra.get("summary") and not article.get("summary"):
                        article["summary"] = extra["summary"]
                except Exception as e:
                    logger.warning(f"Error extracting article content: {e}")

        return all_articles

    def _parse_date(self, entry) -> Optional[datetime]:
        """Parse publication date from feed entry."""
        for date_field in ["published_parsed", "updated_parsed"]:
            parsed = entry.get(date_field)
            if parsed:
                try:
                    from time import mktime
                    return datetime.fromtimestamp(mktime(parsed), tz=timezone.utc)
                except Exception:
                    pass
        return None

    def _extract_image(self, entry) -> Optional[str]:
        """Extract image URL from feed entry."""
        # Check media_content
        media = entry.get("media_content", [])
        if media and isinstance(media, list):
            for m in media:
                if isinstance(m, dict) and m.get("url"):
                    return m["url"]

        # Check media_thumbnail
        thumbs = entry.get("media_thumbnail", [])
        if thumbs and isinstance(thumbs, list):
            for t in thumbs:
                if isinstance(t, dict) and t.get("url"):
                    return t["url"]

        # Check enclosures
        enclosures = entry.get("enclosures", [])
        if enclosures:
            for enc in enclosures:
                if isinstance(enc, dict) and "image" in enc.get("type", ""):
                    return enc.get("href") or enc.get("url")

        return None

    def close(self):
        """Close HTTP client."""
        self.http_client.close()


# ═══════════════════════════════════════════════════════════════════════
# Entertainment Discovery (New — Reddit + Memes + Trends)
# ═══════════════════════════════════════════════════════════════════════

async def run_entertainment_discovery() -> list[dict]:
    """
    Main entertainment content discovery entry point.
    Fetches content from all free comedy sources and stores in DB.
    Returns list of entertainment content items as dicts.
    """
    from app.services.discovery.reddit_scraper import fetch_reddit_trends
    from app.services.discovery.meme_sources import fetch_all_comedy_sources
    from app.services.discovery.google_trends_scraper import (
        fetch_google_trends,
        filter_comedy_trends,
    )

    logger.info("😂 Starting entertainment content discovery...")

    all_content = []

    # 1. Reddit trending comedy posts (primary source)
    try:
        reddit_posts = await fetch_reddit_trends(limit=30)
        all_content.extend(reddit_posts)
        logger.info(f"📱 Reddit: {len(reddit_posts)} comedy posts")
    except Exception as e:
        logger.warning(f"Reddit discovery failed: {e}")

    # 2. Meme templates, jokes, facts, history (supplementary)
    try:
        comedy_content = await fetch_all_comedy_sources(
            jokes_count=10,
            facts_count=5,
            memes_count=15,
            otd_count=5,
        )
        all_content.extend(comedy_content)
        logger.info(f"🎭 Comedy sources: {len(comedy_content)} items")
    except Exception as e:
        logger.warning(f"Comedy sources failed: {e}")

    # 3. Google Trends (trending topics with comedy angle)
    try:
        trends = await fetch_google_trends(limit=20)
        comedy_trends = filter_comedy_trends(trends)
        all_content.extend(comedy_trends)
        logger.info(f"📈 Google Trends: {len(comedy_trends)} comedy-relevant trends")
    except Exception as e:
        logger.warning(f"Google Trends failed: {e}")

    # Sort by virality score
    all_content.sort(key=lambda x: x.get("virality_score", 0), reverse=True)

    # Store in database as articles (reusing existing schema)
    new_items = []
    try:
        async with async_session_factory() as db:
            for item in all_content:
                # Check for duplicates by title (entertainment content doesn't have URLs always)
                item_url = item.get("permalink") or item.get("url") or item.get("id", "")
                if item_url:
                    exists = await db.execute(
                        select(NewsArticle.id).where(NewsArticle.url == item_url)
                    )
                    if exists.scalar_one_or_none() is not None:
                        continue

                article = NewsArticle(
                    source_id=None,  # No source record for free APIs
                    headline=item.get("title", "")[:500],
                    summary=item.get("selftext", "")[:2000] or item.get("title", ""),
                    body=item.get("selftext", ""),
                    url=_clean_url(item_url) or f"entertainment_{item.get('id', '')}",
                    image_url=_clean_url(item.get("image_url")),
                    author=item.get("author"),
                    published_at=item.get("created_at"),
                    category=item.get("category", "entertainment"),
                    keywords=json.dumps({
                        "source": item.get("source", ""),
                        "content_type": item.get("content_type", ""),
                        "virality_score": item.get("virality_score", 0),
                        "subreddit": item.get("subreddit", ""),
                    }),
                )
                db.add(article)
                new_items.append(item)

            await db.commit()
            logger.info(f"💾 Stored {len(new_items)} new entertainment items in database")

    except Exception as e:
        logger.error(f"❌ Entertainment storage failed: {e}", exc_info=True)
        raise

    return new_items


# ═══════════════════════════════════════════════════════════════════════
# Legacy News Discovery (Preserved)
# ═══════════════════════════════════════════════════════════════════════

async def run_news_discovery() -> list[dict]:
    """
    Legacy news discovery entry point (preserved for backward compatibility).
    Fetches all active sources, collects articles, deduplicates, and stores in DB.
    Returns list of new articles as dicts.
    """
    collector = NewsCollector()
    new_articles = []

    try:
        async with async_session_factory() as db:
            # Fetch active sources
            result = await db.execute(
                select(Source).where(Source.is_active.is_(True))
            )
            sources = result.scalars().all()
            source_dicts = [
                {
                    "id": s.id,
                    "name": s.name,
                    "url": s.url,
                    "rss_url": s.rss_url,
                    "trust_score": s.trust_score,
                    "category": s.category,
                }
                for s in sources
            ]

            if not source_dicts:
                logger.warning("No active sources found in database")
                return []

            logger.info(f"🔍 Starting news discovery from {len(source_dicts)} sources")

            # Collect articles (blocking I/O, runs in thread pool)
            raw_articles = collector.collect_from_all_sources(source_dicts)

            # Deduplicate and store
            for article_data in raw_articles:
                # Check if URL already exists
                exists = await db.execute(
                    select(NewsArticle.id).where(NewsArticle.url == article_data["url"])
                )
                if exists.scalar_one_or_none() is not None:
                    continue

                # Only include articles from the last 48 hours
                if article_data.get("published_at"):
                    cutoff = datetime.now(timezone.utc) - timedelta(hours=48)
                    if article_data["published_at"] < cutoff:
                        continue

                article = NewsArticle(
                    source_id=article_data["source_id"],
                    headline=article_data["headline"],
                    summary=article_data.get("summary"),
                    body=article_data.get("body"),
                    url=_clean_url(article_data["url"]) or article_data["url"],
                    image_url=_clean_url(article_data.get("image_url")),
                    author=article_data.get("author"),
                    published_at=article_data.get("published_at"),
                    category=article_data.get("category", "general"),
                    keywords=article_data.get("keywords"),
                )
                db.add(article)
                new_articles.append(article_data)

            await db.commit()
            logger.info(f"💾 Stored {len(new_articles)} new articles in database")

    except Exception as e:
        logger.error(f"❌ Discovery failed: {e}", exc_info=True)
        raise
    finally:
        collector.close()

    return new_articles


# ═══════════════════════════════════════════════════════════════════════
# Main Entry Point — Routes by Content Mode
# ═══════════════════════════════════════════════════════════════════════

async def run_discovery() -> list[dict]:
    """
    Main discovery entry point — routes to the appropriate discovery
    pipeline based on the configured content mode.
    """
    content_mode = getattr(settings, "content_mode", "entertainment")

    if content_mode == "entertainment":
        logger.info("🎭 Running ENTERTAINMENT content discovery")
        return await run_entertainment_discovery()
    else:
        logger.info("📰 Running NEWS content discovery")
        return await run_news_discovery()
