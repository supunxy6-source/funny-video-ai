"""
Stateside Smiles — Story Ranker (Views-Optimized Edition)

Ranks story clusters by newsworthiness using a weighted scoring model
that considers source count, trust scores, recency, category importance,
coverage breadth, and VIRAL POTENTIAL.

VIEWS OPTIMIZATION: Added viral potential scoring dimension that boosts
stories with high-engagement keywords, emotional triggers, and topic
crossover appeal. Rebalanced category scores for Shorts performance.
"""

import json
import logging
import re
from datetime import datetime, timezone
from typing import Optional

from sqlalchemy import select, func
from sqlalchemy.ext.asyncio import AsyncSession

from app.core.config import settings
from app.db.session import async_session_factory
from app.models.article import NewsArticle
from app.models.source import Source
from app.models.script import Script

logger = logging.getLogger(__name__)

# Scoring weights — viral_potential added as a key dimension
WEIGHTS = {
    "source_count": 0.25,           # More sources = more important
    "trust_score": 0.20,            # Higher trust = more credible
    "recency": 0.15,                # More recent = more relevant
    "category_importance": 0.10,    # Some categories rank higher
    "coverage_breadth": 0.10,       # Diverse source types
    "viral_potential": 0.20,        # NEW: likelihood of getting views on Shorts
}

# Category importance scores — rebalanced for YouTube Shorts performance
# Entertainment and sports actually perform VERY well on Shorts
CATEGORY_IMPORTANCE = {
    "breaking": 1.0,
    "politics": 0.9,
    "world": 0.9,
    "technology": 0.90,     # Tech content is huge on Shorts
    "health": 0.85,
    "science": 0.85,
    "business": 0.80,
    "entertainment": 0.80,  # Boosted: entertainment performs well on Shorts
    "sports": 0.75,         # Boosted: sports gets high engagement
    "general": 0.65,
}

# Strict safety filter: content containing these words will be rejected to protect channel reputation
BANNED_POLICY_KEYWORDS = [
    "murder", "killing", "killed", "humping", "suicide", "suicidal", "terrorist", "terrorism",
    "rape", "raping", "rapist", "assault", "execution", "pedophile", "pedophilia", "porn", "nude", "nsfw",
    "incitement to murder", "beheaded", "massacre", "genocide", "torture", "slur", "dildo", "masturbat",
]

# Keywords that indicate viral potential on YouTube Shorts (separated by mode)
COMEDY_VIRAL_KEYWORDS = {
    "tier1": [
        "hilarious", "instant regret", "wait for it", "try not to laugh",
        "caught on camera", "gone wrong", "unexpected", "epic fail",
        "impossible", "genius", "chaos", "worst mistake", "unbelievable",
    ],
    "tier2": [
        "meme", "relatable", "funny", "cat", "dog", "prank", "joke",
        "crying laughing", "wild", "crazy", "insane", "awkward", "clueless",
    ],
    "tier3": [
        "secret", "hack", "trick", "watch till end", "who did this",
        "what happened", "actually", "why", "how",
    ],
}

NEWS_VIRAL_KEYWORDS = {
    "tier1": [
        "billion", "million", "trillion", "scandal", "exposed", "leaked",
        "arrested", "fired", "resigned", "banned", "illegal", "fraud",
        "disaster", "earthquake", "hurricane",
    ],
    "tier2": [
        "ai", "artificial intelligence", "elon musk", "tesla", "apple",
        "google", "openai", "chatgpt", "crypto", "bitcoin", "celebrity",
        "famous", "viral", "shocking", "incredible", "insane", "record",
        "first ever", "never before", "historic", "breakthrough",
        "warning", "emergency", "urgent", "crisis",
    ],
    "tier3": [
        "secret", "hidden", "revealed", "truth", "actually", "real reason",
        "why", "how", "what if", "nobody knows", "surprised", "unexpected",
        "strange", "mysterious", "new law", "new rule", "price", "cost",
        "free", "hack", "trick", "discovered",
    ],
}


