"""Script 1 — Backfill merger.

Parse morning pages and examen files from the live vault.
For each date from 2025-07-01 onward, create a daily note if one does not exist.
Resumable — skips dates that already have a file.

Usage:
    python compute/backfill.py
    python compute/backfill.py --start 2025-07-01 --out /path/to/daily_inputs
"""

import argparse
import datetime
import re
import sys
from pathlib import Path

MORNING_PAGES_PATH = Path(
    "/home/aharon/Documents/vault-alpha/2_Roots/Art/Morning Pages.md"
)
EXAMEN_DIR = Path(
    "/home/aharon/Documents/vault-alpha/2_Roots/יֵשׁוּעַ/Examen"
)
DAILY_INPUTS = Path(
    "/home/aharon/Documents/vault-alpha/3_Nutrients/daily_inputs"
)
DEFAULT_START = datetime.date(2025, 7, 1)

# Matches the start of a morning-pages entry: "- M/D:" or "- M/D." or "* M/D."
_MP_SPLIT_RE = re.compile(r"(?m)^(?=[\*\-] \d+/\d+[:.]\s)")
_MP_HEADER_RE = re.compile(r"^[\*\-] (\d+)/(\d+)[.:]\s*")

# Month section headers in Morning Pages.md (e.g. "# July")
_MP_SECTION_RE = re.compile(
    r"^# (January|February|March|April|May|June|"
    r"July|August|September|October|November|December)\s*$",
    re.MULTILINE | re.IGNORECASE,
)
_MONTH_TO_NUM = {
    "january": 1, "february": 2, "march": 3, "april": 4,
    "may": 5, "june": 6, "july": 7, "august": 8,
    "september": 9, "october": 10, "november": 11, "december": 12,
}

# Matches the start of an examen entry: "* M/D." or "- M/D." or "* M/D:"
_EX_SPLIT_RE = re.compile(r"(?m)^(?=[\*\-] \d+/\d+[.:])")
_EX_HEADER_RE = re.compile(r"^[\*\-] (\d+)/(\d+)[.:]\s*")

_EX_FNAME_RE = re.compile(r"EX_(\d{2})_(\d{4})\.md$", re.IGNORECASE)


# ---------------------------------------------------------------------------
# Parsing
# ---------------------------------------------------------------------------

def parse_morning_pages(path: Path) -> list[tuple[int, int, str]]:
    """Return [(month, day, body), ...] in file order.

    Uses '# Month' section headers to determine the month for each entry.
    This avoids year-resolution errors from out-of-order date prefixes
    (e.g. a '9/3.' entry written inside the '# August' section).
    """
    text = path.read_text(encoding="utf-8")
    header_matches = list(_MP_SECTION_RE.finditer(text))

    if not header_matches:
        # No section headers — fall back to entry-declared month
        entries: list[tuple[int, int, str]] = []
        for chunk in _MP_SPLIT_RE.split(text):
            chunk = chunk.strip()
            m = _MP_HEADER_RE.match(chunk)
            if not m:
                continue
            entries.append((int(m.group(1)), int(m.group(2)), chunk[m.end():].strip()))
        return entries

    entries = []
    for i, hm in enumerate(header_matches):
        section_month = _MONTH_TO_NUM[hm.group(1).lower()]
        section_start = hm.end()
        section_end = header_matches[i + 1].start() if i + 1 < len(header_matches) else len(text)
        section_text = text[section_start:section_end]

        for chunk in _MP_SPLIT_RE.split(section_text):
            chunk = chunk.strip()
            m = _MP_HEADER_RE.match(chunk)
            if not m:
                continue
            day = int(m.group(2))  # month comes from section header, day from entry
            entries.append((section_month, day, chunk[m.end():].strip()))

    return entries


def resolve_mp_years(
    entries: list[tuple[int, int, str]],
    examen_month_years: dict[int, list[int]],
) -> dict[datetime.date, str]:
    """Assign years to morning-pages entries using chronological rollover.

    Uses examen file months as year anchors; rolls over when month decreases.
    """
    if not entries:
        return {}

    first_month = entries[0][0]
    candidate_years = sorted(examen_month_years.get(first_month, []))
    if not candidate_years:
        raise ValueError(
            f"Cannot determine year for morning-pages entries starting in month "
            f"{first_month}. No examen file covers that month."
        )
    if len(candidate_years) > 1:
        raise ValueError(
            f"Month {first_month} appears in examen files for multiple years "
            f"{candidate_years}. Pass --mp-year YYYY to set explicitly."
        )

    current_year = candidate_years[0]
    result: dict[datetime.date, str] = {}
    prev_month: int | None = None

    for month, day, body in entries:
        if prev_month is not None and month < prev_month:
            current_year += 1
            print(f"  [backfill] MP year rollover {prev_month}→{month}, now {current_year}", file=sys.stderr)
        try:
            date = datetime.date(current_year, month, day)
        except ValueError as exc:
            print(f"  [backfill] skipping invalid date {current_year}-{month}-{day}: {exc}", file=sys.stderr)
            prev_month = month
            continue
        result[date] = body
        prev_month = month

    return result


