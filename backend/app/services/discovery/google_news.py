"""
AI News Studio — Google News Scraper

Supplements RSS discovery with trending topics from Google News.
"""

import logging
from typing import Optional

import feedparser

logger = logging.getLogger(__name__)

# Google News RSS endpoints
GOOGLE_NEWS_RSS = "https://news.google.com/rss"
GOOGLE_NEWS_TOPIC_RSS = "https://news.google.com/rss/topics/{topic_id}"

# Topic IDs for Google News RSS
TOPIC_IDS = {
    "world": "CAAqJggKIiBDQkFTRWdvSUwyMHZNRGx1YlY4U0FtVnVHZ0pWVXlnQVAB",
    "business": "CAAqJggKIiBDQkFTRWdvSUwyMHZNRGx6TVdZU0FtVnVHZ0pWVXlnQVAB",
    "technology": "CAAqJggKIiBDQkFTRWdvSUwyMHZNRGRqTVhZU0FtVnVHZ0pWVXlnQVAB",
    "science": "CAAqJggKIiBDQkFTRWdvSUwyMHZNRFp0Y1RjU0FtVnVHZ0pWVXlnQVAB",
    "health": "CAAqIQgKIhtDQkFTRGdvSUwyMHZNR3QwTlRFU0FtVnVLQUFQAQ",
}


class GoogleNewsCollector:
    """Collects trending stories from Google News RSS feeds."""

    def get_trending_headlines(self, limit: int = 20) -> list[dict]:
        """Get top headlines from Google News main feed."""
        articles = []
        try:
            feed = feedparser.parse(GOOGLE_NEWS_RSS)
            for entry in feed.entries[:limit]:
                articles.append({
                    "headline": entry.get("title", "").strip(),
                    "url": entry.get("link", "").strip(),
                    "published_at": entry.get("published", ""),
                    "source_name": self._extract_source(entry.get("title", "")),
                })
            logger.info(f"📰 Google News: fetched {len(articles)} trending headlines")
        except Exception as e:
            logger.error(f"Error fetching Google News: {e}")
        return articles

    def get_topic_headlines(self, topic: str, limit: int = 15) -> list[dict]:
        """Get headlines for a specific topic from Google News."""
        topic_id = TOPIC_IDS.get(topic.lower())
        if not topic_id:
            logger.warning(f"Unknown topic: {topic}")
            return []

        articles = []
        try:
            url = GOOGLE_NEWS_TOPIC_RSS.format(topic_id=topic_id)
            feed = feedparser.parse(url)
            for entry in feed.entries[:limit]:
                articles.append({
                    "headline": entry.get("title", "").strip(),
                    "url": entry.get("link", "").strip(),
                    "published_at": entry.get("published", ""),
                    "topic": topic,
                    "source_name": self._extract_source(entry.get("title", "")),
                })
            logger.info(f"📰 Google News [{topic}]: fetched {len(articles)} headlines")
        except Exception as e:
            logger.error(f"Error fetching Google News topic '{topic}': {e}")
        return articles

    def get_all_trending(self) -> list[dict]:
        """Get trending headlines across all tracked topics."""
        all_articles = self.get_trending_headlines(limit=25)
        for topic in TOPIC_IDS:
            all_articles.extend(self.get_topic_headlines(topic, limit=10))
        return all_articles

    def _extract_source(self, title: str) -> Optional[str]:
        """Extract source name from Google News title (format: 'Headline - Source')."""
        if " - " in title:
            return title.rsplit(" - ", 1)[-1].strip()
        return None
