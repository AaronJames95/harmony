"""Script 2 — Daily extraction.

For any daily note file, send its contents to Claude API and append a
structured JSON extract as a ## 🤖 Daily Extract section.

Skips files that already have that section. Resumable.

Usage:
    # Extract a single file:
    python compute/extract_daily.py --file /path/to/2025-07-01.md

    # Extract all files in a directory:
    python compute/extract_daily.py --dir /path/to/daily_inputs

    # Run on the default vault directory:
    python compute/extract_daily.py
"""

import argparse
import json
import time
from pathlib import Path

import anthropic

from llm_common import DAILY_INPUTS, EXTRACT_MARKER, MODEL, get_client

DELAY_SECONDS = 0.5

SYSTEM_PROMPT = (
    "You are a personal data extraction assistant processing one person's daily note. "
    "Extract what is actually present — generative and difficult equally. "
    "This person is a creative-prophetic artist in NYC doing Ignatian spiritual practice, "
    "fighting hard battles, building toward something real. "
    "Extract with honesty and warmth."
)

_EXTRACT_TOOL: dict = {
    "name": "extract_daily_data",
    "description": "Extract structured data from a personal daily note.",
    "input_schema": {
        "type": "object",
        "properties": {
            "creative_spark_moment": {
                "type": "array",
                "items": {"type": "string"},
                "description": "Specific ideas, lyrical lines, breakthroughs that arrived with energy",
            },
            "verse_and_lyrical_lines": {
                "type": "array",
                "items": {"type": "string"},
                "description": "Phrases with rhythm or poetic quality, near-verbatim from the text",
            },
            "connection_quality": {
                "type": "array",
                "items": {
                    "type": "object",
                    "properties": {
                        "person": {"type": "string"},
                        "rating": {"type": "integer", "minimum": 1, "maximum": 10},
                    },
                    "required": ["person", "rating"],
                },
                "description": "Moments of genuine mutuality, with person name and 1-10 rating",
            },
            "spiritual_consolation_source": {
                "type": "string",
                "description": "What specifically brought peace, joy, or sense of God. Empty string if nothing present.",
            },
            "embodiment_practice": {
                "type": "string",
                "description": "Movement/dance/singing and the emotional shift it caused. Empty string if nothing present.",
            },
            "gratitude_items": {
                "type": "array",
                "items": {"type": "string"},
                "description": "From Gratitude section directly",
            },
            "led_by_love_moments": {
                "type": "array",
                "items": {"type": "string"},
                "description": "From Led by Love section directly",
            },
            "spiritual_movement": {
                "type": "string",
                "description": "consolation/desolation/mixed/unclear + bad spirit/good spirit/neutral",
            },
            "weed_use_context": {
                "type": "string",
                "description": "yes/no + what preceded + what followed. Empty string if not present.",
            },
            "morning_routine_completed": {
                "type": "array",
                "items": {"type": "string"},
                "description": "Which practices happened (meditation, examen, morning pages, etc.)",
            },
            "comparison_trigger": {
                "type": "array",
                "items": {"type": "string"},
                "description": "Who, and what story it triggered",
            },
            "struggles_and_fears": {
                "type": "array",
                "items": {"type": "string"},
                "description": "What was hard, named honestly",
            },
            "desolation_source": {
                "type": "string",
                "description": "bad spirit/good spirit/neutral + one sentence evidence. Empty string if not present.",
            },
            "work_paralysis": {
                "type": "string",
                "description": "yes/no + what the block was. Empty string if not present.",
            },
            "financial_anxiety": {
                "type": "string",
                "description": "1-10 rating + concrete situation vs catastrophizing. Empty string if not present.",
            },
            "tasks_and_intentions": {
                "type": "array",
                "items": {"type": "string"},
                "description": "Everything actionable mentioned",
            },
            "one_thing": {
                "type": "string",
                "description": "From ONE THING section if filled in. Empty string if not present.",
            },
            "energy_level": {
                "type": "string",
                "enum": ["high", "medium", "low", "mixed"],
                "description": "Overall energy level for the day",
            },
            "summary": {
                "type": "string",
                "description": "60-80 words capturing the whole day, valley and mountaintop both",
            },
        },
        "required": [
            "creative_spark_moment",
            "verse_and_lyrical_lines",
            "connection_quality",
            "spiritual_consolation_source",
            "embodiment_practice",
            "gratitude_items",
            "led_by_love_moments",
            "spiritual_movement",
            "weed_use_context",
            "morning_routine_completed",
            "comparison_trigger",
            "struggles_and_fears",
            "desolation_source",
            "work_paralysis",
            "financial_anxiety",
            "tasks_and_intentions",
            "one_thing",
            "energy_level",
            "summary",
        ],
    },
}


def already_extracted(path: Path) -> bool:
    try:
        return EXTRACT_MARKER in path.read_text(encoding="utf-8")
    except OSError:
        return False


def extract_one(path: Path, client: anthropic.Anthropic) -> None:
    if already_extracted(path):
        print(f"  skip  {path.name}")
        return

    content = path.read_text(encoding="utf-8")

    # Build prompt without .format() to avoid issues with curly braces in journal text
    user_message = (
        "Please extract structured data from this daily note.\n\n"
        "FILE: " + path.name + "\n\n"
        + content
    )

    response = client.messages.create(
        model=MODEL,
        max_tokens=4096,
        system=SYSTEM_PROMPT,
        tools=[_EXTRACT_TOOL],
        tool_choice={"type": "tool", "name": "extract_daily_data"},
        messages=[{"role": "user", "content": user_message}],
    )

    extract_data: dict | None = None
    for block in response.content:
        if block.type == "tool_use":
            extract_data = block.input
            break

    if extract_data is None:
        print(f"  FAIL  {path.name}: no tool_use block in response")
        return

    json_block = "```json\n" + json.dumps(extract_data, indent=2, ensure_ascii=False) + "\n```"
    section = "\n\n" + EXTRACT_MARKER + "\n\n" + json_block + "\n"

    with path.open("a", encoding="utf-8") as f:
        f.write(section)

    print(f"  ok    {path.name}")


def main() -> None:
    parser = argparse.ArgumentParser(
        description="Extract structured data from daily note files via Claude API."
    )
    group = parser.add_mutually_exclusive_group()
    group.add_argument("--file", type=Path, help="Extract a single file")
    group.add_argument("--dir", type=Path, default=DAILY_INPUTS,
                       help="Extract all .md files in a directory")
    args = parser.parse_args()

    client = get_client()

    if args.file:
        files = [args.file]
    else:
        target_dir = args.dir
        files = sorted(target_dir.glob("????-??-??.md"))
        if not files:
            raise SystemExit(f"No YYYY-MM-DD.md files found in {target_dir}")
        print(f"Found {len(files)} daily note files in {target_dir}")

    for i, path in enumerate(files):
        extract_one(path, client)
        if i < len(files) - 1:
            time.sleep(DELAY_SECONDS)

    print("Done.")


if __name__ == "__main__":
    main()
