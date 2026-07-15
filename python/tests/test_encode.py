"""Golden encoding tests (complement to the conformance suite)."""

import pytest

from soon_format import SoonEncodeError, decode, encode

HIKES = {
    "context": {"task": "Our favorite hikes together", "location": "Boulder"},
    "friends": ["ana", "luis", "sam"],
    "hikes": [
        {"id": 1, "name": "Blue Lake Trail", "km": 7.5, "sunny": True},
        {"id": 2, "name": "Ridge Overlook", "km": 9.2, "sunny": False},
        {"id": 3, "name": "Wildflower Loop", "km": 5.1, "sunny": True},
    ],
}


def test_hikes_golden():
    doc = encode(HIKES, mode="soon")
    assert doc == (
        "SHAPE hikes = {id,name,km,sunny}\n"
        "context:\n"
        "  task: Our favorite hikes together\n"
        "  location: Boulder\n"
        "friends[3]: ana,luis,sam\n"
        "hikes[3]<hikes>:\n"
        "(1,Blue Lake Trail,7.5,true)\n"
        "(2,Ridge Overlook,9.2,false)\n"
        "(3,Wildflower Loop,5.1,true)"
    )
    assert decode(doc) == HIKES


def test_optional_fields():
    # Enough rows that the SHAPE-table form is genuinely cheaper than raw
    # inline-JSON — otherwise _try_table's honest cost model correctly
    # picks the smaller RAW form, and this test would exercise nothing
    # about optional-field detection.
    data = {
        "users": [
            {"id": 1, "name": "Ada", "email": "ada@x.co"},
            {"id": 2, "name": "Linus"},
            {"id": 3, "name": "Grace", "email": "grace@x.co"},
            {"id": 4, "name": "Alan"},
            {"id": 5, "name": "Barbara", "email": "b@x.co"},
        ]
    }
    doc = encode(data, mode="soon")
    assert "?email" in doc
    assert "(2,Linus,_)" in doc
    assert "(4,Alan,_)" in doc
    assert decode(doc) == data


def test_null_vs_missing():
    # Uniform-enough rows that the TABLE form wins the cost compare
    # against ``![...]``. Tests the null-vs-absent distinction in the
    # emitted tuples.
    data = {
        "rows": [
            {"a": 1, "b": None},
            {"a": 2},
            {"a": 3, "b": None},
            {"a": 4},
            {"a": 5},
            {"a": 6, "b": None},
            {"a": 7},
            {"a": 8, "b": None},
        ]
    }
    doc = encode(data, mode="soon")
    assert "(1,null)" in doc
    assert "(2,_)" in doc
    assert decode(doc) == data


def test_shape_reuse():
    quad = [{"x": 1, "y": 2}, {"x": 3, "y": 4}, {"x": 5, "y": 6}, {"x": 7, "y": 8}]
    data = {"first": quad, "second": quad}
    doc = encode(data, mode="soon")
    assert doc.count("SHAPE ") == 1
    assert "second[4]<first>:" in doc
    assert decode(doc) == data


def test_mixed_kind_field_uses_raw():
    data = {
        "events": [
            {"ts": 1000001, "payload": {"a": 1}},
            {"ts": 1000002, "payload": "plain text here"},
            {"ts": 1000003, "payload": {"a": 2}},
            {"ts": 1000004, "payload": "another plain one"},
        ]
    }
    doc = encode(data, mode="soon")
    assert "payload:!" in doc
    assert decode(doc) == data


def test_never_worse_guarantee():
    # Non-uniform data: auto mode output must never exceed compact JSON.
    import json

    for data in [
        {"a": [1, [2], {"b": 3}]},
        {},
        [],
        {"x": {}},
        [{"only": "one"}],
        {"k": "v"},
    ]:
        doc = encode(data)
        assert len(doc) <= len(json.dumps(data, separators=(",", ":")))
        assert decode(doc) == data


def test_root_scalars_fall_back_to_json():
    for value in [42, "hello", None, True, 3.14]:
        doc = encode(value, mode="soon")
        assert decode(doc) == value


