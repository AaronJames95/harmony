"""Shared helpers for the compute/ review and extraction scripts.

Common pieces: the Claude API client, the daily-extract JSON-fence parser,
and the shared vault paths used across extraction, reviews, and recurring
trackers.
"""

import json
import os
import re
from pathlib import Path

import anthropic

MODEL = "claude-sonnet-4-5"
EXTRACT_MARKER = "## 🤖 Daily Extract"

VAULT_ROOT = Path("/home/aharon/Documents/vault-alpha/3_Nutrients")
DAILY_INPUTS = VAULT_ROOT / "daily_inputs"
RECURRING_TASKS_PATH = VAULT_ROOT / "recurring_tasks.md"

_JSON_FENCE_RE = re.compile(r"```json\s*(.*?)\s*```", re.DOTALL)


def get_client() -> anthropic.Anthropic:
    """Build an Anthropic client from ANTHROPIC_API_KEY, or exit with an error."""
    api_key = os.environ.get("ANTHROPIC_API_KEY")
    if not api_key:
        raise SystemExit("ANTHROPIC_API_KEY environment variable not set")
    return anthropic.Anthropic(api_key=api_key)


def extract_json_section(text: str) -> dict | None:
    """Parse the ```json fenced block under the Daily Extract marker, if present."""
    idx = text.find(EXTRACT_MARKER)
    if idx == -1:
        return None
    section = text[idx:]
    m = _JSON_FENCE_RE.search(section)
    if not m:
        return None
    try:
        return json.loads(m.group(1))
    except json.JSONDecodeError:
        return None


def load_recurring_tasks(path: Path = RECURRING_TASKS_PATH) -> str | None:
    if path.exists():
        return path.read_text(encoding="utf-8")
    return None
