"""Quarterly review.

Uses monthly reviews as input when available (preferred), falls back to
sampled daily extracts if monthly reviews are missing.

Usage:
    python compute/quarterly_review.py --backfill
    python compute/quarterly_review.py --quarter 2025-Q3
"""

import argparse
import json
import time
from datetime import date
from pathlib import Path

import anthropic

from llm_common import (
    DAILY_INPUTS,
    MODEL,
    RECURRING_TASKS_PATH,
    extract_json_section,
    get_client,
    load_recurring_tasks,
)

MONTHLY_REVIEWS = Path(
    "/home/aharon/Documents/vault-alpha/3_Nutrients/monthly_reviews"
)
QUARTERLY_OUT = Path(
    "/home/aharon/Documents/vault-alpha/3_Nutrients/quarterly_reviews"
)
DELAY_SECONDS = 0.5

_QUARTER_MONTHS = {1: (1, 2, 3), 2: (4, 5, 6), 3: (7, 8, 9), 4: (10, 11, 12)}
_MONTH_NAMES = {
    1: "January", 2: "February", 3: "March", 4: "April",
    5: "May", 6: "June", 7: "July", 8: "August",
    9: "September", 10: "October", 11: "November", 12: "December",
}


def quarter_label(year: int, q: int) -> str:
    return f"{year}-Q{q}"


def all_quarters(start_year: int, start_q: int, end_year: int, end_q: int) -> list[tuple[int, int]]:
    result = []
    y, q = start_year, start_q
    while (y, q) <= (end_year, end_q):
        result.append((y, q))
        q += 1
        if q > 4:
            q = 1
            y += 1
    return result


def load_monthly_review(monthly_dir: Path, year: int, month: int) -> str | None:
    path = monthly_dir / f"{year}-{month:02d}.md"
    if path.exists():
        return path.read_text(encoding="utf-8")
    return None


def load_daily_extracts_for_months(
    daily_dir: Path, year: int, months: tuple[int, ...]
) -> list[tuple[str, dict]]:
    month_prefixes = {f"{year}-{m:02d}" for m in months}
    results = []
    for path in sorted(daily_dir.glob("????-??-??.md")):
        if path.stem[:7] in month_prefixes:
            text = path.read_text(encoding="utf-8")
            extract = extract_json_section(text)
            if extract is not None:
                results.append((path.stem, extract))
    return results


def windowed_recurring_tasks_path(quarter_label: str) -> Path:
    return RECURRING_TASKS_PATH.parent / f"recurring_tasks_{quarter_label}.md"


def build_recurring_context(global_text: str | None, windowed_text: str | None) -> str:
    if not global_text and not windowed_text:
        return ""
    parts = []
    if windowed_text:
        parts.append(
            "THIS QUARTER'S RECURRING TASKS (clustered from just this quarter's days — "
            "these are current priorities; weight them most heavily in 'The Central "
            "Struggle' and 'Carried Forward'):\n\n" + windowed_text
        )
    if global_text:
        parts.append(
            "LIFETIME RECURRING THREADS (tracked across the full journal history — "
            "if this quarter connects to one of these long-running threads, name it "
            "and reference how long it's been recurring):\n\n" + global_text
        )
    return "\n\n".join(parts) + "\n\n"


