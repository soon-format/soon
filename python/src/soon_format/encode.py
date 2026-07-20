"""SOON encoder (SPEC §4, §7, §8)."""

from __future__ import annotations

import json
import re
from collections.abc import Callable
from typing import Any

from .errors import SoonEncodeError
from .scalars import compact_json, is_scalar, scalar_literal
from .shape import (
    OBJECT,
    PARRAY,
    RAW,
    SCALAR,
    TABLE,
    Field,
    Shape,
    field_name_token,
    infer_shape,
    serialize_shape,
)
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

    def __init__(
        self,
        cost: CostFn,
        labeled: bool = False,
        shape_hint_rows: int | None = None,
        row_count_guardrail: bool = True,
        elide: bool = False,
        ref: bool = False,
    ) -> None:
        self.by_sig: dict[str, str] = {}
        self.names: set[str] = set()
        self.decls: list[tuple[str, str]] = []
        self.refs: list[tuple[str, str]] = []
        self.cost: CostFn = cost
        self.labeled: bool = labeled
        self.shape_hint_rows: int | None = shape_hint_rows
        self.row_count_guardrail: bool = row_count_guardrail
        self.elide: bool = elide
        self.ref: bool = ref

    def mint_ref(self, hint: str) -> str:
        base = _NAME_SANITIZE.sub("", hint) or "ref"
        if base[0].isdigit():
            base = "r" + base
        name, i = base, 2
        while name in self.names:
            name = f"{base}{i}"
            i += 1
        self.names.add(name)
        return name

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

    def register(self, sig: str, hint: str) -> str:
        existing = self.by_sig.get(sig)
        if existing is not None:
            return existing
        name = self._mint(hint)
        self.names.add(name)
        self.by_sig[sig] = name
        self.decls.append((name, sig))
        return name


def encode(
    data: Any,
    *,
    mode: str = "auto",
    tokenizer: str | None = None,
    shape_hint_rows: int | None = None,
    row_count_guardrail: bool = True,
    elide: bool = False,
    ref: bool = False,
) -> str:
    """Encode *data* (a JSON-compatible value) as a SOON document.

    Modes:
      - ``auto`` (default): SOON, falling back to compact JSON whenever SOON
        would not be strictly smaller (never-worse guarantee, SPEC §2.1).
      - ``soon``: force the SOON encoding (root scalars still use JSON).
      - ``labeled``: force SOON with labeled tuples (``(id=1,name=Ada)``);
        accuracy-insurance variant, per-array table decisions still honor
        the local cost model against JSON fallback.
      - ``json``: force compact JSON.

    ``tokenizer`` names a tiktoken encoding (e.g. ``o200k_base``) used for the
    cost comparison in ``auto`` mode; character counts are used otherwise.

    ``shape_hint_rows`` (v0.2, SPEC §2 comment lines): when a positive int,
    tables with at least ``2 * shape_hint_rows`` rows have their SHAPE
    declaration re-emitted as a comment (``# SHAPE name = {sig}``) every
    N rows. Ablation knob for the retrieval-accuracy harness — measures
    whether periodic re-priming improves LLM recall. Bypasses the
    per-array cost gate; the never-worse compare still applies at the
    document level in ``auto`` mode.

    ``row_count_guardrail`` (v0.2, SPEC §4.1): when False, table headers
    are emitted as ``[]<shape>:`` instead of ``[N]<shape>:``. Ablation
    for the accuracy harness — measures whether stating the row count
    actually helps LLMs. Primitive arrays are unaffected (their length
    is inherent to the inline list).

    ``elide`` (v0.2, SPEC §6.2): when True, required scalar columns
    where the mode value covers ≥80% of rows are dropped from the shape
    body and declared as ``| defaults: k=v`` in the SHAPE decl.
    Exceptional rows carry ``+k=v`` overrides. The per-array cost gate
    picks the winner between elided and non-elided candidates.

    ``ref`` (v0.2, SPEC §6.3): when True, identical OBJECT-typed
    sub-values that appear ≥ 2 times as the same field of the same
    table are hoisted into ``REF &name = (tuple)`` declarations and
    referenced inline via ``&name``. Only applied when net-positive.
    """
    if mode not in ("auto", "soon", "labeled", "json"):
        raise ValueError(f"unknown mode: {mode!r}")
    if shape_hint_rows is not None and shape_hint_rows <= 0:
        raise ValueError("shape_hint_rows must be a positive integer or None")
    cj = compact_json(data)
    if mode == "json":
        return cj
    enc = get_encoder(tokenizer)
    cost: CostFn = (lambda s: text_cost(s, enc)) if enc is not None else len
    labeled = mode == "labeled"
    doc = _encode_soon(
        data,
        cost,
        labeled=labeled,
        shape_hint_rows=shape_hint_rows,
        row_count_guardrail=row_count_guardrail,
        elide=elide,
        ref=ref,
    )
    if doc is None:
        return cj
    if mode in ("soon", "labeled"):
        return doc
    return doc if cost(doc) < cost(cj) else cj


