"""Tests for the lyra_privacy package."""

from __future__ import annotations

from lyra_privacy import (
    AttestationProof,
    DPQueryResult,
    FederatedAggregation,
    FederatedUpdate,
    PrivacyBudget,
    PrivacyBudgetStatus,
    PrivacyConfig,
    PrivacyPreservingAgent,
)


# Data class tests


def test_privacy_budget_status_enum():
    """Test PrivacyBudgetStatus enum values."""
    assert PrivacyBudgetStatus.AVAILABLE.value == "AVAILABLE"
    assert PrivacyBudgetStatus.DEPLETED.value == "DEPLETED"
    assert PrivacyBudgetStatus.WARNING.value == "WARNING"
    assert PrivacyBudgetStatus.EXCEEDED.value == "EXCEEDED"


def test_attestation_proof_defaults():
    """Test AttestationProof defaults."""
    proof = AttestationProof(
        proof_id="p1",
        enclave_type="SGX",
        measurements=(("key", "value"),),
        timestamp=1234567890.0,
    )
    assert proof.proof_id == "p1"
    assert proof.enclave_type == "SGX"
    assert proof.measurements == (("key", "value"),)
    assert proof.timestamp == 1234567890.0
    assert proof.verified is False
    assert proof.issuer == ""


def test_attestation_proof_custom():
    """Test AttestationProof with custom values."""
    proof = AttestationProof(
        proof_id="p2",
        enclave_type="TDX",
        measurements=(("hash", "abc"), ("sig", "def")),
        timestamp=1234567890.0,
        verified=True,
        issuer="enclave-1",
    )
    assert proof.verified is True
    assert proof.issuer == "enclave-1"


def test_privacy_budget_defaults():
    """Test PrivacyBudget defaults."""
    budget = PrivacyBudget(epsilon=1.0, delta=1e-5)
    assert budget.epsilon == 1.0
    assert budget.delta == 1e-5
    assert budget.total_spent_epsilon == 0.0
    assert budget.queries_remaining == 1000
    assert budget.status == "AVAILABLE"
    assert budget.per_user_limits == ()


def test_privacy_budget_custom():
    """Test PrivacyBudget with custom values."""
    budget = PrivacyBudget(
        epsilon=5.0,
        delta=1e-6,
        total_spent_epsilon=2.0,
        queries_remaining=500,
        status="WARNING",
        per_user_limits=(("user1", 3.0), ("user2", 1.0)),
    )
    assert budget.epsilon == 5.0
    assert budget.total_spent_epsilon == 2.0
    assert budget.per_user_limits == (("user1", 3.0), ("user2", 1.0))


def test_dp_query_result():
    """Test DPQueryResult creation."""
    result = DPQueryResult(
        success=True,
        result="abc123",
        noise_scale=1.5,
        epsilon_spent=0.1,
        budget_remaining=0.9,
        privacy_accounting={"epsilon": 0.1, "mechanism": "gaussian"},
    )
    assert result.success is True
    assert result.result == "abc123"
    assert result.epsilon_spent == 0.1
    assert result.privacy_accounting["mechanism"] == "gaussian"


def test_federated_update():
    """Test FederatedUpdate creation."""
    update = FederatedUpdate(
        update_id="u1",
        source_agent="agent-1",
        knowledge_graph_delta={"key1": "value1"},
        encryption_metadata=(("algo", "AES"),),
        differential_privacy_applied=True,
        epsilon_spent=0.05,
    )
    assert update.update_id == "u1"
    assert update.differential_privacy_applied is True
    assert update.epsilon_spent == 0.05


def test_federated_aggregation():
    """Test FederatedAggregation creation."""
    aggregation = FederatedAggregation(
        round_id="r1",
        contributing_agents=("agent-1", "agent-2"),
        aggregated_knowledge={"key": "value"},
        total_epsilon=0.1,
        convergence_score=0.85,
    )
    assert aggregation.round_id == "r1"
    assert aggregation.convergence_score == 0.85


def test_privacy_config_defaults():
    """Test PrivacyConfig defaults."""
    config = PrivacyConfig()
    assert config.confidential_inference_enabled is True
    assert config.differential_privacy_enabled is True
    assert config.federated_learning_enabled is True
    assert config.default_epsilon == 1.0
    assert config.default_delta == 1e-5
    assert config.max_queries_per_user == 1000
    assert config.noise_mechanism == "gaussian"
    assert config.min_contributing_agents == 3


def test_privacy_config_custom():
    """Test PrivacyConfig with custom values."""
    config = PrivacyConfig(
        confidential_inference_enabled=False,
        differential_privacy_enabled=False,
        default_epsilon=0.5,
        min_contributing_agents=2,
    )
    assert config.confidential_inference_enabled is False
    assert config.default_epsilon == 0.5
    assert config.min_contributing_agents == 2


