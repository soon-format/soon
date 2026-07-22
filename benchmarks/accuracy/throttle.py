"""Per-provider request throttling for the parallel harness.

One :class:`Throttle` is shared by all worker threads of a provider. It does
two things:

- **RPM pacing** (optional): spaces request starts ``60/rpm`` seconds apart.
- **Cooperative 429 cooldown**: when any worker hits a rate-limit error it
  calls :meth:`cooldown`, and every worker's next :meth:`wait` blocks until
  the cooldown expires — so one 429 pauses the whole pool instead of each
  thread discovering the limit on its own.

Concurrency itself is bounded by the ThreadPoolExecutor size, not here.
"""

from __future__ import annotations

import threading
import time


class Throttle:
    def __init__(self, rpm: float | None = None) -> None:
        self._lock = threading.Lock()
        self._interval = 60.0 / rpm if rpm else 0.0
        self._next_slot = 0.0
        self._resume_at = 0.0

    def wait(self) -> None:
        """Block until a request may start (cooldown elapsed + RPM slot)."""
        while True:
            with self._lock:
                pause = self._resume_at - time.monotonic()
            if pause <= 0:
                break
            time.sleep(pause)
        if self._interval:
            with self._lock:
                now = time.monotonic()
                slot = max(self._next_slot, now)
                self._next_slot = slot + self._interval
            if slot > now:
                time.sleep(slot - now)

    def cooldown(self, seconds: float) -> None:
        """Pause all workers for at least ``seconds`` (extends, never shortens)."""
        with self._lock:
            self._resume_at = max(self._resume_at, time.monotonic() + seconds)


def is_rate_limit_error(exc: BaseException) -> bool:
    """Best-effort 429 detection across the openai/anthropic/google SDKs."""
    if getattr(exc, "status_code", None) == 429:
        return True
    if getattr(exc, "code", None) == 429:
        return True
    name = type(exc).__name__.lower()
    if "ratelimit" in name or "resourceexhausted" in name or "toomanyrequests" in name:
        return True
    text = str(exc).lower()
    return "429" in text or "rate limit" in text or "rate_limit" in text or "quota" in text
