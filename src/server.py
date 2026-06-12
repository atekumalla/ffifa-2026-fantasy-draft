"""FastAPI web server — serves the dashboard UI and exposes API endpoints.

Endpoints:
  GET  /                  → Dashboard HTML
  GET  /api/status        → Current leaderboard, last sync time, matches
  POST /api/sync          → Trigger score sync (rate limited: 10 min cooldown)
  POST /api/validate      → Trigger validation (rate limited: 10 min cooldown)
  GET  /api/share-text    → Get formatted share text for WhatsApp/clipboard

Demo mode (--demo flag):
  Runs entirely in-memory with pre-generated match data. No credentials needed.
  Sync adds one more match result. Validate is disabled.
"""

from __future__ import annotations

import logging
import os
from contextlib import asynccontextmanager
from pathlib import Path

from fastapi import FastAPI, HTTPException
from fastapi.responses import HTMLResponse, JSONResponse
from fastapi.staticfiles import StaticFiles

from src.config import Config
from src.models.match import Match, MatchStatus
from src.models.player import DraftPlayer
from src.scoring.calculator import ScoringCalculator
from src.scoring.rules import DEFAULT_RULES
from src.utils.logger import setup_logging
from src.utils.rate_limiter import rate_limiter

logger = logging.getLogger(__name__)

# Module-level state
_app_state: dict = {}
_demo_mode: bool = False


def _is_demo_mode() -> bool:
    """Check if demo mode is enabled via flag or env var."""
    return _demo_mode or os.environ.get("FIFA_DEMO_MODE", "").lower() in ("1", "true", "yes")


@asynccontextmanager
async def lifespan(app: FastAPI):
    """Startup/shutdown lifecycle — branches on demo vs production mode."""
    setup_logging()

    if _is_demo_mode():
        from src.config import Config
        from src.demo import DemoState, DEMO_COOLDOWN_SECONDS, initialize_demo_sheet
        from src.data_sources.football_api_stub import FootballDataAPIStub
        from src.data_sources.llm_fallback import LLMFallback

        logger.info("=" * 60)
        logger.info("🎮 DEMO MODE")
        
        # Check if we should use Google Sheets for demo
        demo_sheet_id = Config.DEMO_GOOGLE_SHEETS_ID or Config.GOOGLE_SHEETS_ID
        use_sheets = bool(demo_sheet_id) and (
            Config.has_credentials_json() or 
            Path(Config.GOOGLE_SHEETS_CREDENTIALS_FILE).exists()
        )
        
        if use_sheets:
            logger.info("   ✅ Using REAL Google Sheets with pre-seeded data")
            logger.info("   ✅ Using STUBBED Football API (no real API calls)")
            logger.info(f"   ✅ Using {'REAL' if Config.OPENAI_API_KEY else 'NO'} OpenAI API for validation")
            logger.info(f"   📊 Sheet ID: {demo_sheet_id}")
        else:
            logger.info("   ⚠️  In-memory only (no Google Sheets credentials)")
            logger.info("   Pre-filled with 18 match results. Hit Sync to reveal more.")
        logger.info("=" * 60)

        # Reduce rate limiter cooldown for demo (5 seconds)
        rate_limiter.cooldown_seconds = DEMO_COOLDOWN_SECONDS

        _app_state["demo_mode"] = True
        _app_state["use_sheets"] = use_sheets
        
        if use_sheets:
            # Set up with real Google Sheets
            from src.sheets.client import SheetsClient
            from src.sheets.players import read_draft_picks
            from src.sheets.schedule import read_schedule
            
            # Override sheet ID if demo-specific one is provided
            if Config.DEMO_GOOGLE_SHEETS_ID:
                original_sheet_id = Config.GOOGLE_SHEETS_ID
                Config.GOOGLE_SHEETS_ID = Config.DEMO_GOOGLE_SHEETS_ID
                logger.info(f"Using demo-specific sheet: {Config.DEMO_GOOGLE_SHEETS_ID}")
            
            sheets_client = SheetsClient()
            
            # Initialize sheet with demo data
            demo = initialize_demo_sheet(sheets_client)
            
            # Read back from sheets to verify
            players = read_draft_picks(sheets_client)
            matches = read_schedule(sheets_client)
            
            _app_state.update({
                "demo_state": demo,
                "sheets_client": sheets_client,
                "players": players,
                "matches": matches,
                "calculator": demo.calculator,
                "football_api": FootballDataAPIStub(),  # Stubbed!
                "llm_fallback": LLMFallback() if Config.OPENAI_API_KEY else None,
            })
            
            logger.info(f"✅ Loaded {len(players)} players, {len(matches)} matches from sheet")
        else:
            # In-memory only demo (original behavior)
            demo = DemoState()
            _app_state.update({
                "demo_state": demo,
                "players": demo.players,
                "matches": demo.matches,
                "calculator": demo.calculator,
                "sheets_client": None,
            })

        logger.info("Demo server ready! Open http://localhost:8000")
        yield
        logger.info("Demo server stopped.")
    else:
        from src.config import Config
        from src.data_sources.football_api import FootballDataAPI
        from src.data_sources.llm_fallback import LLMFallback
        from src.sheets.client import SheetsClient
        from src.sheets.players import read_draft_picks
        from src.sheets.schedule import read_schedule
        from src.sync.scheduler import SyncScheduler
        from src.sync.state_manager import StateManager

        logger.info("Starting FIFA 2026 Fantasy Draft server (production)...")

        # Set rate limiter cooldown from config
        rate_limiter.cooldown_seconds = Config.SYNC_COOLDOWN_SECONDS
        logger.info(f"Rate limiter: {Config.SYNC_COOLDOWN_SECONDS}s cooldown between manual syncs")

        state = {
            "demo_mode": False,
            "sheets_client": SheetsClient(),
            "state_manager": StateManager(),
            "calculator": ScoringCalculator(DEFAULT_RULES),
            "football_api": FootballDataAPI(),
            "llm_fallback": LLMFallback(),
            "players": [],
            "matches": [],
        }

        try:
            state["players"] = read_draft_picks(state["sheets_client"])
            state["matches"] = read_schedule(state["sheets_client"])
            logger.info(
                f"Loaded {len(state['players'])} players, {len(state['matches'])} matches"
            )
        except Exception as e:
            logger.error(f"Failed to load from sheets: {e}")

        def _sync():
            _do_sync(state)

        state["scheduler"] = SyncScheduler(sync_fn=_sync)
        state["scheduler"].start()

        _app_state.update(state)
        logger.info("Server ready!")

        yield

        state["scheduler"].stop()
        state["state_manager"].save()
        logger.info("Server stopped.")


