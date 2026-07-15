"""Aggregate per-model result files into a single Markdown report.

Reads ``results/models/*.json``, groups by (model, format, dataset),
computes accuracy and accuracy-per-1K-token metrics, writes
``results/retrieval-accuracy.md``. The report has three sections:

- Overall accuracy table (rows: model, cols: format).
- Per-dataset accuracy breakdown.
- Ablation deltas (mechanism on vs off, one row per mechanism).
"""

from __future__ import annotations

from collections import defaultdict
from pathlib import Path
from statistics import mean

from .storage import load_all

_REPORT_PATH = Path(__file__).resolve().parent / "results" / "retrieval-accuracy.md"


ABLATIONS = [
    ("labeled", "soon", "soon-labeled"),
    ("shape-hint", "soon", "soon-shape-hint"),
    ("no-guardrail", "soon", "soon-no-guardrail"),
    ("elide", "soon", "soon-elide"),
    ("ref", "soon", "soon-ref"),
]


def _acc(results: list[dict]) -> float:
    return mean(1.0 if r["correct"] else 0.0 for r in results) if results else float("nan")


def _acc_per_1k(results: list[dict]) -> float:
    ok = sum(1 for r in results if r["correct"])
    tokens = sum(r.get("prompt_tokens") or r["prompt_chars"] // 4 for r in results)
    return (ok / max(tokens, 1)) * 1000


def build_report() -> str:
    all_data = load_all()
    if not all_data:
        return "# Retrieval accuracy\n\n_No results yet. Run ``benchmarks/accuracy/run.py`` first._\n"

    # Flatten: model → format → dataset → [result dict]
    by_model: dict[str, dict[str, dict[str, list[dict]]]] = defaultdict(lambda: defaultdict(lambda: defaultdict(list)))
    formats_seen: set[str] = set()
    datasets_seen: set[str] = set()
    for model, payload in all_data.items():
        for r in payload["results"]:
            by_model[model][r["format"]][r["dataset"]].append(r)
            formats_seen.add(r["format"])
            datasets_seen.add(r["dataset"])
    formats = sorted(formats_seen)
    datasets = sorted(datasets_seen)

    out: list[str] = []
    out.append("# Retrieval accuracy\n")
    out.append("Deterministic, type-aware scoring. See `benchmarks/accuracy/README.md` for methodology.\n")
    out.append("## Overall accuracy (%)\n")
    out.append("| model | " + " | ".join(formats) + " |")
    out.append("|" + "|".join(["---"] * (len(formats) + 1)) + "|")
    for model in sorted(by_model):
        cells = []
        for fmt in formats:
            rows = [r for ds in by_model[model][fmt].values() for r in ds]
            cells.append(f"{100 * _acc(rows):.1f}" if rows else "—")
        out.append(f"| {model} | " + " | ".join(cells) + " |")
    out.append("")

    out.append("## Accuracy per 1K prompt tokens\n")
    out.append('Higher is better — the "money metric" (accuracy per dollar).\n')
    out.append("| model | " + " | ".join(formats) + " |")
    out.append("|" + "|".join(["---"] * (len(formats) + 1)) + "|")
    for model in sorted(by_model):
        cells = []
        for fmt in formats:
            rows = [r for ds in by_model[model][fmt].values() for r in ds]
            cells.append(f"{_acc_per_1k(rows):.3f}" if rows else "—")
        out.append(f"| {model} | " + " | ".join(cells) + " |")
    out.append("")

    out.append("## Per-dataset accuracy (%)\n")
    for ds in datasets:
        out.append(f"### {ds}\n")
        out.append("| model | " + " | ".join(formats) + " |")
        out.append("|" + "|".join(["---"] * (len(formats) + 1)) + "|")
        for model in sorted(by_model):
            cells = []
            for fmt in formats:
                rows = by_model[model][fmt].get(ds, [])
                cells.append(f"{100 * _acc(rows):.1f}" if rows else "—")
            out.append(f"| {model} | " + " | ".join(cells) + " |")
        out.append("")

    out.append("## Ablation deltas (%)\n")
    out.append("Accuracy delta when the named mechanism is ON vs the plain SOON baseline. Positive = mechanism helps.\n")
    out.append("| model | " + " | ".join(name for name, _, _ in ABLATIONS) + " |")
    out.append("|" + "|".join(["---"] * (len(ABLATIONS) + 1)) + "|")
    for model in sorted(by_model):
        cells = []
        for _, base, arm in ABLATIONS:
            base_rows = [r for ds in by_model[model][base].values() for r in ds]
            arm_rows = [r for ds in by_model[model][arm].values() for r in ds]
            if not base_rows or not arm_rows:
                cells.append("—")
            else:
                delta = 100 * (_acc(arm_rows) - _acc(base_rows))
                cells.append(f"{delta:+.1f}")
        out.append(f"| {model} | " + " | ".join(cells) + " |")
    out.append("")

    return "\n".join(out)


def write_report() -> Path:
    _REPORT_PATH.parent.mkdir(parents=True, exist_ok=True)
    _REPORT_PATH.write_text(build_report(), encoding="utf-8")
    return _REPORT_PATH
