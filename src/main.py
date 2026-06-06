"""FIFA 2026 Fantasy Draft — Main Application Entry Point.

On startup:
  1. Validate configuration
  2. Load state from disk (crash recovery)
  3. Read current data from Google Sheets into memory
  4. Determine if any matches need score updates
  5. Start the scheduler for automatic daily updates
  6. Expose a simple way to trigger manual updates

The app is designed to be resilient:
  - State is persisted after every sync
  - Google Sheet is the source of truth (readable standalone)
  - If the app crashes and restarts, it picks up where it left off
"""

from __future__ import annotations

import logging
import signal
import sys
from datetime import date

from src.config import Config
from src.data_sources.football_api import FootballDataAPI
from src.data_sources.llm_fallback import LLMFallback
from src.models.match import Match, MatchStatus
from src.models.player import DraftPlayer
from src.scoring.calculator import ScoringCalculator
from src.scoring.rules import DEFAULT_RULES
from src.sheets.client import SheetsClient
from src.sheets.players import read_draft_picks
from src.sheets.schedule import read_schedule, write_schedule, update_match_result
from src.sheets.scores import write_leaderboard
from src.sheets.scoring_rules import write_scoring_rules
from src.sync.recovery import get_matches_needing_update, reconcile_matches
from src.sync.scheduler import SyncScheduler
from src.sync.state_manager import StateManager
from src.validation import run_full_validation
from src.utils.logger import setup_logging

logger = logging.getLogger(__name__)


class FantasyDraftApp:
    """Main application orchestrator."""

    def __init__(self):
        self.sheets_client = SheetsClient()
        self.state_manager = StateManager()
        self.calculator = ScoringCalculator(DEFAULT_RULES)
        self.football_api = FootballDataAPI()
        self.llm_fallback = LLMFallback()
        self.scheduler = SyncScheduler(sync_fn=self.sync_scores)

        # In-memory state (loaded from sheet on startup)
        self.players: list[DraftPlayer] = []
        self.matches: list[Match] = []

    def start(self):
        """Initialize and start the application."""
        # Validate config
        errors = Config.validate()
        if errors:
            for err in errors:
                logger.warning(f"Config issue: {err}")
            # Non-fatal — some features may not work

        # Load data from sheets into memory
        self._load_from_sheets()

        # Check for any matches that need updating
        self.sync_scores()

        # Start the scheduler
        self.scheduler.start()

        logger.info("=" * 60)
        logger.info("FIFA 2026 Fantasy Draft app started successfully!")
        logger.info(f"  Players: {len(self.players)}")
        logger.info(f"  Matches loaded: {len(self.matches)}")
        logger.info(f"  Last sync: {self.state_manager.last_sync or 'never'}")
        logger.info(f"  Next auto-sync: {self.scheduler.next_run_time}")
        logger.info("=" * 60)

    def _load_from_sheets(self):
        """Load all data from Google Sheets into memory."""
        logger.info("Loading data from Google Sheets...")

        try:
            self.players = read_draft_picks(self.sheets_client)
            self.matches = read_schedule(self.sheets_client)
            logger.info(
                f"Loaded {len(self.players)} players, {len(self.matches)} matches"
            )
        except Exception as e:
            logger.error(f"Failed to load from sheets: {e}")
            # If sheets fail, we can still start with empty state

    def sync_scores(self):
        """
        Main sync logic — fetch new scores and update everything.

        This is called:
          - On startup (recovery)
          - By the scheduler (daily auto-sync)
          - Manually via trigger_sync()
        """
        logger.info("Starting score sync...")

        try:
            # 1. Determine which matches need updating
            matches_to_update = get_matches_needing_update(
                self.matches, self.state_manager
            )

            if not matches_to_update:
                logger.info("No matches need updating")
                self.state_manager.mark_synced()
                return

            logger.info(f"Found {len(matches_to_update)} matches to update")

            # 2. Try to fetch from football API first
            updated_matches = self._fetch_from_api()

            # 3. If API fails, try LLM fallback
            if not updated_matches:
                logger.info("API returned no data, trying LLM fallback...")
                updated_matches = self._fetch_from_llm(matches_to_update)

            # 4. Reconcile and update in-memory state
            if updated_matches:
                self.matches = reconcile_matches(self.matches, updated_matches)

                # 5. Update Google Sheets
                self._write_to_sheets()

                # 6. Mark matches as scored in state
                for match in updated_matches:
                    if match.status == MatchStatus.FINISHED:
                        self.state_manager.mark_match_scored(match.match_id)

            self.state_manager.mark_synced()
            logger.info("Score sync completed successfully")

            # 7. Run daily validation after sync
            self._run_validation()

        except Exception as e:
            logger.error(f"Sync failed: {e}", exc_info=True)
            self.state_manager.record_error(str(e))

    def _fetch_from_api(self) -> list[Match]:
        """Attempt to fetch match data from football-data.org."""
        try:
            matches = self.football_api.fetch_finished_matches()
            logger.info(f"API returned {len(matches)} finished matches")
            return matches
        except Exception as e:
            logger.warning(f"Football API failed: {e}")
            return []

    def _fetch_from_llm(self, matches_to_check: list[Match]) -> list[Match]:
        """Attempt to get scores from ChatGPT as fallback."""
        try:
            # Group by date and ask for each date's results
            dates = set(m.match_date for m in matches_to_check)
            all_results = []

            for match_date in sorted(dates):
                day_matches = [m for m in matches_to_check if m.match_date == match_date]
                results = self.llm_fallback.fetch_match_results(
                    match_date, known_matches=day_matches
                )
                all_results.extend(results)

            logger.info(f"LLM returned {len(all_results)} match results")
            return all_results
        except Exception as e:
            logger.warning(f"LLM fallback failed: {e}")
            return []

    def _write_to_sheets(self):
        """Write updated data back to Google Sheets."""
        try:
            # Update schedule with scores
            write_schedule(self.sheets_client, self.matches)

            # Update leaderboard
            write_leaderboard(
                self.sheets_client, self.players, self.matches, self.calculator
            )

            logger.info("Google Sheets updated successfully")
        except Exception as e:
            logger.error(f"Failed to write to sheets: {e}", exc_info=True)

    def _run_validation(self):
        """Run daily validation checks after sync."""
        try:
            report = run_full_validation(
                matches=self.matches,
                players=self.players,
                use_llm=bool(Config.OPENAI_API_KEY),
            )
            if not report.is_healthy:
                logger.warning(
                    f"Validation found issues: {report.error_count} errors, "
                    f"{report.warning_count} warnings"
                )
        except Exception as e:
            logger.warning(f"Validation failed to run: {e}")

    def trigger_sync(self):
        """Manually trigger a score sync (for CLI or API use)."""
        self.scheduler.trigger_now()

    def reschedule(self, hour: int, minute: int = 0):
        """Change the daily sync time on the fly."""
        self.scheduler.reschedule(hour, minute)
        logger.info(f"Rescheduled to {hour:02d}:{minute:02d}")

    def get_leaderboard(self) -> list[tuple[str, float]]:
        """Get current standings from in-memory data."""
        standings = []
        for player in self.players:
            total = self.calculator.calculate_player_total(player.teams, self.matches)
            standings.append((player.name, total))
        return sorted(standings, key=lambda x: x[1], reverse=True)

    def stop(self):
        """Gracefully shutdown."""
        self.scheduler.stop()
        self.state_manager.save()
        logger.info("App shut down gracefully")