def test_non_finite_rejected():
    with pytest.raises(SoonEncodeError):
        encode({"x": float("nan")})


def test_non_string_keys_rejected():
    with pytest.raises(SoonEncodeError):
        encode({"rows": [{1: "a", 2: "b"}, {1: "c"}]}, mode="soon")


def test_quoting_edges():
    data = {
        "vals": [
            {"s": "_"},
            {"s": "null"},
            {"s": "-12.5"},
            {"s": "with, comma"},
            {"s": "(paren)"},
            {"s": " padded "},
            {"s": "plain words"},
            {"s": ""},
        ]
    }
    doc = encode(data, mode="soon")
    assert decode(doc) == data


def test_unicode():
    data = {"şehir": "İzmir", "notes": [{"t": "çok güzel"}, {"t": "harika ✨"}]}
    doc = encode(data, mode="soon")
    assert decode(doc) == data


def test_empty_containers():
    data = {"a": [], "b": {}, "c": [[]], "d": [{}]}
    doc = encode(data, mode="soon")
    assert decode(doc) == data


def test_deterministic():
    assert encode(HIKES) == encode(HIKES)


def test_tokenizer_flips_local_decision():
    """Same input; different cost fn → different output. Proves the cost
    function reaches every decision (not just the outer doc-level compare)."""
    tiktoken = pytest.importorskip("tiktoken")
    del tiktoken  # ensure the import succeeded; encode() will look it up itself
    data = {
        "items": [
            {"emoji": "🌟", "name": "star"},
            {"emoji": "🔥", "name": "fire"},
            {"emoji": "✨", "name": "spark"},
        ]
    }
    char_doc = encode(data)
    token_doc = encode(data, tokenizer="o200k_base")
    assert char_doc != token_doc
    # Char-cost picks the SOON table; token-cost falls back to compact JSON.
    assert char_doc.startswith("SHAPE items =")
    assert token_doc.startswith("{")
    # Round-trip both.
    assert decode(char_doc) == data
    assert decode(token_doc) == data


def test_tokenizer_deterministic():
    pytest.importorskip("tiktoken")
    assert encode(HIKES, tokenizer="o200k_base") == encode(HIKES, tokenizer="o200k_base")


def test_labeled_mode_golden():
    doc = encode(HIKES, mode="labeled")
    assert doc == (
        "SHAPE hikes = {id,name,km,sunny}\n"
        "context:\n"
        "  task: Our favorite hikes together\n"
        "  location: Boulder\n"
        "friends[3]: ana,luis,sam\n"
        "hikes[3]<hikes>:\n"
        "(id=1,name=Blue Lake Trail,km=7.5,sunny=true)\n"
        "(id=2,name=Ridge Overlook,km=9.2,sunny=false)\n"
        "(id=3,name=Wildflower Loop,km=5.1,sunny=true)"
    )
    assert decode(doc) == HIKES


def test_labeled_mode_optional_omitted():
    data = {
        "users": [
            {"id": 1, "name": "Ada", "email": "ada@x.co"},
            {"id": 2, "name": "Linus"},
            {"id": 3, "name": "Grace", "email": "grace@x.co"},
            {"id": 4, "name": "Alan"},
            {"id": 5, "name": "Barbara", "email": "b@x.co"},
        ]
    }
    doc = encode(data, mode="labeled")
    assert "(id=2,name=Linus)" in doc
    assert "(id=4,name=Alan)" in doc
    assert "email=" in doc
    assert "_" not in doc.split("\n", 1)[1]  # no positional sentinel in body
    assert decode(doc) == data


def test_labeled_mode_nested_and_tables():
    data = {
        "orders": [
            {
                "id": 1,
                "customer": {"name": "Ada", "city": "Boulder"},
                "items": [{"sku": "A1", "qty": 2}, {"sku": "B2", "qty": 1}],
            },
            {
                "id": 2,
                "customer": {"name": "Linus", "city": "Helsinki"},
                "items": [{"sku": "A1", "qty": 3}, {"sku": "C3", "qty": 5}],
            },
            {
                "id": 3,
                "customer": {"name": "Grace", "city": "Arlington"},
                "items": [{"sku": "A1", "qty": 1}, {"sku": "B2", "qty": 2}],
            },
        ]
    }
    doc = encode(data, mode="labeled")
    assert "customer=(name=Ada,city=Boulder)" in doc
    assert "items=[(sku=A1,qty=2),(sku=B2,qty=1)]" in doc
    assert decode(doc) == data


