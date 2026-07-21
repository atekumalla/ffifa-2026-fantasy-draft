"""Draft configuration loader — single source of truth for player data.

Loads player names, initials, colors, draft picks, picks-per-player, team
aliases, and demo neutral teams from a JSON config file. This removes the need
to hardcode league-specific data across seed_data.py, demo.py,
independent_validator.py, validation.py, the sheet formatters, and the frontend.

The config file location is resolved (in priority order) from:
  1. The ``DRAFT_CONFIG_FILE`` environment variable
  2. ``<project_root>/config/draft_config.json``

Keep ``config/draft_config.json`` as the committed default/example. To run a
different league/deployment, either edit that file or point
``DRAFT_CONFIG_FILE`` at your own JSON.
"""

from __future__ import annotations

import json
import logging
import os
from dataclasses import dataclass, field
from functools import lru_cache
from pathlib import Path

logger = logging.getLogger(__name__)

_PROJECT_ROOT = Path(__file__).resolve().parent.parent
_DEFAULT_CONFIG_PATH = _PROJECT_ROOT / "config" / "draft_config.json"

# Default palette used when a player entry omits an explicit color.
_DEFAULT_COLORS = [
    "#d97706", "#2563eb", "#dc2626", "#7c3aed",
    "#059669", "#db2777", "#0891b2", "#ca8a04",
]


@dataclass(frozen=True)
class PlayerConfig:
    """One drafter's configuration."""

    name: str
    teams: tuple[str, ...]
    initials: str
    color: str


@dataclass(frozen=True)
class DraftConfig:
    """Parsed and validated draft configuration."""

    players: tuple[PlayerConfig, ...]
    picks_per_player: int
    team_aliases: dict[str, str] = field(default_factory=dict)
    neutral_teams: tuple[str, ...] = ()

    @property
    def num_players(self) -> int:
        return len(self.players)

    def canonicalize(self, team_name: str) -> str:
        """Map a draft-pick team name to its canonical schedule name."""
        return self.team_aliases.get(team_name, team_name)


def _config_path() -> Path:
    env_path = os.getenv("DRAFT_CONFIG_FILE", "").strip()
    if env_path:
        return Path(env_path).expanduser().resolve()
    return _DEFAULT_CONFIG_PATH


def _derive_initials(name: str) -> str:
    parts = [p for p in name.split() if p]
    if len(parts) >= 2:
        return (parts[0][0] + parts[1][0]).upper()
    return name[:2].upper()


def _parse(raw: dict, source: str) -> DraftConfig:
    players_raw = raw.get("players")
    if not isinstance(players_raw, list) or not players_raw:
        raise ValueError(f"{source}: 'players' must be a non-empty list")

    picks_per_player = raw.get("picks_per_player")
    if picks_per_player is None:
        # Infer from the first player if not explicitly set.
        picks_per_player = len(players_raw[0].get("teams", []))
    picks_per_player = int(picks_per_player)

    players: list[PlayerConfig] = []
    for i, p in enumerate(players_raw):
        name = str(p.get("name", "")).strip()
        if not name:
            raise ValueError(f"{source}: player #{i + 1} is missing a 'name'")
        teams = tuple(p.get("teams", []))
        initials = str(p.get("initials") or _derive_initials(name)).upper()
        color = str(p.get("color") or _DEFAULT_COLORS[i % len(_DEFAULT_COLORS)])
        players.append(PlayerConfig(name=name, teams=teams, initials=initials, color=color))

    team_aliases = dict(raw.get("team_aliases", {}) or {})
    neutral_teams = tuple(raw.get("neutral_teams", []) or [])

    return DraftConfig(
        players=tuple(players),
        picks_per_player=picks_per_player,
        team_aliases=team_aliases,
        neutral_teams=neutral_teams,
    )


@lru_cache(maxsize=None)
def _load_cached(path_str: str) -> DraftConfig:
    path = Path(path_str)
    if not path.exists():
        raise FileNotFoundError(
            f"Draft config file not found: {path}. "
            f"Copy config/draft_config.example.json to config/draft_config.json "
            f"or set DRAFT_CONFIG_FILE."
        )
    with path.open("r", encoding="utf-8") as f:
        raw = json.load(f)
    config = _parse(raw, source=str(path))
    logger.info(
        "Loaded draft config from %s: %d players, %d picks each",
        path, config.num_players, config.picks_per_player,
    )
    return config


def load_draft_config() -> DraftConfig:
    """Return the parsed draft configuration (cached by resolved path)."""
    return _load_cached(str(_config_path()))


def reload_draft_config() -> DraftConfig:
    """Clear the cache and reload (useful in tests)."""
    _load_cached.cache_clear()
    return load_draft_config()


# ── Convenience accessors ───────────────────────────────────────────────────

def get_players():
    """Return draft players as DraftPlayer models."""
    from src.models.player import DraftPlayer

    return [
        DraftPlayer(name=p.name, teams=list(p.teams))
        for p in load_draft_config().players
    ]


def get_team_aliases() -> dict[str, str]:
    """Return the draft-pick → canonical team-name alias map."""
    return dict(load_draft_config().team_aliases)


def get_picks_per_player() -> int:
    return load_draft_config().picks_per_player


def get_neutral_teams() -> list[str]:
    return list(load_draft_config().neutral_teams)


def canonicalize(team_name: str) -> str:
    return load_draft_config().canonicalize(team_name)


def get_player_meta() -> list[dict]:
    """Return lightweight player metadata for the frontend/API."""
    return [
        {"name": p.name, "initials": p.initials, "color": p.color}
        for p in load_draft_config().players
    ]
