import pytest
from app.services.discovery.collector import NewsCollector
from app.services.discovery.google_news import GoogleNewsCollector


def test_google_news_source_extraction():
    collector = GoogleNewsCollector()
    source = collector._extract_source("Breaking News Event - Reuters")
    assert source == "Reuters"


def test_rss_parser_empty_feed():
    collector = NewsCollector()
    articles = collector.parse_rss_feed({"id": 1, "name": "Test", "rss_url": "invalid_url"})
    assert isinstance(articles, list)
    collector.close()
