"""Tests for the lyra-human-interaction package."""

from __future__ import annotations

import time

import pytest
from lyra_human_interaction import (
    AlignmentDialog,
    ClarificationRequest,
    Explanation,
    ExplanationLevel,
    FeedbackType,
    HumanInteractionEngine,
    InteractionConfig,
    NegotiationPhase,
    NegotiationState,
    UserFeedback,
)

# ---------------------------------------------------------------------------
# Enum tests
# ---------------------------------------------------------------------------


class TestExplanationLevel:
    def test_values(self) -> None:
        assert ExplanationLevel.NOVICE.value == "NOVICE"
        assert ExplanationLevel.INTERMEDIATE.value == "INTERMEDIATE"
        assert ExplanationLevel.EXPERT.value == "EXPERT"
        assert ExplanationLevel.EXECUTIVE.value == "EXECUTIVE"
        assert ExplanationLevel.TECHNICAL.value == "TECHNICAL"

    def test_membership(self) -> None:
        assert ExplanationLevel("NOVICE") == ExplanationLevel.NOVICE
        assert ExplanationLevel("INTERMEDIATE") == ExplanationLevel.INTERMEDIATE
        assert len(ExplanationLevel) == 5


class TestNegotiationPhase:
    def test_values(self) -> None:
        assert NegotiationPhase.PROPOSAL.value == "PROPOSAL"
        assert NegotiationPhase.AGREEMENT.value == "AGREEMENT"
        assert NegotiationPhase.IMPASSE.value == "IMPASSE"

    def test_all_phases_present(self) -> None:
        expected = {
            "PROPOSAL",
            "COUNTER_PROPOSAL",
            "CLARIFICATION",
            "CONCESSION",
            "AGREEMENT",
            "IMPASSE",
        }
        actual = {m.value for m in NegotiationPhase}
        assert actual == expected


class TestFeedbackType:
    def test_values(self) -> None:
        assert FeedbackType.CORRECTION.value == "CORRECTION"
        assert FeedbackType.PREFERENCE.value == "PREFERENCE"
        assert FeedbackType.RATING.value == "RATING"
        assert FeedbackType.SUGGESTION.value == "SUGGESTION"
        assert FeedbackType.CLARIFICATION_REQUEST.value == "CLARIFICATION_REQUEST"


# ---------------------------------------------------------------------------
# Data class tests
# ---------------------------------------------------------------------------


class TestExplanation:
    def test_create(self) -> None:
        exp = Explanation(
            explanation_id="exp_001",
            topic="Route Planning",
            level="INTERMEDIATE",
            summary="A summary.",
            detailed_steps=("Step 1", "Step 2"),
            key_insights=("Insight A",),
            confidence=0.85,
            assumptions=("Data is accurate",),
            limitations=("May miss edge cases",),
        )
        assert exp.explanation_id == "exp_001"
        assert exp.topic == "Route Planning"
        assert exp.confidence == 0.85

    def test_frozen_immutability(self) -> None:
        exp = Explanation(
            explanation_id="e1",
            topic="t",
            level="NOVICE",
            summary="s",
            detailed_steps=(),
            key_insights=(),
            confidence=0.5,
            assumptions=(),
            limitations=(),
        )
        with pytest.raises(AttributeError):
            exp.topic = "changed"  # type: ignore[misc]


class TestNegotiationState:
    def test_create_defaults(self) -> None:
        state = NegotiationState(
            negotiation_id="n1",
            phase="PROPOSAL",
            agent_proposal="Use approach A",
            human_counter="",
            points_of_agreement=(),
            points_of_disagreement=(),
        )
        assert state.resolution == ""
        assert state.round_count == 0

    def test_frozen_immutability(self) -> None:
        state = NegotiationState(
            negotiation_id="n1",
            phase="PROPOSAL",
            agent_proposal="p",
            human_counter="",
            points_of_agreement=(),
            points_of_disagreement=(),
        )
        with pytest.raises(AttributeError):
            state.phase = "AGREEMENT"  # type: ignore[misc]


class TestUserFeedback:
    def test_create(self) -> None:
        fb = UserFeedback(
            feedback_id="fb_1",
            feedback_type="CORRECTION",
            content="Wrong approach",
            target_decision_id="dec_1",
            timestamp=1000.0,
        )
        assert not fb.incorporated