app = FastAPI(title="FIFA 2026 Fantasy Draft", lifespan=lifespan)

# Serve static files (UI)
_static_dir = Path(__file__).resolve().parent.parent / "static"
if _static_dir.exists():
    app.mount("/static", StaticFiles(directory=str(_static_dir)), name="static")


# ─── API ENDPOINTS ───────────────────────────────────────────────────────────


@app.get("/", response_class=HTMLResponse)
async def serve_dashboard():
    """Serve the main dashboard HTML."""
    html_path = _static_dir / "index.html"
    if not html_path.exists():
        return HTMLResponse("<h1>Dashboard not found. Run seed first.</h1>", status_code=404)
    return HTMLResponse(html_path.read_text())


@app.get("/api/status")
async def get_status():
    """Get current state: leaderboard, matches, last sync time."""
    # Demo mode: use DemoState directly
    if _app_state.get("demo_mode"):
        from src.config import Config
        
        demo = _app_state["demo_state"]
        status = demo.get_full_status()
        
        # Update validation availability based on configuration
        if _app_state.get("use_sheets") and Config.OPENAI_API_KEY:
            sync_ready, sync_wait = rate_limiter.can_call("sync"), rate_limiter.seconds_until_ready("sync")
            validate_ready, validate_wait = rate_limiter.can_call("validate"), rate_limiter.seconds_until_ready("validate")
            
            status.update({
                "sync_available": sync_ready,
                "sync_wait_seconds": sync_wait,
                "validate_available": validate_ready,
                "validate_wait_seconds": validate_wait,
                "spreadsheet_url": f"https://docs.google.com/spreadsheets/d/{Config.DEMO_GOOGLE_SHEETS_ID or Config.GOOGLE_SHEETS_ID}",
            })
        
        return status

    # Production mode
    from src.config import Config

    players = _app_state.get("players", [])
    matches = _app_state.get("matches", [])
    calculator = _app_state.get("calculator")
    state_mgr = _app_state.get("state_manager")

    # Calculate leaderboard
    leaderboard = []
    team_points: dict[str, float] = {}
    for match in matches:
        pts = calculator.calculate_match_points(match)
        for team, p in pts.items():
            team_points[team] = team_points.get(team, 0.0) + p

    for player in players:
        total = sum(round(team_points.get(t, 0.0), 2) for t in player.teams)
        team_breakdown = [
            {"team": t, "points": round(team_points.get(t, 0.0), 2)}
            for t in player.teams
        ]
        leaderboard.append({
            "name": player.name,
            "total_points": round(total, 2),
            "teams": team_breakdown,
        })

    leaderboard.sort(key=lambda x: x["total_points"], reverse=True)

    # Recent finished/live matches (last 10)
    finished = [m for m in matches if m.is_live_or_finished]
    finished.sort(key=lambda m: m.match_date, reverse=True)
    
    # Build a mapping of team -> player name
    team_to_player = {}
    for player in players:
        for team in player.teams:
            team_to_player[team] = player.name
    
    recent_matches = []
    for m in finished[:10]:
        pts = calculator.calculate_match_points(m)
        recent_matches.append({
            "date": m.match_date.isoformat(),
            "home_team": m.home_team,
            "away_team": m.away_team,
            "home_goals": m.home_goals,
            "away_goals": m.away_goals,
            "status": m.status.value,  # Include status for live indicator
            "stage": m.stage.value,
            "home_points": pts.get(m.home_team, 0),
            "away_points": pts.get(m.away_team, 0),
            "home_player": team_to_player.get(m.home_team),
            "away_player": team_to_player.get(m.away_team),
        })

    # Upcoming matches (next 5)
    upcoming = [m for m in matches if m.status == MatchStatus.SCHEDULED]
    upcoming.sort(key=lambda m: m.match_date)
    
    upcoming_matches = [
        {
            "date": m.match_date.isoformat(),
            "home_team": m.home_team,
            "away_team": m.away_team,
            "stage": m.stage.value,
            "group": m.group,
            "home_player": team_to_player.get(m.home_team),
            "away_player": team_to_player.get(m.away_team),
        }
        for m in upcoming[:5]
    ]

    # Score worm data (cumulative points by date)
    worm_data = _calculate_worm_data(players, matches, calculator)

    # Sync/validate cooldown status
    sync_ready, sync_wait = rate_limiter.can_call("sync"), rate_limiter.seconds_until_ready("sync")
    validate_ready, validate_wait = rate_limiter.can_call("validate"), rate_limiter.seconds_until_ready("validate")

    return {
        "leaderboard": leaderboard,
        "recent_matches": recent_matches,
        "upcoming_matches": upcoming_matches,
        "worm_data": worm_data,
        "last_sync": state_mgr.last_sync if state_mgr else None,
        "total_matches": len(matches),
        "matches_played": len(finished),
        "spreadsheet_url": f"https://docs.google.com/spreadsheets/d/{Config.GOOGLE_SHEETS_ID}",
        "sync_available": sync_ready,
        "sync_wait_seconds": sync_wait,
        "validate_available": validate_ready,
        "validate_wait_seconds": validate_wait,
        "demo_mode": False,
    }


