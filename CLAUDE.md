# SOON Format — Spec & Conformance Hub

Shape-Oriented Object Notation. Compact, lossless encoding of the JSON data model
designed for LLM input token optimization.

## Repository structure

This is the **spec + conformance + benchmarks** repo. Implementations live in sibling repos:

- `../soon-python/` — Python library (`soon_format` package)
- `../soon-typescript/` — TypeScript library (`@soon-format/soon`)

Key directories here:

| Path | Purpose |
|---|---|
| `SPEC.md` | Normative format spec (v0.2) |
| `conformance/` | 47 language-agnostic JSON fixtures (encode/decode/roundtrip/errors) |
| `benchmarks/` | Size, speed, and accuracy benchmarks |
| `benchmarks/accuracy/` | LLM retrieval-accuracy harness (SOON vs JSON vs YAML vs TOON vs GCF) |
| `playground/` | Vite+TS web app for side-by-side format comparison |

## Benchmark harness

The accuracy benchmark at `benchmarks/accuracy/` measures LLM comprehension across formats.
See `benchmarks/accuracy/README.md` for full docs. Quick reference:

```bash
# Load API keys
export $(grep -v '^#' .env | xargs)

# Mock run (verifies pipeline)
python3 benchmarks/accuracy/run.py --provider mock:fixture

# Real run
python3 benchmarks/accuracy/run.py --provider anthropic:claude-haiku-4-5-20251001
```

Results go to `benchmarks/accuracy/results/retrieval-accuracy.md`.

## Conventions

- Spec changes land as fixtures first, code second
- All benchmark datasets use fixed random seeds for reproducibility
- No LLM judge — all scoring is deterministic via `normalize.py`
- Provider calls use `temperature=0`