def test_data_classes_are_frozen():
    """Test that data classes cannot be mutated."""
    proof = AttestationProof(
        proof_id="p1",
        enclave_type="SGX",
        measurements=(),
        timestamp=1.0,
    )
    # Frozen dataclasses raise FrozenInstanceError (subclass of AttributeError)
    # on attribute assignment
    import dataclasses
    assert dataclasses.is_dataclass(proof)
    import pytest
    with pytest.raises(AttributeError):
        proof.proof_id = "modified"  # type: ignore[misc]


# PrivacyPreservingAgent tests


def test_agent_init_default():
    """Test agent initialization with default config."""
    agent = PrivacyPreservingAgent()
    assert agent.agent_id.startswith("agent_")
    assert getattr(agent, "_total_queries") == 0
    assert getattr(agent, "_total_epsilon_spent") == 0.0
    assert getattr(agent, "_total_federated_rounds") == 0
    assert getattr(agent, "_total_attestations") == 0


def test_agent_init_custom():
    """Test agent initialization with custom config and agent_id."""
    config = PrivacyConfig(
        confidential_inference_enabled=False,
        differential_privacy_enabled=False,
        federated_learning_enabled=False,
        min_contributing_agents=2,
    )
    agent = PrivacyPreservingAgent(config=config, agent_id="custom-agent")
    assert agent.agent_id == "custom-agent"
    assert agent.config.min_contributing_agents == 2


def test_secure_infer_produces_signed_result():
    """Test secure_infer returns a signed result with attestation."""
    agent = PrivacyPreservingAgent(agent_id="test-agent")
    result = agent.secure_infer("What is the capital of France?")

    assert "content" in result
    assert "content_hash" in result
    assert "agent_id" in result
    assert "timestamp" in result
    assert "signature" in result
    assert "attestation" in result
    assert result["agent_id"] == "test-agent"


def test_secure_infer_with_context():
    """Test secure_infer with context."""
    agent = PrivacyPreservingAgent(agent_id="test-agent")
    context = {"session": "test", "user_id": "user-1"}
    result = agent.secure_infer("Hello", context=context)
    assert result["agent_id"] == "test-agent"


def test_generate_and_verify_attestation():
    """Test attestation generation and verification."""
    agent = PrivacyPreservingAgent(agent_id="attest-agent")
    result = agent.secure_infer("Test prompt")

    proof = agent.generate_attestation(result)
    assert isinstance(proof, AttestationProof)
    assert proof.issuer == "attest-agent"
    assert len(proof.proof_id) == 16
    assert proof.verified is False

    verified = agent.verify_attestation(proof)
    assert verified is True


def test_verify_attestation_bad_proof():
    """Test that verification fails for a tampered proof."""
    agent = PrivacyPreservingAgent(agent_id="attest-agent")
    result = agent.secure_infer("Test prompt")
    proof = agent.generate_attestation(result)

    # Modify measurements to simulate tampering — change content_hash value
    # so the recomputed attestation_hash won't match the stored one
    bad_measurements = (
        ("content_hash", "tampered_hash_value"),
        ("signature", proof.measurements[1][1]),
        ("attestation_hash", proof.measurements[2][1]),
    )
    bad_proof = AttestationProof(
        proof_id=proof.proof_id,
        enclave_type=proof.enclave_type,
        measurements=bad_measurements,
        timestamp=proof.timestamp,
        verified=proof.verified,
        issuer=proof.issuer,
    )
    assert agent.verify_attestation(bad_proof) is False


def test_query_with_dp_tracks_epsilon():
    """Test that DP queries track epsilon spending."""
    agent = PrivacyPreservingAgent(
        config=PrivacyConfig(
            default_epsilon=1.0,
            max_queries_per_user=10,
        ),
        agent_id="dp-agent",
    )

    result = agent.query_with_dp("SELECT count(*) FROM users", "dataset-1")
    assert result.success is True
    assert result.epsilon_spent > 0.0
    assert result.noise_scale > 0.0
    assert "epsilon_budget" in result.privacy_accounting
    assert "total_spent" in result.privacy_accounting


def test_query_with_dp_budget_depletion():
    """Test that DP budget depletion returns DEPLETED status."""
    agent = PrivacyPreservingAgent(
        config=PrivacyConfig(default_epsilon=0.01, max_queries_per_user=5),
        agent_id="depletion-agent",
    )

    results = []
    for _ in range(10):
        results.append(
            agent.query_with_dp("SELECT * FROM users", "dataset-1")
        )

    succeeds = [r for r in results if r.success]
    fails = [r for r in results if not r.success]

    assert len(fails) >= 1
    for failed in fails:
        assert failed.privacy_accounting["status"] == "DEPLETED"
        assert failed.budget_remaining == 0.0