@app.post("/api/sync")
async def trigger_sync():
    """Trigger a score sync. Rate limited."""
    # Demo mode: reveal next match
    if _app_state.get("demo_mode"):
        allowed, wait_seconds = rate_limiter.try_call("sync")
        if not allowed:
            raise HTTPException(
                status_code=429,
                detail=f"Rate limited. Try again in {wait_seconds} seconds.",
            )
        
        demo = _app_state["demo_state"]
        
        # If using sheets, sync to sheet as well
        if _app_state.get("use_sheets"):
            from src.demo import sync_demo_to_sheet
            sheets_client = _app_state["sheets_client"]
            result = sync_demo_to_sheet(demo, sheets_client)
            
            # Re-read from sheets to keep state synchronized
            from src.sheets.players import read_draft_picks
            from src.sheets.schedule import read_schedule
            _app_state["players"] = read_draft_picks(sheets_client)
            _app_state["matches"] = read_schedule(sheets_client)
        else:
            # In-memory only
            result = demo.do_sync()
            _app_state["matches"] = demo.matches
        
        return result

    # Production mode
    allowed, wait_seconds = rate_limiter.try_call("sync")
    if not allowed:
        raise HTTPException(
            status_code=429,
            detail=f"Rate limited. Try again in {wait_seconds} seconds.",
        )

    try:
        _do_sync(_app_state)
        return {"status": "ok", "message": "Sync completed successfully"}
    except Exception as e:
        logger.error(f"Sync failed: {e}", exc_info=True)
        raise HTTPException(status_code=500, detail=f"Sync failed: {str(e)}")


