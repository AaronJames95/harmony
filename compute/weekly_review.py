"""Script 3 — Weekly review.

Default mode: generate a review for the current/most recent week.
Backfill mode: generate reviews for every ISO week since --start.

Usage:
    python compute/weekly_review.py                        # current week
    python compute/weekly_review.py --backfill --start 2025-07-09
    python compute/weekly_review.py --dir /path --out /path
"""

import argparse
import json
import time
from collections import defaultdict
from datetime import date
from pathlib import Path

import anthropic

from llm_common import (
    DAILY_INPUTS,
    MODEL,
    extract_json_section,
    get_client,
    load_recurring_tasks,
)

WEEKLY_OUT = Path(
    "/home/aharon/Documents/vault-alpha/3_Nutrients/weekly_reviews"
)
MIN_DAYS = 3
DELAY_SECONDS = 0.5


def load_all_extracts(
    daily_dir: Path,
    start: str | None = None,
) -> list[tuple[str, dict]]:
    results = []
    for path in sorted(daily_dir.glob("????-??-??.md")):
        if start and path.stem < start:
            continue
        text = path.read_text(encoding="utf-8")
        extract = extract_json_section(text)
        if extract is not None:
            results.append((path.stem, extract))
    return results


def group_by_iso_week(
    extracts: list[tuple[str, dict]],
) -> dict[str, list[tuple[str, dict]]]:
    weeks: dict[str, list] = defaultdict(list)
    for date_str, data in extracts:
        d = date.fromisoformat(date_str)
        iso = d.isocalendar()
        key = f"{iso.year}-W{iso.week:02d}"
        weeks[key].append((date_str, data))
    return dict(sorted(weeks.items()))


def build_weekly_prompt(extracts: list[tuple[str, dict]], recurring_tasks: str | None = None) -> str:
    parts = []
    for date_str, data in extracts:
        parts.append(
            "--- " + date_str + " ---\n"
            + json.dumps(data, indent=2, ensure_ascii=False)
        )
    extracts_block = "\n\n".join(parts)

    recurring_block = ""
    if recurring_tasks:
        recurring_block = (
            "KNOWN RECURRING THREADS (tracked across the full journal history — "
            "if this week's tasks, struggles, or intentions connect to one of these, "
            "name it as the same ongoing thread rather than treating it as new; you "
            "can reference how long it's been recurring):\n\n"
            + recurring_tasks + "\n\n"
        )

    n = len(extracts)
    return (
        "You are writing a weekly review for a personal journaling pipeline. "
        "Below are structured daily extracts for " + str(n) + " days from one person's journal. "
        "This person is a creative-prophetic artist in NYC doing Ignatian spiritual practice.\n\n"
        "Write a weekly review markdown document covering ALL of the following sections:\n\n"
        "## Pattern Summary\n"
        "What repeated across the week — themes, moods, behaviors, dynamics.\n\n"
        "## Emotional Arc\n"
        "How did the week move? Start, middle, end. Key inflection points.\n\n"
        "## Verse and Lyrical Clusters\n"
        "Notable lines and phrases that appeared. Group by theme or feeling.\n\n"
        "## Tasks and Follow-Through\n"
        "Everything actionable mentioned. What was completed, what carried over, what was dropped.\n\n"
        "## Recurring Questions\n"
        "The open questions that kept surfacing. What is this person sitting with?\n\n"
        "## Consolation / Desolation Correlates\n"
        "What consistently brought consolation? What triggered desolation? Any patterns?\n\n"
        "## One Question Worth Sitting With\n"
        "The single most generative question to carry into next week.\n\n"
        "Be honest about both the generative and the hard. Do not smooth over struggle. "
        "Pull specific phrases from the data rather than writing generic summaries.\n\n"
        + recurring_block
        + "DAILY EXTRACTS:\n\n"
        + extracts_block
    )


def generate_weekly(
    label: str,
    extracts: list[tuple[str, dict]],
    out_dir: Path,
    client: anthropic.Anthropic,
    recurring_tasks: str | None = None,
) -> None:
    out_path = out_dir / f"{label}.md"
    if out_path.exists():
        print(f"  skip  {label} (already exists)")
        return

    dates = [d for d, _ in extracts]
    print(f"  gen   {label}  ({dates[0]} to {dates[-1]}, {len(extracts)} days)")

    prompt = build_weekly_prompt(extracts, recurring_tasks)
    response = client.messages.create(
        model=MODEL,
        max_tokens=4096,
        messages=[{"role": "user", "content": prompt}],
    )
    review_text = response.content[0].text

    header = (
        f"# Weekly Review — {label}\n"
        f"Days: {dates[0]} through {dates[-1]}\n"
        f"Generated: {date.today().isoformat()}\n\n"
    )
    out_dir.mkdir(parents=True, exist_ok=True)
    out_path.write_text(header + review_text, encoding="utf-8")


def main() -> None:
    parser = argparse.ArgumentParser(
        description="Generate weekly reviews from extracted daily notes."
    )
    parser.add_argument("--dir", type=Path, default=DAILY_INPUTS)
    parser.add_argument("--out", type=Path, default=WEEKLY_OUT)
    parser.add_argument("--backfill", action="store_true",
                        help="Generate reviews for all weeks since --start")
    parser.add_argument("--start", default=None,
                        help="Earliest date to include in backfill (YYYY-MM-DD)")
    parser.add_argument("--min-days", type=int, default=MIN_DAYS,
                        help="Minimum extracted days required to generate a review")
    args = parser.parse_args()

    client = get_client()
    recurring_tasks = load_recurring_tasks()

    if args.backfill:
        print(f"Backfill mode: loading all extracts from {args.start or 'beginning'}...")
        all_extracts = load_all_extracts(args.dir, start=args.start)
        weeks = group_by_iso_week(all_extracts)
        eligible = {k: v for k, v in weeks.items() if len(v) >= args.min_days}
        print(f"Found {len(weeks)} weeks, {len(eligible)} with >= {args.min_days} days")

        for i, (label, extracts) in enumerate(eligible.items()):
            generate_weekly(label, sorted(extracts), args.out, client, recurring_tasks)
            if i < len(eligible) - 1:
                time.sleep(DELAY_SECONDS)
    else:
        # Default: most recent week
        all_extracts = load_all_extracts(args.dir)
        if not all_extracts:
            raise SystemExit("No extracted daily notes found.")
        weeks = group_by_iso_week(all_extracts)
        label, extracts = list(weeks.items())[-1]
        extracts = sorted(extracts)
        if len(extracts) < args.min_days:
            raise SystemExit(
                f"Most recent week {label} only has {len(extracts)} days "
                f"(need {args.min_days}). Use --min-days to lower the threshold."
            )
        generate_weekly(label, extracts, args.out, client, recurring_tasks)

    print("Done.")


if __name__ == "__main__":
    main()
