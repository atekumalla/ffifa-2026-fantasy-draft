"""Leaderboard sheet — manages the 'Leaderboard' tab in Google Sheets.

Sheet layout:
  | Rank | Player | Total Points | Team 1 (pts) | Team 2 (pts) | ... | Team 10 (pts) |
"""

from __future__ import annotations

import logging
from typing import TYPE_CHECKING

from src.models.match import Match
from src.models.player import DraftPlayer
from src.scoring.calculator import ScoringCalculator

if TYPE_CHECKING:
    from src.sheets.client import SheetsClient

logger = logging.getLogger(__name__)

WORKSHEET_TITLE = "Leaderboard"


def write_leaderboard(
    client: SheetsClient,
    players: list[DraftPlayer],
    matches: list[Match],
    calculator: ScoringCalculator,
):
    """
    Calculate and write the leaderboard to Google Sheets.

    Shows each player's total points and per-team breakdown.
    """
    # Pre-compute points per team across all matches
    team_points: dict[str, float] = {}
    for match in matches:
        match_pts = calculator.calculate_match_points(match)
        for team, pts in match_pts.items():
            team_points[team] = team_points.get(team, 0.0) + pts

    # Build rows
    # Find max teams for header
    max_teams = max((p.team_count for p in players), default=10)
    header = ["Rank", "Player", "Total Points"] + [f"Team {i+1}" for i in range(max_teams)]
    # Sub-header showing which team and their points
    # Actually, let's make it more readable with team names
    rows = [header]

    # Calculate totals and sort
    player_scores = []
    for player in players:
        total = 0.0
        team_details = []
        for team in player.teams:
            pts = round(team_points.get(team, 0.0), 2)
            total += pts
            team_details.append(f"{team} ({pts})")
        total = round(total, 2)
        player_scores.append((player.name, total, team_details))

    # Sort by total descending
    player_scores.sort(key=lambda x: x[1], reverse=True)

    for rank, (name, total, details) in enumerate(player_scores, start=1):
        row = [rank, name, total] + details + [""] * (max_teams - len(details))
        rows.append(row)

    client.write_all_values(WORKSHEET_TITLE, rows)
    logger.info(f"Updated leaderboard with {len(player_scores)} players")

    return player_scores


def get_team_points_breakdown(
    matches: list[Match], calculator: ScoringCalculator
) -> dict[str, float]:
    """Get cumulative points for every team across all played matches."""
    team_points: dict[str, float] = {}
    for match in matches:
        match_pts = calculator.calculate_match_points(match)
        for team, pts in match_pts.items():
            team_points[team] = round(team_points.get(team, 0.0) + pts, 2)
    return team_points
