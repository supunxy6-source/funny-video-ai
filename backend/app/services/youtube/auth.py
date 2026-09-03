"""
Stateside Smiles — YouTube OAuth2 Authentication

Handles OAuth2 credential management for YouTube Data API v3.
Supports initial browser-based auth and automatic token refresh.
"""

import json
import logging
from pathlib import Path
from typing import Optional

from google.auth.transport.requests import Request
from google.oauth2.credentials import Credentials
from google_auth_oauthlib.flow import InstalledAppFlow

try:
    from app.core.config import settings
    CLIENT_SECRETS_FILE = getattr(settings, "youtube_client_secrets_file", "config/client_secrets.json")
    TOKEN_FILE = getattr(settings, "youtube_token_file", "config/youtube_token.json")
except Exception:
    CLIENT_SECRETS_FILE = "config/client_secrets.json"
    TOKEN_FILE = "config/youtube_token.json"

logger = logging.getLogger(__name__)

SCOPES = [
    "https://www.googleapis.com/auth/youtube.upload",
    "https://www.googleapis.com/auth/youtube",
    "https://www.googleapis.com/auth/youtube.force-ssl",
]


def _find_config_file(filename: str, configured_path: str) -> Path:
    """Find a configuration or credential file across multiple candidate paths."""
    candidates = [
        Path(configured_path),
        Path("config") / filename,
        Path("backend/config") / filename,
        Path("/app/config") / filename,
        Path(__file__).resolve().parent.parent.parent.parent / "config" / filename,
        Path(__file__).resolve().parent.parent.parent / "config" / filename,
    ]
    for candidate in candidates:
        if candidate.exists():
            return candidate
    return Path(configured_path)


def get_youtube_credentials() -> Credentials:
    """
    Get valid YouTube API credentials.
    Loads existing token or initiates OAuth2 flow.
    """
    token_path = _find_config_file("youtube_token.json", TOKEN_FILE)
    client_secrets_path = _find_config_file("client_secrets.json", CLIENT_SECRETS_FILE)

    creds = None

    # Load existing token
    if token_path.exists():
        try:
            creds = Credentials.from_authorized_user_file(str(token_path), SCOPES)
            logger.info(f"🔑 Loaded existing YouTube credentials from {token_path}")
        except Exception as e:
            logger.warning(f"Failed to load token file ({token_path}): {e}")

    # Refresh if expired
    if creds and (creds.expired or not creds.valid) and creds.refresh_token:
        try:
            creds.refresh(Request())
            logger.info("🔄 YouTube credentials refreshed successfully")
            _save_token(creds, token_path)
        except Exception as e:
            logger.warning(f"Token refresh failed: {e}")

    if not creds or not creds.valid:
        if not token_path.exists():
            raise FileNotFoundError(
                f"YouTube token file not found at {token_path}. "
                "Local fallback active. Complete OAuth login to publish to live channel."
            )

        if not client_secrets_path.exists():
            raise FileNotFoundError(
                f"YouTube client secrets not found at {client_secrets_path}."
            )

        raise RuntimeError("YouTube OAuth token expired or invalid.")

    return creds


def _save_token(creds: Credentials, token_path: Path) -> None:
    """Save credentials to a token file with error handling."""
    try:
        token_path.parent.mkdir(parents=True, exist_ok=True)
        with open(token_path, "w", encoding="utf-8") as f:
            f.write(creds.to_json())
        logger.info(f"💾 YouTube token saved to {token_path}")
    except Exception as e:
        logger.warning(f"Could not persist updated token to disk ({token_path}): {e}")


def is_authenticated() -> bool:
    """Check if YouTube credentials are valid."""
    try:
        creds = get_youtube_credentials()
        return creds is not None and creds.valid
    except Exception:
        return False


def get_channel_info() -> dict:
    """Fetch profile information for the authenticated YouTube channel."""
    try:
        from googleapiclient.discovery import build
        creds = get_youtube_credentials()
        youtube = build("youtube", "v3", credentials=creds)
        resp = youtube.channels().list(part="snippet,statistics", mine=True).execute()
        items = resp.get("items", [])
        if not items:
            return {"authenticated": False, "error": "No channel found"}
        channel = items[0]
        snippet = channel.get("snippet", {})
        stats = channel.get("statistics", {})
        return {
            "authenticated": True,
            "channel_id": channel.get("id"),
            "title": snippet.get("title", "Unknown Channel"),
            "custom_url": snippet.get("customUrl", ""),
            "subscriber_count": int(stats.get("subscriberCount", 0)),
            "view_count": int(stats.get("viewCount", 0)),
            "video_count": int(stats.get("videoCount", 0)),
            "thumbnail_url": snippet.get("thumbnails", {}).get("default", {}).get("url", ""),
        }
    except Exception as e:
        logger.warning(f"Failed to fetch YouTube channel info: {e}")
        return {"authenticated": False, "error": str(e)}


def authenticate_interactive() -> Credentials:
    """
    Run an interactive browser OAuth2 flow to authenticate with YouTube API
    and save credentials to the configured token file.
    """
    client_secrets_path = _find_config_file("client_secrets.json", CLIENT_SECRETS_FILE)
    token_path = _find_config_file("youtube_token.json", TOKEN_FILE)

    if not client_secrets_path.exists():
        raise FileNotFoundError(
            f"YouTube client secrets file not found at {client_secrets_path}. "
            "Please place your OAuth 2.0 client secrets JSON at this location."
        )

    print("\n🌐 Opening browser for YouTube OAuth2 authentication...")
    print("👉 Log into your YouTube account and click 'Allow' to grant upload access.\n")

    flow = InstalledAppFlow.from_client_secrets_file(
        str(client_secrets_path),
        scopes=SCOPES,
    )
    creds = flow.run_local_server(port=0)
    _save_token(creds, token_path)
    print(f"\n🎉 Success! YouTube credentials saved to {token_path}")
    return creds


if __name__ == "__main__":
    logging.basicConfig(level=logging.INFO)
    try:
        authenticate_interactive()
    except Exception as e:
        print(f"❌ OAuth authentication failed: {e}")


