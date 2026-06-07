"""Tests for src/steering/preference_learner.py and trust_calibrator.py."""
from __future__ import annotations

import tempfile
from pathlib import Path

import pytest

from lyra.steering.preference_learner import (
    PreferenceLearner,
    FeedbackEvent,
    UserPreference,
    ProactiveElicitation,
    DecoupledRewind,
    IdentityAnonymizedSteering,
)
from lyra.steering.trust_calibrator import (
    TrustCalibrator,
    TrustEntry,
    DecisionOutcome,
)


# ---------------------------------------------------------------------------
# PreferenceLearner
# ---------------------------------------------------------------------------


class TestPreferenceLearner:
    def test_initial_preference_neutral(self):
        pl = PreferenceLearner()
        score = pl.predict_preference("unknown_action")
        assert score == 0.5

    def test_record_feedback(self):
        pl = PreferenceLearner()
        pl.record_feedback(
            FeedbackEvent(
                session_id="s1",
                action_type="write_file",
                rating=1,
                action_details={"tool": "write"},
            )
        )
        pref = pl.get_preference("write_file")
        assert pref is not None
        assert pref.score > 0.5

    def test_record_feedback_simple(self):
        pl = PreferenceLearner()
        pl.record_feedback_simple("s1", "approve", rating=1)
        pref = pl.get_preference("approve")
        assert pref is not None

    def test_get_preference_unknown(self):
        pl = PreferenceLearner()
        assert pl.get_preference("nonexistent") is None

    def test_get_all_preferences(self):
        pl = PreferenceLearner()
        pl.record_feedback_simple("s1", "action_a", rating=1)
        pl.record_feedback_simple("s2", "action_b", rating=-1)
        all_prefs = pl.get_all_preferences()
        assert len(all_prefs) == 2

    def test_get_all_preferences_filtered(self):
        pl = PreferenceLearner()
        pl.record_feedback_simple("s1", "action_a", rating=1)
        pl.record_feedback_simple("s2", "action_b", rating=-1)
        prefs = pl.get_all_preferences("action_a")
        assert len(prefs) == 1

    def test_feedback_history(self):
        pl = PreferenceLearner()
        pl.record_feedback_simple("s1", "write", 1)
        pl.record_feedback_simple("s2", "read", -1)
        history = pl.get_feedback_history()
        assert len(history) == 2

    def test_feedback_history_filtered(self):
        pl = PreferenceLearner()
        pl.record_feedback_simple("s1", "write", 1)
        pl.record_feedback_simple("s2", "read", -1)
        history = pl.get_feedback_history(action_type="write")
        assert len(history) == 1

    def test_negative_feedback(self):
        pl = PreferenceLearner()
        pl.record_feedback_simple("s1", "delete", rating=-1)
        pref = pl.get_preference("delete")
        assert pref is not None
        assert pref.score < 0.5

    def test_multiple_feedback_updates(self):
        pl = PreferenceLearner()
        pl.record_feedback_simple("s1", "tool_call", rating=1)
        pl.record_feedback_simple("s1", "tool_call", rating=1)
        pref = pl.get_preference("tool_call")
        assert pref is not None
        assert pref.sample_count == 2

    def test_persistence(self, tmp_path):
        persist_path = tmp_path / "prefs.json"
        pl1 = PreferenceLearner(persistence_path=str(persist_path))
        pl1.record_feedback_simple("s1", "test_action", rating=1)

        # New learner loading from same path
        pl2 = PreferenceLearner(persistence_path=str(persist_path))
        pref = pl2.get_preference("test_action")
        assert pref is not None
        assert pref.score > 0.5


# ---------------------------------------------------------------------------
# ProactiveElicitation
# ---------------------------------------------------------------------------


