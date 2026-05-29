"""
Unit tests for Verification System.
"""

from lyra_reasoning.types import ReasoningStep, ReasoningStrategy, ReasoningTrace, StepType
from lyra_reasoning.verification import (
    CrossAgentVerifier,
    ExternalVerifier,
    StepVerifier,
    TraceVerifier,
    VerificationSystem,
)


class TestStepVerifier:
    """Test StepVerifier functionality."""

    def test_verify_good_step(self):
        """Test verification of a good reasoning step."""
        verifier = StepVerifier()

        step = ReasoningStep(
            content="Because the evidence shows X, therefore we can conclude Y",
            step_type=StepType.ANALYSIS,
        )

        score = verifier.verify(step)

        assert 0.0 <= score <= 1.0
        assert score > 0.5  # Should be reasonably high

    def test_verify_poor_step(self):
        """Test verification of a poor reasoning step."""
        verifier = StepVerifier()

        step = ReasoningStep(
            content="Maybe",  # Too short, no reasoning
            step_type=StepType.ANALYSIS,
        )

        score = verifier.verify(step)

        assert 0.0 <= score <= 1.0
        assert score < 0.5  # Should be low

    def test_verify_with_reasoning_indicators(self):
        """Test that reasoning indicators improve score."""
        verifier = StepVerifier()

        step_with_indicators = ReasoningStep(
            content="Given the hypothesis that X, and the evidence showing Y, "
            "we can therefore conclude Z because of the logical connection",
            step_type=StepType.ANALYSIS,
        )

        step_without_indicators = ReasoningStep(
            content="X and Y lead to Z in some way",
            step_type=StepType.ANALYSIS,
        )

        score_with = verifier.verify(step_with_indicators)
        score_without = verifier.verify(step_without_indicators)

        assert score_with > score_without


class TestTraceVerifier:
    """Test TraceVerifier functionality."""

    def test_verify_empty_trace(self):
        """Test verification of empty trace."""
        verifier = TraceVerifier()

        trace = ReasoningTrace(
            task="Test",
            strategy=ReasoningStrategy.CHAIN_OF_THOUGHT,
            steps=[],
        )

        score = verifier.verify(trace)

        assert score == 0.0

    def test_verify_complete_trace(self):
        """Test verification of complete trace."""
        verifier = TraceVerifier()

        trace = ReasoningTrace(
            task="Test",
            strategy=ReasoningStrategy.CHAIN_OF_THOUGHT,
            steps=[
                ReasoningStep(
                    content="Hypothesis", step_type=StepType.HYPOTHESIS, verification_score=0.8
                ),
                ReasoningStep(
                    content="Evidence", step_type=StepType.EVIDENCE, verification_score=0.9
                ),
                ReasoningStep(
                    content="Analysis", step_type=StepType.ANALYSIS, verification_score=0.85
                ),
                ReasoningStep(
                    content="Conclusion", step_type=StepType.CONCLUSION, verification_score=0.9
                ),
            ],
        )

        score = verifier.verify(trace)

        assert 0.0 <= score <= 1.0
        assert score > 0.5  # Complete trace should score well

    def test_verify_incomplete_trace(self):
        """Test verification of incomplete trace."""
        verifier = TraceVerifier()

        trace = ReasoningTrace(
            task="Test",
            strategy=ReasoningStrategy.CHAIN_OF_THOUGHT,
            steps=[
                ReasoningStep(
                    content="Hypothesis", step_type=StepType.HYPOTHESIS, verification_score=0.8
                ),
                # Missing evidence, analysis, conclusion
            ],
        )

        score = verifier.verify(trace)

        assert 0.0 <= score <= 1.0
        # Incomplete trace should score lower than complete


class TestExternalVerifier:
    """Test ExternalVerifier functionality."""

    def test_verify_claim_with_citation(self):
        """Test verification of claim with citation."""
        verifier = ExternalVerifier()

        claim = "According to Smith et al. [2023], the result is X"
        score = verifier.verify(claim)

        assert 0.0 <= score <= 1.0
        assert score > 0.5  # Citations should improve score

    def test_verify_claim_without_citation(self):
        """Test verification of claim without citation."""
        verifier = ExternalVerifier()

        claim = "The result is probably X"
        score = verifier.verify(claim)

        assert 0.0 <= score <= 1.0

    def test_verify_specific_claim(self):
        """Test that specific claims score higher."""
        verifier = ExternalVerifier()

        specific_claim = "The temperature increased by 2.5 degrees Celsius"
        vague_claim = "The temperature increased somewhat"

        specific_score = verifier.verify(specific_claim)
        vague_score = verifier.verify(vague_claim)

        assert specific_score > vague_score


