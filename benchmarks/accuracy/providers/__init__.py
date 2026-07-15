"""LLM provider adapters — one thin wrapper per SDK.

Each provider exposes ``Provider(model_id).complete(system, user) -> (text, usage)``
where ``usage`` is ``{"prompt_tokens": int|None, "response_tokens": int|None}``.
Missing token counts are surfaced as None so the report can fall back to
character-based cost.

Real providers are constructed on demand — imports are lazy so the harness
still works when a provider's SDK isn't installed.
"""

from __future__ import annotations

from typing import Protocol


class Provider(Protocol):
    model: str

    def complete(self, system: str, user: str) -> tuple[str, dict[str, int | None]]:
        ...


def get_provider(model: str) -> Provider:
    """Route ``model`` (e.g. ``openai:gpt-5-nano``) to the right adapter."""
    if ":" not in model:
        raise ValueError(f"model id must be 'provider:name' (got {model!r})")
    kind, _, name = model.partition(":")
    if kind == "mock":
        from .mock_provider import MockProvider
        return MockProvider(name)
    if kind == "openai":
        from .openai_provider import OpenAIProvider
        return OpenAIProvider(name)
    if kind == "anthropic":
        from .anthropic_provider import AnthropicProvider
        return AnthropicProvider(name)
    if kind == "google":
        from .google_provider import GoogleProvider
        return GoogleProvider(name)
    raise ValueError(f"unknown provider kind: {kind!r}")
