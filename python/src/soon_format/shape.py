"""Shape model, inference (SPEC §7) and shape-expression syntax (SPEC §3)."""

from __future__ import annotations

import json
import re
from dataclasses import dataclass, field
from typing import Any

from .errors import SoonDecodeError

SCALAR = "scalar"
OBJECT = "object"
TABLE = "table"
PARRAY = "parray"
RAW = "raw"
_EMPTY = "empty"  # internal classification for []
_NULL = "null"  # internal classification for null

FIELD_NAME = re.compile(r"[A-Za-z0-9_\-]+")

_json_decoder = json.JSONDecoder()


@dataclass
class Field:
    name: str
    kind: str
    optional: bool = False
    shape: Shape | None = None


@dataclass
class Shape:
    fields: list[Field] = field(default_factory=list)


def field_name_token(name: str) -> str:
    if not isinstance(name, str):
        from .errors import SoonEncodeError

        raise SoonEncodeError(f"object keys must be strings, got {type(name).__name__}")
    if FIELD_NAME.fullmatch(name):
        return name
    return json.dumps(name, ensure_ascii=False)


def serialize_shape(shape: Shape) -> str:
    """Canonical shape expression; doubles as the structural signature."""
    parts = []
    for f in shape.fields:
        t = ("?" if f.optional else "") + field_name_token(f.name)
        if f.kind == OBJECT:
            assert f.shape is not None
            t += ":" + serialize_shape(f.shape)
        elif f.kind == TABLE:
            assert f.shape is not None
            t += ":[" + serialize_shape(f.shape) + "]"
        elif f.kind == PARRAY:
            t += ":[]"
        elif f.kind == RAW:
            t += ":!"
        parts.append(t)
    return "{" + ",".join(parts) + "}"


def _classify(value: Any) -> str:
    from .scalars import is_scalar

    if value is None:
        return _NULL
    if isinstance(value, dict):
        return OBJECT
    if isinstance(value, list):
        if not value:
            return _EMPTY
        if all(isinstance(x, dict) for x in value):
            return TABLE
        if all(is_scalar(x) for x in value):
            return PARRAY
        return RAW
    return SCALAR


def infer_shape(elements: list[dict[str, Any]]) -> Shape:
    """Infer the shape of a homogeneous-ish list of objects (SPEC §7)."""
    order: list[str] = []
    infos: dict[str, dict[str, Any]] = {}
    n = len(elements)
    for el in elements:
        for k, v in el.items():
            info = infos.get(k)
            if info is None:
                order.append(k)
                info = infos[k] = {"count": 0, "kinds": set(), "objs": [], "subelems": []}
            info["count"] += 1
            c = _classify(v)
            info["kinds"].add(c)
            if c == OBJECT:
                info["objs"].append(v)
            elif c == TABLE:
                info["subelems"].extend(v)
    fields: list[Field] = []
    for k in order:
        info = infos[k]
        kinds: set[str] = info["kinds"] - {_NULL}
        sub: Shape | None = None
        if not kinds or kinds == {SCALAR}:
            kind = SCALAR
        elif kinds == {OBJECT}:
            kind = OBJECT
            sub = infer_shape(info["objs"])
        elif TABLE in kinds and kinds <= {TABLE, _EMPTY}:
            kind = TABLE
            sub = infer_shape(info["subelems"])
        elif kinds <= {PARRAY, _EMPTY}:
            kind = PARRAY
        else:
            kind = RAW
        fields.append(Field(k, kind, info["count"] < n, sub))
    return Shape(fields)


class ShapeParser:
    """Recursive-descent parser for shape expressions."""

    def __init__(self, text: str) -> None:
        self.s = text
        self.i = 0

    def parse(self) -> Shape:
        shape = self._shape()
        if self.i != len(self.s):
            raise SoonDecodeError(f"trailing characters in shape expression: {self.s[self.i:]!r}")
        return shape

    def _peek(self) -> str:
        return self.s[self.i] if self.i < len(self.s) else ""

    def _expect(self, ch: str) -> None:
        if self._peek() != ch:
            raise SoonDecodeError(f"expected {ch!r} at position {self.i} in shape expression")
        self.i += 1

    def _shape(self) -> Shape:
        self._expect("{")
        fields: list[Field] = []
        if self._peek() == "}":
            self.i += 1
            return Shape(fields)
        while True:
            fields.append(self._field())
            c = self._peek()
            self.i += 1
            if c == ",":
                continue
            if c == "}":
                break
            raise SoonDecodeError("malformed shape expression: expected ',' or '}'")
        return Shape(fields)

    def _field(self) -> Field:
        optional = False
        if self._peek() == "?":
            optional = True
            self.i += 1
        name = self._name()
        kind = SCALAR
        sub: Shape | None = None
        if self._peek() == ":":
            self.i += 1
            c = self._peek()
            if c == "{":
                sub = self._shape()
                kind = OBJECT
            elif c == "[":
                self.i += 1
                if self._peek() == "{":
                    sub = self._shape()
                    kind = TABLE
                    self._expect("]")
                elif self._peek() == "]":
                    self.i += 1
                    kind = PARRAY
                else:
                    raise SoonDecodeError("malformed field type in shape expression")
            elif c == "!":
                self.i += 1
                kind = RAW
            else:
                raise SoonDecodeError("malformed field type in shape expression")
        return Field(name, kind, optional, sub)

    def _name(self) -> str:
        if self._peek() == '"':
            try:
                name, end = _json_decoder.raw_decode(self.s, self.i)
            except ValueError as exc:
                raise SoonDecodeError(f"bad quoted field name: {exc}") from exc
            if not isinstance(name, str):
                raise SoonDecodeError("field name must be a string")
            self.i = end
            return name
        m = FIELD_NAME.match(self.s, self.i)
        if not m:
            raise SoonDecodeError(f"expected field name at position {self.i} in shape expression")
        self.i = m.end()
        return m.group(0)
