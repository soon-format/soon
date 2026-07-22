"""Format registry — one entry per column in the accuracy report.

Every format takes a Python value and returns a string the LLM can
read. Formats that vary the SOON encoder's ablation knobs live here
too — the harness treats each ablation arm as its own format.
"""

from __future__ import annotations

import json
from collections.abc import Callable
from typing import Any

try:
    import yaml as _yaml
except ImportError:  # pragma: no cover
    _yaml = None

from soon_format import encode as soon_encode

from .types import FormatSpec

Renderer = Callable[[Any], str]


PRIMERS: dict[str, FormatSpec] = {
    "toon": FormatSpec(
        "toon",
        "TOON: header ``array[count]{col1,col2,...}:`` declares columns once, "
        "then each row is indented comma-separated values in column order.",
        "toon",
    ),
    "gcf": FormatSpec(
        "gcf",
        "GCF: section headers ``## name [count]{col1,col2,...}`` declare columns, "
        "then rows are pipe-separated values. Nested objects are flattened with "
        "``>`` paths (e.g. ``customer>name``). Arrays use ``^`` placeholder "
        "followed by ``.field [count]`` sub-sections.",
        "gcf",
    ),
    "json": FormatSpec(
        "json",
        "JSON: repeated keys per object, strict, comma-separated.",
        "json",
    ),
    "json-pretty": FormatSpec(
        "json-pretty",
        "JSON: pretty-printed with 2-space indentation; content is identical to compact JSON.",
        "json",
    ),
    "yaml": FormatSpec(
        "yaml",
        "YAML: indentation-based, keys colon-separated, lists as ``- item``.",
        "yaml",
    ),
    "soon": FormatSpec(
        "soon",
        "SOON: shape declared once (``SHAPE name = {fields}``), then rows as "
        "positional tuples ``(v1,v2,...)`` in shape order.",
        "soon",
    ),
    "soon-labeled": FormatSpec(
        "soon-labeled",
        "SOON labeled: same as SOON but tuple values carry field labels "
        "``(id=1,name=Ada)``.",
        "soon",
    ),
    "soon-no-guardrail": FormatSpec(
        "soon-no-guardrail",
        "SOON: same as SOON but the table header omits the row count "
        "(``rows[]<shape>:``).",
        "soon",
    ),
    "soon-shape-hint": FormatSpec(
        "soon-shape-hint",
        "SOON: same as SOON but with ``# SHAPE name = {...}`` comment lines "
        "re-emitted every 10 rows.",
        "soon",
    ),
    "soon-elide": FormatSpec(
        "soon-elide",
        "SOON with ELIDE: majority-value columns are hoisted into "
        "``| defaults: k=v``; exceptional rows carry ``+k=v`` overrides.",
        "soon",
    ),
    "soon-ref": FormatSpec(
        "soon-ref",
        "SOON with REF: repeated OBJECT sub-values are hoisted into "
        "``REF &name = (...)`` and referenced inline via ``&name``.",
        "soon",
    ),
}


def _json(value: Any) -> str:
    return json.dumps(value, separators=(",", ":"), ensure_ascii=False)


def _json_pretty(value: Any) -> str:
    return json.dumps(value, indent=2, ensure_ascii=False)


def _yaml_render(value: Any) -> str:
    if _yaml is None:
        raise RuntimeError("PyYAML is required for the 'yaml' format")
    return _yaml.safe_dump(value, sort_keys=False, allow_unicode=True).rstrip("\n")


def _soon(value: Any) -> str:
    return soon_encode(value, mode="soon")


def _soon_labeled(value: Any) -> str:
    return soon_encode(value, mode="labeled")


def _soon_no_guardrail(value: Any) -> str:
    return soon_encode(value, mode="soon", row_count_guardrail=False)


def _soon_shape_hint(value: Any) -> str:
    return soon_encode(value, mode="soon", shape_hint_rows=10)


def _soon_elide(value: Any) -> str:
    return soon_encode(value, mode="soon", elide=True)


def _soon_ref(value: Any) -> str:
    return soon_encode(value, mode="soon", ref=True)


RENDERERS: dict[str, Renderer] = {
    "json": _json,
    "json-pretty": _json_pretty,
    "yaml": _yaml_render,
    "soon": _soon,
    "soon-labeled": _soon_labeled,
    "soon-no-guardrail": _soon_no_guardrail,
    "soon-shape-hint": _soon_shape_hint,
    "soon-elide": _soon_elide,
    "soon-ref": _soon_ref,
}


DEFAULT_FORMATS = ("json", "yaml", "toon", "gcf", "soon", "soon-labeled")


def render(value: Any, format_name: str) -> str:
    """Render *value* in the named format. Raises for unknown names."""
    if format_name == "toon":
        try:
            from toon_py import encode as toon_encode  # type: ignore[import-not-found]
        except ImportError as exc:  # pragma: no cover
            raise RuntimeError(
                "The 'toon-py' package is required for the 'toon' format. "
                "Install with: pip install toon-py"
            ) from exc
        return toon_encode(value)
    if format_name == "gcf":
        from .gcf_encoder import encode as gcf_encode
        return gcf_encode(value)
    renderer = RENDERERS.get(format_name)
    if renderer is None:
        raise KeyError(f"unknown format: {format_name!r}")
    return renderer(value)
