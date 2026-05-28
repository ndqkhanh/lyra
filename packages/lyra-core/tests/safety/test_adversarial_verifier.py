"""Tests for Cross-Model Adversarial Verifier."""

from __future__ import annotations

import pytest
from lyra_core.safety.adversarial_verifier import (
    AdversarialVerdict,
    AdversarialVerdictType,
    AdversarialVerifier,
    ModelFamily,
    ModelVote,
    VerificationRequest,
    _aggregate_votes,
    _calculate_consensus_level,
    _parse_model_response,
)
from lyra_core.safety.approval_gate import (
    GateAction,
    GateDecision,
    RiskClassification,
    RiskLevel,
    RiskSurface,
)

# ── Mock Model Provider ────────────────────────────────────────────────


class MockModelProvider:
    """Mock model provider for testing."""

    def __init__(self, responses: dict[str, str]):
        """Initialize with predefined responses per model."""
        self.responses = responses
        self.call_count = 0

    async def invoke(
        self,
        prompt: str,
        model_name: str,
        temperature: float = 0.1,
        max_tokens: int = 1000,
    ) -> str:
        """Return predefined response for the model."""
        self.call_count += 1
        return self.responses.get(model_name, "VERDICT: UNCERTAIN\nCONFIDENCE: 0.5\nREASONING: Unknown")


# ── Test Fixtures ──────────────────────────────────────────────────────


@pytest.fixture
def risk_classification() -> RiskClassification:
    """Create a sample risk classification."""
    return RiskClassification(
        level=RiskLevel.HIGH,
        surface=RiskSurface.FILE_SYSTEM,
        confidence=0.9,
        reasoning_flags=(),
        requires_adversarial=True,
        detail="Deleting files in /tmp",
    )


@pytest.fixture
def gate_decision(risk_classification: RiskClassification) -> GateDecision:
    """Create a sample gate decision."""
    return GateDecision(
        action=GateAction.CONFIRM,
        risk=risk_classification,
        gate_id="gate-test123",
    )


@pytest.fixture
def verification_request(
    risk_classification: RiskClassification,
    gate_decision: GateDecision,
) -> VerificationRequest:
    """Create a sample verification request."""
    return VerificationRequest(
        action_description="rm -rf /tmp/cache",
        parameters={"path": "/tmp/cache"},
        risk_classification=risk_classification,
        gate_decision=gate_decision,
        context="User requested cleanup of temporary files",
    )


# ── Unit Tests ─────────────────────────────────────────────────────────


def test_model_vote_confidence_clamping():
    """Test that ModelVote clamps confidence to [0.0, 1.0]."""
    vote = ModelVote(
        model_name="test-model",
        model_family=ModelFamily.SONNET,
        verdict=AdversarialVerdictType.APPROVE,
        confidence=1.5,  # Out of range
        reasoning="Test",
    )
    assert vote.confidence == 1.0

    vote2 = ModelVote(
        model_name="test-model",
        model_family=ModelFamily.SONNET,
        verdict=AdversarialVerdictType.APPROVE,
        confidence=-0.5,  # Out of range
        reasoning="Test",
    )
    assert vote2.confidence == 0.0


def test_parse_model_response():
    """Test parsing of model responses."""
    response = """VERDICT: APPROVE
CONFIDENCE: 0.95
REASONING: The action is safe because it only affects temporary files."""

    vote = _parse_model_response(response, "claude-opus-4", ModelFamily.OPUS)

    assert vote.verdict == AdversarialVerdictType.APPROVE
    assert vote.confidence == 0.95
    assert "safe" in vote.reasoning.lower()
    assert vote.model_name == "claude-opus-4"
    assert vote.model_family == ModelFamily.OPUS


def test_parse_model_response_malformed():
    """Test parsing of malformed responses falls back gracefully."""
    response = "This is not a properly formatted response"

    vote = _parse_model_response(response, "test-model", ModelFamily.HAIKU)

    assert vote.verdict == AdversarialVerdictType.UNCERTAIN
    assert vote.confidence == 0.5
    assert vote.reasoning == response


