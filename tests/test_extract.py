"""Tests for Stage 0c: compute/extract.py.

Unit tests run with no I/O and no Ollama. Integration tests mock requests.post
so they also need no running Ollama instance. Fixtures come from samples/rawdays/.
"""

import json
import sys
from pathlib import Path
from unittest.mock import MagicMock, patch

import pytest

REPO_ROOT = Path(__file__).parent.parent
sys.path.insert(0, str(REPO_ROOT))

from compute.extract import (
    _absence_extract,
    _assemble_extract,
    _build_prompt,
    _build_retry_prompt,
    _extract_one,
    _is_section_start,
    _is_successful_extract,
    _parse_raw_day,
    _strip_video_section,
    _validate,
)

RAWDAYS = REPO_ROOT / "samples" / "rawdays"


# ---------------------------------------------------------------------------
# Helpers
# ---------------------------------------------------------------------------

def _good_model_output() -> dict:
    return {
        "emotional_climate": "A steady, productive day with small bright spots.",
        "energy_level": "medium",
        "spiritual_movement": "consolation",
        "tasks": ["ask Marcus for referral"],
        "verses": [],
        "creative_ideas": ["finish the bridge section"],
        "gratitude_and_consolations": ["coffee with Marcus"],
        "people_mentioned": [{"name": "Marcus", "context": "work"}],
        "questions_alive": ["Is staying in the city faith or stubbornness?"],
        "struggles_or_fears": [],
        "notable_phrases": ["do the next thing"],
        "summary": (
            "A grounded Wednesday where the morning routine paid off. "
            "Work went smoothly, and a conversation with Marcus brought both "
            "warmth and a pang of comparison that passed. Creative ambition "
            "stayed alive — the bridge section waited at the end of the day. "
            "Questions about the city and the next contract lingered, but the "
            "posture was hopeful and action-oriented."
        ),
    }


def _mock_response(data: dict) -> MagicMock:
    mock = MagicMock()
    mock.json.return_value = {"response": json.dumps(data)}
    mock.raise_for_status.return_value = None
    return mock


# ---------------------------------------------------------------------------
# Unit: _parse_raw_day
# ---------------------------------------------------------------------------

def test_parse_frontmatter_legacy():
    fm = _parse_raw_day(RAWDAYS / "2026-03-14.md")
    assert fm["date"] == "2026-03-14"
    assert fm["source_format"] == "legacy"
    assert fm["input_completion_score"] == 1.0
    assert "Morning Pages" in fm["body"]
    assert "Examen" in fm["body"]


def test_parse_frontmatter_absence():
    fm = _parse_raw_day(RAWDAYS / "2026-03-16.md")
    assert fm["date"] == "2026-03-16"
    assert fm["source_format"] == "none"
    assert fm["input_completion_score"] == 0.0
    assert "inputs: none" in fm["body"]


# ---------------------------------------------------------------------------
# Unit: _strip_video_section
# ---------------------------------------------------------------------------

def test_strip_video_removes_block():
    fm = _parse_raw_day(RAWDAYS / "2026-05-28.md")
    stripped = _strip_video_section(fm["body"])
    assert "📹" not in stripped
    # ✅ ONE THING section (immediately before video) must be fully intact
    assert "✅ ONE THING" in stripped
    assert "finish the bridge" in stripped


def test_strip_video_noop_legacy():
    fm = _parse_raw_day(RAWDAYS / "2026-03-14.md")
    body = fm["body"]
    assert _strip_video_section(body) == body


def test_strip_video_removes_only_video_block():
    body = "😌 Meditation\n\n* good\n📹 Daily Video Transcript\n\n* transcript text\n"
    stripped = _strip_video_section(body)
    assert "Meditation" in stripped
    assert "good" in stripped
    assert "📹" not in stripped
    assert "transcript text" not in stripped


# ---------------------------------------------------------------------------
# Unit: _is_section_start
# ---------------------------------------------------------------------------

def test_is_section_start_heading():
    assert _is_section_start("## Daily Note")
    assert _is_section_start("## Morning Pages")


def test_is_section_start_emoji():
    assert _is_section_start("😌 Meditation")
    assert _is_section_start("✅ ONE THING")
    assert _is_section_start("📹 Daily Video Transcript")


def test_is_section_start_plain():
    assert not _is_section_start("* some text")
    assert not _is_section_start("plain line")
    assert not _is_section_start("")


