import pytest
from app.services.analysis.clusterer import StoryClusterer
from app.services.analysis.ranker import StoryRanker
from app.services.analysis.verifier import StoryVerifier


def test_story_clustering():
    clusterer = StoryClusterer()
    articles = [
        {"id": 1, "headline": "Federal Reserve Cuts Interest Rates by 50 bps", "summary": "Fed lowers benchmark rate."},
        {"id": 2, "headline": "Fed Announces 50 Basis Point Rate Cut", "summary": "US central bank slashes interest rates."},
        {"id": 3, "headline": "SpaceX Launches Starship Rocket Test Flight", "summary": "Starship reaches orbit successfully."},
    ]
    clusters = clusterer.cluster_articles(articles)
    assert len(clusters) >= 2


def test_story_verifier():
    verifier = StoryVerifier()
    trust_map = {1: 0.95, 2: 0.90, 3: 0.85}
    articles = [
        {"id": 101, "source_id": 1, "headline": "Verified Headline 1"},
        {"id": 102, "source_id": 2, "headline": "Verified Headline 2"},
        {"id": 103, "source_id": 3, "headline": "Verified Headline 3"},
    ]
    res = verifier.verify_cluster(1, articles, trust_map)
    assert res["is_verified"] is True
    assert res["source_count"] == 3
