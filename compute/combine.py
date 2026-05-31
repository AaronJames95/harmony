"""Stage 0a: parse legacy morning-pages/examen and new-template daily notes,
write one normalized raw-day file per date into --out.

Usage:
    python compute/combine.py --inputs samples/legacy --format legacy     --out out/
    python compute/combine.py --inputs samples/new    --format new_template --out out/
"""

import argparse
import datetime
import re
import sys
from pathlib import Path


# ---------------------------------------------------------------------------
# Skip-marker detection
# ---------------------------------------------------------------------------

_SKIP_MARKERS = ("NOT done", "(skipped)", "(no recording)", "(none)")


def _is_skip(text: str) -> bool:
    """Return True if the section has no substantive content.

    A section is absent when it is empty OR every non-empty content line is a
    skip signal (formal markers or the 'didn't do' prose variant).
    """
    lines = [
        line.strip().lstrip("*").strip()
        for line in text.splitlines()
        if line.strip()
    ]
    if not lines:
        return True
    return all(
        any(m.lower() in line.lower() for m in _SKIP_MARKERS)
        or line.lower().startswith("didn't do")
        for line in lines
    )


# ---------------------------------------------------------------------------
# Legacy parsing
# ---------------------------------------------------------------------------

_ENTRY_RE = re.compile(r"(?m)^(?=- \d+/\d+[:.]\s)")
_HEADER_RE = re.compile(r"^- (\d+)/(\d+)[:.]\s*", re.MULTILINE)


def _parse_morning_pages(path: Path) -> dict[datetime.date, str]:
    """Return {date: body_text} from a legacy Morning Pages file.

    Year is not known yet; returns keys with month/day only as (month, day)
    tuples — caller resolves to full dates after building the year map.
    """
    text = path.read_text(encoding="utf-8")
    entries: dict[tuple[int, int], str] = {}
    chunks = _ENTRY_RE.split(text)
    for chunk in chunks:
        chunk = chunk.strip()
        m = _HEADER_RE.match(chunk)
        if not m:
            continue
        month, day = int(m.group(1)), int(m.group(2))
        body = chunk[m.end():].strip()
        entries[(month, day)] = body
    return entries


_EXAMEN_ENTRY_RE = re.compile(r"(?m)^(?=- \d+/\d+[.:])")
_EXAMEN_HEADER_RE = re.compile(r"^- (\d+)/(\d+)[.:]\s*", re.MULTILINE)
_EXAMEN_FNAME_RE = re.compile(r"EX_(\d{2})_(\d{4})\.md$", re.IGNORECASE)


def _parse_examen_file(path: Path) -> tuple[int, int, dict[tuple[int, int], str]]:
    """Return (month, year, {(month, day): body}) from an EX_MM_YYYY.md file."""
    m = _EXAMEN_FNAME_RE.search(path.name)
    if not m:
        raise ValueError(f"Unexpected examen filename: {path.name}")
    file_month, file_year = int(m.group(1)), int(m.group(2))

    text = path.read_text(encoding="utf-8")
    entries: dict[tuple[int, int], str] = {}
    chunks = _EXAMEN_ENTRY_RE.split(text)
    for chunk in chunks:
        chunk = chunk.strip()
        hm = _EXAMEN_HEADER_RE.match(chunk)
        if not hm:
            continue
        month, day = int(hm.group(1)), int(hm.group(2))
        body = chunk[hm.end():].strip()
        entries[(month, day)] = body
    return file_month, file_year, entries


