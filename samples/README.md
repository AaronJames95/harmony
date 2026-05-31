# Samples — synthetic test data ONLY

Everything in this folder is **fictional**. No real names, no real entries. It exists
so Claude Code (and you) can build and test the pipeline without any real reflection
ever touching an external service. Real data is processed later, locally, by the
local model. Per CLAUDE.md rule 1, this folder is the *only* data safe to read in a
Claude Code session, and nothing real is ever committed.

The voice and themes are modeled on the real corpus (Ignatian discernment,
consolation/desolation, "led by love", creative/music identity, NYC-vs-home tension,
financial anxiety, dating preoccupation, the porn/weed struggle, morning-pages-as-
practice) so the extractor gets tested against true-to-shape content — but all
specifics are invented.

## What's here and what each piece tests

```
legacy/
  Morning Pages.md                  # one file, multiple dated entries (3/14, 3/15, 3/17)
  examen/2026/EX_03_2026.md          # monthly examen file (3/14, 3/15, 3/18)
new/
  2026-05-28.md                      # full new-template day (good day)
  2026-05-29.md                      # new-template day — DISTRESS TEST (see below)
  2026-05-30.md                      # new-template day (partial recovery, mixed)
```

Date coverage is deliberate, to test merge logic:

| Date  | Morning pages | Examen | Tests |
|-------|---------------|--------|-------|
| 3/14  | ✓ | ✓ | both sources merge into one day |
| 3/15  | ✓ | ✓ | both sources merge |
| 3/16  | — | — | **absence** — should still produce an absence note |
| 3/17  | ✓ | — | **partial day** (morning pages only) |
| 3/18  | — | ✓ | **partial day** (examen only) |

The legacy entries also include the real-world messiness on purpose: date prefixes
mix `:` and `.` separators (`- 3/14:` vs `- 3/15.`), so the date regex gets tested
against both.

## The distress test case (2026-05-29)

This day intentionally carries a strong distress signal — collapse of all practices,
isolation, shame after a relapse, and hopelessness language ("couldn't see the point
of wanting anything," "scared by how little I cared"). It exists to exercise
**CLAUDE.md rule 7**: the pipeline must route this *outward to a human*, never file it
silently to a folder.

Two honest caveats:
- It contains **no** explicit self-harm content, and you should not add any. This
  fixture tests the *routing path*, not classifier sensitivity.
- Tuning detection against real signal is something you do privately, on your own
  data, with the local model — not in a Claude Code session and not against this file.

## Encoding notes for the parsers

- Files are UTF-8. The new template uses **emoji as section headers** (🫧 😌 🤲🏽 📝 💡 ✅ 📹)
  and they are load-bearing for parsing — don't strip non-ASCII. The old script's
  `read_text(errors="ignore")` could silently drop them; prefer `errors="replace"` or
  explicit UTF-8 and fail loudly.
- The real examen lives under a Hebrew folder name (יֵשׁוּעַ). Path handling must be
  Unicode-safe. The examen filename pattern `EX_MM_YYYY.md` is parsed for month/year,
  so keep that convention.
