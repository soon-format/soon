# SOON — Spec & Conformance Hub

This is the **main specification repo** for SOON (Structured Output Object Notation).

## Multi-repo architecture

| Change type | Repo |
|---|---|
| Spec changes, conformance fixtures, benchmarks, playground | **This repo** (`soon-format/soon`) |
| Python library code, Python tests, PyPI package | `soon-format/soon-python` (sibling: `../soon-python/`) |
| TypeScript/JS library code, TS tests, npm package | `soon-format/soon-typescript` (sibling: `../soon-typescript/`) |

## Authorship

- NEVER include `Co-Authored-By` or any Claude/AI attribution in commit messages
- NEVER mention Claude, AI, or any AI assistant in PR titles, PR descriptions, or PR comments
- All commits and PRs should read as if written entirely by the human developer

## Conventions

- Conventional Commits: `feat:`, `fix:`, `docs:`, `test:`, `ci:`, `chore:` with scopes `spec`, `conformance`, `python`, `ts` where relevant
- Spec first — no mechanism lands in code before it lands in `SPEC.md` and the conformance suite
- Fixtures are the contract — both implementations must pass 100% of `conformance/`
