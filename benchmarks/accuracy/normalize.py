"""Type-aware answer normalization and comparison.

Design mirrors TOON's benchmarks/src/normalize.ts: deterministic
per-answer-type comparison, no LLM judge. Adapted for the answer types
this harness produces.
"""

from __future__ import annotations

import math
import re
from typing import Any

# Recognize a leading number, with optional currency prefix and optional
# comma thousands separators / decimal / exponent / percent suffix.
_NUM_RE = re.compile(r"[$€£¥]?\s*-?\d[\d,]*(?:\.\d+)?(?:[eE][+-]?\d+)?%?")
_INT_RE = re.compile(r"[$€£¥]?\s*-?\d[\d,]*")
_STRIP_CURR = re.compile(r"[$€£¥,%\s]")


def _strip_wrappers(s: str) -> str:
    s = s.strip()
    # Strip markdown code fences (```...```).
    if s.startswith("```") and s.endswith("```"):
        s = s[3:-3].strip()
        if "\n" in s:
            # First line often a language identifier like ``json``.
            first, rest = s.split("\n", 1)
            if re.fullmatch(r"\w+", first):
                s = rest.strip()
    # Strip surrounding straight or smart quotes.
    if len(s) >= 2 and s[0] in {'"', "'", "“"} and s[-1] in {'"', "'", "”"}:
        s = s[1:-1].strip()
    return s


def _extract_int(s: str) -> int | None:
    s = _strip_wrappers(s)
    m = _INT_RE.search(s)
    if not m:
        return None
    raw = _STRIP_CURR.sub("", m.group(0))
    try:
        return int(raw)
    except ValueError:
        return None


def _extract_number(s: str) -> float | None:
    s = _strip_wrappers(s)
    m = _NUM_RE.search(s)
    if not m:
        return None
    token = m.group(0)
    percent = token.endswith("%")
    raw = _STRIP_CURR.sub("", token)
    if not raw or raw in {"-", "+"}:
        return None
    try:
        value = float(raw)
    except ValueError:
        return None
    return value / 100 if percent else value


def _extract_boolean(s: str) -> bool | None:
    tok = _strip_wrappers(s).lower()
    if tok in {"true", "yes", "y", "1"}:
        return True
    if tok in {"false", "no", "n", "0"}:
        return False
    return None


def _extract_string(s: str) -> str:
    return _strip_wrappers(s)


def _split_list(s: str) -> list[str]:
    s = _strip_wrappers(s)
    if s.startswith("[") and s.endswith("]"):
        s = s[1:-1]
    parts = [p.strip().strip("'\"") for p in re.split(r"[,\n]", s)]
    return [p for p in parts if p]


def compare(response: str, ground_truth: Any, answer_type: str) -> tuple[bool, Any]:
    """Return (correct, normalized_response).

    ``ground_truth`` is the Python value the row/dataset produced;
    ``response`` is the raw LLM output. Comparison is type-aware to
    avoid penalizing "$1,000" vs "1000" or "Yes" vs "true".
    """
    if answer_type == "integer":
        got = _extract_int(response)
        return (got is not None and int(ground_truth) == got, got)
    if answer_type == "number":
        got = _extract_number(response)
        if got is None:
            return False, None
        target = float(ground_truth)
        # Absolute or relative tolerance — 1e-6 either way.
        ok = math.isclose(target, got, rel_tol=1e-6, abs_tol=1e-6)
        return ok, got
    if answer_type == "boolean":
        got_b = _extract_boolean(response)
        return (got_b is not None and bool(ground_truth) == got_b, got_b)
    if answer_type == "string":
        got_s = _extract_string(response)
        # Case-insensitive by default; strings from the datasets are ASCII-ish.
        return (str(ground_truth).strip().lower() == got_s.lower(), got_s)
    if answer_type == "list-ordered":
        parts = _split_list(response)
        target = [str(x).lower() for x in ground_truth]
        return ([p.lower() for p in parts] == target, parts)
    if answer_type == "list-unordered":
        parts = _split_list(response)
        target = sorted(str(x).lower() for x in ground_truth)
        return (sorted(p.lower() for p in parts) == target, parts)
    raise ValueError(f"unknown answer_type: {answer_type!r}")
