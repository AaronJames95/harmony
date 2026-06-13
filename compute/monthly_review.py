"""Monthly review.

Generates a monthly review from all extracted daily notes in a given month.
Backfill mode processes every month since --start.

Usage:
    python compute/monthly_review.py --backfill --start 2025-07
    python compute/monthly_review.py --month 2025-11
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
    RECURRING_TASKS_PATH,
    extract_json_section,
    get_client,
    load_recurring_tasks,
)

MONTHLY_OUT = Path(
    "/home/aharon/Documents/vault-alpha/3_Nutrients/monthly_reviews"
)
MIN_DAYS = 10
DELAY_SECONDS = 0.5

_MONTH_NAMES = {
    1: "January", 2: "February", 3: "March", 4: "April",
    5: "May", 6: "June", 7: "July", 8: "August",
    9: "September", 10: "October", 11: "November", 12: "December",
}


def load_all_extracts(daily_dir: Path, start: str | None = None) -> list[tuple[str, dict]]:
    results = []
    for path in sorted(daily_dir.glob("????-??-??.md")):
        if start and path.stem[:7] < start:
            continue
        text = path.read_text(encoding="utf-8")
        extract = extract_json_section(text)
        if extract is not None:
            results.append((path.stem, extract))
    return results


def group_by_month(extracts: list[tuple[str, dict]]) -> dict[str, list[tuple[str, dict]]]:
    months: dict[str, list] = defaultdict(list)
    for date_str, data in extracts:
        key = date_str[:7]  # YYYY-MM
        months[key].append((date_str, data))
    return dict(sorted(months.items()))


def windowed_recurring_tasks_path(month_label: str) -> Path:
    return RECURRING_TASKS_PATH.parent / f"recurring_tasks_{month_label}.md"


def build_recurring_context(global_text: str | None, windowed_text: str | None) -> str:
    if not global_text and not windowed_text:
        return ""
    parts = []
    if windowed_text:
        parts.append(
            "THIS MONTH'S RECURRING TASKS (clustered from just this month's days — "
            "these are current priorities; weight them most heavily in 'Recurring "
            "Struggles' and 'Tasks and Follow-Through'):\n\n" + windowed_text
        )
    if global_text:
        parts.append(
            "LIFETIME RECURRING THREADS (tracked across the full journal history — "
            "if this month connects to one of these long-running threads, name it "
            "and reference how long it's been recurring):\n\n" + global_text
        )
    return "\n\n".join(parts) + "\n\n"


def build_monthly_prompt(
    month_label: str, extracts: list[tuple[str, dict]], recurring_context: str = ""
) -> str:
    year, month = int(month_label[:4]), int(month_label[5:])
    month_name = _MONTH_NAMES[month]
    n = len(extracts)

    parts = []
    for date_str, data in extracts:
        condensed = {
            "date": date_str,
            "summary": data.get("summary", ""),
            "energy_level": data.get("energy_level", ""),
            "spiritual_movement": data.get("spiritual_movement", ""),
            "creative_spark_moment": data.get("creative_spark_moment", []),
            "struggles_and_fears": data.get("struggles_and_fears", []),
            "spiritual_consolation_source": data.get("spiritual_consolation_source", ""),
            "verse_and_lyrical_lines": data.get("verse_and_lyrical_lines", []),
            "tasks_and_intentions": data.get("tasks_and_intentions", []),
        }
        parts.append("--- " + date_str + " ---\n" + json.dumps(condensed, indent=2, ensure_ascii=False))

    extracts_block = "\n\n".join(parts)

    return (
        "You are writing a monthly review for a personal journaling pipeline. "
        "Below are condensed daily extracts for " + str(n) + " days in " + month_name + " " + str(year) + ". "
        "This person is a creative-prophetic artist in NYC doing Ignatian spiritual practice.\n\n"
        "Write a monthly review covering ALL of the following sections:\n\n"
        "## Month in Brief\n"
        "2-3 sentences capturing the essential character of this month.\n\n"
        "## Emotional Arc\n"
        "How did the month move? Key inflection points, shifts, turning points. Name the phases.\n\n"
        "## Creative Thread\n"
        "What creative work, ideas, or artistic development happened? What built toward something?\n\n"
        "## Spiritual Movement\n"
        "Overall consolation/desolation pattern for the month. What was God doing? "
        "What was the bad spirit doing? Where was the person most alive?\n\n"
        "## Relational Landscape\n"
        "Who mattered this month? What connections deepened, strained, or were sought?\n\n"
        "## Recurring Struggles\n"
        "What kept showing up that hasn't resolved? Be specific — name the actual dynamics.\n\n"
        "## Tasks and Follow-Through\n"
        "What was intended vs what actually happened. What was abandoned. What built momentum.\n\n"
        "## What Built This Month\n"
        "Concrete inner or outer progress. What is genuinely different at month's end?\n\n"
        "## Into Next Month\n"
        "1-2 sentences: what does this month leave behind, and what does it hand forward?\n\n"
        "Be honest. Pull specific phrases. Do not smooth over hard stretches or inflate good ones.\n\n"
        + recurring_context
        + "DAILY EXTRACTS (" + str(n) + " days):\n\n"
        + extracts_block
    )


def generate_monthly(
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

    windowed = load_recurring_tasks(windowed_recurring_tasks_path(label))
    recurring_context = build_recurring_context(recurring_tasks, windowed)
    prompt = build_monthly_prompt(label, extracts, recurring_context)
    response = client.messages.create(
        model=MODEL,
        max_tokens=4096,
        messages=[{"role": "user", "content": prompt}],
    )
    review_text = response.content[0].text

    year, month = int(label[:4]), int(label[5:])
    header = (
        f"# Monthly Review — {_MONTH_NAMES[month]} {year}\n"
        f"Days covered: {dates[0]} through {dates[-1]} ({len(extracts)} days)\n"
        f"Generated: {date.today().isoformat()}\n\n"
    )
    out_dir.mkdir(parents=True, exist_ok=True)
    out_path.write_text(header + review_text, encoding="utf-8")


def main() -> None:
    parser = argparse.ArgumentParser(
        description="Generate monthly reviews from extracted daily notes."
    )
    parser.add_argument("--dir", type=Path, default=DAILY_INPUTS)
    parser.add_argument("--out", type=Path, default=MONTHLY_OUT)
    parser.add_argument("--backfill", action="store_true",
                        help="Generate reviews for all months since --start")
    parser.add_argument("--start", default=None,
                        help="Earliest month to include (YYYY-MM)")
    parser.add_argument("--month", default=None,
                        help="Generate a single month (YYYY-MM)")
    parser.add_argument("--min-days", type=int, default=MIN_DAYS)
    args = parser.parse_args()

    client = get_client()
    recurring_tasks = load_recurring_tasks()

    all_extracts = load_all_extracts(args.dir, start=args.start)
    months = group_by_month(all_extracts)

    if args.month:
        target = {args.month: months.get(args.month, [])}
        if not target[args.month]:
            raise SystemExit(f"No extracts found for month {args.month}")
        months = target
    elif not args.backfill:
        # Default: most recent complete month
        today = date.today()
        current_month = f"{today.year}-{today.month:02d}"
        complete = {k: v for k, v in months.items() if k < current_month}
        if not complete:
            raise SystemExit("No complete months found.")
        last = sorted(complete.keys())[-1]
        months = {last: complete[last]}

    eligible = {k: sorted(v) for k, v in months.items() if len(v) >= args.min_days}
    skipped_thin = {k: v for k, v in months.items() if len(v) < args.min_days}
    if skipped_thin:
        print(f"Skipping {len(skipped_thin)} months with < {args.min_days} days: "
              f"{', '.join(sorted(skipped_thin))}")

    print(f"Generating {len(eligible)} monthly reviews...")
    for i, (label, extracts) in enumerate(eligible.items()):
        generate_monthly(label, extracts, args.out, client, recurring_tasks)
        if i < len(eligible) - 1:
            time.sleep(DELAY_SECONDS)

    print("Done.")


if __name__ == "__main__":
    main()