class TestProactiveElicitation:
    def test_should_ask_unknown_action(self):
        pl = PreferenceLearner()
        elicitor = ProactiveElicitation(pl, uncertainty_threshold=0.4)
        assert elicitor.should_ask("unknown_action") is True

    def test_should_not_ask_known_action(self):
        pl = PreferenceLearner()
        pl.record_feedback_simple("s1", "known_action", rating=1, details={"tool": "write"})
        # Confidence is 0.5 after first feedback, which is >= 0.4 threshold,
        # so should_ask returns False (no need to ask)
        elicitor = ProactiveElicitation(pl, uncertainty_threshold=0.4)
        assert elicitor.should_ask("known_action") is False

    def test_ask_returns_query(self):
        pl = PreferenceLearner()
        elicitor = ProactiveElicitation(pl)
        query = elicitor.ask("write_file", context="user wants to save", options=["save", "discard"])
        assert query is not None
        assert "write_file" in query.question

    def test_answer_query(self):
        pl = PreferenceLearner()
        elicitor = ProactiveElicitation(pl)
        query = elicitor.ask("unknown_action", force=True)
        assert query is not None
        result = elicitor.answer_query(query.query_id, "always allow")
        assert result is True

    def test_answer_nonexistent_query(self):
        pl = PreferenceLearner()
        elicitor = ProactiveElicitation(pl)
        assert elicitor.answer_query("nonexistent", "answer") is False

    def test_pending_queries(self):
        pl = PreferenceLearner()
        elicitor = ProactiveElicitation(pl)
        elicitor.ask("action_a", force=True)
        elicitor.ask("action_b", force=True)
        assert len(elicitor.pending_queries()) == 2

    def test_force_ask_even_when_known(self):
        pl = PreferenceLearner()
        pl.record_feedback_simple("s1", "known", rating=1)
        elicitor = ProactiveElicitation(pl, uncertainty_threshold=0.1)
        # Without force, should not ask (pref exists, confidence 0.5 > 0.1 threshold)
        query = elicitor.ask("known", force=True)
        assert query is not None


# ---------------------------------------------------------------------------
# DecoupledRewind
# ---------------------------------------------------------------------------


class TestDecoupledRewind:
    def test_save_and_rewind(self):
        rewind = DecoupledRewind()
        ckpt_id = rewind.save_checkpoint(
            session_state={"tokens": 100},
            metadata={"action": "tool_call"},
            context_blob={"learned": "important"},
        )
        result = rewind.rewind(ckpt_id)
        assert result is not None
        assert result.session_state == {"tokens": 100}
        assert result.context_blob == {"learned": "important"}

    def test_rewind_nonexistent(self):
        rewind = DecoupledRewind()
        assert rewind.rewind("nonexistent") is None

    def test_list_checkpoints(self):
        rewind = DecoupledRewind()
        rewind.save_checkpoint(metadata={"step": 1})
        rewind.save_checkpoint(metadata={"step": 2})
        assert len(rewind.list_checkpoints()) == 2

    def test_latest_checkpoint(self):
        rewind = DecoupledRewind()
        rewind.save_checkpoint(metadata={"step": 1})
        latest = rewind.latest_checkpoint()
        assert latest is not None
        assert latest.metadata == {"step": 1}

    def test_latest_checkpoint_empty(self):
        rewind = DecoupledRewind()
        assert rewind.latest_checkpoint() is None

    def test_clear(self):
        rewind = DecoupledRewind()
        rewind.save_checkpoint(metadata={"step": 1})
        rewind.clear()
        assert len(rewind.list_checkpoints()) == 0

    def test_context_blob_preserved_on_rewind(self):
        rewind = DecoupledRewind()
        ckpt_id = rewind.save_checkpoint(
            session_state={"tokens": 50},
            context_blob={"analysis": "deep", "facts": ["a", "b"]},
        )
        result = rewind.rewind(ckpt_id)
        assert result is not None
        assert result.context_blob == {"analysis": "deep", "facts": ["a", "b"]}


# ---------------------------------------------------------------------------
# IdentityAnonymizedSteering
# ---------------------------------------------------------------------------


class TestIdentityAnonymizedSteering:
    def test_anonymize_consistent(self):
        anon = IdentityAnonymizedSteering()
        h1 = anon.anonymize("session-123")
        h2 = anon.anonymize("session-123")
        assert h1 == h2
        assert len(h1) == 16

    def test_anonymize_different_sessions(self):
        anon = IdentityAnonymizedSteering()
        h1 = anon.anonymize("session-a")
        h2 = anon.anonymize("session-b")
        assert h1 != h2

    def test_record_decision(self):
        anon = IdentityAnonymizedSteering()
        decision = anon.record_decision("approve", "session-1", reason="safe action")
        assert decision.session_anonymized_id == anon.anonymize("session-1")
        assert decision.action == "approve"

    def test_get_decisions_all(self):
        anon = IdentityAnonymizedSteering()
        anon.record_decision("a", "s1")
        anon.record_decision("b", "s2")
        assert len(anon.get_decisions()) == 2

    def test_get_decisions_filtered(self):
        anon = IdentityAnonymizedSteering()
        anon.record_decision("a", "s1")
        anon.record_decision("b", "s1")
        decisions = anon.get_decisions("s1")
        assert len(decisions) == 2

    def test_get_decision_count(self):
        anon = IdentityAnonymizedSteering()
        assert anon.get_decision_count() == 0
        anon.record_decision("a", "s1")
        assert anon.get_decision_count() == 1


