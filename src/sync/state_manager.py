"""State manager — persists sync state to disk for crash recovery.

The state file tracks:
  - Last successful sync timestamp
  - Which matches have been scored
  - Application health info
"""

from __future__ import annotations

import json
import logging
from datetime import datetime, timezone
from pathlib import Path
from typing import Optional

from src.config import Config

logger = logging.getLogger(__name__)


class StateManager:
    """Manages persistent state so the app can resume after restart."""

    def __init__(self, state_file: str | None = None):
        self.state_file = Path(state_file or Config.STATE_FILE)
        self.state: dict = self._load()

    def _load(self) -> dict:
        """Load state from disk."""
        if self.state_file.exists():
            try:
                with open(self.state_file, "r") as f:
                    state = json.load(f)
                    logger.info(f"Loaded state from {self.state_file}")
                    return state
            except (json.JSONDecodeError, IOError) as e:
                logger.warning(f"Failed to load state file: {e}")
        return self._default_state()

    def _default_state(self) -> dict:
        return {
            "last_sync": None,
            "last_updated": None,
            "scored_match_ids": [],
            "sync_count": 0,
            "last_error": None,
        }

    def save(self):
        """Persist state to disk."""
        self.state_file.parent.mkdir(parents=True, exist_ok=True)
        with open(self.state_file, "w") as f:
            json.dump(self.state, f, indent=2, default=str)
        logger.debug(f"State saved to {self.state_file}")

    @property
    def last_sync(self) -> Optional[str]:
        return self.state.get("last_sync")

    @property
    def scored_match_ids(self) -> list[str]:
        return self.state.get("scored_match_ids", [])

    def mark_synced(self):
        """Record that a sync just completed."""
        now = datetime.now(timezone.utc).isoformat()
        self.state["last_sync"] = now
        self.state["last_updated"] = now
        self.state["sync_count"] = self.state.get("sync_count", 0) + 1
        self.state["last_error"] = None
        self.save()

    def mark_match_scored(self, match_id: str):
        """Mark a match as having been scored (to avoid re-scoring)."""
        if match_id not in self.state["scored_match_ids"]:
            self.state["scored_match_ids"].append(match_id)
            self.save()

    def is_match_scored(self, match_id: str) -> bool:
        """Check if a match has already been scored."""
        return match_id in self.state.get("scored_match_ids", [])

    def record_error(self, error: str):
        """Record the last error for debugging."""
        self.state["last_error"] = {
            "message": error,
            "timestamp": datetime.now(timezone.utc).isoformat(),
        }
        self.save()

    def get_unscored_matches(self, all_matches: list) -> list:
        """Filter to only matches that haven't been scored yet."""
        scored_ids = set(self.scored_match_ids)
        return [m for m in all_matches if m.match_id not in scored_ids]
