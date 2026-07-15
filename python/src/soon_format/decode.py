"""SOON decoder (SPEC sections 4-6 and 9). Treats all input as untrusted."""

from __future__ import annotations

import json
import re
from typing import Any

from .errors import SoonDecodeError
from .scalars import JsonValue, parse_literal
from .shape import OBJECT, PARRAY, TABLE, Field, Shape, ShapeParser

_json_decoder = json.JSONDecoder()

SHAPE_DECL = re.compile(r"SHAPE ([A-Za-z_][A-Za-z0-9_]*) = (\{.*\})")
ROOT_ARRAY = re.compile(r"\[(\d*)\](?:<([A-Za-z_][A-Za-z0-9_]*)>)?:(.*)")
ENTRY_ARRAY = re.compile(r"\[(\d*)\](?:<([A-Za-z_][A-Za-z0-9_]*)>)?:(.*)")
KEY_TOKEN = re.compile(r"[A-Za-z0-9_\-]+")
FIELD_LABEL = re.compile(r"([A-Za-z0-9_\-]+)=")
_MISSING = object()


def decode(text: str) -> JsonValue:
    """Decode a SOON document back to its JSON value."""
    if not isinstance(text, str):
        raise SoonDecodeError(f"expected str, got {type(text).__name__}")
    # SPEC §2.1: JSON fallback documents.
    try:
        return json.loads(text)  # type: ignore[no-any-return]
    except ValueError:
        pass
    return _Parser(text).parse()


class _Parser:
    def __init__(self, text: str) -> None:
        self.lines = text.split("\n")
        self.i = 0
        self.shapes: dict[str, Shape] = {}

    def parse(self) -> JsonValue:
        if not any(line.strip() for line in self.lines):
            raise SoonDecodeError("empty document")
        while self.i < len(self.lines):
            m = SHAPE_DECL.fullmatch(self.lines[self.i])
            if not m:
                break
            name = m.group(1)
            if name in self.shapes:
                raise SoonDecodeError(f"duplicate shape declaration: {name}")
            self.shapes[name] = ShapeParser(m.group(2)).parse()
            self.i += 1
        self._skip_blanks()
        if self.i >= len(self.lines):
            raise SoonDecodeError("document has shape declarations but no body")
        m = ROOT_ARRAY.fullmatch(self.lines[self.i])
        value: JsonValue
        if m:
            self.i += 1
            value = self._array_value(m.group(1), m.group(2), m.group(3))
        else:
            value = self._block(0)
            if not value:
                raise SoonDecodeError("invalid document")
        self._skip_blanks()
        if self.i < len(self.lines):
            raise SoonDecodeError(f"trailing content at line {self.i + 1}")
        return value

    def _skip_blanks(self) -> None:
        while self.i < len(self.lines) and _is_skippable(self.lines[self.i]):
            self.i += 1

    def _block(self, depth: int) -> dict[str, JsonValue]:
        out: dict[str, JsonValue] = {}
        while self.i < len(self.lines):
            line = self.lines[self.i]
            if _is_skippable(line):
                self.i += 1
                continue
            indent = len(line) - len(line.lstrip(" "))
            if indent < depth * 2:
                break
            if indent != depth * 2:
                raise SoonDecodeError(f"bad indentation at line {self.i + 1}")
            self.i += 1
            key, pos = self._key(line, indent)
            if key in out:
                raise SoonDecodeError(f"duplicate key {key!r} at line {self.i}")
            c = line[pos] if pos < len(line) else ""
            if c == "[":
                m = ENTRY_ARRAY.match(line, pos)
                if not m or m.end() != len(line):
                    raise SoonDecodeError(f"malformed array entry at line {self.i}")
                out[key] = self._array_value(m.group(1), m.group(2), m.group(3))
            elif c == ":":
                rest = line[pos + 1 :]
                if rest == "":
                    out[key] = self._block(depth + 1)
                elif rest.startswith(" "):
                    out[key] = self._scalar_entry(rest[1:])
                else:
                    raise SoonDecodeError(f"malformed entry at line {self.i}")
            else:
                raise SoonDecodeError(f"malformed entry at line {self.i}")
        return out

    def _key(self, line: str, pos: int) -> tuple[str, int]:
        if pos < len(line) and line[pos] == '"':
            try:
                key, end = _json_decoder.raw_decode(line, pos)
            except ValueError as exc:
                raise SoonDecodeError(f"bad quoted key at line {self.i}: {exc}") from exc
            if not isinstance(key, str):
                raise SoonDecodeError(f"object key must be a string at line {self.i}")
            return key, end
        m = KEY_TOKEN.match(line, pos)
        if not m:
            raise SoonDecodeError(f"expected key at line {self.i}")
        return m.group(0), m.end()

    def _scalar_entry(self, rest: str) -> JsonValue:
        if rest.startswith("!"):
            return _full_json(rest[1:], "inline JSON value")
        if rest.startswith('"'):
            value = _full_json(rest, "quoted string")
            if not isinstance(value, str):
                raise SoonDecodeError("quoted entry value must be a string")
            return value
        if rest == "":
            raise SoonDecodeError("empty entry value")
        return parse_literal(rest)

    def _array_value(
        self, n_raw: str, shape_name: str | None, rest: str
    ) -> list[JsonValue]:
        if shape_name is not None:
            if rest.strip():
                raise SoonDecodeError("unexpected content after table header")
            shape = self.shapes.get(shape_name)
            if shape is None:
                raise SoonDecodeError(f"unknown shape: {shape_name}")
            rows: list[JsonValue] = []
            if n_raw == "":
                # Guardrail-off form ``[]<shape>:`` — read rows until the
                # next line that isn't a row/blank/comment.
                while self.i < len(self.lines):
                    line = self.lines[self.i]
                    if _is_skippable(line):
                        self.i += 1
                        continue
                    if not line.startswith("("):
                        break
                    self.i += 1
                    rows.append(_TupleParser(line, self.i).parse_row(shape))
                return rows
            n = int(n_raw)
            for _ in range(n):
                while self.i < len(self.lines) and _is_skippable(self.lines[self.i]):
                    self.i += 1
                if self.i >= len(self.lines):
                    raise SoonDecodeError(
                        f"expected {n} rows, found {len(rows)} (unexpected end of document)"
                    )
                row = self.lines[self.i]
                self.i += 1
                rows.append(_TupleParser(row, self.i).parse_row(shape))
            return rows
        # Primitive array — N is required (values are inlined on the header).
        if n_raw == "":
            raise SoonDecodeError("primitive array requires an element count")
        n = int(n_raw)
        if rest == "":
            if n != 0:
                raise SoonDecodeError(f"expected {n} elements, found 0")
            return []
        if not rest.startswith(" "):
            raise SoonDecodeError("malformed primitive array")
        values = _TupleParser(rest[1:], self.i).parse_inline_list()
        if len(values) != n:
            raise SoonDecodeError(f"expected {n} elements, found {len(values)}")
        return values


