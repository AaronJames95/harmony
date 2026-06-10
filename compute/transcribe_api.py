"""HTTP API wrapper around faster-whisper for on-demand transcription.

Runs on Forge, bound to the Tailscale interface.
Single endpoint: POST /transcribe  (multipart, field: file)
Returns:         {"transcript": "<markdown text>", "filename": "<original name>"}

Usage:
    uvicorn compute.transcribe_api:app --host <tailscale-ip> --port 8765

Environment:
    WHISPER_IDLE_TIMEOUT  seconds of inactivity before unloading model (default 600)
"""

import asyncio
import datetime
import gc
import logging
import os
import tempfile
from contextlib import asynccontextmanager
from pathlib import Path

from fastapi import FastAPI, Form, HTTPException, UploadFile
from fastapi.responses import JSONResponse

_MEDIA_EXTENSIONS = {".mp4", ".mov", ".mp3", ".m4a", ".wav", ".ogg", ".webm"}

IDLE_TIMEOUT = int(os.environ.get("WHISPER_IDLE_TIMEOUT", "600"))
_CHECK_INTERVAL = 60

log = logging.getLogger(__name__)

_model = None
_last_used: float = 0.0
_active_count: int = 0
_model_lock: asyncio.Lock


def _load_model():
    global _model
    if _model is None:
        from faster_whisper import WhisperModel  # noqa: PLC0415
        log.info("Loading Whisper model...")
        _model = WhisperModel("large-v3", device="cuda", compute_type="int8_float16")
        log.info("Whisper model loaded.")
    return _model


def _unload_model():
    global _model
    if _model is not None:
        log.info("Unloading Whisper model (idle timeout).")
        _model = None
        gc.collect()


async def _idle_watcher():
    while True:
        await asyncio.sleep(_CHECK_INTERVAL)
        loop = asyncio.get_running_loop()
        async with _model_lock:
            if _model is not None and _active_count == 0:
                if loop.time() - _last_used >= IDLE_TIMEOUT:
                    _unload_model()


@asynccontextmanager
async def lifespan(_app: FastAPI):
    global _model_lock
    _model_lock = asyncio.Lock()
    task = asyncio.create_task(_idle_watcher())
    yield
    task.cancel()
    try:
        await task
    except asyncio.CancelledError:
        pass
    async with _model_lock:
        _unload_model()


app = FastAPI(title="Harmony Transcription API", lifespan=lifespan)


def _fmt_ts(seconds: float) -> str:
    mins, secs = divmod(seconds, 60)
    return f"{int(mins):02d}:{secs:04.1f}"


def _run_transcription(audio_path: Path, model, music: bool = False) -> str:
    kwargs = {}
    if music:
        # Music vocals confuse Whisper's language-model conditioning: an early
        # mistranscribed phrase (e.g. a count-in) gets fed back as context and
        # the model repeats it for the rest of the track. Disabling it plus a
        # temperature fallback ladder lets Whisper escape repetition loops.
        kwargs["condition_on_previous_text"] = False
        kwargs["temperature"] = [0.0, 0.2, 0.4, 0.6, 0.8, 1.0]
        kwargs["vad_filter"] = True
    segments, _info = model.transcribe(str(audio_path), **kwargs)
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
async def transcribe(file: UploadFile, music: bool = Form(False)):
    global _last_used, _active_count

    suffix = Path(file.filename or "upload").suffix.lower()
    if suffix not in _MEDIA_EXTENSIONS:
        raise HTTPException(
            status_code=415,
            detail=f"Unsupported file type '{suffix}'. Accepted: {sorted(_MEDIA_EXTENSIONS)}",
        )

    with tempfile.NamedTemporaryFile(suffix=suffix, delete=False) as tmp:
        tmp_path = Path(tmp.name)
        tmp.write(await file.read())

    async with _model_lock:
        model = _load_model()
        _active_count += 1

    try:
        loop = asyncio.get_running_loop()
        transcript = await loop.run_in_executor(None, _run_transcription, tmp_path, model, music)
    except Exception as exc:
        tmp_path.unlink(missing_ok=True)
        raise HTTPException(status_code=500, detail=f"Transcription failed: {exc}") from exc
    finally:
        tmp_path.unlink(missing_ok=True)
        async with _model_lock:
            _active_count -= 1
            _last_used = asyncio.get_running_loop().time()

    generated_at = datetime.datetime.now().isoformat(timespec="seconds")
    markdown = _wrap_markdown(transcript, file.filename or "upload", generated_at)

    return JSONResponse({"transcript": markdown, "filename": file.filename or "upload"})


@app.get("/health")
def health():
    return {"status": "ok", "model_loaded": _model is not None}