def test_labeled_mode_rejects_underscore():
    from soon_format import SoonDecodeError

    doc = "SHAPE r = {?a,?b}\nrows[1]<r>:\n(a=1,_)"
    with pytest.raises(SoonDecodeError):
        decode(doc)


def test_labeled_mode_unknown_field_rejected():
    from soon_format import SoonDecodeError

    doc = "SHAPE r = {id,name}\nrows[1]<r>:\n(id=1,name=Ada,extra=oops)"
    with pytest.raises(SoonDecodeError):
        decode(doc)


def test_labeled_mode_missing_required_rejected():
    from soon_format import SoonDecodeError

    doc = "SHAPE r = {id,name}\nrows[1]<r>:\n(id=1)"
    with pytest.raises(SoonDecodeError):
        decode(doc)


def test_labeled_mode_unknown_mode_rejected():
    with pytest.raises(ValueError):
        encode({"x": 1}, mode="not_a_mode")


def _long_hikes(n: int) -> dict:
    return {
        "hikes": [
            {"id": i, "name": f"Trail{i}", "km": float(i), "sunny": i % 2 == 0}
            for i in range(1, n + 1)
        ]
    }


def test_shape_hint_rows_interspersed_and_roundtrips():
    doc = encode(_long_hikes(10), mode="soon", shape_hint_rows=3)
    lines = doc.split("\n")
    comment_lines = [ln for ln in lines if ln.startswith("#")]
    assert comment_lines, "expected at least one hint comment line"
    assert all(ln == "# SHAPE hikes = {id,name,km,sunny}" for ln in comment_lines)
    # 10 rows, every=3, floor((10-1)/3)=3 → hints before rows 3, 6, 9
    assert len(comment_lines) == 3
    assert decode(doc) == _long_hikes(10)


def test_shape_hint_rows_skipped_for_short_tables():
    # 4 rows with every=3 → 4 < 2*3, no reminders.
    doc = encode(_long_hikes(4), mode="soon", shape_hint_rows=3)
    assert "#" not in doc
    assert decode(doc) == _long_hikes(4)


def test_shape_hint_rows_composes_with_labeled():
    doc = encode(_long_hikes(6), mode="labeled", shape_hint_rows=2)
    assert "# SHAPE hikes = {id,name,km,sunny}" in doc
    assert "(id=1,name=Trail1" in doc
    assert decode(doc) == _long_hikes(6)


def test_shape_hint_rows_zero_rejected():
    with pytest.raises(ValueError):
        encode({"x": 1}, shape_hint_rows=0)


def test_row_count_guardrail_off_omits_n():
    data = _long_hikes(6)
    doc = encode(data, mode="soon", row_count_guardrail=False)
    assert "hikes[]<hikes>:" in doc
    assert "[6]" not in doc
    assert decode(doc) == data


def test_row_count_guardrail_off_roundtrips_with_labeled_and_hints():
    data = _long_hikes(8)
    doc = encode(
        data, mode="labeled", shape_hint_rows=3, row_count_guardrail=False
    )
    assert "hikes[]<hikes>:" in doc
    assert "# SHAPE hikes = " in doc
    assert "(id=1,name=Trail1" in doc
    assert decode(doc) == data


def test_row_count_guardrail_off_root_array():
    data = [{"a": i, "b": i * i} for i in range(1, 5)]
    doc = encode(data, mode="soon", row_count_guardrail=False)
    assert doc.startswith("SHAPE item = ")
    assert "\n[]<item>:" in doc
    assert decode(doc) == data