def _process_legacy(
    inputs_dir: Path,
    out_dir: Path,
    generated_at: str,
    year_override: int | None,
) -> None:
    # --- Collect examen files and build month→year map ---
    month_to_year: dict[int, int] = {}
    examen_entries: dict[tuple[int, int], str] = {}

    for ex_path in inputs_dir.rglob("EX_*.md"):
        file_month, file_year, entries = _parse_examen_file(ex_path)
        month_to_year[file_month] = file_year
        examen_entries.update(entries)

    def resolve_year(month: int) -> int:
        if year_override is not None:
            return year_override
        if month not in month_to_year:
            raise ValueError(
                f"No examen file covers month {month}; "
                "pass --year YYYY to set the year explicitly."
            )
        return month_to_year[month]

    # --- Collect morning-pages entries ---
    mp_raw: dict[tuple[int, int], str] = {}
    mp_path = inputs_dir / "Morning Pages.md"
    if mp_path.exists():
        mp_raw = _parse_morning_pages(mp_path)

    # --- Resolve full dates ---
    all_md: dict[int, datetime.date] = {}  # month→day→date
    mp: dict[datetime.date, str] = {}
    for (month, day), body in mp_raw.items():
        date = datetime.date(resolve_year(month), month, day)
        mp[date] = body

    ex: dict[datetime.date, str] = {}
    for (month, day), body in examen_entries.items():
        date = datetime.date(resolve_year(month), month, day)
        ex[date] = body

    # --- Merge by date ---
    all_dates = sorted(mp.keys() | ex.keys())
    if not all_dates:
        print("Warning: no entries found in legacy inputs.", file=sys.stderr)
        return

    for date in _date_range(all_dates[0], all_dates[-1]):
        mp_text = mp.get(date)
        ex_text = ex.get(date)

        if mp_text is None and ex_text is None:
            # Gap-fill absence
            _write_raw_day(
                out_dir, date, "none",
                {"morning_pages": False, "examen": False},
                "inputs: none",
                generated_at,
            )
        else:
            sources_present = {
                "morning_pages": mp_text is not None,
                "examen": ex_text is not None,
            }
            body_parts = []
            if mp_text is not None:
                body_parts.append(f"## Morning Pages\n\n{mp_text}")
            if ex_text is not None:
                body_parts.append(f"## Examen\n\n{ex_text}")
            body = "\n\n".join(body_parts)
            _write_raw_day(out_dir, date, "legacy", sources_present, body, generated_at)


# ---------------------------------------------------------------------------
# New-template parsing
# ---------------------------------------------------------------------------

# The four tracked sources and the emoji that heads their section.
_TRACKED_SECTIONS: list[tuple[str, str]] = [
    ("meditation",       "😌"),
    ("examen",           "🤲🏽"),
    ("morning_pages",    "📝"),
    ("video_transcript", "📹"),
]

_DATE_FNAME_RE = re.compile(r"^(\d{4}-\d{2}-\d{2})\.md$")


def _extract_section(text: str, emoji: str) -> str | None:
    """Return the immediate bullet content of the section starting with `emoji`.

    Stops at the next tracked emoji header OR the first non-bullet, non-blank
    line (a plain-text subsection label like "Gratitude" inside the Examen
    block).  This keeps detection focused on the top-level practice marker
    (e.g. "* NOT done") rather than the rich subsection content that follows.
    """
    start_m = re.search(rf"^{re.escape(emoji)}.*?$", text, re.MULTILINE)
    if start_m is None:
        return None

    immediate: list[str] = []
    for line in text[start_m.end():].splitlines():
        stripped = line.strip()
        # Skip leading blank lines before any content appears
        if not stripped and not immediate:
            continue
        # Stop at any tracked emoji (next tracked section)
        if any(stripped.startswith(e) for _, e in _TRACKED_SECTIONS):
            break
        # Blank line once content has started: keep it (multi-bullet sections)
        if not stripped:
            immediate.append(line)
            continue
        # Bullet or checkbox lines belong to this section's immediate content
        if stripped.startswith(("*", "-", "[")):
            immediate.append(line)
        else:
            # Plain non-bullet text = subsection header (e.g. "Gratitude") — stop
            break

    return "\n".join(immediate).strip() or None


