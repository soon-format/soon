"""L10 questions — sparse API response (customers with defaults + exceptions).

Questions concentrate on the exception rows so we measure whether ELIDE's
``+status=…`` override syntax preserves LLM retrievability.
"""

from __future__ import annotations

from collections import Counter
from typing import Any

from ..types import Question


def generate(data: Any) -> list[Question]:
    rows = data["data"]
    out: list[Question] = []
    q = 0

    def qid() -> str:
        nonlocal q
        q += 1
        return f"L10-{q:03d}"

    # Field retrieval — status of each customer (mix of defaults + exceptions).
    for i in range(0, len(rows), 6):
        r = rows[i]
        out.append(Question(
            id=qid(),
            prompt=f"What is the status of customer id {r['id']}?",
            ground_truth=r["status"],
            dataset="L10",
            kind="field-retrieval",
            answer_type="string",
        ))
    for i in range(0, len(rows), 8):
        r = rows[i]
        out.append(Question(
            id=qid(),
            prompt=f"What is the currency of customer id {r['id']}?",
            ground_truth=r["currency"],
            dataset="L10",
            kind="field-retrieval",
            answer_type="string",
        ))
    for i in range(0, len(rows), 10):
        r = rows[i]
        out.append(Question(
            id=qid(),
            prompt=f"Is customer id {r['id']} delinquent? Answer yes or no.",
            ground_truth=r["delinquent"],
            dataset="L10",
            kind="field-retrieval",
            answer_type="boolean",
        ))

    # Aggregations — focus on non-default counts, the load-bearing measure for ELIDE.
    status_counts = Counter(r["status"] for r in rows)
    for status in sorted(status_counts):
        out.append(Question(
            id=qid(),
            prompt=f"How many customers have status '{status}'?",
            ground_truth=status_counts[status],
            dataset="L10",
            kind="aggregation",
            answer_type="integer",
        ))
    out.append(Question(
        id=qid(),
        prompt="How many customers are delinquent (delinquent=true)?",
        ground_truth=sum(1 for r in rows if r["delinquent"]),
        dataset="L10",
        kind="aggregation",
        answer_type="integer",
    ))
    out.append(Question(
        id=qid(),
        prompt="How many customers have currency other than 'usd'?",
        ground_truth=sum(1 for r in rows if r["currency"] != "usd"),
        dataset="L10",
        kind="aggregation",
        answer_type="integer",
    ))

    return out
