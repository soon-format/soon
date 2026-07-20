"""In-memory deterministic provider for CI and dev-loop use.

Answers come from a module-level ``ANSWERS`` map keyed by question id.
``run.py`` populates the map from the ground-truth values on each run,
so the mock always answers correctly regardless of question set drift
— its purpose is to verify plumbing, not to score models.

The map can also be preloaded from ``fixtures/mock_answers.json`` for
tests that don't spin up the full pipeline (see ``test_harness.py``).
"""

from __future__ import annotations

import json
from pathlib import Path

_FIXTURE_PATH = Path(__file__).resolve().parents[1] / "fixtures" / "mock_answers.json"

# Public map: run.py fills this at startup; tests can also override it.
ANSWERS: dict[str, str] = {}


def _load_fixture_if_empty() -> None:
    if ANSWERS:
        return
    if _FIXTURE_PATH.exists():
        ANSWERS.update(json.loads(_FIXTURE_PATH.read_text(encoding="utf-8")))


class MockProvider:
    def __init__(self, name: str) -> None:
        self.model = f"mock:{name}"

    def complete(self, system: str, user: str) -> tuple[str, dict[str, int | None]]:
        del system  # unused — mock doesn't look at the prompt
        _load_fixture_if_empty()
        # The user prompt embeds "question:<id>" for the mock to route on.
        # See evaluate.compose_prompt.
        for line in user.splitlines():
            if line.startswith("question:"):
                qid = line.split(":", 1)[1].strip()
                return ANSWERS.get(qid, ""), {"prompt_tokens": None, "response_tokens": None}
        return "", {"prompt_tokens": None, "response_tokens": None}
