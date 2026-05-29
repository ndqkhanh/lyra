"""
Tests for Socratic Questioning Mode (Phase 2)

Tests State-Challenge-Reflect protocol, intent detection,
and devil's advocate protocol.
"""

import pytest
from lyra_research.socratic.devils_advocate import (
    DevilsAdvocateProtocol,
)
from lyra_research.socratic.intent_detector import (
    IntentDetector,
)
from lyra_research.socratic.socratic_agent import (
    IntentType,
    SocraticQuestioningAgent,
    UserState,
)


class TestIntentDetector:
    """Test intent detection"""

    def test_detect_exploratory_intent(self):
        """Test detection of exploratory queries"""
        detector = IntentDetector()

        # Use queries with clear exploratory dominance
        exploratory_queries = [
            "I want to understand and explore and learn how transformers work",
            "Explain what attention mechanisms are so I can understand them",
            "I'm curious and wondering about the history of neural networks",
            "I want to learn about and understand reinforcement learning concepts",
        ]

        for query in exploratory_queries:
            intent = detector.detect(query)
            # Compare enum values to avoid pytest enum comparison issues
            assert (
                intent.type.value == IntentType.EXPLORATORY.value
            ),(
                f"Failed for query: {query}, got {intent.type.value} with indicators "
                f"{intent.indicators}"
            )
            assert intent.confidence >= 0.5

    def test_detect_goal_oriented_intent(self):
        """Test detection of goal-oriented queries"""
        detector = IntentDetector()

        goal_queries = [
            "Find and search for the best papers on transformers",
            "I need to compare and find differences between BERT and GPT",
            "Show me and get implementations of attention mechanisms",
            "Which model should I use and recommend for NLP?",
        ]

        for query in goal_queries:
            intent = detector.detect(query)
            assert intent.type.value == IntentType.GOAL_ORIENTED.value, f"Failed for query: {query}"
            assert intent.confidence > 0.5

    def test_intent_confidence_calculation(self):
        """Test confidence calculation"""
        detector = IntentDetector()

        # Strong exploratory signal (multiple keywords)
        intent = detector.detect("I want to understand and learn and explore transformers")
        assert intent.type.value == IntentType.EXPLORATORY.value
        assert intent.confidence >= 0.6

        # Mixed signals - should still detect one type
        intent = detector.detect("Find papers to help me understand transformers")
        # Should detect both but one should dominate
        assert intent.confidence > 0.0
        assert intent.type.value in [IntentType.EXPLORATORY.value, IntentType.GOAL_ORIENTED.value]

    def test_is_exploratory_helper(self):
        """Test is_exploratory helper method"""
        detector = IntentDetector()

        assert detector.is_exploratory("Help me understand transformers")
        assert not detector.is_exploratory("Find the best transformer papers")

    def test_is_goal_oriented_helper(self):
        """Test is_goal_oriented helper method"""
        detector = IntentDetector()

        assert detector.is_goal_oriented("Find the best transformer papers")
        assert not detector.is_goal_oriented("Help me understand transformers")