class TestClarificationRequest:
    def test_create(self) -> None:
        req = ClarificationRequest(
            request_id="cr_1",
            context="User asked about X",
            question="Do you mean X or Y?",
            options=("X", "Y"),
            default_answer="X",
        )
        assert not req.resolved


class TestAlignmentDialog:
    def test_create(self) -> None:
        dialog = AlignmentDialog(
            dialog_id="ad_1",
            topic="Privacy settings",
            agent_position="Default to strict",
            human_position="Default to relaxed",
            common_ground=("Both want security",),
            outcome="Compromise found",
            trust_score=0.7,
        )
        assert dialog.trust_score == 0.7


class TestInteractionConfig:
    def test_defaults(self) -> None:
        config = InteractionConfig()
        assert config.default_explanation_level == "INTERMEDIATE"
        assert config.negotiation_rounds_limit == 5
        assert config.feedback_enabled is True
        assert config.max_context_history == 50

    def test_custom(self) -> None:
        config = InteractionConfig(
            default_explanation_level="EXPERT",
            negotiation_rounds_limit=10,
            feedback_enabled=False,
        )
        assert config.default_explanation_level == "EXPERT"
        assert config.negotiation_rounds_limit == 10
        assert config.feedback_enabled is False


# ---------------------------------------------------------------------------
# HumanInteractionEngine tests
# ---------------------------------------------------------------------------