@app.post("/api/validate")
async def trigger_validate():
    """Trigger validation. Rate limited. Works in demo mode if OpenAI is configured."""
    # Check rate limit first
    allowed, wait_seconds = rate_limiter.try_call("validate")
    if not allowed:
        raise HTTPException(
            status_code=429,
            detail=f"Rate limited. Try again in {wait_seconds} seconds.",
        )
    
    # Demo mode with sheets: run real validation if OpenAI is available
    if _app_state.get("demo_mode"):
        from src.config import Config
        
        if not _app_state.get("use_sheets"):
            # In-memory demo: skip validation
            return {
                "status": "ok",
                "healthy": True,
                "summary": "Demo mode (in-memory) — validation skipped",
                "issues": [],
                "checks_passed": 5,
                "checks_failed": 0,
            }
        
        # Demo with sheets: run validation if OpenAI is configured
        if not Config.OPENAI_API_KEY:
            return {
                "status": "ok",
                "healthy": True,
                "summary": "Demo mode — OpenAI API not configured, structural checks only",
                "issues": [],
                "checks_passed": 5,
                "checks_failed": 0,
            }
        
        # Run real validation in demo mode!
        from src.validation import run_full_validation
        
        try:
            matches = _app_state.get("matches", [])
            players = _app_state.get("players", [])
            
            logger.info("🎮 Demo mode: Running REAL validation with OpenAI...")
            report = run_full_validation(
                matches, 
                players, 
                use_llm=True
            )
            
            return {
                "status": "ok",
                "healthy": report.is_healthy,
                "summary": f"Demo validation: {report.summary()}",
                "issues": [
                    {"severity": i.severity, "message": i.message, "details": i.details}
                    for i in report.issues
                ],
                "checks_passed": report.checks_passed,
                "checks_failed": report.checks_failed,
            }
        except Exception as e:
            logger.error(f"Demo validation failed: {e}", exc_info=True)
            raise HTTPException(status_code=500, detail=f"Validation failed: {str(e)}")

    # Production mode
    from src.config import Config
    from src.validation import run_full_validation

    try:
        matches = _app_state.get("matches", [])
        players = _app_state.get("players", [])
        report = run_full_validation(matches, players, use_llm=bool(Config.OPENAI_API_KEY))
        return {
            "status": "ok",
            "healthy": report.is_healthy,
            "summary": report.summary(),
            "issues": [
                {"severity": i.severity, "message": i.message, "details": i.details}
                for i in report.issues
            ],
            "checks_passed": report.checks_passed,
            "checks_failed": report.checks_failed,
        }
    except Exception as e:
        logger.error(f"Validation failed: {e}", exc_info=True)
        raise HTTPException(status_code=500, detail=f"Validation failed: {str(e)}")


@app.get("/api/share-text")
async def get_share_text():
    """Generate a formatted share text for WhatsApp/clipboard."""
    players = _app_state.get("players", [])
    matches = _app_state.get("matches", [])
    calculator = _app_state.get("calculator")

    # Calculate totals
    team_points: dict[str, float] = {}
    for match in matches:
        pts = calculator.calculate_match_points(match)
        for team, p in pts.items():
            team_points[team] = team_points.get(team, 0.0) + p

    standings = []
    for player in players:
        total = sum(round(team_points.get(t, 0.0), 2) for t in player.teams)
        standings.append((player.name, round(total, 2)))
    standings.sort(key=lambda x: x[1], reverse=True)

    # Count matches played
    played = sum(1 for m in matches if m.is_played)

    # Build share text with emojis
    rank_emojis = ["🥇", "🥈", "🥉", "4️⃣"]
    lines = [
        "⚽🏆 *FIFA 2026 Fantasy Draft* 🏆⚽",
        f"📊 Standings after {played} matches:",
        "",
    ]
    for i, (name, pts) in enumerate(standings):
        emoji = rank_emojis[i] if i < len(rank_emojis) else f"{i+1}."
        bar = "█" * max(1, int(pts / 3))  # Visual bar
        lines.append(f"{emoji} *{name}*: {pts} pts")

    # Add gap info
    if len(standings) >= 2:
        gap = standings[0][1] - standings[1][1]
        lines.append("")
        lines.append(f"📈 Gap: {standings[0][0]} leads by {gap} pts")

    # Add dashboard link if configured
    if Config.DASHBOARD_URL:
        lines.append("")
        lines.append(f"🔗 _Updated live at {Config.DASHBOARD_URL}_")

    share_text = "\n".join(lines)
    return {"text": share_text}


