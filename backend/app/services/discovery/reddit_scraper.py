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

from app.core.config import settings

logger = logging.getLogger(__name__)

# Default comedy subreddits to scrape
DEFAULT_SUBREDDITS = [
    "funny", "memes", "dankmemes", "wholesomememes",
    "facepalm", "MadeMeSmile", "me_irl", "meirl",
]

# Reddit JSON API base URL
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


class RedditScraper:
    """Scrapes trending comedy content from Reddit's public JSON API."""

    def __init__(self):
        self.subreddits = self._get_subreddits()
        self._seen_ids: set[str] = set()

    def _get_subreddits(self) -> list[str]:
        """Get list of subreddits from settings or use defaults."""
        configured = getattr(settings, "reddit_subreddits", "")
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
        """Fetch posts from a single subreddit."""
        url = f"{REDDIT_BASE}/r/{subreddit}/{sort}.json"
        params = {"limit": 25, "raw_json": 1}
        if sort == "top":
            params["t"] = time_filter

        resp = await client.get(url, params=params)
        if resp.status_code != 200:
            logger.debug(f"Reddit r/{subreddit} returned status {resp.status_code}")
            return []

        data = resp.json()
        children = data.get("data", {}).get("children", [])

        posts = []
        for child in children:
            post_data = child.get("data", {})
            if not post_data:
                continue

            # Skip pinned, removed, NSFW content
            if post_data.get("stickied"):
                continue
            if post_data.get("over_18"):
                continue
            if post_data.get("removed_by_category"):
                continue

            # Quality filter: minimum engagement
            score = post_data.get("score", 0)
            upvote_ratio = post_data.get("upvote_ratio", 0)
            if score < MIN_SCORE or upvote_ratio < MIN_UPVOTE_RATIO:
                continue

            post = self._parse_post(post_data, subreddit)
            if post:
                posts.append(post)

        logger.info(f"📱 r/{subreddit}: {len(posts)} quality posts (score>{MIN_SCORE})")
        return posts

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
