"""Stage 0b: transcribe audio/video files and write one transcript per date.

Usage:
    python compute/transcribe.py --inputs samples/media/ --out out/transcripts/
"""

import argparse
import datetime
import json
import re
import subprocess
import sys
from pathlib import Path

# From shared/ingest-and-dating.md section 4
_MEDIA_EXTENSIONS = {".mp4", ".mov", ".mp3", ".m4a", ".wav"}


# ---------------------------------------------------------------------------
# Timestamp formatting
# ---------------------------------------------------------------------------

def _fmt_ts(seconds: float) -> str:
    """Return MM:SS.f from a float number of seconds, e.g. 83.4 -> '01:23.4'."""
    mins, secs = divmod(seconds, 60)
    return f"{int(mins):02d}:{secs:04.1f}"


# ---------------------------------------------------------------------------
# Date resolution
# ---------------------------------------------------------------------------

def _probe_creation_time(path: Path) -> "datetime.datetime | None":
    """Return a timezone-aware UTC datetime from ffprobe creation_time, or None."""
    try:
        result = subprocess.run(
            ["ffprobe", "-v", "quiet", "-print_format", "json", "-show_format", str(path)],
            capture_output=True, text=True, check=True,
        )
        data = json.loads(result.stdout)
        raw = data.get("format", {}).get("tags", {}).get("creation_time")
        if not raw:
            return None
        # Normalize trailing Z to +00:00 for fromisoformat compatibility
        raw_norm = raw.replace("Z", "+00:00")
        return datetime.datetime.fromisoformat(raw_norm)
    except Exception as exc:
        print(f"ffprobe error for {path.name}: {exc}", file=sys.stderr)
        return None


# Patterns ordered by specificity: prefixed camera names first, then bare runs
_FNAME_PATTERNS = [
    re.compile(r"(?:PXL|VID|IMG)_(\d{4})(\d{2})(\d{2})_"),
    re.compile(r"(\d{4})(\d{2})(\d{2})"),
    re.compile(r"(\d{4})-(\d{2})-(\d{2})"),
]


def _date_from_filename(path: Path) -> "datetime.date | None":
    """Return a date parsed from the filename stem, or None."""
    stem = path.stem
    for pat in _FNAME_PATTERNS:
        m = pat.search(stem)
        if m:
            try:
                return datetime.date(int(m.group(1)), int(m.group(2)), int(m.group(3)))
            except ValueError:
                continue
    return None


def _resolve_date(path: Path) -> "tuple[datetime.date, str]":
    """Return (date, source) using ffprobe -> filename -> mtime priority."""
    utc_dt = _probe_creation_time(path)
    if utc_dt is not None:
        date = utc_dt.astimezone().date()
        print(f"{path.name} -> {date} (via ffprobe)", file=sys.stderr)
        return date, "ffprobe"

    date = _date_from_filename(path)
    if date is not None:
        print(f"{path.name} -> {date} (via filename)", file=sys.stderr)
        return date, "filename"

    date = datetime.datetime.fromtimestamp(path.stat().st_mtime).date()
    print(f"{path.name} -> {date} (via mtime)", file=sys.stderr)
    return date, "mtime"


# ---------------------------------------------------------------------------
# Output file management
# ---------------------------------------------------------------------------

def _read_sources(out_path: Path) -> list[str]:
    """Return the list of source filenames already written to out_path."""
    if not out_path.exists():
        return []
    text = out_path.read_text(encoding="utf-8")
    # Frontmatter is between the first and second '---' lines
    parts = text.split("---", 2)
    if len(parts) < 2:
        return []
    fm = parts[1]
    sources: list[str] = []
    in_sources = False
    for line in fm.splitlines():
        if line.strip() == "sources:":
            in_sources = True
            continue
        if in_sources:
            stripped = line.strip()
            if stripped.startswith("- "):
                sources.append(stripped[2:].strip())
            elif stripped and not stripped.startswith("-"):
                in_sources = False
    return sources


def _write_or_append(
    out_path: Path,
    date: datetime.date,
    source_filename: str,
    transcript: str,
    date_source: str,
    generated_at: str,
) -> None:
    section_header = f"## {source_filename} (date via {date_source})"
    section_body = f"{section_header}\n\n{transcript}"

    if not out_path.exists():
        content = (
            f"---\n"
            f"date: {date}\n"
            f"generated_by: transcribe.py\n"
            f"generated_at: {generated_at}\n"
            f"sources:\n"
            f"  - {source_filename}\n"
            f"---\n"
            f"\n"
            f"{section_body}\n"
        )
        out_path.write_text(content, encoding="utf-8")
        return

    # Append: update sources list in frontmatter and add new section to body
    existing = out_path.read_text(encoding="utf-8")
    parts = existing.split("---", 2)
    if len(parts) < 3:
        # Malformed file — append defensively
        out_path.write_text(existing.rstrip() + f"\n\n{section_body}\n", encoding="utf-8")
        return

    _open, fm, body = parts
    fm_updated = fm.rstrip() + f"\n  - {source_filename}\n"
    body_updated = body.rstrip() + f"\n\n{section_body}\n"
    out_path.write_text(f"---{fm_updated}---{body_updated}", encoding="utf-8")


# ---------------------------------------------------------------------------
# Transcription
# ---------------------------------------------------------------------------

def _transcribe_file(
    model: "object",
    path: Path,
    out_dir: Path,
    generated_at: str,
) -> bool:
    """Transcribe one file. Returns True if transcribed, False if skipped."""
    date, date_source = _resolve_date(path)
    out_path = out_dir / f"{date}.md"

    if path.name in _read_sources(out_path):
        print(f"skip (already done): {path.name}", file=sys.stderr)
        return False

    segments, _info = model.transcribe(str(path))
    transcript = "\n".join(
        f"[{_fmt_ts(seg.start)} -> {_fmt_ts(seg.end)}] {seg.text.strip()}"
        for seg in segments
    )
    _write_or_append(out_path, date, path.name, transcript, date_source, generated_at)
    return True


# ---------------------------------------------------------------------------
# CLI
# ---------------------------------------------------------------------------

def main() -> None:
    parser = argparse.ArgumentParser(
        description="Stage 0b: transcribe audio/video files into per-date transcript notes."
    )
    parser.add_argument("--inputs", required=True, type=Path, help="Input directory")
    parser.add_argument("--out", required=True, type=Path, help="Output directory")
    args = parser.parse_args()

    if not args.inputs.exists():
        sys.exit(f"Error: inputs directory does not exist: {args.inputs}")

    args.out.mkdir(parents=True, exist_ok=True)
    generated_at = datetime.datetime.now().isoformat(timespec="seconds")

    media_files = sorted(
        p for p in args.inputs.iterdir() if p.suffix.lower() in _MEDIA_EXTENSIONS
    )
    print(f"Found {len(media_files)} media file(s)", file=sys.stderr)

    from faster_whisper import WhisperModel  # noqa: PLC0415 — imported late to allow mocking
    model = WhisperModel("large-v3", device="cuda", compute_type="int8_float16")

    transcribed = skipped = failed = 0
    for path in media_files:
        try:
            did_transcribe = _transcribe_file(model, path, args.out, generated_at)
            if did_transcribe:
                transcribed += 1
            else:
                skipped += 1
        except Exception as exc:
            print(f"ERROR: {path.name}: {exc}", file=sys.stderr)
            failed += 1

    print(f"Done: {transcribed} transcribed, {skipped} skipped, {failed} failed", file=sys.stderr)


if __name__ == "__main__":
    main()
