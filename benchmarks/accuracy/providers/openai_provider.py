"""OpenAI Responses/Chat provider.

Uses the official ``openai`` SDK. Requires ``OPENAI_API_KEY``.
"""

from __future__ import annotations

import os


class OpenAIProvider:
    def __init__(self, name: str) -> None:
        try:
            from openai import OpenAI
        except ImportError as exc:  # pragma: no cover
            raise RuntimeError(
                "pip install openai to use the openai provider"
            ) from exc
        self._client = OpenAI(api_key=os.environ["OPENAI_API_KEY"], timeout=30)
        self.model = f"openai:{name}"
        self._model_name = name

    def complete(self, system: str, user: str) -> tuple[str, dict[str, int | None]]:
        resp = self._client.chat.completions.create(
            model=self._model_name,
            temperature=0,
            messages=[
                {"role": "system", "content": system},
                {"role": "user", "content": user},
            ],
        )
        text = resp.choices[0].message.content or ""
        usage = getattr(resp, "usage", None)
        return text, {
            "prompt_tokens": getattr(usage, "prompt_tokens", None) if usage else None,
            "response_tokens": getattr(usage, "completion_tokens", None) if usage else None,
        }
