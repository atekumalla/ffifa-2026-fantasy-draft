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


class TestPenaltyScoreExtraction:
    """Test that penalty shootout goals are properly excluded from regular-time scores."""

    def test_penalty_match_with_regular_time_field(self):
        """When API provides regularTime, use it instead of fullTime for penalty matches."""
        api = FootballDataAPI(api_key="test-key")
        
        # Simulate Germany vs Paraguay: 1-1 after ET, 4-2 on penalties
        # API v4.1 may return fullTime as aggregate (5-3) for penalty matches
        raw_match = {
            "id": 99001,
            "utcDate": "2026-06-29T20:00:00Z",
            "stage": "LAST_16",
            "homeTeam": {"name": "Germany"},
            "awayTeam": {"name": "Paraguay"},
            "status": "FINISHED",
            "score": {
                "duration": "PENALTY_SHOOTOUT",
                "fullTime": {"home": 5, "away": 3},
                "regularTime": {"home": 1, "away": 1},
                "extraTime": {"home": 0, "away": 0},
                "penalties": {"home": 4, "away": 2},
            }
        }
        
        match = api._parse_single_match(raw_match)
        
        # Should use regularTime + extraTime, NOT fullTime
        assert match.home_goals == 1
        assert match.away_goals == 1
        assert match.home_penalties == 4
        assert match.away_penalties == 2

    def test_penalty_match_subtract_from_fulltime(self):
        """When regularTime is missing, subtract penalties from fullTime."""
        api = FootballDataAPI(api_key="test-key")
        
        raw_match = {
            "id": 99002,
            "utcDate": "2026-07-01T18:00:00Z",
            "stage": "LAST_16",
            "homeTeam": {"name": "Brazil"},
            "awayTeam": {"name": "Japan"},
            "status": "FINISHED",
            "score": {
                "duration": "PENALTY_SHOOTOUT",
                "fullTime": {"home": 6, "away": 5},
                "penalties": {"home": 4, "away": 3},
            }
        }
        
        match = api._parse_single_match(raw_match)
        
        # 6-5 fullTime minus 4-3 penalties = 2-2 regular time
        assert match.home_goals == 2
        assert match.away_goals == 2
        assert match.home_penalties == 4
        assert match.away_penalties == 3

    def test_penalty_match_fulltime_already_correct(self):
        """When fullTime is already a draw (API returned correctly), keep it."""
        api = FootballDataAPI(api_key="test-key")
        
        raw_match = {
            "id": 99003,
            "utcDate": "2026-07-02T20:00:00Z",
            "stage": "QUARTER_FINALS",
            "homeTeam": {"name": "England"},
            "awayTeam": {"name": "Colombia"},
            "status": "FINISHED",
            "score": {
                "duration": "PENALTY_SHOOTOUT",
                "fullTime": {"home": 2, "away": 2},
                "penalties": {"home": 5, "away": 4},
            }
        }
        
        match = api._parse_single_match(raw_match)
        
        # fullTime is already a draw, so it's the correct regular-time score
        assert match.home_goals == 2
        assert match.away_goals == 2
        assert match.home_penalties == 5
        assert match.away_penalties == 4

    def test_non_penalty_match_uses_fulltime(self):
        """Non-penalty matches should use fullTime as-is."""
        api = FootballDataAPI(api_key="test-key")
        
        raw_match = {
            "id": 99004,
            "utcDate": "2026-06-20T18:00:00Z",
            "stage": "GROUP_STAGE",
            "group": "GROUP_B",
            "homeTeam": {"name": "France"},
            "awayTeam": {"name": "Australia"},
            "status": "FINISHED",
            "score": {
                "duration": "REGULAR",
                "fullTime": {"home": 3, "away": 1},
                "penalties": {"home": None, "away": None},
            }
        }
        
        match = api._parse_single_match(raw_match)
        
        assert match.home_goals == 3
        assert match.away_goals == 1
        assert match.home_penalties is None
        assert match.away_penalties is None

    def test_penalty_match_extra_time_goals_included(self):
        """Extra time goals should be included in the regular-time score."""
        api = FootballDataAPI(api_key="test-key")
        
        raw_match = {
            "id": 99005,
            "utcDate": "2026-07-03T20:00:00Z",
            "stage": "QUARTER_FINALS",
            "homeTeam": {"name": "Argentina"},
            "awayTeam": {"name": "Netherlands"},
            "status": "FINISHED",
            "score": {
                "duration": "PENALTY_SHOOTOUT",
                "fullTime": {"home": 6, "away": 5},
                "regularTime": {"home": 2, "away": 1},
                "extraTime": {"home": 1, "away": 2},
                "penalties": {"home": 3, "away": 2},
            }
        }
        
        match = api._parse_single_match(raw_match)
        
        # regularTime (2-1) + extraTime (1-2) = 3-3
        assert match.home_goals == 3
        assert match.away_goals == 3
        assert match.home_penalties == 3
        assert match.away_penalties == 2

    def test_penalty_scoring_only_counts_regular_goals(self):
        """Verify that scoring calculator uses only regular-time goals for penalty matches.
        Penalty winner gets full win points (3), loser gets 0."""
        from src.scoring.calculator import ScoringCalculator
        from src.scoring.rules import DEFAULT_RULES
        
        calculator = ScoringCalculator(DEFAULT_RULES)
        
        # Match: 1-1 after ET, 4-2 on penalties (Germany wins)
        match = Match(
            match_id="pen_test",
            match_date=datetime(2026, 6, 29).date(),
            stage=MatchStage.ROUND_OF_16,
            home_team="Germany",
            away_team="Paraguay",
            home_goals=1,  # Regular time only
            away_goals=1,
            home_penalties=4,
            away_penalties=2,
            status=MatchStatus.FINISHED,
        )
        
        points = calculator.calculate_match_points(match)
        
        # Germany (penalty winner): 1 goal × 0.75 + 3 (win) = 3.75
        assert points["Germany"] == 3.75
        # Paraguay (penalty loser): 1 goal × 0.75 + 0 (loss) = 0.75
        assert points["Paraguay"] == 0.75


if __name__ == "__main__":
    pytest.main([__file__, "-v"])
