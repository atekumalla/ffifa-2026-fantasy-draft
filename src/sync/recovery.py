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

from src.models.match import Match, MatchStage, MatchStatus
from src.sync.state_manager import StateManager

logger = logging.getLogger(__name__)


def update_knockout_bracket(
    sheet_matches: list[Match], api_matches: list[Match]
) -> list[Match]:
    """
    Replace TBD knockout placeholder matches with real matches from the API.

    When the knockout bracket is determined (teams assigned), the API returns
    matches with real team names. This function replaces our TBD placeholders
    with those real matches, preserving group stage matches and any knockout
    matches already populated.

    Args:
        sheet_matches: Current schedule (may have TBD knockout placeholders)
        api_matches: Latest matches from the API (with real team names)

    Returns:
        Updated match list with TBD placeholders replaced where possible
    """
    # Separate sheet matches into group stage and knockout
    group_matches = [m for m in sheet_matches if m.stage == MatchStage.GROUP]
    knockout_sheet = [m for m in sheet_matches if m.stage != MatchStage.GROUP]

    # Identify TBD and non-TBD knockout matches in our sheet
    tbd_by_stage: dict[MatchStage, list[Match]] = {}
    real_knockout_sheet: list[Match] = []

    for m in knockout_sheet:
        if "TBD" in m.home_team or "TBD" in m.away_team:
            tbd_by_stage.setdefault(m.stage, []).append(m)
        else:
            real_knockout_sheet.append(m)

    # Get real knockout matches from the API (non-TBD)
    api_knockout = [
        m for m in api_matches
        if m.stage != MatchStage.GROUP
        and "TBD" not in m.home_team
        and "TBD" not in m.away_team
    ]

    # Build a set of keys already in our sheet (non-TBD knockout matches)
    existing_keys = {_match_key(m) for m in real_knockout_sheet}

    # For each stage, replace TBD placeholders with new API matches
    replacements_made = 0
    for stage, tbd_matches in tbd_by_stage.items():
        # Find API matches for this stage that we don't already have
        new_api_for_stage = [
            m for m in api_knockout
            if m.stage == stage and _match_key(m) not in existing_keys
        ]

        if not new_api_for_stage:
            # No API matches for this stage yet — keep all TBD placeholders
            real_knockout_sheet.extend(tbd_matches)
            continue

        # Sort both by date to align them positionally
        tbd_matches.sort(key=lambda m: m.match_date)
        new_api_for_stage.sort(key=lambda m: m.match_date)

        # Replace TBD matches with API matches (up to how many we have)
        for i, api_match in enumerate(new_api_for_stage):
            if i >= len(tbd_matches):
                # More API matches than TBD slots — add them
                real_knockout_sheet.append(api_match)
                existing_keys.add(_match_key(api_match))
                replacements_made += 1
            else:
                # Replace the TBD placeholder
                real_knockout_sheet.append(api_match)
                existing_keys.add(_match_key(api_match))
                tbd_matches[i] = None  # Mark as replaced
                replacements_made += 1

        # Keep any un-replaced TBD matches (still waiting for those matchups)
        for m in tbd_matches:
            if m is not None:
                real_knockout_sheet.append(m)

    if replacements_made:
        logger.info(
            f"Knockout bracket: replaced {replacements_made} TBD matches with real teams"
        )
    else:
        logger.debug("Knockout bracket: no new matches to fill in")

    # Recombine and sort
    all_matches = group_matches + real_knockout_sheet
    all_matches.sort(key=lambda m: m.match_date)
    return all_matches


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
