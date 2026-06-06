"""Scoring rules for the FIFA 2026 Fantasy Draft.

Rules:
  Group Stage:
    - Win: 3 points
    - Draw: 1.5 points for each team
    - Goal scored: 0.5 points for each goal scored

  Knockout Rounds (Round of 32 onwards till Final):
    - Win: 3 points
    - Draw (after 90/120 min): 1.5 points
    - Goal scored: 0.75 points for each goal scored
    - Penalty shootout goals: DO NOT count
"""

from __future__ import annotations

from dataclasses import dataclass


@dataclass(frozen=True)
class ScoringRules:
    """Immutable scoring rules configuration."""

    # Group stage
    group_win: float = 3.0
    group_draw: float = 1.5
    group_goal_scored: float = 0.5
    group_goal_conceded: float = 0.0  # No negative points

    # Knockout rounds
    knockout_win: float = 3.0
    knockout_draw: float = 1.5  # If match goes to penalties, both teams drew in regular time
    knockout_goal_scored: float = 0.75
    knockout_goal_conceded: float = 0.0  # No negative points

    def to_dict(self) -> dict:
        return {
            "group_stage": {
                "win": self.group_win,
                "draw": self.group_draw,
                "goal_scored": self.group_goal_scored,
                "goal_conceded": self.group_goal_conceded,
            },
            "knockout": {
                "win": self.knockout_win,
                "draw": self.knockout_draw,
                "goal_scored": self.knockout_goal_scored,
                "goal_conceded": self.knockout_goal_conceded,
            },
            "notes": [
                "Penalty shootout goals do NOT count for scoring",
                "Only regular time + extra time goals count",
            ],
        }


# Default rules instance
DEFAULT_RULES = ScoringRules()