def build_quarterly_from_monthlies(
    label: str, monthly_texts: list[tuple[str, str]], recurring_context: str = ""
) -> str:
    year, q = int(label[:4]), int(label[6])
    months = _QUARTER_MONTHS[q]
    month_range = f"{_MONTH_NAMES[months[0]]}–{_MONTH_NAMES[months[2]]} {year}"
    n = len(monthly_texts)

    parts = []
    for month_label, text in monthly_texts:
        parts.append("=== " + month_label + " ===\n\n" + text)
    content_block = "\n\n".join(parts)

    return (
        "You are writing a quarterly review for a personal journaling pipeline. "
        "Below are " + str(n) + " monthly reviews covering " + month_range + ". "
        "This person is a creative-prophetic artist in NYC doing Ignatian spiritual practice.\n\n"
        "Write a high-altitude quarterly review covering ALL of the following sections:\n\n"
        "## The Character of This Quarter\n"
        "What would you name this quarter? What was its essential nature — the dominant key it was written in?\n\n"
        "## Major Chapters\n"
        "The distinct phases or seasons within these three months. What shifted between them?\n\n"
        "## Interior Trajectory\n"
        "How did this person change? What shifted in their inner life, self-understanding, or faith?\n\n"
        "## Creative Arc\n"
        "What was built, attempted, abandoned, or begun creatively? What's the direction of travel?\n\n"
        "## The Central Struggle\n"
        "The dominant battle this quarter — name it precisely. How did it move?\n\n"
        "## Consolation Patterns\n"
        "What consistently brought life, peace, or creative fire? What is God pointing toward?\n\n"
        "## Tasks and Momentum\n"
        "What got done. What was perpetually deferred. What broke through.\n\n"
        "## Carried Forward\n"
        "The unresolved threads this quarter hands to the next. What is still alive and moving?\n\n"
        "## One True Thing\n"
        "The single most important sentence about this quarter.\n\n"
        "Connect dots across months. Be willing to name what's actually happening beneath the surface. "
        "This is a high-altitude view — synthesis, not summary.\n\n"
        + recurring_context
        + "MONTHLY REVIEWS:\n\n"
        + content_block
    )


def build_quarterly_from_dailies(
    label: str, extracts: list[tuple[str, dict]], recurring_context: str = ""
) -> str:
    year, q = int(label[:4]), int(label[6])
    months = _QUARTER_MONTHS[q]
    month_range = f"{_MONTH_NAMES[months[0]]}–{_MONTH_NAMES[months[2]]} {year}"
    n = len(extracts)

    parts = []
    for date_str, data in extracts:
        condensed = {
            "date": date_str,
            "summary": data.get("summary", ""),
            "energy_level": data.get("energy_level", ""),
            "spiritual_movement": data.get("spiritual_movement", ""),
            "creative_spark_moment": data.get("creative_spark_moment", [])[:2],
            "struggles_and_fears": data.get("struggles_and_fears", [])[:2],
        }
        parts.append("--- " + date_str + " ---\n" + json.dumps(condensed, ensure_ascii=False))
    content_block = "\n\n".join(parts)

    return (
        "You are writing a quarterly review for a personal journaling pipeline. "
        "Below are condensed daily extracts for " + str(n) + " days covering " + month_range + ". "
        "This person is a creative-prophetic artist in NYC doing Ignatian spiritual practice.\n\n"
        "Write a high-altitude quarterly review covering ALL of the following sections:\n\n"
        "## The Character of This Quarter\n"
        "What would you name this quarter? What was its essential nature?\n\n"
        "## Major Chapters\n"
        "The distinct phases or seasons within these three months.\n\n"
        "## Interior Trajectory\n"
        "How did this person change over the quarter?\n\n"
        "## Creative Arc\n"
        "What was built, attempted, abandoned, or begun creatively?\n\n"
        "## The Central Struggle\n"
        "The dominant battle — name it precisely.\n\n"
        "## Consolation Patterns\n"
        "What consistently brought life or peace?\n\n"
        "## Tasks and Momentum\n"
        "What got done vs what was perpetually deferred.\n\n"
        "## Carried Forward\n"
        "Unresolved threads handed to next quarter.\n\n"
        "## One True Thing\n"
        "The single most important sentence about this quarter.\n\n"
        + recurring_context
        + "DAILY EXTRACTS (" + str(n) + " days):\n\n"
        + content_block
    )


