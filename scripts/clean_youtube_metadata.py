"""
Stateside Smiles — Clean YouTube Metadata CLI

Scans all published videos on the channel, removes legacy '#BreakingNews' / news
descriptions, and updates them to pure comedy metadata with channel subscribe links.

Usage:
    python scripts/clean_youtube_metadata.py --dry-run
    python scripts/clean_youtube_metadata.py --execute
"""

import argparse
import json
import re
import sys
from datetime import datetime, timezone
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


def clean_channel_videos(execute: bool = False):
    youtube = get_youtube_client()

    print("Fetching channel uploads playlist...")
    channels_res = youtube.channels().list(mine=True, part="snippet,contentDetails").execute()
    items = channels_res.get("items", [])
    if not items:
        print("No channel found.")
        return

    channel_title = items[0]["snippet"]["title"]
    uploads_id = items[0]["contentDetails"]["relatedPlaylists"]["uploads"]
    print(f"Connected to channel: {channel_title}")

    # Fetch all video IDs from uploads playlist
    video_ids = []
    next_page = None
    while True:
        res = youtube.playlistItems().list(
            playlistId=uploads_id,
            part="contentDetails",
            maxResults=50,
            pageToken=next_page,
        ).execute()
        for item in res.get("items", []):
            video_ids.append(item["contentDetails"]["videoId"])
        next_page = res.get("nextPageToken")
        if not next_page:
            break

    print(f"Found {len(video_ids)} total videos on channel.\n")

    # Inspect each batch of up to 50 videos
    updated_count = 0
    for i in range(0, len(video_ids), 50):
        batch = video_ids[i:i + 50]
        v_res = youtube.videos().list(id=",".join(batch), part="snippet").execute()

        for vid in v_res.get("items", []):
            vid_id = vid["id"]
            snippet = vid["snippet"]
            title = snippet.get("title", "")
            desc = snippet.get("description", "")
            tags = snippet.get("tags", [])
            category_id = snippet.get("categoryId", "23")

            needs_update = False
            desc_lower = desc.lower()

            if any(term in desc_lower for term in ["get the latest news", "breaking news", "breakingnews", "#news"]):
                needs_update = True

            if any("breaking news" in t.lower() or "news" in t.lower() for t in tags):
                needs_update = True

            if not needs_update:
                continue

            # Extract the actual hook / topic from the first 1-2 lines before the news boilerplates
            lines = [l.strip() for l in desc.split("\n") if l.strip()]
            clean_lines = []
            for line in lines:
                if any(bad in line.lower() for bad in ["get the latest news", "what do you think", "follow for daily news", "#news", "#breakingnews", "verified reports", "international agencies"]):
                    break
                clean_lines.append(line)

            topic_text = "\n\n".join(clean_lines[:2]) if clean_lines else title.replace("#Shorts", "").strip()

            new_desc = (
                f"{topic_text}\n\n"
                f"😂 Daily comedy, viral memes & funny moments!\n\n"
                f"👉 Subscribe to Stateside Smiles for daily laughs: https://youtube.com/@StatesideSmiles?sub_confirmation=1\n\n"
                f"💬 Which part made you laugh the hardest? Drop your comment below! 👇\n\n"
                f"#Shorts #Funny #Memes #Comedy #TryNotToLaugh #StatesideSmiles"
            )

            # Clean tags: filter out news tags and inject comedy tags
            clean_tags = [
                t for t in tags
                if not any(bad in t.lower() for bad in ["news", "breaking", "world news", "news today"])
            ]
            base_tags = ["funny", "memes", "comedy", "try not to laugh", "stateside smiles", "shorts"]
            for bt in base_tags:
                if bt not in clean_tags:
                    clean_tags.append(bt)

            print(f"[{'EXECUTE' if execute else 'DRY RUN'}] Video: '{title}' ({vid_id})")
            print(f"  Old Desc Snippet: {desc[:60]}...")
            print(f"  New Tags Count: {len(clean_tags)}")

            if execute:
                snippet["description"] = new_desc
                snippet["tags"] = clean_tags[:30]
                snippet["categoryId"] = "23"  # Comedy

                youtube.videos().update(
                    part="snippet",
                    body={
                        "id": vid_id,
                        "snippet": snippet,
                    }
                ).execute()
                print(f"  -> Successfully updated video {vid_id} on YouTube!")

            updated_count += 1
            print("-" * 50)

    action_label = "Updated" if execute else "Flagged for update"
    print(f"\nDone! {action_label} {updated_count} videos with '#BreakingNews' / news tags.")


if __name__ == "__main__":
    parser = argparse.ArgumentParser(description="Clean legacy news metadata on Stateside Smiles")
    parser.add_argument("--execute", action="store_true", help="Actually execute updates via YouTube Data API")
    args = parser.parse_args()
    clean_channel_videos(execute=args.execute)