class StoryRanker:
    """Ranks story clusters by newsworthiness and viral potential."""

    def score_cluster(
        self,
        cluster_id: int,
        articles: list[dict],
        source_trust_map: dict[int, float],
    ) -> dict:
        """
        Score a single story cluster.

        Returns a dict with cluster_id, score breakdown, and total score.
        """
        if not articles:
            return {"cluster_id": cluster_id, "total_score": 0.0}

        # 1. Source count score (normalized, max at 10 sources)
        unique_sources = set(a["source_id"] for a in articles)
        source_count_score = min(len(unique_sources) / 10.0, 1.0)

        # 2. Trust score (average trust of covering sources)
        trust_scores = [
            source_trust_map.get(a["source_id"], 0.5) for a in articles
        ]
        avg_trust_score = sum(trust_scores) / len(trust_scores) if trust_scores else 0.5

        # 3. Recency score (exponential decay over 24 hours)
        now = datetime.now(timezone.utc)
        ages_hours = []
        for a in articles:
            pub = a.get("published_at")
            if pub:
                if isinstance(pub, str):
                    try:
                        pub = datetime.fromisoformat(pub)
                    except ValueError:
                        continue
                age = (now - pub).total_seconds() / 3600
                ages_hours.append(max(age, 0))

        if ages_hours:
            min_age = min(ages_hours)
            recency_score = max(0, 1.0 - (min_age / 48.0))  # Linear decay over 48h
        else:
            recency_score = 0.5

        # 4. Category importance
        categories = [a.get("category", "general") for a in articles]
        cat_scores = [CATEGORY_IMPORTANCE.get(c, 0.5) for c in categories]
        category_score = max(cat_scores) if cat_scores else 0.5

        # 5. Coverage breadth (diversity of source types)
        coverage_score = min(len(unique_sources) / 5.0, 1.0)

        # 6. NEW: Viral potential score
        viral_score = self._score_viral_potential(articles)

        # None-safe guards
        source_count_score = source_count_score if source_count_score is not None else 0.0
        avg_trust_score = avg_trust_score if avg_trust_score is not None else 0.5
        recency_score = recency_score if recency_score is not None else 0.5
        category_score = category_score if category_score is not None else 0.5
        coverage_score = coverage_score if coverage_score is not None else 0.5
        viral_score = viral_score if viral_score is not None else 0.0

        # Weighted total
        total = (
            WEIGHTS["source_count"] * source_count_score
            + WEIGHTS["trust_score"] * avg_trust_score
            + WEIGHTS["recency"] * recency_score
            + WEIGHTS["category_importance"] * category_score
            + WEIGHTS["coverage_breadth"] * coverage_score
            + WEIGHTS["viral_potential"] * viral_score
        )

        return {
            "cluster_id": cluster_id,
            "total_score": round(total, 4),
            "article_count": len(articles),
            "source_count": len(unique_sources),
            "scores": {
                "source_count": round(source_count_score, 3),
                "trust": round(avg_trust_score, 3),
                "recency": round(recency_score, 3),
                "category": round(category_score, 3),
                "coverage": round(coverage_score, 3),
                "viral_potential": round(viral_score, 3),
            },
            "top_headline": articles[0]["headline"] if articles else "",
        }

    def _score_viral_potential(self, articles: list[dict]) -> float:
        """Score the viral potential of a story cluster for YouTube Shorts.
        
        Analyzes headlines and summaries for:
        - Strict policy check (disqualifies banned/NSFW keywords)
        - High-engagement trigger keywords (mode-aware)
        - Headline punchiness (shorter = more viral)
        - Multi-category crossover appeal
        - Emotional intensity signals
        """
        # Combine all text for keyword analysis
        all_text = " ".join(
            (a.get("headline", "") + " " + (a.get("summary", "") or "")).lower()
            for a in articles
        )

        # Policy check: Disqualify any cluster containing banned terms
        if any(banned in all_text for banned in BANNED_POLICY_KEYWORDS):
            return 0.0

        content_mode = getattr(settings, "content_mode", "entertainment")
        keywords_dict = COMEDY_VIRAL_KEYWORDS if content_mode == "entertainment" else NEWS_VIRAL_KEYWORDS

        score = 0.3  # Base score
        
        # Tier 1 keywords (highest viral signal)
        tier1_matches = sum(1 for kw in keywords_dict["tier1"] if kw in all_text)
        if tier1_matches >= 3:
            score += 0.35
        elif tier1_matches >= 1:
            score += 0.25
        
        # Tier 2 keywords (high viral signal)
        tier2_matches = sum(1 for kw in keywords_dict["tier2"] if kw in all_text)
        if tier2_matches >= 3:
            score += 0.20
        elif tier2_matches >= 1:
            score += 0.12
        
        # Tier 3 keywords (medium viral signal)
        tier3_matches = sum(1 for kw in keywords_dict["tier3"] if kw in all_text)
        if tier3_matches >= 2:
            score += 0.10
        elif tier3_matches >= 1:
            score += 0.05
        
        # Headline punchiness — shorter, more impactful headlines = more viral
        top_headline = articles[0].get("headline", "") if articles else ""
        headline_len = len(top_headline)
        if 20 <= headline_len <= 50:
            score += 0.10  # Sweet spot for Shorts titles
        elif headline_len > 80:
            score -= 0.05  # Too long for impact
        
        # Multi-category crossover (story spans multiple categories = broader appeal)
        unique_categories = set(a.get("category", "general") for a in articles)
        if len(unique_categories) >= 3:
            score += 0.10  # Multi-category crossover appeal
        elif len(unique_categories) >= 2:
            score += 0.05
        
        # Number presence in headlines (numbers boost engagement)
        if any(re.search(r'\d', a.get("headline", "")) for a in articles):
            score += 0.05
        
        return min(max(score, 0.0), 1.0)

        
