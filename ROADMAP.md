# SOON Roadmap

Improvements ordered by impact-per-effort, grounded in the v0.1 benchmark
findings (`benchmarks/README.md`). Each item states its goal, the evidence
behind it, and its definition of done.

---

## v0.2 — Prove accuracy, close the measured gaps

### 1. Retrieval-accuracy benchmark (highest priority)
Size is proven; accuracy is not — and it's the #1 criticism aimed at every
compact format. Build the harness: 200+ questions over L2/L5/L6/L7 datasets,
3-4 models, formats = JSON / TOON / SOON, metric = accuracy and
**acc%/1K-token efficiency score**. Include ablations: labeled mode on/off,
shape-reminder rows on/off, row-count guardrail on/off.
**Done when:** published table; if SOON accuracy trails JSON by >2pts on any
dataset, the losing mechanism is identified and fixed or gated.

### 2. Unquoted-string literals for the fallback path (steal TOON's L9 win)
Benchmark L9: TOON beat compact JSON by 12% on irregular data purely via
YAML-style unquoted keys/strings; SOON's fallback returned plain JSON (+0.1%).
Add a "relaxed literal" layer to non-tabular entries so irregular data also
benefits.
**Done when:** L9 ≥ +10% while all conformance/roundtrip/differential gates
stay green.

### 3. ELIDE — default-value elision
Real API payloads are 20-40% nulls/defaults. If ≥80% of a column shares one
value, drop the column into the header (`| defaults: status=active`), emit
exceptions per-row (`+status=cancelled`).
**Done when:** new L10 "sparse API response" dataset shows ≥15pt gain over
v0.1 SOON; spec + fixtures land first.

### 4. REF — repeated-subtree deduplication
Hash subtrees during encode; emit `REF &hq = (San Francisco,94105)` once,
reference thereafter. Only when net-positive; never for high-entropy values.
**Done when:** new L11 "shared-address employees" dataset shows the win;
ablation proves no accuracy regression (REF is the riskiest mechanism for
retrieval — measure before shipping as default).

### 5. Labeled mode (accuracy insurance)
`mode="labeled"`: `(id=1,(name=Ada,...))` for accuracy-critical use. Cheap to
implement, needed by the #1 harness as an ablation arm anyway.

## v0.3 — Token-true optimization

### 6. Tokenizer-aware encoding decisions
Today's cost model is characters; the bill is tokens. (a) Ship a small
bundled fallback vocab so `--tokenizer` works offline; (b) choose delimiter
(`,` vs `\t`) and quoting variants by measured token cost per document,
declared in the header; (c) add token-count columns to `benchmarks/run.py`
CI output.
**Done when:** token savings ≥ char savings on o200k/cl100k/Llama-3
tokenizers across L1-L9.

### 7. Adaptive block selection
`auto` currently decides per-array. Generalize to per-subtree: compare
table vs relaxed-literal vs compact JSON for every node, pick cheapest
(deterministically).
**Done when:** no dataset regresses; L7/L8 gain ≥5pts.

### 8. Streaming APIs
`encode_iter()` / `decode_iter()` for row-at-a-time processing of large
payloads; CLI gains `--stream`. Unlocks agent/tool-output middleware usage.

## v0.4 — Ecosystem

### 9. Integrations where the tokens actually burn
MCP server (`soon_compress` tool), LangChain/LlamaIndex document
transformers, a Vercel AI SDK middleware. One npm/pip install away from any
agent stack.

### 10. More ports via the conformance suite
Go and Rust (the suite makes ports verifiable from day one); Rust core could
later back a `soon-format[fast]` extra (current pure-Python encode is ~2ms
per 24KB — fine for prompts, too slow for log pipelines).

### 11. Developer surface
Playground web page (paste JSON → SOON + token deltas), syntax highlighting
(TextMate grammar → VS Code), `soon diff` for comparing encodings.

## Continuous (not versioned)

- **Fuzzing in CI**: nightly 10^5-document round-trip fuzz, failures frozen
  into `conformance/` automatically.
- **Real-world corpus**: replace synthetic L-datasets gradually with
  anonymized Stripe/GitHub/Shopify-shaped payloads; re-run TOON comparison
  against the official TypeScript encoder (current numbers use the
  `toon-py` port).
- **Spec RFC process**: every mechanism above lands as spec + fixtures
  before code (the v0.1 discipline that made the TS port land bug-free).

## Priority summary

| Priority | Item | Why |
|---|---|---|
| P0 | 1. Accuracy benchmark | Unproven accuracy blocks serious adoption |
| P0 | 2. Relaxed literals | Only measured loss vs TOON outside its niche |
| P1 | 3. ELIDE / 4. REF | Biggest remaining size wins on real payloads |
| P1 | 6. Tokenizer-aware | Bill is tokens, not chars |
| P2 | 7-11 | Growth: adaptivity, streaming, ecosystem |
