# SOON Benchmarks

Two tracks, both fully reproducible from fixed seeds:

1. **Size** (`run.py`) — SOON vs compact JSON, pretty JSON, YAML and TOON
   across nine datasets ordered from simple to hard (`datasets.py`).
2. **Speed** (`test_speed.py`) — encode/decode throughput via
   [pytest-benchmark](https://pypi.org/project/pytest-benchmark/), with
   stdlib `json.dumps` as the reference point.

```bash
# from the repo root
pip install pyyaml toon-py pytest-benchmark
PYTHONPATH=python/src python3 benchmarks/run.py                      # chars
PYTHONPATH=python/src python3 benchmarks/run.py --tokenizer o200k_base   # real tokens
PYTHONPATH=python/src:benchmarks python3 -m pytest benchmarks/test_speed.py -q
```

## Methodology

- Compact JSON (`separators=(",", ":")`) is the baseline; savings are
  `1 - size/json_size`, positive = smaller.
- TOON is produced by [`toon-py`](https://pypi.org/project/toon-py/), a
  Python port of the official `@byjohann/toon` implementation. Re-run with
  the official TypeScript encoder before quoting TOON numbers publicly.
- Character counts are the default; pass `--tokenizer` for tiktoken token
  counts (numbers below are characters — token savings track character
  savings closely but are not identical; measure on your tokenizer).
- Before any SOON number is reported, `run.py` asserts losslessness
  (`decode(encode(x)) == x`) and the never-worse guarantee
  (`len(soon) <= len(json)`), so the table cannot silently contain a
  broken encoding.

## Size results (characters, savings vs compact JSON)

| Dataset | json | yaml | toon | soon |
|---|---|---|---|---|
| L1 flat config | 113 | +11.5% | +12.4% | **+12.4%** |
| L2 flat table (100 uniform rows) | 6900 | +1.5% | **+59.0%** | +58.6% |
| L3 primitive arrays | 3057 | -25.7% | +6.4% | **+6.4%** |
| L4 nested small (10 orders, depth 3) | 2497 | -9.3% | -8.3% | **+56.6%** |
| L5 nested large (100 orders, depth 3) | 24254 | -9.2% | -9.7% | **+60.6%** |
| L6 deeply nested (tables in tables, depth 5) | 5660 | -36.3% | -198.6% | **+56.2%** |
| L7 semi-uniform (event log, optionals) | 9801 | -1.5% | -22.3% | **+44.0%** |
| L8 mixed kinds | 2950 | -6.5% | -25.2% | **+39.5%** |
| L9 adversarial (worst case) | 1412 | -42.1% | **+12.3%** | +0.1% |

Reading of the results, including where SOON loses:

- **Flat tables (L2) are TOON's home turf and TOON wins it** — by 0.4pt.
  Use TOON or CSV there; SOON is effectively tied.
- **Nested data (L4-L8) is the entire point of SOON**: +40 to +61% while
  TOON and YAML are *negative* (TOON -199% on deep nesting — its list form
  expands nested structures beyond compact JSON).
- **Adversarial irregular data (L9)**: SOON's never-worse guarantee kicks
  in and returns ~compact JSON (+0.1%). TOON's YAML-like unquoted syntax
  actually beats JSON by 12% here — an idea worth stealing for SOON v0.2.

## Speed results (Python 3.10, pure Python, L5 = 24 KB JSON)

| Operation | Mean | Throughput |
|---|---|---|
| `json.dumps` (C-accelerated, baseline) | 0.19 ms | 5211 ops/s |
| `soon.encode` L5 | 2.32 ms | 430 ops/s |
| `soon.decode` L5 | 2.10 ms | 476 ops/s |

Encoding a 24 KB payload costs ~2 ms — noise next to any LLM call it
precedes. Run `test_speed.py` on your machine for local numbers.

## Not covered yet

**Retrieval accuracy** (does the model answer as well from SOON as from
JSON?) requires LLM API calls and is planned as the v0.2 harness with
ablations (labeled mode on/off, shape-reminder rows on/off). Until that
lands, treat SOON as size-proven but accuracy-unproven on your task:
benchmark before production use.
