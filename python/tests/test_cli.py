"""End-to-end tests for the ``soon`` CLI."""

from __future__ import annotations

import io
import json
from contextlib import redirect_stderr, redirect_stdout

import pytest

from soon_format import decode
from soon_format.cli import main

SAMPLE = {"users": [{"id": 1, "name": "Ada"}, {"id": 2, "name": "Linus"}]}


def _run(args: list[str], stdin: str = "") -> tuple[int, str, str]:
    out, err = io.StringIO(), io.StringIO()
    import sys

    saved_stdin = sys.stdin
    sys.stdin = io.StringIO(stdin)
    try:
        with redirect_stdout(out), redirect_stderr(err):
            rc = main(args)
    finally:
        sys.stdin = saved_stdin
    return rc, out.getvalue(), err.getvalue()


def test_encode_decode_roundtrip_via_stdin():
    rc, out, _ = _run(["encode", "-"], stdin=json.dumps(SAMPLE))
    assert rc == 0
    assert decode(out) == SAMPLE

    rc, dec, _ = _run(["decode", "-"], stdin=out)
    assert rc == 0
    assert json.loads(dec) == SAMPLE


def test_decode_pretty_indents_output():
    rc, encoded, _ = _run(["encode", "-"], stdin=json.dumps(SAMPLE))
    assert rc == 0

    rc, compact, _ = _run(["decode", "-"], stdin=encoded)
    rc2, pretty, _ = _run(["decode", "-", "--pretty"], stdin=encoded)
    assert rc == 0 and rc2 == 0
    assert "\n" not in compact.rstrip("\n")
    assert "\n  " in pretty  # 2-space indent present
    assert json.loads(compact) == json.loads(pretty) == SAMPLE


def test_encode_stats_writes_to_stderr():
    rc, _, err = _run(["encode", "-", "--stats"], stdin=json.dumps(SAMPLE))
    assert rc == 0
    report = json.loads(err.strip().splitlines()[-1])
    assert {"json_chars", "soon_chars", "saving", "fallback"} <= report.keys()


def test_check_reports_ok_and_exits_zero():
    rc, _, err = _run(["check", "-"], stdin=json.dumps(SAMPLE))
    assert rc == 0
    assert "round-trip OK" in err


def test_bad_json_input_exits_nonzero():
    rc, _, err = _run(["encode", "-"], stdin="{not json")
    assert rc == 1
    assert "error" in err


def test_unknown_mode_rejected():
    with pytest.raises(SystemExit):
        _run(["encode", "-", "--mode", "bogus"], stdin=json.dumps(SAMPLE))
