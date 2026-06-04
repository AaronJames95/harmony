"""HTTP API wrapper around faster-whisper for on-demand transcription.

Runs on Forge, bound to the Tailscale interface.
Single endpoint: POST /transcribe  (multipart, field: file)
Returns:         {"transcript": "<markdown text>", "filename": "<original name>"}

Usage:
    uvicorn compute.transcribe_api:app --host <tailscale-ip> --port 8765
"""

import datetime
import tempfile
from pathlib import Path

from fastapi import FastAPI, HTTPException, UploadFile
from fastapi.responses import JSONResponse

_MEDIA_EXTENSIONS = {".mp4", ".mov", ".mp3", ".m4a", ".wav", ".ogg", ".webm"}

app = FastAPI(title="Harmony Transcription API")

# Model is loaded once at startup — expensive, keep it alive.
_model = None


def _get_model():
    global _model
    if _model is None:
        from faster_whisper import WhisperModel  # noqa: PLC0415
        _model = WhisperModel("large-v3", device="cuda", compute_type="int8_float16")
    return _model


def _fmt_ts(seconds: float) -> str:
    mins, secs = divmod(seconds, 60)
    return f"{int(mins):02d}:{secs:04.1f}"


def _run_transcription(audio_path: Path) -> str:
    model = _get_model()
    segments, _info = model.transcribe(str(audio_path))
    lines = [
        f"[{_fmt_ts(seg.start)} -> {_fmt_ts(seg.end)}] {seg.text.strip()}"
        for seg in segments
    ]
    return "\n".join(lines)


def _wrap_markdown(transcript: str, filename: str, generated_at: str) -> str:
    return (
        f"---\n"
        f"source: {filename}\n"
        f"generated_by: transcribe_api.py\n"
        f"generated_at: {generated_at}\n"
        f"---\n\n"
        f"{transcript}\n"
    )


@app.post("/transcribe")
async def transcribe(file: UploadFile):
    suffix = Path(file.filename or "upload").suffix.lower()
    if suffix not in _MEDIA_EXTENSIONS:
        raise HTTPException(
            status_code=415,
            detail=f"Unsupported file type '{suffix}'. Accepted: {sorted(_MEDIA_EXTENSIONS)}",
        )

    with tempfile.NamedTemporaryFile(suffix=suffix, delete=False) as tmp:
        tmp_path = Path(tmp.name)
        tmp.write(await file.read())

    try:
        transcript = _run_transcription(tmp_path)
    except Exception as exc:
        tmp_path.unlink(missing_ok=True)
        raise HTTPException(status_code=500, detail=f"Transcription failed: {exc}") from exc

    tmp_path.unlink(missing_ok=True)
    generated_at = datetime.datetime.now().isoformat(timespec="seconds")
    markdown = _wrap_markdown(transcript, file.filename or "upload", generated_at)

    return JSONResponse({"transcript": markdown, "filename": file.filename or "upload"})


@app.get("/health")
def health():
    return {"status": "ok"}