# ---------------------------------------------------------------------------
# Unit: _validate
# ---------------------------------------------------------------------------

def test_validate_ok():
    _validate(_good_model_output())  # must not raise


def test_validate_bad_energy_level():
    data = _good_model_output()
    data["energy_level"] = "very_high"
    with pytest.raises(ValueError, match="energy_level"):
        _validate(data)


def test_validate_bad_spiritual_movement():
    data = _good_model_output()
    data["spiritual_movement"] = "good"
    with pytest.raises(ValueError, match="spiritual_movement"):
        _validate(data)


def test_validate_missing_field():
    data = _good_model_output()
    del data["summary"]
    with pytest.raises(ValueError, match="summary"):
        _validate(data)


def test_validate_bad_person_context():
    data = _good_model_output()
    data["people_mentioned"] = [{"name": "Sam", "context": "colleague"}]
    with pytest.raises(ValueError, match="context"):
        _validate(data)


def test_validate_list_field_not_list():
    data = _good_model_output()
    data["tasks"] = "ask Marcus"
    with pytest.raises(ValueError, match="tasks"):
        _validate(data)


def test_validate_absence_passes():
    fm = {"date": "2026-03-16", "source_format": "none", "input_completion_score": 0.0}
    absence = _absence_extract(fm)
    _validate(absence)  # must not raise — absence shape is valid


# ---------------------------------------------------------------------------
# Unit: _is_successful_extract
# ---------------------------------------------------------------------------

def test_is_successful_extract_missing(tmp_path):
    assert not _is_successful_extract(tmp_path / "2026-01-01.json")


def test_is_successful_extract_stub(tmp_path):
    p = tmp_path / "2026-01-01.json"
    p.write_text(json.dumps({"extraction_failed": True, "error": "oops"}), encoding="utf-8")
    assert not _is_successful_extract(p)


def test_is_successful_extract_good(tmp_path):
    p = tmp_path / "2026-01-01.json"
    p.write_text(json.dumps({"date": "2026-01-01", "summary": "ok"}), encoding="utf-8")
    assert _is_successful_extract(p)


# ---------------------------------------------------------------------------
# Integration: _extract_one (mocked Ollama)
# ---------------------------------------------------------------------------

@patch("compute.extract.requests.post")
def test_extract_legacy_day(mock_post, tmp_path):
    mock_post.return_value = _mock_response(_good_model_output())
    _extract_one(RAWDAYS / "2026-03-14.md", tmp_path, "qwen3:14b", "http://localhost:11434")
    out = json.loads((tmp_path / "2026-03-14.json").read_text(encoding="utf-8"))
    # carry-through from frontmatter
    assert out["date"] == "2026-03-14"
    assert out["source_format"] == "legacy"
    assert out["input_completion_score"] == 1.0
    # required schema fields present
    for key in ["emotional_climate", "energy_level", "spiritual_movement", "summary"]:
        assert key in out


@patch("compute.extract.requests.post")
def test_extract_new_template_day(mock_post, tmp_path):
    mock_post.return_value = _mock_response(_good_model_output())
    _extract_one(RAWDAYS / "2026-05-28.md", tmp_path, "qwen3:14b", "http://localhost:11434")
    out = json.loads((tmp_path / "2026-05-28.json").read_text(encoding="utf-8"))
    assert out["date"] == "2026-05-28"
    assert out["source_format"] == "new_template"
    assert out["input_completion_score"] == 1.0
    assert "extraction_failed" not in out


@patch("compute.extract.requests.post")
def test_extract_distress_day(mock_post, tmp_path):
    # 2026-05-29: score 0.0, source_format=new_template — NOT an absence day
    mock_post.return_value = _mock_response(_good_model_output())
    _extract_one(RAWDAYS / "2026-05-29.md", tmp_path, "qwen3:14b", "http://localhost:11434")
    # model must have been called (not skipped as absence)
    mock_post.assert_called_once()
    out = json.loads((tmp_path / "2026-05-29.json").read_text(encoding="utf-8"))
    assert out["source_format"] == "new_template"
    assert out["input_completion_score"] == 0.0
    assert "extraction_failed" not in out


