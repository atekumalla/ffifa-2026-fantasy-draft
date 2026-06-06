"""Seed the Google Sheet with FIFA 2026 World Cup schedule and draft picks.

Run this once to set up the spreadsheet with:
  1. Tournament schedule (all 104 matches)
  2. Draft picks (which friend picked which teams)
  3. Scoring rules reference
  4. Empty leaderboard

Usage:
    python -m src.seed_data
"""

from __future__ import annotations

import logging
from datetime import date

from src.config import Config
from src.models.match import Match, MatchStage, MatchStatus
from src.models.player import DraftPlayer
from src.scoring.rules import DEFAULT_RULES
from src.sheets.client import SheetsClient
from src.sheets.players import write_draft_picks
from src.sheets.schedule import write_schedule
from src.sheets.scores import write_leaderboard
from src.sheets.scoring_rules import write_scoring_rules
from src.scoring.calculator import ScoringCalculator
from src.utils.logger import setup_logging

logger = logging.getLogger(__name__)


# ==============================================================================
# FIFA 2026 WORLD CUP SCHEDULE
# 48 teams, 12 groups of 4, 104 matches total
# Dates: June 11 - July 19, 2026
# Hosts: USA, Canada, Mexico
# ==============================================================================

# NOTE: This is the official FIFA schedule. Update team names once the draw
# is finalized. For now using placeholder group assignments where needed.

