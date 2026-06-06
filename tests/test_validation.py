"""Tests for the validation module."""

from datetime import date

from src.models.match import Match, MatchStage, MatchStatus
from src.models.player import DraftPlayer
from src.validation import (
    validate_structural,
    ValidationReport,
)


def _make_match(
    match_id="m1",
    home="Team A",
    away="Team B",
    home_goals=None,
    away_goals=None,
    status=MatchStatus.SCHEDULED,
    stage=MatchStage.GROUP,
    match_date=None,
):
    return Match(
        match_id=match_id,
        match_date=match_date or date(2026, 6, 15),
        stage=stage,
        home_team=home,
        away_team=away,
        home_goals=home_goals,
        away_goals=away_goals,
        status=status,
    )


def _make_players():
    """Create valid 4 players × 10 teams."""
    return [
        DraftPlayer(name="P1", teams=[f"Team {i}" for i in range(1, 11)]),
        DraftPlayer(name="P2", teams=[f"Team {i}" for i in range(11, 21)]),
        DraftPlayer(name="P3", teams=[f"Team {i}" for i in range(21, 31)]),
        DraftPlayer(name="P4", teams=[f"Team {i}" for i in range(31, 41)]),
    ]


class TestStructuralValidation:
    def test_healthy_data(self):
        """Valid data should produce a healthy report."""
        matches = [
            _make_match(match_id=f"m{i}", home=f"H{i}", away=f"A{i}")
            for i in range(104)
        ]
        players = _make_players()

        report = validate_structural(matches, players)
        assert report.is_healthy
        assert report.error_count == 0

    def test_missing_matches(self):
        """Should flag if fewer than 104 matches."""
        matches = [_make_match(match_id=f"m{i}") for i in range(50)]
        players = _make_players()

        report = validate_structural(matches, players)
        assert not report.is_healthy
        assert any("Missing matches" in i.message for i in report.issues)

    def test_duplicate_matches(self):
        """Should flag duplicate match entries."""
        m = _make_match(match_id="m1", home="Brazil", away="Germany")
        matches = [m, m] + [
            _make_match(match_id=f"m{i}", home=f"H{i}", away=f"A{i}")
            for i in range(102)
        ]
        players = _make_players()

        report = validate_structural(matches, players)
        assert any("duplicate" in i.message.lower() for i in report.issues)

    def test_finished_without_scores(self):
        """Finished match without scores should be flagged."""
        matches = [
            _make_match(
                match_id="m1",
                status=MatchStatus.FINISHED,
                home_goals=None,  # Missing!
                away_goals=None,
            )
        ] + [
            _make_match(match_id=f"m{i}", home=f"H{i}", away=f"A{i}")
            for i in range(103)
        ]
        players = _make_players()

        report = validate_structural(matches, players)
        assert any("FINISHED but missing scores" in i.message for i in report.issues)

    def test_scheduled_with_scores(self):
        """Scheduled match with scores should be flagged."""
        matches = [
            _make_match(
                match_id="m1",
                status=MatchStatus.SCHEDULED,
                home_goals=2,
                away_goals=1,
            )
        ] + [
            _make_match(match_id=f"m{i}", home=f"H{i}", away=f"A{i}")
            for i in range(103)
        ]
        players = _make_players()

        report = validate_structural(matches, players)
        assert any("SCHEDULED but has scores" in i.message for i in report.issues)

    def test_wrong_player_count(self):
        """Should flag if not exactly 4 players."""
        matches = [_make_match(match_id=f"m{i}") for i in range(104)]
        players = [
            DraftPlayer(name="P1", teams=[f"Team {i}" for i in range(1, 11)]),
            DraftPlayer(name="P2", teams=[f"Team {i}" for i in range(11, 21)]),
        ]

        report = validate_structural(matches, players)
        assert any("Expected 4 players" in i.message for i in report.issues)

    def test_wrong_team_count(self):
        """Should flag if a player doesn't have exactly 10 teams."""
        matches = [_make_match(match_id=f"m{i}") for i in range(104)]
        players = [
            DraftPlayer(name="P1", teams=["Team 1", "Team 2"]),  # Only 2!
            DraftPlayer(name="P2", teams=[f"Team {i}" for i in range(11, 21)]),
            DraftPlayer(name="P3", teams=[f"Team {i}" for i in range(21, 31)]),
            DraftPlayer(name="P4", teams=[f"Team {i}" for i in range(31, 41)]),
        ]

        report = validate_structural(matches, players)
        assert any("has 2 teams" in i.message for i in report.issues)

    def test_duplicate_team_assignment(self):
        """Should flag if same team assigned to two players."""
        matches = [_make_match(match_id=f"m{i}") for i in range(104)]
        players = [
            DraftPlayer(name="P1", teams=[f"Team {i}" for i in range(1, 11)]),
            DraftPlayer(name="P2", teams=[f"Team {i}" for i in range(1, 11)]),  # Same!
            DraftPlayer(name="P3", teams=[f"Team {i}" for i in range(21, 31)]),
            DraftPlayer(name="P4", teams=[f"Team {i}" for i in range(31, 41)]),
        ]

        report = validate_structural(matches, players)
        assert any("multiple players" in i.message.lower() for i in report.issues)

    def test_unreasonable_score(self):
        """Should warn about very high-scoring matches."""
        matches = [
            _make_match(
                match_id="m1",
                status=MatchStatus.FINISHED,
                home_goals=15,
                away_goals=0,
            )
        ] + [
            _make_match(match_id=f"m{i}", home=f"H{i}", away=f"A{i}")
            for i in range(103)
        ]
        players = _make_players()

        report = validate_structural(matches, players)
        assert any("Unusual score" in i.message for i in report.issues)