class TestCrossAgentVerifier:
    """Test CrossAgentVerifier functionality."""

    def test_verify_trace(self):
        """Test cross-agent verification."""
        verifier = CrossAgentVerifier()

        trace = ReasoningTrace(
            task="Test",
            strategy=ReasoningStrategy.CHAIN_OF_THOUGHT,
            steps=[
                ReasoningStep(
                    content="Step 1", step_type=StepType.HYPOTHESIS, verification_score=0.8
                ),
                ReasoningStep(
                    content="Step 2", step_type=StepType.EVIDENCE, verification_score=0.9
                ),
            ],
        )

        scores = verifier.verify(trace, num_verifiers=3)

        assert len(scores) == 3
        assert all(0.0 <= score <= 1.0 for score in scores)

    def test_verify_with_different_verifier_counts(self):
        """Test verification with different numbers of verifiers."""
        verifier = CrossAgentVerifier()

        trace = ReasoningTrace(
            task="Test",
            strategy=ReasoningStrategy.CHAIN_OF_THOUGHT,
            steps=[
                ReasoningStep(
                    content="Step", step_type=StepType.HYPOTHESIS, verification_score=0.8
                ),
            ],
        )

        scores_3 = verifier.verify(trace, num_verifiers=3)
        scores_5 = verifier.verify(trace, num_verifiers=5)

        assert len(scores_3) == 3
        assert len(scores_5) == 5


class TestVerificationSystem:
    """Test VerificationSystem functionality."""

    def test_initialization(self):
        """Test verification system initialization."""
        system = VerificationSystem()

        assert system.step_verifier is not None
        assert system.trace_verifier is not None
        assert system.external_verifier is not None
        assert system.cross_agent_verifier is not None

    def test_verify_complete_trace(self):
        """Test verification of complete trace."""
        system = VerificationSystem()

        trace = ReasoningTrace(
            task="Test task",
            strategy=ReasoningStrategy.CHAIN_OF_THOUGHT,
            steps=[
                ReasoningStep(
                    content="Initial hypothesis based on the problem",
                    step_type=StepType.HYPOTHESIS,
                ),
                ReasoningStep(
                    content="Evidence from research shows X",
                    step_type=StepType.EVIDENCE,
                ),
                ReasoningStep(
                    content="Analysis of the evidence indicates Y",
                    step_type=StepType.ANALYSIS,
                ),
                ReasoningStep(
                    content="Therefore, we conclude Z",
                    step_type=StepType.CONCLUSION,
                ),
            ],
        )

        result = system.verify(trace)

        assert 0.0 <= result.overall_score <= 1.0
        assert len(result.step_scores) == 4
        assert result.trace_score >= 0.0
        assert isinstance(result.passed, bool)

    def test_verify_with_external_disabled(self):
        """Test verification with external verification disabled."""
        system = VerificationSystem()

        trace = ReasoningTrace(
            task="Test",
            strategy=ReasoningStrategy.CHAIN_OF_THOUGHT,
            steps=[
                ReasoningStep(content="Step", step_type=StepType.HYPOTHESIS),
            ],
        )

        result = system.verify(trace, enable_external=False)

        assert result.external_scores == []

    def test_verify_with_cross_agent_disabled(self):
        """Test verification with cross-agent verification disabled."""
        system = VerificationSystem()

        trace = ReasoningTrace(
            task="Test",
            strategy=ReasoningStrategy.CHAIN_OF_THOUGHT,
            steps=[
                ReasoningStep(content="Step", step_type=StepType.HYPOTHESIS),
            ],
        )

        result = system.verify(trace, enable_cross_agent=False)

        assert result.cross_agent_scores == []

    def test_verification_passed_threshold(self):
        """Test that verification passed is based on threshold."""
        system = VerificationSystem()

        # Create a high-quality trace
        good_trace = ReasoningTrace(
            task="Test",
            strategy=ReasoningStrategy.CHAIN_OF_THOUGHT,
            steps=[
                ReasoningStep(
                    content="Well-reasoned hypothesis because of X",
                    step_type=StepType.HYPOTHESIS,
                    verification_score=0.9,
                ),
                ReasoningStep(
                    content="Strong evidence from research [2023]",
                    step_type=StepType.EVIDENCE,
                    verification_score=0.95,
                ),
                ReasoningStep(
                    content="Thorough analysis therefore shows Y",
                    step_type=StepType.ANALYSIS,
                    verification_score=0.9,
                ),
                ReasoningStep(
                    content="Clear conclusion based on evidence",
                    step_type=StepType.CONCLUSION,
                    verification_score=0.92,
                ),
            ],
        )

        result = system.verify(good_trace)

        # High-quality trace should pass
        assert result.overall_score >= 0.7
        assert result.passed is True

    def test_verification_details(self):
        """Test that verification includes detailed metrics."""
        system = VerificationSystem()

        trace = ReasoningTrace(
            task="Test",
            strategy=ReasoningStrategy.CHAIN_OF_THOUGHT,
            steps=[
                ReasoningStep(
                    content="Step 1", step_type=StepType.HYPOTHESIS, verification_score=0.8
                ),
                ReasoningStep(
                    content="Step 2", step_type=StepType.EVIDENCE, verification_score=0.9
                ),
            ],
        )

        result = system.verify(trace)

        assert "avg_step_score" in result.details
        assert "avg_external_score" in result.details
        assert "avg_cross_agent_score" in result.details