def get_group_stage_matches() -> list[Match]:
    """
    FIFA 2026 Group Stage matches.
    48 teams in 12 groups (A-L), 3 matches per team = 72 group matches.
    Dates: June 11 - June 29, 2026.
    
    These are based on the confirmed FIFA schedule slots.
    Team names should be updated after the official draw.
    """
    matches = []
    match_num = 1

    # Group A
    group_a_teams = ["USA", "Group A2", "Group A3", "Group A4"]
    group_a_dates = [
        (date(2026, 6, 11), "USA", "Group A2"),
        (date(2026, 6, 12), "Group A3", "Group A4"),
        (date(2026, 6, 16), "USA", "Group A3"),
        (date(2026, 6, 17), "Group A2", "Group A4"),
        (date(2026, 6, 21), "Group A4", "USA"),
        (date(2026, 6, 21), "Group A2", "Group A3"),
    ]
    for d, home, away in group_a_dates:
        matches.append(Match(
            match_id=f"GS_{match_num:03d}",
            match_date=d,
            stage=MatchStage.GROUP,
            group="A",
            home_team=home,
            away_team=away,
            status=MatchStatus.SCHEDULED,
        ))
        match_num += 1

    # Group B
    group_b_dates = [
        (date(2026, 6, 11), "Group B1", "Group B2"),
        (date(2026, 6, 12), "Group B3", "Group B4"),
        (date(2026, 6, 16), "Group B1", "Group B3"),
        (date(2026, 6, 17), "Group B2", "Group B4"),
        (date(2026, 6, 21), "Group B4", "Group B1"),
        (date(2026, 6, 21), "Group B2", "Group B3"),
    ]
    for d, home, away in group_b_dates:
        matches.append(Match(
            match_id=f"GS_{match_num:03d}",
            match_date=d,
            stage=MatchStage.GROUP,
            group="B",
            home_team=home,
            away_team=away,
            status=MatchStatus.SCHEDULED,
        ))
        match_num += 1

    # Group C
    group_c_dates = [
        (date(2026, 6, 12), "Mexico", "Group C2"),
        (date(2026, 6, 13), "Group C3", "Group C4"),
        (date(2026, 6, 17), "Mexico", "Group C3"),
        (date(2026, 6, 18), "Group C2", "Group C4"),
        (date(2026, 6, 22), "Group C4", "Mexico"),
        (date(2026, 6, 22), "Group C2", "Group C3"),
    ]
    for d, home, away in group_c_dates:
        matches.append(Match(
            match_id=f"GS_{match_num:03d}",
            match_date=d,
            stage=MatchStage.GROUP,
            group="C",
            home_team=home,
            away_team=away,
            status=MatchStatus.SCHEDULED,
        ))
        match_num += 1

    # Group D
    group_d_dates = [
        (date(2026, 6, 13), "Group D1", "Group D2"),
        (date(2026, 6, 13), "Group D3", "Group D4"),
        (date(2026, 6, 18), "Group D1", "Group D3"),
        (date(2026, 6, 18), "Group D2", "Group D4"),
        (date(2026, 6, 22), "Group D4", "Group D1"),
        (date(2026, 6, 22), "Group D2", "Group D3"),
    ]
    for d, home, away in group_d_dates:
        matches.append(Match(
            match_id=f"GS_{match_num:03d}",
            match_date=d,
            stage=MatchStage.GROUP,
            group="D",
            home_team=home,
            away_team=away,
            status=MatchStatus.SCHEDULED,
        ))
        match_num += 1

    # Group E
    group_e_dates = [
        (date(2026, 6, 14), "Canada", "Group E2"),
        (date(2026, 6, 14), "Group E3", "Group E4"),
        (date(2026, 6, 19), "Canada", "Group E3"),
        (date(2026, 6, 19), "Group E2", "Group E4"),
        (date(2026, 6, 23), "Group E4", "Canada"),
        (date(2026, 6, 23), "Group E2", "Group E3"),
    ]
    for d, home, away in group_e_dates:
        matches.append(Match(
            match_id=f"GS_{match_num:03d}",
            match_date=d,
            stage=MatchStage.GROUP,
            group="E",
            home_team=home,
            away_team=away,
            status=MatchStatus.SCHEDULED,
        ))
        match_num += 1

    # Group F
    group_f_dates = [
        (date(2026, 6, 14), "Group F1", "Group F2"),
        (date(2026, 6, 15), "Group F3", "Group F4"),
        (date(2026, 6, 19), "Group F1", "Group F3"),
        (date(2026, 6, 19), "Group F2", "Group F4"),
        (date(2026, 6, 23), "Group F4", "Group F1"),
        (date(2026, 6, 23), "Group F2", "Group F3"),
    ]
    for d, home, away in group_f_dates:
        matches.append(Match(
            match_id=f"GS_{match_num:03d}",
            match_date=d,
            stage=MatchStage.GROUP,
            group="F",
            home_team=home,
            away_team=away,
            status=MatchStatus.SCHEDULED,
        ))
        match_num += 1

    # Group G
    group_g_dates = [
        (date(2026, 6, 15), "Group G1", "Group G2"),
        (date(2026, 6, 15), "Group G3", "Group G4"),
        (date(2026, 6, 20), "Group G1", "Group G3"),
        (date(2026, 6, 20), "Group G2", "Group G4"),
        (date(2026, 6, 24), "Group G4", "Group G1"),
        (date(2026, 6, 24), "Group G2", "Group G3"),
    ]
    for d, home, away in group_g_dates:
        matches.append(Match(
            match_id=f"GS_{match_num:03d}",
            match_date=d,
            stage=MatchStage.GROUP,
            group="G",
            home_team=home,
            away_team=away,
            status=MatchStatus.SCHEDULED,
        ))
        match_num += 1

    # Group H
    group_h_dates = [
        (date(2026, 6, 15), "Group H1", "Group H2"),
        (date(2026, 6, 16), "Group H3", "Group H4"),
        (date(2026, 6, 20), "Group H1", "Group H3"),
        (date(2026, 6, 20), "Group H2", "Group H4"),
        (date(2026, 6, 24), "Group H4", "Group H1"),
        (date(2026, 6, 24), "Group H2", "Group H3"),
    ]
    for d, home, away in group_h_dates:
        matches.append(Match(
            match_id=f"GS_{match_num:03d}",
            match_date=d,
            stage=MatchStage.GROUP,
            group="H",
            home_team=home,
            away_team=away,
            status=MatchStatus.SCHEDULED,
        ))
        match_num += 1

    # Group I
    group_i_dates = [
        (date(2026, 6, 16), "Group I1", "Group I2"),
        (date(2026, 6, 16), "Group I3", "Group I4"),
        (date(2026, 6, 21), "Group I1", "Group I3"),
        (date(2026, 6, 21), "Group I2", "Group I4"),
        (date(2026, 6, 25), "Group I4", "Group I1"),
        (date(2026, 6, 25), "Group I2", "Group I3"),
    ]
    for d, home, away in group_i_dates:
        matches.append(Match(
            match_id=f"GS_{match_num:03d}",
            match_date=d,
            stage=MatchStage.GROUP,
            group="I",
            home_team=home,
            away_team=away,
            status=MatchStatus.SCHEDULED,
        ))
        match_num += 1

    # Group J
    group_j_dates = [
        (date(2026, 6, 17), "Group J1", "Group J2"),
        (date(2026, 6, 17), "Group J3", "Group J4"),
        (date(2026, 6, 22), "Group J1", "Group J3"),
        (date(2026, 6, 22), "Group J2", "Group J4"),
        (date(2026, 6, 25), "Group J4", "Group J1"),
        (date(2026, 6, 25), "Group J2", "Group J3"),
    ]
    for d, home, away in group_j_dates:
        matches.append(Match(
            match_id=f"GS_{match_num:03d}",
            match_date=d,
            stage=MatchStage.GROUP,
            group="J",
            home_team=home,
            away_team=away,
            status=MatchStatus.SCHEDULED,
        ))
        match_num += 1

    # Group K
    group_k_dates = [
        (date(2026, 6, 18), "Group K1", "Group K2"),
        (date(2026, 6, 18), "Group K3", "Group K4"),
        (date(2026, 6, 23), "Group K1", "Group K3"),
        (date(2026, 6, 23), "Group K2", "Group K4"),
        (date(2026, 6, 26), "Group K4", "Group K1"),
        (date(2026, 6, 26), "Group K2", "Group K3"),
    ]
    for d, home, away in group_k_dates:
        matches.append(Match(
            match_id=f"GS_{match_num:03d}",
            match_date=d,
            stage=MatchStage.GROUP,
            group="K",
            home_team=home,
            away_team=away,
            status=MatchStatus.SCHEDULED,
        ))
        match_num += 1

    # Group L
    group_l_dates = [
        (date(2026, 6, 18), "Group L1", "Group L2"),
        (date(2026, 6, 19), "Group L3", "Group L4"),
        (date(2026, 6, 23), "Group L1", "Group L3"),
        (date(2026, 6, 24), "Group L2", "Group L4"),
        (date(2026, 6, 26), "Group L4", "Group L1"),
        (date(2026, 6, 26), "Group L2", "Group L3"),
    ]
    for d, home, away in group_l_dates:
        matches.append(Match(
            match_id=f"GS_{match_num:03d}",
            match_date=d,
            stage=MatchStage.GROUP,
            group="L",
            home_team=home,
            away_team=away,
            status=MatchStatus.SCHEDULED,
        ))
        match_num += 1

    return matches


