"""Anthropic Messages API provider.

Uses the official ``anthropic`` SDK. Requires ``ANTHROPIC_API_KEY``.
"""

from __future__ import annotations

import os


class AnthropicProvider:
    def __init__(self, name: str) -> None:
        try:
            from anthropic import Anthropic
        except ImportError as exc:  # pragma: no cover
            raise RuntimeError(
                "pip install anthropic to use the anthropic provider"
            ) from exc
        self._client = Anthropic(api_key=os.environ["ANTHROPIC_API_KEY"])
        self.model = f"anthropic:{name}"
        self._model_name = name

    def complete(self, system: str, user: str) -> tuple[str, dict[str, int | None]]:
        resp = self._client.messages.create(
            model=self._model_name,
            max_tokens=1024,
            system=system,
            messages=[{"role": "user", "content": user}],
        )
        text = "".join(
            block.text for block in resp.content if getattr(block, "type", None) == "text"
        )
        usage = getattr(resp, "usage", None)
        return text, {
            "prompt_tokens": getattr(usage, "input_tokens", None) if usage else None,
            "response_tokens": getattr(usage, "output_tokens", None) if usage else None,
        }
