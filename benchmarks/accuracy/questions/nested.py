"""L5 questions — 100 nested orders."""

from __future__ import annotations

from collections import Counter
from typing import Any

from ..types import Question


def generate(data: Any) -> list[Question]:
    orders = data["orders"]
    out: list[Question] = []
    q = 0

    def qid() -> str:
        nonlocal q
        q += 1
        return f"L5-{q:03d}"

    templates = [
        ("field-retrieval", "string", lambda o: (f"What is the status of order {o['id']}?", o["status"])),
        ("path", "string", lambda o: (f"What is the customer name for order {o['id']}?", o["customer"]["name"])),
        ("path", "string", lambda o: (f"What tier is the customer of order {o['id']}?", o["customer"]["tier"])),
        ("path", "string", lambda o: (f"What city is the customer of order {o['id']} in?", o["customer"]["address"]["city"])),
        ("cardinality", "integer", lambda o: (f"How many items are in order {o['id']}?", len(o["items"]))),
    ]
    for i in range(0, len(orders), 3):
        order = orders[i]
        kind, atype, fn = templates[(i // 3) % len(templates)]
        prompt, gt = fn(order)
        out.append(Question(id=qid(), prompt=prompt, ground_truth=gt,
                            dataset="L5", kind=kind, answer_type=atype))

    status_counts = Counter(o["status"] for o in orders)
    for status in sorted(status_counts):
        out.append(Question(
            id=qid(),
            prompt=f"How many orders have status '{status}'?",
            ground_truth=status_counts[status],
            dataset="L5",
            kind="aggregation",
            answer_type="integer",
        ))
    tier_counts = Counter(o["customer"]["tier"] for o in orders)
    for tier in sorted(tier_counts):
        out.append(Question(
            id=qid(),
            prompt=f"How many orders are from a '{tier}'-tier customer?",
            ground_truth=tier_counts[tier],
            dataset="L5",
            kind="aggregation",
            answer_type="integer",
        ))

    for threshold in (2, 3):
        out.append(Question(
            id=qid(),
            prompt=f"How many orders have more than {threshold} items?",
            ground_truth=sum(1 for o in orders if len(o["items"]) > threshold),
            dataset="L5",
            kind="cardinality",
            answer_type="integer",
        ))

    return out