# Stop words for title deduplication
DEDUP_STOP_WORDS = {
    "the", "a", "an", "and", "or", "but", "in", "on", "at", "to", "for", "of",
    "with", "by", "from", "up", "about", "into", "over", "after", "is", "are",
    "was", "were", "be", "been", "being", "have", "has", "had", "do", "does",
    "did", "will", "would", "shall", "should", "may", "might", "must", "can",
    "could", "this", "that", "these", "those", "what", "which", "who", "when",
    "where", "why", "how", "all", "any", "both", "each", "few", "more", "most",
    "other", "some", "such", "shorts", "video", "funny", "memes", "comedy",
}


def _clean_title_for_dedup(text: str) -> str:
    """Normalize title for fuzzy comparison."""
    if not text:
        return ""
    t = re.sub(r'#shorts\b', '', text, flags=re.IGNORECASE)
    t = re.sub(r'[^\w\s]', ' ', t.lower())
    return " ".join(t.split())


def is_duplicate_topic(candidate_text: str, used_titles: set[str]) -> bool:
    """
    Check if candidate story is a duplicate of any previously used title.
    Uses:
    1. Exact normalized match
    2. Substring containment
    3. Keyword / token overlap (>= 50% keyword similarity)
    """
    cand_clean = _clean_title_for_dedup(candidate_text)
    if not cand_clean or len(cand_clean) < 5:
        return False

    cand_words = {w for w in cand_clean.split() if len(w) >= 3 and w not in DEDUP_STOP_WORDS}

    for ut in used_titles:
        ut_clean = _clean_title_for_dedup(ut)
        if not ut_clean or len(ut_clean) < 5:
            continue

        # 1. Exact match
        if cand_clean == ut_clean:
            return True

        # 2. Substring match
        if len(cand_clean) >= 12 and (cand_clean in ut_clean or ut_clean in cand_clean):
            return True

        # 3. Word token overlap
        ut_words = {w for w in ut_clean.split() if len(w) >= 3 and w not in DEDUP_STOP_WORDS}
        if len(cand_words) >= 3 and len(ut_words) >= 3:
            overlap = len(cand_words & ut_words)
            min_len = min(len(cand_words), len(ut_words))
            if min_len > 0 and (overlap / min_len) >= 0.50:
                return True

    return False


