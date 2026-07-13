# SOON — Shape-Oriented Object Notation

**Lossless, token-efficient encoding of nested JSON for LLM prompts.**

LLM tokens cost money, and nested JSON wastes most of them repeating the same
keys on every object. SOON declares the *shape* of repeated objects once, then
streams only the values — cutting **~60% of characters on realistic nested
payloads** while staying fully lossless and human-readable.

```bash
echo '{"orders":[...]}' | npx @soon-format/cli encode -      # Node
pip install soon-format && soon encode data.json --stats     # Python
```

## The 10-second pitch

This JSON (205 chars):

```json
{"orders":[
  {"id":1,"customer":{"name":"Ada","address":{"city":"Boulder"}},"items":[{"sku":"A1","qty":2}]},
  {"id":2,"customer":{"name":"Linus","address":{"city":"Helsinki"}},"items":[{"sku":"B2","qty":1}]}]}
```

becomes this SOON (148 chars — and savings *grow* with row count):

```
SHAPE orders = {id,customer:{name,address:{city}},items:[{sku,qty}]}
orders[2]<orders>:
(1,(Ada,(Boulder)),[(A1,2)])
(2,(Linus,(Helsinki)),[(B2,1)])
```

Keys appear **once**, in the `SHAPE` declaration. Rows are positional tuples.
`[N]` element counts and field headers stay in place as guardrails the model
can verify. On a realistic 50-order nested payload this measures **60.4%
smaller** than compact JSON (11,456 → 4,532 chars).

## Why not TOON / CSV / YAML?

[TOON](https://github.com/toon-format/toon) pioneered token-oriented encoding,
but its tabular layout only works for **flat** uniform arrays — on nested data
it degrades to a YAML-like list form and loses its advantage. CSV cannot
represent nesting at all. SOON's shape/tuple mechanism is recursive by design:
nested objects become nested tuples, nested arrays of objects become lists of
tuples, and irregularity is absorbed with three tools — optional fields (`?` /
`_`), a raw-JSON escape hatch (`!`), and per-array cost checks.

**The never-worse guarantee:** in `auto` mode the encoder compares its output
against compact JSON and returns whichever is smaller. SOON output is never
larger than compact JSON.

## Usage

**Python**

```python
from soon_format import encode, decode, stats

doc = encode(data)                      # auto mode, never-worse guarantee
data == decode(doc)                     # True — lossless
stats(data)                             # {"json_chars": ..., "soon_chars": ..., "saving": ...}
encode(data, tokenizer="o200k_base")    # real-token cost decisions (pip install soon-format[tokens])
```

**TypeScript / JavaScript**

```ts
import { encode, decode, stats } from "@soon-format/soon";

const doc = encode(data);               // same semantics, same bytes
decode(doc);                            // original value
```

**CLI (both ecosystems)**

```bash
npx @soon-format/cli encode data.json --stats
uvx soon-format encode data.json       # or: pipx run soon-format
soon decode doc.soon                   # back to JSON
soon check data.json                   # round-trip verification (CI-friendly)
```

**Prompting:** tell the model once, e.g. *"Data is in SOON format: `SHAPE`
declares field names; each row is a tuple of values in shape order; `_` means
the field is absent."*

## When NOT to use SOON

- **Flat tabular data** — CSV is smaller; TOON is also excellent there.
- **Tiny or deeply irregular payloads** — `auto` mode will just hand you
  compact JSON (that's the guarantee working as intended).
- **Retrieval-accuracy-critical tasks** — positional values are denser than
  key-value pairs; benchmark on your task before committing. An accuracy
  benchmark harness is planned for v0.2.

## Repository layout

| Path | What |
|---|---|
| [`SPEC.md`](SPEC.md) | Normative format specification (v0.1) |
| [`conformance/`](conformance/) | Language-agnostic fixture suite — the contract both implementations must pass |
| [`python/`](python/) | `soon-format` on PyPI (reference implementation) |
| [`ts/packages/soon`](ts/packages/soon) | `@soon-format/soon` on npm |
| [`ts/packages/cli`](ts/packages/cli) | `@soon-format/cli` on npm (`npx`-runnable) |
| [`tools/`](tools/) | Fixture generator, cross-implementation differential test |

Both implementations pass the same 41 conformance fixtures byte-for-byte,
plus property-based round-trip tests (`decode(encode(x)) == x`, hypothesis /
seeded fuzzing) and a differential CI job that byte-compares encoder outputs.

## Roadmap

- **v0.2:** REF (repeated-subtree dedup), ELIDE (default-value elision),
  shape variants, retrieval-accuracy benchmark vs JSON/TOON/YAML.
- **v0.3:** tokenizer-aware delimiter selection, streaming APIs.

## Contributing

See [CONTRIBUTING.md](CONTRIBUTING.md). Spec first, fixtures are the
contract, zero runtime deps. New language ports are very welcome — the
conformance suite makes them verifiable from day one.

## License

[MIT](LICENSE) © Yasin Ughur
