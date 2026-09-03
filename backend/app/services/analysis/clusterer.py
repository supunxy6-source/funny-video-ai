"""
Stateside Smiles — Story Clusterer

Groups duplicate/related news stories using TF-IDF vectorization
and agglomerative clustering. This ensures we identify the same
story being reported by multiple sources.
"""

import logging
from typing import Optional

import numpy as np
from sklearn.cluster import AgglomerativeClustering
from sklearn.feature_extraction.text import TfidfVectorizer
from sklearn.metrics.pairwise import cosine_similarity
from sqlalchemy import select, update
from sqlalchemy.ext.asyncio import AsyncSession

from app.db.session import async_session_factory
from app.models.article import NewsArticle

logger = logging.getLogger(__name__)

# Clustering parameters
SIMILARITY_THRESHOLD = 0.35  # Articles above this similarity are clustered together
MIN_CLUSTER_SIZE = 1


class StoryClusterer:
    """Groups related news articles into story clusters."""

    def __init__(self):
        self.vectorizer = TfidfVectorizer(
            max_features=5000,
            stop_words="english",
            ngram_range=(1, 2),
            min_df=1,
            max_df=0.95,
        )

    def cluster_articles(
        self, articles: list[dict], threshold: float = SIMILARITY_THRESHOLD
    ) -> dict[int, list[int]]:
        """
        Cluster articles by headline + summary similarity.

        Returns:
            Dictionary mapping cluster_id -> list of article ids
        """
        if len(articles) < 2:
            return {0: [a["id"] for a in articles]} if articles else {}

        # Combine headline and summary for better similarity
        texts = [
            f"{a.get('headline', '')} {a.get('summary', '') or ''}"
            for a in articles
        ]

        # Vectorize texts
        try:
            tfidf_matrix = self.vectorizer.fit_transform(texts)
        except ValueError as e:
            logger.warning(f"TF-IDF vectorization failed: {e}")
            return {i: [a["id"]] for i, a in enumerate(articles)}

        # Compute similarity matrix
        similarity_matrix = cosine_similarity(tfidf_matrix)

        # Convert similarity to distance for clustering
        distance_matrix = 1 - similarity_matrix
        np.fill_diagonal(distance_matrix, 0)
        distance_matrix = np.maximum(distance_matrix, 0)  # Ensure non-negative

        # Agglomerative clustering
        try:
            clustering = AgglomerativeClustering(
                n_clusters=None,
                distance_threshold=1 - threshold,
                metric="precomputed",
                linkage="average",
            )
            labels = clustering.fit_predict(distance_matrix)
        except Exception as e:
            logger.warning(f"Clustering failed, treating each article as its own cluster: {e}")
            labels = list(range(len(articles)))

        # Group articles by cluster
        clusters: dict[int, list[int]] = {}
        for idx, label in enumerate(labels):
            cluster_id = int(label)
            if cluster_id not in clusters:
                clusters[cluster_id] = []
            clusters[cluster_id].append(articles[idx]["id"])

        logger.info(
            f"🔗 Clustered {len(articles)} articles into {len(clusters)} story groups"
        )

        return clusters


async def run_clustering() -> dict[int, list[int]]:
    """
    Main clustering entry point called by Celery task.
    Fetches unclustered articles, clusters them, and updates cluster_ids in DB.
    """
    clusterer = StoryClusterer()

    async with async_session_factory() as db:
        # Fetch articles without cluster assignments (recent only)
        result = await db.execute(
            select(NewsArticle)
            .where(NewsArticle.cluster_id.is_(None))
            .order_by(NewsArticle.created_at.desc())
            .limit(500)
        )
        articles = result.scalars().all()

        if not articles:
            logger.info("No unclustered articles found")
            return {}

        article_dicts = [
            {"id": a.id, "headline": a.headline, "summary": a.summary}
            for a in articles
        ]

        # Run clustering
        clusters = clusterer.cluster_articles(article_dicts)

        # Update cluster_ids in database
        for cluster_id, article_ids in clusters.items():
            await db.execute(
                update(NewsArticle)
                .where(NewsArticle.id.in_(article_ids))
                .values(cluster_id=cluster_id)
            )

        await db.commit()
        logger.info(f"💾 Updated cluster assignments for {len(articles)} articles")

        return clusters
