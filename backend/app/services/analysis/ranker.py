"""
Stateside Smiles — Story Ranker (Views-Optimized Edition)

Ranks story clusters by newsworthiness using a weighted scoring model
that considers source count, trust scores, recency, category importance,
coverage breadth, and VIRAL POTENTIAL.

VIEWS OPTIMIZATION: Added viral potential scoring dimension that boosts
stories with high-engagement keywords, emotional triggers, and topic
crossover appeal. Rebalanced category scores for Shorts performance.
"""

import logging
import re
from datetime import datetime, timezone
from typing import Optional

from sqlalchemy import select, func
from sqlalchemy.ext.asyncio import AsyncSession

from app.db.session import async_session_factory
from app.models.article import NewsArticle
from app.models.source import Source

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

# Keywords that indicate viral potential on YouTube Shorts
VIRAL_KEYWORDS = {
    "tier1": [  # Highest viral potential — controversy, disaster, big money
        "killed", "dead", "dies", "death", "murder", "shooting", "explosion",
        "crash", "disaster", "earthquake", "hurricane", "war", "attack",
        "billion", "million", "trillion", "scandal", "exposed", "leaked",
        "arrested", "fired", "resigned", "banned", "illegal", "fraud",
    ],
    "tier2": [  # High viral — celebrity, tech, emotion
        "ai", "artificial intelligence", "elon musk", "tesla", "apple",
        "google", "openai", "chatgpt", "crypto", "bitcoin", "celebrity",
        "famous", "viral", "shocking", "incredible", "insane", "record",
        "first ever", "never before", "historic", "breakthrough",
        "warning", "emergency", "urgent", "crisis", "pandemic",
    ],
    "tier3": [  # Medium viral — curiosity, trends
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
        - High-engagement trigger keywords (tiered)
        - Headline punchiness (shorter = more viral)
        - Multi-category crossover appeal
        - Emotional intensity signals
        """
        score = 0.3  # Base score
        
        # Combine all text for keyword analysis
        all_text = " ".join(
            (a.get("headline", "") + " " + (a.get("summary", "") or "")).lower()
            for a in articles
        )
        
        # Tier 1 keywords (highest viral signal)
        tier1_matches = sum(1 for kw in VIRAL_KEYWORDS["tier1"] if kw in all_text)
        if tier1_matches >= 3:
            score += 0.35
        elif tier1_matches >= 1:
            score += 0.25
        
        # Tier 2 keywords (high viral signal)
        tier2_matches = sum(1 for kw in VIRAL_KEYWORDS["tier2"] if kw in all_text)
        if tier2_matches >= 3:
            score += 0.20
        elif tier2_matches >= 1:
            score += 0.12
        
        # Tier 3 keywords (medium viral signal)
        tier3_matches = sum(1 for kw in VIRAL_KEYWORDS["tier3"] if kw in all_text)
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


async def rank_stories() -> list[dict]:
    """
    Main ranking entry point called by Celery task.
    Ranks all story clusters and returns them sorted by score.
    """
    ranker = StoryRanker()

    async with async_session_factory() as db:
        # Get all unique cluster IDs
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

            score = ranker.score_cluster(cluster_id, article_dicts, trust_map)
            scored_clusters.append(score)

        # Sort by total score descending
        scored_clusters.sort(key=lambda x: x["total_score"], reverse=True)

        if scored_clusters:
            top = scored_clusters[0]
            logger.info(
                f"📊 Ranked {len(scored_clusters)} story clusters. "
                f"Top story: '{top['top_headline'][:60]}...' "
                f"(score: {top['total_score']}, viral: {top['scores']['viral_potential']})"
            )
        else:
            logger.info("No stories to rank")

        return scored_clusters