# ─── HELPERS ─────────────────────────────────────────────────────────────────


def _calculate_worm_data(
    players: list[DraftPlayer],
    matches: list[Match],
    calculator: ScoringCalculator,
) -> dict:
    """Calculate cumulative points by date for the score worm chart."""
    from datetime import date as dt_date, timedelta

    finished = [m for m in matches if m.is_played]
    if not finished:
        return {"dates": [], "players": {p.name: [] for p in players}}

    finished.sort(key=lambda m: m.match_date)

    # Get all unique match dates
    all_dates = sorted(set(m.match_date for m in finished))
    
    # Add a starting point (one day before first match) where everyone has 0 points
    if all_dates:
        start_date = all_dates[0] - timedelta(days=1)
        all_dates = [start_date] + all_dates

    # Calculate cumulative points per player per date
    player_cumulative: dict[str, list[float]] = {p.name: [] for p in players}
    running_totals: dict[str, float] = {p.name: 0.0 for p in players}

    for d in all_dates:
        day_matches = [m for m in finished if m.match_date == d]
        for match in day_matches:
            pts = calculator.calculate_match_points(match)
            for player in players:
                for team in player.teams:
                    if team in pts:
                        running_totals[player.name] += pts[team]

        for player in players:
            player_cumulative[player.name].append(round(running_totals[player.name], 2))

    return {
        "dates": [d.isoformat() for d in all_dates],
        "players": player_cumulative,
    }


def _do_sync(state: dict):
    """Execute a full sync cycle (production mode only)."""
    from src.sheets.schedule import write_schedule
    from src.sheets.scores import write_leaderboard
    from src.sync.recovery import get_matches_needing_update, reconcile_matches

    matches = state["matches"]
    state_mgr = state["state_manager"]
    football_api = state["football_api"]
    llm_fallback = state["llm_fallback"]
    sheets_client = state["sheets_client"]
    players = state["players"]
    calculator = state["calculator"]

    # Determine what needs updating
    matches_to_update = get_matches_needing_update(matches, state_mgr)
    if not matches_to_update:
        logger.info("No matches need updating")
        state_mgr.mark_synced()
        return

    # Try API first
    updated = []
    try:
        updated = football_api.fetch_live_and_finished_matches()
        logger.info(f"API returned {len(updated)} live/finished matches")
    except Exception as e:
        logger.warning(f"Football API failed: {e}")

    # Fallback to LLM
    if not updated:
        try:
            dates = set(m.match_date for m in matches_to_update)
            for match_date in sorted(dates):
                day_matches = [m for m in matches_to_update if m.match_date == match_date]
                results = llm_fallback.fetch_match_results(match_date, known_matches=day_matches)
                updated.extend(results)
        except Exception as e:
            logger.warning(f"LLM fallback failed: {e}")

    # Reconcile and update
    if updated:
        state["matches"] = reconcile_matches(matches, updated)

        # Write to sheets
        try:
            write_schedule(sheets_client, state["matches"])
            write_leaderboard(sheets_client, players, state["matches"], calculator)
        except Exception as e:
            logger.error(f"Failed to write to sheets: {e}")

        # Mark scored
        for m in updated:
            if m.status == MatchStatus.FINISHED:
                state_mgr.mark_match_scored(m.match_id)

    state_mgr.mark_synced()
    logger.info("Sync completed")


def start():
    """Entry point for starting the web server (used by pyproject.toml script)."""
    import argparse
    import uvicorn

    global _demo_mode

    parser = argparse.ArgumentParser(description="FIFA 2026 Fantasy Draft Server")
    parser.add_argument(
        "--demo", action="store_true",
        help="Run in demo mode with pre-filled data (no credentials needed)"
    )
    parser.add_argument(
        "--port", type=int, default=None,
        help="Port to listen on (default: 8000 or $PORT env var)"
    )
    args = parser.parse_args()

    if args.demo:
        _demo_mode = True
        # Set env var so uvicorn's re-import of this module picks it up
        os.environ["FIFA_DEMO_MODE"] = "1"

    if args.port:
        port = args.port
    elif os.environ.get("PORT"):
        port = int(os.environ["PORT"])
    else:
        port = 8000

    uvicorn.run("src.server:app", host="0.0.0.0", port=port, reload=False)


if __name__ == "__main__":
    start()
