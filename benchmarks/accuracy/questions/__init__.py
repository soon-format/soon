"""Programmatic question generators.

Each dataset's questions live in its own module and expose a top-level
``generate(data) -> list[Question]`` function. Ground truth is computed
directly from the data, so questions and answers stay in sync as the
generators evolve. No LLM in the loop.
"""

from __future__ import annotations

from ..types import Question
from . import code_graph, deep, events, nested, shared_ref, sparse, tabular


def all_questions(datasets: dict[str, object]) -> list[Question]:
    """Generate every question over the provided datasets map.

    ``datasets`` maps a dataset short-name (``L2``, ``L5``, ...) to the
    raw payload from ``benchmarks.datasets`` — the harness's ``run.py``
    is what actually builds this mapping.
    """
    out: list[Question] = []
    if "L2" in datasets:
        out += tabular.generate(datasets["L2"])
    if "L5" in datasets:
        out += nested.generate(datasets["L5"])
    if "L6" in datasets:
        out += deep.generate(datasets["L6"])
    if "L7" in datasets:
        out += events.generate(datasets["L7"])
    if "L10" in datasets:
        out += sparse.generate(datasets["L10"])
    if "L11" in datasets:
        out += shared_ref.generate(datasets["L11"])
    if "L12" in datasets:
        out += code_graph.generate(datasets["L12"])
    return out
