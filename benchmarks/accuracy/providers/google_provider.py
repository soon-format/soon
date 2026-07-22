"""Google Gemini provider.

Uses the official ``google-genai`` SDK. Requires ``GEMINI_API_KEY``.
"""

from __future__ import annotations

import os


class GoogleProvider:
    def __init__(self, name: str) -> None:
        try:
            from google import genai
        except ImportError as exc:  # pragma: no cover
            raise RuntimeError(
                "pip install google-genai to use the google provider"
            ) from exc
        self._client = genai.Client(api_key=os.environ["GEMINI_API_KEY"])
        self.model = f"google:{name}"
        self._model_name = name

    def complete(self, system: str, user: str) -> tuple[str, dict[str, int | None]]:
        from google.genai import types

        resp = self._client.models.generate_content(
            model=self._model_name,
            contents=user,
            config=types.GenerateContentConfig(
                system_instruction=system,
                temperature=0,
            ),
        )
        text = getattr(resp, "text", "") or ""
        # google-genai usage metadata shape varies; probe defensively.
        um = getattr(resp, "usage_metadata", None)
        return text, {
            "prompt_tokens": getattr(um, "prompt_token_count", None) if um else None,
            "response_tokens": getattr(um, "candidates_token_count", None) if um else None,
        }
