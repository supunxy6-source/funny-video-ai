import pytest
from app.services.youtube.auth import SCOPES


def test_youtube_auth_scopes():
    assert "https://www.googleapis.com/auth/youtube.upload" in SCOPES
