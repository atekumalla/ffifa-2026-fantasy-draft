"""Schedule sheet — manages the 'Match Schedule' tab in Google Sheets.

Sheet layout:
  | Date | Stage | Group | Home Team | Away Team | Home Goals | Away Goals | Home Pen | Away Pen | Status | Home Pts | Away Pts | Kickoff Time | Venue |
"""

from __future__ import annotations

import logging
from datetime import date, datetime
from typing import TYPE_CHECKING

from src.models.match import Match, MatchStage, MatchStatus

if TYPE_CHECKING:
    from src.sheets.client import SheetsClient

logger = logging.getLogger(__name__)

WORKSHEET_TITLE = "Match Schedule"

# Column headers for the schedule sheet
HEADERS = [
    "Date",
    "Stage",
    "Group",
    "Home Team",
    "Away Team",
    "Home Goals",
    "Away Goals",
    "Home Penalties",
    "Away Penalties",
    "Status",
    "Home Points",
    "Away Points",
    "Kickoff Time",
    "Venue",
]


def read_schedule(client: SheetsClient) -> list[Match]:
    """Read the match schedule from Google Sheets."""
    data = client.read_all_values(WORKSHEET_TITLE)

    if not data or len(data) < 2:
        logger.warning("No schedule data found in sheet")
        return []

    matches = []
    for i, row in enumerate(data[1:], start=2):  # Skip header
        if not row or len(row) < 5:
            continue
        try:
            match = _row_to_match(row, i)
            matches.append(match)
        except Exception as e:
            logger.warning(f"Failed to parse row {i}: {e}")

    logger.info(f"Loaded {len(matches)} matches from sheet")
    return matches


def write_schedule(client: SheetsClient, matches: list[Match]):
    """Write the full match schedule to Google Sheets."""
    rows = [HEADERS]
    for match in sorted(matches, key=lambda m: m.match_date):
        rows.append(_match_to_row(match))

    client.write_all_values(WORKSHEET_TITLE, rows)
    logger.info(f"Wrote {len(matches)} matches to '{WORKSHEET_TITLE}'")


def update_match_result(
    client: SheetsClient,
    match: Match,
    home_points: float,
    away_points: float,
    row_index: int,
):
    """Update a specific match row with scores and points."""
    # Columns F-L (6-12) are the score/status/points columns
    values = [
        [
            match.home_goals if match.home_goals is not None else "",
            match.away_goals if match.away_goals is not None else "",
            match.home_penalties if match.home_penalties is not None else "",
            match.away_penalties if match.away_penalties is not None else "",
            match.status.value,
            home_points,
            away_points,
        ]
    ]
    range_str = f"F{row_index}:L{row_index}"
    client.update_range(WORKSHEET_TITLE, range_str, values)


def _match_to_row(match: Match, home_pts: float = 0, away_pts: float = 0) -> list:
    """Convert a Match to a sheet row."""
    return [
        match.match_date.isoformat(),
        match.stage.value,
        match.group or "",
        match.home_team,
        match.away_team,
        match.home_goals if match.home_goals is not None else "",
        match.away_goals if match.away_goals is not None else "",
        match.home_penalties if match.home_penalties is not None else "",
        match.away_penalties if match.away_penalties is not None else "",
        match.status.value,
        home_pts,
        away_pts,
        match.kickoff_time.isoformat() if match.kickoff_time else "",
        match.venue or "",
    ]


def _row_to_match(row: list, row_index: int) -> Match:
    """Convert a sheet row to a Match object."""
    # Pad row to expected length
    while len(row) < len(HEADERS):
        row.append("")

    stage_map = {s.value: s for s in MatchStage}
    status_map = {s.value: s for s in MatchStatus}

    # Parse kickoff time (ISO format with timezone)
    kickoff_time = None
    if row[12] and row[12].strip():
        try:
            kickoff_time = datetime.fromisoformat(row[12])
        except (ValueError, IndexError):
            pass

    # Parse venue
    venue = row[13] if len(row) > 13 and row[13] else None

    return Match(
        match_id=f"sheet_row_{row_index}",
        match_date=date.fromisoformat(row[0]),
        kickoff_time=kickoff_time,
        venue=venue,
        stage=stage_map.get(row[1], MatchStage.GROUP),
        group=row[2] or None,
        home_team=row[3],
        away_team=row[4],
        home_goals=int(row[5]) if row[5] not in ("", None) else None,
        away_goals=int(row[6]) if row[6] not in ("", None) else None,
        home_penalties=int(row[7]) if row[7] not in ("", None) else None,
        away_penalties=int(row[8]) if row[8] not in ("", None) else None,
        status=status_map.get(row[9], MatchStatus.SCHEDULED),
    )
