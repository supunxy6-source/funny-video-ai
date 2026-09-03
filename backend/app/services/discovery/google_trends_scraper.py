"""
Stateside Smiles — Google Trends Scraper

Fetches currently trending search topics from Google Trends RSS feed.
Completely free, no API key required.

Used to cross-reference trending topics with entertainment/comedy angle
and validate viral potential for content creation.
"""

import logging
import re
from datetime import datetime, timezone
from typing import Optional

import feedparser
import httpx

logger = logging.getLogger(__name__)

# Google Trends RSS feeds
GOOGLE_TRENDS_RSS_US = "https://trends.google.com/trending/rss?geo=US"
GOOGLE_TRENDS_RSS_GLOBAL = "https://trends.google.com/trending/rss"

REQUEST_TIMEOUT = 15.0

USER_AGENT = (
    "StatesideSmiles/1.0 (Entertainment content aggregator; "
    "educational/research use)"
)


async def fetch_google_trends(limit: int = 20, geo: str = "US") -> list[dict]:
    """
    Fetch currently trending search topics from Google Trends RSS.

    Args:
        limit: Max number of trends to return
        geo: Geographic region (US, global)

    Returns:
        List of trending topic dicts with virality scoring
    """
    rss_url = GOOGLE_TRENDS_RSS_US if geo == "US" else GOOGLE_TRENDS_RSS_GLOBAL
    results = []

    try:
        # feedparser can handle URLs directly, but we use httpx for timeout control
        async with httpx.AsyncClient(
            timeout=REQUEST_TIMEOUT,
            follow_redirects=True,
            headers={"User-Agent": USER_AGENT},
        ) as client:
            resp = await client.get(rss_url)
            if resp.status_code != 200:
                logger.warning(f"Google Trends RSS returned {resp.status_code}")
                return []

            feed = feedparser.parse(resp.text)

            for i, entry in enumerate(feed.entries[:limit]):
                title = entry.get("title", "").strip()
                if not title:
                    continue

                # Extract traffic volume if available
                # Google Trends RSS includes approximate search volume
                traffic = 0
                traffic_text = entry.get("ht_approx_traffic", "") or ""
                traffic_match = re.search(r"([\d,]+)", traffic_text.replace(",", ""))
                if traffic_match:
                    try:
                        traffic = int(traffic_match.group(1))
                    except ValueError:
                        pass

                # Extract related news articles
                news_items = []
                ht_news = entry.get("ht_news_item", [])
                if isinstance(ht_news, dict):
                    ht_news = [ht_news]
                for news in ht_news[:3]:
                    if isinstance(news, dict):
                        news_items.append({
                            "title": news.get("ht_news_item_title", ""),
                            "url": news.get("ht_news_item_url", ""),
                            "source": news.get("ht_news_item_source", ""),
                        })

                # Calculate virality score
                virality_score = max(10, traffic // 100) + (limit - i) * 5

                results.append({
                    "id": f"gtrend_{i}_{title[:20].replace(' ', '_')}",
                    "source": "google_trends",
                    "title": title,
                    "selftext": f"Trending topic: {title}",
                    "content_type": "trending_topic",
                    "image_url": None,
                    "virality_score": virality_score,
                    "category": "trending",
                    "traffic_volume": traffic,
                    "related_news": news_items,
                    "geo": geo,
                    "created_at": datetime.now(timezone.utc),
                })

            logger.info(f"📈 Google Trends: Fetched {len(results)} trending topics ({geo})")

    except Exception as e:
        logger.warning(f"Google Trends RSS error: {e}")

    return results


def filter_comedy_trends(trends: list[dict]) -> list[dict]:
    """
    Filter trending topics to find ones with comedy/entertainment potential.

    Uses keyword matching to identify trends that could be turned into
    funny content (celebrity drama, weird news, viral challenges, etc).
    """
    comedy_keywords = {
        "funny", "meme", "viral", "challenge", "fail", "win", "epic",
        "weird", "bizarre", "crazy", "wild", "hilarious", "lol",
        "trend", "celebrity", "drama", "react", "caught", "exposed",
        "best", "worst", "top", "ranking", "vs", "debate",
        "game", "movie", "show", "music", "tiktok", "instagram",
    }

    filtered = []
    for trend in trends:
        title_lower = trend.get("title", "").lower()
        # Check if any comedy keyword is in the title
        has_comedy_angle = any(kw in title_lower for kw in comedy_keywords)
        # High-traffic topics are inherently interesting
        high_traffic = trend.get("traffic_volume", 0) > 50000

        if has_comedy_angle or high_traffic:
            if has_comedy_angle:
                trend["virality_score"] = trend.get("virality_score", 0) + 30
            filtered.append(trend)

    return filtered
