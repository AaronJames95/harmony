"""Integration tests for Stage 0a: compute/combine.py.

Runs the script against samples/legacy and samples/new, then asserts the
validation cases from samples/README.md and shared/raw-day-format.md.
"""

import os
import re
import subprocess
import sys
import tempfile
from pathlib import Path

import pytest

REPO_ROOT = Path(__file__).parent.parent
SCRIPT = REPO_ROOT / "compute" / "combine.py"
LEGACY_INPUTS = REPO_ROOT / "samples" / "legacy"
NEW_INPUTS = REPO_ROOT / "samples" / "new"


# ---------------------------------------------------------------------------
# Frontmatter parser (no PyYAML dep)
# ---------------------------------------------------------------------------

def _parse_frontmatter(text: str) -> dict:
    """Extract YAML frontmatter into a flat dict.

    Handles scalar values and one level of indented block (sources_present).
    """
    m = re.match(r"^---\n(.*?)\n---\n", text, re.DOTALL)
    if not m:
        raise ValueError("No YAML frontmatter found")
    fm_text = m.group(1)

    result: dict = {}
    current_block_key: str | None = None
    current_block: dict = {}

    for line in fm_text.splitlines():
        # Indented sub-key (sources_present block)
        if line.startswith("  "):
            sub_m = re.match(r"  (\w+): (true|false)", line)
            if sub_m and current_block_key:
                current_block[sub_m.group(1)] = sub_m.group(2) == "true"
            continue

        # Flush previous block
        if current_block_key is not None:
            result[current_block_key] = current_block
            current_block_key = None
            current_block = {}

        # Top-level key: value
        kv = re.match(r"^(\w+): (.+)$", line)
        if not kv:
            # Could be "sources_present:" with no inline value
            block_start = re.match(r"^(\w+):\s*$", line)
            if block_start:
                current_block_key = block_start.group(1)
            continue

        key, val = kv.group(1), kv.group(2)
        if val == "true":
            result[key] = True
        elif val == "false":
            result[key] = False
        else:
            try:
                result[key] = float(val)
            except ValueError:
                result[key] = val

    if current_block_key is not None:
        result[current_block_key] = current_block

    return result


def _body(text: str) -> str:
    """Return everything after the closing --- of the frontmatter."""
    m = re.match(r"^---\n.*?\n---\n\n?", text, re.DOTALL)
    if not m:
        raise ValueError("No frontmatter delimiter found")
    return text[m.end():]


def _run(inputs: Path, fmt: str, out: Path) -> subprocess.CompletedProcess:
    return subprocess.run(
        [sys.executable, str(SCRIPT), "--inputs", str(inputs), "--format", fmt, "--out", str(out)],
        capture_output=True,
        text=True,
        cwd=str(REPO_ROOT),
    )


# ---------------------------------------------------------------------------
# Legacy batch
# ---------------------------------------------------------------------------

@pytest.fixture(scope="module")
def legacy_out(tmp_path_factory):
    d = tmp_path_factory.mktemp("legacy_out")
    result = _run(LEGACY_INPUTS, "legacy", d)
    assert result.returncode == 0, result.stderr
    return d


def test_legacy_file_count(legacy_out):
    files = sorted(legacy_out.glob("*.md"))
    assert len(files) == 5, f"Expected 5 files, got: {[f.name for f in files]}"


def test_legacy_0314_both_sources(legacy_out):
    text = (legacy_out / "2026-03-14.md").read_text(encoding="utf-8")
    fm = _parse_frontmatter(text)
    assert fm["source_format"] == "legacy"
    assert fm["sources_present"]["morning_pages"] is True
    assert fm["sources_present"]["examen"] is True
    assert fm["input_completion_score"] == 1.0
    body = _body(text)
    assert "ok here we go again" in body
    assert "contract got extended" in body
    assert "## Morning Pages" in body
    assert "## Examen" in body


