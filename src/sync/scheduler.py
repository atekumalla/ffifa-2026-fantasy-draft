"""Scheduler — runs sync at configurable intervals using APScheduler.

Supports:
  - Regular interval sync (default: every 60 minutes)
  - Aggressive live-match sync (default: every 2 minutes when a match is in play)
  - Automatic switching between regular and live modes
  - Manual trigger
  - On-the-fly schedule changes (no restart needed)
"""

from __future__ import annotations

import logging
import threading
from typing import Callable, Optional

from apscheduler.schedulers.background import BackgroundScheduler
from apscheduler.triggers.interval import IntervalTrigger

from src.config import Config

logger = logging.getLogger(__name__)

JOB_ID = "score_sync"


class SyncScheduler:
    """Manages scheduled and manual score syncing with adaptive frequency.
    
    When no live matches are detected, syncs at the regular interval
    (SYNC_INTERVAL_MINUTES, default 60 min). When live matches are
    detected, switches to aggressive mode (SYNC_LIVE_INTERVAL_SECONDS,
    default 120s / 2 min).
    """

    def __init__(self, sync_fn: Callable[[], None], has_live_matches_fn: Optional[Callable[[], bool]] = None):
        """
        Args:
            sync_fn: The function to call when it's time to sync scores.
            has_live_matches_fn: Optional function that returns True if there are live matches.
                                 Used to switch between regular and live intervals.
        """
        self.sync_fn = sync_fn
        self.has_live_matches_fn = has_live_matches_fn
        self.scheduler = BackgroundScheduler(timezone=Config.SYNC_TIMEZONE)
        self._lock = threading.Lock()
        self._is_live_mode = False
        self._regular_interval = Config.SYNC_INTERVAL_MINUTES * 60  # convert to seconds
        self._live_interval = Config.SYNC_LIVE_INTERVAL_SECONDS

    def start(self):
        """Start the scheduler with the regular interval."""
        self._schedule_job(self._regular_interval)
        self.scheduler.start()
        logger.info(
            f"Scheduler started — regular sync every {Config.SYNC_INTERVAL_MINUTES} min, "
            f"live sync every {Config.SYNC_LIVE_INTERVAL_SECONDS}s"
        )

    def stop(self):
        """Gracefully shut down the scheduler."""
        self.scheduler.shutdown(wait=False)
        logger.info("Scheduler stopped")

    def reschedule(self, interval_seconds: int):
        """Change the sync interval on the fly (no restart required)."""
        with self._lock:
            self._schedule_job(interval_seconds)
            logger.info(f"Rescheduled sync to every {interval_seconds}s")

    def trigger_now(self):
        """Manually trigger a sync immediately (runs in background thread)."""
        logger.info("Manual sync triggered")
        thread = threading.Thread(target=self._safe_sync, daemon=True)
        thread.start()

    def _schedule_job(self, interval_seconds: int):
        """Schedule or replace the interval job."""
        trigger = IntervalTrigger(seconds=interval_seconds)

        # Remove existing job if any
        if self.scheduler.get_job(JOB_ID):
            self.scheduler.reschedule_job(JOB_ID, trigger=trigger)
        else:
            self.scheduler.add_job(
                self._safe_sync,
                trigger=trigger,
                id=JOB_ID,
                name="FIFA Score Sync",
                replace_existing=True,
            )

    def _check_and_adapt_interval(self):
        """Check for live matches and switch interval mode if needed."""
        if not self.has_live_matches_fn:
            return

        try:
            live_now = self.has_live_matches_fn()
        except Exception as e:
            logger.warning(f"Failed to check live match status: {e}")
            return

        if live_now and not self._is_live_mode:
            # Switch to aggressive live mode
            self._is_live_mode = True
            self._schedule_job(self._live_interval)
            logger.info(
                f"⚡ Live match detected! Switching to aggressive sync "
                f"(every {self._live_interval}s)"
            )
        elif not live_now and self._is_live_mode:
            # Switch back to regular mode
            self._is_live_mode = False
            self._schedule_job(self._regular_interval)
            logger.info(
                f"No live matches — switching back to regular sync "
                f"(every {Config.SYNC_INTERVAL_MINUTES} min)"
            )

    def _safe_sync(self):
        """Wrapper around sync_fn with error handling and adaptive interval logic."""
        try:
            self.sync_fn()
        except Exception as e:
            logger.error(f"Sync failed: {e}", exc_info=True)
        finally:
            # After each sync, check if we need to switch modes
            self._check_and_adapt_interval()

    @property
    def next_run_time(self) -> Optional[str]:
        """Get next scheduled run time."""
        job = self.scheduler.get_job(JOB_ID)
        if job and job.next_run_time:
            return job.next_run_time.isoformat()
        return None

    @property
    def is_live_mode(self) -> bool:
        """Whether the scheduler is currently in aggressive live-match mode."""
        return self._is_live_mode

    @property
    def current_interval_seconds(self) -> int:
        """Current sync interval in seconds."""
        return self._live_interval if self._is_live_mode else self._regular_interval
