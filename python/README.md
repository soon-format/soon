# soon-format

**SOON (Shape-Oriented Object Notation)** — lossless, token-efficient encoding
of nested JSON for LLM prompts. Declares the shape of repeated objects once,
then streams only values: ~60% smaller than compact JSON on realistic nested
payloads, with a never-worse-than-JSON guarantee.

```bash
pip install soon-format            # library + `soon` CLI
pip install "soon-format[tokens]"  # + tiktoken-based cost decisions
```

```python
from soon_format import encode, decode, stats

doc = encode({"users": [{"id": 1, "name": "Ada"}, {"id": 2, "name": "Linus"}]})
print(doc)
# SHAPE users = {id,name}
# users[2]<users>:
# (1,Ada)
# (2,Linus)

assert decode(doc) == {"users": [{"id": 1, "name": "Ada"}, {"id": 2, "name": "Linus"}]}
print(stats({"users": [{"id": 1, "name": "Ada"}, {"id": 2, "name": "Linus"}]}))
```

CLI:

```bash
soon encode data.json --stats
soon decode doc.soon              # compact JSON to stdout
soon decode doc.soon --pretty     # indented JSON
soon check data.json              # round-trip verification
```

Docs, spec and the shared conformance suite:
https://github.com/soon-format/soon