def _encode_soon(
    data: Any,
    cost: CostFn,
    labeled: bool = False,
    shape_hint_rows: int | None = None,
    row_count_guardrail: bool = True,
    elide: bool = False,
    ref: bool = False,
) -> str | None:
    reg = _Registry(
        cost,
        labeled=labeled,
        shape_hint_rows=shape_hint_rows,
        row_count_guardrail=row_count_guardrail,
        elide=elide,
        ref=ref,
    )
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
    decls += [f"REF &{name} = {text}" for name, text in reg.refs]
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
    count_seg = f"[{len(value)}]" if reg.row_count_guardrail else "[]"
    header_prefix = f"{pad}{kt}{count_seg}"
    json_line = f"{pad}{kt}: !{compact_json(value)}"
    table = _try_table(value, hint, reg, header_prefix, json_line)
    if table is not None:
        name, rows = table
        return [f"{header_prefix}<{name}>:", *rows]
    return [json_line]


ELIDE_THRESHOLD = 0.8


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
    refs_by_hash, ref_decls = _collect_refs(value, shape, reg) if reg.ref else ({}, [])
    base_rows = [_tuple(el, shape, reg.labeled, refs_by_hash) for el in value]
    candidates: list[tuple[str, list[str]]] = [(serialize_shape(shape), base_rows)]
    if reg.elide:
        elided = _elide_candidate(value, shape, reg.labeled, refs_by_hash)
        if elided is not None:
            candidates.append(elided)
    # Local cost gate + winner selection. Labeled and shape-hint modes
    # bypass the JSON fallback comparison; the user opted in precisely
    # to get these forms.
    bypass = reg.labeled or reg.shape_hint_rows is not None
    best: tuple[str, list[str], int, str] | None = None  # (sig, rows, cost, body)
    for cand_sig, cand_rows in candidates:
        cand_name = reg.peek(cand_sig, hint)
        cand_rows_hinted = _intersperse_hints(cand_rows, cand_name, cand_sig, reg.shape_hint_rows)
        body = f"{header_prefix}<{cand_name}>:\n" + "\n".join(cand_rows_hinted)
        fragment = body if reg.has(cand_sig) else f"SHAPE {cand_name} = {cand_sig}\n{body}"
        c = reg.cost(fragment)
        if best is None or c < best[2]:
            best = (cand_sig, cand_rows_hinted, c, body)
    assert best is not None
    sig, rows, fragment_cost, _ = best
    # Include REF-decl cost too — a promotion that hurts the doc more
    # than it saves at the table-body cost gate is a net loss.
    ref_decl_cost = sum(reg.cost(f"REF &{n} = {t}") for n, t in ref_decls)
    if not bypass and fragment_cost + ref_decl_cost >= reg.cost(json_line):
        return None
    reg.register(sig, hint)
    for ref_name, ref_text in ref_decls:
        reg.refs.append((ref_name, ref_text))
    return reg.peek(sig, hint), rows


def _collect_refs(
    value: list[dict[str, Any]],
    shape: Shape,
    reg: _Registry,
) -> tuple[dict[str, str], list[tuple[str, str]]]:
    """For each OBJECT-typed field, hoist duplicated sub-values into
    ``REF &name = (tuple)`` declarations. Returns (hash → ref_name map,
    list of (ref_name, ref_text) to append to reg.refs on commit).

    Only net-positive promotions are kept: the sum of inline emissions
    saved must exceed the REF declaration cost plus per-use ``&name``
    cost. Uses ``reg.cost`` so token- and character-modes decide the
    same way.
    """
    from collections import Counter

    refs_by_hash: dict[str, str] = {}
    ref_decls: list[tuple[str, str]] = []
    for f in shape.fields:
        if f.kind != OBJECT or f.shape is None:
            continue
        # Extract this field's per-row values; skip rows where it's absent.
        vals: list[dict[str, Any]] = []
        for row in value:
            v = row.get(f.name)
            if isinstance(v, dict):
                vals.append(v)
        if len(vals) < 2:
            continue
        hashes = [_canonical(v) for v in vals]
        counts = Counter(hashes)
        for h, count in counts.items():
            if count < 2 or h in refs_by_hash:
                continue
            # Cost model: pick the first matching value to emit.
            sample = vals[hashes.index(h)]
            tuple_text = _tuple(sample, f.shape, reg.labeled, {})
            ref_name = reg.mint_ref(f.name)
            use_text = f"&{ref_name}"
            saved = count * reg.cost(tuple_text) - (
                reg.cost(f"REF &{ref_name} = {tuple_text}")
                + count * reg.cost(use_text)
            )
            if saved > 0:
                refs_by_hash[h] = ref_name
                ref_decls.append((ref_name, tuple_text))
            else:
                # Unmint (release the name) so cost gates aren't polluted.
                reg.names.discard(ref_name)
    return refs_by_hash, ref_decls


def _canonical(value: Any) -> str:
    """Structural canonical form for hashing subtree equality."""
    return compact_json(_canon(value))


def _canon(value: Any) -> Any:
    if isinstance(value, dict):
        return {k: _canon(value[k]) for k in sorted(value)}
    if isinstance(value, list):
        return [_canon(x) for x in value]
    return value


