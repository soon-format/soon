#!/usr/bin/env python3
"""Generate the shared conformance suite from the Python reference implementation.

Run from the repo root:
    PYTHONPATH=python/src python3 tools/gen_conformance.py

Outputs are frozen fixtures: regenerating must be a deliberate act tied to a
spec change (see CONTRIBUTING.md). Review diffs carefully.
"""

from __future__ import annotations

import json
import sys
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parents[1] / "python" / "src"))

from soon_format import decode, encode  # noqa: E402

ROOT = Path(__file__).resolve().parents[1] / "conformance"

ORDERS = [
    {
        "id": 1,
        "customer": {"name": "Ada", "tier": "gold", "address": {"city": "Boulder", "zip": "80301"}},
        "items": [{"sku": "A1", "qty": 2, "price": 9.5}, {"sku": "B2", "qty": 1, "price": 4.25}],
    },
    {
        "id": 2,
        "customer": {"name": "Linus", "tier": "silver", "address": {"city": "Helsinki", "zip": "00100"}},
        "items": [{"sku": "A1", "qty": 1, "price": 9.5}],
    },
    {
        "id": 3,
        "customer": {"name": "Grace", "tier": "gold", "address": {"city": "Arlington", "zip": "22201"}},
        "items": [],
    },
]

ENCODE_CASES: list[dict] = [
    {
        "name": "flat_object",
        "options": {"mode": "soon"},
        "input": {"name": "Ada", "age": 36, "active": True, "score": 7.5, "note": None},
    },
    {
        "name": "primitive_arrays",
        "options": {"mode": "soon"},
        "input": {"tags": ["a", "b c", "true", "3", ""], "nums": [1, 2.5, -3], "empty": []},
    },
    {
        "name": "table_basic",
        "options": {"mode": "soon"},
        "input": {
            "hikes": [
                {"id": 1, "name": "Blue Lake Trail", "km": 7.5, "sunny": True},
                {"id": 2, "name": "Ridge Overlook", "km": 9.2, "sunny": False},
                {"id": 3, "name": "Wildflower Loop", "km": 5.1, "sunny": True},
            ]
        },
    },
    {
        "name": "table_optionals_null_vs_missing",
        "options": {"mode": "soon"},
        "input": {
            "users": [
                {"id": 1, "name": "Ada", "email": "ada@x.co", "phone": None},
                {"id": 2, "name": "Linus"},
                {"id": 3, "name": "Grace", "email": "grace@x.co"},
                {"id": 4, "name": "Edsger", "phone": None},
            ]
        },
    },
    {
        "name": "nested_orders",
        "options": {"mode": "soon"},
        "input": {"orders": ORDERS},
    },
    {
        "name": "root_table",
        "options": {"mode": "soon"},
        "input": ORDERS,
    },
    {
        "name": "root_primitive_array",
        "options": {"mode": "soon"},
        "input": [1, 2.5, "three", None, True],
    },
    {
        "name": "mixed_kind_field_raw",
        "options": {"mode": "soon"},
        "input": {
            "events": [
                {"ts": 1000001, "payload": {"a": 1}},
                {"ts": 1000002, "payload": "plain text here"},
                {"ts": 1000003, "payload": [1, 2, 3]},
                {"ts": 1000004, "payload": None},
            ]
        },
    },
    {
        "name": "nonuniform_array_escape",
        "options": {"mode": "soon"},
        "input": {"weird": [1, [2], {"b": 3}], "normal": "fine"},
    },
    {
        "name": "quoting_edges",
        "options": {"mode": "soon"},
        "input": {
            "vals": [
                {"s": "_"},
                {"s": "null"},
                {"s": "-12.5"},
                {"s": "1e5"},
                {"s": "with, comma"},
                {"s": "(paren)"},
                {"s": " padded "},
                {"s": "plain words"},
                {"s": ""},
                {"s": "tab\there"},
            ]
        },
    },
    {
        "name": "unicode",
        "options": {"mode": "soon"},
        "input": {"şehir": "İzmir", "notes": [{"t": "çok güzel"}, {"t": "harika ✨"}, {"t": "日本語"}]},
    },
    {
        "name": "empty_containers",
        "options": {"mode": "soon"},
        "input": {"a": [], "b": {}, "c": [[]], "d": [{}]},
    },
    {
        "name": "shape_reuse",
        "options": {"mode": "soon"},
        "input": {
            "q1": [{"x": 1, "y": 2}, {"x": 3, "y": 4}, {"x": 5, "y": 6}, {"x": 7, "y": 8}],
            "q2": [{"x": 9, "y": 10}, {"x": 11, "y": 12}, {"x": 13, "y": 14}, {"x": 15, "y": 16}],
        },
    },
    {
        "name": "deep_nesting",
        "options": {"mode": "soon"},
        "input": {
            "app": {
                "server": {
                    "http": {"host": "0.0.0.0", "port": 8080},
                    "limits": {"maxBody": 1048576},
                },
                "workers": [
                    {"id": "w1", "queues": ["default", "mail"], "opts": {"retries": 3, "backoff": "exp"}},
                    {"id": "w2", "queues": ["default"], "opts": {"retries": 5, "backoff": "lin"}},
                    {"id": "w3", "queues": [], "opts": {"retries": 1, "backoff": "exp"}},
                ],
            }
        },
    },
    {
        "name": "quoted_keys",
        "options": {"mode": "soon"},
        "input": {"weird key": 1, "a:b": 2, "rows": [{"has space": 1, "ok": 2}, {"has space": 3, "ok": 4}, {"has space": 5, "ok": 6}]},
    },
    {
        "name": "auto_fallback_small",
        "options": {"mode": "auto"},
        "input": {"a": 1},
    },
    {
        "name": "auto_fallback_empty_object",
        "options": {"mode": "auto"},
        "input": {},
    },
    {
        "name": "auto_prefers_soon_when_smaller",
        "options": {"mode": "auto"},
        "input": {"orders": ORDERS},
    },
]

