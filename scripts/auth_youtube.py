"""
Stateside Smiles — YouTube OAuth Authentication Helper

Use this script to check, refresh, or re-authenticate YouTube API credentials.

Usage:
    python scripts/auth_youtube.py --check         # Check current token status
    python scripts/auth_youtube.py --login         # Open browser to authenticate
    python scripts/auth_youtube.py --print-secret  # Output token JSON for GitHub Actions Secret
"""

import sys
import json
import argparse
from pathlib import Path

# Add backend directory to sys.path
backend_dir = Path(__file__).parent.parent / "backend"
sys.path.insert(0, str(backend_dir))

from google.oauth2.credentials import Credentials
from google.auth.transport.requests import Request
from google_auth_oauthlib.flow import InstalledAppFlow
from googleapiclient.discovery import build

SCOPES = [
    "https://www.googleapis.com/auth/youtube.upload",
    "https://www.googleapis.com/auth/youtube",
    "https://www.googleapis.com/auth/youtube.force-ssl",
]

PROJECT_ROOT = Path(__file__).parent.parent
CONFIG_PATHS = [
    PROJECT_ROOT / "config",
    PROJECT_ROOT / "backend" / "config",
]


def _find_file(filename: str) -> Path | None:
    for base in CONFIG_PATHS:
        p = base / filename
        if p.exists():
            return p
    return PROJECT_ROOT / "config" / filename


def _save_to_all(filename: str, content: str):
    for base in CONFIG_PATHS:
        try:
            base.mkdir(parents=True, exist_ok=True)
            target = base / filename
            target.write_text(content, encoding="utf-8")
            print(f"  💾 Saved to {target}")
        except Exception as e:
            print(f"  ⚠️ Warning saving to {base / filename}: {e}")


def check_status() -> bool:
    print("\n🔍 Checking YouTube OAuth Token Status...")
    secrets_path = _find_file("client_secrets.json")
    token_path = _find_file("youtube_token.json")

    if not secrets_path or not secrets_path.exists():
        print(f"❌ client_secrets.json NOT found (checked {CONFIG_PATHS})")
        return False
    print(f"✅ client_secrets.json found at {secrets_path}")

    if not token_path or not token_path.exists():
        print(f"❌ youtube_token.json NOT found at {token_path}")
        print("👉 Run: python scripts/auth_youtube.py --login")
        return False
    print(f"✅ youtube_token.json found at {token_path}")

    try:
        with open(token_path, "r", encoding="utf-8") as f:
            data = json.load(f)
        creds = Credentials.from_authorized_user_info(data, SCOPES)
    except Exception as e:
        print(f"❌ Failed to parse youtube_token.json: {e}")
        return False

    print(f"ℹ️ Token expired: {creds.expired}")
    print(f"ℹ️ Has refresh token: {bool(creds.refresh_token)}")

    if creds.expired or not creds.valid:
        print("🔄 Attempting to refresh token using refresh_token...")
        try:
            creds.refresh(Request())
            _save_to_all("youtube_token.json", creds.to_json())
            print(f"🎉 Token refreshed successfully! New expiry: {creds.expiry}")
        except Exception as e:
            print(f"\n❌ Token refresh failed: {e}")
            print("\n📋 Common Causes:")
            print("  1. Google Cloud OAuth Consent Screen is in 'Testing' mode:")
            print("     -> Refresh tokens automatically expire after 7 days!")
            print("     -> Fix: In Google Cloud Console (OAuth consent screen), click 'PUBLISH APP' (In production).")
            print("  2. Token was revoked or Google account password was changed.")
            print("\n👉 To fix, run: python scripts/auth_youtube.py --login")
            return False

    # Verify API access by querying channel
    try:
        youtube = build("youtube", "v3", credentials=creds)
        resp = youtube.channels().list(part="snippet,statistics", mine=True).execute()
        items = resp.get("items", [])
        if items:
            channel = items[0]
            snippet = channel.get("snippet", {})
            stats = channel.get("statistics", {})
            print("\n✅ YouTube API Authentication Verified!")
            print(f"   Channel:      {snippet.get('title')}")
            print(f"   Channel ID:   {channel.get('id')}")
            print(f"   Subscribers:  {stats.get('subscriberCount', 0)}")
            print(f"   Videos:       {stats.get('videoCount', 0)}")
            return True
        else:
            print("⚠️ Authenticated, but no YouTube channel found for this Google account.")
            return True
    except Exception as e:
        print(f"❌ YouTube API test query failed: {e}")
        return False


def login():
    print("\n🌐 Starting YouTube OAuth2 Interactive Flow...")
    secrets_path = _find_file("client_secrets.json")
    if not secrets_path or not secrets_path.exists():
        print(f"❌ Missing client_secrets.json. Place it in config/client_secrets.json")
        sys.exit(1)

    print(f"Using client secrets from: {secrets_path}")
    print("👉 A browser window will open. Sign in to your YouTube account and click 'Allow'.\n")

    flow = InstalledAppFlow.from_client_secrets_file(
        str(secrets_path),
        scopes=SCOPES,
    )
    creds = flow.run_local_server(port=0)

    token_json = creds.to_json()
    print("\n🎉 Authentication successful!")
    _save_to_all("youtube_token.json", token_json)

    # Check channel
    try:
        youtube = build("youtube", "v3", credentials=creds)
        resp = youtube.channels().list(part="snippet", mine=True).execute()
        items = resp.get("items", [])
        if items:
            print(f"📺 Connected Channel: {items[0]['snippet'].get('title')} ({items[0].get('id')})")
    except Exception as e:
        print(f"⚠️ Channel lookup: {e}")

    print("\n" + "=" * 60)
    print("📢 IMPORTANT FOR GITHUB ACTIONS CI/CD:")
    print("Copy the JSON below and update your GitHub Repository Secret:")
    print("Repository -> Settings -> Secrets and variables -> Actions -> YOUTUBE_TOKEN")
    print("=" * 60)
    print(token_json)
    print("=" * 60)


def print_secret():
    token_path = _find_file("youtube_token.json")
    if not token_path or not token_path.exists():
        print(f"❌ youtube_token.json not found at {token_path}")
        sys.exit(1)
    print(token_path.read_text(encoding="utf-8"))


if __name__ == "__main__":
    parser = argparse.ArgumentParser(description="Stateside Smiles YouTube OAuth Helper")
    group = parser.add_mutually_exclusive_group()
    group.add_argument("--check", action="store_true", help="Check token validity and refresh if possible")
    group.add_argument("--login", action="store_true", help="Run interactive browser OAuth login")
    group.add_argument("--print-secret", action="store_true", help="Print token content for GitHub Secret")

    args = parser.parse_args()

    if args.login:
        login()
    elif args.print_secret:
        print_secret()
    else:
        # Default action is check
        success = check_status()
        if not success:
            sys.exit(1)
