"""Run the shared, language-agnostic conformance suite."""

import json
from pathlib import Path

import pytest

from soon_format import SoonDecodeError, decode, encode

CONFORMANCE = Path(__file__).resolve().parents[2] / "conformance"


def _fixtures(sub: str) -> list:
    files = sorted((CONFORMANCE / sub).glob("*.json"))
    assert files, f"no fixtures found in {CONFORMANCE / sub}"
    return [pytest.param(json.loads(f.read_text(encoding="utf-8")), id=f.stem) for f in files]


@pytest.mark.parametrize("case", _fixtures("encode"))
def test_encode(case):
    assert encode(case["input"], **case.get("options", {})) == case["expected"]


@pytest.mark.parametrize("case", _fixtures("decode"))
def test_decode(case):
    assert decode(case["input"]) == case["expected"]


@pytest.mark.parametrize("case", _fixtures("roundtrip"))
def test_roundtrip(case):
    for mode in ("auto", "soon"):
        assert decode(encode(case["input"], mode=mode)) == case["input"]


@pytest.mark.parametrize("case", _fixtures("errors"))
def test_errors(case):
    with pytest.raises(SoonDecodeError):
        decode(case["input"])