def test_calculate_consensus_level_unanimous():
    """Test consensus calculation for unanimous votes."""
    votes = (
        ModelVote("m1", ModelFamily.OPUS, AdversarialVerdictType.APPROVE, 0.9, "r1"),
        ModelVote("m2", ModelFamily.SONNET, AdversarialVerdictType.APPROVE, 0.8, "r2"),
        ModelVote("m3", ModelFamily.HAIKU, AdversarialVerdictType.APPROVE, 0.85, "r3"),
    )

    consensus = _calculate_consensus_level(votes)
    assert consensus == 1.0


def test_calculate_consensus_level_majority():
    """Test consensus calculation for 2/3 majority."""
    votes = (
        ModelVote("m1", ModelFamily.OPUS, AdversarialVerdictType.APPROVE, 0.9, "r1"),
        ModelVote("m2", ModelFamily.SONNET, AdversarialVerdictType.APPROVE, 0.8, "r2"),
        ModelVote("m3", ModelFamily.HAIKU, AdversarialVerdictType.DENY, 0.85, "r3"),
    )

    consensus = _calculate_consensus_level(votes)
    assert consensus == 0.67


def test_calculate_consensus_level_no_majority():
    """Test consensus calculation when all votes differ."""
    votes = (
        ModelVote("m1", ModelFamily.OPUS, AdversarialVerdictType.APPROVE, 0.9, "r1"),
        ModelVote("m2", ModelFamily.SONNET, AdversarialVerdictType.DENY, 0.8, "r2"),
        ModelVote("m3", ModelFamily.HAIKU, AdversarialVerdictType.UNCERTAIN, 0.85, "r3"),
    )

    consensus = _calculate_consensus_level(votes)
    assert consensus == 0.33


def test_aggregate_votes_unanimous_approve():
    """Test vote aggregation with unanimous APPROVE."""
    votes = (
        ModelVote("m1", ModelFamily.OPUS, AdversarialVerdictType.APPROVE, 0.9, "r1"),
        ModelVote("m2", ModelFamily.SONNET, AdversarialVerdictType.APPROVE, 0.95, "r2"),
        ModelVote("m3", ModelFamily.HAIKU, AdversarialVerdictType.APPROVE, 0.85, "r3"),
    )

    final_verdict, confidence, reasoning = _aggregate_votes(votes)

    assert final_verdict == AdversarialVerdictType.APPROVE
    assert 0.85 <= confidence <= 0.95
    assert "Adversarial verification" in reasoning


def test_aggregate_votes_majority_deny():
    """Test vote aggregation with 2/3 DENY majority."""
    votes = (
        ModelVote("m1", ModelFamily.OPUS, AdversarialVerdictType.DENY, 0.9, "r1"),
        ModelVote("m2", ModelFamily.SONNET, AdversarialVerdictType.DENY, 0.85, "r2"),
        ModelVote("m3", ModelFamily.HAIKU, AdversarialVerdictType.APPROVE, 0.7, "r3"),
    )

    final_verdict, confidence, reasoning = _aggregate_votes(votes)

    assert final_verdict == AdversarialVerdictType.DENY
    assert "Dissenting opinions" in reasoning


def test_aggregate_votes_weighted():
    """Test that vote aggregation uses confidence weighting."""
    # High-confidence DENY should win over low-confidence APPROVE
    votes = (
        ModelVote("m1", ModelFamily.OPUS, AdversarialVerdictType.DENY, 0.95, "r1"),
        ModelVote("m2", ModelFamily.SONNET, AdversarialVerdictType.APPROVE, 0.3, "r2"),
        ModelVote("m3", ModelFamily.HAIKU, AdversarialVerdictType.APPROVE, 0.4, "r3"),
    )

    final_verdict, confidence, reasoning = _aggregate_votes(votes)

    # DENY should win due to higher confidence weight
    assert final_verdict == AdversarialVerdictType.DENY


