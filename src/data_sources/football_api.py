"""Football-data.org API v4 client for FIFA World Cup 2026 match data.

Free tier: 10 requests/minute, covers all major competitions including World Cup.
Sign up: https://www.football-data.org/client/register
"""

from __future__ import annotations

import logging
from datetime import date, datetime
from typing import Optional

import requests
from tenacity import retry, stop_after_attempt, wait_exponential

from src.config import Config
from src.models.match import Match, MatchStage, MatchStatus

logger = logging.getLogger(__name__)

# Mapping football-data.org stage names to our MatchStage enum
_STAGE_MAP = {
    "GROUP_STAGE": MatchStage.GROUP,
    "LAST_32": MatchStage.ROUND_OF_32,
    "LAST_16": MatchStage.ROUND_OF_16,
    "QUARTER_FINALS": MatchStage.QUARTER_FINAL,
    "SEMI_FINALS": MatchStage.SEMI_FINAL,
    "THIRD_PLACE": MatchStage.THIRD_PLACE,
    "FINAL": MatchStage.FINAL,
}

_STATUS_MAP = {
    "SCHEDULED": MatchStatus.SCHEDULED,
    "TIMED": MatchStatus.SCHEDULED,
    "IN_PLAY": MatchStatus.IN_PLAY,
    "PAUSED": MatchStatus.IN_PLAY,
    "FINISHED": MatchStatus.FINISHED,
    "POSTPONED": MatchStatus.POSTPONED,
    "CANCELLED": MatchStatus.POSTPONED,
}


class FootballDataAPI:
    """Client for football-data.org REST API v4."""

    def __init__(self, api_key: str | None = None):
        self.api_key = api_key or Config.FOOTBALL_API_KEY
        self.base_url = Config.FOOTBALL_API_BASE_URL
        self.competition = Config.FOOTBALL_API_COMPETITION
        self.session = requests.Session()
        self.session.headers.update({"X-Auth-Token": self.api_key})

    @retry(stop=stop_after_attempt(3), wait=wait_exponential(min=2, max=30))
    def _get(self, endpoint: str, params: dict | None = None) -> dict:
        """Make authenticated GET request with retry logic."""
        url = f"{self.base_url}/{endpoint}"
        response = self.session.get(url, params=params, timeout=30)

        if response.status_code == 429:
            logger.warning("Rate limited by football-data.org, retrying...")
            raise requests.exceptions.HTTPError("Rate limited")

        response.raise_for_status()
        return response.json()

    def fetch_all_matches(self) -> list[Match]:
        """Fetch all World Cup 2026 matches (scheduled + completed)."""
        data = self._get(f"competitions/{self.competition}/matches")
        return self._parse_matches(data.get("matches", []))

    def fetch_matches_by_date(self, match_date: date) -> list[Match]:
        """Fetch matches for a specific date."""
        params = {
            "dateFrom": match_date.isoformat(),
            "dateTo": match_date.isoformat(),
        }
        data = self._get(f"competitions/{self.competition}/matches", params=params)
        return self._parse_matches(data.get("matches", []))

    def fetch_finished_matches(self) -> list[Match]:
        """Fetch only completed matches."""
        params = {"status": "FINISHED"}
        data = self._get(f"competitions/{self.competition}/matches", params=params)
        return self._parse_matches(data.get("matches", []))

    def fetch_todays_matches(self) -> list[Match]:
        """Fetch today's matches."""
        return self.fetch_matches_by_date(date.today())

    def _parse_matches(self, raw_matches: list[dict]) -> list[Match]:
        """Parse API response into Match models."""
        matches = []
        for m in raw_matches:
            try:
                match = self._parse_single_match(m)
                matches.append(match)
            except Exception as e:
                logger.warning(f"Failed to parse match {m.get('id')}: {e}")
        return matches

    def _parse_single_match(self, m: dict) -> Match:
        """Parse a single match from the API response."""
        score = m.get("score", {})
        full_time = score.get("fullTime", {})
        penalties = score.get("penalties", {})

        # Parse date
        utc_date = m.get("utcDate", "")
        match_date = datetime.fromisoformat(utc_date.replace("Z", "+00:00")).date()
        kickoff = datetime.fromisoformat(utc_date.replace("Z", "+00:00"))

        # Parse stage
        stage_str = m.get("stage", "GROUP_STAGE")
        stage = _STAGE_MAP.get(stage_str, MatchStage.GROUP)

        # Parse status
        status_str = m.get("status", "SCHEDULED")
        status = _STATUS_MAP.get(status_str, MatchStatus.SCHEDULED)

        # Parse teams
        home_team = m.get("homeTeam", {}).get("name", "TBD")
        away_team = m.get("awayTeam", {}).get("name", "TBD")

        # Parse group
        group = m.get("group", "")
        if group:
            group = group.replace("GROUP_", "")  # "GROUP_A" -> "A"

        return Match(
            match_id=str(m.get("id", "")),
            match_date=match_date,
            kickoff_time=kickoff,
            stage=stage,
            group=group if group else None,
            home_team=home_team,
            away_team=away_team,
            home_goals=full_time.get("home"),
            away_goals=full_time.get("away"),
            home_penalties=penalties.get("home"),
            away_penalties=penalties.get("away"),
            status=status,
        )
