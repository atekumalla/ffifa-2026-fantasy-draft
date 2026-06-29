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
        ["", "Win", rules.knockout_win, "Team that advances (incl. penalty winner)"],
        ["", "Loss", 0, "Team eliminated gets 0 result points"],
        ["", "Goal Scored", rules.knockout_goal_scored, "Per goal in regular/extra time ONLY"],
        [],
        ["IMPORTANT NOTES", "", "", ""],
        ["", "No Draw in Knockouts", "", "There's always a winner — penalty winner gets 3 pts"],
        ["", "Penalty Shootout Goals", "0 pts", "Penalty goals do NOT earn goal points"],
        ["", "Extra Time Goals", "0.75 pts", "Goals in extra time count at knockout rate"],
        ["", "Goals Conceded", "0", "No negative points for goals conceded"],
        [],
        ["EXAMPLE", "", "", ""],
        ["", "Germany 1-1 Paraguay", "", "Match goes to penalties (4-2)"],
        ["", "Germany (winner):", "3.75 pts", "1 goal × 0.75 + 3 (win)"],
        ["", "Paraguay (loser):", "0.75 pts", "1 goal × 0.75 + 0 (loss)"],
    ]

    client.write_all_values(WORKSHEET_TITLE, rows)
    logger.info("Wrote scoring rules to sheet")