DECODE_CASES: list[dict] = [
    {
        "name": "lenient_spaces_in_rows",
        "input": "SHAPE u = {id,name}\nusers[2]<u>:\n(1, Ada)\n(2, Linus)",
        "expected": {"users": [{"id": 1, "name": "Ada"}, {"id": 2, "name": "Linus"}]},
    },
    {
        "name": "trailing_newline",
        "input": "a: 1\n",
        "expected": {"a": 1},
    },
    {
        "name": "blank_line_between_entries",
        "input": "a: 1\n\nb: 2",
        "expected": {"a": 1, "b": 2},
    },
    {
        "name": "json_fallback_object",
        "input": "{\"a\":[1,2],\"b\":null}",
        "expected": {"a": [1, 2], "b": None},
    },
    {
        "name": "json_fallback_scalar",
        "input": "\"hello\"",
        "expected": "hello",
    },
    {
        "name": "raw_null_field_value",
        "input": "SHAPE e = {ts,payload:!}\nevents[1]<e>:\n(1,!null)",
        "expected": {"events": [{"ts": 1, "payload": None}]},
    },
]

ERROR_CASES: list[dict] = [
    {"name": "row_count_short", "input": "SHAPE u = {id}\nusers[3]<u>:\n(1)\n(2)"},
    {"name": "unknown_shape", "input": "users[1]<nope>:\n(1)"},
    {"name": "underscore_required", "input": "SHAPE u = {id,name}\nusers[1]<u>:\n(1,_)"},
    {"name": "bad_indent", "input": "a:\n   b: 1"},
    {"name": "trailing_garbage", "input": "a: 1\n)))"},
    {"name": "primitive_count_mismatch", "input": "xs[3]: 1,2"},
    {"name": "unterminated_tuple", "input": "SHAPE u = {id}\nusers[1]<u>:\n(1"},
    {"name": "duplicate_key", "input": "a: 1\na: 2"},
    {"name": "empty_document", "input": ""},
    {"name": "bad_inline_json", "input": "a: !{broken"},
]

ROUNDTRIP_CASES: list[dict] = [
    {"name": "orders", "input": {"orders": ORDERS}},
    {"name": "empty_everything", "input": {"a": [], "b": {}, "c": None, "d": ""}},
    {"name": "numbers", "input": {"xs": [0, -1, 3.5, 1e-3, 123456789, -0.25]}},
    {
        "name": "optionals_torture",
        "input": {
            "rows": [
                {"a": 1},
                {"b": 2},
                {"a": 3, "b": 4, "c": {"deep": [{"x": 1}, {"x": 2}]}},
                {"c": {"deep": []}},
                {"a": None, "b": None},
            ]
        },
    },
    {
        "name": "strings_torture",
        "input": {
            "rows": [
                {"s": "line\nbreak"},
                {"s": "quote\"inside"},
                {"s": "back\\slash"},
                {"s": "ünïcodé 🎒"},
                {"s": "ends with space "},
                {"s": "[bracket]"},
                {"s": "{brace}"},
                {"s": "!bang"},
            ]
        },
    },
    {"name": "root_array_of_arrays", "input": [[1, 2], [3, 4]]},
    {"name": "single_element_table", "input": {"one": [{"only": 1}]}},
]


def main() -> None:
    for sub in ("encode", "decode", "roundtrip", "errors"):
        (ROOT / sub).mkdir(parents=True, exist_ok=True)

    for case in ENCODE_CASES:
        expected = encode(case["input"], **case["options"])
        assert decode(expected) == case["input"], f"self-check failed: {case['name']}"
        fixture = {"input": case["input"], "options": case["options"], "expected": expected}
        path = ROOT / "encode" / f"{case['name']}.json"
        path.write_text(json.dumps(fixture, indent=2, ensure_ascii=False) + "\n", encoding="utf-8")

    for case in DECODE_CASES:
        assert decode(case["input"]) == case["expected"], f"self-check failed: {case['name']}"
        fixture = {"input": case["input"], "expected": case["expected"]}
        path = ROOT / "decode" / f"{case['name']}.json"
        path.write_text(json.dumps(fixture, indent=2, ensure_ascii=False) + "\n", encoding="utf-8")

    for case in ERROR_CASES:
        path = ROOT / "errors" / f"{case['name']}.json"
        path.write_text(
            json.dumps({"input": case["input"]}, indent=2, ensure_ascii=False) + "\n",
            encoding="utf-8",
        )

    for case in ROUNDTRIP_CASES:
        for mode in ("auto", "soon"):
            assert decode(encode(case["input"], mode=mode)) == case["input"], case["name"]
        path = ROOT / "roundtrip" / f"{case['name']}.json"
        path.write_text(
            json.dumps({"input": case["input"]}, indent=2, ensure_ascii=False) + "\n",
            encoding="utf-8",
        )

    total = len(ENCODE_CASES) + len(DECODE_CASES) + len(ERROR_CASES) + len(ROUNDTRIP_CASES)
    print(f"wrote {total} fixtures to {ROOT}")


if __name__ == "__main__":
    main()
