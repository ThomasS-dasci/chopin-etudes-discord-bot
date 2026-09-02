import json
import os
from pathlib import Path

import requests


YOUTUBE_API_KEY = os.environ["YOUTUBE_API_KEY"]
YOUTUBE_CHANNEL_ID = os.environ["YOUTUBE_CHANNEL_ID"]

DISCORD_TOKEN = os.environ["DISCORD_TOKEN"]
DISCORD_CHANNEL_ID = os.environ["YOUTUBE_UPLOAD_CHANNEL_ID"]
UPLOAD_ROLE_ID = os.environ["UPLOAD_NOTIFICATION_ROLE_ID"]

STATE_FILE = Path("youtube_state.json")


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
            "part": "snippet,liveStreamingDetails",
            "id": ",".join(video_ids),
        },
    )

    return data.get("items", [])


def load_state():
    if not STATE_FILE.exists():
        return None

    with STATE_FILE.open("r", encoding="utf-8") as file:
        return json.load(file)


def save_state(latest_video_id):
    with STATE_FILE.open("w", encoding="utf-8") as file:
        json.dump(
            {"latest_video_id": latest_video_id},
            file,
            indent=2,
        )


def send_discord_message(video):
    video_id = video["id"]
    title = video["snippet"]["title"]

    url = f"https://www.youtube.com/watch?v={video_id}"

    message = (
        f"<@&{UPLOAD_ROLE_ID}>\n"
        f"**New YouTube Upload!**\n"
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
                "roles": [UPLOAD_ROLE_ID]
            },
        },
        timeout=30,
    )

    response.raise_for_status()


def main():
    uploads_playlist = get_uploads_playlist()
    recent_ids = get_recent_video_ids(uploads_playlist)

    if not recent_ids:
        print("No videos found.")
        return

    state = load_state()

    # First run:
    # remember the newest video, but don't announce old uploads.
    if state is None:
        save_state(recent_ids[0])
        print(f"Initialized with video: {recent_ids[0]}")
        return

    previous_latest = state["latest_video_id"]

    if recent_ids[0] == previous_latest:
        print("No new uploads.")
        return

    new_ids = []

    for video_id in recent_ids:
        if video_id == previous_latest:
            break
        new_ids.append(video_id)

    videos = get_video_details(new_ids)

    # API may not preserve our exact order
    videos_by_id = {video["id"]: video for video in videos}

    # oldest new upload first
    for video_id in reversed(new_ids):
        video = videos_by_id.get(video_id)

        if not video:
            continue

        # Any video with liveStreamingDetails was/is a livestream.
        # We deliberately don't announce it as a normal upload.
        if "liveStreamingDetails" in video:
            print(
                f"Skipping livestream/VOD: "
                f"{video['snippet']['title']}"
            )
            continue

        print(f"Announcing: {video['snippet']['title']}")
        send_discord_message(video)

    save_state(recent_ids[0])
    print(f"State updated to: {recent_ids[0]}")


if __name__ == "__main__":
    main()