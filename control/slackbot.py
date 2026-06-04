"""Slack bot: receive audio/video uploads, transcribe via Forge, return markdown.

Runs on Conductor using Socket Mode (no public port needed).
Reads from environment (or .env):
    SLACK_BOT_TOKEN   — xoxb-...
    SLACK_APP_TOKEN   — xapp-...  (Socket Mode app-level token)
    FORGE_API_URL     — e.g. http://100.x.x.x:8765

Usage:
    python control/slackbot.py
"""

import io
import os
import sys
from pathlib import Path

import requests
from dotenv import load_dotenv
from slack_bolt import App
from slack_bolt.adapter.socket_mode import SocketModeHandler

load_dotenv()

_BOT_TOKEN = os.environ["SLACK_BOT_TOKEN"]
_APP_TOKEN = os.environ["SLACK_APP_TOKEN"]
_FORGE_URL = os.environ["FORGE_API_URL"].rstrip("/")

_MEDIA_EXTENSIONS = {".mp4", ".mov", ".mp3", ".m4a", ".wav", ".ogg", ".webm"}

app = App(token=_BOT_TOKEN)


def _download_slack_file(url: str) -> bytes:
    resp = requests.get(
        url,
        headers={"Authorization": f"Bearer {_BOT_TOKEN}"},
        timeout=120,
    )
    resp.raise_for_status()
    return resp.content


def _transcribe_on_forge(data: bytes, filename: str) -> str:
    resp = requests.post(
        f"{_FORGE_URL}/transcribe",
        files={"file": (filename, io.BytesIO(data))},
        timeout=600,  # transcription can take a while
    )
    resp.raise_for_status()
    return resp.json()["transcript"]


@app.event("file_shared")
def handle_file_shared(event, client, say):
    file_id = event.get("file_id")
    channel_id = event.get("channel_id")

    # Fetch file metadata
    info = client.files_info(file=file_id)
    file_obj = info["file"]
    filename = file_obj.get("name", "upload")
    download_url = file_obj.get("url_private_download") or file_obj.get("url_private")

    if not download_url:
        say(channel=channel_id, text=f"Could not get a download URL for `{filename}`.")
        return

    suffix = Path(filename).suffix.lower()
    if suffix not in _MEDIA_EXTENSIONS:
        # Silently ignore non-media files — bot may see all uploads in a channel.
        return

    say(channel=channel_id, text=f"Transcribing `{filename}`… this may take a minute.")

    try:
        audio_bytes = _download_slack_file(download_url)
    except Exception as exc:
        say(channel=channel_id, text=f"Failed to download `{filename}`: {exc}")
        return

    try:
        transcript_md = _transcribe_on_forge(audio_bytes, filename)
    except requests.HTTPError as exc:
        say(channel=channel_id, text=f"Forge returned an error: {exc.response.status_code} — {exc.response.text[:200]}")
        return
    except Exception as exc:
        say(channel=channel_id, text=f"Transcription failed: {exc}")
        return

    stem = Path(filename).stem
    md_filename = f"{stem}_transcript.md"

    try:
        client.files_upload_v2(
            channel=channel_id,
            content=transcript_md,
            filename=md_filename,
            title=f"Transcript: {filename}",
        )
    except Exception as exc:
        # Fall back to posting inline if upload fails
        say(channel=channel_id, text=f"Upload failed ({exc}), posting inline:\n```\n{transcript_md[:2000]}\n```")


def main():
    missing = [v for v in ("SLACK_BOT_TOKEN", "SLACK_APP_TOKEN", "FORGE_API_URL") if not os.environ.get(v)]
    if missing:
        sys.exit(f"Missing required env vars: {', '.join(missing)}")

    print("Starting Harmony Slack bot (Socket Mode)…", flush=True)
    handler = SocketModeHandler(app, _APP_TOKEN)
    handler.start()


if __name__ == "__main__":
    main()
