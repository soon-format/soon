"""``soon`` command-line interface.

Examples:
    soon encode data.json            # JSON in, SOON out (stdout)
    cat data.json | soon encode -    # stdin
    soon decode doc.soon             # SOON in, compact JSON out
    soon stats data.json --tokenizer o200k_base
    soon check data.json             # round-trip verification, exit code 0/1
"""

from __future__ import annotations

import argparse
import json
import sys

from . import __version__, decode, encode, stats
from .errors import SoonError


def _read(path: str) -> str:
    if path == "-":
        return sys.stdin.read()
    with open(path, encoding="utf-8") as fh:
        return fh.read()


def _write(text: str, out: str | None) -> None:
    if out is None or out == "-":
        sys.stdout.write(text + "\n")
    else:
        with open(out, "w", encoding="utf-8") as fh:
            fh.write(text + "\n")


def build_parser() -> argparse.ArgumentParser:
    parser = argparse.ArgumentParser(
        prog="soon",
        description="SOON (Shape-Oriented Object Notation): token-efficient JSON for LLM prompts.",
    )
    parser.add_argument("--version", action="version", version=f"soon-format {__version__}")
    sub = parser.add_subparsers(dest="command", required=True)

    p_encode = sub.add_parser("encode", help="encode JSON as SOON")
    p_encode.add_argument("input", nargs="?", default="-", help="input JSON file or '-' (stdin)")
    p_encode.add_argument("-o", "--output", help="output file (default: stdout)")
    p_encode.add_argument("--mode", choices=["auto", "soon", "json"], default="auto")
    p_encode.add_argument("--tokenizer", help="tiktoken encoding for cost decisions")
    p_encode.add_argument(
        "--stats", action="store_true", help="print a savings report to stderr"
    )

    p_decode = sub.add_parser("decode", help="decode SOON back to compact JSON")
    p_decode.add_argument("input", nargs="?", default="-", help="input SOON file or '-' (stdin)")
    p_decode.add_argument("-o", "--output", help="output file (default: stdout)")
    p_decode.add_argument(
        "--pretty", action="store_true", help="indent JSON output (default: compact)"
    )

    p_stats = sub.add_parser("stats", help="report SOON vs JSON size for a JSON input")
    p_stats.add_argument("input", nargs="?", default="-")
    p_stats.add_argument("--tokenizer", help="tiktoken encoding (e.g. o200k_base)")

    p_check = sub.add_parser("check", help="verify decode(encode(x)) == x for a JSON input")
    p_check.add_argument("input", nargs="?", default="-")
    p_check.add_argument(
        "--tokenizer",
        help="tiktoken encoding (e.g. o200k_base); also round-trips the "
        "tokenizer-driven auto-mode output",
    )
    return parser


def main(argv: list[str] | None = None) -> int:
    args = build_parser().parse_args(argv)
    try:
        if args.command == "encode":
            data = json.loads(_read(args.input))
            doc = encode(data, mode=args.mode, tokenizer=args.tokenizer)
            _write(doc, args.output)
            if args.stats:
                report = stats(data, tokenizer=args.tokenizer)
                sys.stderr.write(json.dumps(report) + "\n")
        elif args.command == "decode":
            value = decode(_read(args.input))
            if args.pretty:
                out = json.dumps(value, indent=2, ensure_ascii=False)
            else:
                out = json.dumps(value, separators=(",", ":"), ensure_ascii=False)
            _write(out, args.output)
        elif args.command == "stats":
            data = json.loads(_read(args.input))
            sys.stdout.write(
                json.dumps(stats(data, tokenizer=args.tokenizer), indent=2) + "\n"
            )
        elif args.command == "check":
            data = json.loads(_read(args.input))
            tokenizer = args.tokenizer
            for mode in ("auto", "soon"):
                if decode(encode(data, mode=mode, tokenizer=tokenizer)) != data:
                    label = f"mode={mode}" + (
                        f", tokenizer={tokenizer}" if tokenizer else ""
                    )
                    sys.stderr.write(f"round-trip FAILED in {label}\n")
                    return 1
            summary = "round-trip OK (auto, soon)"
            if tokenizer:
                summary += f" with tokenizer={tokenizer}"
            sys.stderr.write(summary + "\n")
    except (SoonError, json.JSONDecodeError, OSError) as exc:
        sys.stderr.write(f"error: {exc}\n")
        return 1
    return 0


if __name__ == "__main__":  # pragma: no cover
    sys.exit(main())
