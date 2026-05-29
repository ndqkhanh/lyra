"""Tests for ChampionTracker — champion hypothesis lifecycle management."""

import pytest

from lyra_core.collective.champion_tracker import (
    ChampionState,
    ChampionStatus,
    ChampionTracker,
)


class TestChampionState:
    """Unit tests for ChampionState dataclass."""

    def test_initial_state(self):
        state = ChampionState(
            hypothesis_id="h1",
            statement="X causes Y",
            proposed_by="agent_a",
        )
        assert state.hypothesis_id == "h1"
        assert state.status == ChampionStatus.PROPOSED
        assert state.verification_score == 0.0
        assert state.confirmations == 0
        assert state.is_active is True
        assert state.is_confirmed is False

    def test_staleness_tracks_time(self):
        state = ChampionState(
            hypothesis_id="h1",
            statement="X causes Y",
            proposed_by="agent_a",
        )
        # Fresh state should have near-zero staleness
        assert state.staleness_s < 1.0

    def test_record_verification_updates_score(self):
        state = ChampionState(
            hypothesis_id="h1",
            statement="X causes Y",
            proposed_by="agent_a",
        )
        state.record_verification(0.85, "agent_b")
        assert state.verification_score == 0.85
        assert state.confirmations == 1
        assert "agent_b" in state.confirmer_ids
        assert state.last_verified_at > 0

    def test_record_verification_clamps_score(self):
        state = ChampionState(
            hypothesis_id="h1",
            statement="X causes Y",
            proposed_by="agent_a",
        )
        state.record_verification(1.5, "agent_b")
        assert state.verification_score == 1.0
        state.record_verification(-0.5, "agent_c")
        assert state.verification_score == 0.0

    def test_same_verifier_not_double_counted(self):
        state = ChampionState(
            hypothesis_id="h1",
            statement="X causes Y",
            proposed_by="agent_a",
        )
        state.record_verification(0.7, "agent_b")
        state.record_verification(0.9, "agent_b")
        assert state.confirmations == 1

    def test_is_active_states(self):
        state = ChampionState(
            hypothesis_id="h1",
            statement="X causes Y",
            proposed_by="agent_a",
        )
        assert state.is_active is True

        state.status = ChampionStatus.FALSIFIED
        assert state.is_active is False

        state.status = ChampionStatus.STALE
        assert state.is_active is False

        state.status = ChampionStatus.SUPERSEDED
        assert state.is_active is False


class TestChampionTracker:
    """Unit tests for ChampionTracker."""

    def test_propose_champion(self):
        tracker = ChampionTracker()
        state = tracker.propose_champion("h1", "X causes Y", "agent_a")
        assert state.hypothesis_id == "h1"
        assert state.status == ChampionStatus.PROPOSED
        assert tracker.get_champion("default") is state

    def test_propose_champion_with_area(self):
        tracker = ChampionTracker()
        tracker.propose_champion("h1", "X causes Y", "agent_a", area="physics")
        assert tracker.get_champion("physics").hypothesis_id == "h1"
        assert tracker.get_champion("default") is None

    def test_verify_champion_promotes_to_confirming(self):
        tracker = ChampionTracker(confirmation_threshold=2)
        tracker.propose_champion("h1", "X causes Y", "agent_a")
        status = tracker.verify_champion("h1", 0.8, "agent_b")
        assert status == ChampionStatus.CONFIRMING

    def test_verify_champion_promotes_to_confirmed(self):
        tracker = ChampionTracker(confirmation_threshold=2)
        tracker.propose_champion("h1", "X causes Y", "agent_a")
        tracker.verify_champion("h1", 0.8, "agent_b")
        status = tracker.verify_champion("h1", 0.9, "agent_c")
        assert status == ChampionStatus.CONFIRMED

    def test_verify_unknown_champion_raises(self):
        tracker = ChampionTracker()
        with pytest.raises(KeyError, match="Unknown champion"):
            tracker.verify_champion("nonexistent", 0.5, "agent_b")

    def test_falsify_champion(self):
        tracker = ChampionTracker()
        tracker.propose_champion("h1", "X causes Y", "agent_a")
        tracker.falsify_champion("h1", "experiment disproved it")

        state = tracker.get_champion_by_id("h1")
        assert state.status == ChampionStatus.FALSIFIED
        assert tracker.get_champion("default") is None
        assert len(tracker.history) == 1

    def test_competing_champions_contest_each_other(self):
        tracker = ChampionTracker()
        tracker.propose_champion("h1", "X causes Y", "agent_a")
        tracker.propose_champion("h2", "Z causes Y", "agent_b")

        h1 = tracker.get_champion_by_id("h1")
        h2 = tracker.get_champion_by_id("h2")
        assert h1.status == ChampionStatus.CONTESTED
        assert "h2" in h1.competing_ids
        assert "h1" in h2.competing_ids

    def test_check_staleness(self):
        tracker = ChampionTracker(staleness_threshold_s=0.0)  # Immediate staleness
        tracker.propose_champion("h1", "X causes Y", "agent_a")
        stale = tracker.check_staleness()
        assert "h1" in stale
        assert tracker.get_champion_by_id("h1").status == ChampionStatus.STALE

    def test_refresh_champion_resets_staleness(self):
        tracker = ChampionTracker(staleness_threshold_s=0.0)
        tracker.propose_champion("h1", "X causes Y", "agent_a")
        tracker.check_staleness()
        assert tracker.get_champion_by_id("h1").status == ChampionStatus.STALE

        tracker.refresh_champion("h1")
        assert tracker.get_champion_by_id("h1").status == ChampionStatus.CONFIRMING

    def test_active_champions_filter(self):
        tracker = ChampionTracker()
        tracker.propose_champion("h1", "X causes Y", "agent_a")
        tracker.propose_champion("h2", "A causes B", "agent_c", area="physics")
        tracker.falsify_champion("h1", "wrong")

        active = tracker.active_champions
        assert len(active) == 1
        assert active[0].hypothesis_id == "h2"

    def test_confirmed_champions_filter(self):
        tracker = ChampionTracker(confirmation_threshold=1)
        tracker.propose_champion("h1", "X causes Y", "agent_a")
        tracker.verify_champion("h1", 0.8, "agent_b")

        assert len(tracker.confirmed_champions) == 1
        assert tracker.confirmed_champions[0].hypothesis_id == "h1"

    def test_summary(self):
        tracker = ChampionTracker()
        tracker.propose_champion("h1", "X causes Y", "agent_a")
        tracker.propose_champion("h2", "A causes B", "agent_c", area="physics")

        s = tracker.summary()
        assert s["areas"] == 2
        assert s["active"] == 2
        assert s["total_tracked"] == 2

    def test_multiple_areas_independent(self):
        tracker = ChampionTracker()
        tracker.propose_champion("h1", "X causes Y", "agent_a", area="physics")
        tracker.propose_champion("h2", "A causes B", "agent_c", area="biology")

        assert tracker.get_champion("physics").hypothesis_id == "h1"
        assert tracker.get_champion("biology").hypothesis_id == "h2"
        assert len(tracker.areas) == 2

    def test_falsify_nonexistent_is_noop(self):
        tracker = ChampionTracker()
        tracker.falsify_champion("nonexistent", "reason")
        assert len(tracker.history) == 0