class TestHumanInteractionEngine:
    def test_default_initialization(self) -> None:
        engine = HumanInteractionEngine()
        stats = engine.get_stats()
        assert stats["explanations_generated"] == 0
        assert stats["negotiations_started"] == 0

    def test_custom_config(self) -> None:
        config = InteractionConfig(
            default_explanation_level="EXPERT",
            feedback_enabled=False,
        )
        engine = HumanInteractionEngine(config=config)
        assert engine._config.default_explanation_level == "EXPERT"
        assert engine._config.feedback_enabled is False

    # -- generate_explanation

    def test_generate_explanation_default_level(self) -> None:
        engine = HumanInteractionEngine()
        exp = engine.generate_explanation(
            topic="Q-Learning",
            decision_context="Selecting exploration rate",
            reasoning=["Considered epsilon decay", "Evaluated state space size"],
        )
        assert exp.explanation_id.startswith("exp_")
        assert exp.topic == "Q-Learning"
        assert exp.level == "INTERMEDIATE"
        assert len(exp.detailed_steps) >= 1
        assert len(exp.key_insights) >= 1
        assert 0.0 <= exp.confidence <= 1.0

    def test_generate_explanation_novice(self) -> None:
        engine = HumanInteractionEngine()
        exp = engine.generate_explanation(
            topic="Q-Learning",
            decision_context="test",
            reasoning=["Step one", "Step two", "Step three"],
            level="NOVICE",
        )
        assert exp.level == "NOVICE"
        assert "simple terms" in exp.summary.lower()
        assert len(exp.detailed_steps) <= 3

    def test_generate_explanation_expert(self) -> None:
        engine = HumanInteractionEngine()
        exp = engine.generate_explanation(
            topic="Gradient Descent",
            decision_context="Hyperparameter tuning",
            reasoning=["Selected learning rate", "Chose batch size", "Set momentum"],
            level="EXPERT",
        )
        assert exp.level == "EXPERT"
        assert exp.confidence >= 0.8
        assert len(exp.detailed_steps) >= 3

    def test_generate_explanation_executive(self) -> None:
        engine = HumanInteractionEngine()
        exp = engine.generate_explanation(
            topic="Model Selection",
            decision_context="Production deployment",
            reasoning=["Compared accuracy", "Evaluated latency"],
            level="EXECUTIVE",
        )
        assert exp.level == "EXECUTIVE"
        assert "strategic" in exp.summary.lower()

    def test_generate_explanation_technical(self) -> None:
        engine = HumanInteractionEngine()
        exp = engine.generate_explanation(
            topic="Attention Mechanism",
            decision_context="Transformer layer count",
            reasoning=["Head dimension analysis", "Key-query dot product check"],
            level="TECHNICAL",
        )
        assert exp.level == "TECHNICAL"
        assert len(exp.detailed_steps) >= 2

    def test_generate_explanation_with_audience_knowledge(self) -> None:
        engine = HumanInteractionEngine()
        exp = engine.generate_explanation(
            topic="Reinforcement Learning",
            decision_context="test",
            reasoning=["Saw reward signal", "Updated policy"],
            audience_knowledge="Python, basic ML",
        )
        assert "Python" in exp.summary or "basic ML" in exp.summary

    # -- start_negotiation

    def test_start_negotiation(self) -> None:
        engine = HumanInteractionEngine()
        state = engine.start_negotiation(
            topic="Deployment strategy",
            agent_proposal="Deploy to staging first, then production",
        )
        assert state.negotiation_id.startswith("neg_")
        assert state.phase == "PROPOSAL"
        assert state.round_count == 0
        assert state.resolution == ""

    # -- negotiate_round

    def test_negotiate_round_agreement(self) -> None:
        engine = HumanInteractionEngine()
        state = engine.start_negotiation(
            topic="Test scheduling",
            agent_proposal="Run tests nightly",
        )
        new_state = engine.negotiate_round(
            state,
            human_response="I agree, nightly tests are a good idea",
        )
        assert new_state.phase == "AGREEMENT"
        assert new_state.round_count == 1
        assert len(new_state.points_of_agreement) >= 1

    def test_negotiate_round_disagreement(self) -> None:
        engine = HumanInteractionEngine()
        state = engine.start_negotiation(
            topic="Framework choice",
            agent_proposal="Use framework A",
        )
        new_state = engine.negotiate_round(
            state,
            human_response="I disagree, framework B is better",
            agent_concession="What about framework C?",
        )
        # Agent concedes with a counter-proposal -> COUNTER_PROPOSAL phase
        assert new_state.phase == "COUNTER_PROPOSAL"
        assert new_state.round_count == 1

    def test_negotiate_round_clarification(self) -> None:
        engine = HumanInteractionEngine()
        state = engine.start_negotiation(
            topic="Budget allocation",
            agent_proposal="Allocate 50% to R&D",
        )
        new_state = engine.negotiate_round(
            state,
            human_response="Can you explain the breakdown more?",
        )
        assert new_state.phase == "CLARIFICATION"

    # -- process_feedback

    def test_process_feedback_correction(self) -> None:
        engine = HumanInteractionEngine()
        fb = UserFeedback(
            feedback_id="fb_1",
            feedback_type="CORRECTION",
            content="The estimate should be $500, not $600",
            target_decision_id="dec_1",
            timestamp=time.time(),
        )
        revised, incorporated = engine.process_feedback(fb, "Cost estimate: $600")
        assert incorporated
        assert "Incorporated feedback" in revised

    def test_process_feedback_preference_not_incorporated(self) -> None:
        engine = HumanInteractionEngine()
        fb = UserFeedback(
            feedback_id="fb_2",
            feedback_type="PREFERENCE",
            content="I prefer the blue theme",
            target_decision_id="dec_2",
            timestamp=time.time(),
        )
        revised, incorporated = engine.process_feedback(fb, "Theme: dark")
        assert not incorporated
        assert revised == "Theme: dark"

    def test_process_feedback_disabled(self) -> None:
        config = InteractionConfig(feedback_enabled=False)
        engine = HumanInteractionEngine(config=config)
        fb = UserFeedback(
            feedback_id="fb_3",
            feedback_type="CORRECTION",
            content="Fix this",
            target_decision_id="dec_3",
            timestamp=time.time(),
        )
        revised, incorporated = engine.process_feedback(fb, "Original")
        assert not incorporated
        assert revised == "Original"

    # -- clarification

    def test_request_clarification(self) -> None:
        engine = HumanInteractionEngine()
        req = engine.request_clarification(
            context="User asked about model comparison",
            question="Which metric matters most: accuracy or latency?",
            options=["accuracy", "latency", "both"],
        )
        assert req.request_id.startswith("clar_")
        assert req.options == ("accuracy", "latency", "both")
        assert req.default_answer == "accuracy"
        assert not req.resolved

    def test_resolve_clarification(self) -> None:
        engine = HumanInteractionEngine()
        req = engine.request_clarification(
            context="test",
            question="A or B?",
            options=["A", "B"],
        )
        resolved = engine.resolve_clarification(req, "A")
        assert resolved.resolved
        assert resolved.request_id == req.request_id

    # -- alignment dialog

    def test_start_alignment_dialog(self) -> None:
        engine = HumanInteractionEngine()
        dialog = engine.start_alignment_dialog(
            topic="Notification frequency",
            agent_position="Notify on every event",
        )
        assert dialog.dialog_id.startswith("dialog_")
        assert dialog.topic == "Notification frequency"
        assert dialog.trust_score == 0.5
        assert dialog.outcome == "In progress"

    # -- suggest_compromise

    def test_suggest_compromise_agreement_and_disagreement(self) -> None:
        engine = HumanInteractionEngine()
        state = NegotiationState(
            negotiation_id="n_test",
            phase="CONCESSION",
            agent_proposal="Use Python",
            human_counter="Use Java",
            points_of_agreement=("Both want typed language",),
            points_of_disagreement=("Ecosystem preference",),
        )
        suggestion = engine.suggest_compromise(state)
        assert "Areas of agreement" in suggestion
        assert "Outstanding differences" in suggestion

    def test_suggest_compromise_empty(self) -> None:
        engine = HumanInteractionEngine()
        state = NegotiationState(
            negotiation_id="n_empty",
            phase="PROPOSAL",
            agent_proposal="Initial proposal",
            human_counter="",
            points_of_agreement=(),
            points_of_disagreement=(),
        )
        suggestion = engine.suggest_compromise(state)
        assert "current proposal" in suggestion.lower()

    # -- full lifecycle

    def test_full_negotiation_lifecycle(self) -> None:
        """Simulate a full negotiation from proposal to agreement."""
        engine = HumanInteractionEngine()
        state = engine.start_negotiation(
            topic="Sprint scope",
            agent_proposal="Complete 5 stories this sprint",
        )
        assert state.phase == "PROPOSAL"

        # Round 1: human counters
        state = engine.negotiate_round(
            state,
            human_response="5 is too many, can we do 3?",
            agent_concession="How about 4?",
        )
        assert state.round_count == 1

        # Round 2: agreement
        state = engine.negotiate_round(
            state,
            human_response="Yes, 4 stories sounds good, I agree",
        )
        assert state.phase == "AGREEMENT"
        assert state.round_count == 2
        assert len(state.points_of_agreement) >= 1

    # -- interaction history

    def test_interaction_history(self) -> None:
        engine = HumanInteractionEngine()
        assert engine.get_interaction_history() == []

        engine.generate_explanation(
            topic="Test",
            decision_context="ctx",
            reasoning=["reason"],
        )
        assert len(engine.get_interaction_history()) == 1

        engine.start_negotiation(topic="Test", agent_proposal="Proposal")
        assert len(engine.get_interaction_history()) == 2

    # -- get_stats

    def test_get_stats(self) -> None:
        engine = HumanInteractionEngine()

        # Generate some activity
        engine.generate_explanation(
            topic="T1",
            decision_context="ctx",
            reasoning=["r1"],
        )
        engine.generate_explanation(
            topic="T2",
            decision_context="ctx",
            reasoning=["r1"],
            level="EXPERT",
        )
        engine.start_negotiation(topic="T3", agent_proposal="p")

        stats = engine.get_stats()
        assert stats["explanations_generated"] == 2
        assert stats["negotiations_started"] == 1
        assert stats["history_size"] == 3
        assert stats["config"]["default_explanation_level"] == "INTERMEDIATE"

    def test_history_capping(self) -> None:
        config = InteractionConfig(max_context_history=2)
        engine = HumanInteractionEngine(config=config)

        engine.generate_explanation(topic="A", decision_context="ctx", reasoning=["r"])
        engine.generate_explanation(topic="B", decision_context="ctx", reasoning=["r"])
        engine.generate_explanation(topic="C", decision_context="ctx", reasoning=["r"])

        assert len(engine.get_interaction_history()) == 2
        # Only the last two remain
        assert engine.get_interaction_history()[-1]["topic"] == "C"
