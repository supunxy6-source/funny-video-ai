"""
AI News Studio — News Collector

Discovers and collects breaking/trending news from 15+ trusted sources
via RSS feeds and web scraping. Runs hourly via Celery Beat.
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
    """Collects news articles from RSS feeds and web scraping."""

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


async def run_discovery() -> list[dict]:
    """
    Main discovery entry point called by Celery task.
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
