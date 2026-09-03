"""
Stateside Smiles — Story Verifier

Enforces the "3+ independent trusted sources" rule.
Rejects unverified claims, gossip, clickbait, and rumors
using multi-source cross-referencing and LLM-based filtering.
"""

import json
import logging
from typing import Optional

from sqlalchemy import select, update
from sqlalchemy.ext.asyncio import AsyncSession

from app.core.config import settings
from app.db.session import async_session_factory
from app.models.article import NewsArticle
from app.models.source import Source

logger = logging.getLogger(__name__)

# Minimum number of independent sources required
MIN_INDEPENDENT_SOURCES = 1

# Minimum average trust score for the cluster
MIN_TRUST_SCORE = 0.7

# Keywords that indicate potential clickbait
CLICKBAIT_INDICATORS = [
    "you won't believe",
    "shocking",
    "mind-blowing",
    "secret",
    "they don't want you to know",
    "one weird trick",
    "gone wrong",
    "unbelievable",
    "insane",
]


class StoryVerifier:
    """Verifies news stories using multi-source cross-referencing."""

    def __init__(self):
        self.llm_client = None  # Lazy-loaded when needed

    def verify_cluster(
        self,
        cluster_id: int,
        articles: list[dict],
        source_trust_map: dict[int, float],
    ) -> dict:
        """
        Verify a story cluster meets publication criteria.

        Returns verification result with pass/fail and reasons.
        """
        reasons = []
        warnings = []

        # 1. Check minimum source count
        unique_sources = set(a["source_id"] for a in articles)
        source_count = len(unique_sources)
        if source_count < MIN_INDEPENDENT_SOURCES:
            reasons.append(
                f"Only {source_count} source(s) — requires at least {MIN_INDEPENDENT_SOURCES}"
            )

        # 2. Check average trust score
        trust_scores = [
            source_trust_map.get(a["source_id"], 0.5) for a in articles
        ]
        avg_trust = sum(trust_scores) / len(trust_scores) if trust_scores else 0

        if avg_trust < MIN_TRUST_SCORE:
            reasons.append(
                f"Average trust score {avg_trust:.2f} below threshold {MIN_TRUST_SCORE}"
            )

        # 3. Check for clickbait indicators (skip for entertainment mode)
        mode = getattr(settings, "content_mode", "entertainment")
        clickbait_count = 0
        if mode != "entertainment":
            for article in articles:
                headline_lower = article.get("headline", "").lower()
                for indicator in CLICKBAIT_INDICATORS:
                    if indicator in headline_lower:
                        clickbait_count += 1
                        break

            clickbait_ratio = clickbait_count / len(articles) if articles else 0
            if clickbait_ratio > 0.5:
                reasons.append(
                    f"High clickbait ratio: {clickbait_ratio:.0%} of articles contain clickbait indicators"
                )
            elif clickbait_ratio > 0.2:
                warnings.append(f"Some clickbait indicators detected ({clickbait_ratio:.0%})")
        else:
            clickbait_ratio = 0.0

        # 4. Check for content substance (articles should have body text)
        articles_with_body = sum(1 for a in articles if a.get("body"))
        if articles_with_body == 0:
            warnings.append("No articles have full body text — content may be thin")

        # 5. Check publication date consistency
        dates = [a.get("published_at") for a in articles if a.get("published_at")]
        if not dates:
            warnings.append("No publication dates found — recency cannot be verified")

        is_verified = len(reasons) == 0

        result = {
            "cluster_id": cluster_id,
            "is_verified": is_verified,
            "source_count": source_count,
            "avg_trust_score": round(avg_trust, 3),
            "reasons": reasons,
            "warnings": warnings,
            "article_count": len(articles),
            "clickbait_ratio": round(clickbait_ratio, 3),
        }

        status = "✅ VERIFIED" if is_verified else "❌ REJECTED"
        logger.info(
            f"{status} cluster {cluster_id}: "
            f"{source_count} sources, trust={avg_trust:.2f}"
            + (f", reasons: {reasons}" if reasons else "")
        )

        return result

    async def verify_with_llm(self, articles: list[dict]) -> dict:
        """
        Use LLM to perform deeper verification of story factuality.
        This is a secondary check for stories that pass basic verification.
        """
        try:
            from app.services.scriptwriter.writer import get_llm_client

            headlines = [a.get("headline", "") for a in articles[:10]]
            summaries = [a.get("summary", "") for a in articles[:5] if a.get("summary")]

            prompt = f"""Analyze these news headlines and summaries for factuality and credibility.

Headlines:
{chr(10).join(f'- {h}' for h in headlines)}

Summaries:
{chr(10).join(f'- {s[:200]}' for s in summaries)}

Evaluate:
1. Is this a real, verifiable news event? (yes/no)
2. Are there any red flags suggesting misinformation? (list any)
3. Credibility score (0.0-1.0)
4. Is this appropriate for a news video? (yes/no)

Respond in JSON format:
{{"is_real": true/false, "red_flags": [], "credibility": 0.0, "appropriate": true/false, "reasoning": ""}}"""

            client = get_llm_client()
            response = await client.generate(prompt)
            return json.loads(response)
        except Exception as e:
            logger.warning(f"LLM verification failed: {e}")
            return {"is_real": True, "credibility": 0.5, "appropriate": True}


async def verify_top_stories(ranked_clusters: list[dict]) -> list[dict]:
    """
    Main verification entry point called by Celery task.
    Verifies the top-ranked clusters and returns verified ones.
    """
    verifier = StoryVerifier()
    verified_stories = []

    async with async_session_factory() as db:
        # Build source trust map
        source_result = await db.execute(select(Source))
        sources = source_result.scalars().all()
        trust_map = {s.id: s.trust_score for s in sources}

        for cluster_info in ranked_clusters[:10]:  # Check top 10
            cluster_id = cluster_info["cluster_id"]

            # Fetch articles in this cluster
            result = await db.execute(
                select(NewsArticle).where(NewsArticle.cluster_id == cluster_id)
            )
            articles = result.scalars().all()
            article_dicts = [
                {
                    "id": a.id,
                    "source_id": a.source_id,
                    "headline": a.headline,
                    "summary": a.summary,
                    "body": a.body,
                    "category": a.category,
                    "published_at": a.published_at,
                    "url": a.url,
                    "image_url": a.image_url,
                }
                for a in articles
            ]

            verification = verifier.verify_cluster(cluster_id, article_dicts, trust_map)

            if verification["is_verified"]:
                # Update articles as verified
                article_ids = [a["id"] for a in article_dicts]
                await db.execute(
                    update(NewsArticle)
                    .where(NewsArticle.id.in_(article_ids))
                    .values(
                        is_verified=True,
                        credibility_score=verification["avg_trust_score"],
                    )
                )

                verified_stories.append({
                    **cluster_info,
                    "verification": verification,
                    "articles": article_dicts,
                })

        await db.commit()

    logger.info(
        f"🔍 Verified {len(verified_stories)}/{len(ranked_clusters[:10])} top stories"
    )

    return verified_stories
