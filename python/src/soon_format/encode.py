"""SOON encoder (SPEC §4, §7, §8)."""

from __future__ import annotations

import json
import re
from collections.abc import Callable
from typing import Any

from .errors import SoonEncodeError
from .scalars import compact_json, is_scalar, scalar_literal
from .shape import OBJECT, PARRAY, RAW, SCALAR, TABLE, Field, Shape, infer_shape, serialize_shape
from .tokencost import get_encoder, text_cost

INDENT = "  "
KEY_TOKEN = re.compile(r"[A-Za-z0-9_\-]+")
_NAME_SANITIZE = re.compile(r"[^A-Za-z0-9_]")

# A cost function measures a candidate encoding fragment. Defaults to
# character length; when a tokenizer is configured it returns real token
# counts. Threaded via ``_Registry.cost`` so every local decision that has
# a real alternative (table vs. inline-JSON fallback) is measured against
# the same unit the outer document-level compare in ``encode()`` uses.
CostFn = Callable[[str], int]


class _Registry:
    """Named shape declarations, deduplicated by structural signature.

    ``peek`` returns the name a subsequent ``register`` would assign,
    without committing state — so the local cost estimator in
    ``_try_table`` can measure the exact string that will be emitted
    (including the possibly collision-suffixed name) before deciding
    whether the table is worth registering at all.
    """

    def __init__(self, cost: CostFn) -> None:
        self.by_sig: dict[str, str] = {}
        self.names: set[str] = set()
        self.decls: list[tuple[str, str]] = []
        self.cost: CostFn = cost

    def has(self, sig: str) -> bool:
        return sig in self.by_sig

    def _mint(self, hint: str) -> str:
        base = _NAME_SANITIZE.sub("", hint) or "shape"
        if base[0].isdigit():
            base = "s" + base
        name, i = base, 2
        while name in self.names:
            name = f"{base}{i}"
            i += 1
        return name

    def peek(self, sig: str, hint: str) -> str:
        existing = self.by_sig.get(sig)
        return existing if existing is not None else self._mint(hint)

    def register(self, shape: Shape, hint: str) -> str:
        sig = serialize_shape(shape)
        existing = self.by_sig.get(sig)
        if existing is not None:
            return existing
        name = self._mint(hint)
        self.names.add(name)
        self.by_sig[sig] = name
        self.decls.append((name, sig))
        return name


def encode(data: Any, *, mode: str = "auto", tokenizer: str | None = None) -> str:
    """Encode *data* (a JSON-compatible value) as a SOON document.

    Modes:
      - ``auto`` (default): SOON, falling back to compact JSON whenever SOON
        would not be strictly smaller (never-worse guarantee, SPEC §2.1).
      - ``soon``: force the SOON encoding (root scalars still use JSON).
      - ``json``: force compact JSON.

    ``tokenizer`` names a tiktoken encoding (e.g. ``o200k_base``) used for the
    cost comparison in ``auto`` mode; character counts are used otherwise.
    """
    if mode not in ("auto", "soon", "json"):
        raise ValueError(f"unknown mode: {mode!r}")
    cj = compact_json(data)
    if mode == "json":
        return cj
    enc = get_encoder(tokenizer)
    cost: CostFn = (lambda s: text_cost(s, enc)) if enc is not None else len
    doc = _encode_soon(data, cost)
    if doc is None:
        return cj
    if mode == "soon":
        return doc
    return doc if cost(doc) < cost(cj) else cj


def _encode_soon(data: Any, cost: CostFn) -> str | None:
    reg = _Registry(cost)
    body: list[str] | None
    if isinstance(data, dict):
        body = _entries(data, 0, reg) if data else None
    elif isinstance(data, list):
        body = _root_array(data, reg)
    else:
        body = None
    if body is None:
        return None
    decls = [f"SHAPE {name} = {sig}" for name, sig in reg.decls]
    return "\n".join(decls + body)


def _key_token(key: Any) -> str:
    if not isinstance(key, str):
        raise SoonEncodeError(f"object keys must be strings, got {type(key).__name__}")
    if KEY_TOKEN.fullmatch(key):
        return key
    return json.dumps(key, ensure_ascii=False)