def test_legacy_0315_both_sources(legacy_out):
    text = (legacy_out / "2026-03-15.md").read_text(encoding="utf-8")
    fm = _parse_frontmatter(text)
    assert fm["source_format"] == "legacy"
    assert fm["sources_present"]["morning_pages"] is True
    assert fm["sources_present"]["examen"] is True
    assert fm["input_completion_score"] == 1.0


def test_legacy_0316_absence(legacy_out):
    text = (legacy_out / "2026-03-16.md").read_text(encoding="utf-8")
    fm = _parse_frontmatter(text)
    assert fm["source_format"] == "none"
    assert fm["sources_present"]["morning_pages"] is False
    assert fm["sources_present"]["examen"] is False
    assert fm["input_completion_score"] == 0.0
    assert _body(text).strip() == "inputs: none"


def test_legacy_0317_morning_pages_only(legacy_out):
    text = (legacy_out / "2026-03-17.md").read_text(encoding="utf-8")
    fm = _parse_frontmatter(text)
    assert fm["source_format"] == "legacy"
    assert fm["sources_present"]["morning_pages"] is True
    assert fm["sources_present"]["examen"] is False
    assert fm["input_completion_score"] == 0.5
    body = _body(text)
    assert "rough one" in body
    assert "## Examen" not in body


def test_legacy_0318_examen_only(legacy_out):
    text = (legacy_out / "2026-03-18.md").read_text(encoding="utf-8")
    fm = _parse_frontmatter(text)
    assert fm["source_format"] == "legacy"
    assert fm["sources_present"]["morning_pages"] is False
    assert fm["sources_present"]["examen"] is True
    assert fm["input_completion_score"] == 0.5


# ---------------------------------------------------------------------------
# New-template batch
# ---------------------------------------------------------------------------

@pytest.fixture(scope="module")
def new_out(tmp_path_factory):
    d = tmp_path_factory.mktemp("new_out")
    result = _run(NEW_INPUTS, "new_template", d)
    assert result.returncode == 0, result.stderr
    return d


def test_new_file_count(new_out):
    files = sorted(new_out.glob("*.md"))
    assert len(files) == 3, f"Expected 3 files, got: {[f.name for f in files]}"


def test_new_0528_full(new_out):
    text = (new_out / "2026-05-28.md").read_text(encoding="utf-8")
    fm = _parse_frontmatter(text)
    assert fm["source_format"] == "new_template"
    sp = fm["sources_present"]
    assert sp["meditation"] is True
    assert sp["examen"] is True
    assert sp["morning_pages"] is True
    assert sp["video_transcript"] is True
    assert fm["input_completion_score"] == 1.0


def test_new_0529_distress_not_absence(new_out):
    """2026-05-29: all practices skipped but it is NOT an absence day."""
    text = (new_out / "2026-05-29.md").read_text(encoding="utf-8")
    fm = _parse_frontmatter(text)
    # Must be new_template, NOT none — there is a real file with real content
    assert fm["source_format"] == "new_template"
    sp = fm["sources_present"]
    assert sp["meditation"] is False
    assert sp["examen"] is False
    assert sp["morning_pages"] is False
    assert sp["video_transcript"] is False
    assert fm["input_completion_score"] == 0.0
    # Body must preserve the full file content
    body = _body(text)
    assert "couldn't find any this morning" in body
    assert "## Daily Note" in body


def test_new_0530_full_recovery(new_out):
    text = (new_out / "2026-05-30.md").read_text(encoding="utf-8")
    fm = _parse_frontmatter(text)
    assert fm["source_format"] == "new_template"
    sp = fm["sources_present"]
    assert sp["meditation"] is True
    assert sp["examen"] is True
    assert sp["morning_pages"] is True
    assert sp["video_transcript"] is True
    assert fm["input_completion_score"] == 1.0


# ---------------------------------------------------------------------------
# Cross-cutting: UTF-8 and resumable
# ---------------------------------------------------------------------------

