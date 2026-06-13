"""Slack bot: command-driven audio/video transcription and denoising via Forge.

Runs on Conductor using Socket Mode (no public port needed).

Users upload a media file with a command in the message body:
    /transcribe          transcribe and return the transcript as a file
    /clean                denoise via DeepFilterNet and return the cleaned MP3
    /clean transcribe     denoise, then transcribe the cleaned audio; return both
                          (/transcribe clean also works)

A file with no recognized command gets a help reply. All replies go to the
thread of the upload message.

Reads from environment (or .env):
    SLACK_BOT_TOKEN   — xoxb-...
    SLACK_APP_TOKEN   — xapp-...  (Socket Mode app-level token)
    FORGE_API_URL     — e.g. http://100.x.x.x:8765

Usage:
    python control/slackbot.py
"""

import io
import os
import re
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

_HELP_TEXT = "Available commands: /transcribe, /clean, /clean transcribe"

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


def _clean_on_forge(data: bytes, filename: str) -> bytes:
    resp = requests.post(
        f"{_FORGE_URL}/clean",
        files={"file": (filename, io.BytesIO(data))},
        timeout=600,
    )
    resp.raise_for_status()
    return resp.content


def _parse_command(text: str) -> tuple[bool, bool] | None:
    """Return (do_clean, do_transcribe), or None if no recognized command."""
    tokens = set(re.findall(r"/(\w+)", text.lower()))
    do_clean = "clean" in tokens
    do_transcribe = "transcribe" in tokens
    if not do_clean and not do_transcribe:
        return None
    return do_clean, do_transcribe


def _process_file(file_obj, do_clean, do_transcribe, channel_id, thread_ts, client, say):
    filename = file_obj.get("name", "upload")
    download_url = file_obj.get("url_private_download") or file_obj.get("url_private")

    if not download_url:
        say(channel=channel_id, thread_ts=thread_ts, text=f"Could not get a download URL for `{filename}`.")
        return

    if do_clean and do_transcribe:
        action = "Cleaning and transcribing"
    elif do_clean:
        action = "Cleaning"
    else:
        action = "Transcribing"
    say(channel=channel_id, thread_ts=thread_ts, text=f"{action} `{filename}`… this may take a minute.")

    try:
        audio_bytes = _download_slack_file(download_url)
    except Exception as exc:
        say(channel=channel_id, thread_ts=thread_ts, text=f"Failed to download `{filename}`: {exc}")
        return

    transcribe_bytes = audio_bytes
    transcribe_filename = filename

    if do_clean:
        try:
            cleaned_bytes = _clean_on_forge(audio_bytes, filename)
        except requests.HTTPError as exc:
            say(channel=channel_id, thread_ts=thread_ts,
                text=f"Denoising failed: Forge returned {exc.response.status_code} — {exc.response.text[:200]}")
            return
        except Exception as exc:
            say(channel=channel_id, thread_ts=thread_ts, text=f"Denoising failed: {exc}")
            return

        stem = Path(filename).stem
        cleaned_filename = f"{stem}_denoised.mp3"

        try:
            client.files_upload_v2(
                channel=channel_id,
                thread_ts=thread_ts,
                content=cleaned_bytes,
                filename=cleaned_filename,
                title=f"Cleaned audio: {filename}",
            )
        except Exception as exc:
            say(channel=channel_id, thread_ts=thread_ts, text=f"Cleaned-audio upload failed: {exc}")
            return

        # Whisper runs on the cleaned audio, not the original.
        transcribe_bytes = cleaned_bytes
        transcribe_filename = cleaned_filename

    if not do_transcribe:
        return

    try:
        transcript_md = _transcribe_on_forge(transcribe_bytes, transcribe_filename)
    except requests.HTTPError as exc:
        say(channel=channel_id, thread_ts=thread_ts,
            text=f"Forge returned an error: {exc.response.status_code} — {exc.response.text[:200]}")
        return
    except Exception as exc:
        say(channel=channel_id, thread_ts=thread_ts, text=f"Transcription failed: {exc}")
        return

    stem = Path(filename).stem
    md_filename = f"{stem}_transcript.md"

    try:
        client.files_upload_v2(
            channel=channel_id,
            thread_ts=thread_ts,
            content=transcript_md,
            filename=md_filename,
            title=f"Transcript: {filename}",
        )
    except Exception as exc:
        # Fall back to posting inline if upload fails
        say(channel=channel_id, thread_ts=thread_ts,
            text=f"Upload failed ({exc}), posting inline:\n```\n{transcript_md[:2000]}\n```")


@app.event("message")
def handle_message(event, client, say):
    if event.get("subtype") != "file_share":
        return

    files = event.get("files") or []
    media_files = [f for f in files if Path(f.get("name", "")).suffix.lower() in _MEDIA_EXTENSIONS]
    if not media_files:
        # Silently ignore non-media uploads — bot may see all uploads in a channel.
        return

    channel_id = event.get("channel")
    thread_ts = event.get("ts")

    command = _parse_command(event.get("text", ""))
    if command is None:
        say(channel=channel_id, thread_ts=thread_ts, text=_HELP_TEXT)
        return

    do_clean, do_transcribe = command
    for file_obj in media_files:
        _process_file(file_obj, do_clean, do_transcribe, channel_id, thread_ts, client, say)


def main():
    missing = [v for v in ("SLACK_BOT_TOKEN", "SLACK_APP_TOKEN", "FORGE_API_URL") if not os.environ.get(v)]
    if missing:
        sys.exit(f"Missing required env vars: {', '.join(missing)}")

    print("Starting Harmony Slack bot (Socket Mode)…", flush=True)
    handler = SocketModeHandler(app, _APP_TOKEN)
    handler.start()


if __name__ == "__main__":
    main()
