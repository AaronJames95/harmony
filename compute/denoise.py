"""Audio denoising via DeepFilterNet.

Exposes a single entry point, `denoise_audio`, so the implementation can be
swapped later (e.g. for Resemble Enhance) without touching callers.

Requires the `deepfilternet` package (needs a Rust toolchain to build) and a
working `ffmpeg` on PATH for the wav -> mp3 conversion.
"""

import logging
import subprocess
import tempfile
from pathlib import Path

log = logging.getLogger(__name__)

_model = None
_df_state = None


def _load_model():
    global _model, _df_state
    if _model is None:
        from df.enhance import init_df  # noqa: PLC0415
        log.info("Loading DeepFilterNet model...")
        _model, _df_state, _ = init_df()
        log.info("DeepFilterNet model loaded.")
    return _model, _df_state


def denoise_audio(input_path: Path, output_path: Path | None = None) -> Path:
    """Run DeepFilterNet on `input_path` and write a cleaned MP3.

    Returns the path to the cleaned file. If `output_path` is not given,
    writes alongside the input with `_denoised` appended to the stem.
    """
    from df.enhance import enhance, load_audio, save_audio  # noqa: PLC0415

    if output_path is None:
        output_path = input_path.with_name(f"{input_path.stem}_denoised.mp3")

    model, df_state = _load_model()
    audio, _ = load_audio(str(input_path), sr=df_state.sr())
    enhanced = enhance(model, df_state, audio)

    with tempfile.NamedTemporaryFile(suffix=".wav", delete=False) as tmp:
        wav_path = Path(tmp.name)
    try:
        save_audio(str(wav_path), enhanced, df_state.sr())
        subprocess.run(
            ["ffmpeg", "-y", "-i", str(wav_path), "-codec:a", "libmp3lame", "-qscale:a", "2", str(output_path)],
            check=True, capture_output=True,
        )
    finally:
        wav_path.unlink(missing_ok=True)

    return output_path