def test_primitive_array_still_requires_count():
    from soon_format import SoonDecodeError

    # Encoder never emits ``[]`` for primitive arrays; decoder still rejects
    # a hand-crafted document that tries it.
    with pytest.raises(SoonDecodeError):
        decode("nums[]: 1,2,3")


def test_guardrail_off_terminates_at_dedent_or_eof():
    data = {"rows": [{"a": 1}, {"a": 2}, {"a": 3}], "next": "sentinel"}
    doc = encode(data, mode="soon", row_count_guardrail=False)
    # ``next: sentinel`` is a normal entry after the rows block; unindented
    # non-``(`` line terminates the guardrail-less table.
    assert decode(doc) == data


def _sparse_users(n_active: int, n_other: int) -> dict:
    users = [
        {"id": i + 1, "name": f"u{i+1}", "status": "active"}
        for i in range(n_active)
    ]
    users += [
        {"id": n_active + i + 1, "name": f"u{n_active+i+1}", "status": "cancelled"}
        for i in range(n_other)
    ]
    return {"users": users}


def test_elide_drops_majority_column():
    # 9/10 active → status field elides.
    data = _sparse_users(9, 1)
    doc = encode(data, mode="soon", elide=True)
    assert "| defaults: status=active" in doc
    assert "+status=cancelled" in doc
    # Non-override rows have no trailing +override.
    active_rows = [ln for ln in doc.split("\n") if ln.startswith("(") and "+" not in ln]
    assert len(active_rows) == 9
    assert decode(doc) == data


def test_elide_no_op_when_below_threshold():
    # 6/10 active → below 80% → no elision.
    data = _sparse_users(6, 4)
    doc = encode(data, mode="soon", elide=True)
    assert "| defaults" not in doc
    assert decode(doc) == data


def test_elide_off_by_default():
    data = _sparse_users(9, 1)
    doc = encode(data, mode="soon")
    assert "| defaults" not in doc
    assert decode(doc) == data


def test_elide_composes_with_labeled():
    data = _sparse_users(9, 1)
    doc = encode(data, mode="labeled", elide=True)
    assert "| defaults: status=active" in doc
    assert "(id=1,name=u1)" in doc
    assert "+status=cancelled" in doc
    assert decode(doc) == data


def test_elide_composes_with_guardrail_off():
    data = _sparse_users(9, 1)
    doc = encode(data, mode="soon", elide=True, row_count_guardrail=False)
    assert "users[]<users>:" in doc
    assert "| defaults: status=active" in doc
    assert decode(doc) == data


def test_elide_multi_column():
    data = {
        "rows": [
            {"id": i + 1, "a": "x", "b": "y"} for i in range(8)
        ] + [
            {"id": 9, "a": "x", "b": "z"},
            {"id": 10, "a": "q", "b": "y"},
        ]
    }
    doc = encode(data, mode="soon", elide=True)
    assert "| defaults: a=x,b=y" in doc or "| defaults: b=y,a=x" in doc
    assert decode(doc) == data


def test_decoder_rejects_override_of_undeclared_field():
    from soon_format import SoonDecodeError

    doc = (
        "SHAPE r = {id,name} | defaults: status=active\n"
        "rows[1]<r>:\n"
        "(1,Ada) +nonexistent=oops"
    )
    with pytest.raises(SoonDecodeError):
        decode(doc)


def test_decoder_rejects_default_colliding_with_field():
    from soon_format import SoonDecodeError

    doc = "SHAPE r = {id,name,status} | defaults: status=active\nrows[0]<r>:"
    with pytest.raises(SoonDecodeError):
        decode(doc)


def test_comment_lines_ignored_by_decoder():
    # A hand-written comment between entries and inside a table.
    doc = (
        "SHAPE t = {a,b}\n"
        "# top-level comment\n"
        "x: 1\n"
        "  # indented comment (still skipped)\n"
        "rows[2]<t>:\n"
        "# between-rows comment\n"
        "(1,2)\n"
        "# another between-rows comment\n"
        "(3,4)"
    )
    assert decode(doc) == {"x": 1, "rows": [{"a": 1, "b": 2}, {"a": 3, "b": 4}]}
