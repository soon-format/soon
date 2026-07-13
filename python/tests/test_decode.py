"""Decoder behaviour and error handling."""

import pytest

from soon_format import SoonDecodeError, decode


def test_json_fallback_documents():
    assert decode('{"a":1}') == {"a": 1}
    assert decode("[1,2]") == [1, 2]
    assert decode('"hello"') == "hello"
    assert decode("null") is None


def test_lenient_spaces_and_trailing_newline():
    doc = (
        "SHAPE u = {id,name}\n"
        "users[2]<u>:\n"
        "(1, Ada)\n"
        "(2, Linus)\n"
    )
    assert decode(doc) == {"users": [{"id": 1, "name": "Ada"}, {"id": 2, "name": "Linus"}]}


def test_quoted_keys():
    assert decode('"weird key": 5') == {"weird key": 5}


def test_row_count_mismatch():
    with pytest.raises(SoonDecodeError):
        decode("SHAPE u = {id}\nusers[3]<u>:\n(1)\n(2)")


def test_unknown_shape():
    with pytest.raises(SoonDecodeError):
        decode("users[1]<nope>:\n(1)")


def test_underscore_for_required_field():
    with pytest.raises(SoonDecodeError):
        decode("SHAPE u = {id,name}\nusers[1]<u>:\n(1,_)")


def test_bad_indentation():
    with pytest.raises(SoonDecodeError):
        decode("a:\n   b: 1")


def test_trailing_garbage():
    with pytest.raises(SoonDecodeError):
        decode("a: 1\n)))")


def test_empty_document():
    with pytest.raises(SoonDecodeError):
        decode("")
    with pytest.raises(SoonDecodeError):
        decode("   \n  ")


def test_primitive_array_count_mismatch():
    with pytest.raises(SoonDecodeError):
        decode("xs[3]: 1,2")


def test_duplicate_keys_rejected():
    with pytest.raises(SoonDecodeError):
        decode("a: 1\na: 2")


def test_malformed_tuple():
    with pytest.raises(SoonDecodeError):
        decode("SHAPE u = {id}\nusers[1]<u>:\n(1")