def main():
    """Entry point."""
    setup_logging()
    app = FantasyDraftApp()

    # Handle Ctrl+C gracefully
    def signal_handler(sig, frame):
        logger.info("Shutting down...")
        app.stop()
        sys.exit(0)

    signal.signal(signal.SIGINT, signal_handler)
    signal.signal(signal.SIGTERM, signal_handler)

    app.start()

    # Keep the main thread alive
    logger.info("App is running. Press Ctrl+C to stop.")
    logger.info("Commands: 'sync' to trigger manual sync, 'quit' to exit")

    try:
        while True:
            cmd = input("> ").strip().lower()
            if cmd == "sync":
                app.trigger_sync()
            elif cmd == "status":
                for name, pts in app.get_leaderboard():
                    print(f"  {name}: {pts} pts")
            elif cmd == "validate":
                print("Running validation...")
                report = run_full_validation(
                    app.matches, app.players, use_llm=bool(Config.OPENAI_API_KEY)
                )
                print(f"  {report.summary()}")
                for issue in report.issues:
                    print(f"  [{issue.severity}] {issue.message}")
            elif cmd in ("quit", "exit", "q"):
                break
            elif cmd.startswith("reschedule"):
                # reschedule HH:MM
                try:
                    parts = cmd.split()
                    time_parts = parts[1].split(":")
                    app.reschedule(int(time_parts[0]), int(time_parts[1]))
                except (IndexError, ValueError):
                    print("Usage: reschedule HH:MM")
            elif cmd == "help":
                print("Commands: sync, status, validate, reschedule HH:MM, quit")
            else:
                if cmd:
                    print("Unknown command. Type 'help' for options.")
    except EOFError:
        pass

    app.stop()


if __name__ == "__main__":
    main()
