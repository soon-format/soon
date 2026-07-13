"""Encode/decode throughput via pytest-benchmark.

Run from the repo root:
    PYTHONPATH=python/src:benchmarks python3 -m pytest benchmarks/test_speed.py -q
"""

import json

import pytest
from datasets import l5_nested_uniform_large, l7_semi_uniform

from soon_format import decode, encode

L5 = l5_nested_uniform_large()
L7 = l7_semi_uniform()
L5_DOC = encode(L5)
L7_DOC = encode(L7)


@pytest.mark.parametrize("data,label", [(L5, "L5-nested"), (L7, "L7-semi")], ids=["L5", "L7"])
def test_encode_speed(benchmark, data, label):
    benchmark(encode, data)


@pytest.mark.parametrize("doc,expected", [(L5_DOC, L5), (L7_DOC, L7)], ids=["L5", "L7"])
def test_decode_speed(benchmark, doc, expected):
    assert benchmark(decode, doc) == expected


@pytest.mark.parametrize("data", [L5], ids=["L5"])
def test_json_baseline_speed(benchmark, data):
    """Reference point: stdlib compact json.dumps on the same payload."""
    benchmark(json.dumps, data, separators=(",", ":"))
