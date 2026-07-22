# Retrieval accuracy

Deterministic, type-aware scoring. See `benchmarks/accuracy/README.md` for methodology.

## Overall accuracy (%)

| model | gcf | json | soon | soon-elide | soon-labeled | soon-no-guardrail | soon-ref | soon-shape-hint | toon | yaml |
|---|---|---|---|---|---|---|---|---|---|---|
| anthropic:claude-haiku-4-5-20251001 | 73.1 | 74.2 | 73.1 | 73.1 | 74.2 | 72.7 | 72.0 | 73.8 | 75.3 | 72.0 |
| openai:gpt-4o-mini | 69.1 | 68.7 | 70.9 | 69.8 | 67.3 | 69.1 | 62.5 | 70.2 | 69.8 | 64.4 |

## Accuracy per 1K prompt tokens

Higher is better — the "money metric" (accuracy per dollar).

| model | gcf | json | soon | soon-elide | soon-labeled | soon-no-guardrail | soon-ref | soon-shape-hint | toon | yaml |
|---|---|---|---|---|---|---|---|---|---|---|
| anthropic:claude-haiku-4-5-20251001 | 0.163 | 0.103 | 0.173 | 0.170 | 0.103 | 0.162 | 0.180 | 0.151 | 0.125 | 0.088 |
| openai:gpt-4o-mini | 0.170 | 0.107 | 0.196 | 0.198 | 0.108 | 0.188 | 0.184 | 0.174 | 0.130 | 0.086 |

## Per-dataset accuracy (%)

### L10

| model | gcf | json | soon | soon-elide | soon-labeled | soon-no-guardrail | soon-ref | soon-shape-hint | toon | yaml |
|---|---|---|---|---|---|---|---|---|---|---|
| anthropic:claude-haiku-4-5-20251001 | 91.3 | 93.5 | 93.5 | 95.7 | 93.5 | 91.3 | 91.3 | 91.3 | 89.1 | 91.3 |
| openai:gpt-4o-mini | 89.1 | 89.1 | 89.1 | 89.1 | 89.1 | 87.0 | 87.0 | 89.1 | 87.0 | 91.3 |

### L11

| model | gcf | json | soon | soon-elide | soon-labeled | soon-no-guardrail | soon-ref | soon-shape-hint | toon | yaml |
|---|---|---|---|---|---|---|---|---|---|---|
| anthropic:claude-haiku-4-5-20251001 | 90.2 | 88.2 | 86.3 | 86.3 | 88.2 | 86.3 | 86.3 | 88.2 | 90.2 | 88.2 |
| openai:gpt-4o-mini | 82.4 | 86.3 | 84.3 | 84.3 | 84.3 | 86.3 | 60.8 | 82.4 | 88.2 | 68.6 |

### L12

| model | gcf | json | soon | soon-elide | soon-labeled | soon-no-guardrail | soon-ref | soon-shape-hint | toon | yaml |
|---|---|---|---|---|---|---|---|---|---|---|
| anthropic:claude-haiku-4-5-20251001 | 25.6 | 25.6 | 30.2 | 25.6 | 23.3 | 25.6 | 30.2 | 27.9 | 25.6 | 20.9 |
| openai:gpt-4o-mini | 27.9 | 25.6 | 25.6 | 23.3 | 25.6 | 23.3 | 27.9 | 20.9 | 30.2 | 23.3 |

### L2

| model | gcf | json | soon | soon-elide | soon-labeled | soon-no-guardrail | soon-ref | soon-shape-hint | toon | yaml |
|---|---|---|---|---|---|---|---|---|---|---|
| anthropic:claude-haiku-4-5-20251001 | 62.1 | 72.4 | 58.6 | 58.6 | 65.5 | 58.6 | 58.6 | 62.1 | 58.6 | 58.6 |
| openai:gpt-4o-mini | 65.5 | 58.6 | 62.1 | 62.1 | 58.6 | 65.5 | 62.1 | 62.1 | 62.1 | 58.6 |

### L5

| model | gcf | json | soon | soon-elide | soon-labeled | soon-no-guardrail | soon-ref | soon-shape-hint | toon | yaml |
|---|---|---|---|---|---|---|---|---|---|---|
| anthropic:claude-haiku-4-5-20251001 | 76.2 | 71.4 | 73.8 | 73.8 | 73.8 | 71.4 | 71.4 | 78.6 | 81.0 | 73.8 |
| openai:gpt-4o-mini | 69.0 | 71.4 | 76.2 | 76.2 | 64.3 | 76.2 | 71.4 | 76.2 | 73.8 | 71.4 |

### L6

| model | gcf | json | soon | soon-elide | soon-labeled | soon-no-guardrail | soon-ref | soon-shape-hint | toon | yaml |
|---|---|---|---|---|---|---|---|---|---|---|
| anthropic:claude-haiku-4-5-20251001 | 100.0 | 96.7 | 96.7 | 93.3 | 96.7 | 100.0 | 93.3 | 93.3 | 100.0 | 93.3 |
| openai:gpt-4o-mini | 93.3 | 83.3 | 86.7 | 80.0 | 86.7 | 80.0 | 76.7 | 80.0 | 93.3 | 80.0 |

### L7

| model | gcf | json | soon | soon-elide | soon-labeled | soon-no-guardrail | soon-ref | soon-shape-hint | toon | yaml |
|---|---|---|---|---|---|---|---|---|---|---|
| anthropic:claude-haiku-4-5-20251001 | 64.7 | 73.5 | 70.6 | 76.5 | 79.4 | 76.5 | 70.6 | 73.5 | 82.4 | 76.5 |
| openai:gpt-4o-mini | 55.9 | 61.8 | 70.6 | 70.6 | 58.8 | 61.8 | 52.9 | 79.4 | 50.0 | 55.9 |

## Ablation deltas (%)

Accuracy delta when the named mechanism is ON vs the plain SOON baseline. Positive = mechanism helps.

| model | labeled | shape-hint | no-guardrail | elide | ref |
|---|---|---|---|---|---|
| anthropic:claude-haiku-4-5-20251001 | +1.1 | +0.7 | -0.4 | +0.0 | -1.1 |
| openai:gpt-4o-mini | -3.6 | -0.7 | -1.8 | -1.1 | -8.4 |
