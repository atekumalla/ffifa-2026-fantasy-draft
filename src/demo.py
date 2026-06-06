"""Demo mode - run the dashboard with pre-filled fake data, no credentials needed.

Generates realistic match results for ~18 completed group stage matches,
schedules upcoming matches relative to today, and lets you "sync" to reveal
one more match result at a time.

Usage:
    python -m src.server --demo
"""

from __future__ import annotations

import logging
import random
from datetime import date, timedelta
from typing import Optional

from src.models.match import Match, MatchStage, MatchStatus
from src.models.player import DraftPlayer
from src.scoring.calculator import ScoringCalculator
from src.scoring.rules import DEFAULT_RULES

logger = logging.getLogger(__name__)

# --- DEMO CONFIGURATION ---

# How many matches are "already played" when demo starts
INITIAL_PLAYED_MATCHES = 18

# Rate limiter cooldown in demo (5 seconds instead of 10 min)
DEMO_COOLDOWN_SECONDS = 5

# Seed for reproducible results (but still interesting)
DEMO_SEED = 2026


# --- TEAMS ---

# All 48 teams: 40 drafted + 8 "neutral" (undrafted)
NEUTRAL_TEAMS = [
    "Serbia", "Denmark", "Chile", "Peru",
    "Nigeria", "Cameroon", "Jamaica", "New Zealand",
]


def get_demo_players() -> list[DraftPlayer]:
    """The 4 friends and their draft picks."""
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


def _get_all_teams() -> list[str]:
    """All 48 teams (40 drafted + 8 neutral)."""
    players = get_demo_players()
    teams = []
    for p in players:
        teams.extend(p.teams)
    teams.extend(NEUTRAL_TEAMS)
    return teams


# --- SCHEDULE GENERATION ---

