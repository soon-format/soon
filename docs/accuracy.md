# Retrieval accuracy

**How well do LLMs answer questions about the same data when it's rendered
as JSON, YAML, TOON, or SOON?** This page publishes the measured numbers.

Companion to the [size benchmark](../benchmarks/results.md), which shows
SOON is 40–60% smaller than JSON on nested payloads. This one answers
the *other* question every serious adopter asks: does that saving come
at the cost of retrieval quality?

## Methodology

- **Datasets.** L2 (flat table), L5 (nested orders), L6 (deeply nested
  org tree), L7 (event log with optional fields), L10 (sparse API
  response — the ELIDE showcase), L11 (shared-address employees — the
  REF showcase). Same seeded generators the size benchmark uses.
- **Questions.** 232 pairs, all programmatic. Types: field retrieval,
  nested path traversal, aggregation, cardinality, filter+select,
  existence. Ground truth is computed from the seeded data, so
  questions and answers can't drift. Full generators live under
  [`benchmarks/accuracy/questions/`](../benchmarks/accuracy/questions/).
- **Formats.** JSON (compact), YAML, TOON, SOON (positional), and one
  SOON variant per ablation arm: `labeled`, `no-guardrail`, `shape-hint`,
  `elide`, `ref`.
- **Models.** Three current-generation tiers, one per major provider.
  The default set in the workflow is `openai:gpt-5-nano`,
  `anthropic:claude-haiku-4-5-20251001`, `google:gemini-3-flash-preview`.
  Providers and model ids are CLI-configurable — third parties can drop
  in whatever they want to test.
- **Scoring.** Deterministic and type-aware. Integers strip currency
  and commas; numbers use `math.isclose` with 1e-6 tolerance; booleans
  accept yes/no/true/false/y/n/1/0; strings are case-insensitive; lists
  compare ordered or unordered based on the question. No LLM judge —
  the scorer is exactly the [`normalize.py`](../benchmarks/accuracy/normalize.py)
  Python module used at evaluation time.
- **Cost metric.** The "money metric" is *accuracy per 1K prompt
  tokens*. Bare accuracy without cost is easy: give the model 5× the
  context and it wins on retrieval but loses on your bill. The per-1K
  figure captures both.

## How to reproduce

```bash
# Cheap plumbing check (mock provider, ~1 second):
python3 benchmarks/accuracy/run.py --provider mock:fixture

# Real run against one model (10-question dry run first is cheap):
export OPENAI_API_KEY=...
python3 benchmarks/accuracy/run.py --provider openai:gpt-5-nano --dry-run
python3 benchmarks/accuracy/run.py --provider openai:gpt-5-nano

# Full three-tier reference run:
python3 benchmarks/accuracy/run.py \
    --provider openai:gpt-5-nano \
    --provider anthropic:claude-haiku-4-5-20251001 \
    --provider google:gemini-3-flash-preview
```

Per-model raw results land at `benchmarks/accuracy/results/models/{model}.json`.
The aggregated markdown that this page mirrors lives at
`benchmarks/accuracy/results/retrieval-accuracy.md`.

## Cost estimate

A full run of 232 questions × 8 formats × 3 models is ≈ 5,600 calls.
At current API prices (Q2 2026, approximate):

| Provider tier | Approx. cost per full run |
|---|---|
| `openai:gpt-5-nano` | $0.30 |
| `anthropic:claude-haiku-4-5` | $0.80 |
| `google:gemini-3-flash-preview` | $0.20 |

## Results

_Results tables are appended by
[`.github/workflows/accuracy.yml`](../.github/workflows/accuracy.yml)
whenever the `Retrieval accuracy` workflow's `workflow_dispatch` job
finishes a real-provider run. Until the first run lands, the report at
`benchmarks/accuracy/results/retrieval-accuracy.md` is the authoritative
source and gets copied here._

<!-- results:begin -->
_No published results yet. Trigger the workflow, or run the harness
locally and paste the generated table above this comment._
<!-- results:end -->

## What we do when a format loses

Acceptance gate (from issue #8):

> If SOON accuracy trails JSON by >2 pts on any dataset, the losing
> mechanism is identified and either fixed or gated behind an opt-in
> encoder option.

The ablation table above is the primary tool for this triage: each row
compares one SOON mechanism against the plain-SOON baseline. A negative
delta on a given (model, mechanism) cell tells us the arm hurt
retrieval; combined with the per-dataset breakdown it identifies which
kind of payload it hurt on. Any mechanism that consistently regresses
either gets fixed or moved behind a non-default flag before we
recommend it.
