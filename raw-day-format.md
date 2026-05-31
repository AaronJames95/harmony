# Normalized Raw-Day Format — the Stage 0a output contract

Stage 0a parses the three input formats and writes **one file per date** in this
format. This is the *only* thing 0a produces. Extraction (0c) reads these files;
0a itself does no LLM work and makes no judgments about content.

## File

- One Markdown file per date, named `YYYY-MM-DD.md`, written to the output dir
  (e.g. `out/` during sample testing — gitignored).
- UTF-8. **Read inputs as explicit UTF-8 and fail loudly on a decode error.** Do not
  use `errors="ignore"` — it silently eats the emoji section headers in the new
  template and Hebrew in examen paths.
- Resumable: if the output file for a date already exists, skip it.

## Structure

YAML frontmatter + a Markdown body that preserves the raw source text verbatim.

```
---
date: YYYY-MM-DD
source_format: legacy | new_template | none
sources_present:
  morning_pages: bool
  examen: bool
  meditation: bool          # new_template only
  video_transcript: bool    # new_template only
input_completion_score: 0.0–1.0
generated_by: combine.py
generated_at: <ISO timestamp>
---

## <Source name>

<raw text, verbatim>

## <Source name>

<raw text, verbatim>
```

### `input_completion_score` is format-aware

Score = present sources ÷ sources *expected for that format*:
- **legacy** expects `{morning_pages, examen}` → denominator 2.
- **new_template** expects `{meditation, examen, morning_pages, video_transcript}` → denominator 4.
- **none** (absence) → score `0.0`.

Only include the `sources_present` keys relevant to that format.

### Presence detection is mechanical, not semantic

A source counts as present if its section has real content — not empty, and not a
skip marker (`(skipped)`, `NOT done`, `(no recording)`, `(none)`). Coarse string
logic is fine here. Semantic nuance is 0c's job, not 0a's.

> **Important:** the completion score and the body are independent. A day can score
> `0.0` (all *practices* skipped) and still have a body full of text in other
> sections. Always preserve **all** source content in the body regardless of the
> booleans. (See the 2026-05-29 example — it is a low-completion day that is *not*
> an absence day, and the body must keep every word.)

## Examples

### Both sources merge (3/14)
```
---
date: 2026-03-14
source_format: legacy
sources_present:
  morning_pages: true
  examen: true
input_completion_score: 1.0
generated_by: combine.py
generated_at: 2026-05-31T12:00:00
---

## Morning Pages

ok here we go again with the pages...

## Examen

I'm grateful the contract got extended two more weeks...
```

### Partial day — morning pages only (3/17)
```
---
date: 2026-03-17
source_format: legacy
sources_present:
  morning_pages: true
  examen: false
input_completion_score: 0.5
generated_by: combine.py
generated_at: 2026-05-31T12:00:00
---

## Morning Pages

rough one. didnt write yesterday at all...
```

### Absence (3/16) — no source files in range
```
---
date: 2026-03-16
source_format: none
sources_present:
  morning_pages: false
  examen: false
input_completion_score: 0.0
generated_by: combine.py
generated_at: 2026-05-31T12:00:00
---

inputs: none
```

### New template, full day (5/28)
```
---
date: 2026-05-28
source_format: new_template
sources_present:
  meditation: true
  examen: true
  morning_pages: true
  video_transcript: true
input_completion_score: 1.0
generated_by: combine.py
generated_at: 2026-05-31T12:00:00
---

## Daily Note

#dailynote
2026-05-28 — Wednesday
... full template content preserved verbatim, emoji headers intact ...
```

### New template, low completion but NOT absence (5/29)
```
---
date: 2026-05-29
source_format: new_template
sources_present:
  meditation: false
  examen: false
  morning_pages: false
  video_transcript: false
input_completion_score: 0.0
generated_by: combine.py
generated_at: 2026-05-31T12:00:00
---

## Daily Note

#dailynote
2026-05-29 — Thursday
... full content preserved verbatim — Gratitude / Interior Movement / etc.
    still contain text and must be kept ...
```

## Behaviors 0a must implement

1. **Merge** same-date sources into one file (legacy morning pages + examen).
2. **Partial days** — emit with the right booleans (either source missing).
3. **Absence gap-fill within the processed range:** iterate from the earliest to the
   latest date *in the current batch* and emit a `source_format: none` file for any
   date with no sources. Process `samples/legacy/` and `samples/new/` as **separate
   batches** so gap-fill stays within each period (otherwise you'd generate ~70 empty
   days between 3/18 and 5/28).
4. **Date parsing** — legacy prefixes mix `:` and `.` (`- 3/14:` and `- 3/15.`);
   handle both. Examen month/year comes from the filename (`EX_MM_YYYY.md`).
5. **Resumable + UTF-8-strict**, as above.

Suggested CLI (Claude Code may refine in plan mode):
`python compute/combine.py --inputs samples/legacy --format legacy --out out/`
