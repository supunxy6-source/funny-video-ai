"""
Stateside Smiles — TikTok OAuth 2.0 Authentication

Manages TikTok API credentials and token lifecycle.
Tokens are stored in config/tiktok_token.json (same pattern as YouTube).
"""

import json
import logging
import os
import time
from pathlib import Path
from typing import Optional

import requests

logger = logging.getLogger(__name__)

# TikTok OAuth endpoints
TIKTOK_AUTH_URL = "https://www.tiktok.com/v2/auth/authorize/"
TIKTOK_TOKEN_URL = "https://open.tiktokapis.com/v2/oauth/token/"
TIKTOK_USER_INFO_URL = "https://open.tiktokapis.com/v2/user/info/"


def _get_token_path() -> Path:
    """Return the path to the stored TikTok token file."""
    from app.core.config import settings
    return Path(settings.media_root).parent / "config" / "tiktok_token.json"


def _load_stored_token() -> Optional[dict]:
    """Load stored token from disk."""
    token_path = _get_token_path()
    if not token_path.exists():
        return None
    try:
        with open(token_path) as f:
            return json.load(f)
    except (json.JSONDecodeError, OSError) as e:
        logger.warning(f"Failed to load TikTok token: {e}")
        return None


def _save_token(token_data: dict) -> None:
    """Persist token data to disk."""
    token_path = _get_token_path()
    token_path.parent.mkdir(parents=True, exist_ok=True)
    with open(token_path, "w") as f:
        json.dump(token_data, f, indent=2)
    logger.info("🔑 TikTok token saved to disk")


def get_tiktok_credentials() -> dict:
    """
    Get valid TikTok access credentials.

    Returns a dict with 'access_token' and 'open_id'.
    Attempts to refresh the token if it's expired.
    """
    from app.core.config import settings

    # First check: direct access token from env/config
    access_token = getattr(settings, "tiktok_access_token", "") or os.getenv("TIKTOK_ACCESS_TOKEN", "")
    if access_token:
        stored = _load_stored_token()
        open_id = (stored or {}).get("open_id", "")
        return {"access_token": access_token, "open_id": open_id}

    # Second check: stored token file
    stored = _load_stored_token()
    if not stored:
        raise FileNotFoundError(
            "TikTok credentials not configured. "
            "Set TIKTOK_ACCESS_TOKEN in .env or run the TikTok OAuth setup."
        )

    # Check if token needs refresh
    expires_at = stored.get("expires_at", 0)
    if time.time() >= expires_at - 300:  # Refresh 5 min before expiry
        stored = refresh_tiktok_token(stored.get("refresh_token", ""))

    return {
        "access_token": stored["access_token"],
        "open_id": stored.get("open_id", ""),
    }


def refresh_tiktok_token(refresh_token: str) -> dict:
    """
    Refresh an expired TikTok access token.

    Returns the updated token data and persists it to disk.
    """
    from app.core.config import settings

    client_key = getattr(settings, "tiktok_client_key", "") or os.getenv("TIKTOK_CLIENT_KEY", "")
    client_secret = getattr(settings, "tiktok_client_secret", "") or os.getenv("TIKTOK_CLIENT_SECRET", "")

    if not client_key or not client_secret:
        raise ValueError(
            "TIKTOK_CLIENT_KEY and TIKTOK_CLIENT_SECRET are required for token refresh. "
            "Set them in .env or pass them to the configuration."
        )

    if not refresh_token:
        raise ValueError(
            "No refresh token available. Re-authorize via the TikTok OAuth flow."
        )

    response = requests.post(
        TIKTOK_TOKEN_URL,
        headers={"Content-Type": "application/x-www-form-urlencoded"},
        data={
            "client_key": client_key,
            "client_secret": client_secret,
            "grant_type": "refresh_token",
            "refresh_token": refresh_token,
        },
        timeout=15,
    )

    result = response.json()

    if result.get("error") or "access_token" not in result:
        error_desc = result.get("error_description", result.get("error", "Unknown error"))
        raise RuntimeError(f"TikTok token refresh failed: {error_desc}")

    token_data = {
        "access_token": result["access_token"],
        "refresh_token": result.get("refresh_token", refresh_token),
        "open_id": result.get("open_id", ""),
        "expires_at": time.time() + result.get("expires_in", 86400),
        "refresh_expires_at": time.time() + result.get("refresh_expires_in", 86400 * 365),
    }

    _save_token(token_data)
    logger.info("🔑 TikTok access token refreshed successfully")
    return token_data


def get_tiktok_user_info() -> dict:
    """
    Fetch TikTok user profile information.
    Returns account details for display in the settings dashboard.
    """
    from app.core.config import settings

    try:
        creds = get_tiktok_credentials()
    except (FileNotFoundError, ValueError) as e:
        return {"connected": False, "error": str(e)}

    try:
        response = requests.get(
            TIKTOK_USER_INFO_URL,
            headers={"Authorization": f"Bearer {creds['access_token']}"},
            params={"fields": "open_id,union_id,avatar_url,display_name,follower_count,following_count,likes_count,video_count"},
            timeout=10,
        )
        data = response.json()

        if data.get("error", {}).get("code") != "ok" and "data" not in data:
            error_msg = data.get("error", {}).get("message", "Unknown error")
            return {"connected": False, "error": error_msg}

        user_data = data.get("data", {}).get("user", {})
        return {
            "connected": True,
            "open_id": user_data.get("open_id", creds.get("open_id", "")),
            "display_name": user_data.get("display_name", "TikTok User"),
            "avatar_url": user_data.get("avatar_url", ""),
            "follower_count": user_data.get("follower_count", 0),
            "following_count": user_data.get("following_count", 0),
            "likes_count": user_data.get("likes_count", 0),
            "video_count": user_data.get("video_count", 0),
        }

    except Exception as e:
        logger.warning(f"Failed to fetch TikTok user info: {e}")
        return {"connected": False, "error": str(e)}
