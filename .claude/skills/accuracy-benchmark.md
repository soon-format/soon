---
name: accuracy-benchmark
description: Run the SOON retrieval-accuracy benchmark against LLM providers
user_invocable: true
---

# Accuracy Benchmark Skill

Run the SOON retrieval-accuracy benchmark that measures how well LLMs comprehend data encoded in SOON vs JSON, YAML, TOON, and GCF.

## Prerequisites

Before running, verify:

1. **API keys** — Check `.env` for `ANTHROPIC_API_KEY`, `OPENAI_API_KEY`, `GEMINI_API_KEY`. Load with: `export $(grep -v '^#' .env | xargs)`
2. **GCF encoder** — Needs `playground/node_modules`. If missing: `cd playground && npm install`
3. **TOON** — `pip install toon-py` (optional, skipped if missing)

## How to run

### Quick validation (no API cost)

```bash
python3 benchmarks/accuracy/run.py --provider mock:fixture --dry-run
```

Must print `100.0` for all formats. If not, the scoring pipeline is broken.

### Dry run against a real provider (10 questions, < $0.01)

```bash
export $(grep -v '^#' .env | xargs)
python3 benchmarks/accuracy/run.py \
    --provider anthropic:claude-haiku-4-5-20251001 --dry-run
```

### Full single-provider run

```bash
python3 benchmarks/accuracy/run.py \
    --provider anthropic:claude-haiku-4-5-20251001
```

### Full multi-provider run (~$1.65)

```bash
python3 benchmarks/accuracy/run.py \
    --provider anthropic:claude-haiku-4-5-20251001 \
    --provider openai:gpt-4o-mini \
    --provider google:gemini-2.0-flash
```

### Subset run (specific formats or datasets)

```bash
python3 benchmarks/accuracy/run.py \
    --provider anthropic:claude-haiku-4-5-20251001 \
    --format json --format gcf --format soon \
    --dataset L5 --dataset L12
```

## What it tests

- **275 questions** across 7 datasets (L2 flat, L5 nested, L6 deep, L7 events, L10 sparse, L11 shared-ref, L12 code-graph)
- **10 formats**: json, yaml, toon, gcf, soon, soon-labeled, soon-no-guardrail, soon-shape-hint, soon-elide, soon-ref
- **Deterministic scoring** — type-aware comparison, no LLM judge, `temperature=0`
- **Metrics**: raw accuracy, accuracy per 1K prompt tokens, per-dataset breakdown, ablation deltas

## Output files

- `benchmarks/accuracy/results/models/{provider}_{model}.json` — raw per-question results
- `benchmarks/accuracy/results/retrieval-accuracy.md` — aggregated report

## After running

Read and share the report:

```bash
cat benchmarks/accuracy/results/retrieval-accuracy.md
```

Key tables to look at:
1. **Overall accuracy** — does SOON match or beat JSON/GCF/TOON?
2. **Accuracy per 1K tokens** — SOON should lead (smaller payload + comparable accuracy)
3. **Per-dataset** — L5/L6 (nested) is where SOON should dominate; L12 (flat) is GCF's best shape
4. **Ablation deltas** — which mechanisms help, which hurt
