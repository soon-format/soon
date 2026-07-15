"""Single-question evaluation loop.

Composes the prompt, calls the provider, normalizes and scores the
response, and returns an :class:`EvaluationResult`. Retries on transient
errors are handled here so the top-level loop stays a simple pipeline.
"""

from __future__ import annotations

import time

from .normalize import compare
from .providers import Provider
from .types import EvaluationResult, Question

SYSTEM_PROMPT = (
    "You answer questions about the data below. Respond with ONLY the answer value — "
    "no explanation, no units unless part of the value, no markdown. If the answer is a "
    "list, use comma-separated values. Booleans are 'yes' or 'no'."
)


def compose_prompt(question: Question, format_primer: str, rendered_data: str, fence: str) -> str:
    return (
        f"Format: {format_primer}\n"
        f"question:{question.id}\n"  # mock provider parses this
        f"\n```{fence}\n{rendered_data}\n```\n"
        f"\nQuestion: {question.prompt}"
    )


def evaluate_one(
    provider: Provider,
    question: Question,
    format_name: str,
    format_primer: str,
    fence: str,
    rendered_data: str,
    *,
    retries: int = 2,
    backoff_seconds: float = 2.0,
) -> EvaluationResult:
    user_prompt = compose_prompt(question, format_primer, rendered_data, fence)
    attempt = 0
    last_error: str | None = None
    while attempt <= retries:
        try:
            raw, usage = provider.complete(SYSTEM_PROMPT, user_prompt)
            correct, normalized = compare(raw, question.ground_truth, question.answer_type)
            return EvaluationResult(
                question_id=question.id,
                format=format_name,
                model=provider.model,
                dataset=question.dataset,
                kind=question.kind,
                ground_truth=question.ground_truth,
                raw_response=raw,
                normalized=normalized,
                correct=correct,
                prompt_chars=len(user_prompt),
                response_chars=len(raw),
                prompt_tokens=usage.get("prompt_tokens"),
                response_tokens=usage.get("response_tokens"),
            )
        except Exception as exc:  # pragma: no cover — retry loop
            last_error = f"{type(exc).__name__}: {exc}"
            attempt += 1
            if attempt <= retries:
                time.sleep(backoff_seconds * attempt)
    return EvaluationResult(
        question_id=question.id,
        format=format_name,
        model=provider.model,
        dataset=question.dataset,
        kind=question.kind,
        ground_truth=question.ground_truth,
        raw_response="",
        normalized=None,
        correct=False,
        prompt_chars=len(user_prompt),
        response_chars=0,
        error=last_error,
    )
