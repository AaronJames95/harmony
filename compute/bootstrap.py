"""Script 4 — Bootstrap analysis.

One-time (or periodic) analysis that samples extracted daily data across the
full date range to recommend what to systematically track.

Pass 1: Randomly sample up to 50 daily notes with a ## 🤖 Daily Extract section,
        spread evenly across the full date range.
Pass 2: Send all 50 extracts to Claude API with the bootstrap prompt.

Output is saved to the vault's bootstrap/ directory.
Resumable — will not overwrite an existing output file.

Usage:
    python compute/bootstrap.py
    python compute/bootstrap.py --dir /path/to/daily_inputs --out /path/to/bootstrap
    python compute/bootstrap.py --force   # overwrite existing output
"""

import argparse
import json
import random
from datetime import date
from pathlib import Path

from llm_common import DAILY_INPUTS, MODEL, extract_json_section, get_client

BOOTSTRAP_OUT = Path(
    "/home/aharon/Documents/vault-alpha/bootstrap"
)
OUTPUT_FILE = "bootstrap_recommendations.md"
SAMPLE_SIZE = 50


def collect_all_extracts(
    daily_dir: Path,
    start: str | None = None,
    end: str | None = None,
) -> list[tuple[str, dict]]:
    """Return [(date_str, extract_dict), ...] for all files with an extract, sorted by date."""
    results: list[tuple[str, dict]] = []
    for path in sorted(daily_dir.glob("????-??-??.md")):
        stem = path.stem
        if start and stem < start:
            continue
        if end and stem > end:
            continue
        text = path.read_text(encoding="utf-8")
        extract = extract_json_section(text)
        if extract is not None:
            results.append((stem, extract))
    return results


def spread_sample(all_extracts: list[tuple[str, dict]], n: int) -> list[tuple[str, dict]]:
    """Sample n items spread evenly across the full date range."""
    if len(all_extracts) <= n:
        return all_extracts

    # Divide into n buckets and sample one from each
    bucket_size = len(all_extracts) / n
    sampled: list[tuple[str, dict]] = []
    for i in range(n):
        start = int(i * bucket_size)
        end = int((i + 1) * bucket_size)
        bucket = all_extracts[start:end]
        if bucket:
            sampled.append(random.choice(bucket))
    return sampled


def build_bootstrap_prompt(sample: list[tuple[str, dict]]) -> str:
    n = len(sample)
    parts = []
    for date_str, data in sample:
        parts.append(
            "--- " + date_str + " ---\n"
            + json.dumps(data, indent=2, ensure_ascii=False)
        )
    extracts_block = "\n\n".join(parts)

    # Use string concatenation, not .format(), since journal content may contain curly braces
    prompt = (
        "You are analyzing "
        + str(n)
        + " days of structured daily data from one person's journal. "
        "Your job is to recommend what this specific person should systematically track going forward. "
        "Be balanced — surface generative and life-giving patterns equally alongside struggles. "
        "Structure your response in three sections:\n\n"
        "GENERATIVE TRACKING (creative output, consolations, connection, ideas)\n"
        "PATTERN TRACKING (recurring dynamics worth understanding)\n"
        "CHALLENGE TRACKING (struggles where data would help)\n\n"
        "Also identify:\n"
        "- The 3-5 dominant themes across the corpus\n"
        "- What correlates with high vs low energy days\n"
        "- The most interesting generative thread worth pulling on\n\n"
        "DATA (" + str(n) + " sampled days, spread across full date range):\n\n"
        + extracts_block
    )
    return prompt


def main() -> None:
    parser = argparse.ArgumentParser(
        description="Bootstrap analysis: sample extracted days and recommend what to track."
    )
    parser.add_argument("--dir", type=Path, default=DAILY_INPUTS)
    parser.add_argument("--out", type=Path, default=BOOTSTRAP_OUT)
    parser.add_argument("--start", default=None, help="Earliest date to include (YYYY-MM-DD)")
    parser.add_argument("--end", default=None, help="Latest date to include (YYYY-MM-DD)")
    parser.add_argument("--sample-size", type=int, default=SAMPLE_SIZE)
    parser.add_argument("--seed", type=int, default=None,
                        help="Random seed for reproducible sampling")
    parser.add_argument("--force", action="store_true",
                        help="Overwrite existing output file")
    args = parser.parse_args()

    client = get_client()

    out_path = args.out / OUTPUT_FILE
    if out_path.exists() and not args.force:
        raise SystemExit(
            f"Bootstrap output already exists: {out_path}\n"
            "Use --force to regenerate."
        )

    print("Collecting all extracted daily notes...")
    all_extracts = collect_all_extracts(args.dir, start=args.start, end=args.end)
    if not all_extracts:
        raise SystemExit("No extracted daily notes found. Run extract_daily.py first.")
    print(f"  Found {len(all_extracts)} extracted days "
          f"({all_extracts[0][0]} to {all_extracts[-1][0]})")

    if args.seed is not None:
        random.seed(args.seed)
    sample = spread_sample(all_extracts, args.sample_size)
    print(f"  Sampled {len(sample)} days spread across date range")

    print("Sending to Claude API...")
    prompt = build_bootstrap_prompt(sample)
    response = client.messages.create(
        model=MODEL,
        max_tokens=8096,
        messages=[{"role": "user", "content": prompt}],
    )

    analysis_text = response.content[0].text

    header = (
        f"# Bootstrap Recommendations\n"
        f"Generated: {date.today().isoformat()}\n"
        f"Sample: {len(sample)} days from {all_extracts[0][0]} to {all_extracts[-1][0]}\n"
        f"Total extracted days in corpus: {len(all_extracts)}\n\n"
    )

    args.out.mkdir(parents=True, exist_ok=True)
    out_path.write_text(header + analysis_text, encoding="utf-8")
    print(f"Saved: {out_path}")


if __name__ == "__main__":
    main()
