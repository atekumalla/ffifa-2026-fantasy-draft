"""Match model representing a single FIFA World Cup 2026 game."""

from __future__ import annotations

from datetime import date, datetime
from enum import Enum
from typing import Optional

from pydantic import BaseModel, Field


class MatchStage(str, Enum):
    """Tournament stage — determines scoring multipliers."""
    GROUP = "group"
    ROUND_OF_32 = "round_of_32"
    ROUND_OF_16 = "round_of_16"
    QUARTER_FINAL = "quarter_final"
    SEMI_FINAL = "semi_final"
    THIRD_PLACE = "third_place"
    FINAL = "final"

    @property
    def is_knockout(self) -> bool:
        return self != MatchStage.GROUP


class MatchStatus(str, Enum):
    SCHEDULED = "scheduled"
    IN_PLAY = "in_play"
    FINISHED = "finished"
    POSTPONED = "postponed"


class Match(BaseModel):
    """A single World Cup match."""

    match_id: str = Field(description="Unique match identifier")
    match_date: date
    kickoff_time: Optional[datetime] = None
    stage: MatchStage = MatchStage.GROUP
    group: Optional[str] = None  # e.g. "A", "B", etc.

    home_team: str
    away_team: str

    # Scores (None = not yet played)
    home_goals: Optional[int] = None
    away_goals: Optional[int] = None

    # Penalty shootout goals (don't count for scoring)
    home_penalties: Optional[int] = None
    away_penalties: Optional[int] = None

    status: MatchStatus = MatchStatus.SCHEDULED

    @property
    def is_played(self) -> bool:
        """Match is finished."""
        return self.status == MatchStatus.FINISHED

    @property
    def is_live_or_finished(self) -> bool:
        """Match is currently in play or has finished."""
        return self.status in (MatchStatus.IN_PLAY, MatchStatus.FINISHED)

    @property
    def home_goals_regular(self) -> int:
        """Goals scored in regular/extra time (excludes penalties)."""
        return self.home_goals or 0

    @property
    def away_goals_regular(self) -> int:
        """Goals scored in regular/extra time (excludes penalties)."""
        return self.away_goals or 0

    @property
    def result_for_team(self) -> dict[str, str]:
        """Returns 'win', 'draw', or 'loss' for each team."""
        if not self.is_live_or_finished:
            return {}
        hg, ag = self.home_goals_regular, self.away_goals_regular
        if hg > ag:
            return {self.home_team: "win", self.away_team: "loss"}
        elif ag > hg:
            return {self.home_team: "loss", self.away_team: "win"}
        else:
            return {self.home_team: "draw", self.away_team: "draw"}
