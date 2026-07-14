#!/usr/bin/env python3
"""Differential test: Python and TypeScript encoders must produce
byte-identical output for every conformance input.

Requires the TS workspace to be built (`npm run build`).
Run from the repo root: python3 tools/differential.py
"""

from __future__ import annotations

import json
import subprocess
import sys
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT / "python" / "src"))

from soon_format import encode  # noqa: E402

NODE_SNIPPET = """
const { encode } = await import(new URL("../ts/packages/soon/dist/index.js", import.meta.url));
const { readFileSync } = await import("node:fs");
const cases = JSON.parse(readFileSync(0, "utf-8"));
process.stdout.write(JSON.stringify(cases.map((c) => encode(c.input, c.options ?? {}))));
"""


def main() -> int:
    cases = []
    skipped_tokenizer = 0
    for f in sorted((ROOT / "conformance" / "encode").glob("*.json")):
        fixture = json.loads(f.read_text(encoding="utf-8"))
        opts = fixture.get("options", {})
        # Tokenizer-parameterized fixtures can't run cross-implementation until
        # TS gets tokenizer parity (#9); skip them here.
        if "tokenizer" in opts:
            skipped_tokenizer += 1
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
        cwd=ROOT / "tools",
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
    suffix = f" (skipped {skipped_tokenizer} tokenizer-only)" if skipped_tokenizer else ""
    print(f"differential OK: {len(cases)} cases byte-identical across implementations{suffix}")
    return 0


if __name__ == "__main__":
    sys.exit(main())
