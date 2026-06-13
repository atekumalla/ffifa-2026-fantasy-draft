"""Scoring calculator — computes fantasy points for matches."""

from __future__ import annotations

from src.models.match import Match, MatchStage
from src.scoring.rules import ScoringRules, DEFAULT_RULES


class ScoringCalculator:
    """Calculates fantasy draft points for each team in a match."""

    def __init__(self, rules: ScoringRules | None = None):
        self.rules = rules or DEFAULT_RULES

    def calculate_match_points(self, match: Match) -> dict[str, float]:
        """
        Calculate fantasy points for both teams in a match.

        Returns:
            Dict mapping team name -> points earned in this match.
            Empty dict if match hasn't been played yet.
        """
        if not match.is_live_or_finished:
            return {}

        is_knockout = match.stage.is_knockout
        home_goals = match.home_goals_regular
        away_goals = match.away_goals_regular

        home_points = self._calculate_team_points(
            goals_scored=home_goals,
            goals_conceded=away_goals,
            is_knockout=is_knockout,
        )
        away_points = self._calculate_team_points(
            goals_scored=away_goals,
            goals_conceded=home_goals,
            is_knockout=is_knockout,
        )

        # Add result points (win/draw)
        result = match.result_for_team
        home_points += self._result_points(result.get(match.home_team, ""), is_knockout)
        away_points += self._result_points(result.get(match.away_team, ""), is_knockout)

        return {
            match.home_team: round(home_points, 2),
            match.away_team: round(away_points, 2),
        }

    def _calculate_team_points(
        self, goals_scored: int, goals_conceded: int, is_knockout: bool
    ) -> float:
        """Calculate goal-based points for a single team."""
        if is_knockout:
            gf_multiplier = self.rules.knockout_goal_scored
            ga_multiplier = self.rules.knockout_goal_conceded
        else:
            gf_multiplier = self.rules.group_goal_scored
            ga_multiplier = self.rules.group_goal_conceded

        return (goals_scored * gf_multiplier) + (goals_conceded * ga_multiplier)

    def _result_points(self, result: str, is_knockout: bool) -> float:
        """Points for win/draw result."""
        if result == "win":
            return self.rules.knockout_win if is_knockout else self.rules.group_win
        elif result == "draw":
            return self.rules.knockout_draw if is_knockout else self.rules.group_draw
        return 0.0

    def calculate_player_total(
        self, player_teams: list[str], matches: list[Match]
    ) -> float:
        """Calculate total points for a draft player across all their teams."""
        total = 0.0
        for match in matches:
            points = self.calculate_match_points(match)
            for team in player_teams:
                total += points.get(team, 0.0)
        return round(total, 2)
