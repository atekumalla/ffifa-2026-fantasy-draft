"""Draft pick model — maps a team to the player who drafted it."""

from __future__ import annotations

from pydantic import BaseModel


class DraftPick(BaseModel):
    """A single draft pick: which friend picked which national team."""

    player_name: str  # The friend who picked
    team_name: str  # The national team picked
    pick_order: int = 0  # Order in which they were picked (optional)
