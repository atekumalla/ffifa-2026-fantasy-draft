"""Tests for recovery and state management."""

import json
import tempfile
from datetime import date
from pathlib import Path

from src.models.match import Match, MatchStage, MatchStatus
from src.sync.state_manager import StateManager
from src.sync.recovery import get_matches_needing_update, reconcile_matches


def make_match(match_id="m1", status=MatchStatus.SCHEDULED, match_date=None):
    return Match(
        match_id=match_id,
        match_date=match_date or date(2026, 6, 15),
        stage=MatchStage.GROUP,
        home_team="Team A",
        away_team="Team B",
        status=status,
    )


class TestStateManager:
    def test_fresh_state(self, tmp_path):
        """New state file starts with sensible defaults."""
        state_file = str(tmp_path / "state.json")
        sm = StateManager(state_file=state_file)

        assert sm.last_sync is None
        assert sm.scored_match_ids == []

    def test_mark_synced(self, tmp_path):
        """mark_synced updates timestamp and persists."""
        state_file = str(tmp_path / "state.json")
        sm = StateManager(state_file=state_file)

        sm.mark_synced()

        assert sm.last_sync is not None
        assert sm.state["sync_count"] == 1

        # Reload from disk
        sm2 = StateManager(state_file=state_file)
        assert sm2.last_sync == sm.last_sync

    def test_mark_match_scored(self, tmp_path):
        """Scored match IDs are persisted."""
        state_file = str(tmp_path / "state.json")
        sm = StateManager(state_file=state_file)

        sm.mark_match_scored("match_001")
        sm.mark_match_scored("match_002")
        sm.mark_match_scored("match_001")  # Duplicate

        assert sm.scored_match_ids == ["match_001", "match_002"]
        assert sm.is_match_scored("match_001")
        assert not sm.is_match_scored("match_999")

    def test_recovery_from_disk(self, tmp_path):
        """App can recover state after simulated crash."""
        state_file = str(tmp_path / "state.json")

        # Simulate previous run
        sm1 = StateManager(state_file=state_file)
        sm1.mark_synced()
        sm1.mark_match_scored("m1")
        sm1.mark_match_scored("m2")

        # Simulate new start (reload)
        sm2 = StateManager(state_file=state_file)
        assert sm2.is_match_scored("m1")
        assert sm2.is_match_scored("m2")
        assert sm2.state["sync_count"] == 1


class TestRecovery:
    def test_matches_needing_update(self, tmp_path):
        """Only past, unscored matches need updates."""
        state_file = str(tmp_path / "state.json")
        sm = StateManager(state_file=state_file)
        sm.mark_match_scored("m1")

        matches = [
            make_match("m1", MatchStatus.SCHEDULED, date(2026, 6, 2)),  # Already scored
            make_match("m2", MatchStatus.SCHEDULED, date(2026, 6, 2)),  # Needs update (past)
            make_match("m3", MatchStatus.SCHEDULED, date(2026, 7, 19)),  # Future
        ]

        needs_update = get_matches_needing_update(matches, sm)
        assert len(needs_update) == 1
        assert needs_update[0].match_id == "m2"

    def test_reconcile_prefers_api_finished(self):
        """Reconcile should prefer API data for finished matches."""
        sheet_match = Match(
            match_id="s1",
            match_date=date(2026, 6, 15),
            stage=MatchStage.GROUP,
            home_team="Brazil",
            away_team="Germany",
            status=MatchStatus.SCHEDULED,
        )
        api_match = Match(
            match_id="a1",
            match_date=date(2026, 6, 15),
            stage=MatchStage.GROUP,
            home_team="Brazil",
            away_team="Germany",
            home_goals=2,
            away_goals=1,
            status=MatchStatus.FINISHED,
        )

        result = reconcile_matches([sheet_match], [api_match])
        assert len(result) == 1
        assert result[0].status == MatchStatus.FINISHED
        assert result[0].home_goals == 2
