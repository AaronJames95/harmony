# Conductor setup — command-driven Slack bot (`/transcribe`, `/clean`, `/clean transcribe`)

Forge is already done (see `forge-clean-command-setup.md`) — its `/clean` endpoint
is live. This is what's left, run on Conductor (the NUC). You can run Claude Code
there and point it at this file.

## 1. Pull the changes

```
cd ~/Documents/harmony   # or wherever this repo lives on Conductor
git pull
```

The only file that changed for this machine is `control/slackbot.py`. No new
Python dependencies were added to `control/requirements.txt` — `re` is stdlib, so
`.venv/bin/pip install -r control/requirements.txt` is not strictly required, but
running it is harmless if you want to be safe.

## 2. What changed in slackbot.py

- It now listens for `message` events with `subtype == "file_share"` instead of
  `file_shared`, because it needs to read the message text (the command) alongside
  the uploaded file. `file_shared` events don't include `text`.
- It parses `/transcribe`, `/clean`, and `/clean transcribe` (either order) from
  the message text.
- `/clean` and `/clean transcribe` call Forge's new `POST /clean` endpoint.
- All replies (`say(...)`) now include `thread_ts` so they land in the upload's
  thread.
- A file upload with no recognized command gets a help reply: "Available
  commands: /transcribe, /clean, /clean transcribe".

## 3. Check Slack app scopes (likely action needed)

Reading `event["text"]` on `message` events requires history scopes that the old
`file_shared`-only listener didn't need. Go to
https://api.slack.com/apps -> your app -> **OAuth & Permissions** and confirm the
bot token has, for whatever channel types it's used in:

- `channels:history` (public channels)
- `groups:history` (private channels)
- `im:history` / `mpim:history` (DMs / group DMs), if relevant

Also check **Event Subscriptions** / Socket Mode event subscriptions include
`message.channels` (and the corresponding `message.groups` / `message.im` /
`message.mpim` if those channel types are used).

If you add any new scopes, **reinstall the app to the workspace** — scope changes
don't take effect until reinstall.

## 4. Restart the bot

```
sudo systemctl restart slackbot.service
journalctl -u slackbot.service -f   # watch for startup errors
```

## 5. Smoke test

In a channel the bot is in, upload a short mp3/m4a/etc with each of these as the
message text:

- `/transcribe` — expect a thread reply ("Transcribing…") then a transcript file.
- `/clean` — expect a thread reply ("Cleaning…") then `<name>_denoised.mp3`.
- `/clean transcribe` (and try `/transcribe clean` too) — expect both the cleaned
  MP3 and a transcript generated from the *cleaned* audio.
- No command — expect just the help text, no files.

If something fails, the bot's reply will include the Forge error detail (denoising
or transcription failure), or `journalctl -u slackbot.service` will show a
download/Slack-API error.
