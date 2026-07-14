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
