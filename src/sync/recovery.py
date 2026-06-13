"""Recovery module — handles resuming after crashes or restarts.

On startup:
  1. Load state from disk (last_sync.json)
  2. Read current data from Google Sheet
  3. Determine what's changed since last sync
  4. Fetch any missing scores
  5. Update sheet and state
"""

from __future__ import annotations

import logging
from datetime import date, datetime
from typing import Optional

from src.models.match import Match, MatchStatus
from src.sync.state_manager import StateManager

logger = logging.getLogger(__name__)


def get_matches_needing_update(
    matches: list[Match], state: StateManager
) -> list[Match]:
    """
    Determine which matches need score updates.

    A match needs updating if:
      - It's scheduled for today or earlier
      - Its status isn't FINISHED in our records
      - It hasn't been marked as scored in state
    """
    today = date.today()
    needs_update = []

    for match in matches:
        # Skip future matches
        if match.match_date > today:
            continue

        # Skip already-scored matches
        if state.is_match_scored(match.match_id):
            continue

        # Skip matches already marked finished with scores
        if match.status == MatchStatus.FINISHED and match.home_goals is not None:
            # This match has a score but wasn't in state — mark it
            state.mark_match_scored(match.match_id)
            continue

        needs_update.append(match)

    logger.info(
        f"Recovery check: {len(needs_update)} matches need updates "
        f"(out of {len(matches)} total)"
    )
    return needs_update


def reconcile_matches(
    sheet_matches: list[Match], api_matches: list[Match]
) -> list[Match]:
    """
    Merge API data with sheet data, preferring API data for finished matches.

    Returns the reconciled list of matches.
    """
    # Index API matches by a composite key
    api_index: dict[str, Match] = {}
    for m in api_matches:
        key = _match_key(m)
        api_index[key] = m

    reconciled = []
    for sheet_match in sheet_matches:
        key = _match_key(sheet_match)
        if key in api_index:
            api_match = api_index[key]
            # If API says finished or in-play, take API data (it's more current)
            if api_match.status in (MatchStatus.FINISHED, MatchStatus.IN_PLAY):
                reconciled.append(api_match)
            else:
                reconciled.append(sheet_match)
        else:
            reconciled.append(sheet_match)

    # Add any API matches not in sheet
    sheet_keys = {_match_key(m) for m in sheet_matches}
    for key, api_match in api_index.items():
        if key not in sheet_keys:
            reconciled.append(api_match)

    return sorted(reconciled, key=lambda m: m.match_date)


# Normalize team names for consistent key matching
# Handles cases where API returned unnormalized names in previous syncs
_KEY_NORMALIZE = {
    "united states": "usa",
    "cape verde islands": "cape verde",
    "congo dr": "dr congo",
    "czechia": "czech republic",
    "bosnia-herzegovina": "bosnia and herzegovina",
    "korea republic": "south korea",
}


def _normalize_for_key(name: str) -> str:
    """Normalize a team name for key matching purposes."""
    lower = name.lower()
    return _KEY_NORMALIZE.get(lower, lower)


def _match_key(match: Match) -> str:
    """Create a lookup key for a match (stage + teams, ignoring date due to timezone differences).
    
    The Football API may return matches with UTC dates that differ from local timezone dates,
    causing the same match to be keyed differently. Using stage + normalized team names ensures
    proper matching while allowing the same teams to play in different stages (e.g., group vs knockout).
    """
    teams = sorted([_normalize_for_key(match.home_team), _normalize_for_key(match.away_team)])
    return f"{match.stage.value}_{teams[0]}_{teams[1]}"
