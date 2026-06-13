"""Recurring desolations tracker.

Scans every daily extract's `struggles_and_fears`, `desolation_source`, and
`comparison_trigger` fields and clusters near-duplicate phrasings into recurring
desolation threads — the negative thoughts, fears, and triggers that keep coming
back, with how often and over what span each one appears.

Standalone / ad hoc, mirrors compute/recurring_tasks.py. Not wired into the
weekly/monthly/quarterly pipeline by default.

Usage:
    python compute/recurring_desolations.py
    python compute/recurring_desolations.py --start 2026-05-01 --end 2026-05-31 \\
        --out /path/to/recurring_desolations_2026-05.md
"""

import argparse
from pathlib import Path

from llm_common import DAILY_INPUTS, MODEL, extract_json_section, get_client

OUT_PATH = Path(
    "/home/aharon/Documents/vault-alpha/3_Nutrients/recurring_desolations.md"
)

_CLUSTER_TOOL: dict = {
    "name": "cluster_recurring_desolations",
    "description": "Cluster near-duplicate negative-thought/desolation phrasings into recurring threads.",
    "input_schema": {
        "type": "object",
        "properties": {
            "recurring_desolations": {
                "type": "array",
                "items": {
                    "type": "object",
                    "properties": {
                        "canonical_name": {
                            "type": "string",
                            "description": "Short name for this recurring desolation/negative-thought thread, e.g. 'Comparison to Anastasia'",
                        },
                        "occurrences": {
                            "type": "integer",
                            "description": "Number of distinct days this thought/trigger or a clear restatement of it appears",
                        },
                        "first_seen": {"type": "string", "description": "Earliest date (YYYY-MM-DD)"},
                        "last_seen": {"type": "string", "description": "Latest date (YYYY-MM-DD)"},
                        "sample_phrasings": {
                            "type": "array",
                            "items": {"type": "string"},
                            "description": "2-4 example phrasings as written, to show how it was expressed differently over time",
                        },
                        "pattern_note": {
                            "type": "string",
                            "description": "One sentence: is this intensifying, fading, steady, or tied to a specific recurring trigger/situation?",
                        },
                    },
                    "required": [
                        "canonical_name",
                        "occurrences",
                        "first_seen",
                        "last_seen",
                        "sample_phrasings",
                        "pattern_note",
                    ],
                },
            },
        },
        "required": ["recurring_desolations"],
    },
}


def load_desolations_by_day(daily_dir: Path, start: str | None, end: str | None) -> list[tuple[str, list[str]]]:
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

        items: list[str] = []
        items.extend(extract.get("struggles_and_fears", []))
        items.extend(extract.get("comparison_trigger", []))
        desolation_source = extract.get("desolation_source", "")
        if desolation_source:
            items.append(desolation_source)

        if items:
            results.append((path.stem, items))
    return results


def build_prompt(items_by_day: list[tuple[str, list[str]]]) -> str:
    parts = []
    for date_str, items in items_by_day:
        for t in items:
            parts.append(f"{date_str}: {t}")
    items_block = "\n".join(parts)

    return (
        "Below is a list of struggles, fears, comparison triggers, and desolation "
        "notes from one person's daily journal, one per line, prefixed with the date "
        "they were mentioned. The same underlying negative thought or trigger is often "
        "restated differently on different days (e.g. 'jealous of Ana's album', "
        "'rage at Ana's Instagram post', 'comparison spiral about Ana' might all be "
        "the same thread).\n\n"
        "Cluster these into recurring desolation threads — negative thoughts, fears, "
        "or triggers that appear, in some form, on MULTIPLE distinct days. Do NOT "
        "include one-off mentions that only appear once. For each recurring thread, "
        "give a canonical name, how many distinct days it appears, the first and last "
        "date seen, a few sample phrasings showing how the wording changed over time, "
        "and a one-sentence pattern note (intensifying, fading, steady, or tied to a "
        "specific recurring trigger/situation).\n\n"
        "Order the results by `occurrences` descending — the most-repeated threads first.\n\n"
        "ITEMS BY DAY:\n\n" + items_block
    )


def render_markdown(label_range: str, clusters: list[dict], min_occurrences: int) -> str:
    from datetime import date

    clusters = [c for c in clusters if c.get("occurrences", 0) >= min_occurrences]
    clusters.sort(key=lambda c: c.get("occurrences", 0), reverse=True)

    lines = [
        "# Recurring Desolations",
        f"Range: {label_range}",
        f"Generated: {date.today().isoformat()}",
        f"Minimum occurrences: {min_occurrences}",
        "",
        "Negative thoughts, fears, and desolation triggers that show up repeatedly "
        "across the journal, clustered by underlying theme. Higher occurrence counts "
        "= more weight — these are the threads quietly carrying across weeks even "
        "when they're not named as such day to day.",
        "",
    ]

    for c in clusters:
        lines.append(f"## {c['canonical_name']}")
        lines.append("")
        lines.append(f"- **Occurrences:** {c['occurrences']}")
        lines.append(f"- **First seen:** {c['first_seen']}")
        lines.append(f"- **Last seen:** {c['last_seen']}")
        lines.append(f"- **Pattern:** {c['pattern_note']}")
        lines.append("- **Sample phrasings:**")
        for s in c.get("sample_phrasings", []):
            lines.append(f"  - \"{s}\"")
        lines.append("")

    return "\n".join(lines)


def main() -> None:
    parser = argparse.ArgumentParser(
        description="Cluster recurring negative thoughts/desolations across daily extracts."
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

    items_by_day = load_desolations_by_day(args.dir, args.start, args.end)
    if not items_by_day:
        raise SystemExit("No daily extracts with struggles_and_fears/desolation data found.")

    total_items = sum(len(t) for _, t in items_by_day)
    label_range = f"{items_by_day[0][0]} to {items_by_day[-1][0]}"
    print(f"Loaded {total_items} desolation mentions across {len(items_by_day)} days ({label_range})")

    prompt = build_prompt(items_by_day)
    response = client.messages.create(
        model=MODEL,
        max_tokens=16000,
        tools=[_CLUSTER_TOOL],
        tool_choice={"type": "tool", "name": "cluster_recurring_desolations"},
        messages=[{"role": "user", "content": prompt}],
    )

    clusters = None
    for block in response.content:
        if block.type == "tool_use":
            clusters = block.input.get("recurring_desolations", [])
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
