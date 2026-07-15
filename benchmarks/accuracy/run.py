"""Retrieval-accuracy benchmark CLI.

Usage::

    # Mock provider, small run, verifies plumbing:
    python3 benchmarks/accuracy/run.py --provider mock:fixture --dry-run

    # Real run against three providers:
    python3 benchmarks/accuracy/run.py \\
        --provider openai:gpt-5-nano \\
        --provider anthropic:claude-haiku-4-5-20251001 \\
        --provider google:gemini-3-flash-preview

Results land in ``benchmarks/accuracy/results/models/{model}.json`` and
the aggregated report at ``benchmarks/accuracy/results/retrieval-accuracy.md``.
"""

from __future__ import annotations

import argparse
import datetime as _dt
import sys
from pathlib import Path

# Make ``soon_format`` importable when run from a checkout.
_ROOT = Path(__file__).resolve().parents[2]
sys.path.insert(0, str(_ROOT / "python" / "src"))
sys.path.insert(0, str(_ROOT))

from benchmarks.datasets import (  # noqa: E402
    l10_sparse_api_response,
    l11_shared_address_employees,
    l2_flat_table,
    l5_nested_uniform_large,
    l6_deeply_nested,
    l7_semi_uniform,
)

from benchmarks.accuracy.evaluate import evaluate_one  # noqa: E402
from benchmarks.accuracy.formats import PRIMERS, render  # noqa: E402
from benchmarks.accuracy.providers import get_provider  # noqa: E402
from benchmarks.accuracy.questions import all_questions  # noqa: E402
from benchmarks.accuracy.report import write_report  # noqa: E402
from benchmarks.accuracy.storage import save  # noqa: E402

DATASETS = {
    "L2": l2_flat_table(),
    "L5": l5_nested_uniform_large(),
    "L6": l6_deeply_nested(),
    "L7": l7_semi_uniform(),
    "L10": l10_sparse_api_response(),
    "L11": l11_shared_address_employees(),
}

# Map dataset short-name → the raw payload each question generator sees.
DATASET_ROOT_KEY = {
    "L2": "employees",
    "L5": "orders",
    "L6": "org",
    "L7": "events",
    "L10": "data",
    "L11": "employees",
}

DEFAULT_FORMATS = (
    "json",
    "yaml",
    "soon",
    "soon-labeled",
    "soon-no-guardrail",
    "soon-shape-hint",
    "soon-elide",
    "soon-ref",
)


def parse_args(argv: list[str] | None = None) -> argparse.Namespace:
    p = argparse.ArgumentParser(description="SOON retrieval-accuracy harness")
    p.add_argument(
        "--provider",
        action="append",
        required=True,
        help='"provider:model-name" (e.g. "openai:gpt-5-nano", "mock:fixture")',
    )
    p.add_argument(
        "--format",
        action="append",
        default=None,
        help="Formats to test (repeat). Defaults to the full ablation set.",
    )
    p.add_argument(
        "--dataset",
        action="append",
        default=None,
        help="Subset of datasets (L2/L5/L6/L7/L10/L11). Default: all.",
    )
    p.add_argument("--dry-run", action="store_true", help="Cap at 10 questions total.")
    return p.parse_args(argv)


def main(argv: list[str] | None = None) -> int:
    args = parse_args(argv)
    formats = list(args.format) if args.format else list(DEFAULT_FORMATS)
    dataset_names = list(args.dataset) if args.dataset else list(DATASETS)

    subset = {name: DATASETS[name] for name in dataset_names if name in DATASETS}
    questions = all_questions(subset)
    if not questions:
        print("no questions generated — question modules are still stubs (Phase C).", file=sys.stderr)
        return 2
    if args.dry_run:
        questions = questions[:10]

    generated_at = _dt.datetime.now(_dt.timezone.utc).isoformat()

    # Pre-render each (dataset, format) once — dominates cost otherwise.
    rendered: dict[tuple[str, str], str] = {}
    for ds_name, data in subset.items():
        for fmt in formats:
            try:
                rendered[(ds_name, fmt)] = render(data, fmt)
            except Exception as exc:
                print(f"skip {ds_name}/{fmt}: {exc}", file=sys.stderr)

    for model_id in args.provider:
        provider = get_provider(model_id)
        print(f"→ {model_id}: {len(questions)} questions × {len(formats)} formats")
        results = []
        for q in questions:
            for fmt in formats:
                key = (q.dataset, fmt)
                data_str = rendered.get(key)
                if data_str is None:
                    continue
                spec = PRIMERS.get(fmt)
                if spec is None:
                    continue
                r = evaluate_one(provider, q, fmt, spec.primer, spec.fence, data_str)
                results.append(r)
        out_path = save(provider.model, results, generated_at)
        print(f"  wrote {out_path}")

    report_path = write_report()
    print(f"→ report: {report_path}")
    return 0


if __name__ == "__main__":
    sys.exit(main())
