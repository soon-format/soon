"""Cost measurement: characters by default, real tokens via tiktoken (optional)."""

from __future__ import annotations

from typing import Any

from .errors import SoonError


def get_encoder(name: str | None) -> Any | None:
    """Return a tiktoken encoder for *name*, or None for character costing."""
    if name is None:
        return None
    try:
        import tiktoken
    except ImportError as exc:  # pragma: no cover
        raise SoonError(
            "tokenizer support requires tiktoken; install with: pip install 'soon-format[tokens]'"
        ) from exc
    return tiktoken.get_encoding(name)


def text_cost(text: str, encoder: Any | None = None) -> int:
    if encoder is None:
        return len(text)
    return len(encoder.encode(text))
