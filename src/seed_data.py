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

# NOTE: Updated with official FIFA World Cup 2026 draw results (December 5, 2025)
# Groups A-L with actual qualified teams

def get_group_stage_matches() -> list[Match]:
    """
    FIFA 2026 Group Stage matches.
    48 teams in 12 groups (A-L), 3 matches per team = 72 group matches.
    Dates: June 11 - June 27, 2026.
    
    Based on the official FIFA World Cup 2026 draw.
    """
    matches = []
    match_num = 1

    # Group A: Mexico (host), South Africa, South Korea, Czech Republic
    group_a_dates = [
        (date(2026, 6, 11), "Mexico", "South Africa"),
        (date(2026, 6, 11), "South Korea", "Czech Republic"),
        (date(2026, 6, 18), "Mexico", "South Korea"),
        (date(2026, 6, 18), "South Africa", "Czech Republic"),
        (date(2026, 6, 24), "Czech Republic", "Mexico"),
        (date(2026, 6, 24), "South Africa", "South Korea"),
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

    # Group B: Canada (host), Bosnia and Herzegovina, Switzerland, Qatar
    group_b_dates = [
        (date(2026, 6, 12), "Canada", "Bosnia and Herzegovina"),
        (date(2026, 6, 13), "Switzerland", "Qatar"),
        (date(2026, 6, 18), "Switzerland", "Bosnia and Herzegovina"),
        (date(2026, 6, 18), "Canada", "Qatar"),
        (date(2026, 6, 24), "Switzerland", "Canada"),
        (date(2026, 6, 24), "Bosnia and Herzegovina", "Qatar"),
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

    # Group C: Brazil, Morocco, Scotland, Haiti
    group_c_dates = [
        (date(2026, 6, 13), "Brazil", "Morocco"),
        (date(2026, 6, 13), "Scotland", "Haiti"),
        (date(2026, 6, 19), "Scotland", "Morocco"),
        (date(2026, 6, 19), "Brazil", "Haiti"),
        (date(2026, 6, 24), "Scotland", "Brazil"),
        (date(2026, 6, 24), "Morocco", "Haiti"),
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

    # Group D: USA (host), Paraguay, Turkey, Australia
    group_d_dates = [
        (date(2026, 6, 12), "USA", "Paraguay"),
        (date(2026, 6, 13), "Turkey", "Australia"),
        (date(2026, 6, 19), "USA", "Turkey"),
        (date(2026, 6, 19), "Paraguay", "Australia"),
        (date(2026, 6, 25), "Turkey", "USA"),
        (date(2026, 6, 25), "Paraguay", "Australia"),
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

    # Group E: Germany, Curaçao, Ecuador, Ivory Coast
    group_e_dates = [
        (date(2026, 6, 14), "Germany", "Curaçao"),
        (date(2026, 6, 14), "Ecuador", "Ivory Coast"),
        (date(2026, 6, 20), "Germany", "Ecuador"),
        (date(2026, 6, 20), "Curaçao", "Ivory Coast"),
        (date(2026, 6, 25), "Curaçao", "Ecuador"),
        (date(2026, 6, 25), "Ivory Coast", "Germany"),
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

    # Group F: Netherlands, Japan, Sweden, Tunisia
    group_f_dates = [
        (date(2026, 6, 14), "Netherlands", "Japan"),
        (date(2026, 6, 14), "Sweden", "Tunisia"),
        (date(2026, 6, 20), "Netherlands", "Sweden"),
        (date(2026, 6, 20), "Japan", "Tunisia"),
        (date(2026, 6, 25), "Japan", "Sweden"),
        (date(2026, 6, 25), "Tunisia", "Netherlands"),
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

    # Group G: Belgium, Egypt, Iran, New Zealand
    group_g_dates = [
        (date(2026, 6, 15), "Belgium", "Egypt"),
        (date(2026, 6, 15), "Iran", "New Zealand"),
        (date(2026, 6, 21), "Belgium", "Iran"),
        (date(2026, 6, 21), "Egypt", "New Zealand"),
        (date(2026, 6, 26), "Egypt", "Iran"),
        (date(2026, 6, 26), "New Zealand", "Belgium"),
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

    # Group H: Spain, Cape Verde, Saudi Arabia, Uruguay
    group_h_dates = [
        (date(2026, 6, 15), "Spain", "Cape Verde"),
        (date(2026, 6, 15), "Saudi Arabia", "Uruguay"),
        (date(2026, 6, 21), "Spain", "Saudi Arabia"),
        (date(2026, 6, 21), "Uruguay", "Cape Verde"),
        (date(2026, 6, 26), "Cape Verde", "Saudi Arabia"),
        (date(2026, 6, 26), "Uruguay", "Spain"),
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

    # Group I: France, Senegal, Iraq, Norway
    group_i_dates = [
        (date(2026, 6, 16), "France", "Senegal"),
        (date(2026, 6, 16), "Iraq", "Norway"),
        (date(2026, 6, 22), "France", "Iraq"),
        (date(2026, 6, 22), "Norway", "Senegal"),
        (date(2026, 6, 26), "Norway", "France"),
        (date(2026, 6, 26), "Senegal", "Iraq"),
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

    # Group J: Argentina, Algeria, Austria, Jordan
    group_j_dates = [
        (date(2026, 6, 16), "Argentina", "Algeria"),
        (date(2026, 6, 16), "Austria", "Jordan"),
        (date(2026, 6, 22), "Argentina", "Austria"),
        (date(2026, 6, 22), "Jordan", "Algeria"),
        (date(2026, 6, 27), "Algeria", "Austria"),
        (date(2026, 6, 27), "Jordan", "Argentina"),
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

    # Group K: Portugal, DR Congo, Uzbekistan, Colombia
    group_k_dates = [
        (date(2026, 6, 17), "Portugal", "DR Congo"),
        (date(2026, 6, 17), "Uzbekistan", "Colombia"),
        (date(2026, 6, 23), "Portugal", "Uzbekistan"),
        (date(2026, 6, 23), "Colombia", "DR Congo"),
        (date(2026, 6, 27), "Colombia", "Portugal"),
        (date(2026, 6, 27), "DR Congo", "Uzbekistan"),
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

    # Group L: England, Croatia, Ghana, Panama
    group_l_dates = [
        (date(2026, 6, 17), "England", "Croatia"),
        (date(2026, 6, 17), "Ghana", "Panama"),
        (date(2026, 6, 23), "England", "Ghana"),
        (date(2026, 6, 23), "Panama", "Croatia"),
        (date(2026, 6, 27), "Panama", "England"),
        (date(2026, 6, 27), "Croatia", "Ghana"),
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