def test_get_privacy_budget():
    """Test get_privacy_budget returns correct state."""
    agent = PrivacyPreservingAgent(
        config=PrivacyConfig(default_epsilon=1.0),
        agent_id="budget-agent",
    )

    budget = agent.get_privacy_budget()
    assert budget.epsilon == 1.0
    assert budget.total_spent_epsilon == 0.0
    assert budget.status == "AVAILABLE"

    agent.query_with_dp("SELECT * FROM users", "dataset-1")
    budget_after = agent.get_privacy_budget()
    assert budget_after.total_spent_epsilon > 0.0


def test_create_federated_update():
    """Test federated update creation with DP."""
    agent = PrivacyPreservingAgent(agent_id="fl-agent")
    knowledge_delta = {
        "intent": "greeting",
        "confidence": 0.95,
        "frequency": 42,
    }

    update = agent.create_federated_update(knowledge_delta)
    assert update.source_agent == "fl-agent"
    assert update.differential_privacy_applied is True
    assert update.epsilon_spent > 0.0
    assert len(update.encryption_metadata) > 0


def test_federated_update_no_dp():
    """Test federated update without DP."""
    config = PrivacyConfig(differential_privacy_enabled=False)
    agent = PrivacyPreservingAgent(config=config, agent_id="fl-no-dp")
    update = agent.create_federated_update({"key": "value"})
    assert update.differential_privacy_applied is False
    assert update.epsilon_spent == 0.0


def test_aggregate_updates():
    """Test aggregation of federated updates."""
    config = PrivacyConfig(min_contributing_agents=2)
    agent1 = PrivacyPreservingAgent(config=config, agent_id="agent-a")
    agent2 = PrivacyPreservingAgent(config=config, agent_id="agent-b")

    update1 = agent1.create_federated_update(
        {"confidence": 0.9, "intent": "greeting"}
    )
    update2 = agent2.create_federated_update(
        {"confidence": 0.8, "intent": "greeting"}
    )

    agg = agent1.aggregate_updates([update1, update2])
    assert agg.round_id is not None
    assert "agent-a" in agg.contributing_agents
    assert "agent-b" in agg.contributing_agents
    assert agg.convergence_score > 0.0
    assert agg.total_epsilon > 0.0
    assert "confidence" in agg.aggregated_knowledge
    # Average of 0.9 and 0.8 — should be close to 0.85 with small noise
    assert 0.5 < agg.aggregated_knowledge["confidence"] < 1.2
    assert "intent" in agg.aggregated_knowledge


def test_aggregate_updates_below_threshold():
    """Test aggregation fails below min_contributing_agents."""
    config = PrivacyConfig(min_contributing_agents=3)
    agent = PrivacyPreservingAgent(config=config, agent_id="single")

    update = agent.create_federated_update({"key": "value"})

    import pytest
    with pytest.raises(ValueError, match="Need at least 3"):
        agent.aggregate_updates([update])


def test_get_stats():
    """Test get_stats returns correct aggregate statistics."""
    config = PrivacyConfig(min_contributing_agents=2)
    agent = PrivacyPreservingAgent(config=config, agent_id="stats-agent")
    stats = agent.get_stats()

    assert stats["agent_id"] == "stats-agent"
    assert stats["total_queries"] == 0
    assert stats["total_epsilon_spent"] == 0.0
    assert stats["total_federated_rounds"] == 0
    assert stats["total_attestations"] == 0

    agent.secure_infer("test")
    agent.query_with_dp("SELECT 1", "ds-1")
    agent.create_federated_update({"test": 1})
    update1 = agent.create_federated_update({"a": 1})
    update2 = PrivacyPreservingAgent(
        agent_id="other"
    ).create_federated_update({"a": 2})
    agent.aggregate_updates([update1, update2])

    stats_after = agent.get_stats()
    assert stats_after["total_queries"] >= 1
    assert stats_after["total_epsilon_spent"] > 0.0
    assert stats_after["total_federated_rounds"] == 1
    assert stats_after["total_attestations"] >= 1


def test_secure_infer_no_attestation_when_disabled():
    """Test secure_infer skips attestation when confidential inference is off."""
    config = PrivacyConfig(confidential_inference_enabled=False)
    agent = PrivacyPreservingAgent(config=config)
    result = agent.secure_infer("test")
    assert "attestation" not in result
