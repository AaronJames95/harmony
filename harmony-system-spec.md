# Harmony Data Center — System Spec
> Reusable context for design prompts. Paste this in so any model (or future you)
> reasons correctly about where things run, what each machine is for, and the rules.
> Last updated: 2026-05-30

---

## Purpose

Harmony is a personal, private data center. Design goal: a self-hosted "personal
operating system" — storage, services, and an AI reflection pipeline — that keeps
sensitive personal data on-premises and uses external APIs only as an occasional,
deliberate consultant.

When proposing changes, respect the **two-plane model** below and the **design
principles** at the end. Default to small, composable, MVP-first services.

---

## Topology at a glance

```
   Devices (laptop, phone, desktop) ──┐
                                       │  Tailscale mesh (private, 100.x)
        ┌──────────────────────────────┴───────────────────────────┐
        │                                                           │
  CONTROL PLANE                                              COMPUTE PLANE
  NUC "Conductor"                                            Workstation "Forge"
  always-on orchestrator                                     on-demand GPU inference
  Nextcloud · vault · scheduler · watcher · scraper          Whisper · Ollama · batch jobs
        │                                                           │
        └─────────────── dispatches jobs over Tailscale ───────────┘

  External consultant (rare, deliberate): Claude API — anonymized/compressed only
```

Two planes, one mesh. The NUC decides *what* and *when*; the workstation does the
*heavy compute*; Tailscale is the private wire between them; Claude API is brought
in occasionally for the highest-stakes synthesis.

---

## Machines

### Conductor — control plane (currently `NUCserver`)
| | |
|---|---|
| Role | Always-on orchestrator + storage + services. **Never runs LLMs.** |
| Hardware | Intel N95 (4c) · 16GB RAM · Intel UHD (integrated) |
| OS | Ubuntu 24.04 LTS, headless/server |
| Uptime | 238+ days — proven reliable; suited to always-on duty |
| Runs | Nextcloud · Obsidian vault (source of truth) · scheduler (cron/systemd) · file watcher · info scraper · Git |
| Storage | 467GB root · `/mnt/hdd-data` 7.2TB |
| Does NOT | Run Whisper, Ollama, or any model. Dispatches those to Forge. |

### Forge — compute plane (currently `AIWORKSTATION` / host `server`)
| | |
|---|---|
| Role | GPU inference engine. Heavy/batch work, on demand or scheduled. |
| Hardware | AMD Ryzen 7 5700X (8c/16t) · 64GB RAM · **RTX 3090 (24GB VRAM)** |
| OS | Linux Mint 21.2 (desktop — also runs heavier GUI apps) |
| Runs | faster-whisper (large-v3) · Ollama (as a service) · backlog batch jobs |
| Config notes | Ollama bound to the Tailscale interface; sleep/suspend disabled so Conductor can dispatch overnight jobs |
| Storage | 3.1TB SSD (backup volume) |

> Naming: hosts are currently confusingly named (the workstation's hostname is
> literally `server`, the NUC is `NUCserver`). Proposed convention: rename by role
> under the Harmony theme — **Conductor** (NUC, orchestrates) and **Forge** (3090,
> does the work). Adjust to taste; just make hostnames unambiguous.

---

## Model selection (Forge / Ollama)

| Task | Model | Why |
|---|---|---|
| Transcription | faster-whisper `large-v3` (int8/fp16) | ~4x faster than vanilla whisper, fits in ~3–4GB, leaves VRAM for the LLM |
| Daily extraction | 8–14B class (e.g. current Qwen 3 14B Q4) | speed over depth, runs 365x/yr |
| Weekly / quarterly reasoning | Qwen 3 32B Q4 (~20GB) | best single-3090 reasoning |
| One-time bootstrap synthesis | **Claude API, Opus-tier** | highest-leverage, lowest-frequency call; worth the strongest reasoning |

Do **not** run 70B locally — it spills past 24GB into RAM and crawls (~2–6 tok/s).

---

## Storage & data layout

