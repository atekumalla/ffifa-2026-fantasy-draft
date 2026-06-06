"""Scoring Rules sheet — writes the rules to a reference tab in Google Sheets.

Sheet layout:
  | Category | Event | Points |
  | Group Stage | Win | 3 |
  | Group Stage | Draw | 1.5 |
  ...
"""

from __future__ import annotations

import logging
from typing import TYPE_CHECKING

from src.scoring.rules import ScoringRules, DEFAULT_RULES

if TYPE_CHECKING:
    from src.sheets.client import SheetsClient

logger = logging.getLogger(__name__)

WORKSHEET_TITLE = "Scoring Rules"


def write_scoring_rules(client: SheetsClient, rules: ScoringRules | None = None):
    """Write scoring rules to a reference tab so anyone looking at the sheet can see them."""
    rules = rules or DEFAULT_RULES

    rows = [
        ["Category", "Event", "Points", "Notes"],
        [],
        ["GROUP STAGE", "", "", ""],
        ["", "Win", rules.group_win, "Team wins the match"],
        ["", "Draw", rules.group_draw, "Match ends in a draw (1.5 pts for each team)"],
        ["", "Goal Scored", rules.group_goal_scored, "Per goal in regular time"],
        [],
        ["KNOCKOUT ROUNDS", "", "", ""],
        ["", "Win", rules.knockout_win, "Team wins (regular/ET)"],
        ["", "Draw (to Penalties)", rules.knockout_draw, "If match goes to shootout"],
        ["", "Goal Scored", rules.knockout_goal_scored, "Per goal in regular/extra time"],
        [],
        ["IMPORTANT NOTES", "", "", ""],
        ["", "Penalty Shootout", "N/A", "Penalty goals do NOT count for scoring"],
        ["", "Extra Time Goals", "Count", "Goals in extra time count as regular goals"],
        ["", "Goals Conceded", "0", "No negative points for goals conceded"],
    ]

    client.write_all_values(WORKSHEET_TITLE, rows)
    logger.info("Wrote scoring rules to sheet")
