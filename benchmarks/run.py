#!/usr/bin/env python3
"""Token-efficiency benchmark: SOON vs JSON / YAML / TOON / GCF, simple to hard.

Usage (from repo root):
    python3 benchmarks/run.py [--tokenizer o200k_base]

Requires: pip install soon-format[dev] gcf-python

- Sizes are always reported in characters. Pass ``--tokenizer`` to add a
  second table measured in real BPE tokens. Bundled encodings
  (``o200k_base``) load from the wheel and never touch the network.
- TOON is encoded with the ``toon-py`` package.
- GCF is encoded with the ``gcf-python`` package (generic profile).
- Every SOON encoding is verified lossless (``decode(encode(x)) == x``)
  and never-worse-than-compact-JSON in the *cost-function unit the
  encoder actually used* to make its auto-mode decision.

Writes benchmarks/results.json and benchmarks/results.md.
"""

from __future__ import annotations

import argparse
import json
import sys
from pathlib import Path
from typing import Any, Callable

ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT / "benchmarks"))

from datasets import DATASETS  # noqa: E402

from soon_format import decode as soon_decode  # noqa: E402
from soon_format import encode as soon_encode  # noqa: E402
from soon_format.tokencost import get_encoder, text_cost  # noqa: E402


def formatters(tokenizer: str | None) -> dict[str, Callable[[Any], str]]:
    fmts: dict[str, Callable[[Any], str]] = {
        "json": lambda d: json.dumps(d, separators=(",", ":"), ensure_ascii=False),
        "json-pretty": lambda d: json.dumps(d, indent=2, ensure_ascii=False),
    }
    try:
        import yaml
    except ImportError as exc:  # pragma: no cover
        raise SystemExit(
            "benchmark requires pyyaml; install with: pip install pyyaml"
        ) from exc
    fmts["yaml"] = lambda d: yaml.safe_dump(
        d, default_flow_style=False, allow_unicode=True, sort_keys=False
    )
    try:
        from toon_py import encode as toon_encode
    except ImportError as exc:  # pragma: no cover
        raise SystemExit(
            "benchmark requires toon-py for the TOON comparison column; "
            "install with: pip install 'soon-format[dev]' (or: pip install toon-py)"
        ) from exc
    fmts["toon"] = lambda d: toon_encode(d)
    try:
        from gcf import encode_generic as gcf_encode
    except ImportError as exc:  # pragma: no cover
        raise SystemExit(
            "benchmark requires gcf-python for the GCF comparison column; "
            "install with: pip install gcf-python"
        ) from exc
    fmts["gcf"] = lambda d: gcf_encode(d)
    # SOON's auto-mode decisions use the same tokenizer the bench measures with.
    fmts["soon"] = lambda d: soon_encode(d, tokenizer=tokenizer)
    return fmts


def _md_table(results: list[dict[str, Any]], unit_label: str, key: str) -> list[str]:
    """Render one Markdown savings table for the given size key ('chars' or 'tokens')."""
    fmt_names = [f for f in results[0]["sizes"][key] if f != "json"]
    lines = [
        f"## Sizes in {unit_label}",
        "",
        "| Dataset | json | " + " | ".join(fmt_names) + " |",
        "|---|---|" + "---|" * len(fmt_names),
    ]
    for r in results:
        base = r["sizes"][key]["json"]
        cells = []
        for fmt in fmt_names:
            n = r["sizes"][key].get(fmt)
            cells.append(f"{n} ({(1 - n / base) * 100:+.1f}%)" if n else "-")
        lines.append(
            f"| {r['dataset']} — {r['description']} | {base} | " + " | ".join(cells) + " |"
        )
    lines.append("")
    return lines


def main() -> int:
    parser = argparse.ArgumentParser()
    parser.add_argument(
        "--tokenizer",
        help="tiktoken encoding name (e.g. o200k_base); adds a token-cost table",
    )
    args = parser.parse_args()

    encoder = get_encoder(args.tokenizer) if args.tokenizer else None
    # decision_unit is the unit encode()'s auto-mode compare actually used —
    # so this is the *only* unit in which SOON is contractually never-worse
    # than compact JSON. Asserting the invariant in any other unit would be
    # a category error.
    decision_unit = "tokens" if encoder is not None else "chars"
    counters: dict[str, Callable[[str], int]] = {"chars": len}
    if encoder is not None:
        counters["tokens"] = lambda s: text_cost(s, encoder)  # noqa: E731

    fmts = formatters(args.tokenizer)
    results: list[dict[str, Any]] = []
    for name, desc, gen in DATASETS:
        data = gen()
        # One encode per formatter; SOON is encoded exactly once per dataset.
        encoded = {fmt: f(data) for fmt, f in fmts.items()}
        soon_doc = encoded["soon"]
        cj = encoded["json"]
        assert soon_decode(soon_doc) == data, f"lossless check failed: {name}"
        # Never-worse guarantee: assert only in the unit auto-mode compared.
        assert counters[decision_unit](soon_doc) <= counters[decision_unit](cj), (
            f"never-worse check failed: {name} ({decision_unit})"
        )
        sizes = {
            cname: {fmt: counter(text) for fmt, text in encoded.items()}
            for cname, counter in counters.items()
        }
        results.append({"dataset": name, "description": desc, "sizes": sizes})

    out = {
        "tokenizer": args.tokenizer,
        "units": list(counters.keys()),
        "decision_unit": decision_unit,
        "results": results,
    }
    (ROOT / "benchmarks" / "results.json").write_text(
        json.dumps(out, indent=2) + "\n", encoding="utf-8"
    )

    header = [
        "# Size benchmark",
        "",
        "Savings vs compact JSON; positive is smaller. Generated by `benchmarks/run.py`.",
        "",
    ]
    if args.tokenizer:
        header.append(f"Tokenizer: `{args.tokenizer}` (loaded from bundled vocab, offline).")
        header.append("")
    body: list[str] = []
    body.extend(_md_table(results, "characters", "chars"))
    if "tokens" in counters:
        body.extend(_md_table(results, f"tokens ({args.tokenizer})", "tokens"))
    md = "\n".join(header + body) + "\n"
    (ROOT / "benchmarks" / "results.md").write_text(md, encoding="utf-8")
    print(md)
    return 0


if __name__ == "__main__":
    sys.exit(main())
