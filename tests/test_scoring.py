"""Tests for the scoring system."""

from datetime import date

from src.models.match import Match, MatchStage, MatchStatus
from src.scoring.calculator import ScoringCalculator
from src.scoring.rules import ScoringRules, DEFAULT_RULES


def make_match(
    home="Team A",
    away="Team B",
    home_goals=0,
    away_goals=0,
    stage=MatchStage.GROUP,
    home_pen=None,
    away_pen=None,
) -> Match:
    """Helper to create a finished match."""
    return Match(
        match_id="test_001",
        match_date=date(2026, 6, 15),
        stage=stage,
        home_team=home,
        away_team=away,
        home_goals=home_goals,
        away_goals=away_goals,
        home_penalties=home_pen,
        away_penalties=away_pen,
        status=MatchStatus.FINISHED,
    )


class TestGroupStageScoring:
    """Test group stage scoring rules."""

    def test_win_3_0(self):
        """Win 3-0: winner gets 3 (win) + 1.5 (3 goals) = 4.5, loser gets 0"""
        calc = ScoringCalculator()
        match = make_match(home_goals=3, away_goals=0)
        points = calc.calculate_match_points(match)

        # Home: 3 (win) + 3*0.5 (goals scored) = 4.5
        assert points["Team A"] == 4.5
        # Away: 0 (loss) + 0*0.5 (goals scored) = 0
        assert points["Team B"] == 0.0

    def test_draw_1_1(self):
        """Draw 1-1: each team gets 1.5 (draw) + 0.5 (1 goal) = 2.0"""
        calc = ScoringCalculator()
        match = make_match(home_goals=1, away_goals=1)
        points = calc.calculate_match_points(match)

        assert points["Team A"] == 2.0
        assert points["Team B"] == 2.0

    def test_draw_0_0(self):
        """Draw 0-0: each team gets 1.5 (draw) + 0 = 1.5"""
        calc = ScoringCalculator()
        match = make_match(home_goals=0, away_goals=0)
        points = calc.calculate_match_points(match)

        assert points["Team A"] == 1.5
        assert points["Team B"] == 1.5

    def test_win_2_1(self):
        """Win 2-1: winner gets 3 + 1.0 = 4.0, loser gets 0 + 0.5 = 0.5"""
        calc = ScoringCalculator()
        match = make_match(home_goals=2, away_goals=1)
        points = calc.calculate_match_points(match)

        # Home: 3 (win) + 2*0.5 = 4.0
        assert points["Team A"] == 4.0
        # Away: 0 (loss) + 1*0.5 = 0.5
        assert points["Team B"] == 0.5

    def test_high_scoring_draw(self):
        """Draw 3-3: each team gets 1.5 + 1.5 = 3.0"""
        calc = ScoringCalculator()
        match = make_match(home_goals=3, away_goals=3)
        points = calc.calculate_match_points(match)

        assert points["Team A"] == 3.0
        assert points["Team B"] == 3.0


class TestKnockoutScoring:
    """Test knockout stage scoring rules."""

    def test_knockout_win_2_0(self):
        """Knockout win 2-0: winner gets 3 + 2*0.75 = 4.5, loser gets 0"""
        calc = ScoringCalculator()
        match = make_match(
            home_goals=2, away_goals=0, stage=MatchStage.ROUND_OF_16
        )
        points = calc.calculate_match_points(match)

        # Home: 3 (win) + 2*0.75 = 4.5
        assert points["Team A"] == 4.5
        # Away: 0 (loss) + 0*0.75 = 0
        assert points["Team B"] == 0.0

    def test_knockout_draw_with_penalties(self):
        """1-1 after ET, penalties 4-3: winner gets 3 (win) + 0.75, loser gets 0 + 0.75."""
        calc = ScoringCalculator()
        match = make_match(
            home_goals=1,
            away_goals=1,
            stage=MatchStage.QUARTER_FINAL,
            home_pen=4,
            away_pen=3,
        )
        points = calc.calculate_match_points(match)

        # Home won on penalties: 3 (win) + 1*0.75 = 3.75
        assert points["Team A"] == 3.75
        # Away lost on penalties: 0 (loss) + 1*0.75 = 0.75
        assert points["Team B"] == 0.75

    def test_knockout_goal_value_higher(self):
        """Knockout goals worth 0.75 vs group stage 0.5."""
        calc = ScoringCalculator()

        group_match = make_match(home_goals=1, away_goals=0, stage=MatchStage.GROUP)
        ko_match = make_match(home_goals=1, away_goals=0, stage=MatchStage.SEMI_FINAL)

        group_pts = calc.calculate_match_points(group_match)
        ko_pts = calc.calculate_match_points(ko_match)

        # Group: 3 + 0.5 = 3.5
        assert group_pts["Team A"] == 3.5
        # Knockout: 3 + 0.75 = 3.75
        assert ko_pts["Team A"] == 3.75

    def test_final_scoring(self):
        """Final uses knockout scoring."""
        calc = ScoringCalculator()
        match = make_match(home_goals=3, away_goals=1, stage=MatchStage.FINAL)
        points = calc.calculate_match_points(match)

        # Home: 3 (win) + 3*0.75 = 5.25
        assert points["Team A"] == 5.25
        # Away: 0 (loss) + 1*0.75 = 0.75
        assert points["Team B"] == 0.75


class TestPlayerTotals:
    """Test total calculation across multiple matches."""

    def test_player_total_multiple_teams(self):
        """Player with multiple teams accumulates points from all their teams' matches."""
        calc = ScoringCalculator()
        matches = [
            make_match(home="Brazil", away="Germany", home_goals=2, away_goals=0),
            make_match(home="France", away="Brazil", home_goals=1, away_goals=1),
        ]

        # Player owns Brazil and France
        total = calc.calculate_player_total(["Brazil", "France"], matches)

        # Brazil in match 1: 3 + 1.0 = 4.0
        # Brazil in match 2: 1.5 + 0.5 = 2.0
        # France in match 2: 1.5 + 0.5 = 2.0
        assert total == 8.0

    def test_unplayed_match_gives_zero(self):
        """Scheduled matches don't contribute points."""
        calc = ScoringCalculator()
        match = Match(
            match_id="test",
            match_date=date(2026, 7, 1),
            stage=MatchStage.GROUP,
            home_team="Brazil",
            away_team="Germany",
            status=MatchStatus.SCHEDULED,
        )

        total = calc.calculate_player_total(["Brazil"], [match])
        assert total == 0.0
