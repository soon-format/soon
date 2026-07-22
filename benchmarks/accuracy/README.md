# SOON retrieval-accuracy benchmark

Measures how well LLMs answer questions about the same underlying data
when the data is presented in different serialization formats. Companion
to the size benchmark (`benchmarks/README.md`) and the deliverable for
issue #8.

## What it measures

- **Raw accuracy** per (model, format, dataset).
- **Accuracy per 1K prompt tokens** — the "money metric" that captures
  cost-effectiveness: how much correct information per dollar.
- **Per-mechanism ablation deltas** — labeled tuples, shape-reminder
  comments, row-count guardrail, ELIDE, REF. One row per mechanism
  turned on vs the plain SOON baseline.

Scoring is deterministic and type-aware (see `normalize.py`); no LLM
judge is involved. All providers use `temperature=0` for reproducibility.

## Formats compared

| Name | What it is |
|---|---|
| `json` | Compact JSON (baseline) |
| `yaml` | YAML |
| `toon` | TOON (requires `pip install toon-py`) |
| `gcf` | GCF (requires `cd playground && npm install`) |
| `soon` | SOON positional |
| `soon-labeled` | SOON with `mode="labeled"` |
| `soon-no-guardrail` | SOON with `row_count_guardrail=False` |
| `soon-shape-hint` | SOON with `shape_hint_rows=10` |
| `soon-elide` | SOON with `elide=True` |
| `soon-ref` | SOON with `ref=True` |

## Datasets

Reuses generators from `benchmarks/datasets.py`:

| Short | Description | Records | Depth | Questions |
|---|---|---|---|---|
| `L2` | Flat employee rows | 100 | 1 | ~35 |
| `L5` | Nested orders (customer + address + items) | 100 | 3 | ~50 |
| `L6` | Deeply nested org tree | ~30 | 5 | ~30 |
| `L7` | Event log with optional fields | 120 | 2 | ~35 |
| `L10` | Sparse API response (ELIDE showcase) | 100 | 1 | ~35 |
| `L11` | Shared-address employees (REF showcase) | 90 | 2 | ~45 |
| `L12` | Code graph — 500 symbols + 200 edges (GCF benchmark shape) | 500+200 | 1 | 43 |

**Total: 275 questions across 7 datasets.**

L12 is designed to replicate GCF's benchmark shape (flat symbol table
with distance grouping + edge list) so we can compare SOON against GCF
on their home turf.

## Setup

```bash
# 1. Install Python deps (from repo root):
pip install toon-py   # TOON format (optional, skipped if missing)

# 2. Install GCF encoder (from playground):
cd playground && npm install && cd ..

# 3. Copy and fill API keys:
cp .env.example .env
# Edit .env with your keys — you only need keys for providers you test
```

## Running

```bash
# Load .env (if using):
export $(grep -v '^#' .env | xargs)

# Plumbing test — mock provider, verifies pipeline scores 100%:
python3 benchmarks/accuracy/run.py --provider mock:fixture --dry-run

# Full mock run (no API cost):
python3 benchmarks/accuracy/run.py --provider mock:fixture

# Dry run against a real provider (10 questions, cheap):
python3 benchmarks/accuracy/run.py \
    --provider anthropic:claude-haiku-4-5-20251001 --dry-run

# Full single-provider run:
python3 benchmarks/accuracy/run.py \
    --provider anthropic:claude-haiku-4-5-20251001

# Multi-provider run:
python3 benchmarks/accuracy/run.py \
    --provider anthropic:claude-haiku-4-5-20251001 \
    --provider openai:gpt-4o-mini \
    --provider google:gemini-2.0-flash

# Subset of formats or datasets:
python3 benchmarks/accuracy/run.py \
    --provider anthropic:claude-haiku-4-5-20251001 \
    --format json --format gcf --format soon \
    --dataset L5 --dataset L12
```

Results land at `results/models/{model}.json`; the aggregated report is
`results/retrieval-accuracy.md`.

### Parallelism and rate limits

Requests run in parallel — a thread pool per provider, and providers run
concurrently with each other (their rate limits are independent). Default
workers: anthropic 6, openai 8, google 4. When any worker hits a 429 the
whole pool for that provider pauses with exponential backoff (5s → 60s),
so the harness adapts to whatever tier your key is on.

```bash
# Override worker counts ("N" for all, or "provider=N"):
python3 benchmarks/accuracy/run.py --provider openai:gpt-4o-mini --concurrency 4
python3 benchmarks/accuracy/run.py --provider google:gemini-2.0-flash --concurrency google=2

# Hard requests-per-minute cap (off by default; useful for free-tier quotas):
python3 benchmarks/accuracy/run.py --provider google:gemini-2.0-flash --rpm google=10
```

## Cost estimate

A full run: 275 questions × 10 formats × 1 model ≈ 2,750 API calls.

| Provider | Model | Approx. cost per full run |
|---|---|---|
| Anthropic | claude-haiku-4-5 | ~$1.00 |
| OpenAI | gpt-4o-mini | ~$0.40 |
| Google | gemini-2.0-flash | ~$0.25 |

Three providers: ~$1.65 total. A `--dry-run` (10 questions) costs < $0.01.

## Output

The report at `results/retrieval-accuracy.md` contains:

1. **Overall accuracy table** — rows: models, columns: formats
2. **Accuracy per 1K prompt tokens** — the efficiency metric
3. **Per-dataset breakdown** — which format wins on which data shape
4. **Ablation deltas** — which SOON mechanism helps/hurts on which model

## Adding formats

Add a `FormatSpec` to `PRIMERS` in `formats.py` and a renderer to the
`render()` function. The format will appear in all reports automatically.

## Adding datasets

1. Add a generator to `benchmarks/datasets.py`.
2. Add a question module under `benchmarks/accuracy/questions/`
   exposing `generate(data) -> list[Question]`.
3. Wire it into `benchmarks/accuracy/questions/__init__.py` and the
   `DATASETS` / `DATASET_ROOT_KEY` maps in `run.py`.

## Adding providers

Implement the `Provider` protocol from `providers/__init__.py`:
`complete(system, user) -> (text, usage)`. Register the `kind:` prefix
in `get_provider()`. All providers must use `temperature=0`.
