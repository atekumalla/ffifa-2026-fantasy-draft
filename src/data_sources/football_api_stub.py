"""Stubbed Football Data API - returns empty results for demo mode.

This stub allows testing all other components (Google Sheets, OpenAI validation,
UI, etc.) without making real API calls to football-data.org.
"""

from __future__ import annotations

import logging
from typing import Optional

from src.models.match import Match

logger = logging.getLogger(__name__)


class FootballDataAPIStub:
    """
    Stubbed Football API client that returns no data.
    
    This allows demo mode to:
    - Use real Google Sheets
    - Test validation with OpenAI
    - Test UI rendering
    - Avoid real API rate limits and dependencies
    """

    def __init__(self):
        logger.info("Using STUBBED Football API (no real API calls)")

    def fetch_matches(self, competition: str = "WC") -> list[Match]:
        """Return empty list - no matches from API."""
        logger.info("Football API stub: fetch_matches() - returning empty list")
        return []

    def fetch_match_details(self, match_id: str) -> Optional[Match]:
        """Return None - no match details from API."""
        logger.info(f"Football API stub: fetch_match_details({match_id}) - returning None")
        return None

    def get_competition_standings(self, competition: str = "WC") -> dict:
        """Return empty standings."""
        logger.info("Football API stub: get_competition_standings() - returning empty dict")
        return {}
