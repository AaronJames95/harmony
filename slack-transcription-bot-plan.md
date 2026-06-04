# Slack Transcription Bot — Plan

## Goal

A Slack bot that accepts audio/video file uploads, transcribes them via faster-whisper
on Forge, and returns the transcript as a markdown file in the same Slack thread.

## Architecture

**Conductor (this machine)** — `control/slackbot.py`
- Runs a Slack Socket Mode listener (no public port needed)
- On `file_shared` event: downloads the file from Slack to a staging dir
- POSTs the file to Forge's transcription HTTP API over Tailscale
- When result comes back, posts the markdown transcript to Slack as a file

**Forge** — `compute/transcribe_api.py`
- Small FastAPI app bound to the Tailscale interface
- Single endpoint: `POST /transcribe` — accepts an audio file, runs faster-whisper large-v3, returns transcript text
- Systemd service so it's always available

## Files to create

| File | Machine | Purpose |
|---|---|---|
| `compute/transcribe_api.py` | Forge | FastAPI wrapper around faster-whisper |
| `control/slackbot.py` | Conductor | Slack Socket Mode bot |
| `control/slackbot.service` | Conductor | systemd unit |
| `compute/transcribe_api.service` | Forge | systemd unit |
| `.env` (gitignored) | both | `SLACK_BOT_TOKEN`, `SLACK_APP_TOKEN`, `FORGE_API_URL` |

## API contract

`POST /transcribe`
- Body: multipart form, field `file` = audio/video file
- Response: `{ "transcript": "<markdown text>" }`

## Build order

1. `compute/transcribe_api.py` — short, defines the contract both sides depend on
2. `control/slackbot.py` — consumes that API
3. Systemd units for both
4. Deploy `compute/` to Forge, test end-to-end

## Out of scope for this branch

- Integration with the broader reflection pipeline (that's Stage 1+)
- Any vault writes — transcript is returned to Slack only
