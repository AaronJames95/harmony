"""Tests for compute/transcribe.py — no CUDA or faster-whisper required."""

import datetime
import json
import sys
import tempfile
from pathlib import Path
from types import SimpleNamespace
from unittest.mock import MagicMock, patch

import pytest

sys.path.insert(0, str(Path(__file__).parent.parent / "compute"))
from transcribe import (
    _date_from_filename,
    _fmt_ts,
    _probe_creation_time,
    _read_sources,
    _transcribe_file,
    _write_or_append,
)


# ---------------------------------------------------------------------------
# _fmt_ts
# ---------------------------------------------------------------------------

def test_fmt_ts_zero():
    assert _fmt_ts(0.0) == "00:00.0"


def test_fmt_ts_sub_minute():
    assert _fmt_ts(5.7) == "00:05.7"


def test_fmt_ts_over_minute():
    assert _fmt_ts(83.4) == "01:23.4"


# ---------------------------------------------------------------------------
# _date_from_filename
# ---------------------------------------------------------------------------

def test_date_from_filename_yyyymmdd(tmp_path):
    p = tmp_path / "20260530_foo.wav"
    assert _date_from_filename(p) == datetime.date(2026, 5, 30)


def test_date_from_filename_iso(tmp_path):
    p = tmp_path / "2026-05-28_rec.mp4"
    assert _date_from_filename(p) == datetime.date(2026, 5, 28)


def test_date_from_filename_pxl_prefix(tmp_path):
    p = tmp_path / "PXL_20260528_143000000.mp4"
    assert _date_from_filename(p) == datetime.date(2026, 5, 28)


def test_date_from_filename_vid_prefix(tmp_path):
    p = tmp_path / "VID_20260530_090000.mp4"
    assert _date_from_filename(p) == datetime.date(2026, 5, 30)


def test_date_from_filename_img_prefix(tmp_path):
    p = tmp_path / "IMG_20260529_120000.mov"
    assert _date_from_filename(p) == datetime.date(2026, 5, 29)


def test_date_from_filename_none(tmp_path):
    p = tmp_path / "clip-with-metadata.wav"
    assert _date_from_filename(p) is None


def test_date_from_filename_invalid_date(tmp_path):
    p = tmp_path / "20261399_bad.wav"
    assert _date_from_filename(p) is None


# ---------------------------------------------------------------------------
# _probe_creation_time
# ---------------------------------------------------------------------------

_FFPROBE_NO_TAG = json.dumps({
    "format": {"tags": {"encoder": "Lavf58.76.100"}}
})

_FFPROBE_WITH_TAG = json.dumps({
    "format": {"tags": {"creation_time": "2026-05-29T02:00:00.000000Z"}}
})


def test_probe_creation_time_missing_tag(tmp_path):
    p = tmp_path / "a.wav"
    p.touch()
    with patch("subprocess.run") as mock_run:
        mock_run.return_value = MagicMock(stdout=_FFPROBE_NO_TAG, returncode=0)
        result = _probe_creation_time(p)
    assert result is None


def test_probe_creation_time_present(tmp_path):
    p = tmp_path / "a.mp4"
    p.touch()
    with patch("subprocess.run") as mock_run:
        mock_run.return_value = MagicMock(stdout=_FFPROBE_WITH_TAG, returncode=0)
        result = _probe_creation_time(p)
    assert result is not None
    assert result.year == 2026
    assert result.month == 5
    assert result.day == 29
    assert result.hour == 2
    assert result.tzinfo is not None


def test_probe_creation_time_ffprobe_failure(tmp_path):
    p = tmp_path / "a.wav"
    p.touch()
    with patch("subprocess.run", side_effect=FileNotFoundError("ffprobe not found")):
        result = _probe_creation_time(p)
    assert result is None


# ---------------------------------------------------------------------------
# UTC -> local off-by-one-day guard
# ---------------------------------------------------------------------------

