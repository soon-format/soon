"""Cost measurement: characters by default, real tokens via tiktoken (optional).

Tokenizers are loaded from BPE artefacts bundled inside the wheel — no network
access is required at any point, and there is no fall-through path that could
hit the network. ``tiktoken`` is still the BPE engine; it just never has to
download. Encoding names outside the bundled set raise :class:`SoonError`
rather than silently reaching for :func:`tiktoken.get_encoding` — this keeps
Python behaviour aligned with the TypeScript side, where the analogue is
:func:`getEncoder` throwing on unknown names.
"""

from __future__ import annotations

import base64
import gzip
from importlib import resources
from typing import Any

from .errors import SoonError

# Registry of encodings whose BPE file we ship inside the wheel. The pat_str /
# special-tokens definitions are copied verbatim from tiktoken_ext.openai_public
# to keep offline output byte-identical to what tiktoken.get_encoding() would
# have produced online. ``tools/check_bundled_vocab.py`` guards against drift.
_O200K_PAT = "|".join(
    [
        r"""[^\r\n\p{L}\p{N}]?[\p{Lu}\p{Lt}\p{Lm}\p{Lo}\p{M}]*[\p{Ll}\p{Lm}\p{Lo}\p{M}]+(?i:'s|'t|'re|'ve|'m|'ll|'d)?""",
        r"""[^\r\n\p{L}\p{N}]?[\p{Lu}\p{Lt}\p{Lm}\p{Lo}\p{M}]+[\p{Ll}\p{Lm}\p{Lo}\p{M}]*(?i:'s|'t|'re|'ve|'m|'ll|'d)?""",
        r"""\p{N}{1,3}""",
        r""" ?[^\s\p{L}\p{N}]+[\r\n/]*""",
        r"""\s*[\r\n]+""",
        r"""\s+(?!\S)""",
        r"""\s+""",
    ]
)

_BUNDLED: dict[str, dict[str, Any]] = {
    "o200k_base": {
        "file": "o200k_base.tiktoken.gz",
        "pat_str": _O200K_PAT,
        "special_tokens": {"<|endoftext|>": 199999, "<|endofprompt|>": 200018},
    },
}


def _require_tiktoken() -> Any:
    """Return the ``tiktoken`` module, or raise a :class:`SoonError` with a
    single, canonical install hint. Kept as one function so the message
    never drifts between call sites."""
    try:
        import tiktoken
    except ImportError as exc:  # pragma: no cover
        raise SoonError(
            "tokenizer support requires tiktoken; install with: "
            "pip install 'soon-format[tokens]'"
        ) from exc
    return tiktoken


def _load_bundled_ranks(filename: str) -> dict[bytes, int]:
    """Parse a gzipped .tiktoken file into a mergeable_ranks mapping."""
    with resources.files("soon_format.vocab").joinpath(filename).open("rb") as raw:
        with gzip.open(raw, "rb") as fh:
            ranks: dict[bytes, int] = {}
            for line in fh:
                b64, rank = line.split()
                ranks[base64.b64decode(b64)] = int(rank)
            return ranks


def _build_encoder(name: str) -> Any:
    cfg = _BUNDLED[name]
    tiktoken = _require_tiktoken()
    return tiktoken.Encoding(
        name=name,
        pat_str=cfg["pat_str"],
        mergeable_ranks=_load_bundled_ranks(cfg["file"]),
        special_tokens=cfg["special_tokens"],
    )


# Encoders are pure-function tokenizers keyed by name; cache to avoid rebuilding
# the ~200k-entry rank table on every encode() call.
_CACHE: dict[str, Any] = {}


def get_encoder(name: str | None) -> Any | None:
    """Return an encoder for *name*, or None for character costing.

    Raises :class:`SoonError` if *name* is not one of the bundled encodings
    (see :data:`_BUNDLED`). This keeps the module strictly offline and
    matches the TypeScript side's ``getEncoder`` behaviour.
    """
    if name is None:
        return None
    cached = _CACHE.get(name)
    if cached is not None:
        return cached
    if name not in _BUNDLED:
        supported = ", ".join(sorted(_BUNDLED)) or "(none)"
        raise SoonError(
            f"unknown tokenizer {name!r}; supported (bundled offline): {supported}"
        )
    encoder = _build_encoder(name)
    _CACHE[name] = encoder
    return encoder


def text_cost(text: str, encoder: Any | None = None) -> int:
    if encoder is None:
        return len(text)
    return len(encoder.encode(text))
