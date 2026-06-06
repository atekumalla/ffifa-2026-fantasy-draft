"""Scheduler — runs sync at configurable times using APScheduler.

Supports:
  - Automatic daily sync at a configured time
  - Manual trigger
  - On-the-fly schedule changes (no restart needed)
"""

from __future__ import annotations

import logging
import threading
from typing import Callable, Optional

from apscheduler.schedulers.background import BackgroundScheduler
from apscheduler.triggers.cron import CronTrigger

from src.config import Config

logger = logging.getLogger(__name__)

JOB_ID = "daily_score_sync"


class SyncScheduler:
    """Manages scheduled and manual score syncing."""

    def __init__(self, sync_fn: Callable[[], None]):
        """
        Args:
            sync_fn: The function to call when it's time to sync scores.
        """
        self.sync_fn = sync_fn
        self.scheduler = BackgroundScheduler(timezone=Config.SYNC_TIMEZONE)
        self._lock = threading.Lock()

    def start(self):
        """Start the scheduler with the configured time."""
        self._schedule_daily_job(Config.SYNC_HOUR, Config.SYNC_MINUTE)
        self.scheduler.start()
        logger.info(
            f"Scheduler started — daily sync at "
            f"{Config.SYNC_HOUR:02d}:{Config.SYNC_MINUTE:02d} {Config.SYNC_TIMEZONE}"
        )

    def stop(self):
        """Gracefully shut down the scheduler."""
        self.scheduler.shutdown(wait=False)
        logger.info("Scheduler stopped")

    def reschedule(self, hour: int, minute: int = 0):
        """Change the daily sync time on the fly (no restart required)."""
        with self._lock:
            self._schedule_daily_job(hour, minute)
            logger.info(f"Rescheduled daily sync to {hour:02d}:{minute:02d}")

    def trigger_now(self):
        """Manually trigger a sync immediately (runs in background thread)."""
        logger.info("Manual sync triggered")
        thread = threading.Thread(target=self._safe_sync, daemon=True)
        thread.start()

    def _schedule_daily_job(self, hour: int, minute: int):
        """Schedule or replace the daily cron job."""
        trigger = CronTrigger(hour=hour, minute=minute)

        # Remove existing job if any
        if self.scheduler.get_job(JOB_ID):
            self.scheduler.reschedule_job(JOB_ID, trigger=trigger)
        else:
            self.scheduler.add_job(
                self._safe_sync,
                trigger=trigger,
                id=JOB_ID,
                name="Daily FIFA Score Sync",
                replace_existing=True,
            )

    def _safe_sync(self):
        """Wrapper around sync_fn with error handling."""
        try:
            self.sync_fn()
        except Exception as e:
            logger.error(f"Sync failed: {e}", exc_info=True)

    @property
    def next_run_time(self) -> Optional[str]:
        """Get next scheduled run time."""
        job = self.scheduler.get_job(JOB_ID)
        if job and job.next_run_time:
            return job.next_run_time.isoformat()
        return None
