"""Data sources for fetching match scores."""

from .football_api import FootballDataAPI
from .llm_fallback import LLMFallback

__all__ = ["FootballDataAPI", "LLMFallback"]
