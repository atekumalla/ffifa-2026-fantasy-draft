"""Tests for Football API client, especially country name normalization."""

from datetime import datetime

import pytest

from src.data_sources.football_api import FootballDataAPI, _normalize_team_name
from src.models.match import Match, MatchStage, MatchStatus


class TestCountryNameNormalization:
    """Test that API country names are normalized to match our seed data."""

    def test_czechia_normalized_to_czech_republic(self):
        """Czechia from API should become Czech Republic."""
        assert _normalize_team_name("Czechia") == "Czech Republic"

    def test_bosnia_herzegovina_normalized(self):
        """Bosnia-Herzegovina from API should become Bosnia and Herzegovina."""
        assert _normalize_team_name("Bosnia-Herzegovina") == "Bosnia and Herzegovina"

    def test_korea_republic_normalized(self):
        """Korea Republic from API should become South Korea."""
        assert _normalize_team_name("Korea Republic") == "South Korea"

    def test_other_countries_unchanged(self):
        """Countries without mappings should pass through unchanged."""
        assert _normalize_team_name("Brazil") == "Brazil"
        assert _normalize_team_name("Germany") == "Germany"
        assert _normalize_team_name("South Korea") == "South Korea"

    def test_tbd_unchanged(self):
        """TBD placeholder should not be modified."""
        assert _normalize_team_name("TBD") == "TBD"


class TestMatchParsing:
    """Test that match parsing applies country name normalization."""

    def test_parse_match_with_czechia(self):
        """Match with Czechia should have Czech Republic in the parsed result."""
        api = FootballDataAPI(api_key="test-key")
        
        # Simulate API response with Czechia
        raw_match = {
            "id": 12345,
            "utcDate": "2026-06-11T18:00:00Z",
            "stage": "GROUP_STAGE",
            "group": "GROUP_A",
            "homeTeam": {"name": "South Korea"},
            "awayTeam": {"name": "Czechia"},
            "status": "SCHEDULED",
            "score": {
                "fullTime": {"home": None, "away": None},
                "penalties": {"home": None, "away": None}
            }
        }
        
        match = api._parse_single_match(raw_match)
        
        assert match.home_team == "South Korea"
        assert match.away_team == "Czech Republic"  # Should be normalized
        assert match.group == "A"
        assert match.stage == MatchStage.GROUP

    def test_parse_finished_match_with_czechia(self):
        """Finished match with Czechia should normalize and preserve scores."""
        api = FootballDataAPI(api_key="test-key")
        
        raw_match = {
            "id": 12346,
            "utcDate": "2026-06-18T20:00:00Z",
            "stage": "GROUP_STAGE",
            "group": "GROUP_A",
            "homeTeam": {"name": "Czechia"},
            "awayTeam": {"name": "Mexico"},
            "status": "FINISHED",
            "score": {
                "fullTime": {"home": 2, "away": 1},
                "penalties": {"home": None, "away": None}
            }
        }
        
        match = api._parse_single_match(raw_match)
        
        assert match.home_team == "Czech Republic"  # Normalized
        assert match.away_team == "Mexico"
        assert match.home_goals == 2
        assert match.away_goals == 1
        assert match.status == MatchStatus.FINISHED


if __name__ == "__main__":
    pytest.main([__file__, "-v"])
