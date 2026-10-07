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


# Words that immediately disqualify a trend from being comedy (sports, matches, politics, tragedies)
EXCLUDED_TREND_KEYWORDS = {
    # Sports matches, leagues, teams, tournaments
    "vs", "v.", "versus", "score", "scores", "match", "cup", "league", "fc", "cf",
    "championship", "tournament", "qualifier", "playoff", "finals", "stadium", "fifa",
    "uefa", "nfl", "nba", "mlb", "nhl", "premier league", "conmebol", "concacaf", "mls",
    "quarterback", "touchdown", "goal", "goalkeeper", "soccer", "football", "basketball",
    "baseball", "cricket", "rugby", "tennis",
    # Serious news, politics, tragedies
    "election", "senate", "congress", "president", "court", "trial", "verdict",
    "shooting", "crash", "explosion", "killed", "dead", "death", "war", "strike",
    "earthquake", "hurricane", "tsunami", "hostage", "arrested", "murder", "casualty",
    # Finance & business
    "stock", "shares", "nasdaq", "dow", "inflation", "interest rate",
}

COMEDY_KEYWORDS = {
    "funny", "meme", "viral", "challenge", "fail", "win", "epic",
    "weird", "bizarre", "crazy", "wild", "hilarious", "lol",
    "drama", "react", "caught", "exposed", "prank", "humor",
    "unhinged", "absurd", "awkward", "blooper", "parody",
}


def filter_comedy_trends(trends: list[dict]) -> list[dict]:
    """
    Filter trending topics to find ones with genuine comedy/entertainment potential.

    Strictly excludes sports matches (e.g., 'guatemala vs suriname'), politics,
    and tragedies, ensuring only funny/viral topics make it to the video pipeline.
    """
    filtered = []
    for trend in trends:
        title = trend.get("title", "")
        title_lower = title.lower()
        title_words = set(re.findall(r'\b[a-zA-Z]+\b', title_lower))

        # 1. Reject if ANY excluded keyword matches as a whole word
        if any(bad_word in title_words for bad_word in EXCLUDED_TREND_KEYWORDS):
            logger.debug(f"Rejecting non-comedy trend '{title}': matched exclusion")
            continue

        # 2. Require an explicit comedy/entertainment angle
        has_comedy_angle = any(kw in title_lower for kw in COMEDY_KEYWORDS)

        # 3. Only keep trends that have a verified comedy angle
        if has_comedy_angle:
            trend["virality_score"] = trend.get("virality_score", 0) + 30
            filtered.append(trend)

    return filtered
