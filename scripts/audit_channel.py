import json
import sys
from pathlib import Path

TOKEN_FILE = Path(__file__).parent.parent / "config" / "youtube_token.json"

from google.oauth2.credentials import Credentials
from google.auth.transport.requests import Request
from googleapiclient.discovery import build

def get_youtube():
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

def audit():
    yt = get_youtube()
    res = yt.channels().list(mine=True, part="snippet,contentDetails,statistics").execute()
    items = res.get("items", [])
    if not items:
        print("No channel found!")
        return
    channel = items[0]
    print(f"Channel: {channel['snippet']['title']} (ID: {channel['id']})")
    print(f"Subscribers: {channel['statistics'].get('subscriberCount')}")
    print(f"Total Views: {channel['statistics'].get('viewCount')}")
    print(f"Total Videos: {channel['statistics'].get('videoCount')}")
    print("=" * 60)

    uploads_id = channel["contentDetails"]["relatedPlaylists"]["uploads"]
    video_ids = []
    next_page = None
    while True:
        p_res = yt.playlistItems().list(
            playlistId=uploads_id,
            part="contentDetails",
            maxResults=50,
            pageToken=next_page,
        ).execute()
        for it in p_res.get("items", []):
            video_ids.append(it["contentDetails"]["videoId"])
        next_page = p_res.get("nextPageToken")
        if not next_page:
            break

    print(f"Total Uploaded Videos on Channel: {len(video_ids)}")
    
    # Query details
    for i in range(0, len(video_ids), 50):
        batch = video_ids[i:i+50]
        v_res = yt.videos().list(
            id=",".join(batch),
            part="snippet,status,contentDetails,statistics"
        ).execute()
        for v in v_res.get("items", []):
            vid = v["id"]
            title = v["snippet"].get("title", "")
            cat = v["snippet"].get("categoryId", "")
            status = v["status"].get("privacyStatus", "")
            duration = v["contentDetails"].get("duration", "")
            stats = v.get("statistics", {})
            views = stats.get("viewCount", "0")
            likes = stats.get("likeCount", "0")
            comments = stats.get("commentCount", "0")
            print(f"ID: {vid} | Views: {views:>3} | Likes: {likes:>2} | Privacy: {status:>7} | Dur: {duration:>8} | Cat: {cat:>2} | Title: {title}")

if __name__ == "__main__":
    audit()
