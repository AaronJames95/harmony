# Harmony — Personal Reflection Pipeline

Read this fully before doing anything. Also read `harmony-system-spec.md` in this
repo for the hardware topology. Build one stage at a time. Do not build ahead.

## What this is

A private, self-hosted pipeline that ingests daily personal reflection (writing,
prayer/examen, transcribed audio/video), extracts structured data with an LLM,
produces weekly and quarterly reviews, and (later) prepares agent outputs into an
inbox. It runs across two machines connected by Tailscale.

## Architecture (two planes)

- **Conductor** (NUC, Ubuntu, always-on, no GPU): orchestrator + storage. Runs the
  scheduler, file watcher, job dispatch, inbox delivery, Nextcloud, the vault, Git.
  Code lives in `control/`. **Never runs models here.**
- **Forge** (workstation, Mint, RTX 3090 24GB): compute. Runs faster-whisper and
  Ollama, does transcription + extraction + weekly/quarterly model calls. Code lives
  in `compute/`. Conductor dispatches jobs to Forge's Ollama over the tailnet.

Monorepo layout:
```
/harmony
  CLAUDE.md
  harmony-system-spec.md
  compute/      # runs on Forge
  control/      # runs on Conductor
  shared/       # schemas, prompts, small utils used by both
  samples/      # synthetic/redacted test data ONLY (safe to read)
  .gitignore
```

## Hard rules (do not violate)

1. **Never commit personal data.** Real reflections, transcripts, the vault,
   extracts, and bootstrap outputs must never enter Git. Ensure `.gitignore`
   covers: `vault/`, `data/`, `transcripts/`, `extracts/`, `bootstrap/`, `*.env`,
   `.env`, `secrets*`. Test only against `samples/` (synthetic or redacted).
2. **Never hardcode secrets.** API keys come from environment / a gitignored
   `.env`. No keys in source, ever.
3. **Structured output on every LLM call.** Local (Ollama): pass a JSON schema via
   the `format` field. Claude API: use tool-use with the schema forced via
   `tool_choice`. Always validate; on failure, retry once then fall back to a
   json-repair pass. Raw `json.loads` on a free-text completion is not acceptable —
   it is the known cause of past data loss.
4. **All batch jobs are resumable.** Skip already-processed days. Safe to restart.
5. **Local-first.** Raw reflections stay on Harmony. The Claude API is used only for
   the rare, one-time bootstrap synthesis, and only on compressed/anonymized input.
6. **No 70B locally.** It exceeds 24GB VRAM and crawls. Use the model table below.
7. **Distress is the exception to the inbox model.** If any stage detects acute
   distress, it must surface a path to a **human**, never file it silently to a
   folder, and the system is never positioned as a crisis safety net.
8. **MVP, one stage at a time.** Build the smallest working version of the current
   stage, get its validation gate to pass, commit, then stop. Do not scaffold
   future stages.

## Models (for the pipeline's own calls — not Claude Code's model)

| Task | Model |
|---|---|
| Transcription | faster-whisper `large-v3` (int8/fp16) on Forge |
| Daily extraction | small local model, ~8–14B Q4 via Ollama |
| Weekly / quarterly | Qwen 3 32B Q4 via Ollama |
| One-time bootstrap synthesis | Claude API, Opus-tier, anonymized input |

## Build order (with validation gates)

- **Stage 0 — Backlog.** (a) per-day combine script; (b) faster-whisper batch
  transcription (resumable); (c) resumable Ollama extraction with structured output.
  Gate: spot-check 10 random extracted sample days against their source — real
  capture, no hallucination.
- **Stage 1 — Foundation.** Going-forward daily extraction + a file watcher on
  Conductor that dispatches to Forge. Gate: drop a sample file, a structured note
  appears with no manual step; empty days still produce an absence note.
- **Stage 2 — Weekly review.** Pull last 7 extracts, run 32B, write to `weekly/`.
  Gate: output rings true against a known sample week.
- **Stage 3 — First agents (pick two).** Follow-through agent + quarterly letter.
  Inbox delivery pattern. Gate: something useful and not noisy lands in `/inbox`.
- Stage 4+ — only after the above earns it.

## Commands

Fill these in as you build each piece; keep this list current.
```
# (compute/) combine legacy backlog: python compute/combine.py --inputs samples/legacy --format legacy --out out/
# (compute/) combine new-template:   python compute/combine.py --inputs samples/new --format new_template --out out/
# (compute/) transcribe backlog:     python compute/transcribe.py --inputs <media-dir> --out <out-dir>
# (compute/) extract one day:        <cmd>
# (compute/) run weekly review:      <cmd>
# (control/) start the watcher:      <cmd>
# run tests:                         .venv/bin/python -m pytest tests/ -v
```

## Conventions

- Python. Standard library + `requests`/`anthropic`/`faster-whisper`; ask before
  adding heavier deps. Type hints. Small, single-purpose modules.
- Dates are the join key across sources; parse them robustly (filenames may use
  `YYYY-MM-DD`; the morning-pages file has ambiguous `M/D` dates — confirm the
  parsing strategy before trusting it for the time series).
- Outputs are Markdown notes written into the vault structure (see spec).