def test_adversarial_verdict_validation():
    """Test that AdversarialVerdict validates vote count."""
    votes = (
        ModelVote("m1", ModelFamily.OPUS, AdversarialVerdictType.APPROVE, 0.9, "r1"),
        ModelVote("m2", ModelFamily.SONNET, AdversarialVerdictType.APPROVE, 0.8, "r2"),
        ModelVote("m3", ModelFamily.HAIKU, AdversarialVerdictType.APPROVE, 0.85, "r3"),
    )

    verdict = AdversarialVerdict(
        verdict_id="test-123",
        votes=votes,
        final_verdict=AdversarialVerdictType.APPROVE,
        confidence=0.88,
        consensus_level=1.0,
        reasoning_summary="Test",
        requires_escalation=False,
        total_latency_ms=100.0,
    )

    assert len(verdict.votes) == 3

    # Test that invalid vote count raises error
    with pytest.raises(ValueError, match="exactly 3 votes"):
        AdversarialVerdict(
            verdict_id="test-456",
            votes=(votes[0], votes[1]),  # Only 2 votes
            final_verdict=AdversarialVerdictType.APPROVE,
            confidence=0.88,
            consensus_level=1.0,
            reasoning_summary="Test",
            requires_escalation=False,
            total_latency_ms=100.0,
        )


@pytest.mark.asyncio
async def test_adversarial_verifier_unanimous_approve(verification_request: VerificationRequest):
    """Test verifier with unanimous APPROVE votes."""
    mock_provider = MockModelProvider({
        "claude-opus-4": "VERDICT: APPROVE\nCONFIDENCE: 0.9\nREASONING: Safe operation",
        "claude-sonnet-4": "VERDICT: APPROVE\nCONFIDENCE: 0.85\nREASONING: Acceptable risk",
        "claude-haiku-4": "VERDICT: APPROVE\nCONFIDENCE: 0.8\nREASONING: Within bounds",
    })

    verifier = AdversarialVerifier(model_provider=mock_provider)
    verdict = await verifier.verify(verification_request)

    assert verdict.final_verdict == AdversarialVerdictType.APPROVE
    assert verdict.consensus_level == 1.0
    assert len(verdict.votes) == 3
    assert mock_provider.call_count == 3
    assert not verdict.requires_escalation  # High confidence, high consensus


@pytest.mark.asyncio
async def test_adversarial_verifier_majority_deny(verification_request: VerificationRequest):
    """Test verifier with 2/3 DENY majority."""
    mock_provider = MockModelProvider({
        "claude-opus-4": "VERDICT: DENY\nCONFIDENCE: 0.95\nREASONING: Too risky",
        "claude-sonnet-4": "VERDICT: DENY\nCONFIDENCE: 0.9\nREASONING: Dangerous operation",
        "claude-haiku-4": "VERDICT: APPROVE\nCONFIDENCE: 0.6\nREASONING: Seems okay",
    })

    verifier = AdversarialVerifier(model_provider=mock_provider)
    verdict = await verifier.verify(verification_request)

    assert verdict.final_verdict == AdversarialVerdictType.DENY
    assert verdict.consensus_level == 0.67
    assert len(verdict.votes) == 3


@pytest.mark.asyncio
async def test_adversarial_verifier_escalation_low_confidence(verification_request: VerificationRequest):
    """Test that low confidence triggers escalation."""
    mock_provider = MockModelProvider({
        "claude-opus-4": "VERDICT: APPROVE\nCONFIDENCE: 0.5\nREASONING: Uncertain",
        "claude-sonnet-4": "VERDICT: APPROVE\nCONFIDENCE: 0.4\nREASONING: Not sure",
        "claude-haiku-4": "VERDICT: APPROVE\nCONFIDENCE: 0.45\nREASONING: Maybe okay",
    })

    verifier = AdversarialVerifier(
        model_provider=mock_provider,
        escalation_threshold=0.7,
    )
    verdict = await verifier.verify(verification_request)

    assert verdict.requires_escalation  # Low confidence should trigger escalation


