# Forge setup — `/clean` and `/clean transcribe` commands (DONE)

This was completed directly on Forge. Notes for reference / re-deploys:

1. Installed Rust via rustup (`curl --proto '=https' --tlsv1.2 -sSf https://sh.rustup.rs | sh`)
   — needed to build `deepfilterlib`, the Rust extension behind `deepfilternet`.

2. `ffmpeg` was already installed (used by `compute/denoise.py` for the wav -> mp3
   conversion).

3. `compute/requirements.txt` now pins `torch==2.8.0` and `torchaudio==2.8.0` —
   deepfilternet 0.5.6 imports `torchaudio.backend.common`, which was removed in
   torchaudio 2.9+. Newer torch/torchaudio installed cleanly but broke this import;
   pinning to 2.8.0 fixed it (with deprecation warnings only).

4. `compute/transcribe_api.py` imports `denoise.py` via `from .denoise import
   denoise_audio` — it must be a relative import because the systemd service runs it
   as `python3 -m uvicorn compute.transcribe_api:app` (package import), not as a
   standalone script.

5. Ran `.venv/bin/pip install -r compute/requirements.txt`, restarted
   `transcribe_api.service`, and verified:
   ```
   curl http://<forge-tailscale-ip>:8765/health
   curl http://<forge-tailscale-ip>:8765/openapi.json   # paths include /transcribe, /clean, /health
   ```
   Also ran `denoise_audio()` directly against `samples/media/20260603_181545.mp3` —
   produced a valid denoised MP3. DeepFilterNet3 model auto-downloaded to
   `~/.cache/DeepFilterNet/`.

See `conductor-clean-command-setup.md` for the remaining Conductor-side work.