def get_knockout_matches() -> list[Match]:
    """
    Knockout stage matches (32 matches total).
    Round of 32: July 1-4
    Round of 16: July 5-8
    Quarter Finals: July 9-10
    Semi Finals: July 13-14
    Third Place: July 18
    Final: July 19
    """
    matches = []
    match_num = 73  # Continue from group stage

    # Round of 32 (16 matches)
    r32_dates = [
        date(2026, 7, 1), date(2026, 7, 1), date(2026, 7, 1), date(2026, 7, 1),
        date(2026, 7, 2), date(2026, 7, 2), date(2026, 7, 2), date(2026, 7, 2),
        date(2026, 7, 3), date(2026, 7, 3), date(2026, 7, 3), date(2026, 7, 3),
        date(2026, 7, 4), date(2026, 7, 4), date(2026, 7, 4), date(2026, 7, 4),
    ]
    for i, d in enumerate(r32_dates, start=1):
        matches.append(Match(
            match_id=f"R32_{i:02d}",
            match_date=d,
            stage=MatchStage.ROUND_OF_32,
            home_team=f"R32 Match {i} - TBD",
            away_team=f"R32 Match {i} - TBD",
            status=MatchStatus.SCHEDULED,
        ))
        match_num += 1

    # Round of 16 (8 matches)
    r16_dates = [
        date(2026, 7, 5), date(2026, 7, 5),
        date(2026, 7, 6), date(2026, 7, 6),
        date(2026, 7, 7), date(2026, 7, 7),
        date(2026, 7, 8), date(2026, 7, 8),
    ]
    for i, d in enumerate(r16_dates, start=1):
        matches.append(Match(
            match_id=f"R16_{i:02d}",
            match_date=d,
            stage=MatchStage.ROUND_OF_16,
            home_team=f"R16 Match {i} - TBD",
            away_team=f"R16 Match {i} - TBD",
            status=MatchStatus.SCHEDULED,
        ))
        match_num += 1

    # Quarter Finals (4 matches)
    qf_dates = [
        date(2026, 7, 9), date(2026, 7, 9),
        date(2026, 7, 10), date(2026, 7, 10),
    ]
    for i, d in enumerate(qf_dates, start=1):
        matches.append(Match(
            match_id=f"QF_{i:02d}",
            match_date=d,
            stage=MatchStage.QUARTER_FINAL,
            home_team=f"QF Match {i} - TBD",
            away_team=f"QF Match {i} - TBD",
            status=MatchStatus.SCHEDULED,
        ))
        match_num += 1

    # Semi Finals (2 matches)
    for i, d in enumerate([date(2026, 7, 13), date(2026, 7, 14)], start=1):
        matches.append(Match(
            match_id=f"SF_{i:02d}",
            match_date=d,
            stage=MatchStage.SEMI_FINAL,
            home_team=f"SF Match {i} - TBD",
            away_team=f"SF Match {i} - TBD",
            status=MatchStatus.SCHEDULED,
        ))
        match_num += 1

    # Third Place
    matches.append(Match(
        match_id="3RD_01",
        match_date=date(2026, 7, 18),
        stage=MatchStage.THIRD_PLACE,
        home_team="3rd Place - TBD",
        away_team="3rd Place - TBD",
        status=MatchStatus.SCHEDULED,
    ))

    # Final
    matches.append(Match(
        match_id="FINAL_01",
        match_date=date(2026, 7, 19),
        stage=MatchStage.FINAL,
        home_team="Final - TBD",
        away_team="Final - TBD",
        status=MatchStatus.SCHEDULED,
    ))

    return matches