# ---------------------------------------------------------------------------
# TrustCalibrator
# ---------------------------------------------------------------------------


class TestTrustCalibrator:
    def test_initial_trust_neutral(self):
        tc = TrustCalibrator()
        assert tc.get_trust("unknown") == 0.5

    def test_record_success_increases_trust(self):
        tc = TrustCalibrator(learning_rate=0.1, min_observations=1)
        tc.record_outcome("write_file", success=True, confidence=0.8)
        assert tc.get_trust("write_file") > 0.5

    def test_record_failure_decreases_trust(self):
        tc = TrustCalibrator(learning_rate=0.1, min_observations=1)
        tc.record_outcome("write_file", success=False, confidence=0.8)
        assert tc.get_trust("write_file") < 0.5

    def test_trust_level_high(self):
        tc = TrustCalibrator(min_observations=1)
        tc.record_outcome("ctx", True, 0.9)
        tc.record_outcome("ctx", True, 0.9)
        assert tc.get_trust_level("ctx") in ("high", "medium")

    def test_trust_level_unknown(self):
        tc = TrustCalibrator()
        # Default trust is 0.5, which maps to "medium"
        assert tc.get_trust_level("nonexistent") == "medium"

    def test_should_override_low_trust(self):
        tc = TrustCalibrator(min_observations=1)
        tc.record_outcome("risky_op", False, 0.9)  # Low trust
        tc.record_outcome("risky_op", False, 0.9)  # Even lower
        assert tc.should_override("risky_op", 0.5) is True

    def test_should_override_unknown_context(self):
        tc = TrustCalibrator(min_observations=5)
        assert tc.should_override("unknown", 0.3) is True

    def test_get_context_summary(self):
        tc = TrustCalibrator()
        tc.record_outcome("ctx", True, 0.9)
        summary = tc.get_context_summary("ctx")
        assert summary is not None
        assert summary.context == "ctx"
        assert summary.decision_count == 1
        assert tc.get_context_summary("unknown") is None

    def test_get_all_contexts(self):
        tc = TrustCalibrator()
        tc.record_outcome("a", True)
        tc.record_outcome("b", False)
        assert len(tc.get_all_contexts()) == 2

    def test_get_success_rate(self):
        tc = TrustCalibrator()
        tc.record_outcome("ctx", True, 0.9)
        tc.record_outcome("ctx", True, 0.9)
        tc.record_outcome("ctx", False, 0.9)
        rate = tc.get_success_rate("ctx")
        assert rate == 2 / 3

    def test_get_success_rate_unknown(self):
        tc = TrustCalibrator()
        assert tc.get_success_rate("unknown") == 0.5

    def test_get_outcomes(self):
        tc = TrustCalibrator()
        tc.record_outcome("ctx", True)
        tc.record_outcome("ctx2", False)
        outcomes = tc.get_outcomes()
        assert len(outcomes) == 2

    def test_get_outcomes_filtered(self):
        tc = TrustCalibrator()
        tc.record_outcome("ctx", True)
        tc.record_outcome("other", False)
        outcomes = tc.get_outcomes(context="ctx")
        assert len(outcomes) == 1

    def test_reset_context(self):
        tc = TrustCalibrator(min_observations=1)
        tc.record_outcome("ctx", False, 0.8)
        assert tc.reset_context("ctx") is True
        assert tc.reset_context("unknown") is False
        assert tc.get_trust("ctx") == 0.5

    def test_reset_all(self):
        tc = TrustCalibrator()
        tc.record_outcome("a", True)
        tc.record_outcome("b", False)
        tc.reset_all()
        assert tc.get_all_contexts() == []
        assert tc.get_outcomes() == []
