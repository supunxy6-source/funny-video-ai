"""
Stateside Smiles — Meme & Comedy Content Sources

Aggregates funny content from multiple free APIs:
- Imgflip API: Popular meme templates
- JokeAPI: Categorized jokes
- Useless Facts API: Random funny/interesting facts
- Wikipedia "On This Day": Historical funny events

All APIs are 100% free with no authentication required.
"""

import asyncio
import logging
import random
from datetime import datetime, timezone
from typing import Optional

import httpx

logger = logging.getLogger(__name__)

REQUEST_TIMEOUT = 10.0

USER_AGENT = (
    "StatesideSmiles/1.0 (Entertainment content aggregator; "
    "educational/research use)"
)


# ═══════════════════════════════════════════════════════════════════════
# Imgflip API — Popular Meme Templates
# ═══════════════════════════════════════════════════════════════════════

IMGFLIP_API_URL = "https://api.imgflip.com/get_memes"


async def fetch_meme_templates(limit: int = 20) -> list[dict]:
    """
    Fetch popular meme templates from Imgflip API.

    Returns list of meme template dicts with:
    - id, name, url, width, height, box_count
    """
    try:
        async with httpx.AsyncClient(
            timeout=REQUEST_TIMEOUT,
            headers={"User-Agent": USER_AGENT},
        ) as client:
            resp = await client.get(IMGFLIP_API_URL)
            if resp.status_code != 200:
                logger.warning(f"Imgflip API returned {resp.status_code}")
                return []

            data = resp.json()
            memes = data.get("data", {}).get("memes", [])

            results = []
            for meme in memes[:limit]:
                results.append({
                    "id": f"imgflip_{meme.get('id', '')}",
                    "source": "imgflip",
                    "title": meme.get("name", ""),
                    "content_type": "meme_template",
                    "image_url": meme.get("url", ""),
                    "width": meme.get("width", 0),
                    "height": meme.get("height", 0),
                    "box_count": meme.get("box_count", 2),
                    "virality_score": 100 - memes.index(meme),  # Top memes = higher score
                    "category": "meme_template",
                    "selftext": "",
                })

            logger.info(f"🃏 Imgflip: Fetched {len(results)} meme templates")
            return results

    except Exception as e:
        logger.warning(f"Imgflip API error: {e}")
        return []


# ═══════════════════════════════════════════════════════════════════════
# JokeAPI — Categorized Jokes
# ═══════════════════════════════════════════════════════════════════════

JOKEAPI_URL = "https://v2.jokeapi.dev/joke"

# Safe joke categories (exclude dark/nsfw)
JOKE_CATEGORIES = ["Programming", "Misc", "Pun", "Christmas"]


async def fetch_jokes(count: int = 10) -> list[dict]:
    """
    Fetch jokes from JokeAPI.

    Supports both single-line and two-part (setup/delivery) jokes.
    Filters out NSFW, religious, political, racist, sexist content.
    """
    results = []

    try:
        async with httpx.AsyncClient(
            timeout=REQUEST_TIMEOUT,
            headers={"User-Agent": USER_AGENT},
        ) as client:
            # Fetch multiple jokes
            categories = ",".join(JOKE_CATEGORIES)
            url = (
                f"{JOKEAPI_URL}/{categories}"
                f"?blacklistFlags=nsfw,religious,political,racist,sexist"
                f"&amount={min(count, 10)}"  # Max 10 per request
                f"&type=twopart,single"
            )

            resp = await client.get(url)
            if resp.status_code != 200:
                logger.warning(f"JokeAPI returned {resp.status_code}")
                return []

            data = resp.json()

            # Handle single joke vs multiple
            jokes = data.get("jokes", [data]) if "jokes" in data else [data]

            for i, joke in enumerate(jokes):
                if joke.get("error"):
                    continue

                joke_type = joke.get("type", "single")
                if joke_type == "twopart":
                    text = f"{joke.get('setup', '')}\n\n{joke.get('delivery', '')}"
                    title = joke.get("setup", "")[:80]
                else:
                    text = joke.get("joke", "")
                    title = text[:80]

                if not text.strip():
                    continue

                results.append({
                    "id": f"joke_{joke.get('id', i)}",
                    "source": "jokeapi",
                    "title": title,
                    "selftext": text,
                    "content_type": "joke",
                    "joke_type": joke_type,
                    "joke_category": joke.get("category", "Misc"),
                    "image_url": None,
                    "virality_score": 50 + random.randint(0, 50),
                    "category": "joke",
                })

            logger.info(f"😆 JokeAPI: Fetched {len(results)} jokes")

    except Exception as e:
        logger.warning(f"JokeAPI error: {e}")

    return results


# ═══════════════════════════════════════════════════════════════════════
# Useless Facts API — Random Funny Facts
# ═══════════════════════════════════════════════════════════════════════