- **Vault** lives inside Nextcloud on Conductor → single source of truth, synced to
  all devices, backed up. Forge mounts/syncs it to read input and write extracts.
- **Raw backlog** (audio/video, often large) lives on the big drives, not in the
  synced vault. Transcripts + extracts go into the vault.
- **Git** on the vault (toward the GitLab goal) for version history of how the
  thinking changes over time.

| Drive | Suggested use |
|---|---|
| NUC `/mnt/hdd-data` 7.2TB | bulk: Nextcloud data, raw backlog working copy |
| 8TB HDD (external) | encrypted backup target (vault + Nextcloud) |
| 4TB SSD | fast scratch for batch transcription/extraction on Forge |
| 2TB HDD | rotating/offline backup copy |

---

## Backups (the data is irreplaceable and sensitive — treat as tier-1)

3-2-1: at least **3** copies, on **2** media, **1** off the working machine.
- Source: Nextcloud + vault on Conductor.
- Backup: encrypted to the 8TB external (e.g. restic/borg, scheduled by Conductor).
- Off-machine: periodic copy to the 2TB taken offline, or an encrypted remote.

---

## Networking

- **Tailscale** mesh connects approved devices only. Services bind to the tailnet
  (100.x), never to public interfaces.
- Forge's Ollama/Whisper endpoints are reachable **only** over Tailscale, from
  Conductor and trusted devices. Use ACLs to scope who can hit the inference ports.
- Tailscale SSH for admin. No exposed ports to the open internet.

---

## AI reflection pipeline → where each stage runs

| Stage | Runs on | Frequency |
|---|---|---|
| Backlog transcription | Forge (Whisper) | once |
| Per-day combine | Conductor (script) | once / ongoing |
| Daily extraction | Forge (Ollama, small model), dispatched by Conductor | daily |
| Weekly review | Forge (Ollama 32B), scheduled by Conductor | weekly |
| Quarterly analysis | Forge (Ollama 32B) | quarterly |
| Bootstrap / recalibration | **Claude API (Opus-tier), anonymized** | rare |
| Watcher, scheduling, inbox delivery, storage | Conductor | always |

---

## Design principles

- **Two planes.** Conductor orchestrates and stores; Forge computes. Don't put models
  on Conductor; don't make Forge the always-on coordinator.
- **Local-first for raw data.** Raw reflections never leave Harmony. Claude API sees
  only compressed/anonymized material, only occasionally, by deliberate choice.
- **Schema once, run local forever.** Use the strong external model to *derive* the
  extraction/tracking schema; hand the repeatable per-day work to the local model.
- **MVP, tiny, composable.** Small single-purpose services over monoliths. Ship the
  smallest thing that works, then grow it.
- **Inbox model for agent output.** Agents *prepare* and drop drafts/briefs in `/inbox`;
  they never send, delete, or act outward without you.
- **Distress is the exception to the inbox model.** Any detection of acute distress must
  route **outward to a human**, never silently into a folder — and the system is never
  the safety net for a crisis. (See companion design notes.)

---

## Current state vs planned

**Exists now:** both machines, Tailscale mesh, Nextcloud on the NUC, ~50 backlog days
extracted via Claude API, bootstrap recommendations drafted.

**Planned / aspirational:** Ollama-as-service on Forge, vault-in-Nextcloud + Git,
full backlog transcription, automated daily/weekly pipeline, GitLab, RustDesk,
info scraper, possible future move of Nextcloud to an RPi.

---

## Open decisions (recommended default in italics)

1. Hostnames — *adopt Conductor / Forge (or your own unambiguous scheme).*
2. Vault home — *inside Nextcloud on Conductor, Git-tracked.*
3. Forge availability — *disable sleep; Ollama as a systemd service on the tailnet.*
4. Backup tooling — *restic or borg to the 8TB, encrypted, scheduled.*
5. Minor health note — Forge shows swap at 100% (2GB) with RAM half-free; harmless
   but worth a glance (lower swappiness or grow swap if batch jobs ever OOM).
