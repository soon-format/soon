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
import threading
from concurrent.futures import ThreadPoolExecutor, as_completed
from pathlib import Path

# Make ``soon_format`` importable when run from a checkout.
_ROOT = Path(__file__).resolve().parents[2]
sys.path.insert(0, str(_ROOT / "python" / "src"))
sys.path.insert(0, str(_ROOT))

from benchmarks.datasets import (  # noqa: E402
    l10_sparse_api_response,
    l11_shared_address_employees,
    l12_code_graph,
    l2_flat_table,
    l5_nested_uniform_large,
    l6_deeply_nested,
    l7_semi_uniform,
)

from benchmarks.accuracy.evaluate import evaluate_one  # noqa: E402
from benchmarks.accuracy.formats import PRIMERS, render  # noqa: E402
from benchmarks.accuracy.normalize import format_expected  # noqa: E402
from benchmarks.accuracy.providers import get_provider  # noqa: E402
from benchmarks.accuracy.providers import mock_provider as _mock  # noqa: E402
from benchmarks.accuracy.questions import all_questions  # noqa: E402
from benchmarks.accuracy.report import write_report  # noqa: E402
from benchmarks.accuracy.storage import save  # noqa: E402
from benchmarks.accuracy.throttle import Throttle  # noqa: E402

DATASETS = {
    "L2": l2_flat_table(),
    "L5": l5_nested_uniform_large(),
    "L6": l6_deeply_nested(),
    "L7": l7_semi_uniform(),
    "L10": l10_sparse_api_response(),
    "L11": l11_shared_address_employees(),
    "L12": l12_code_graph(),
}

# Map dataset short-name → the raw payload each question generator sees.
DATASET_ROOT_KEY = {
    "L2": "employees",
    "L5": "orders",
    "L6": "org",
    "L7": "events",
    "L10": "data",
    "L11": "employees",
    "L12": "symbols",
}

# Parallel workers per provider kind. Concurrency (not RPM) is the primary
# throttle; a shared per-provider cooldown handles 429s adaptively, so these
# just need to be low enough not to hammer the API on the first burst.
DEFAULT_CONCURRENCY = {
    "anthropic": 6,
    "openai": 8,
    "google": 4,
    "mock": 16,
}

DEFAULT_FORMATS = (
    "json",
    "yaml",
    "toon",
    "gcf",
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
        help="Subset of datasets (L2/L5/L6/L7/L10/L11/L12). Default: all.",
    )
    p.add_argument("--dry-run", action="store_true", help="Cap at 10 questions total.")
    p.add_argument(
        "--concurrency",
        action="append",
        default=None,
        help='Parallel workers: "N" for all providers or "provider=N" (repeatable). '
        f"Defaults: {DEFAULT_CONCURRENCY}",
    )
    p.add_argument(
        "--rpm",
        action="append",
        default=None,
        help='Requests-per-minute cap: "N" or "provider=N" (repeatable). '
        "Off by default — 429 backoff adapts on its own; set this for hard "
        "free-tier quotas (e.g. google=10).",
    )
    return p.parse_args(argv)


def _parse_overrides(values: list[str] | None, base: dict[str, int]) -> dict[str, int]:
    """Merge "N" / "provider=N" CLI values into a per-provider-kind map."""
    out = dict(base)
    for raw in values or []:
        if "=" in raw:
            kind, _, num = raw.partition("=")
            out[kind.strip()] = int(num)
        else:
            for kind in ("anthropic", "openai", "google", "mock"):
                out[kind] = int(raw)
    return out


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

    # Preload the mock provider's answer map from the actual ground truth so
    # a mock run scores 100% when the pipeline is intact.
    _mock.ANSWERS.clear()
    for q in questions:
        _mock.ANSWERS[q.id] = format_expected(q.ground_truth, q.answer_type)

    generated_at = _dt.datetime.now(_dt.timezone.utc).isoformat()

    # Pre-render each (dataset, format) once — dominates cost otherwise.
    rendered: dict[tuple[str, str], str] = {}
    for ds_name, data in subset.items():
        for fmt in formats:
            try:
                rendered[(ds_name, fmt)] = render(data, fmt)
            except Exception as exc:
                print(f"skip {ds_name}/{fmt}: {exc}", file=sys.stderr)

    concurrency = _parse_overrides(args.concurrency, DEFAULT_CONCURRENCY)
    rpm = _parse_overrides(args.rpm, {})

    # One task per (question, format) with a stable index so saved results
    # keep the same deterministic order the sequential loop produced.
    tasks: list[tuple[int, object, str, str, str, str]] = []
    for q in questions:
        for fmt in formats:
            data_str = rendered.get((q.dataset, fmt))
            spec = PRIMERS.get(fmt)
            if data_str is None or spec is None:
                continue
            tasks.append((len(tasks), q, fmt, spec.primer, spec.fence, data_str))

    print_lock = threading.Lock()

    def run_provider(model_id: str) -> None:
        provider = get_provider(model_id)
        kind = model_id.partition(":")[0]
        workers = max(1, concurrency.get(kind, 4))
        throttle = Throttle(rpm.get(kind))
        with print_lock:
            print(
                f"→ {model_id}: {len(questions)} questions × {len(formats)} formats "
                f"= {len(tasks)} calls ({workers} workers"
                + (f", {rpm[kind]} rpm" if kind in rpm else "")
                + ")"
            )
        indexed: list[tuple[int, object]] = []
        done = 0
        with ThreadPoolExecutor(max_workers=workers) as pool:
            futures = {
                pool.submit(
                    evaluate_one, provider, q, fmt, primer, fence, data_str, throttle=throttle
                ): idx
                for idx, q, fmt, primer, fence, data_str in tasks
            }
            for fut in as_completed(futures):
                indexed.append((futures[fut], fut.result()))
                done += 1
                if done % 100 == 0 or done == len(tasks):
                    with print_lock:
                        print(f"  [{model_id}] {done}/{len(tasks)} ({done*100//len(tasks)}%)", flush=True)
        results = [r for _, r in sorted(indexed, key=lambda pair: pair[0])]
        errors = sum(1 for r in results if r.error)
        out_path = save(provider.model, results, generated_at)
        with print_lock:
            print(f"  [{model_id}] wrote {out_path}" + (f" ({errors} errors)" if errors else ""))

    # Providers have independent rate limits — run them concurrently too.
    with ThreadPoolExecutor(max_workers=len(args.provider)) as providers_pool:
        provider_futures = [providers_pool.submit(run_provider, m) for m in args.provider]
        for fut in provider_futures:
            fut.result()

    report_path = write_report()
    print(f"→ report: {report_path}")
    return 0


if __name__ == "__main__":
    sys.exit(main())