def parse_examen_files(
    examen_dir: Path,
) -> tuple[dict[datetime.date, str], dict[int, list[int]]]:
    """Return (date_to_text, month_to_years) from all EX_MM_YYYY.md files."""
    by_date: dict[datetime.date, str] = {}
    month_years: dict[int, list[int]] = {}

    for path in sorted(examen_dir.rglob("EX_*.md")):
        m = _EX_FNAME_RE.search(path.name)
        if not m:
            continue
        file_month, file_year = int(m.group(1)), int(m.group(2))
        month_years.setdefault(file_month, []).append(file_year)

        text = path.read_text(encoding="utf-8")
        for chunk in _EX_SPLIT_RE.split(text):
            chunk = chunk.strip()
            hm = _EX_HEADER_RE.match(chunk)
            if not hm:
                continue
            month, day = int(hm.group(1)), int(hm.group(2))
            try:
                date = datetime.date(file_year, month, day)
            except ValueError:
                continue
            by_date[date] = chunk[hm.end():].strip()

    return by_date, month_years


# ---------------------------------------------------------------------------
# Note generation
# ---------------------------------------------------------------------------

def _weekday_name(d: datetime.date) -> str:
    return d.strftime("%A")


def build_note(date: datetime.date, mp_text: str | None, ex_text: str | None) -> str:
    lines = [
        "#dailynote",
        f"# {date} — {_weekday_name(date)}",
        "",
    ]
    if ex_text:
        lines += [
            "## 🤲🏽 Examen",
            ex_text,
            "",
        ]
    if mp_text:
        lines += [
            "## 📝 Morning Pages",
            mp_text,
            "",
        ]
    lines += [
        "## 💡 Sort Thoughts",
        "",
        "## ✅ ONE THING",
        "",
        "## 📹 Daily Video Transcript",
        "",
    ]
    return "\n".join(lines)


# ---------------------------------------------------------------------------
# Main
# ---------------------------------------------------------------------------

def main() -> None:
    parser = argparse.ArgumentParser(
        description="Backfill daily notes from morning pages and examen sources."
    )
    parser.add_argument("--out", type=Path, default=DAILY_INPUTS)
    parser.add_argument("--start", default=str(DEFAULT_START))
    parser.add_argument("--mp-year", type=int, default=None,
                        help="Override starting year for morning-pages resolution")
    args = parser.parse_args()

    start = datetime.date.fromisoformat(args.start)
    today = datetime.date.today()
    out_dir: Path = args.out
    out_dir.mkdir(parents=True, exist_ok=True)

    print("Parsing examen files...")
    ex_by_date, month_years = parse_examen_files(EXAMEN_DIR)
    print(f"  {len(ex_by_date)} examen entries across {len(month_years)} months")

    print("Parsing morning pages...")
    if not MORNING_PAGES_PATH.exists():
        sys.exit(f"Morning pages file not found: {MORNING_PAGES_PATH}")
    mp_ordered = parse_morning_pages(MORNING_PAGES_PATH)

    # Allow year override for edge cases
    if args.mp_year is not None:
        # Inject a fake anchor for the first month
        first_month = mp_ordered[0][0] if mp_ordered else 1
        month_years[first_month] = [args.mp_year]

    mp_by_date = resolve_mp_years(mp_ordered, month_years)
    print(f"  {len(mp_by_date)} morning-pages entries")

    all_dates = sorted(
        d for d in (mp_by_date.keys() | ex_by_date.keys())
        if start <= d <= today
    )
    print(f"Processing {len(all_dates)} dates from {start} to {today}...")

    created = skipped = 0
    for date in all_dates:
        out_path = out_dir / f"{date}.md"
        if out_path.exists():
            skipped += 1
            continue
        mp = mp_by_date.get(date)
        ex = ex_by_date.get(date)
        out_path.write_text(build_note(date, mp, ex), encoding="utf-8")
        created += 1
        print(f"  created  {date}")

    print(f"\nDone. created={created}  skipped={skipped}")


if __name__ == "__main__":
    main()
