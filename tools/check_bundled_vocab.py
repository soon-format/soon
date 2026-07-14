#!/usr/bin/env python3
"""Drift check for bundled BPE vocabularies.

For every encoding registered in ``soon_format.tokencost._BUNDLED``, this
tool loads (a) the offline encoder we build from the bundled ``.tiktoken.gz``
file and the pat_str / special_tokens definitions in ``tokencost.py``, and
(b) the reference encoder ``tiktoken`` builds from
``tiktoken_ext.openai_public``. It then asserts that:

  * ``pat_str`` is byte-identical
  * ``special_tokens`` is identical
  * ``mergeable_ranks`` is identical (same 200 000-entry mapping)
  * tokenization of a fixed corpus produces identical token ids

Any drift here means our bundled artefact is silently disagreeing with the
tokenizer OpenAI's client library uses, which would give users token counts
that don't match what an actual inference call bills. This is not caught by
runtime code because ``tiktoken`` is not a runtime dependency of
``soon-format`` — this tool exists precisely to fail loudly in CI when the
bundle needs regenerating.

Usage (from repo root, with dev deps installed):

    PYTHONPATH=python/src python3 tools/check_bundled_vocab.py

Exits 0 on parity, 1 (with a specific diff summary) on any drift.
"""

from __future__ import annotations

import sys
from pathlib import Path
from typing import Any, Callable

ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT / "python" / "src"))

from soon_format.tokencost import _BUNDLED, _build_encoder  # noqa: E402

_UPSTREAM_FACTORIES: dict[str, Callable[[], dict[str, Any]]] = {}


def _register_upstream_factories() -> None:
    """Look up the upstream ``tiktoken_ext.openai_public`` config factories.

    Kept in its own function so an ImportError from a stale tiktoken install
    (missing an encoding we bundled) becomes a clear message instead of a
    top-level module-load traceback.
    """
    try:
        from tiktoken_ext import openai_public  # type: ignore[import-untyped]
    except ImportError as exc:  # pragma: no cover
        raise SystemExit(
            "check_bundled_vocab requires tiktoken; install with: "
            "pip install 'soon-format[dev]'"
        ) from exc
    for name in _BUNDLED:
        factory = getattr(openai_public, name, None)
        if factory is None:
            raise SystemExit(
                f"tiktoken_ext.openai_public has no factory named {name!r}; "
                "either the encoding was renamed upstream or our _BUNDLED "
                "registry lists an encoding tiktoken doesn't ship."
            )
        _UPSTREAM_FACTORIES[name] = factory


# Sample corpus tokenized under both encoders; a mismatch here is the only
# real way to catch drift that isn't visible in pat_str / special_tokens
# (e.g. a rank reshuffle that leaves the top-level knobs unchanged).
_CORPUS: list[str] = [
    "",
    "Hello, world!",
    '{"users":[{"id":1,"name":"Ada"}]}',
    "🌟 emoji test 🔥",
    "multi\nline\ntext with\ttabs",
    "SHAPE hikes = {id,name,km,sunny}\n(1,Blue Lake Trail,7.5,true)",
    "".join(chr(c) for c in range(32, 127)),  # printable ASCII
    "こんにちは、世界",
    "\r\n\t   \n\n",
]


def _diff_mappings(
    ours: dict[Any, Any], theirs: dict[Any, Any], label: str
) -> list[str]:
    problems: list[str] = []
    missing = theirs.keys() - ours.keys()
    extra = ours.keys() - theirs.keys()
    if missing:
        problems.append(
            f"{label}: {len(missing)} entries present upstream but missing in bundle "
            f"(e.g. {sorted(repr(k) for k in list(missing)[:3])})"
        )
    if extra:
        problems.append(
            f"{label}: {len(extra)} entries present in bundle but not upstream "
            f"(e.g. {sorted(repr(k) for k in list(extra)[:3])})"
        )
    mismatched = [k for k in ours.keys() & theirs.keys() if ours[k] != theirs[k]]
    if mismatched:
        problems.append(
            f"{label}: {len(mismatched)} entries with different values "
            f"(e.g. {[(repr(k), ours[k], theirs[k]) for k in mismatched[:3]]})"
        )
    return problems


def _check(name: str) -> list[str]:
    problems: list[str] = []
    upstream_cfg = _UPSTREAM_FACTORIES[name]()
    bundled_cfg = _BUNDLED[name]

    if upstream_cfg["pat_str"] != bundled_cfg["pat_str"]:
        problems.append(
            f"{name}: pat_str drift. "
            f"upstream={upstream_cfg['pat_str']!r} bundled={bundled_cfg['pat_str']!r}"
        )
    if upstream_cfg["special_tokens"] != bundled_cfg["special_tokens"]:
        problems.append(
            f"{name}: special_tokens drift. "
            f"upstream={upstream_cfg['special_tokens']!r} "
            f"bundled={bundled_cfg['special_tokens']!r}"
        )

    offline = _build_encoder(name)
    # Force upstream to actually resolve mergeable_ranks (which may hit the
    # network on a cold tiktoken cache; that's fine — this is a dev tool).
    import tiktoken  # noqa: F401

    online = _build_online_encoder(upstream_cfg, name)

    problems.extend(
        _diff_mappings(
            offline._mergeable_ranks,  # type: ignore[attr-defined]
            online._mergeable_ranks,  # type: ignore[attr-defined]
            f"{name}: mergeable_ranks",
        )
    )

    mismatches = [s for s in _CORPUS if offline.encode(s) != online.encode(s)]
    if mismatches:
        problems.append(
            f"{name}: {len(mismatches)} corpus sample(s) tokenize differently "
            f"(first: {mismatches[0]!r})"
        )
    return problems


def _build_online_encoder(cfg: dict[str, Any], name: str) -> Any:
    """Build a tiktoken Encoding directly from the upstream factory config.

    We avoid ``tiktoken.get_encoding`` because it goes through a caching
    layer keyed by name; here we want the freshest upstream ranks.
    """
    import tiktoken

    ranks = cfg["mergeable_ranks"]
    if isinstance(ranks, str):
        # Some factories return a URL / cache-key placeholder; fall back to
        # the public API in that case (which resolves it).
        return tiktoken.get_encoding(name)
    return tiktoken.Encoding(
        name=name,
        pat_str=cfg["pat_str"],
        mergeable_ranks=ranks,
        special_tokens=cfg["special_tokens"],
    )


def main() -> int:
    _register_upstream_factories()
    all_problems: list[str] = []
    for name in sorted(_BUNDLED):
        print(f"checking {name} ...", file=sys.stderr)
        all_problems.extend(_check(name))
    if all_problems:
        print("BUNDLED VOCAB DRIFT DETECTED:", file=sys.stderr)
        for p in all_problems:
            print(f"  - {p}", file=sys.stderr)
        print(
            "\nregenerate the bundled artefacts and update pat_str / special_tokens "
            "in python/src/soon_format/tokencost.py to match tiktoken_ext.openai_public.",
            file=sys.stderr,
        )
        return 1
    print("bundled vocab matches upstream tiktoken_ext.openai_public.", file=sys.stderr)
    return 0


if __name__ == "__main__":
    sys.exit(main())