async def rank_stories() -> list[dict]:
    """
    Main ranking entry point called by Celery task.
    Ranks all story clusters and returns them sorted by score.
    Strictly filters out:
    1. Clusters whose articles have already been turned into a Script (deduplication)
    2. Clusters matching any previously published YouTube video (persistent cross-run dedup)
    3. Clusters containing banned policy keywords (safety filter)
    """
    ranker = StoryRanker()

    async with async_session_factory() as db:
        # Step A: Collect all article IDs and titles already used in generated scripts (local DB)
        script_res = await db.execute(select(Script.article_ids, Script.title, Script.topic_summary))
        used_article_ids = set()
        used_titles = set()
        for aid_json, title, topic_summary in script_res.all():
            if aid_json:
                try:
                    loaded = json.loads(aid_json)
                    if isinstance(loaded, list):
                        used_article_ids.update(loaded)
                    elif isinstance(loaded, int):
                        used_article_ids.add(loaded)
                except Exception:
                    pass
            if title:
                used_titles.add(title.strip().lower())
            if topic_summary:
                used_titles.add(topic_summary.strip().lower())

        # Step A2: Also fetch already uploaded video titles directly from YouTube channel!
        # This provides persistent deduplication even on ephemeral CI/CD runners (e.g. GitHub Actions)
        try:
            from app.services.youtube.auth import get_recent_uploaded_titles
            yt_titles = get_recent_uploaded_titles(limit=50)
            for yt_t in yt_titles:
                if yt_t:
                    used_titles.add(yt_t.strip().lower())
            if yt_titles:
                logger.info(f"📺 Ingested {len(yt_titles)} live YouTube titles for persistent deduplication")
        except Exception as yt_err:
            logger.debug(f"YouTube title dedup fetch skipped: {yt_err}")

        # Step B: Get all unique cluster IDs
        result = await db.execute(
            select(NewsArticle.cluster_id)
            .where(NewsArticle.cluster_id.is_not(None))
            .distinct()
        )
        cluster_ids = [row[0] for row in result.all()]

        if not cluster_ids:
            logger.warning("No clusters found for ranking")
            return []

        # Build source trust map
        source_result = await db.execute(select(Source))
        sources = source_result.scalars().all()
        trust_map = {s.id: s.trust_score for s in sources}

        # Score each cluster
        scored_clusters = []
        for cluster_id in cluster_ids:
            articles_result = await db.execute(
                select(NewsArticle).where(NewsArticle.cluster_id == cluster_id)
            )
            articles = articles_result.scalars().all()

            # DEDUPLICATION 1: Skip cluster if any article in it has already been used in a Script
            if any(a.id in used_article_ids for a in articles):
                continue

            # DEDUPLICATION 2: Skip cluster if top headline or summary matches any existing script or YouTube video
            top_h = (articles[0].headline or "").strip() if articles else ""
            top_s = (articles[0].summary or "").strip() if articles else ""
            if top_h and is_duplicate_topic(top_h, used_titles):
                logger.info(f"🔄 Skipping duplicate story cluster (headline match): '{top_h[:60]}'")
                continue
            if top_s and is_duplicate_topic(top_s[:100], used_titles):
                logger.info(f"🔄 Skipping duplicate story cluster (summary match): '{top_s[:60]}'")
                continue

            article_dicts = [
                {
                    "id": a.id,
                    "source_id": a.source_id,
                    "headline": a.headline,
                    "summary": a.summary,
                    "category": a.category,
                    "published_at": a.published_at,
                }
                for a in articles
            ]

            # SAFETY: Skip cluster if top headline or summary has banned words
            all_text = " ".join(
                (a.get("headline", "") + " " + (a.get("summary", "") or "")).lower()
                for a in article_dicts
            )
            if any(banned in all_text for banned in BANNED_POLICY_KEYWORDS):
                logger.warning(f"🛡️ Skipping policy-violating cluster {cluster_id}: '{article_dicts[0]['headline'][:50]}'")
                continue

            score = ranker.score_cluster(cluster_id, article_dicts, trust_map)
            if score.get("total_score", 0) > 0:
                scored_clusters.append(score)

        # Sort by total score descending
        scored_clusters.sort(key=lambda x: x["total_score"], reverse=True)

        if scored_clusters:
            top = scored_clusters[0]
            logger.info(
                f"📊 Ranked {len(scored_clusters)} fresh story clusters (excluded {len(used_article_ids)} previously produced articles). "
                f"Top story: '{top['top_headline'][:60]}...' "
                f"(score: {top['total_score']}, viral: {top['scores']['viral_potential']})"
            )
        else:
            logger.info("No fresh unproduced stories to rank")

        return scored_clusters