def _process_new_template(
    inputs_dir: Path,
    out_dir: Path,
    generated_at: str,
) -> None:
    dated_files: list[tuple[datetime.date, Path]] = []
    for p in inputs_dir.iterdir():
        m = _DATE_FNAME_RE.match(p.name)
        if m:
            dated_files.append((datetime.date.fromisoformat(m.group(1)), p))

    if not dated_files:
        print("Warning: no YYYY-MM-DD.md files found in new-template inputs.", file=sys.stderr)
        return

    dated_files.sort()
    real_dates: set[datetime.date] = set()

    for date, path in dated_files:
        real_dates.add(date)
        text = path.read_text(encoding="utf-8")

        sources_present: dict[str, bool] = {}
        for key, emoji in _TRACKED_SECTIONS:
            section = _extract_section(text, emoji)
            sources_present[key] = (section is not None and not _is_skip(section))

        body = f"## Daily Note\n\n{text.strip()}"
        _write_raw_day(out_dir, date, "new_template", sources_present, body, generated_at)

    # Gap-fill within the new-template batch range
    all_dates = sorted(real_dates)
    for date in _date_range(all_dates[0], all_dates[-1]):
        if date not in real_dates:
            _write_raw_day(
                out_dir, date, "none",
                {"meditation": False, "examen": False,
                 "morning_pages": False, "video_transcript": False},
                "inputs: none",
                generated_at,
            )


# ---------------------------------------------------------------------------
# Output writing
# ---------------------------------------------------------------------------

def _compute_score(source_format: str, sources_present: dict[str, bool]) -> float:
    if source_format == "none":
        return 0.0
    denominator = 2 if source_format == "legacy" else 4
    return sum(sources_present.values()) / denominator


def _write_raw_day(
    out_dir: Path,
    date: datetime.date,
    source_format: str,
    sources_present: dict[str, bool],
    body: str,
    generated_at: str,
) -> None:
    path = out_dir / f"{date}.md"
    if path.exists():
        return  # resumable: already written

    score = _compute_score(source_format, sources_present)
    sp_lines = "\n".join(
        f"  {k}: {str(v).lower()}" for k, v in sources_present.items()
    )
    content = (
        f"---\n"
        f"date: {date}\n"
        f"source_format: {source_format}\n"
        f"sources_present:\n"
        f"{sp_lines}\n"
        f"input_completion_score: {score}\n"
        f"generated_by: combine.py\n"
        f"generated_at: {generated_at}\n"
        f"---\n"
        f"\n"
        f"{body}\n"
    )
    path.write_text(content, encoding="utf-8")


# ---------------------------------------------------------------------------
# Helpers
# ---------------------------------------------------------------------------

def _date_range(start: datetime.date, end: datetime.date):
    current = start
    while current <= end:
        yield current
        current += datetime.timedelta(days=1)


# ---------------------------------------------------------------------------
# CLI
# ---------------------------------------------------------------------------

def main() -> None:
    parser = argparse.ArgumentParser(
        description="Stage 0a: combine raw sources into normalized raw-day files."
    )
    parser.add_argument("--inputs", required=True, type=Path, help="Input directory")
    parser.add_argument(
        "--format", required=True, choices=["legacy", "new_template"],
        dest="fmt", help="Input format"
    )
    parser.add_argument("--out", required=True, type=Path, help="Output directory")
    parser.add_argument(
        "--year", type=int, default=None,
        help="Override year for legacy morning-pages entries (when no examen files present)"
    )
    args = parser.parse_args()

    if not args.inputs.exists():
        sys.exit(f"Error: inputs directory does not exist: {args.inputs}")

    args.out.mkdir(parents=True, exist_ok=True)
    generated_at = datetime.datetime.now().isoformat(timespec="seconds")

    if args.fmt == "legacy":
        _process_legacy(args.inputs, args.out, generated_at, args.year)
    else:
        _process_new_template(args.inputs, args.out, generated_at)


if __name__ == "__main__":
    main()
