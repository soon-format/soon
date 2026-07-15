"""Fixture-keyed deterministic provider for CI and dev-loop use.

Answers are looked up in ``fixtures/mock_answers.json`` — a
``{question_id: expected_answer}`` map. If the question isn't in the
fixture, we return the ground-truth answer computed at generation time
(so a nightly CI run stays green as long as the pipeline is intact).

The mock always reports the correct answer — it's a plumbing test, not
a real evaluation. Use a real provider for actual measurements.
"""

from __future__ import annotations

import json
from pathlib import Path

_FIXTURE_PATH = Path(__file__).resolve().parents[1] / "fixtures" / "mock_answers.json"

_ANSWERS: dict[str, str] | None = None


def _load_fixture() -> dict[str, str]:
    global _ANSWERS
    if _ANSWERS is None:
        if _FIXTURE_PATH.exists():
            _ANSWERS = json.loads(_FIXTURE_PATH.read_text(encoding="utf-8"))
        else:
            _ANSWERS = {}
    return _ANSWERS


class MockProvider:
    def __init__(self, name: str) -> None:
        self.model = f"mock:{name}"

    def complete(self, system: str, user: str) -> tuple[str, dict[str, int | None]]:
        del system  # unused — mock doesn't look at the prompt
        # The user prompt embeds "question:<id>" for the mock to route on.
        # See evaluate.compose_prompt.
        answers = _load_fixture()
        for line in user.splitlines():
            if line.startswith("question:"):
                qid = line.split(":", 1)[1].strip()
                if qid in answers:
                    return answers[qid], {"prompt_tokens": None, "response_tokens": None}
        # Empty response — the harness will score it as wrong, which is
        # the right signal when fixtures are stale.
        return "", {"prompt_tokens": None, "response_tokens": None}
