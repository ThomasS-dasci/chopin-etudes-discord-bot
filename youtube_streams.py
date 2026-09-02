import json
import os
from pathlib import Path

import requests


YOUTUBE_API_KEY = os.environ["YOUTUBE_API_KEY"]
YOUTUBE_CHANNEL_ID = os.environ["YOUTUBE_CHANNEL_ID"]

DISCORD_TOKEN = os.environ["DISCORD_TOKEN"]
DISCORD_CHANNEL_ID = os.environ["STREAM_NOTIFICATION_CHANNEL_ID"]
STREAM_ROLE_ID = os.environ["STREAM_NOTIFICATION_ROLE_ID"]

STATE_FILE = Path("youtube_stream_state.json")


def youtube_get(endpoint, params):
    params["key"] = YOUTUBE_API_KEY

    response = requests.get(
        f"https://www.googleapis.com/youtube/v3/{endpoint}",
        params=params,
        timeout=30,
    )
    response.raise_for_status()

    return response.json()


def get_uploads_playlist():
    data = youtube_get(
        "channels",
        {
            "part": "contentDetails",
            "id": YOUTUBE_CHANNEL_ID,
        },
    )

    return data["items"][0]["contentDetails"]["relatedPlaylists"]["uploads"]


def get_recent_video_ids(playlist_id):
    data = youtube_get(
        "playlistItems",
        {
            "part": "contentDetails",
            "playlistId": playlist_id,
            "maxResults": 10,
        },
    )

    return [
        item["contentDetails"]["videoId"]
        for item in data.get("items", [])
    ]


def get_video_details(video_ids):
    if not video_ids:
        return []

    data = youtube_get(
        "videos",
        {
            "part": "snippet,liveStreamingDetails,status",
            "id": ",".join(video_ids),
        },
    )

    return data.get("items", [])


def load_state():
    if not STATE_FILE.exists():
        return {"announced_streams": []}

    with STATE_FILE.open("r", encoding="utf-8") as file:
        return json.load(file)


def save_state(state):
    with STATE_FILE.open("w", encoding="utf-8") as file:
        json.dump(state, file, indent=2)


def is_live(video):
    snippet = video.get("snippet", {})
    live_details = video.get("liveStreamingDetails", {})

    return (
        snippet.get("liveBroadcastContent") == "live"
        and "actualStartTime" in live_details
        and "actualEndTime" not in live_details
    )


def send_discord_notification(video):
    video_id = video["id"]
    title = video["snippet"]["title"]
    url = f"https://www.youtube.com/watch?v={video_id}"

    message = (
        f"<@&{STREAM_ROLE_ID}>\n"
        f"🔴 **LIVE NOW**\n"
        f"**{title}**\n"
        f"{url}"
    )

    response = requests.post(
        f"https://discord.com/api/v10/channels/{DISCORD_CHANNEL_ID}/messages",
        headers={
            "Authorization": f"Bot {DISCORD_TOKEN}",
            "Content-Type": "application/json",
        },
        json={
            "content": message,
            "allowed_mentions": {
                "roles": [STREAM_ROLE_ID]
            },
        },
        timeout=30,
    )

    response.raise_for_status()


def main():
    state = load_state()

    playlist_id = get_uploads_playlist()
    video_ids = get_recent_video_ids(playlist_id)
    videos = get_video_details(video_ids)

    announced = set(state.get("announced_streams", []))

    for video in videos:
        video_id = video["id"]

        if not is_live(video):
            continue

        if video_id in announced:
            print(f"Already announced: {video['snippet']['title']}")
            continue

        print(f"New livestream detected: {video['snippet']['title']}")

        send_discord_notification(video)

        announced.add(video_id)

    # Keep the state file small.
    state["announced_streams"] = list(announced)[-50:]
    save_state(state)


if __name__ == "__main__":
    main()