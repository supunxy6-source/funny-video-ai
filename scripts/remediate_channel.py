"""
Stateside Smiles — Channel Remediation CLI

Applies automated fixes to the YouTube channel:
1. Privatizes duplicate video uploads to clear YouTube's spam/reused content penalty.
2. Privatizes or sanitizes policy-violating titles ("murder", "humping").
3. Revitalizes active 0-view videos with viral, high-CTR curiosity hooks.

Usage:
    python scripts/remediate_channel.py --dry-run
    python scripts/remediate_channel.py --execute
"""

import argparse
import json
import sys
from pathlib import Path

# Add backend directory to sys.path
backend_dir = Path(__file__).parent.parent / "backend"
sys.path.insert(0, str(backend_dir))

from google.oauth2.credentials import Credentials
from google.auth.transport.requests import Request
from googleapiclient.discovery import build

TOKEN_FILE = Path(__file__).parent.parent / "config" / "youtube_token.json"


def get_youtube_client():
    if not TOKEN_FILE.exists():
        raise FileNotFoundError(f"YouTube token file not found at {TOKEN_FILE}")

    with open(TOKEN_FILE, "r") as f:
        token_data = json.load(f)

    creds = Credentials(
        token=token_data.get("token"),
        refresh_token=token_data.get("refresh_token"),
        token_uri=token_data.get("token_uri", "https://oauth2.googleapis.com/token"),
        client_id=token_data.get("client_id"),
        client_secret=token_data.get("client_secret"),
        scopes=token_data.get("scopes", []),
    )

    if creds.expired and creds.refresh_token:
        creds.refresh(Request())
        with open(TOKEN_FILE, "w") as f:
            f.write(creds.to_json())

    return build("youtube", "v3", credentials=creds)


# Videos to privatize to clear duplicate / policy penalty
# Format: video_id -> reason
VIDEOS_TO_PRIVATIZE = {
    # Policy violations
    "smWweCTsWf8": "Policy violation: 'incitement to murder' (violence flag)",
    "sAvqjQByKtw": "Policy violation: 'Humping The Rainbow' (NSFW slang, 0 views)",
    "2p4kKVaQ9Ns": "Policy violation: 'Humping The Rainbow' (NSFW slang, 2 views)",
    
    # Duplicates of 'You're invited to Reddit's first-ever' (kept 8sdsiSlTl9o with 928 views)
    "5mU5vPyXMRk": "Duplicate: Reddit first-ever (14 views vs 928 views)",
    "Ndt08kTJSYM": "Duplicate: Reddit first-ever (179 views vs 928 views)",
    "W35Sm12LP5s": "Duplicate: Reddit first-ever (236 views vs 928 views)",

    # Duplicates of 'Failed attempt at leaning on a car' (kept Fy5T4FT2nMI with 880 views)
    "84nYXEOSvvU": "Duplicate: Leaning on a car (769 views vs 880 views)",

    # Duplicates of 'Two mice throwing hands' (kept -fqTUcC1a_s with 62 views)
    "V3LkRanHeso": "Duplicate: Two mice fighting (44 views vs 62 views)",
    "rDtqHI1WJNs": "Duplicate: Two mice fighting (57 views vs 62 views)",

    # Duplicate of 'The death of Julius Caesar' (kept jANx_fiyXnQ with 362 views)
    "Ea3SbM53jf4": "Duplicate: Julius Caesar (279 views vs 362 views)",

    # Duplicate of 'Apparently the scary floor doesn’t count' (kept -IjlEqZi4D8 with 731 views)
    "uJu_z5Ues0o": "Duplicate: Scary floor (188 views vs 731 views)",

    # Duplicate of 'Real technique from Unai Emery' (kept 8PxbnehY3eU with 13 views)
    "e_ZKIHuGYrc": "Duplicate: Unai Emery technique (10 views vs 13 views)",
}

