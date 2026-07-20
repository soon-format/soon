# SOON — Spec & Conformance Hub

This is the **specification and conformance** repository. It does NOT contain any library code.

## Multi-repo architecture

SOON uses a multi-repo structure. Know which repo to touch:

| Change type | Repo |
|---|---|
| Spec changes, new encoding mechanisms | **This repo** (`soon-format/soon`) |
| New conformance fixtures | **This repo** |
| Benchmarks, accuracy harness | **This repo** |
| TypeScript/JS library code, TS tests, npm package | `soon-format/soon-typescript` (sibling: `../soon-typescript/`) |
| Python library code, Python tests, PyPI package | `soon-format/soon-python` (sibling: `../soon-python/`) |
| Cross-language consistency issues | **This repo** (matrix test), then fix in the relevant impl repo |

## Workflow for new features

1. **Spec first**: update `SPEC.md` with the new mechanism
2. **Fixtures second**: add conformance fixtures to `conformance/` (encode, decode, roundtrip, errors)
3. **Implement**: make changes in `soon-typescript` and/or `soon-python` — they pull fixtures via git submodule (`spec/`)
4. **Verify**: run `python3 tests/cross-language-matrix.py` from this repo to confirm cross-language agreement

## What lives here

- `SPEC.md` — normative format specification
- `conformance/` — language-agnostic JSON fixtures (encode/, decode/, roundtrip/, errors/)
- `benchmarks/` — size, speed, and accuracy benchmarks (Python-based)
- `tests/cross-language-matrix.py` — NxN encoder×decoder verification across all implementations
- `tests/conformance-coverage.py` — fixture coverage reporter
- `tools/differential.py` — quick encode-only cross-language check
- `docs/`, `ROADMAP.md` — documentation and roadmap

## Commands

```bash
# Cross-language matrix test (requires sibling repos installed)
python3 tests/cross-language-matrix.py

# Quick differential check
python3 tools/differential.py

# Conformance coverage report
python3 tests/conformance-coverage.py

# Benchmarks (requires: pip install -e ../soon-python[dev])
python3 benchmarks/run.py
```

## Conventions

- Conventional Commits with scopes: `spec`, `conformance`, `bench`, `ci`
- Every new mechanism: spec change → fixtures → implementation (never code without fixtures)
- Conformance fixtures are the contract — if a fixture says X, every implementation must produce X byte-for-byte
