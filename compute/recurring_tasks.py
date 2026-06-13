"""Recurring tasks tracker.

Scans every daily extract's `tasks_and_intentions` and clusters near-duplicate
phrasings (e.g. "get adderall" / "talk to psychiatrist about ADHD meds") into
canonical recurring threads, with how often and over what span each one
appears. Tasks that show up many times across many days are the ones quietly
carrying the most weight — this surfaces them.

Standalone / ad hoc: not wired into the weekly/monthly/quarterly pipeline.
Run it whenever you want a cross-time-series view.

Usage:
    python compute/recurring_tasks.py
    python compute/recurring_tasks.py --start 2026-01-01
    python compute/recurring_tasks.py --min-occurrences 3
"""

import argparse
from pathlib import Path

from llm_common import DAILY_INPUTS, MODEL, RECURRING_TASKS_PATH, extract_json_section, get_client

OUT_PATH = RECURRING_TASKS_PATH

_CLUSTER_TOOL: dict = {
    "name": "cluster_recurring_tasks",
    "description": "Cluster near-duplicate task/intention phrasings into recurring threads.",
    "input_schema": {
        "type": "object",
        "properties": {
            "recurring_tasks": {
                "type": "array",
                "items": {
                    "type": "object",
                    "properties": {
                        "canonical_name": {
                            "type": "string",
                            "description": "Short name for this recurring task/thread, e.g. 'Get ADHD medication sorted'",
                        },
                        "occurrences": {
                            "type": "integer",
                            "description": "Number of distinct days this task or a clear restatement of it appears",
                        },
                        "first_seen": {"type": "string", "description": "Earliest date (YYYY-MM-DD)"},
                        "last_seen": {"type": "string", "description": "Latest date (YYYY-MM-DD)"},
                        "sample_phrasings": {
                            "type": "array",
                            "items": {"type": "string"},
                            "description": "2-4 example phrasings as written, to show how it was expressed differently over time",
                        },
                        "status_note": {
                            "type": "string",
                            "description": "One sentence: does it look resolved, still open, or recurring without resolution?",
                        },
                    },
                    "required": [
                        "canonical_name",
                        "occurrences",
                        "first_seen",
                        "last_seen",
                        "sample_phrasings",
                        "status_note",
                    ],
                },
            },
        },
        "required": ["recurring_tasks"],
    },
}


def load_tasks_by_day(
    daily_dir: Path, start: str | None, end: str | None = None
) -> list[tuple[str, list[str]]]:
    results = []
    for path in sorted(daily_dir.glob("????-??-??.md")):
        if start and path.stem < start:
            continue
        if end and path.stem > end:
            continue
        text = path.read_text(encoding="utf-8")
        extract = extract_json_section(text)
        if extract is None:
            continue
        tasks = extract.get("tasks_and_intentions", [])
        if tasks:
            results.append((path.stem, tasks))
    return results


def build_prompt(tasks_by_day: list[tuple[str, list[str]]]) -> str:
    parts = []
    for date_str, tasks in tasks_by_day:
        for t in tasks:
            parts.append(f"{date_str}: {t}")
    tasks_block = "\n".join(parts)

    return (
        "Below is a list of tasks/intentions mentioned in one person's daily journal, "
        "one per line, prefixed with the date they were mentioned. The same underlying "
        "task is often restated differently on different days (e.g. 'get adderall', "
        "'follow up on ADHD meds with psychiatrist', 'call about Medicaid for meds' "
        "might all be the same thread).\n\n"
        "Cluster these into recurring threads — tasks/intentions that appear, in some "
        "form, on MULTIPLE distinct days. Do NOT include one-off tasks that only appear "
        "once. For each recurring thread, give a canonical name, how many distinct days "
        "it appears, the first and last date seen, a few sample phrasings showing how "
        "the wording changed over time, and a one-sentence status note (resolved, still "
        "open, or recurring without resolution).\n\n"
        "Order the results by `occurrences` descending — the most-repeated threads first.\n\n"
        "TASKS BY DAY:\n\n" + tasks_block
    )


def render_markdown(label_range: str, clusters: list[dict], min_occurrences: int) -> str:
    from datetime import date

    clusters = [c for c in clusters if c.get("occurrences", 0) >= min_occurrences]
    clusters.sort(key=lambda c: c.get("occurrences", 0), reverse=True)

    lines = [
        "# Recurring Tasks",
        f"Range: {label_range}",
        f"Generated: {date.today().isoformat()}",
        f"Minimum occurrences: {min_occurrences}",
        "",
        "Tasks/intentions that show up repeatedly across the journal, clustered by "
        "underlying theme. Higher occurrence counts = more weight — these are the "
        "threads quietly carrying across weeks even when they're not named as such "
        "day to day.",
        "",
    ]

    for c in clusters:
        lines.append(f"## {c['canonical_name']}")
        lines.append("")
        lines.append(f"- **Occurrences:** {c['occurrences']}")
        lines.append(f"- **First seen:** {c['first_seen']}")
        lines.append(f"- **Last seen:** {c['last_seen']}")
        lines.append(f"- **Status:** {c['status_note']}")
        lines.append("- **Sample phrasings:**")
        for s in c.get("sample_phrasings", []):
            lines.append(f"  - \"{s}\"")
        lines.append("")

    return "\n".join(lines)


def main() -> None:
    parser = argparse.ArgumentParser(
        description="Cluster recurring tasks/intentions across daily extracts."
    )
    parser.add_argument("--dir", type=Path, default=DAILY_INPUTS)
    parser.add_argument("--out", type=Path, default=OUT_PATH)
    parser.add_argument("--start", default=None,
                        help="Earliest date to include (YYYY-MM-DD)")
    parser.add_argument("--end", default=None,
                        help="Latest date to include (YYYY-MM-DD)")
    parser.add_argument("--min-occurrences", type=int, default=2,
                        help="Only show threads appearing on at least this many days (default 2)")
    args = parser.parse_args()

    client = get_client()

    tasks_by_day = load_tasks_by_day(args.dir, args.start, args.end)
    if not tasks_by_day:
        raise SystemExit("No daily extracts with tasks_and_intentions found.")

    total_tasks = sum(len(t) for _, t in tasks_by_day)
    label_range = f"{tasks_by_day[0][0]} to {tasks_by_day[-1][0]}"
    print(f"Loaded {total_tasks} task mentions across {len(tasks_by_day)} days ({label_range})")

    prompt = build_prompt(tasks_by_day)
    response = client.messages.create(
        model=MODEL,
        max_tokens=8096,
        tools=[_CLUSTER_TOOL],
        tool_choice={"type": "tool", "name": "cluster_recurring_tasks"},
        messages=[{"role": "user", "content": prompt}],
    )

    clusters = None
    for block in response.content:
        if block.type == "tool_use":
            clusters = block.input.get("recurring_tasks", [])
            break

    if clusters is None:
        raise SystemExit("No tool_use block in response.")

    print(f"Found {len(clusters)} recurring threads (>= {args.min_occurrences} occurrences shown)")

    md = render_markdown(label_range, clusters, args.min_occurrences)
    args.out.parent.mkdir(parents=True, exist_ok=True)
    args.out.write_text(md, encoding="utf-8")
    print(f"Wrote {args.out}")


if __name__ == "__main__":
    main()
