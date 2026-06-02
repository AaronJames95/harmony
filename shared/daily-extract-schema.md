# Daily Extract Schema — the Stage 0c output contract

Stage 0c reads one normalized raw-day file (from 0a) and produces one structured
extract per date. This schema is the same regardless of input format — legacy or
new template both land here. 0c runs on Forge via Ollama (local model), with the
reliability rules below. The bootstrap (separate, rare) uses the same schema via
Claude API tool-use.

**Scope:** 0c is source-agnostic — it reads whatever text the raw-day contains and
never reasons about where it came from. By project decision, video transcripts are
NOT processed: they remain standalone readable notes and do not feed extraction.
0c needs no transcript handling of any kind.

## The schema

```json
{
  "date": "YYYY-MM-DD",
  "source_format": "legacy | new_template | none",
  "input_completion_score": 0.0,
  "emotional_climate": "",
  "energy_level": "high | medium | low | mixed",
  "spiritual_movement": "consolation | desolation | mixed | unclear",
  "tasks": [],
  "verses": [],
  "creative_ideas": [],
  "gratitude_and_consolations": [],
  "people_mentioned": [],
  "questions_alive": [],
  "struggles_or_fears": [],
  "notable_phrases": [],
  "summary": ""
}
```

Field notes:
- `emotional_climate`: one honest sentence — positive, negative, or mixed as it was.
- `energy_level` / `spiritual_movement`: one of the enum values only.
- list fields: be generous, capture intent not just explicit statements; empty `[]` is fine.
- `people_mentioned`: each item `{ "name": "", "context": "friend|family|romantic|work|mentor|other" }`.
- `summary`: 80–100 words, the whole day, not just the hard parts.
- Carry `date`, `source_format`, `input_completion_score` straight through from the
  raw-day frontmatter — do not ask the model to invent them.

## Reliability rules (CLAUDE.md rule 3 — this is the whole point of 0c)

1. **Force structure.** Local: Ollama `format` = this JSON schema. Bootstrap: Claude
   API tool-use with the schema, `tool_choice` forced. No free-text completions parsed
   with raw `json.loads`.
2. **Validate** every result against the schema (types + enums). On failure:
3. **Retry once**, re-prompting with the validation error.
4. **Repair fallback**: if it still fails, run a `json-repair` pass; if *that* fails,
   write a `{ "date": ..., "extraction_failed": true, "error": ... }` stub so the day
   is visible, not silently dropped. (Silent drops were the 40–45/50 problem.)
5. **Resumable**: skip dates already extracted successfully; retry only failed stubs.
6. **Set `max_tokens` generously** (≥ 2000) — truncation mid-object is a failure mode.

## Output

- `out/extracts/YYYY-MM-DD.json` (gitignored).
- A human-readable `out/extracts/YYYY-MM-DD.md` rendering is optional and nice for
  spot-checking, but the JSON is the source of truth.
