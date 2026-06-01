# Ingest & Dating — amendment to Stage 0b

Refines how reflection videos get from the phone into the transcription step.
Read alongside `STAGE-0BC-PREP.md`. Supersedes the "filename contains YYYY-MM-DD"
assumption in the original 0b contract.

## 1. Dedicated ingest folder — not the Instant Upload firehose

Instant Upload captures all phone media (photos, screenshots, junk clips).
Do **not** point the pipeline at it. Define one Nextcloud folder, `/Reflections/`,
that holds only daily reflection videos. Populate it either by:
- configuring the phone to auto-upload a specific album into `/Reflections`, or
- dropping/moving the day's video there yourself.

The transcribe step watches `/Reflections`, never `/InstantUpload`.

## 2. Forge ↔ Nextcloud access — never the raw data dir

Media lives in Nextcloud on Conductor. Forge needs the bytes but must **never**
read or write Nextcloud's data directory on disk directly — it desyncs Nextcloud's
file cache (repair requires `occ files:scan`; direct writes can corrupt it). Always
go through Nextcloud's interface. Pick one pattern:

- **MVP — sync client on Forge.** Nextcloud desktop client, selective-sync
  `/Reflections` (down) and the vault (up). Files appear as a local folder; the
  watcher triggers; transcripts written into the synced vault propagate back.
  Cost: media duplicated onto Forge's SSD (fine, 3TB).
- **Cleaner — WebDAV pull.** Forge pulls on demand over Tailscale via rclone's
  WebDAV backend or a davfs2 mount, writes transcripts back via WebDAV. No
  duplication, more setup.

Either way: WebDAV/sync only, never the data dir.

## 3. Date resolution (replaces filename-only dating)

Resolve each media file's date in this priority, and **log which source won**:
1. **Container creation time** via `ffprobe` (`format_tags.creation_time`).
   Convert **UTC → local timezone** before taking the date — a late-night local
   recording can be stored as the next day in UTC.
2. **Filename date** — handle `YYYYMMDD`, `YYYY-MM-DD`, and `PXL_/VID_/IMG_` prefixes.
3. **File mtime** — last resort only.

Then group by resolved date and append all of a day's videos into
`transcripts/<date>.txt` (as the 0b contract already specifies).

## 4. Filter

Process only audio/video extensions (`.mp4 .mov .mp3 .m4a .wav`). Ignore images and
everything else in the folder.

## 5. Amend the 0b plan-mode prompt

Add to the 0b prompt:
> Source media from a local folder that mirrors the Nextcloud `/Reflections` folder
> (pass it via `--inputs`), not Instant Upload. Resolve each file's date by `ffprobe`
> `creation_time` (convert UTC→local) first, then a filename date, then mtime, logging
> which source was used. Filter to audio/video extensions only. Never touch any
> Nextcloud data directory.

## 6. Testing the date logic on samples

Make the silent test clips exercise both date paths:
```bash
# metadata path — embeds a creation_time
ffmpeg -f lavfi -i anullsrc=r=16000:cl=mono -t 3 \
  -metadata creation_time="2026-05-28T14:30:00" \
  samples/media/clip-with-metadata.wav

# filename path — date only in the name, no metadata
ffmpeg -f lavfi -i anullsrc=r=16000:cl=mono -t 3 \
  samples/media/20260530_imported.wav
```
Validation add-on: the first resolves to 2026-05-28 via metadata, the second to
2026-05-30 via filename, and the log states which source each used.
