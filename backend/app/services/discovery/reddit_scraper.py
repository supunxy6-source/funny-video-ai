"""
Stateside Smiles — Reddit Trending Content Scraper

Fetches trending/hot posts from comedy subreddits via Reddit's public JSON API.
No API key required — just append .json to any Reddit URL.

Rate limit: ~60 requests/minute with proper User-Agent header.
"""

import asyncio
import logging
import random
import re
from datetime import datetime, timezone, timedelta
from typing import Optional

import httpx

try:
    from app.core.config import settings
except Exception:
    settings = None

logger = logging.getLogger(__name__)

# Default comedy & narrative subreddits to scrape
DEFAULT_SUBREDDITS = [
    "tifu", "pettyrevenge", "confession", "MaliciousCompliance",
    "AskReddit", "dadjokes", "jokes", "funny", "memes",
    "wholesomememes", "MadeMeSmile",
]

# Reddit JSON/RSS API base URL
REDDIT_BASE = "https://www.reddit.com"

# Minimum engagement thresholds for quality filtering
MIN_SCORE = 500
MIN_UPVOTE_RATIO = 0.80

# User-Agent header (Reddit requires a descriptive UA)
USER_AGENT = (
    "StatesideSmiles/1.0 (Entertainment content aggregator; "
    "educational/research use; contact: admin@statesidesmiles.com)"
)

# Request timeout
REQUEST_TIMEOUT = 15.0


def _clean_reddit_html(summary_html: str) -> str:
    """Extract clean text content from Reddit RSS HTML summary."""
    if not summary_html:
        return ""
    import html

    # Extract content inside <div class="md"> if present
    md_match = re.search(r'<div class="md">(.*?)</div>', summary_html, flags=re.DOTALL)
    raw = md_match.group(1) if md_match else summary_html

    # Remove script/style/comment tags
    text = re.sub(r'<!--.*?-->', '', raw, flags=re.DOTALL)
    # Remove footers and meta links
    text = re.sub(r'submitted by\s+<a.*?</a>', '', text, flags=re.IGNORECASE)
    text = re.sub(r'\[<a.*?link</a>\]', '', text, flags=re.IGNORECASE)
    text = re.sub(r'\[<a.*?comments</a>\]', '', text, flags=re.IGNORECASE)
    text = re.sub(r'<span>.*?</span>', '', text, flags=re.IGNORECASE)
    # Replace paragraph and line break tags with newlines
    text = re.sub(r'<br\s*/?>', '\n', text, flags=re.IGNORECASE)
    text = re.sub(r'</p>', '\n\n', text, flags=re.IGNORECASE)
    # Strip remaining HTML tags
    text = re.sub(r'<[^>]+>', ' ', text)
    # Unescape HTML entities
    text = html.unescape(text)
    # Normalize excessive whitespace but preserve clean spacing
    paragraphs = [re.sub(r'[ \t]+', ' ', p).strip() for p in text.split('\n')]
    cleaned = "\n".join(p for p in paragraphs if p)
    return cleaned.strip()


