"""Savings report for a value: JSON vs SOON, by characters and (optionally) tokens."""

from __future__ import annotations

from typing import Any

from .encode import encode
from .scalars import compact_json
from .tokencost import get_encoder, text_cost


def stats(data: Any, *, tokenizer: str | None = None) -> dict[str, Any]:
    """Return a savings report for encoding *data* as SOON in ``auto`` mode."""
    cj = compact_json(data)
    doc = encode(data, mode="auto", tokenizer=tokenizer)
    encoder = get_encoder(tokenizer)
    report: dict[str, Any] = {
        "json_chars": len(cj),
        "soon_chars": len(doc),
        "fallback": doc == cj,
    }
    if encoder is not None:
        report["json_tokens"] = text_cost(cj, encoder)
        report["soon_tokens"] = text_cost(doc, encoder)
        base, mine = report["json_tokens"], report["soon_tokens"]
    else:
        base, mine = len(cj), len(doc)
    report["saving"] = round(1 - mine / base, 4) if base else 0.0
    return report
