"""Rate limiter — prevents excessive API/LLM calls.

Ensures sync and validate can't be called more than once every 10 minutes,
protecting against accidental DOS and API rate limits.
"""

from __future__ import annotations

import logging
import time
from functools import wraps
from typing import Callable

logger = logging.getLogger(__name__)

# Default cooldown: 10 minutes (600 seconds)
DEFAULT_COOLDOWN_SECONDS = 600


class RateLimiter:
    """Simple per-function rate limiter with configurable cooldown."""

    def __init__(self, cooldown_seconds: int = DEFAULT_COOLDOWN_SECONDS):
        self.cooldown_seconds = cooldown_seconds
        self._last_called: dict[str, float] = {}

    def can_call(self, key: str) -> bool:
        """Check if the function identified by key can be called."""
        last = self._last_called.get(key, 0)
        return (time.time() - last) >= self.cooldown_seconds

    def seconds_until_ready(self, key: str) -> int:
        """Seconds remaining before the function can be called again."""
        last = self._last_called.get(key, 0)
        elapsed = time.time() - last
        remaining = self.cooldown_seconds - elapsed
        return max(0, int(remaining))

    def record_call(self, key: str):
        """Record that the function was just called."""
        self._last_called[key] = time.time()

    def try_call(self, key: str) -> tuple[bool, int]:
        """
        Attempt to call. Returns (allowed, seconds_remaining).
        If allowed, automatically records the call.
        """
        if self.can_call(key):
            self.record_call(key)
            return True, 0
        else:
            remaining = self.seconds_until_ready(key)
            logger.warning(
                f"Rate limited: '{key}' called too soon. "
                f"Wait {remaining}s (cooldown: {self.cooldown_seconds}s)"
            )
            return False, remaining

    def reset(self, key: str):
        """Reset the cooldown for a specific key (for testing)."""
        self._last_called.pop(key, None)


# Global rate limiter instance (shared across the app)
rate_limiter = RateLimiter(cooldown_seconds=DEFAULT_COOLDOWN_SECONDS)