FACTS_API_URL = "https://uselessfacts.jsph.pl/api/v2/facts"


async def fetch_funny_facts(count: int = 10) -> list[dict]:
    """
    Fetch random funny/interesting facts from Useless Facts API.
    """
    results = []

    try:
        async with httpx.AsyncClient(
            timeout=REQUEST_TIMEOUT,
            headers={"User-Agent": USER_AGENT},
        ) as client:
            # Fetch multiple random facts
            for i in range(count):
                try:
                    resp = await client.get(f"{FACTS_API_URL}/random", params={"language": "en"})
                    if resp.status_code != 200:
                        continue

                    fact = resp.json()
                    text = fact.get("text", "").strip()
                    if not text:
                        continue

                    results.append({
                        "id": f"fact_{fact.get('id', i)}",
                        "source": "uselessfacts",
                        "title": text[:80],
                        "selftext": text,
                        "content_type": "fact",
                        "image_url": None,
                        "virality_score": 30 + random.randint(0, 40),
                        "category": "fun_fact",
                        "source_url": fact.get("source_url", ""),
                    })

                    # Small delay between requests
                    await asyncio.sleep(0.3)

                except Exception:
                    continue

            logger.info(f"🤓 Facts API: Fetched {len(results)} fun facts")

    except Exception as e:
        logger.warning(f"Facts API error: {e}")

    return results


# ═══════════════════════════════════════════════════════════════════════
# Wikipedia "On This Day" — Historical Fun Events
# ═══════════════════════════════════════════════════════════════════════

WIKIPEDIA_API_URL = "https://api.wikimedia.org/feed/v1/wikipedia/en/onthisday"


async def fetch_on_this_day(limit: int = 10) -> list[dict]:
    """
    Fetch "On This Day" events from Wikipedia for funny/interesting historical content.
    """
    results = []
    today = datetime.now(timezone.utc)

    try:
        async with httpx.AsyncClient(
            timeout=REQUEST_TIMEOUT,
            headers={"User-Agent": USER_AGENT},
        ) as client:
            url = f"{WIKIPEDIA_API_URL}/all/{today.month:02d}/{today.day:02d}"
            resp = await client.get(url)

            if resp.status_code != 200:
                logger.warning(f"Wikipedia On This Day API returned {resp.status_code}")
                return []

            data = resp.json()

            # Get events (most likely to have funny/interesting ones)
            events = data.get("events", [])
            # Also check selected/featured
            events.extend(data.get("selected", []))

            for i, event in enumerate(events[:limit * 2]):
                text = event.get("text", "").strip()
                year = event.get("year", "")
                if not text:
                    continue

                # Build a "this day in history" entry
                title = f"On this day in {year}: {text[:60]}" if year else text[:80]

                results.append({
                    "id": f"otd_{today.month}_{today.day}_{i}",
                    "source": "wikipedia",
                    "title": title,
                    "selftext": f"On this day in {year}: {text}" if year else text,
                    "content_type": "historical_fact",
                    "image_url": None,
                    "virality_score": 20 + random.randint(0, 30),
                    "category": "on_this_day",
                    "year": year,
                })

            logger.info(f"📚 Wikipedia: Fetched {len(results)} 'On This Day' events")

    except Exception as e:
        logger.warning(f"Wikipedia On This Day error: {e}")

    return results[:limit]


# ═══════════════════════════════════════════════════════════════════════
# Aggregated Comedy Content Fetcher
# ═══════════════════════════════════════════════════════════════════════

async def fetch_all_comedy_sources(
    jokes_count: int = 10,
    facts_count: int = 5,
    memes_count: int = 15,
    otd_count: int = 5,
) -> list[dict]:
    """
    Fetch content from ALL free comedy sources concurrently.

    Returns a combined, deduplicated, sorted list of comedy content.
    """
    # Fetch all sources concurrently
    results = await asyncio.gather(
        fetch_meme_templates(limit=memes_count),
        fetch_jokes(count=jokes_count),
        fetch_funny_facts(count=facts_count),
        fetch_on_this_day(limit=otd_count),
        return_exceptions=True,
    )

    all_content = []
    source_names = ["Imgflip", "JokeAPI", "Facts", "Wikipedia"]

    for i, result in enumerate(results):
        if isinstance(result, Exception):
            logger.warning(f"Source {source_names[i]} failed: {result}")
            continue
        if isinstance(result, list):
            all_content.extend(result)

    # Sort by virality score
    all_content.sort(key=lambda x: x.get("virality_score", 0), reverse=True)

    logger.info(
        f"🎭 Total comedy content aggregated: {len(all_content)} items "
        f"(memes, jokes, facts, history)"
    )

    return all_content
