"""Savings report for a value: JSON vs SOON, by characters and (optionally) tokens.

Shares the encoder + cost computation with the auto-mode decision so a single
``stats()`` call performs one tokenization pass per candidate string, not two.
"""

from __future__ import annotations

from typing import Any

from .encode import CostFn, _encode_soon
from .scalars import compact_json
from .tokencost import get_encoder, text_cost


def stats(data: Any, *, tokenizer: str | None = None) -> dict[str, Any]:
    """Return a savings report for encoding *data* as SOON in ``auto`` mode."""
    cj = compact_json(data)
    encoder = get_encoder(tokenizer)
    cost: CostFn = (lambda s: text_cost(s, encoder)) if encoder is not None else len

    cj_cost = cost(cj)
    soon = _encode_soon(data, cost)
    if soon is None:
        doc, doc_cost, fallback = cj, cj_cost, True
    else:
        soon_cost = cost(soon)
        if soon_cost < cj_cost:
            doc, doc_cost, fallback = soon, soon_cost, False
        else:
            doc, doc_cost, fallback = cj, cj_cost, True

    report: dict[str, Any] = {
        "json_chars": len(cj),
        "soon_chars": len(doc),
        "fallback": fallback,
    }
    if encoder is not None:
        report["json_tokens"] = cj_cost
        report["soon_tokens"] = doc_cost
        base, mine = cj_cost, doc_cost
    else:
        base, mine = len(cj), len(doc)
    report["saving"] = round(1 - mine / base, 4) if base else 0.0
    return report
