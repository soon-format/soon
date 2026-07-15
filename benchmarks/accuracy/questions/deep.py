"""L6 questions — deeply nested org tree (org → teams → projects → tasks)."""

from __future__ import annotations

from typing import Any

from ..types import Question


def generate(data: Any) -> list[Question]:
    org = data["org"]
    teams = org["teams"]
    out: list[Question] = []
    q = 0

    def qid() -> str:
        nonlocal q
        q += 1
        return f"L6-{q:03d}"

    for team in teams:
        out.append(Question(
            id=qid(),
            prompt=f"Who is the lead of {team['team']}?",
            ground_truth=team["lead"],
            dataset="L6",
            kind="path",
            answer_type="string",
        ))
        out.append(Question(
            id=qid(),
            prompt=f"How many projects does {team['team']} have?",
            ground_truth=len(team["projects"]),
            dataset="L6",
            kind="aggregation",
            answer_type="integer",
        ))
        first_project = team["projects"][0]
        out.append(Question(
            id=qid(),
            prompt=f"What is the budget of project {first_project['key']}?",
            ground_truth=first_project["budget"],
            dataset="L6",
            kind="path",
            answer_type="integer",
        ))
        out.append(Question(
            id=qid(),
            prompt=f"How many tasks are in project {first_project['key']}?",
            ground_truth=len(first_project["tasks"]),
            dataset="L6",
            kind="aggregation",
            answer_type="integer",
        ))

    # A cross-tree tally per team: total tasks anywhere under it.
    for team in teams:
        total_tasks = sum(len(p["tasks"]) for p in team["projects"])
        out.append(Question(
            id=qid(),
            prompt=f"How many tasks does {team['team']} have in total across all its projects?",
            ground_truth=total_tasks,
            dataset="L6",
            kind="aggregation",
            answer_type="integer",
        ))

    return out