def generate_quarterly(
    year: int,
    q: int,
    daily_dir: Path,
    monthly_dir: Path,
    out_dir: Path,
    client: anthropic.Anthropic,
    recurring_tasks: str | None = None,
) -> None:
    label = quarter_label(year, q)
    out_path = out_dir / f"{label}.md"
    if out_path.exists():
        print(f"  skip  {label} (already exists)")
        return

    months = _QUARTER_MONTHS[q]

    # Prefer monthly reviews as input
    monthly_texts = []
    for m in months:
        text = load_monthly_review(monthly_dir, year, m)
        if text:
            monthly_texts.append((f"{year}-{m:02d}", text))

    windowed = load_recurring_tasks(windowed_recurring_tasks_path(label))
    recurring_context = build_recurring_context(recurring_tasks, windowed)

    if len(monthly_texts) == len(months):
        print(f"  gen   {label}  (from {len(monthly_texts)} monthly reviews)")
        prompt = build_quarterly_from_monthlies(label, monthly_texts, recurring_context)
    else:
        # Fall back to daily extracts
        extracts = load_daily_extracts_for_months(daily_dir, year, months)
        if not extracts:
            print(f"  skip  {label} (no data)")
            return
        missing = len(months) - len(monthly_texts)
        print(f"  gen   {label}  (from {len(extracts)} daily extracts; {missing} monthly reviews missing)")
        prompt = build_quarterly_from_dailies(label, extracts, recurring_context)

    response = client.messages.create(
        model=MODEL,
        max_tokens=8096,
        messages=[{"role": "user", "content": prompt}],
    )
    review_text = response.content[0].text

    month_names = [_MONTH_NAMES[m] for m in months]
    header = (
        f"# Quarterly Review — Q{q} {year}\n"
        f"Period: {month_names[0]}–{month_names[2]} {year}\n"
        f"Generated: {date.today().isoformat()}\n\n"
    )
    out_dir.mkdir(parents=True, exist_ok=True)
    out_path.write_text(header + review_text, encoding="utf-8")


def main() -> None:
    parser = argparse.ArgumentParser(
        description="Generate quarterly reviews, preferring monthly reviews as input."
    )
    parser.add_argument("--dir", type=Path, default=DAILY_INPUTS)
    parser.add_argument("--monthly-dir", type=Path, default=MONTHLY_REVIEWS)
    parser.add_argument("--out", type=Path, default=QUARTERLY_OUT)
    parser.add_argument("--backfill", action="store_true",
                        help="Generate all quarters from --start to last complete quarter")
    parser.add_argument("--start", default="2025-Q3",
                        help="Earliest quarter (YYYY-QN, default: 2025-Q3)")
    parser.add_argument("--quarter", default=None,
                        help="Generate a single quarter (YYYY-QN)")
    args = parser.parse_args()

    client = get_client()
    recurring_tasks = load_recurring_tasks()

    today = date.today()
    current_q = (today.month - 1) // 3 + 1

    if args.quarter:
        year, q = int(args.quarter[:4]), int(args.quarter[6])
        quarters = [(year, q)]
    elif args.backfill:
        start_year, start_q = int(args.start[:4]), int(args.start[6])
        # End at last complete quarter
        end_q = current_q - 1
        end_year = today.year
        if end_q < 1:
            end_q = 4
            end_year -= 1
        quarters = all_quarters(start_year, start_q, end_year, end_q)
    else:
        # Default: most recent complete quarter
        end_q = current_q - 1
        end_year = today.year
        if end_q < 1:
            end_q = 4
            end_year -= 1
        quarters = [(end_year, end_q)]

    print(f"Generating {len(quarters)} quarterly review(s)...")
    for i, (year, q) in enumerate(quarters):
        generate_quarterly(year, q, args.dir, args.monthly_dir, args.out, client, recurring_tasks)
        if i < len(quarters) - 1:
            time.sleep(DELAY_SECONDS)

    print("Done.")


if __name__ == "__main__":
    main()