# Videos to update with high-CTR curiosity hooks and safe titles
VIDEOS_TO_UPDATE_TITLES = {
    # Sanitize high-view policy violation to safe viral comedy title
    "asFggRdKFDk": "Bro took this way too seriously 💀 #Shorts",

    # Revitalize active 0-view and low-view videos with viral hooks
    "5rApaBtlsH0": "He really built a car with TWO front ends 💀🚗 #Shorts",
    "o50wp0tY7dQ": "They replaced the sidewalk and forgot one thing 😭 #Shorts",
    "UpyT7ok--VY": "Wait till the end... instant regret 😭 #Shorts",
    "KKQ51QINU28": "My last two braincells trying their best 💀 #Shorts",
    "CU9TDXSU7kM": "Subway vs Pita Pit: The disrespect is crazy 🥪😂 #Shorts",
    "vWvwNU9xnM0": "Tag someone who needs this immediately 😭 #Shorts",
    "HE6_scH6tto": "The one place you should NEVER enter 💀 #Shorts",
    "S2zsdURXt7c": "When they replace your entire team with AI 😭 #Shorts",
    "spkIOYeJGdA": "Grocery Outlet bargains got out of hand 😭🛒 #Shorts",
    "ZFrZEBM_Skc": "Amazon curbside pickup did NOT go as planned 💀📦 #Shorts",
    "pHf65tTkULU": "Wait for what he says next... 😂 #Shorts",
}


def remediate_channel(execute: bool = False):
    youtube = get_youtube_client()

    print("\n" + "=" * 65)
    print(f"🛠️ STATESIDE SMILES — CHANNEL REMEDIATION ({'EXECUTE' if execute else 'DRY RUN'})")
    print("=" * 65 + "\n")

    # Step 1: Privatize duplicates and policy violations
    print("🔒 Step 1: Privatizing Duplicate & Policy-Flagged Videos...")
    for vid_id, reason in VIDEOS_TO_PRIVATIZE.items():
        print(f"  • Video {vid_id}: {reason}")
        if execute:
            try:
                youtube.videos().update(
                    part="status",
                    body={
                        "id": vid_id,
                        "status": {
                            "privacyStatus": "private",
                            "selfDeclaredMadeForKids": False,
                        },
                    },
                ).execute()
                print(f"    -> Successfully set {vid_id} to PRIVATE")
            except Exception as exc:
                print(f"    -> ❌ Failed to update {vid_id}: {exc}")

    # Step 2: Update titles & metadata of active videos
    print("\n✍️ Step 2: Updating Titles & Metadata for Low-View Videos...")
    all_update_ids = list(VIDEOS_TO_UPDATE_TITLES.keys())
    
    # Fetch existing snippets so we don't wipe descriptions and tags
    for i in range(0, len(all_update_ids), 50):
        batch = all_update_ids[i:i + 50]
        res = youtube.videos().list(id=",".join(batch), part="snippet").execute()

        for item in res.get("items", []):
            vid_id = item["id"]
            snippet = item["snippet"]
            old_title = snippet.get("title", "")
            new_title = VIDEOS_TO_UPDATE_TITLES.get(vid_id)

            if not new_title:
                continue

            print(f"  • Video {vid_id}:")
            print(f"    Old: {old_title}")
            print(f"    New: {new_title}")

            if execute:
                try:
                    snippet["title"] = new_title
                    snippet["categoryId"] = "23"  # Comedy
                    youtube.videos().update(
                        part="snippet",
                        body={
                            "id": vid_id,
                            "snippet": snippet,
                        },
                    ).execute()
                    print(f"    -> Successfully updated {vid_id} title on YouTube!")
                except Exception as exc:
                    print(f"    -> ❌ Failed to update {vid_id}: {exc}")

    print("\n" + "=" * 65)
    action_text = "Changes successfully applied to YouTube!" if execute else "Dry run complete. No changes made yet."
    print(f"🎉 {action_text}")
    print("=" * 65 + "\n")


if __name__ == "__main__":
    parser = argparse.ArgumentParser(description="Remediate Stateside Smiles channel videos")
    parser.add_argument("--execute", action="store_true", help="Apply updates via YouTube API")
    parser.add_argument("--dry-run", action="store_true", help="Preview updates without applying")
    args = parser.parse_args()
    remediate_channel(execute=args.execute)