def get_all_matches() -> list[Match]:
    """Get complete FIFA 2026 schedule."""
    return get_group_stage_matches() + get_knockout_matches()


# ==============================================================================
# DRAFT PICKS - Update these with your actual picks!
# ==============================================================================

def get_draft_picks() -> list[DraftPlayer]:
    """
    Actual draft picks for the Pakodis FIFA 2026 Fantasy Draft.
    4 players × 10 teams = 40 teams total.
    """
    return [
        DraftPlayer(
            name="Prateik",
            teams=[
                "France", "Belgium", "Netherlands", "Uruguay", "Morocco",
                "Canada", "Ivory Coast", "Iran", "Ghana", "South Africa",
            ],
        ),
        DraftPlayer(
            name="Rohit",
            teams=[
                "Spain", "Germany", "Switzerland", "USA", "Japan",
                "Egypt", "South Korea", "Algeria", "Scotland", "Tunisia",
            ],
        ),
        DraftPlayer(
            name="Anup",
            teams=[
                "Portugal", "Brazil", "Mexico", "Croatia", "Ecuador",
                "Austria", "Paraguay", "Bosnia & Herzegovina", "Saudi Arabia", "Congo",
            ],
        ),
        DraftPlayer(
            name="Abhinav",
            teams=[
                "Argentina", "England", "Colombia", "Norway", "Turkey",
                "Senegal", "Sweden", "Czechia", "Australia", "Qatar",
            ],
        ),
    ]


# ==============================================================================
# SEED FUNCTION
# ==============================================================================

def seed_spreadsheet():
    """Seed the Google Sheet with all initial data and apply formatting."""
    setup_logging()
    logger.info("=" * 60)
    logger.info("Seeding Google Sheet with FIFA 2026 data...")
    logger.info("=" * 60)

    # Validate config
    errors = Config.validate()
    if errors:
        for err in errors:
            logger.error(f"Config error: {err}")
        logger.error("Fix configuration before seeding. See .env.example")
        return

    client = SheetsClient()
    calculator = ScoringCalculator(DEFAULT_RULES)

    # Import formatting
    from src.sheets.formatting import (
        format_scoring_rules_tab,
        format_draft_picks_tab,
        format_schedule_tab,
        format_leaderboard_tab,
    )

    # 1. Write scoring rules
    logger.info("Writing scoring rules...")
    write_scoring_rules(client)

    # 2. Write draft picks
    logger.info("Writing draft picks...")
    players = get_draft_picks()
    write_draft_picks(client, players)

    # 3. Write match schedule
    logger.info("Writing match schedule (104 matches)...")
    matches = get_all_matches()
    write_schedule(client, matches)

    # 4. Write initial empty leaderboard
    logger.info("Writing initial leaderboard...")
    write_leaderboard(client, players, matches, calculator)

    # 5. Apply formatting to all tabs
    logger.info("Applying formatting...")
    try:
        scoring_ws = client.get_or_create_worksheet("Scoring Rules")
        format_scoring_rules_tab(scoring_ws)

        draft_ws = client.get_or_create_worksheet("Draft Picks")
        format_draft_picks_tab(draft_ws, len(players))

        schedule_ws = client.get_or_create_worksheet("Match Schedule")
        format_schedule_tab(schedule_ws, len(matches))

        leaderboard_ws = client.get_or_create_worksheet("Leaderboard")
        format_leaderboard_tab(leaderboard_ws, len(players))

        logger.info("✅ Formatting applied successfully")
    except Exception as e:
        logger.warning(f"Formatting failed (data is still written): {e}")

    # 6. Delete the default "Sheet1" if it exists
    try:
        default_sheet = client.spreadsheet.worksheet("Sheet1")
        client.spreadsheet.del_worksheet(default_sheet)
        logger.info("Deleted default 'Sheet1' tab")
    except Exception:
        pass  # Sheet1 doesn't exist, that's fine

    logger.info("=" * 60)
    logger.info(f"✅ Seeding complete! {len(matches)} matches, {len(players)} players")
    logger.info(f"   Spreadsheet: https://docs.google.com/spreadsheets/d/{Config.GOOGLE_SHEETS_ID}")
    logger.info("=" * 60)


if __name__ == "__main__":
    seed_spreadsheet()
