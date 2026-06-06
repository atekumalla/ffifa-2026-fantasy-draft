"""Tests for sheets module (mocked — no actual Google API calls)."""

from datetime import date
from unittest.mock import MagicMock, patch

from src.models.match import Match, MatchStage, MatchStatus
from src.models.player import DraftPlayer
from src.sheets.schedule import _match_to_row, _row_to_match, HEADERS
from src.sheets.players import read_draft_picks


class TestScheduleConversion:
    """Test match <-> row conversion."""

    def test_match_to_row_group(self):
        match = Match(
            match_id="GS_001",
            match_date=date(2026, 6, 15),
            stage=MatchStage.GROUP,
            group="A",
            home_team="Brazil",
            away_team="Germany",
            home_goals=2,
            away_goals=1,
            status=MatchStatus.FINISHED,
        )
        row = _match_to_row(match)

        assert row[0] == "2026-06-15"
        assert row[1] == "group"
        assert row[2] == "A"
        assert row[3] == "Brazil"
        assert row[4] == "Germany"
        assert row[5] == 2
        assert row[6] == 1

    def test_row_to_match_round_trip(self):
        """Converting match -> row -> match preserves data."""
        original = Match(
            match_id="test",
            match_date=date(2026, 7, 5),
            stage=MatchStage.ROUND_OF_16,
            group=None,
            home_team="France",
            away_team="Spain",
            home_goals=3,
            away_goals=2,
            status=MatchStatus.FINISHED,
        )
        row = _match_to_row(original)
        # row_to_match expects row index for match_id
        reconstructed = _row_to_match(row, 5)

        assert reconstructed.match_date == original.match_date
        assert reconstructed.stage == original.stage
        assert reconstructed.home_team == original.home_team
        assert reconstructed.away_team == original.away_team
        assert reconstructed.home_goals == original.home_goals
        assert reconstructed.away_goals == original.away_goals

    def test_scheduled_match_has_no_goals(self):
        """Scheduled matches have empty goal fields."""
        match = Match(
            match_id="GS_010",
            match_date=date(2026, 6, 20),
            stage=MatchStage.GROUP,
            group="C",
            home_team="Mexico",
            away_team="Japan",
            status=MatchStatus.SCHEDULED,
        )
        row = _match_to_row(match)
        assert row[5] == ""  # home_goals
        assert row[6] == ""  # away_goals


class TestDraftPicksParsing:
    """Test reading draft picks from sheet data."""

    def test_read_draft_picks(self):
        """Mock sheet data should parse into DraftPlayer objects."""
        mock_client = MagicMock()
        mock_client.read_all_values.return_value = [
            ["Player", "Team 1", "Team 2", "Team 3"],
            ["Alice", "Brazil", "France", "Germany"],
            ["Bob", "Spain", "Italy", "Argentina"],
        ]

        players = read_draft_picks(mock_client)

        assert len(players) == 2
        assert players[0].name == "Alice"
        assert players[0].teams == ["Brazil", "France", "Germany"]
        assert players[1].name == "Bob"
        assert len(players[1].teams) == 3