def _is_skippable(line: str) -> bool:
    """Blank line or a ``#``-comment line (SPEC §2, v0.2)."""
    stripped = line.lstrip(" ")
    return stripped == "" or stripped.startswith("#")


def _full_json(text: str, what: str) -> JsonValue:
    try:
        value, end = _json_decoder.raw_decode(text, 0)
    except ValueError as exc:
        raise SoonDecodeError(f"bad {what}: {exc}") from exc
    if text[end:].strip():
        raise SoonDecodeError(f"trailing characters after {what}")
    return value  # type: ignore[no-any-return]


class _TupleParser:
    """Cursor-based parser for row tuples and inline scalar lists (SPEC §6)."""

    def __init__(self, s: str, line_no: int = 0) -> None:
        self.s = s
        self.i = 0
        self.line_no = line_no

    def _err(self, msg: str) -> SoonDecodeError:
        return SoonDecodeError(f"line {self.line_no}: {msg} (at column {self.i + 1})")

    def _peek(self) -> str:
        return self.s[self.i] if self.i < len(self.s) else ""

    def _expect(self, ch: str) -> None:
        if self._peek() != ch:
            raise self._err(f"expected {ch!r}")
        self.i += 1

    def _skip_ws(self) -> None:
        while self.i < len(self.s) and self.s[self.i] == " ":
            self.i += 1

    def _boundary(self, j: int) -> bool:
        return j >= len(self.s) or self.s[j] in ",)]"

    def parse_row(self, shape: Shape) -> dict[str, JsonValue]:
        value = self._tuple(shape)
        self._skip_ws()
        if self.i != len(self.s):
            raise self._err("trailing characters in row")
        return value

    def parse_inline_list(self) -> list[JsonValue]:
        out = [self._scalar_token()]
        self._skip_ws()
        while self.i < len(self.s):
            self._expect(",")
            out.append(self._scalar_token())
            self._skip_ws()
        return out

    def _tuple(self, shape: Shape) -> dict[str, JsonValue]:
        self._skip_ws()
        self._expect("(")
        # Peek for labeled form (SPEC §6.2). Empty ``()`` is only legal
        # in labeled mode (all-optional shape); positional grammar requires
        # a value per field.
        self._skip_ws()
        if self._peek() == ")" or self._is_labeled_head(shape):
            return self._labeled_tuple(shape)
        out: dict[str, JsonValue] = {}
        for idx, f in enumerate(shape.fields):
            if idx:
                self._skip_ws()
                self._expect(",")
            value = self._field_value(f)
            if value is not _MISSING:
                out[f.name] = value
        self._skip_ws()
        self._expect(")")
        return out

    def _is_labeled_head(self, shape: Shape) -> bool:
        """True iff the next token is a shape field name followed by ``=``.

        Accepts both bare tokens (``foo=``) and quoted names (``")="=``)
        for non-token keys. Positional tuple values never start with a
        field name followed by ``=``: scalars matching a shape field name
        would still be followed by ``,``/``)`` boundary chars, not ``=``.
        """
        name, end = self._peek_label_name()
        if name is None or end >= len(self.s) or self.s[end] != "=":
            return False
        return any(f.name == name for f in shape.fields)

    def _peek_label_name(self) -> tuple[str | None, int]:
        if self._peek() == '"':
            try:
                value, end = _json_decoder.raw_decode(self.s, self.i)
            except ValueError:
                return None, self.i
            if not isinstance(value, str):
                return None, self.i
            return value, end
        m = FIELD_LABEL.match(self.s, self.i)
        if not m:
            return None, self.i
        # FIELD_LABEL captures the name-plus-``=``; return just the name and
        # the position of the ``=`` so the caller can validate it.
        return m.group(1), m.start() + len(m.group(1))

    def _labeled_tuple(self, shape: Shape) -> dict[str, JsonValue]:
        by_name = {f.name: f for f in shape.fields}
        out: dict[str, JsonValue] = {}
        first = True
        while True:
            self._skip_ws()
            if first and self._peek() == ")":
                self.i += 1
                break
            if not first:
                self._expect(",")
                self._skip_ws()
            name, end = self._peek_label_name()
            if name is None or end >= len(self.s) or self.s[end] != "=":
                raise self._err("expected labeled field 'name='")
            self.i = end + 1
            f = by_name.get(name)
            if f is None:
                raise self._err(f"unknown field {name!r} in labeled tuple")
            if name in out:
                raise self._err(f"duplicate labeled field {name!r}")
            value = self._field_value(f)
            if value is _MISSING:
                raise self._err(f"'_' not allowed for labeled field {name!r}")
            out[name] = value
            first = False
            self._skip_ws()
            if self._peek() == ")":
                self.i += 1
                break
        for f in shape.fields:
            if not f.optional and f.name not in out:
                raise self._err(f"missing required field {f.name!r} in labeled tuple")
        return out

    def _field_value(self, f: Field) -> Any:
        self._skip_ws()
        c = self._peek()
        if c == "":
            raise self._err(f"unexpected end of row in field {f.name!r}")
        if c == "_" and self._boundary(self.i + 1):
            if not f.optional:
                raise self._err(f"'_' used for required field {f.name!r}")
            self.i += 1
            return _MISSING
        if c == "!":
            self.i += 1
            return self._raw_json()
        if c == "(":
            if f.kind != OBJECT or f.shape is None:
                raise self._err(f"unexpected tuple for field {f.name!r}")
            return self._tuple(f.shape)
        if c == "[":
            return self._list_value(f)
        return self._scalar_token()

    def _list_value(self, f: Field) -> list[JsonValue]:
        self._expect("[")
        out: list[JsonValue] = []
        self._skip_ws()
        if self._peek() == "]":
            self.i += 1
            return out
        while True:
            if f.kind == TABLE and f.shape is not None:
                out.append(self._tuple(f.shape))
            elif f.kind == PARRAY:
                out.append(self._scalar_token())
            else:
                raise self._err(f"unexpected list for field {f.name!r}")
            self._skip_ws()
            c = self._peek()
            self.i += 1
            if c == ",":
                continue
            if c == "]":
                break
            raise self._err("expected ',' or ']' in list")
        return out

    def _raw_json(self) -> JsonValue:
        try:
            value, end = _json_decoder.raw_decode(self.s, self.i)
        except ValueError as exc:
            raise self._err(f"bad inline JSON: {exc}") from exc
        self.i = end
        return value  # type: ignore[no-any-return]

    def _scalar_token(self) -> JsonValue:
        self._skip_ws()
        if self._peek() == '"':
            value = self._raw_json()
            if not isinstance(value, str):
                raise self._err("quoted value must be a string")
            return value
        j = self.i
        while j < len(self.s) and self.s[j] not in ",)]":
            j += 1
        token = self.s[self.i : j]
        if token == "":
            raise self._err("empty value")
        self.i = j
        return parse_literal(token)
