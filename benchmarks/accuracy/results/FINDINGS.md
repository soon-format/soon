# Retrieval-accuracy findings — 2026-07-22 run

Full run of the accuracy harness: **275 questions × 10 formats × 2 models = 5,500
API calls**, zero API errors. Models: `anthropic:claude-haiku-4-5-20251001` and
`openai:gpt-4o-mini`, both at `temperature=0`. A `google:gemini-3.5-flash` run was
started but aborted (free-tier quota made it ~20× slower); it is not included.

Raw per-call data: `models/*.json`. Aggregated tables: `retrieval-accuracy.md`.

## Headline

**Compact formats cost no meaningful comprehension.** SOON, TOON, and GCF are
understood roughly as well as JSON by both models — most overall-accuracy
differences fall within the ±3 pp sampling noise of a 275-question cell — while
using 40–60% fewer tokens. On the accuracy-per-1K-prompt-tokens metric, SOON
delivers ~1.7–1.8× JSON on both models.

| Overall accuracy (%) | gcf | json | soon | toon | yaml |
|---|---|---|---|---|---|
| claude-haiku-4.5 | 73.1 | 74.2 | 73.1 | **75.3** | 72.0 |
| gpt-4o-mini | 69.1 | 68.7 | **70.9** | 69.8 | 64.4 |

| Accuracy / 1K prompt tokens | gcf | json | soon | toon | yaml |
|---|---|---|---|---|---|
| claude-haiku-4.5 | 0.163 | 0.103 | 0.173 | 0.125 | 0.088 |
| gpt-4o-mini | 0.170 | 0.107 | 0.196 | 0.130 | 0.086 |

## Notable results

1. **`soon-ref` craters on the smaller model.** GPT-4o-mini: 62.5% overall
   (−8.4 pp vs plain SOON), and on L11 (shared-address, the REF showcase) it
   scores 60.8% vs 84.3% for plain SOON. Haiku handles refs fine (86.3% on L11).
   The reference-following indirection appears to exceed what a small model can
   do reliably.

2. **SOON mechanisms are neutral-to-positive on Haiku, neutral-to-negative on
   GPT-4o-mini.** Ablation deltas vs plain SOON:

   | model | labeled | shape-hint | no-guardrail | elide | ref |
   |---|---|---|---|---|---|
   | claude-haiku-4.5 | +1.1 | +0.7 | −0.4 | +0.0 | −1.1 |
   | gpt-4o-mini | −3.6 | −0.7 | −1.8 | −1.1 | −8.4 |

   Plain SOON is the safest cross-model default.

3. **L2 flat table is SOON's weakest dataset on Haiku**: 58.6% vs 72.4% for
   JSON. This is the shape the new compact-flat-rows encoding (inline schema +
   bare tuples) targets — worth a per-question look before assuming the
   encoding is at fault, but it is the only dataset where JSON beats SOON by
   more than noise.

4. **TOON's wins concentrate where its explicit tabular headers apply.** Haiku
   L7 (semi-uniform events): TOON 82.4 vs SOON 70.6. Haiku L5: TOON 81.0 vs
   SOON 73.8.

5. **L12 (code graph) is hard for every format and both models** (21–30%
   everywhere). Format choice doesn't move it; the difficulty is the multi-hop
   graph task itself, not the encoding.

6. **YAML is the worst format on both models** — worst overall accuracy on
   GPT-4o-mini (64.4%) and worst tokens-per-correct-answer on both.

Caveat: compare formats within a model row, not across models — GPT-4o-mini is
simply weaker at this task in every format.

## Reproduce

```bash
export $(grep -v '^#' .env | xargs)
python3 benchmarks/accuracy/run.py \
    --provider anthropic:claude-haiku-4-5-20251001 \
    --provider openai:gpt-4o-mini
```

Runs are parallel (per-provider worker pools + adaptive 429 backoff); the two
models above complete in ~10 and ~25 minutes respectively depending on API tier.
