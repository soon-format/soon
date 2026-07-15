"""L7 questions — 120-event log with optional fields."""

from __future__ import annotations

from collections import Counter
from typing import Any

from ..types import Question


def generate(data: Any) -> list[Question]:
    events = data["events"]
    out: list[Question] = []
    q = 0

    def qid() -> str:
        nonlocal q
        q += 1
        return f"L7-{q:03d}"

    for i in range(0, len(events), 8):
        ev = events[i]
        out.append(Question(
            id=qid(),
            prompt=f"What is the type of the event whose ts is {ev['ts']}?",
            ground_truth=ev["type"],
            dataset="L7",
            kind="field-retrieval",
            answer_type="string",
        ))

    for i in range(0, len(events), 10):
        ev = events[i]
        out.append(Question(
            id=qid(),
            prompt=f"Does the event with ts {ev['ts']} have a user field? Answer yes or no.",
            ground_truth="user" in ev,
            dataset="L7",
            kind="existence",
            answer_type="boolean",
        ))

    type_counts = Counter(e["type"] for e in events)
    for t in sorted(type_counts):
        out.append(Question(
            id=qid(),
            prompt=f"How many events have type '{t}'?",
            ground_truth=type_counts[t],
            dataset="L7",
            kind="aggregation",
            answer_type="integer",
        ))
    out.append(Question(
        id=qid(),
        prompt="How many events have a 'user' field present?",
        ground_truth=sum(1 for e in events if "user" in e),
        dataset="L7",
        kind="aggregation",
        answer_type="integer",
    ))
    out.append(Question(
        id=qid(),
        prompt="How many error events are marked fatal (fatal=true)?",
        ground_truth=sum(1 for e in events if e.get("fatal") is True),
        dataset="L7",
        kind="aggregation",
        answer_type="integer",
    ))

    return out
