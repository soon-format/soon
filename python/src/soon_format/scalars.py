"""Scalar literal encoding/decoding shared by the encoder and decoder.

The rules here are normative (SPEC.md §5) and must match the TypeScript
implementation byte for byte.
"""

from __future__ import annotations

import json
import math
import re
from typing import Any, Union

from .errors import SoonEncodeError

JsonValue = Union[None, bool, int, float, str, "list[JsonValue]", "dict[str, JsonValue]"]

# SPEC §5.1.5 — deterministic, language-independent number detection.
NUMBER_LIKE = re.compile(r"[+-]?(\d+(\.\d*)?|\.\d+)([eE][+-]?\d+)?")
INT_TOKEN = re.compile(r"-?\d+")
SAFE_UNQUOTED = re.compile(r"[A-Za-z0-9_.+\-@/ ]+")
KEYWORDS = frozenset({"null", "true", "false"})


def compact_json(value: Any) -> str:
    """Serialize *value* as compact JSON. Rejects non-finite numbers."""
    try:
        return json.dumps(value, separators=(",", ":"), ensure_ascii=False, allow_nan=False)
    except (TypeError, ValueError) as exc:
        raise SoonEncodeError(f"value is not JSON-serializable: {exc}") from exc


def is_scalar(value: Any) -> bool:
    return value is None or isinstance(value, (bool, int, float, str))


def is_safe_unquoted(s: str) -> bool:
    """SPEC §5.1 — may this string be emitted without quotes?"""
    if not s or s == "_" or s in KEYWORDS:
        return False
    if s[0] == " " or s[-1] == " ":
        return False
    if not SAFE_UNQUOTED.fullmatch(s):
        return False
    return not NUMBER_LIKE.fullmatch(s)


def scalar_literal(value: Any) -> str:
    """Encode a scalar as a SOON literal (SPEC §5)."""
    if value is None:
        return "null"
    if value is True:
        return "true"
    if value is False:
        return "false"
    if isinstance(value, int):
        return str(value)
    if isinstance(value, float):
        if not math.isfinite(value):
            raise SoonEncodeError("non-finite numbers are not supported")
        return json.dumps(value)
    if isinstance(value, str):
        if is_safe_unquoted(value):
            return value
        return json.dumps(value, ensure_ascii=False)
    raise SoonEncodeError(f"not a scalar: {type(value).__name__}")


def parse_literal(token: str) -> JsonValue:
    """Decode a bare token (SPEC §5.2)."""
    if token == "null":
        return None
    if token == "true":
        return True
    if token == "false":
        return False
    if INT_TOKEN.fullmatch(token):
        return int(token)
    if NUMBER_LIKE.fullmatch(token):
        return float(token)
    return token