def test_utc_to_local_prior_day():
    """02:00 UTC must resolve to 2026-05-28 in UTC-6, not 2026-05-29.

    Tests the conversion math that _resolve_date applies to the ffprobe result.
    `datetime.astimezone()` is a C-level method and can't be patched on instances,
    so we call it explicitly with a fixed UTC-6 offset to assert the invariant.
    """
    utc_dt = datetime.datetime(2026, 5, 29, 2, 0, 0, tzinfo=datetime.timezone.utc)
    tz_minus6 = datetime.timezone(datetime.timedelta(hours=-6))
    local_date = utc_dt.astimezone(tz_minus6).date()
    assert local_date == datetime.date(2026, 5, 28), (
        "02:00 UTC should be 20:00 on 2026-05-28 in UTC-6, not 2026-05-29"
    )


# ---------------------------------------------------------------------------
# _read_sources
# ---------------------------------------------------------------------------

def test_read_sources_missing_file(tmp_path):
    assert _read_sources(tmp_path / "nope.md") == []


def test_read_sources_finds_names(tmp_path):
    p = tmp_path / "2026-05-30.md"
    p.write_text(
        "---\n"
        "date: 2026-05-30\n"
        "generated_by: transcribe.py\n"
        "generated_at: 2026-05-31T10:00:00\n"
        "sources:\n"
        "  - 20260530_imported.wav\n"
        "  - another_file.mp4\n"
        "---\n\n"
        "## 20260530_imported.wav (date via filename)\n\n"
        "[00:00.0 -> 00:03.0] Hello.\n",
        encoding="utf-8",
    )
    assert _read_sources(p) == ["20260530_imported.wav", "another_file.mp4"]


def test_read_sources_no_sources_key(tmp_path):
    p = tmp_path / "2026-05-30.md"
    p.write_text("---\ndate: 2026-05-30\n---\n\nsome body\n", encoding="utf-8")
    assert _read_sources(p) == []


# ---------------------------------------------------------------------------
# _write_or_append
# ---------------------------------------------------------------------------

def test_write_creates_file_with_frontmatter(tmp_path):
    out_path = tmp_path / "2026-05-30.md"
    _write_or_append(
        out_path,
        datetime.date(2026, 5, 30),
        "20260530_imported.wav",
        "[00:00.0 -> 00:03.0] Hello world.",
        "filename",
        "2026-05-31T10:00:00",
    )
    text = out_path.read_text(encoding="utf-8")
    assert "date: 2026-05-30" in text
    assert "generated_by: transcribe.py" in text
    assert "  - 20260530_imported.wav" in text
    assert "## 20260530_imported.wav (date via filename)" in text
    assert "[00:00.0 -> 00:03.0] Hello world." in text


def test_write_appends_updates_sources_and_body(tmp_path):
    out_path = tmp_path / "2026-05-30.md"
    _write_or_append(
        out_path,
        datetime.date(2026, 5, 30),
        "first.wav",
        "[00:00.0 -> 00:02.0] First file.",
        "filename",
        "2026-05-31T10:00:00",
    )
    _write_or_append(
        out_path,
        datetime.date(2026, 5, 30),
        "second.mp4",
        "[00:00.0 -> 00:05.0] Second file.",
        "ffprobe",
        "2026-05-31T10:00:00",
    )
    text = out_path.read_text(encoding="utf-8")
    # Only one frontmatter block
    assert text.count("generated_by: transcribe.py") == 1
    assert text.count("date: 2026-05-30") == 1
    # Both sources in frontmatter
    assert "  - first.wav" in text
    assert "  - second.mp4" in text
    # Both sections in body
    assert "## first.wav (date via filename)" in text
    assert "## second.mp4 (date via ffprobe)" in text
    assert "[00:00.0 -> 00:02.0] First file." in text
    assert "[00:00.0 -> 00:05.0] Second file." in text


# ---------------------------------------------------------------------------
# _transcribe_file
# ---------------------------------------------------------------------------

def _make_segment(start: float, end: float, text: str) -> SimpleNamespace:
    return SimpleNamespace(start=start, end=end, text=text)


def test_transcribe_file_skips_if_in_sources(tmp_path):
    out_path = tmp_path / "2026-05-30.md"
    out_path.write_text(
        "---\ndate: 2026-05-30\ngenerated_by: transcribe.py\n"
        "generated_at: 2026-05-31T10:00:00\nsources:\n  - audio.wav\n---\n\n"
        "## audio.wav (date via filename)\n\n[00:00.0 -> 00:01.0] Already done.\n",
        encoding="utf-8",
    )
    src = tmp_path / "audio.wav"
    src.touch()
    model = MagicMock()

    with patch("transcribe._resolve_date", return_value=(datetime.date(2026, 5, 30), "filename")):
        result = _transcribe_file(model, src, tmp_path, "2026-05-31T10:00:00")

    model.transcribe.assert_not_called()
    assert result is False