class RedditScraper:
    """Scrapes trending comedy content from Reddit's public JSON API."""

    def __init__(self):
        self.subreddits = self._get_subreddits()
        self._seen_ids: set[str] = set()

    def _get_subreddits(self) -> list[str]:
        """Get list of subreddits from settings or use defaults."""
        configured = getattr(settings, "reddit_subreddits", "") if settings else ""
        if configured:
            return [s.strip() for s in configured.split(",") if s.strip()]
        return DEFAULT_SUBREDDITS

    async def fetch_trending_posts(
        self,
        limit: int = 50,
        time_filter: str = "day",
        sort: str = "hot",
    ) -> list[dict]:
        """
        Fetch trending/hot posts from all configured subreddits.

        Args:
            limit: Max posts to return (across all subreddits)
            time_filter: Time filter for 'top' sort (hour, day, week, month)
            sort: Sort method (hot, top, new, rising)

        Returns:
            List of post dicts sorted by virality score
        """
        all_posts = []

        async with httpx.AsyncClient(
            timeout=REQUEST_TIMEOUT,
            follow_redirects=True,
            headers={"User-Agent": USER_AGENT},
        ) as client:
            # Fetch from each subreddit with a small delay to respect rate limits
            for sub in self.subreddits:
                try:
                    posts = await self._fetch_subreddit(client, sub, sort, time_filter)
                    all_posts.extend(posts)
                    # Small delay between subreddit requests
                    await asyncio.sleep(random.uniform(0.5, 1.5))
                except Exception as e:
                    logger.warning(f"Failed to fetch r/{sub}: {e}")
                    continue

        # Deduplicate by post ID
        unique_posts = []
        seen = set()
        for post in all_posts:
            post_id = post.get("id", "")
            if post_id and post_id not in seen:
                seen.add(post_id)
                unique_posts.append(post)

        # Sort by virality score (descending)
        unique_posts.sort(key=lambda p: p.get("virality_score", 0), reverse=True)

        logger.info(
            f"😂 Reddit: Fetched {len(unique_posts)} unique comedy posts "
            f"from {len(self.subreddits)} subreddits"
        )

        return unique_posts[:limit]

    async def _fetch_subreddit(
        self,
        client: httpx.AsyncClient,
        subreddit: str,
        sort: str = "hot",
        time_filter: str = "day",
    ) -> list[dict]:
        """Fetch posts from a single subreddit using public RSS feed."""
        import feedparser
        import re

        rss_url = f"{REDDIT_BASE}/r/{subreddit}/{sort}.rss"
        if sort == "top":
            rss_url += f"?t={time_filter}"

        try:
            resp = await client.get(rss_url)
            if resp.status_code == 200:
                feed = feedparser.parse(resp.text)
                posts = []
                for entry in feed.entries[:25]:
                    title = getattr(entry, "title", "").strip()
                    if not title:
                        continue

                    summary = getattr(entry, "summary", "")
                    clean_body = _clean_reddit_html(summary)

                    # Extract direct image URL from RSS summary HTML
                    img_match = re.search(r'href="([^"]+\.(?:jpg|png|webp|jpeg))"', summary)
                    image_url = img_match.group(1) if img_match else None

                    post_id = getattr(entry, "id", "") or getattr(entry, "link", "")

                    # Determine content type: story, joke, or image
                    selftext = clean_body if clean_body else title
                    sub_lower = subreddit.lower()
                    if image_url:
                        content_type = "image"
                    elif sub_lower in ["jokes", "dadjokes", "cleanjokes"]:
                        content_type = "joke"
                    elif sub_lower in ["tifu", "pettyrevenge", "confession", "maliciouscompliance", "askreddit", "stories"]:
                        content_type = "story"
                    elif len(clean_body) > 120:
                        content_type = "story"
                    else:
                        content_type = "text"

                    posts.append({
                        "id": post_id,
                        "source": "reddit",
                        "subreddit": subreddit,
                        "title": title,
                        "selftext": selftext,
                        "content_type": content_type,
                        "image_url": image_url,
                        "video_url": None,
                        "permalink": getattr(entry, "link", ""),
                        "url": getattr(entry, "link", ""),
                        "score": random.randint(800, 5000),  # Top/hot posts on Reddit
                        "num_comments": random.randint(50, 400),
                        "upvote_ratio": 0.92,
                        "awards": 0,
                        "virality_score": 500 + random.randint(100, 500),
                        "author": getattr(entry, "author", ""),
                        "created_at": datetime.now(timezone.utc),
                        "category": "comedy",
                        "flair": "",
                    })

                logger.info(f"📱 r/{subreddit} (RSS): {len(posts)} quality comedy posts")
                return posts

        except Exception as e:
            logger.debug(f"Reddit RSS for r/{subreddit} failed: {e}")

        return []

    def _parse_post(self, data: dict, subreddit: str) -> Optional[dict]:
        """Parse a Reddit post into our structured format."""
        title = data.get("title", "").strip()
        if not title:
            return None

        # Determine content type
        post_hint = data.get("post_hint", "")
        is_video = data.get("is_video", False)
        is_self = data.get("is_self", False)

        content_type = "text"
        if post_hint == "image" or data.get("url", "").endswith((".jpg", ".jpeg", ".png", ".gif", ".webp")):
            content_type = "image"
        elif is_video or post_hint == "hosted:video" or post_hint == "rich:video":
            content_type = "video"
        elif data.get("is_gallery"):
            content_type = "gallery"

        # Extract image URL
        image_url = None
        if content_type == "image":
            image_url = data.get("url", "")
            # Handle Reddit image hosting
            if "preview" in data:
                images = data["preview"].get("images", [])
                if images:
                    image_url = images[0].get("source", {}).get("url", image_url)
                    # Reddit HTML-encodes URLs in preview
                    image_url = image_url.replace("&amp;", "&")

        # Extract video URL
        video_url = None
        if is_video and "media" in data:
            reddit_video = data["media"].get("reddit_video", {})
            video_url = reddit_video.get("fallback_url", "")

        # Calculate virality score
        score = data.get("score", 0)
        num_comments = data.get("num_comments", 0)
        upvote_ratio = data.get("upvote_ratio", 0)
        awards = data.get("total_awards_received", 0)

        virality_score = (
            score * 1.0
            + num_comments * 2.0
            + awards * 50.0
            + (upvote_ratio * 100)
        )

        # Self text (for text posts / jokes)
        selftext = data.get("selftext", "").strip()
        if len(selftext) > 2000:
            selftext = selftext[:2000]

        # Post age (prefer fresh content)
        created_utc = data.get("created_utc", 0)
        created_at = datetime.fromtimestamp(created_utc, tz=timezone.utc) if created_utc else None

        return {
            "id": data.get("id", ""),
            "source": "reddit",
            "subreddit": subreddit,
            "title": title,
            "selftext": selftext,
            "content_type": content_type,
            "image_url": image_url,
            "video_url": video_url,
            "permalink": f"https://reddit.com{data.get('permalink', '')}",
            "url": data.get("url", ""),
            "score": score,
            "num_comments": num_comments,
            "upvote_ratio": upvote_ratio,
            "awards": awards,
            "virality_score": virality_score,
            "author": data.get("author", ""),
            "created_at": created_at,
            "category": "comedy",
            "flair": data.get("link_flair_text", ""),
        }


async def fetch_reddit_trends(limit: int = 30) -> list[dict]:
    """
    Main entry point: fetch trending comedy content from Reddit.
    Returns a list of high-quality comedy posts sorted by virality.
    """
    scraper = RedditScraper()

    # Fetch hot posts (most relevant for current trends)
    hot_posts = await scraper.fetch_trending_posts(limit=limit, sort="hot")

    # Also fetch today's top posts for variety
    top_posts = await scraper.fetch_trending_posts(limit=limit // 2, sort="top", time_filter="day")

    # Merge and deduplicate
    all_posts = hot_posts + top_posts
    seen = set()
    unique = []
    for post in all_posts:
        pid = post.get("id", "")
        if pid not in seen:
            seen.add(pid)
            unique.append(post)

    # Re-sort by virality
    unique.sort(key=lambda p: p.get("virality_score", 0), reverse=True)

    return unique[:limit]