def test_all_outputs_valid_utf8(legacy_out, new_out):
    for path in list(legacy_out.glob("*.md")) + list(new_out.glob("*.md")):
        path.read_text(encoding="utf-8")  # raises on bad bytes


def test_resumable(tmp_path):
    """Second run into the same dir must not overwrite existing files."""
    result1 = _run(LEGACY_INPUTS, "legacy", tmp_path)
    assert result1.returncode == 0, result1.stderr

    mtimes_before = {p.name: p.stat().st_mtime for p in tmp_path.glob("*.md")}

    result2 = _run(LEGACY_INPUTS, "legacy", tmp_path)
    assert result2.returncode == 0, result2.stderr

    mtimes_after = {p.name: p.stat().st_mtime for p in tmp_path.glob("*.md")}
    assert mtimes_before == mtimes_after, "Second run rewrote files that should be skipped"


# ---------------------------------------------------------------------------
# Dec→Jan year-rollover (multi-year corpus bug)
# ---------------------------------------------------------------------------

def _make_dec_jan_inputs(tmp_path_factory) -> Path:
    inputs = tmp_path_factory.mktemp("dec_jan_inputs")

    (inputs / "Morning Pages.md").write_text(
        "- 12/29: end of year, feeling tired and grateful\n"
        "- 12/31: last night of the year, quiet\n"
        "- 1/2. fresh start, lighter somehow\n",
        encoding="utf-8",
    )

    ex_dir_2025 = inputs / "examen" / "2025"
    ex_dir_2025.mkdir(parents=True)
    (ex_dir_2025 / "EX_12_2025.md").write_text(
        "- 12/29: grateful for a hard year\n"
        "- 12/31: closing out with honesty\n",
        encoding="utf-8",
    )

    ex_dir_2026 = inputs / "examen" / "2026"
    ex_dir_2026.mkdir(parents=True)
    (ex_dir_2026 / "EX_01_2026.md").write_text(
        "- 1/2: first examen of the new year\n",
        encoding="utf-8",
    )

    return inputs


@pytest.fixture(scope="module")
def dec_jan_out(tmp_path_factory):
    inputs = _make_dec_jan_inputs(tmp_path_factory)
    out = tmp_path_factory.mktemp("dec_jan_out")
    result = _run(inputs, "legacy", out)
    assert result.returncode == 0, result.stderr
    return out


def test_dec_jan_december_dates(dec_jan_out):
    for date_str in ("2025-12-29", "2025-12-31"):
        p = dec_jan_out / f"{date_str}.md"
        assert p.exists(), f"Expected {date_str}.md"
        fm = _parse_frontmatter(p.read_text(encoding="utf-8"))
        assert fm["date"] == date_str
        assert fm["source_format"] == "legacy"


def test_dec_jan_january_date(dec_jan_out):
    p = dec_jan_out / "2026-01-02.md"
    assert p.exists(), "Expected 2026-01-02.md after year rollover"
    fm = _parse_frontmatter(p.read_text(encoding="utf-8"))
    assert fm["date"] == "2026-01-02"
    assert fm["source_format"] == "legacy"
    assert fm["input_completion_score"] == 1.0


def test_dec_jan_no_wrong_year_files(dec_jan_out):
    # The January entry must not be mis-dated to 2025
    assert not (dec_jan_out / "2025-01-02.md").exists()
    # The December entries must not be mis-dated to 2026
    assert not (dec_jan_out / "2026-12-29.md").exists()
    assert not (dec_jan_out / "2026-12-31.md").exists()


def test_dec_jan_rollover_logged(tmp_path_factory):
    """Rollover and per-entry assignments must appear in stderr."""
    inputs = _make_dec_jan_inputs(tmp_path_factory)
    out = tmp_path_factory.mktemp("dec_jan_log_out")
    result = _run(inputs, "legacy", out)
    assert result.returncode == 0, result.stderr
    assert "rollover" in result.stderr
    assert "2025-12-29" in result.stderr
    assert "2026-01-02" in result.stderr