def test_extract_absence_no_model_call(tmp_path):
    with patch("compute.extract.requests.post") as mock_post:
        _extract_one(RAWDAYS / "2026-03-16.md", tmp_path, "qwen3:14b", "http://localhost:11434")
        mock_post.assert_not_called()
    out = json.loads((tmp_path / "2026-03-16.json").read_text(encoding="utf-8"))
    assert out["source_format"] == "none"
    assert "extraction_failed" not in out
    _validate(out)  # absence extract must pass validation


@patch("compute.extract.requests.post")
def test_resumable_skips_good_extract(mock_post, tmp_path):
    mock_post.return_value = _mock_response(_good_model_output())
    # first run — writes the extract
    _extract_one(RAWDAYS / "2026-03-14.md", tmp_path, "qwen3:14b", "http://localhost:11434")
    assert mock_post.call_count == 1
    # second run — extract already exists, must skip
    mock_post.reset_mock()
    _extract_one(RAWDAYS / "2026-03-14.md", tmp_path, "qwen3:14b", "http://localhost:11434")
    mock_post.assert_not_called()


@patch("compute.extract.requests.post")
def test_resumable_retries_stub(mock_post, tmp_path):
    # pre-write a stub
    stub_path = tmp_path / "2026-03-14.json"
    stub_path.write_text(
        json.dumps({"extraction_failed": True, "error": "prev error"}), encoding="utf-8"
    )
    mock_post.return_value = _mock_response(_good_model_output())
    _extract_one(RAWDAYS / "2026-03-14.md", tmp_path, "qwen3:14b", "http://localhost:11434")
    # model must have been called to re-attempt
    mock_post.assert_called_once()
    out = json.loads(stub_path.read_text(encoding="utf-8"))
    assert "extraction_failed" not in out


@patch("compute.extract.requests.post")
def test_retry_on_validation_failure(mock_post, tmp_path):
    bad = _good_model_output()
    bad["energy_level"] = "INVALID"
    good = _good_model_output()
    mock_post.side_effect = [_mock_response(bad), _mock_response(good)]

    _extract_one(RAWDAYS / "2026-03-14.md", tmp_path, "qwen3:14b", "http://localhost:11434")
    assert mock_post.call_count == 2
    out = json.loads((tmp_path / "2026-03-14.json").read_text(encoding="utf-8"))
    assert "extraction_failed" not in out
    assert out["energy_level"] in {"high", "medium", "low", "mixed", "unclear"}


@patch("compute.extract.requests.post")
def test_fallback_to_stub(mock_post, tmp_path):
    # Both calls return invalid JSON; json-repair also can't help
    mock = MagicMock()
    mock.json.return_value = {"response": "not json at all ~~~"}
    mock.raise_for_status.return_value = None
    mock_post.return_value = mock

    _extract_one(RAWDAYS / "2026-03-14.md", tmp_path, "qwen3:14b", "http://localhost:11434")
    assert mock_post.call_count == 2  # attempt 1 + retry
    out = json.loads((tmp_path / "2026-03-14.json").read_text(encoding="utf-8"))
    assert out["extraction_failed"] is True
    assert "error" in out
    assert out["date"] == "2026-03-14"


@patch("compute.extract.requests.post")
def test_carry_through_not_from_model(mock_post, tmp_path):
    # model output intentionally omits date/source_format/input_completion_score
    model_out = _good_model_output()
    # (they're not in the schema — model never produces them)
    mock_post.return_value = _mock_response(model_out)
    _extract_one(RAWDAYS / "2026-03-14.md", tmp_path, "qwen3:14b", "http://localhost:11434")
    out = json.loads((tmp_path / "2026-03-14.json").read_text(encoding="utf-8"))
    assert out["date"] == "2026-03-14"
    assert out["source_format"] == "legacy"
    assert out["input_completion_score"] == 1.0


@patch("compute.extract.requests.post")
def test_video_not_in_prompt(mock_post, tmp_path):
    mock_post.return_value = _mock_response(_good_model_output())
    _extract_one(RAWDAYS / "2026-05-28.md", tmp_path, "qwen3:14b", "http://localhost:11434")
    # Inspect the prompt that was sent
    call_kwargs = mock_post.call_args
    prompt_sent = call_kwargs[1]["json"]["prompt"]  # keyword arg
    assert "📹" not in prompt_sent
    # The morning pages section (before the video) must still be present
    assert "Morning Pages" in prompt_sent or "morning" in prompt_sent.lower()
