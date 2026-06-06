"""Draft Picks sheet — manages the 'Draft Picks' tab in Google Sheets.

Sheet layout:
  | Player | Team 1 | Team 2 | ... | Team 10 |
  | Abhinav | Brazil | Germany | ... | ... |
  | Friend1 | ... | ... | ... | ... |
"""

from __future__ import annotations

import logging
from typing import TYPE_CHECKING

from src.models.player import DraftPlayer

if TYPE_CHECKING:
    from src.sheets.client import SheetsClient

logger = logging.getLogger(__name__)

WORKSHEET_TITLE = "Draft Picks"


def read_draft_picks(client: SheetsClient) -> list[DraftPlayer]:
    """Read draft picks from the Google Sheet and return DraftPlayer objects."""
    data = client.read_all_values(WORKSHEET_TITLE)

    if not data or len(data) < 2:
        logger.warning("No draft pick data found in sheet")
        return []

    # First row is header: Player, Team 1, Team 2, ..., Team 10
    players = []
    for row in data[1:]:  # Skip header
        if not row or not row[0].strip():
            continue
        name = row[0].strip()
        teams = [cell.strip() for cell in row[1:] if cell.strip()]
        players.append(DraftPlayer(name=name, teams=teams))

    logger.info(f"Loaded {len(players)} draft players from sheet")
    return players


def write_draft_picks(client: SheetsClient, players: list[DraftPlayer]):
    """Write draft picks to the Google Sheet."""
    max_teams = max((p.team_count for p in players), default=10)

    # Header row
    header = ["Player"] + [f"Team {i+1}" for i in range(max_teams)]

    rows = [header]
    for player in players:
        row = [player.name] + player.teams + [""] * (max_teams - player.team_count)
        rows.append(row)

    client.write_all_values(WORKSHEET_TITLE, rows)
    logger.info(f"Wrote {len(players)} players to '{WORKSHEET_TITLE}'")
