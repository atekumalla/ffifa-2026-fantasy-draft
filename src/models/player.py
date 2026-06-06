"""Draft Player model — represents one of the 4 friends in the fantasy draft."""

from __future__ import annotations

from pydantic import BaseModel, Field


class DraftPlayer(BaseModel):
    """A person participating in the fantasy draft (you or your friends)."""

    name: str  # e.g. "Abhinav", "Friend1"
    teams: list[str] = Field(default_factory=list)  # List of team names picked
    total_points: float = 0.0

    @property
    def team_count(self) -> int:
        return len(self.teams)
