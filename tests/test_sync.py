"""Tests for the sync scheduler."""

from unittest.mock import MagicMock, patch

from src.sync.scheduler import SyncScheduler


class TestSyncScheduler:
    def test_scheduler_initializes(self):
        """Scheduler can be created with a sync function."""
        mock_fn = MagicMock()
        scheduler = SyncScheduler(sync_fn=mock_fn)
        assert scheduler.sync_fn == mock_fn

    def test_trigger_now(self):
        """Manual trigger invokes the sync function."""
        mock_fn = MagicMock()
        scheduler = SyncScheduler(sync_fn=mock_fn)

        # trigger_now runs in a thread, but we can test the function gets called
        scheduler._safe_sync()
        mock_fn.assert_called_once()

    def test_safe_sync_handles_errors(self):
        """Errors in sync function don't crash the scheduler."""
        mock_fn = MagicMock(side_effect=RuntimeError("API down"))
        scheduler = SyncScheduler(sync_fn=mock_fn)

        # Should not raise
        scheduler._safe_sync()
        mock_fn.assert_called_once()

    @patch("src.config.Config.SYNC_HOUR", 10)
    @patch("src.config.Config.SYNC_MINUTE", 30)
    def test_start_and_stop(self):
        """Scheduler can start and stop cleanly."""
        mock_fn = MagicMock()
        scheduler = SyncScheduler(sync_fn=mock_fn)

        scheduler.start()
        assert scheduler.next_run_time is not None

        scheduler.stop()
