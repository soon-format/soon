# Contributing to SOON

Thanks for your interest! This repo hosts the SOON spec, the shared conformance
suite, and two implementations (Python and TypeScript).

## Ground rules

1. **Spec first.** No mechanism lands in code before it lands in `SPEC.md` and
   the conformance suite. A fixture change requires the corresponding spec
   change in the same PR.
2. **Fixtures are the contract.** Both implementations must pass 100% of
   `conformance/`. If you find a divergence between implementations, freeze the
   failing input as a fixture before fixing it.
3. **Zero runtime dependencies** in the core libraries. Tokenizer support stays
   behind optional extras.
4. **Conventional Commits** (`feat:`, `fix:`, `docs:`, `test:`, `ci:`, `chore:`)
   with scopes `python`, `ts`, `spec`, `conformance` where relevant.

## Development

### Python

```bash
cd python
pip install -e ".[dev,tokens]"
pytest
ruff check src tests
mypy src
```

### TypeScript

```bash
npm install
npm run build --workspaces
npm test --workspaces --if-present
```

## Cross-implementation notes

- JavaScript has a single `number` type. Fixtures avoid non-integral floats
  with a `.0` suffix (e.g. `2.0`) and integers beyond 2^53 so both
  implementations produce byte-identical output.
- JavaScript objects reorder integer-like string keys; fixtures avoid such keys.

## Reporting bugs / proposing spec changes

Open an issue. Spec changes go through an RFC-labelled issue before a PR.
Security issues: see [SECURITY.md](SECURITY.md).
