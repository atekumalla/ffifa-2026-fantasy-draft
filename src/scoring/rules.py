"""Scoring rules for the FIFA 2026 Fantasy Draft.

Rules:
  Group Stage:
    - Win: 3 points
    - Draw: 1.5 points for each team
    - Goal scored: 0.5 points per goal

  Knockout Rounds (Round of 32 onwards till Final):
    - Win (regular time, extra time, OR penalties): 3 points
    - Loss: 0 points
    - Goal scored (regular + extra time only): 0.75 points per goal
    - Penalty shootout goals: DO NOT count (0 points)

  There is NO draw in knockout rounds. The penalty winner gets full 3 win pts.
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

    # Knockout rounds (no draws — penalty winner gets win points)
    knockout_win: float = 3.0
    knockout_draw: float = 0.0  # Not applicable: knockouts always have a winner
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
                "goal_scored": self.knockout_goal_scored,
                "goal_conceded": self.knockout_goal_conceded,
            },
            "notes": [
                "Knockout rounds: penalty winner gets 3 pts (full win)",
                "Penalty shootout goals do NOT count for goal points",
                "Only regular time + extra time goals count",
            ],
        }


# Default rules instance
DEFAULT_RULES = ScoringRules()
