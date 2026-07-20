"""L2 questions — 100 flat employees {id,name,role,salary,remote}."""

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
        return f"L2-{q:03d}"

    templates = [
        ("salary", "integer", lambda e: f"What is the salary of the employee with id {e['id']}?"),
        ("role", "string", lambda e: f"What role does the employee with id {e['id']} have?"),
        ("name", "string", lambda e: f"What is the name of the employee with id {e['id']}?"),
        ("remote", "boolean", lambda e: f"Is the employee with id {e['id']} remote?"),
    ]
    for i in range(0, len(employees), 6):
        emp = employees[i]
        field, atype, prompt = templates[i // 6 % len(templates)]
        out.append(Question(
            id=qid(),
            prompt=prompt(emp),
            ground_truth=emp[field],
            dataset="L2",
            kind="field-retrieval",
            answer_type=atype,
        ))

    role_counts = Counter(e["role"] for e in employees)
    for role in sorted(role_counts):
        out.append(Question(
            id=qid(),
            prompt=f"How many employees have role '{role}'?",
            ground_truth=role_counts[role],
            dataset="L2",
            kind="aggregation",
            answer_type="integer",
        ))
    out.append(Question(
        id=qid(),
        prompt="How many employees are remote?",
        ground_truth=sum(1 for e in employees if e["remote"]),
        dataset="L2",
        kind="aggregation",
        answer_type="integer",
    ))

    for threshold in (80_000, 100_000, 120_000):
        out.append(Question(
            id=qid(),
            prompt=f"How many employees earn more than {threshold}?",
            ground_truth=sum(1 for e in employees if e["salary"] > threshold),
            dataset="L2",
            kind="cardinality",
            answer_type="integer",
        ))

    for role in ("admin", "dev", "ops"):
        names = [e["name"] for e in employees if e["role"] == role]
        capped = sorted(set(names))[:8]
        out.append(Question(
            id=qid(),
            prompt=(
                f"List the distinct names (up to 8, alphabetical) of employees whose role is "
                f"'{role}'."
            ),
            ground_truth=capped,
            dataset="L2",
            kind="filter-select",
            answer_type="list-unordered",
        ))

    return out
