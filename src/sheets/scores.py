"""Leaderboard sheet — manages the 'Leaderboard' tab in Google Sheets.

Sheet layout:
  | Rank | Player | Total Points | Team 1 (pts) | Team 2 (pts) | ... | Team 10 (pts) |

After knockout stages begin, eliminated teams are shown with strikethrough
formatting and moved to the bottom of each player's team list.
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

# Draft picks may use different names than the match schedule / API.
# This maps draft-pick names → canonical match names so points are found.
_TEAM_ALIASES = {
    "Czechia": "Czech Republic",
    "Bosnia & Herzegovina": "Bosnia and Herzegovina",
    "Congo": "DR Congo",
}


def get_eliminated_teams(matches: list[Match]) -> set[str]:
    """
    Determine all eliminated teams — both from knockout losses AND
    teams that failed to advance past the group stage.

    A team is considered eliminated from the group stage if:
      1. All group matches in their group are finished
      2. The team does NOT appear in any knockout match
    """
    eliminated = set()

    # 1. Teams knocked out in knockout matches (lost a knockout game)
    for match in matches:
        loser = match.knockout_loser
        if loser:
            eliminated.add(loser)

    # 2. Teams eliminated at the group stage (didn't advance)
    eliminated.update(_get_group_stage_eliminated(matches))

    return eliminated


def _get_group_stage_eliminated(matches: list[Match]) -> set[str]:
    """
    Find teams that didn't advance past the group stage.

    Logic: If all matches in a group are finished AND knockout matches
    have real team names (not TBD), any group team not in knockouts is out.
    """
    from src.models.match import MatchStage

    # Collect group stage info: group → list of matches
    group_matches: dict[str, list[Match]] = {}
    group_teams: dict[str, set[str]] = {}

    for match in matches:
        if match.stage == MatchStage.GROUP and match.group:
            group_matches.setdefault(match.group, []).append(match)
            group_teams.setdefault(match.group, set()).update(
                [match.home_team, match.away_team]
            )

    # Collect all teams that appear in any knockout match (with real names)
    knockout_teams: set[str] = set()
    for match in matches:
        if match.stage.is_knockout:
            # Skip placeholder/TBD team names
            if "TBD" not in match.home_team:
                knockout_teams.add(match.home_team)
            if "TBD" not in match.away_team:
                knockout_teams.add(match.away_team)

    # If no knockout teams with real names exist yet, can't determine elimination
    if not knockout_teams:
        return set()

    # For each group where ALL matches are finished, find teams not in knockouts
    eliminated = set()
    for group, group_match_list in group_matches.items():
        all_finished = all(m.is_played for m in group_match_list)
        if not all_finished:
            continue
        # Teams in this group that didn't make it to knockouts
        teams_in_group = group_teams.get(group, set())
        for team in teams_in_group:
            if team not in knockout_teams:
                eliminated.add(team)

    return eliminated


def _has_knockout_started(matches: list[Match]) -> bool:
    """Check if at least one knockout match has been played."""
    return any(
        match.stage.is_knockout and match.is_played
        for match in matches
    )


def write_leaderboard(
    client: SheetsClient,
    players: list[DraftPlayer],
    matches: list[Match],
    calculator: ScoringCalculator,
):
    """
    Calculate and write the leaderboard to Google Sheets.

    Shows each player's total points and per-team breakdown.
    After knockout stages begin, eliminated teams get strikethrough
    formatting and are moved to the bottom of the team list.
    """
    # Pre-compute points per team across all matches
    team_points: dict[str, float] = {}
    for match in matches:
        match_pts = calculator.calculate_match_points(match)
        for team, pts in match_pts.items():
            team_points[team] = team_points.get(team, 0.0) + pts

    # Determine eliminated teams (only relevant once knockouts start)
    knockout_started = _has_knockout_started(matches)
    eliminated_teams = get_eliminated_teams(matches) if knockout_started else set()

    # Build rows
    max_teams = max((p.team_count for p in players), default=10)
    header = ["Rank", "Player", "Total Points"] + [f"Team {i+1}" for i in range(max_teams)]
    rows = [header]

    # Calculate totals and sort
    player_scores = []
    # Track which cells (row, col) contain eliminated teams for formatting
    eliminated_cells: list[tuple[int, int]] = []

    for player in players:
        total = 0.0
        active_details = []
        eliminated_details = []
        for team in player.teams:
            canonical = _TEAM_ALIASES.get(team, team)
            pts = round(team_points.get(canonical, 0.0), 2)
            total += pts
            detail = (pts, f"{team} ({pts})")
            if knockout_started and canonical in eliminated_teams:
                eliminated_details.append(detail)
            else:
                active_details.append(detail)
        total = round(total, 2)
        # Sort each group by points descending (highest scoring teams first)
        active_details.sort(key=lambda x: x[0], reverse=True)
        eliminated_details.sort(key=lambda x: x[0], reverse=True)
        # Active teams first, then eliminated teams at the bottom
        ordered_details = [d[1] for d in active_details] + [d[1] for d in eliminated_details]
        player_scores.append((player.name, total, ordered_details, len(active_details)))

    # Sort by total descending
    player_scores.sort(key=lambda x: x[1], reverse=True)

    for rank, (name, total, details, active_count) in enumerate(player_scores, start=1):
        row = [rank, name, total] + details + [""] * (max_teams - len(details))
        rows.append(row)
        # Track eliminated team cells (0-indexed row in sheet = rank, col starts at 3)
        if knockout_started:
            for col_offset in range(active_count, len(details)):
                # row index in sheet is rank (1-indexed data rows, +1 for header)
                eliminated_cells.append((rank, 3 + col_offset))

    client.write_all_values(WORKSHEET_TITLE, rows)
    logger.info(f"Updated leaderboard with {len(player_scores)} players")

    # Apply strikethrough formatting to eliminated team cells
    if eliminated_cells:
        _apply_eliminated_formatting(client, eliminated_cells)

    return player_scores


def _apply_eliminated_formatting(
    client: SheetsClient, eliminated_cells: list[tuple[int, int]]
):
    """Apply strikethrough and gray color to eliminated team cells in the leaderboard."""
    from src.sheets.formatting import format_eliminated_teams
    try:
        ws = client.get_or_create_worksheet(WORKSHEET_TITLE)
        format_eliminated_teams(ws, eliminated_cells)
    except Exception as e:
        logger.warning(f"Failed to apply eliminated team formatting: {e}")


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
