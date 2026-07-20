#!/usr/bin/env python3
"""Cross-language conformance matrix.

For each conformance fixture, encode with every implementation and decode
every encoder's output with every decoder. All combinations must agree.

Requires:
  - Python: pip install -e ../soon-python
  - TypeScript: cd ../soon-typescript && npm ci && npm run build

Run from repo root: python3 tests/cross-language-matrix.py
"""

from __future__ import annotations

import json
import subprocess
import sys
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
CONFORMANCE = ROOT / "conformance"

# ---------------------------------------------------------------------------
# Language adapters
# ---------------------------------------------------------------------------

def py_encode(data, options):
    """Encode via the Python implementation."""
    from soon_format import encode
    return encode(data, **options)

def py_decode(text):
    """Decode via the Python implementation."""
    from soon_format import decode
    return decode(text)

def _ts_batch(cases, operation):
    """Run a batch of encode/decode operations via Node subprocess."""
    ts_root = ROOT.parent / "soon-typescript"
    if not ts_root.exists():
        sys.exit(f"error: {ts_root} not found — clone soon-typescript alongside this repo")

    if operation == "encode":
        snippet = """
const { encode } = await import("./dist/index.js");
const { readFileSync } = await import("node:fs");
const cases = JSON.parse(readFileSync(0, "utf-8"));
process.stdout.write(JSON.stringify(cases.map(c => encode(c.input, c.options ?? {}))));
"""
    else:
        snippet = """
const { decode } = await import("./dist/index.js");
const { readFileSync } = await import("node:fs");
const cases = JSON.parse(readFileSync(0, "utf-8"));
process.stdout.write(JSON.stringify(cases.map(c => decode(c.input))));
"""
    result = subprocess.run(
        ["node", "--input-type=module", "-e", snippet],
        input=json.dumps(cases),
        capture_output=True,
        text=True,
        cwd=ts_root,
        check=True,
    )
    return json.loads(result.stdout)


def ts_encode_batch(cases):
    return _ts_batch(cases, "encode")


def ts_decode_batch(cases):
    return _ts_batch(cases, "decode")


# ---------------------------------------------------------------------------
# Main
# ---------------------------------------------------------------------------

def main() -> int:
    # Gather conformance fixtures
    encode_cases = []
    for f in sorted((CONFORMANCE / "encode").glob("*.json")):
        fixture = json.loads(f.read_text(encoding="utf-8"))
        opts = fixture.get("options", {})
        # Skip v0.2-only options/modes that not all implementations support yet
        v02_options = {"shape_hint_rows", "row_count_guardrail", "elide", "ref"}
        if v02_options & opts.keys():
            continue
        if opts.get("mode", "auto") not in ("auto", "soon", "json"):
            continue
        encode_cases.append({"name": f.stem, "input": fixture["input"], "options": opts})

    roundtrip_cases = []
    for f in sorted((CONFORMANCE / "roundtrip").glob("*.json")):
        fixture = json.loads(f.read_text(encoding="utf-8"))
        for mode in ("auto", "soon"):
            roundtrip_cases.append({
                "name": f"{f.stem}:{mode}",
                "input": fixture["input"],
                "options": {"mode": mode},
            })

    all_cases = encode_cases + roundtrip_cases

    print(f"Running cross-language matrix on {len(all_cases)} cases...")

    # Phase 1: Encode with both implementations
    py_encoded = []
    for case in all_cases:
        py_encoded.append(py_encode(case["input"], case["options"]))

    ts_encoded = ts_encode_batch(all_cases)
    if len(ts_encoded) != len(all_cases):
        print(f"error: TS returned {len(ts_encoded)} outputs for {len(all_cases)} cases")
        return 2

    # Phase 2: Check encoder agreement (byte-identical)
    encode_mismatches = 0
    for i, case in enumerate(all_cases):
        if py_encoded[i] != ts_encoded[i]:
            encode_mismatches += 1
            print(f"ENCODE MISMATCH {case['name']}")
            print(f"  py: {py_encoded[i]!r}")
            print(f"  ts: {ts_encoded[i]!r}")

    # Phase 3: Cross-decode (every encoder output through every decoder)
    ts_decode_inputs = [{"input": e} for e in py_encoded] + [{"input": e} for e in ts_encoded]
    ts_decoded = ts_decode_batch(ts_decode_inputs)

    ts_of_py = ts_decoded[:len(all_cases)]   # TS decoding Python's output
    ts_of_ts = ts_decoded[len(all_cases):]   # TS decoding its own output

    decode_mismatches = 0
    for i, case in enumerate(all_cases):
        py_of_py = py_decode(py_encoded[i])
        py_of_ts = py_decode(ts_encoded[i])

        results = {
            "py->py": py_of_py,
            "py->ts": ts_of_py[i],
            "ts->py": py_of_ts,
            "ts->ts": ts_of_ts[i],
        }

        # All four must agree
        canonical = json.dumps(py_of_py, sort_keys=True)
        for label, result in results.items():
            if json.dumps(result, sort_keys=True) != canonical:
                decode_mismatches += 1
                print(f"DECODE MISMATCH {case['name']} ({label} disagrees)")
                print(f"  canonical: {canonical}")
                print(f"  {label}: {json.dumps(result, sort_keys=True)}")

    # Summary
    total = len(all_cases)
    if encode_mismatches or decode_mismatches:
        print(f"\nFAILED: {encode_mismatches} encode + {decode_mismatches} decode mismatches out of {total} cases")
        return 1

    print(f"\nOK: {total} cases x 2 encoders x 2 decoders -- all byte-identical")
    return 0


if __name__ == "__main__":
    sys.exit(main())
