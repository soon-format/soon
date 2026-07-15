"""L11 questions — shared-address employees (REF-showcase dataset)."""

from __future__ import annotations

from collections import Counter
from typing import Any

from ..types import Question


def generate(data: Any) -> list[Question]:
    employees = data["employees"]
    out: list[Question] = []
    q = 0

    def qid() -> str:
        nonlocal q
        q += 1
        return f"L11-{q:03d}"

    for i in range(0, len(employees), 5):
        e = employees[i]
        out.append(Question(
            id=qid(),
            prompt=f"In what city does employee id {e['id']} work?",
            ground_truth=e["office"]["city"],
            dataset="L11",
            kind="path",
            answer_type="string",
        ))
    for i in range(0, len(employees), 7):
        e = employees[i]
        out.append(Question(
            id=qid(),
            prompt=f"What is the country of employee id {e['id']}'s office?",
            ground_truth=e["office"]["country"],
            dataset="L11",
            kind="path",
            answer_type="string",
        ))
    for i in range(0, len(employees), 9):
        e = employees[i]
        out.append(Question(
            id=qid(),
            prompt=f"What role does employee id {e['id']} have?",
            ground_truth=e["role"],
            dataset="L11",
            kind="field-retrieval",
            answer_type="string",
        ))

    city_counts = Counter(e["office"]["city"] for e in employees)
    for city in sorted(city_counts):
        out.append(Question(
            id=qid(),
            prompt=f"How many employees work in the {city} office?",
            ground_truth=city_counts[city],
            dataset="L11",
            kind="aggregation",
            answer_type="integer",
        ))
    country_counts = Counter(e["office"]["country"] for e in employees)
    for country in sorted(country_counts):
        out.append(Question(
            id=qid(),
            prompt=f"How many employees work in country '{country}'?",
            ground_truth=country_counts[country],
            dataset="L11",
            kind="aggregation",
            answer_type="integer",
        ))

    return out