@pytest.mark.asyncio
async def test_adversarial_verifier_escalation_low_consensus(verification_request: VerificationRequest):
    """Test that low consensus triggers escalation."""
    mock_provider = MockModelProvider({
        "claude-opus-4": "VERDICT: APPROVE\nCONFIDENCE: 0.9\nREASONING: Safe",
        "claude-sonnet-4": "VERDICT: DENY\nCONFIDENCE: 0.85\nREASONING: Risky",
        "claude-haiku-4": "VERDICT: UNCERTAIN\nCONFIDENCE: 0.5\nREASONING: Unknown",
    })

    verifier = AdversarialVerifier(
        model_provider=mock_provider,
        consensus_threshold=0.67,
    )
    verdict = await verifier.verify(verification_request)

    assert verdict.consensus_level == 0.33  # No majority
    assert verdict.requires_escalation


@pytest.mark.asyncio
async def test_adversarial_verifier_history(verification_request: VerificationRequest):
    """Test that verifier maintains history."""
    mock_provider = MockModelProvider({
        "claude-opus-4": "VERDICT: APPROVE\nCONFIDENCE: 0.9\nREASONING: Safe",
        "claude-sonnet-4": "VERDICT: APPROVE\nCONFIDENCE: 0.85\nREASONING: Okay",
        "claude-haiku-4": "VERDICT: APPROVE\nCONFIDENCE: 0.8\nREASONING: Good",
    })

    verifier = AdversarialVerifier(model_provider=mock_provider)

    assert len(verifier.history) == 0

    await verifier.verify(verification_request)
    assert len(verifier.history) == 1

    await verifier.verify(verification_request)
    assert len(verifier.history) == 2

    verifier.clear_history()
    assert len(verifier.history) == 0


@pytest.mark.asyncio
async def test_adversarial_verifier_accuracy_metrics(verification_request: VerificationRequest):
    """Test accuracy metrics calculation."""
    mock_provider = MockModelProvider({
        "claude-opus-4": "VERDICT: APPROVE\nCONFIDENCE: 0.9\nREASONING: Safe",
        "claude-sonnet-4": "VERDICT: APPROVE\nCONFIDENCE: 0.85\nREASONING: Okay",
        "claude-haiku-4": "VERDICT: APPROVE\nCONFIDENCE: 0.8\nREASONING: Good",
    })

    verifier = AdversarialVerifier(model_provider=mock_provider)

    # No history yet
    metrics = verifier.get_accuracy_metrics()
    assert metrics["approval_rate"] == 0.0

    # Add some verdicts
    await verifier.verify(verification_request)
    await verifier.verify(verification_request)

    metrics = verifier.get_accuracy_metrics()
    assert metrics["approval_rate"] == 1.0
    assert metrics["denial_rate"] == 0.0
    assert metrics["avg_confidence"] > 0.8
    assert metrics["avg_consensus"] == 1.0


def test_adversarial_verifier_sync_wrapper(verification_request: VerificationRequest):
    """Test synchronous wrapper for verify()."""
    mock_provider = MockModelProvider({
        "claude-opus-4": "VERDICT: APPROVE\nCONFIDENCE: 0.9\nREASONING: Safe",
        "claude-sonnet-4": "VERDICT: APPROVE\nCONFIDENCE: 0.85\nREASONING: Okay",
        "claude-haiku-4": "VERDICT: APPROVE\nCONFIDENCE: 0.8\nREASONING: Good",
    })

    verifier = AdversarialVerifier(model_provider=mock_provider)
    verdict = verifier.verify_sync(verification_request)

    assert verdict.final_verdict == AdversarialVerdictType.APPROVE
    assert len(verdict.votes) == 3