def _entries(obj: dict[str, Any], depth: int, reg: _Registry) -> list[str]:
    pad = INDENT * depth
    lines: list[str] = []
    for key, value in obj.items():
        kt = _key_token(key)
        if isinstance(value, dict):
            if not value:
                lines.append(f"{pad}{kt}: !{{}}")
            else:
                lines.append(f"{pad}{kt}:")
                lines.extend(_entries(value, depth + 1, reg))
        elif isinstance(value, list):
            lines.extend(_array_entry(kt, value, key, pad, reg))
        else:
            lines.append(f"{pad}{kt}: {scalar_literal(value)}")
    return lines


def _array_entry(
    kt: str, value: list[Any], hint: str, pad: str, reg: _Registry
) -> list[str]:
    if all(is_scalar(x) for x in value):
        inline = ",".join(scalar_literal(x) for x in value)
        head = f"{pad}{kt}[{len(value)}]:"
        return [head + (" " + inline if inline else "")]
    header_prefix = f"{pad}{kt}[{len(value)}]"
    json_line = f"{pad}{kt}: !{compact_json(value)}"
    table = _try_table(value, hint, reg, header_prefix, json_line)
    if table is not None:
        name, rows = table
        return [f"{header_prefix}<{name}>:", *rows]
    return [json_line]


def _try_table(
    value: list[Any],
    hint: str,
    reg: _Registry,
    header_prefix: str,
    json_line: str,
) -> tuple[str, list[str]] | None:
    """Decide whether ``value`` should be emitted as a SOON table.

    ``header_prefix`` is the caller-supplied string that will precede the
    ``<name>:`` marker in the emitted header (e.g. ``"{pad}{kt}[N]"`` for
    an inline array, ``"[N]"`` for a root array). ``json_line`` is the
    concrete JSON fallback the caller would emit if this returns None.

    The cost estimate tokenizes the actual emitted SOON fragment —
    including the header, the resolved shape name, and (when the shape is
    new) its ``SHAPE`` declaration — so the local decision agrees with
    what ``encode()`` will observe at the document level.
    """
    if len(value) < 2 or not all(isinstance(x, dict) for x in value):
        return None
    shape = infer_shape(value)
    sig = serialize_shape(shape)
    rows = [_tuple(el, shape) for el in value]
    name = reg.peek(sig, hint)
    body = f"{header_prefix}<{name}>:\n" + "\n".join(rows)
    soon_fragment = body if reg.has(sig) else f"SHAPE {name} = {sig}\n{body}"
    if reg.cost(soon_fragment) >= reg.cost(json_line):
        return None
    reg.register(shape, hint)
    return name, rows


def _root_array(value: list[Any], reg: _Registry) -> list[str] | None:
    if all(is_scalar(x) for x in value):
        inline = ",".join(scalar_literal(x) for x in value)
        head = f"[{len(value)}]:"
        return [head + (" " + inline if inline else "")]
    # At root, the JSON fallback is the whole compact JSON of the value;
    # there is no key/padding to prepend.
    header_prefix = f"[{len(value)}]"
    json_line = compact_json(value)
    table = _try_table(value, "item", reg, header_prefix, json_line)
    if table is not None:
        name, rows = table
        return [f"{header_prefix}<{name}>:", *rows]
    return None


def _tuple(el: dict[str, Any], shape: Shape) -> str:
    parts: list[str] = []
    for f in shape.fields:
        if f.name not in el:
            parts.append("_")
        else:
            parts.append(_field_value(el[f.name], f))
    return "(" + ",".join(parts) + ")"


def _field_value(value: Any, f: Field) -> str:
    if f.kind == RAW:
        return "!" + compact_json(value)
    if value is None:
        return "null"
    if f.kind == SCALAR:
        return scalar_literal(value)
    if f.kind == OBJECT:
        assert f.shape is not None
        return _tuple(value, f.shape)
    if f.kind == TABLE:
        assert f.shape is not None
        return "[" + ",".join(_tuple(el, f.shape) for el in value) + "]"
    if f.kind == PARRAY:
        return "[" + ",".join(scalar_literal(x) for x in value) + "]"
    raise SoonEncodeError(f"unknown field kind: {f.kind}")  # pragma: no cover
