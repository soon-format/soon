# SOON retrieval-accuracy benchmark

Measures how well LLMs answer questions about the same underlying data
when the data is presented in different serialization formats. Companion
to the size benchmark (`benchmarks/README.md`) and the deliverable for
issue #8.

## What it measures

- **Raw accuracy** per (model, format, dataset).
- **Accuracy per 1K prompt tokens** — the "money metric".
- **Per-mechanism ablation deltas** — labeled tuples, shape-reminder
  comments, row-count guardrail, ELIDE, REF. One row per mechanism
  turned on vs the plain SOON baseline.

Scoring is deterministic and type-aware (see `normalize.py`); no LLM
judge is involved.

## Datasets

Reuses generators from `benchmarks/datasets.py`:

| Short | Description |
|---|---|
| `L2` | 100 flat employee rows |
| `L5` | 100 nested orders (customer + address + items) |
| `L6` | Deeply nested org tree (5 levels) |
| `L7` | 120-event log with optional fields |
| `L10` | Sparse API response (ELIDE showcase) |
| `L11` | Shared-address employees (REF showcase) |

## Running

```bash
# Plumbing test — mock provider, capped at 10 questions:
python3 benchmarks/accuracy/run.py --provider mock:fixture --dry-run

# Full run against a real provider:
export OPENAI_API_KEY=...
python3 benchmarks/accuracy/run.py --provider openai:gpt-5-nano

# Multiple providers in one invocation:
python3 benchmarks/accuracy/run.py \
    --provider openai:gpt-5-nano \
    --provider anthropic:claude-haiku-4-5-20251001 \
    --provider google:gemini-3-flash-preview
```

Results land at `results/models/{model}.json`; the aggregated report is
`results/retrieval-accuracy.md`.

## Formats measured

| Name | What it is |
|---|---|
| `json` | Compact JSON (baseline) |
| `yaml` | YAML |
| `toon` | TOON (requires `pip install toon-py`) |
| `soon` | SOON positional |
| `soon-labeled` | SOON with `mode="labeled"` |
| `soon-no-guardrail` | SOON with `row_count_guardrail=False` |
| `soon-shape-hint` | SOON with `shape_hint_rows=10` |
| `soon-elide` | SOON with `elide=True` |
| `soon-ref` | SOON with `ref=True` |

## Cost estimate

A full run of 240 questions × 8 formats × 3 models is ~5,700 model
calls. At current API prices (approximate):

- gpt-5-nano: ≈ $0.30 per full run
- claude-haiku-4-5: ≈ $0.80 per full run
- gemini-3-flash-preview: ≈ $0.20 per full run

Actual cost depends on payload sizes and completion length.

## Adding your own datasets

1. Add a generator to `benchmarks/datasets.py`.
2. Add a question module under `benchmarks/accuracy/questions/`
   exposing `generate(data) -> list[Question]`.
3. Wire it into `benchmarks/accuracy/questions/__init__.py` and the
   `DATASETS` map in `run.py`.
