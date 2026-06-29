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

# Mapping API country names to our internal names
# The API may use different naming conventions than our seed data
_COUNTRY_NAME_MAP = {
    "Czechia": "Czech Republic",
    "Korea Republic": "South Korea",
    "Bosnia-Herzegovina": "Bosnia and Herzegovina",
    "United States": "USA",
    "Cape Verde Islands": "Cape Verde",
    "Congo DR": "DR Congo",
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


def _normalize_team_name(api_name: str) -> str:
    """Normalize team names from the API to match our internal conventions.
    
    Args:
        api_name: Team name as returned by the API
        
    Returns:
        Normalized team name matching our seed data
    """
    return _COUNTRY_NAME_MAP.get(api_name, api_name)



class FootballDataAPI:
    """Client for football-data.org REST API v4."""

    # Class-level venue cache (persists across instances within the same process)
    _venue_cache: dict[str, str] = {}

    def __init__(self, api_key: str | None = None):
        self.api_key = api_key or Config.FOOTBALL_API_KEY
        self.base_url = Config.FOOTBALL_API_BASE_URL
        self.competition = Config.FOOTBALL_API_COMPETITION
        self.session = requests.Session()
        self.session.headers.update({
            "X-Auth-Token": self.api_key,
            "X-Api-Version": "v4.1",
        })

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
    
    def fetch_live_and_finished_matches(self) -> list[Match]:
        """Fetch live (in-play) and finished matches."""
        logger.info(f"Fetching live and finished matches (today: {date.today()})")
        
        all_matches = {}
        
        # Fetch today's matches (all statuses for today)
        today_matches = self.fetch_todays_matches()
        logger.info(f"Today's matches: {len(today_matches)} total")
        for m in today_matches:
            logger.info(f"  - {m.home_team} vs {m.away_team}: {m.status.value} (ID: {m.match_id}, Date: {m.match_date})")
            all_matches[m.match_id] = m
        
        # Fetch finished matches to catch any from recent days
        finished_matches = self.fetch_finished_matches()
        logger.info(f"Finished matches (by status): {len(finished_matches)} total")
        for m in finished_matches:
            if m.match_id not in all_matches:
                logger.info(f"  - {m.home_team} vs {m.away_team}: {m.status.value} (ID: {m.match_id}, Date: {m.match_date})")
            all_matches[m.match_id] = m
        
        # Also try fetching by status=IN_PLAY to catch live matches
        try:
            params = {"status": "IN_PLAY"}
            data = self._get(f"competitions/{self.competition}/matches", params=params)
            live_matches = self._parse_matches(data.get("matches", []))
            logger.info(f"Live matches (by status): {len(live_matches)} total")
            for m in live_matches:
                logger.info(f"  - {m.home_team} vs {m.away_team}: {m.status.value} (ID: {m.match_id}, Date: {m.match_date})")
                all_matches[m.match_id] = m  # Live data takes precedence
        except Exception as e:
            logger.warning(f"Failed to fetch IN_PLAY matches: {e}")
        
        # Combine and deduplicate by match_id
        for m in today_matches:
            all_matches[m.match_id] = m  # Today's data takes precedence
        
        result = list(all_matches.values())
        logger.info(f"Combined result: {len(result)} matches")
        return result

    def fetch_todays_matches(self) -> list[Match]:
        """Fetch today's matches."""
        return self.fetch_matches_by_date(date.today())

    def _parse_matches(self, raw_matches: list[dict]) -> list[Match]:
        """Parse API response into Match models."""
        matches = []
        for m in raw_matches:
            try:
                match = self._parse_single_match(m)
                if match is not None:
                    matches.append(match)
            except Exception as e:
                logger.warning(f"Failed to parse match {m.get('id')}: {e}")
        return matches

    def _parse_single_match(self, m: dict) -> Match | None:
        """Parse a single match from the API response. Returns None for TBD knockout matches."""
        score = m.get("score", {})
        full_time = score.get("fullTime", {})
        penalties = score.get("penalties", {})
        duration = score.get("duration", "")
        regular_time = score.get("regularTime", {})
        extra_time = score.get("extraTime", {})

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

        # Parse teams — API returns null for TBD knockout matches
        home_team_raw = m.get("homeTeam", {}).get("name") or None
        away_team_raw = m.get("awayTeam", {}).get("name") or None
        
        # Skip matches where teams haven't been determined yet (knockout TBD)
        if not home_team_raw or not away_team_raw:
            return None
        
        # Normalize team names to match our internal conventions
        home_team = _normalize_team_name(home_team_raw)
        away_team = _normalize_team_name(away_team_raw)
        
        # Log any name translations for debugging
        if home_team != home_team_raw or away_team != away_team_raw:
            logger.info(
                f"Team name translation: '{home_team_raw}' -> '{home_team}', "
                f"'{away_team_raw}' -> '{away_team}' (Status: {status_str})"
            )

        # Parse group
        group = m.get("group", "")
        if group:
            group = group.replace("GROUP_", "")  # "GROUP_A" -> "A"

        # Parse venue (only available from individual match endpoint)
        venue = m.get("venue")

        # Determine regular-time goals (excluding penalty shootout goals).
        # The football-data.org API v4.1 'fullTime' field may include penalty
        # goals in the aggregate for PENALTY_SHOOTOUT matches. We need to
        # extract only the goals scored during regular/extra time.
        home_goals, away_goals = self._extract_regular_time_goals(
            full_time, penalties, regular_time, extra_time, duration
        )

        # Extract penalty shootout score
        home_pen = penalties.get("home") if penalties else None
        away_pen = penalties.get("away") if penalties else None

        # Log penalty match details for debugging
        if duration == "PENALTY_SHOOTOUT":
            logger.info(
                f"Penalty match: {home_team} vs {away_team} — "
                f"FT(raw): {full_time.get('home')}-{full_time.get('away')}, "
                f"RegularTime: {regular_time.get('home')}-{regular_time.get('away')}, "
                f"ExtraTime: {extra_time.get('home')}-{extra_time.get('away')}, "
                f"Penalties: {home_pen}-{away_pen}, "
                f"Computed regular goals: {home_goals}-{away_goals}"
            )

        return Match(
            match_id=str(m.get("id", "")),
            match_date=match_date,
            kickoff_time=kickoff,
            venue=venue,
            stage=stage,
            group=group if group else None,
            home_team=home_team,
            away_team=away_team,
            home_goals=home_goals,
            away_goals=away_goals,
            home_penalties=home_pen,
            away_penalties=away_pen,
            minute=m.get("minute"),
            injury_time=m.get("injuryTime"),
            status=status,
        )

    def _extract_regular_time_goals(
        self,
        full_time: dict,
        penalties: dict,
        regular_time: dict,
        extra_time: dict,
        duration: str,
    ) -> tuple[Optional[int], Optional[int]]:
        """Extract only regular/extra-time goals, excluding penalty shootout goals.

        The football-data.org API v4.1 may return aggregate scores (including
        penalty goals) in the 'fullTime' field for penalty shootout matches.
        This method uses 'regularTime' + 'extraTime' fields when available to
        get the true pre-penalty score.

        Returns:
            Tuple of (home_goals, away_goals) for regular + extra time only.
        """
        if duration != "PENALTY_SHOOTOUT":
            # Non-penalty match: fullTime is the correct score
            return full_time.get("home"), full_time.get("away")

        # Penalty shootout match — need to exclude penalty goals.
        # Strategy 1: Use regularTime + extraTime if available
        if regular_time and regular_time.get("home") is not None:
            home_reg = regular_time.get("home", 0)
            away_reg = regular_time.get("away", 0)
            # Add extra time goals if available
            if extra_time and extra_time.get("home") is not None:
                home_reg += extra_time.get("home", 0)
                away_reg += extra_time.get("away", 0)
            return home_reg, away_reg

        # Strategy 2: If fullTime appears to include penalties, subtract them
        ft_home = full_time.get("home")
        ft_away = full_time.get("away")
        pen_home = penalties.get("home", 0) if penalties else 0
        pen_away = penalties.get("away", 0) if penalties else 0

        if ft_home is not None and ft_away is not None and pen_home and pen_away:
            # Check if fullTime looks inflated (larger than what penalties-only would suggest)
            computed_home = ft_home - pen_home
            computed_away = ft_away - pen_away
            # Sanity check: the regular-time score in a penalty match should be a draw
            if computed_home >= 0 and computed_away >= 0 and computed_home == computed_away:
                logger.info(
                    f"Corrected penalty-inflated fullTime: {ft_home}-{ft_away} -> "
                    f"{computed_home}-{computed_away} (subtracted penalties {pen_home}-{pen_away})"
                )
                return computed_home, computed_away

        # Strategy 3: Fallback — if fullTime is already a draw, it's likely correct
        if ft_home is not None and ft_away is not None and ft_home == ft_away:
            return ft_home, ft_away

        # Last resort: use fullTime as-is (may be wrong but best available)
        logger.warning(
            f"Could not determine regular-time score for penalty match. "
            f"fullTime={ft_home}-{ft_away}, penalties={pen_home}-{pen_away}. Using fullTime."
        )
        return ft_home, ft_away

    def fetch_match_venue(self, match_id: str) -> str | None:
        """Fetch venue for a single match from the individual match endpoint.
        
        The bulk matches endpoint doesn't include venue, so we need to
        call the individual match endpoint to get it.
        Uses a class-level cache to avoid repeat API calls.
        """
        # Check cache first
        if match_id in self._venue_cache:
            return self._venue_cache[match_id]

        try:
            data = self._get(f"matches/{match_id}")
            venue = data.get("venue")
            if venue:
                self._venue_cache[match_id] = venue
                logger.debug(f"Cached venue for match {match_id}: {venue}")
            return venue
        except Exception as e:
            logger.warning(f"Failed to fetch venue for match {match_id}: {e}")
            return None

    def enrich_matches_with_venues(self, matches: list[Match]) -> list[Match]:
        """Enrich matches with venue info, fetching from API where needed.
        
        Only fetches venues for matches that don't already have one cached.
        Includes a small delay between requests to avoid rate limiting.
        
        Args:
            matches: List of matches to enrich (must have football-data.org IDs)
            
        Returns:
            The same list of matches with venue field populated where possible
        """
        import time

        requests_made = 0
        for match in matches:
            # Skip if venue already set
            if match.venue:
                continue

            # Check cache
            if match.match_id in self._venue_cache:
                match.venue = self._venue_cache[match.match_id]
                continue

            # Skip non-numeric IDs (e.g. sheet_row_XX) — not valid API IDs
            if not match.match_id.isdigit():
                continue

            # Throttle: wait between requests to avoid rate limits
            if requests_made > 0:
                time.sleep(6)  # ~10 requests/minute stays well within limits

            venue = self.fetch_match_venue(match.match_id)
            if venue:
                match.venue = venue
            requests_made += 1

        cached_count = sum(1 for m in matches if m.venue)
        logger.info(f"Venue enrichment: {cached_count}/{len(matches)} matches have venues "
                   f"({requests_made} API calls made)")
        return matches

    def enrich_schedule_from_api(self, sheet_matches: list[Match]) -> list[Match]:
        """Enrich sheet matches with kickoff times and venues from the API.
        
        Fetches all matches from the API bulk endpoint (1 API call) to get
        kickoff times, then fetches venues individually for upcoming matches.
        
        Args:
            sheet_matches: Matches loaded from the Google Sheet
            
        Returns:
            Enriched matches with kickoff_time and venue where available
        """
        try:
            api_matches = self.fetch_all_matches()
            logger.info(f"Fetched {len(api_matches)} matches from API for enrichment")
        except Exception as e:
            logger.warning(f"Failed to fetch matches for enrichment: {e}")
            return sheet_matches

        # Build a lookup from composite key to API match
        from src.sync.recovery import _match_key
        api_index: dict[str, Match] = {}
        for m in api_matches:
            key = _match_key(m)
            api_index[key] = m

        # Enrich sheet matches with kickoff_time and API match_id
        for sheet_match in sheet_matches:
            key = _match_key(sheet_match)
            if key in api_index:
                api_match = api_index[key]
                # Copy kickoff_time from API (which parses utcDate)
                if api_match.kickoff_time and not sheet_match.kickoff_time:
                    sheet_match.kickoff_time = api_match.kickoff_time
                # Update match_id to the API ID so venue fetching works
                if api_match.match_id.isdigit():
                    sheet_match.match_id = api_match.match_id
                # Copy venue if already available (from individual endpoint)
                if api_match.venue and not sheet_match.venue:
                    sheet_match.venue = api_match.venue

        # Now fetch venues for upcoming matches using the correct API IDs
        from src.models.match import MatchStatus
        upcoming = [m for m in sheet_matches if m.status == MatchStatus.SCHEDULED and not m.venue]
        upcoming.sort(key=lambda m: m.match_date)
        if upcoming:
            self.enrich_matches_with_venues(upcoming)

        return sheet_matches