class TestSocraticQuestioningAgent:
    """Test Socratic questioning agent"""

    def test_engage_exploratory_query(self):
        """Test engagement with exploratory query"""
        agent = SocraticQuestioningAgent()

        dialogue = agent.engage("I want to understand how attention mechanisms work", {})

        assert dialogue.intent == IntentType.EXPLORATORY
        assert len(dialogue.turns) == 2  # state + challenge
        assert dialogue.turns[0]["type"] == "state"
        assert dialogue.turns[1]["type"] == "challenge"

    def test_engage_goal_oriented_query(self):
        """Test engagement with goal-oriented query"""
        agent = SocraticQuestioningAgent()

        dialogue = agent.engage("Find the best papers on transformers", {})

        assert dialogue.intent == IntentType.GOAL_ORIENTED
        assert len(dialogue.turns) == 1  # direct_research
        assert dialogue.turns[0]["type"] == "direct_research"

    def test_certainty_estimation(self):
        """Test certainty estimation from query"""
        agent = SocraticQuestioningAgent()

        # High certainty
        certainty = agent.estimate_certainty("Transformers are definitely the best architecture")
        assert certainty > 0.7

        # Low certainty
        certainty = agent.estimate_certainty("I'm not sure if transformers are good")
        assert certainty < 0.5

        # Medium certainty
        certainty = agent.estimate_certainty("Transformers are a good architecture")
        assert 0.4 <= certainty <= 0.6

    def test_assumption_extraction(self):
        """Test extraction of assumptions"""
        agent = SocraticQuestioningAgent()

        assumptions = agent.extract_assumptions(
            "Transformers are better because they use attention"
        )
        assert len(assumptions) > 0
        assert "attention" in assumptions[0].lower()

    def test_knowledge_gap_identification(self):
        """Test identification of knowledge gaps"""
        agent = SocraticQuestioningAgent()

        gaps = agent.identify_gaps("How do transformers work?", {})
        assert "Mechanism" in gaps[0] or "process" in gaps[0]

        gaps = agent.identify_gaps("Why are transformers effective?", {})
        assert "Causal" in gaps[0] or "rationale" in gaps[0]

    def test_challenge_generation_high_certainty(self):
        """Test challenge generation for high certainty"""
        agent = SocraticQuestioningAgent()

        state = UserState(
            query="Transformers are the best", certainty=0.9, assumptions=[], knowledge_gaps=[]
        )

        challenge = agent.generate_challenge(state)
        assert challenge.type == "contradiction"
        assert "evidence" in challenge.question.lower()

    def test_challenge_generation_low_certainty(self):
        """Test challenge generation for low certainty"""
        agent = SocraticQuestioningAgent()

        state = UserState(
            query="I'm not sure about transformers",
            certainty=0.2,
            assumptions=[],
            knowledge_gaps=["Definitional understanding"],
        )

        challenge = agent.generate_challenge(state)
        assert challenge.type == "clarification"

    def test_challenge_generation_medium_certainty(self):
        """Test challenge generation for medium certainty"""
        agent = SocraticQuestioningAgent()

        state = UserState(
            query="Transformers seem good", certainty=0.5, assumptions=[], knowledge_gaps=[]
        )

        challenge = agent.generate_challenge(state)
        assert challenge.type == "alternatives"