def _generate_demo_schedule(today: date) -> list[Match]:
    """
    Generate a realistic group stage schedule + knockout placeholders.

    Distributes games so that:
      - ~18 matches are before today (already played)
      - Some matches are on today and next few days (imminent)
      - Remaining matches stretch into the future
    """
    rng = random.Random(DEMO_SEED)
    all_teams = _get_all_teams()
    rng.shuffle(all_teams)

    # Create 12 groups of 4
    groups = {}
    for i in range(12):
        letter = chr(ord("A") + i)
        groups[letter] = all_teams[i * 4: (i + 1) * 4]

    matches: list[Match] = []
    match_num = 1

    # Tournament starts 6 days before today
    tournament_start = today - timedelta(days=6)

    # Group stage: each group has 6 matches (round-robin of 4 teams)
    day_offset = 0
    for letter, teams in groups.items():
        pairings = [
            (teams[0], teams[1]),
            (teams[2], teams[3]),
            (teams[0], teams[2]),
            (teams[1], teams[3]),
            (teams[3], teams[0]),
            (teams[1], teams[2]),
        ]

        for game_idx, (home, away) in enumerate(pairings):
            game_day = day_offset + (game_idx // 2)
            match_date = tournament_start + timedelta(days=game_day)

            matches.append(Match(
                match_id=f"GS_{match_num:03d}",
                match_date=match_date,
                stage=MatchStage.GROUP,
                group=letter,
                home_team=home,
                away_team=away,
                status=MatchStatus.SCHEDULED,
            ))
            match_num += 1

        day_offset = (day_offset + 1) % 3

    # Sort matches by date
    matches.sort(key=lambda m: (m.match_date, m.match_id))

    # Knockout matches (placeholders - future dates)
    ko_start = tournament_start + timedelta(days=18)
    ko_stages = [
        (MatchStage.ROUND_OF_32, 16, ko_start),
        (MatchStage.ROUND_OF_16, 8, ko_start + timedelta(days=4)),
        (MatchStage.QUARTER_FINAL, 4, ko_start + timedelta(days=8)),
        (MatchStage.SEMI_FINAL, 2, ko_start + timedelta(days=11)),
        (MatchStage.THIRD_PLACE, 1, ko_start + timedelta(days=14)),
        (MatchStage.FINAL, 1, ko_start + timedelta(days=15)),
    ]

    for stage, count, base_date in ko_stages:
        for i in range(count):
            game_date = base_date + timedelta(days=i // 4)
            stage_label = stage.value.replace("_", " ").title()
            matches.append(Match(
                match_id=f"{stage.value.upper()}_{i+1:02d}",
                match_date=game_date,
                stage=stage,
                home_team=f"TBD ({stage_label} #{i+1})",
                away_team=f"TBD ({stage_label} #{i+1})",
                status=MatchStatus.SCHEDULED,
            ))

    return matches


def _generate_score(rng: random.Random) -> tuple[int, int]:
    """Generate a realistic football score."""
    score_weights = [
        (0, 0, 6), (1, 0, 12), (0, 1, 12), (1, 1, 10),
        (2, 0, 8), (0, 2, 8), (2, 1, 10), (1, 2, 10),
        (3, 0, 4), (0, 3, 4), (3, 1, 5), (1, 3, 5),
        (2, 2, 5), (3, 2, 3), (2, 3, 3), (4, 1, 2),
        (4, 0, 1), (5, 0, 1),
    ]
    choices = [(h, a) for h, a, w in score_weights for _ in range(w)]
    return rng.choice(choices)


# --- DEMO STATE ---

class DemoState:
    """
    Manages the demo's in-memory state.

    All matches exist in self.matches (visible on dashboard).
    The first N group stage matches are pre-scored. Sync reveals the next
    unplayed group match's result one at a time.
    """

    def __init__(self, today: Optional[date] = None):
        self.today = today or date.today()
        self.rng = random.Random(DEMO_SEED)
        self.players = get_demo_players()
        self.calculator = ScoringCalculator(DEFAULT_RULES)

        # Generate full schedule - ALL matches stay in self.matches
        self.matches = _generate_demo_schedule(self.today)
        self.matches.sort(key=lambda m: (m.match_date, m.match_id))

        # Pre-score the first N group stage matches (sorted by date)
        group_matches = [m for m in self.matches if m.stage == MatchStage.GROUP]
        group_matches.sort(key=lambda m: (m.match_date, m.match_id))
        scored_count = min(INITIAL_PLAYED_MATCHES, len(group_matches))
        for i in range(scored_count):
            h, a = _generate_score(self.rng)
            group_matches[i].home_goals = h
            group_matches[i].away_goals = a
            group_matches[i].status = MatchStatus.FINISHED

        # Track sync count and scoring order (for LIFO display)
        self.sync_count = 0
        self._last_sync_time: Optional[str] = None
        self._scored_order: list[str] = [m.match_id for m in group_matches[:scored_count]]

        played = sum(1 for m in self.matches if m.is_played)
        scheduled_group = sum(
            1 for m in self.matches
            if m.stage == MatchStage.GROUP and m.status == MatchStatus.SCHEDULED
        )
        logger.info(
            f"Demo initialized: {played} played, "
            f"{scheduled_group} group matches pending, "
            f"{len(self.matches)} total"
        )

    @property
    def last_sync(self) -> Optional[str]:
        return self._last_sync_time

    @property
    def _next_unplayed_group_matches(self) -> list[Match]:
        """Get group stage matches not yet played, sorted by date."""
        return sorted(
            [m for m in self.matches
             if m.stage == MatchStage.GROUP and m.status == MatchStatus.SCHEDULED],
            key=lambda m: (m.match_date, m.match_id),
        )

    def do_sync(self) -> dict:
        """
        Simulate a sync by scoring the next unplayed group match.
        Returns info about what happened.
        """
        from datetime import datetime

        self._last_sync_time = datetime.now().isoformat()
        self.sync_count += 1

        pending = self._next_unplayed_group_matches
        if not pending:
            return {
                "status": "ok",
                "message": "All group stage matches complete! Knockout stage awaits.",
                "match": None,
            }

        # Score the next match
        match = pending[0]
        h, a = _generate_score(self.rng)
        match.home_goals = h
        match.away_goals = a
        match.status = MatchStatus.FINISHED

        # Track scoring order (newest first for LIFO display)
        self._scored_order.append(match.match_id)

        remaining = len(pending) - 1
        msg = (
            f"New result: {match.home_team} {h} - {a} {match.away_team} "
            f"({remaining} group matches remaining)"
        )
        logger.info(f"Demo sync #{self.sync_count}: {msg}")

        return {
            "status": "ok",
            "message": msg,
            "match": {
                "home_team": match.home_team,
                "away_team": match.away_team,
                "home_goals": h,
                "away_goals": a,
            },
        }

    def get_leaderboard(self) -> list[dict]:
        """Calculate current leaderboard from played matches."""
        team_points: dict[str, float] = {}
        for match in self.matches:
            pts = self.calculator.calculate_match_points(match)
            for team, p in pts.items():
                team_points[team] = team_points.get(team, 0.0) + p

        leaderboard = []
        for player in self.players:
            total = sum(round(team_points.get(t, 0.0), 2) for t in player.teams)
            team_breakdown = [
                {"team": t, "points": round(team_points.get(t, 0.0), 2)}
                for t in sorted(
                    player.teams,
                    key=lambda t: team_points.get(t, 0.0),
                    reverse=True,
                )
            ]
            leaderboard.append({
                "name": player.name,
                "total_points": round(total, 2),
                "teams": team_breakdown,
            })

        leaderboard.sort(key=lambda x: x["total_points"], reverse=True)
        return leaderboard

    def get_worm_data(self) -> dict:
        """Calculate cumulative score worm data."""
        finished = [m for m in self.matches if m.is_played]
        if not finished:
            return {"dates": [], "players": {p.name: [] for p in self.players}}

        finished.sort(key=lambda m: m.match_date)
        all_dates = sorted(set(m.match_date for m in finished))

        player_cumulative: dict[str, list[float]] = {p.name: [] for p in self.players}
        running: dict[str, float] = {p.name: 0.0 for p in self.players}

        for d in all_dates:
            day_matches = [m for m in finished if m.match_date == d]
            for match in day_matches:
                pts = self.calculator.calculate_match_points(match)
                for player in self.players:
                    for team in player.teams:
                        if team in pts:
                            running[player.name] += pts[team]
            for player in self.players:
                player_cumulative[player.name].append(
                    round(running[player.name], 2)
                )

        return {
            "dates": [d.isoformat() for d in all_dates],
            "players": player_cumulative,
        }

    def get_recent_matches(self, limit: int = 10) -> list[dict]:
        """Get most recently scored matches (LIFO — newest sync first)."""
        finished = [m for m in self.matches if m.is_played]

        # Sort by scored order (LIFO) — most recently scored first
        order_map = {mid: idx for idx, mid in enumerate(self._scored_order)}
        finished.sort(key=lambda m: order_map.get(m.match_id, 0), reverse=True)

        # Build per-player points mapping
        player_teams: dict[str, list[str]] = {p.name: p.teams for p in self.players}

        results = []
        for m in finished[:limit]:
            pts = self.calculator.calculate_match_points(m)
            # Calculate per-player points for this match
            player_points = {}
            for player in self.players:
                pp = 0.0
                for team in player.teams:
                    if team in pts:
                        pp += pts[team]
                player_points[player.name] = round(pp, 2)

            results.append({
                "date": m.match_date.isoformat(),
                "home_team": m.home_team,
                "away_team": m.away_team,
                "home_goals": m.home_goals,
                "away_goals": m.away_goals,
                "stage": m.stage.value,
                "group": m.group,
                "home_points": pts.get(m.home_team, 0),
                "away_points": pts.get(m.away_team, 0),
                "player_points": player_points,
            })
        return results

    def get_upcoming_matches(self, limit: int = 6) -> list[dict]:
        """Get next scheduled GROUP matches (skip TBD knockout)."""
        upcoming = [
            m for m in self.matches
            if m.status == MatchStatus.SCHEDULED and m.stage == MatchStage.GROUP
        ]
        upcoming.sort(key=lambda m: m.match_date)
        return [
            {
                "date": m.match_date.isoformat(),
                "home_team": m.home_team,
                "away_team": m.away_team,
                "stage": m.stage.value,
                "group": m.group,
            }
            for m in upcoming[:limit]
        ]

    def get_full_status(self) -> dict:
        """Build the complete API response for /api/status."""
        played = sum(1 for m in self.matches if m.is_played)
        pending_group = len(self._next_unplayed_group_matches)
        return {
            "leaderboard": self.get_leaderboard(),
            "recent_matches": self.get_recent_matches(),
            "upcoming_matches": self.get_upcoming_matches(),
            "worm_data": self.get_worm_data(),
            "last_sync": self.last_sync,
            "total_matches": len(self.matches),
            "matches_played": played,
            "spreadsheet_url": "#demo-mode",
            "sync_available": True,
            "sync_wait_seconds": 0,
            "validate_available": False,
            "validate_wait_seconds": 0,
            "demo_mode": True,
            "pending_matches": pending_group,
            "player_names": [p.name for p in self.players],
        }
