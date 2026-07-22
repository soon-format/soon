"""L12 questions — 500-symbol, 200-edge code graph.

Comparable to GCF's benchmark: symbol counting, edge counting,
distance grouping, kind filtering, positional retrieval, and
cross-structure queries.
"""

from __future__ import annotations

from collections import Counter
from typing import Any

from ..types import Question


def generate(data: Any) -> list[Question]:
    symbols = data["symbols"]
    edges = data["edges"]
    out: list[Question] = []
    q = 0

    def qid() -> str:
        nonlocal q
        q += 1
        return f"L12-{q:03d}"

    # --- Cardinality: total counts ---
    out.append(Question(
        id=qid(),
        prompt="How many symbols are there in total?",
        ground_truth=len(symbols),
        dataset="L12",
        kind="cardinality",
        answer_type="integer",
    ))
    out.append(Question(
        id=qid(),
        prompt="How many edges are there in total?",
        ground_truth=len(edges),
        dataset="L12",
        kind="cardinality",
        answer_type="integer",
    ))

    # --- Distance grouping ---
    dist_counts = Counter(s["distance"] for s in symbols)
    out.append(Question(
        id=qid(),
        prompt="How many symbols have distance 0 (targets)?",
        ground_truth=dist_counts[0],
        dataset="L12",
        kind="aggregation",
        answer_type="integer",
    ))
    out.append(Question(
        id=qid(),
        prompt="How many symbols have distance 1 (related)?",
        ground_truth=dist_counts[1],
        dataset="L12",
        kind="aggregation",
        answer_type="integer",
    ))
    out.append(Question(
        id=qid(),
        prompt="How many symbols have distance 2 (extended)?",
        ground_truth=dist_counts[2],
        dataset="L12",
        kind="aggregation",
        answer_type="integer",
    ))

    # --- Kind aggregation ---
    kind_counts = Counter(s["kind"] for s in symbols)
    for kind in sorted(kind_counts):
        out.append(Question(
            id=qid(),
            prompt=f"How many symbols have kind '{kind}'?",
            ground_truth=kind_counts[kind],
            dataset="L12",
            kind="aggregation",
            answer_type="integer",
        ))

    # --- Provenance aggregation ---
    prov_counts = Counter(s["provenance"] for s in symbols)
    for prov in sorted(prov_counts):
        out.append(Question(
            id=qid(),
            prompt=f"How many symbols have provenance '{prov}'?",
            ground_truth=prov_counts[prov],
            dataset="L12",
            kind="aggregation",
            answer_type="integer",
        ))

    # --- Edge relation aggregation ---
    rel_counts = Counter(e["relation"] for e in edges)
    for rel in sorted(rel_counts):
        out.append(Question(
            id=qid(),
            prompt=f"How many edges have relation '{rel}'?",
            ground_truth=rel_counts[rel],
            dataset="L12",
            kind="aggregation",
            answer_type="integer",
        ))

    # --- Positional field retrieval ---
    for idx in (0, 49, 99, 249, 499):
        s = symbols[idx]
        out.append(Question(
            id=qid(),
            prompt=f"What is the qualifiedName of symbol at index {idx} (0-based)?",
            ground_truth=s["qualifiedName"],
            dataset="L12",
            kind="field-retrieval",
            answer_type="string",
        ))
        out.append(Question(
            id=qid(),
            prompt=f"What kind is the symbol at index {idx} (0-based)?",
            ground_truth=s["kind"],
            dataset="L12",
            kind="field-retrieval",
            answer_type="string",
        ))
        out.append(Question(
            id=qid(),
            prompt=f"What is the distance of the symbol at index {idx} (0-based)?",
            ground_truth=s["distance"],
            dataset="L12",
            kind="field-retrieval",
            answer_type="integer",
        ))

    # --- First/last symbol ---
    out.append(Question(
        id=qid(),
        prompt="What kind is the first symbol?",
        ground_truth=symbols[0]["kind"],
        dataset="L12",
        kind="field-retrieval",
        answer_type="string",
    ))
    out.append(Question(
        id=qid(),
        prompt="What kind is the last symbol?",
        ground_truth=symbols[-1]["kind"],
        dataset="L12",
        kind="field-retrieval",
        answer_type="string",
    ))

    # --- Filter-select: high-score targets ---
    targets_above_08 = [
        s["qualifiedName"]
        for s in symbols
        if s["distance"] == 0 and s["score"] >= 0.8
    ]
    out.append(Question(
        id=qid(),
        prompt="How many target symbols (distance 0) have a score >= 0.8?",
        ground_truth=len(targets_above_08),
        dataset="L12",
        kind="filter-select",
        answer_type="integer",
    ))

    # --- Cross-structure: specific symbol lookup by name ---
    for search_idx in (10, 100, 300):
        s = symbols[search_idx]
        out.append(Question(
            id=qid(),
            prompt=f"What is the score of the symbol with qualifiedName '{s['qualifiedName']}'?",
            ground_truth=s["score"],
            dataset="L12",
            kind="field-retrieval",
            answer_type="number",
        ))

    # --- Combined: kind × distance ---
    for kind_val in ("function", "interface"):
        for dist_val in (0, 2):
            count = sum(
                1 for s in symbols
                if s["kind"] == kind_val and s["distance"] == dist_val
            )
            label = {0: "target", 1: "related", 2: "extended"}[dist_val]
            out.append(Question(
                id=qid(),
                prompt=f"How many {label} (distance {dist_val}) symbols have kind '{kind_val}'?",
                ground_truth=count,
                dataset="L12",
                kind="filter-select",
                answer_type="integer",
            ))

    return out