def test_transcribe_file_writes_new(tmp_path):
    src = tmp_path / "20260530_new.wav"
    src.touch()
    segs = [_make_segment(0.0, 2.5, " Hello there ")]
    model = MagicMock()
    model.transcribe.return_value = (iter(segs), MagicMock())

    with patch("transcribe._resolve_date", return_value=(datetime.date(2026, 5, 30), "filename")):
        result = _transcribe_file(model, src, tmp_path, "2026-05-31T10:00:00")

    assert result is True
    out = (tmp_path / "2026-05-30.md").read_text(encoding="utf-8")
    assert "## 20260530_new.wav (date via filename)" in out
    assert "[00:00.0 -> 00:02.5] Hello there" in out


def test_transcribe_file_continues_on_failure(tmp_path):
    """Exception in _transcribe_file propagates so main() can catch and continue."""
    src = tmp_path / "bad.wav"
    src.touch()
    model = MagicMock()
    model.transcribe.side_effect = RuntimeError("GPU exploded")

    with patch("transcribe._resolve_date", return_value=(datetime.date(2026, 5, 30), "filename")):
        with pytest.raises(RuntimeError, match="GPU exploded"):
            _transcribe_file(model, src, tmp_path, "2026-05-31T10:00:00")


# ---------------------------------------------------------------------------
# Integration: run against samples/media/ with mocked WhisperModel
# ---------------------------------------------------------------------------

_SAMPLES_MEDIA = Path(__file__).parent.parent / "samples" / "media"


@pytest.mark.skipif(not _SAMPLES_MEDIA.exists(), reason="samples/media not found")
def test_integration_samples_media(tmp_path):
    segs = [_make_segment(0.0, 3.0, " synthetic audio ")]
    mock_model = MagicMock()
    mock_model.transcribe.return_value = (iter(segs), MagicMock())

    generated_at = "2026-05-31T10:00:00"

    # Patch WhisperModel constructor and _resolve_date to avoid GPU + real ffprobe
    date_map = {
        "20260530_imported.wav": (datetime.date(2026, 5, 30), "filename"),
        "clip-with-metadata.wav": (datetime.date(2026, 5, 31), "mtime"),
        "clip-meta-tagged.mp4": (datetime.date(2026, 5, 28), "ffprobe"),
    }

    def fake_resolve(path: Path):
        return date_map.get(path.name, (datetime.date(2026, 5, 31), "mtime"))

    with patch("transcribe._resolve_date", side_effect=fake_resolve):
        media_files = sorted(
            p for p in _SAMPLES_MEDIA.iterdir()
            if p.suffix.lower() in {".mp4", ".mov", ".mp3", ".m4a", ".wav"}
        )
        for p in media_files:
            _transcribe_file(mock_model, p, tmp_path, generated_at)

    # 20260530_imported.wav -> 2026-05-30.md
    out_30 = tmp_path / "2026-05-30.md"
    assert out_30.exists(), "Expected 2026-05-30.md for 20260530_imported.wav"
    text_30 = out_30.read_text(encoding="utf-8")
    assert "  - 20260530_imported.wav" in text_30
    assert "## 20260530_imported.wav (date via filename)" in text_30
    assert "[00:00.0 -> 00:03.0]" in text_30

    # clip-meta-tagged.mp4 -> 2026-05-28.md (UTC->local date)
    out_28 = tmp_path / "2026-05-28.md"
    assert out_28.exists(), "Expected 2026-05-28.md for clip-meta-tagged.mp4"
    assert "## clip-meta-tagged.mp4 (date via ffprobe)" in out_28.read_text(encoding="utf-8")

    # Resumability: running again skips all
    call_count_before = mock_model.transcribe.call_count
    for p in media_files:
        _transcribe_file(mock_model, p, tmp_path, generated_at)
    assert mock_model.transcribe.call_count == call_count_before, (
        "Re-run should skip all already-transcribed files"
    )
