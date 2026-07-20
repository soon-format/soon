"""On-disk cache for per-model raw evaluation results.

Layout::

    benchmarks/accuracy/results/models/{model-slug}.json

Each file holds ``{"model": ..., "generated_at": ..., "results": [EvaluationResult...]}``.
The report generator reads all files and produces one aggregated markdown.
"""

from __future__ import annotations

import json
from dataclasses import asdict
from pathlib import Path

from .types import EvaluationResult

_RESULTS_ROOT = Path(__file__).resolve().parent / "results" / "models"


def _slug(model: str) -> str:
    return model.replace(":", "_").replace("/", "_")


def path_for(model: str) -> Path:
    _RESULTS_ROOT.mkdir(parents=True, exist_ok=True)
    return _RESULTS_ROOT / f"{_slug(model)}.json"


def save(model: str, results: list[EvaluationResult], generated_at: str) -> Path:
    p = path_for(model)
    p.write_text(
        json.dumps(
            {"model": model, "generated_at": generated_at, "results": [asdict(r) for r in results]},
            ensure_ascii=False,
            indent=2,
        ),
        encoding="utf-8",
    )
    return p


def load_all() -> dict[str, dict]:
    """Return {model: {generated_at, results}} for every model file present."""
    _RESULTS_ROOT.mkdir(parents=True, exist_ok=True)
    out: dict[str, dict] = {}
    for f in sorted(_RESULTS_ROOT.glob("*.json")):
        data = json.loads(f.read_text(encoding="utf-8"))
        out[data["model"]] = data
    return out