def _elide_candidate(
    value: list[dict[str, Any]],
    shape: Shape,
    labeled: bool,
    refs_by_hash: dict[str, str] | None = None,
) -> tuple[str, list[str]] | None:
    """Compute the elided-shape variant, or ``None`` if nothing qualifies.

    A required scalar field qualifies for elision iff its most common
    value appears in ``ceil(ELIDE_THRESHOLD * n)`` or more rows. Optional
    fields never qualify — dropping them would collapse the ``absent`` vs
    ``defaulted`` distinction.
    """
    n = len(value)
    from collections import Counter

    threshold = -(-int(ELIDE_THRESHOLD * 100) * n // 100)  # ceil(0.8 * n)
    defaults: dict[str, Any] = {}
    for f in shape.fields:
        if f.optional or f.kind != SCALAR:
            continue
        # Hashable check: skip fields whose values include unhashable
        # types (shouldn't happen for scalars, but be defensive).
        try:
            counts = Counter(row.get(f.name) for row in value)
        except TypeError:
            continue
        mode_val, mode_count = counts.most_common(1)[0]
        if mode_count >= threshold:
            defaults[f.name] = mode_val
    if not defaults:
        return None
    reduced_fields = [f for f in shape.fields if f.name not in defaults]
    reduced = Shape(reduced_fields)
    reduced_sig_body = serialize_shape(reduced)
    defaults_clause = ",".join(
        f"{field_name_token(k)}={scalar_literal(v)}" for k, v in defaults.items()
    )
    sig = f"{reduced_sig_body} | defaults: {defaults_clause}"
    rows: list[str] = []
    for row in value:
        base = _tuple(row, reduced, labeled, refs_by_hash or {})
        overrides: list[str] = []
        for k, default_val in defaults.items():
            if row.get(k) != default_val:
                overrides.append(f"+{field_name_token(k)}={scalar_literal(row[k])}")
        if overrides:
            rows.append(base + " " + " ".join(overrides))
        else:
            rows.append(base)
    return sig, rows


def _intersperse_hints(
    rows: list[str], name: str, sig: str, every: int | None
) -> list[str]:
    """Insert ``# SHAPE name = {sig}`` comment lines every ``every`` rows.

    Only applied when the table has at least ``2 * every`` rows — a single
    reminder in a small table has no re-anchoring value.
    """
    if every is None or len(rows) < 2 * every:
        return rows
    out: list[str] = []
    comment = f"# SHAPE {name} = {sig}"
    for idx, row in enumerate(rows):
        if idx > 0 and idx % every == 0:
            out.append(comment)
        out.append(row)
    return out


def _root_array(value: list[Any], reg: _Registry) -> list[str] | None:
    if all(is_scalar(x) for x in value):
        inline = ",".join(scalar_literal(x) for x in value)
        head = f"[{len(value)}]:"
        return [head + (" " + inline if inline else "")]
    # At root, the JSON fallback is the whole compact JSON of the value;
    # there is no key/padding to prepend.
    header_prefix = f"[{len(value)}]" if reg.row_count_guardrail else "[]"
    json_line = compact_json(value)
    table = _try_table(value, "item", reg, header_prefix, json_line)
    if table is not None:
        name, rows = table
        return [f"{header_prefix}<{name}>:", *rows]
    return None


def _tuple(
    el: dict[str, Any],
    shape: Shape,
    labeled: bool = False,
    refs_by_hash: dict[str, str] | None = None,
) -> str:
    refs_by_hash = refs_by_hash or {}
    parts: list[str] = []
    for f in shape.fields:
        if f.name not in el:
            # Labeled tuples drop absent optional fields entirely — the
            # explicit key=value form makes presence self-describing.
            if labeled:
                continue
            parts.append("_")
        elif labeled:
            parts.append(
                f"{field_name_token(f.name)}={_field_value(el[f.name], f, labeled, refs_by_hash)}"
            )
        else:
            parts.append(_field_value(el[f.name], f, labeled, refs_by_hash))
    return "(" + ",".join(parts) + ")"


def _field_value(
    value: Any,
    f: Field,
    labeled: bool = False,
    refs_by_hash: dict[str, str] | None = None,
) -> str:
    refs_by_hash = refs_by_hash or {}
    if f.kind == RAW:
        return "!" + compact_json(value)
    if value is None:
        return "null"
    if f.kind == SCALAR:
        return scalar_literal(value)
    if f.kind == OBJECT:
        assert f.shape is not None
        if refs_by_hash and isinstance(value, dict):
            ref_name = refs_by_hash.get(_canonical(value))
            if ref_name is not None:
                return f"&{ref_name}"
        return _tuple(value, f.shape, labeled, refs_by_hash)
    if f.kind == TABLE:
        assert f.shape is not None
        return "[" + ",".join(_tuple(el, f.shape, labeled, refs_by_hash) for el in value) + "]"
    if f.kind == PARRAY:
        return "[" + ",".join(scalar_literal(x) for x in value) + "]"
    raise SoonEncodeError(f"unknown field kind: {f.kind}")  # pragma: no cover
