"""Team model — represents a country in the World Cup."""

from __future__ import annotations

from pydantic import BaseModel


class Team(BaseModel):
    """A national team participating in the World Cup."""

    name: str  # e.g. "Brazil", "Germany"
    code: str = ""  # FIFA code e.g. "BRA", "GER"
    group: str = ""  # Group letter e.g. "A"

    def __hash__(self):
        return hash(self.name.lower())

    def __eq__(self, other):
        if isinstance(other, Team):
            return self.name.lower() == other.name.lower()
        if isinstance(other, str):
            return self.name.lower() == other.lower()
        return False
