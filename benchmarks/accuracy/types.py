"""Shared dataclasses for the retrieval-accuracy harness."""

from __future__ import annotations

from dataclasses import dataclass, field
from typing import Any


AnswerType = str  # one of: integer, number, boolean, date, string, list-ordered, list-unordered


@dataclass(frozen=True)
class Question:
    """A single retrieval question over a named dataset.

    Ground truth is exact — the value the answer must reduce to under
    ``normalize.compare``. ``answer_type`` selects the normalizer.
    """

    id: str
    prompt: str
    ground_truth: Any
    dataset: str
    kind: str  # field-retrieval | aggregation | filter-select | path | existence | cardinality
    answer_type: AnswerType


@dataclass(frozen=True)
class FormatSpec:
    """A named way to render a dataset for the LLM."""

    name: str
    primer: str  # short text prepended to the prompt so the model knows the format
    fence: str  # markdown code-fence language tag


@dataclass
class EvaluationResult:
    """One (question, format, model) evaluation outcome."""

    question_id: str
    format: str
    model: str
    dataset: str
    kind: str
    ground_truth: Any
    raw_response: str
    normalized: Any
    correct: bool
    prompt_chars: int
    response_chars: int
    prompt_tokens: int | None = None
    response_tokens: int | None = None
    error: str | None = None
    meta: dict[str, Any] = field(default_factory=dict)