class TestDevilsAdvocateProtocol:
    """Test devil's advocate protocol"""

    def test_strong_rebuttal_concession(self):
        """Test concession on strong rebuttal"""
        protocol = DevilsAdvocateProtocol(concession_threshold=4)

        # Strong rebuttal with evidence and reasoning
        result = protocol.evaluate_rebuttal(
            "Transformers are always better",
(
                "However, research by Smith et al. shows that RNNs outperform transformers on"
                "sequential tasks because they maintain better temporal dependencies. The study"
                "used 10,000 samples and controlled for confounding factors."
            ),
        )

        assert result.score >= 4
        assert result.concede

    def test_weak_rebuttal_no_concession(self):
        """Test no concession on weak rebuttal"""
        protocol = DevilsAdvocateProtocol(concession_threshold=4)

        result = protocol.evaluate_rebuttal("Transformers are always better", "I disagree")

        assert result.score < 4
        assert not result.concede
        assert result.counter_rebuttal is not None

    def test_frame_lock_detection(self):
        """Test frame-lock detection (consecutive concessions)"""
        protocol = DevilsAdvocateProtocol(concession_threshold=3)  # Lower threshold

        # First strong rebuttal - should concede
        result1 = protocol.evaluate_rebuttal(
            "Claim 1",
(
                "Strong rebuttal with evidence from research study and data showing clear"
                "counter-examples with detailed reasoning because of X therefore Y"
            ),
        )
        assert result1.concede

        # Second strong rebuttal - should NOT concede (frame-lock)
        result2 = protocol.evaluate_rebuttal(
            "Claim 2",
(
                "Another strong rebuttal with evidence from research study and data showing clear"
                "counter-examples with detailed reasoning because of X therefore Y"
            ),
        )
        assert not result2.concede
        assert "frame-lock" in result2.reason.lower()

    def test_rebuttal_scoring(self):
        """Test rebuttal scoring logic"""
        protocol = DevilsAdvocateProtocol()

        # Weak rebuttal
        score = protocol.score_rebuttal("Claim", "I disagree")
        assert score == 1

        # Moderate rebuttal with reasoning
        score = protocol.score_rebuttal("Claim", "I disagree because of X")
        assert score >= 2

        # Strong rebuttal with evidence and reasoning
        score = protocol.score_rebuttal(
            "Claim",
            "Research shows that X. Therefore, Y. However, Z provides a counter-example. " * 10,
        )
        assert score >= 4

    def test_consecutive_concession_reset(self):
        """Test that consecutive concessions reset after non-concession"""
        protocol = DevilsAdvocateProtocol(concession_threshold=3)  # Lower threshold

        # First concession
        protocol.evaluate_rebuttal(
            "Claim 1",
(
                "Strong rebuttal with evidence from research study and data showing clear"
                "counter-examples with detailed reasoning because of X therefore Y"
            ),
        )

        # Weak rebuttal - resets counter
        protocol.evaluate_rebuttal("Claim 2", "Weak")

        # Another strong rebuttal - should concede (counter was reset)
        result = protocol.evaluate_rebuttal(
            "Claim 3",
(
                "Strong rebuttal with evidence from research study and data showing clear"
                "counter-examples with detailed reasoning because of X therefore Y"
            ),
        )
        assert result.concede

    def test_protocol_reset(self):
        """Test protocol reset"""
        protocol = DevilsAdvocateProtocol(concession_threshold=3)  # Lower threshold

        # Make a concession
        protocol.evaluate_rebuttal(
            "Claim",
(
                "Strong rebuttal with evidence from research study and data showing clear"
                "counter-examples with detailed reasoning because of X therefore Y"
            ),
        )

        assert len(protocol.concession_history) > 0

        # Reset
        protocol.reset()

        assert protocol.consecutive_concessions == 0
        assert len(protocol.concession_history) == 0


class TestSocraticIntegration:
    """Test integration of Socratic components"""

    def test_full_socratic_workflow(self):
        """Test complete Socratic questioning workflow"""
        agent = SocraticQuestioningAgent()
        detector = IntentDetector()
        advocate = DevilsAdvocateProtocol(concession_threshold=3)

        # Step 1: Detect intent (use stronger exploratory signal)
        query = "I want to understand and learn and explore how transformers work"
        intent = detector.detect(query)
        assert intent.type.value == IntentType.EXPLORATORY.value

        # Step 2: Engage in Socratic dialogue
        dialogue = agent.engage(query, {})
        assert dialogue.intent.value == IntentType.EXPLORATORY.value
        assert len(dialogue.turns) >= 2

        # Step 3: User responds with high certainty
        user_response = "Transformers definitely work better than RNNs"
        state = agent.extract_state(user_response, {})
        assert state.certainty > 0.7

        # Step 4: Generate challenge
        challenge = agent.generate_challenge(state)
        assert challenge.type == "contradiction"

        # Step 5: User provides rebuttal
        rebuttal =(
            "Research study by Smith shows transformers outperform RNNs because of attention"
            "mechanisms therefore they are better"
        )
        result = advocate.evaluate_rebuttal(user_response, rebuttal)

        # Should have a score and decision
        assert result.score >= 1
        assert isinstance(result.concede, bool)


if __name__ == "__main__":
    pytest.main([__file__, "-v"])
