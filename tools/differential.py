#!/usr/bin/env python3
"""Differential test: Python and TypeScript encoders must produce
byte-identical output for every conformance input.

Requires sibling repos:
  - ../soon-python:      pip install -e ../soon-python
  - ../soon-typescript:  cd ../soon-typescript && npm ci && npm run build

Run from the repo root: python3 tools/differential.py

Note: tests/cross-language-matrix.py is the full NxN matrix version of
this test that also cross-decodes. This script is the simpler encode-only
variant kept for quick local checks.
"""

from __future__ import annotations

import json
import subprocess
import sys
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]

from soon_format import encode  # noqa: E402

_V01_MODES = {"auto", "soon", "json"}
_V02_ONLY_OPTIONS = {"shape_hint_rows", "row_count_guardrail", "elide", "ref"}

TS_ROOT = ROOT.parent / "soon-typescript"

NODE_SNIPPET = """
const { encode } = await import("./dist/index.js");
const { readFileSync } = await import("node:fs");
const cases = JSON.parse(readFileSync(0, "utf-8"));
process.stdout.write(JSON.stringify(cases.map((c) => encode(c.input, c.options ?? {}))));
"""


def main() -> int:
    if not TS_ROOT.exists():
        print(f"error: {TS_ROOT} not found — clone soon-typescript alongside this repo")
        return 2

    cases = []
    for f in sorted((ROOT / "conformance" / "encode").glob("*.json")):
        fixture = json.loads(f.read_text(encoding="utf-8"))
        opts = fixture.get("options", {})
        if opts.get("mode", "auto") not in _V01_MODES:
            continue
        if _V02_ONLY_OPTIONS & opts.keys():
            continue
        cases.append({"name": f.stem, "input": fixture["input"], "options": opts})
    for f in sorted((ROOT / "conformance" / "roundtrip").glob("*.json")):
        fixture = json.loads(f.read_text(encoding="utf-8"))
        for mode in ("auto", "soon"):
            cases.append({"name": f"{f.stem}:{mode}", "input": fixture["input"], "options": {"mode": mode}})

    result = subprocess.run(
        ["node", "--input-type=module", "-e", NODE_SNIPPET],
        input=json.dumps(cases),
        capture_output=True,
        text=True,
        cwd=TS_ROOT,
        check=True,
    )
    ts_outputs = json.loads(result.stdout)
    if len(ts_outputs) != len(cases):
        print(
            f"protocol error: TS returned {len(ts_outputs)} outputs for {len(cases)} cases",
            file=sys.stderr,
        )
        return 2

    failures = 0
    for case, ts_out in zip(cases, ts_outputs, strict=True):
        py_out = encode(case["input"], **case["options"])
        if py_out != ts_out:
            failures += 1
            print(f"MISMATCH {case['name']}\n  py: {py_out!r}\n  ts: {ts_out!r}")
    if failures:
        print(f"{failures}/{len(cases)} cases diverged")
        return 1
    print(f"differential OK: {len(cases)} cases byte-identical across implementations")
    return 0


if __name__ == "__main__":
    sys.exit(main())
