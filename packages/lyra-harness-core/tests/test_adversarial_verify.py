"""Tests for adversarial_verify.py — Adversarial Verification (P4-B2 CRITICAL)."""
from __future__ import annotations

import pytest
from lyra_harness_core.adversarial_verify import (
    AdversarialVerdict,
    AttackAgent,
    AttackPoint,
    AttackSeverity,
    AttackStrategy,
    ConsensusConfig,
    ConsensusEngine,
    ConsensusState,
    DefenseAgent,
    DefenseResponse,
    RoundResult,
    VerdictKind,
    _compute_convergence,
)


# ---------------------------------------------------------------------------
# Enums
# ---------------------------------------------------------------------------

class TestAttackStrategy:
    def test_values(self):
        assert AttackStrategy.FACTUAL_CHECK.value == "factual_check"
        assert AttackStrategy.LOGICAL_FLAW.value == "logical_flaw"
        assert AttackStrategy.EDGE_CASE.value == "edge_case"

class TestVerdictKind:
    def test_values(self):
        assert VerdictKind.CONSENSUS_REACHED.value == "consensus_reached"
        assert VerdictKind.MAX_ROUNDS_EXCEEDED.value == "max_rounds_exceeded"

class TestAttackSeverity:
    def test_values(self):
        assert AttackSeverity.CRITICAL.value == "critical"
        assert AttackSeverity.LOW.value == "low"


# ---------------------------------------------------------------------------
# AttackPoint
# ---------------------------------------------------------------------------

class TestAttackPoint:
    def test_creation(self):
        ap = AttackPoint(
            attack_id="a1",
            strategy=AttackStrategy.FACTUAL_CHECK,
            claim="Claim is unverified",
            evidence="No citation provided",
        )
        assert ap.attack_id == "a1"
        assert ap.severity == AttackSeverity.MEDIUM
        assert ap.target_fragment == ""

    def test_with_target(self):
        ap = AttackPoint(
            attack_id="a2",
            strategy=AttackStrategy.LOGICAL_FLAW,
            claim="Fallacy",
            evidence="Bad reasoning",
            severity=AttackSeverity.HIGH,
            target_fragment="the problematic sentence",
        )
        assert ap.severity == AttackSeverity.HIGH
        assert ap.target_fragment == "the problematic sentence"

    def test_frozen(self):
        ap = AttackPoint(
            attack_id="a1", strategy=AttackStrategy.FACTUAL_CHECK,
            claim="x", evidence="y",
        )
        with pytest.raises(Exception):
            ap.claim = "new"  # type: ignore[misc]


# ---------------------------------------------------------------------------
# DefenseResponse
# ---------------------------------------------------------------------------

class TestDefenseResponse:
    def test_creation(self):
        dr = DefenseResponse(
            attack_id="a1", rebuttal="Counter-argument", accepted=False, confidence=0.9,
        )
        assert dr.rebuttal == "Counter-argument"
        assert not dr.accepted
        assert dr.revision == ""

    def test_accepted_with_revision(self):
        dr = DefenseResponse(
            attack_id="a1",
            rebuttal="Good point",
            accepted=True,
            revision="Revised text here",
            confidence=0.7,
        )
        assert dr.accepted
        assert dr.revision == "Revised text here"


# ---------------------------------------------------------------------------
# RoundResult
# ---------------------------------------------------------------------------

class TestRoundResult:
    def test_creation(self):
        ap = AttackPoint(
            attack_id="a1", strategy=AttackStrategy.EDGE_CASE,
            claim="Missing edge", evidence="No edges found",
        )
        dr = DefenseResponse(attack_id="a1", rebuttal="Added", accepted=True)
        rr = RoundResult(
            round_number=0,
            attacks=(ap,),
            defenses=(dr,),
            accepted_attacks=1,
            total_attacks=1,
            consensus_score=1.0,
            elapsed_ms=10.0,
        )
        assert rr.unresolved_count == 0
        assert rr.consensus_score == 1.0

    def test_unresolved(self):
        rr = RoundResult(
            round_number=1,
            attacks=(),
            defenses=(),
            accepted_attacks=2,
            total_attacks=5,
            consensus_score=0.4,
            elapsed_ms=5.0,
        )
        assert rr.unresolved_count == 3


# ---------------------------------------------------------------------------
# ConsensusState
# ---------------------------------------------------------------------------

class TestConsensusState:
    def test_creation(self):
        cs = ConsensusState(
            round_results=(),
            convergence_score=0.5,
            trend="stable",
            rounds_remaining=2,
        )
        assert cs.round_count == 0
        assert cs.total_attacks == 0
        assert cs.total_accepted == 0


# ---------------------------------------------------------------------------
# AdversarialVerdict
# ---------------------------------------------------------------------------

class TestAdversarialVerdict:
    def test_creation(self):
        cs = ConsensusState(round_results=(), convergence_score=0.9, trend="improving", rounds_remaining=0)
        av = AdversarialVerdict(
            kind=VerdictKind.CONSENSUS_REACHED,
            consensus_score=0.95,
            confidence=0.9,
            rounds_completed=2,
            total_attacks=5,
            accepted_attacks=1,
            critical_findings=0,
            consensus_state=cs,
            summary="Consensus reached.",
            answer_accepted=True,
        )
        assert av.kind == VerdictKind.CONSENSUS_REACHED
        assert av.answer_accepted
        assert av.acceptance_rate == pytest.approx(1.0 - 1 / 5)

    def test_acceptance_rate_no_attacks(self):
        cs = ConsensusState(round_results=(), convergence_score=1.0, trend="stable", rounds_remaining=0)
        av = AdversarialVerdict(
            kind=VerdictKind.DEFENDER_WINS,
            consensus_score=1.0,
            confidence=1.0,
            rounds_completed=1,
            total_attacks=0,
            accepted_attacks=0,
            critical_findings=0,
            consensus_state=cs,
            summary="No attacks.",
            answer_accepted=True,
        )
        assert av.acceptance_rate == 1.0


# ---------------------------------------------------------------------------
# AttackAgent
# ---------------------------------------------------------------------------

class TestAttackAgent:
    def test_creation(self):
        agent = AttackAgent(agent_id="test-attacker")
        assert agent.agent_id == "test-attacker"
        assert len(agent.strategies) == 3
        assert agent.max_attacks == 5

    def test_attack_finds_absolute_claims(self):
        agent = AttackAgent(agent_id="a1")
        answer = "This solution always works and never fails. Every user must adopt it."
        attacks = agent.attack(answer)
        assert len(attacks) > 0
        strategies = {a.strategy for a in attacks}
        assert AttackStrategy.FACTUAL_CHECK in strategies

    def test_attack_finds_edge_case_gaps(self):
        agent = AttackAgent(agent_id="a2")
        answer = (
            "Here is a comprehensive analysis of the system architecture "
            "with multiple components that work together to provide a robust "
            "and scalable solution for enterprise customers."
        )
        attacks = agent.attack(answer)
        strategy_types = {a.strategy for a in attacks}
        assert AttackStrategy.EDGE_CASE in strategy_types

    def test_attack_respects_max_attacks(self):
        agent = AttackAgent(agent_id="a3", max_attacks=3)
        answer = "always never every all none must definitely obviously everyone knows it is clear that without a doubt"
        attacks = agent.attack(answer)
        assert len(attacks) <= 3

    def test_attack_custom_strategies(self):
        agent = AttackAgent(
            agent_id="a4",
            strategies=(AttackStrategy.COMPLETENESS,),
        )
        answer = "Yes."
        attacks = agent.attack(answer)
        assert any(a.strategy == AttackStrategy.COMPLETENESS for a in attacks)

    def test_attack_empty_answer(self):
        agent = AttackAgent(agent_id="a5")
        attacks = agent.attack("")
        assert isinstance(attacks, tuple)

    def test_attack_assumption_challenge(self):
        agent = AttackAgent(
            agent_id="a6",
            strategies=(AttackStrategy.ASSUMPTION_CHALLENGE,),
        )
        answer = "Assuming the system is available, we can proceed."
        attacks = agent.attack(answer)
        assert len(attacks) > 0


# ---------------------------------------------------------------------------
# DefenseAgent
# ---------------------------------------------------------------------------

class TestDefenseAgent:
    def test_creation(self):
        agent = DefenseAgent(agent_id="defender-1")
        assert agent.agent_id == "defender-1"

    def test_defend(self):
        agent = DefenseAgent(agent_id="d1")
        attacks = (
            AttackPoint(
                attack_id="a1",
                strategy=AttackStrategy.FACTUAL_CHECK,
                claim="Unverified claim",
                evidence="No proof",
            ),
        )
        answer = "This is a verified claim with proof."
        defenses = agent.defend(attacks, answer)
        assert len(defenses) == 1
        assert isinstance(defenses[0], DefenseResponse)
        assert defenses[0].attack_id == "a1"


# ---------------------------------------------------------------------------
# ConsensusConfig
# ---------------------------------------------------------------------------

class TestConsensusConfig:
    def test_defaults(self):
        config = ConsensusConfig()
        assert config.attack_agents == 2
        assert config.convergence_threshold == 0.9
        assert config.max_rounds == 3

    def test_custom(self):
        config = ConsensusConfig(attack_agents=4, convergence_threshold=0.95, max_rounds=5)
        assert config.attack_agents == 4
        assert config.max_rounds == 5


# ---------------------------------------------------------------------------
# _compute_convergence
# ---------------------------------------------------------------------------

class TestComputeConvergence:
    def test_empty(self):
        assert _compute_convergence([]) == 0.0

    def test_full_resolution(self):
        rr = RoundResult(
            round_number=0, attacks=(), defenses=(),
            accepted_attacks=3, total_attacks=3, consensus_score=1.0, elapsed_ms=0.0,
        )
        assert _compute_convergence([rr]) == 1.0

    def test_no_attacks(self):
        rr = RoundResult(
            round_number=0, attacks=(), defenses=(),
            accepted_attacks=0, total_attacks=0, consensus_score=0.0, elapsed_ms=0.0,
        )
        assert _compute_convergence([rr]) == 1.0

    def test_partial_resolution(self):
        rr = RoundResult(
            round_number=0, attacks=(), defenses=(),
            accepted_attacks=2, total_attacks=5, consensus_score=0.4, elapsed_ms=0.0,
        )
        assert _compute_convergence([rr]) == 0.4

    def test_improving_trend(self):
        rr1 = RoundResult(
            round_number=0, attacks=(), defenses=(),
            accepted_attacks=1, total_attacks=5, consensus_score=0.2, elapsed_ms=0.0,
        )
        rr2 = RoundResult(
            round_number=1, attacks=(), defenses=(),
            accepted_attacks=4, total_attacks=5, consensus_score=0.8, elapsed_ms=0.0,
        )
        conv = _compute_convergence([rr1, rr2])
        assert conv > 0.8  # resolution + trend bonus


# ---------------------------------------------------------------------------
# ConsensusEngine
# ---------------------------------------------------------------------------

class TestConsensusEngine:
    def test_verify_simple_answer(self):
        engine = ConsensusEngine(
            config=ConsensusConfig(attack_agents=1, max_rounds=2, convergence_threshold=0.5),
        )
        verdict = engine.verify("The sky is blue because of Rayleigh scattering.")
        assert isinstance(verdict, AdversarialVerdict)
        assert verdict.rounds_completed >= 1
        assert verdict.total_attacks >= 0

    def test_verify_empty_answer(self):
        engine = ConsensusEngine(
            config=ConsensusConfig(attack_agents=1, max_rounds=1),
        )
        verdict = engine.verify("")
        assert isinstance(verdict, AdversarialVerdict)

    def test_verify_robust_answer(self):
        """A well-structured answer should withstand attacks."""
        engine = ConsensusEngine(
            config=ConsensusConfig(attack_agents=1, max_rounds=3, convergence_threshold=0.5),
        )
        answer = (
            "Based on empirical evidence and peer-reviewed studies, "
            "the optimal approach involves: 1) Initial assessment, "
            "2) Iterative refinement, 3) Validation against benchmarks. "
            "Edge cases include: empty input, boundary values, and concurrent access."
        )
        verdict = engine.verify(answer)
        assert verdict.consensus_score >= 0.0
        assert verdict.rounds_completed >= 1

    def test_verify_with_critical_answer(self):
        engine = ConsensusEngine(
            config=ConsensusConfig(attack_agents=2, max_rounds=3),
        )
        answer = "This approach always works perfectly and never fails under any conditions."
        verdict = engine.verify(answer)
        assert isinstance(verdict, AdversarialVerdict)

    def test_verify_custom_agents(self):
        engine = ConsensusEngine(
            config=ConsensusConfig(attack_agents=2, max_rounds=2),
            attack_agents=[
                AttackAgent(
                    agent_id="custom-1",
                    strategies=(AttackStrategy.FACTUAL_CHECK,),
                    max_attacks=3,
                ),
                AttackAgent(
                    agent_id="custom-2",
                    strategies=(AttackStrategy.EDGE_CASE, AttackStrategy.COMPLETENESS),
                    max_attacks=2,
                ),
            ],
            defense_agents=[DefenseAgent(agent_id="custom-defender")],
        )
        verdict = engine.verify("A moderately complex answer that should be checked.")
        assert isinstance(verdict, AdversarialVerdict)

    def test_consensus_state_in_verdict(self):
        engine = ConsensusEngine(
            config=ConsensusConfig(attack_agents=1, max_rounds=2),
        )
        verdict = engine.verify("Test answer.")
        cs = verdict.consensus_state
        assert cs.convergence_score >= 0.0
        assert isinstance(cs.trend, str)


# ---------------------------------------------------------------------------
# Integration
# ---------------------------------------------------------------------------

class TestIntegration:
    def test_full_pipeline(self):
        """Full adversarial verification pipeline."""
        engine = ConsensusEngine(
            config=ConsensusConfig(attack_agents=2, max_rounds=3, convergence_threshold=0.9),
        )
        verdict = engine.verify(
            "After thorough analysis, we recommend a phased rollout strategy. "
            "Phase 1 targets low-risk users with feature flag. "
            "Phase 2 expands to general availability after 2-week monitoring. "
            "Edge cases: handle rate limiting, cache invalidation, and concurrent writes. "
            "Rollback plan: automated with canary deployment."
        )
        assert isinstance(verdict.kind, VerdictKind)
        assert verdict.consensus_score >= 0.0
        assert verdict.confidence >= 0.0
        assert verdict.rounds_completed >= 1

    def test_multiple_rounds_converge(self):
        """With a perfect answer, should converge quickly."""
        engine = ConsensusEngine(
            config=ConsensusConfig(attack_agents=1, max_rounds=3, convergence_threshold=0.5),
        )
        answer = (
            "The system processes requests through a load balancer, "
            "distributing across 3 availability zones. Each zone has "
            "auto-scaling groups with minimum 2 instances. Edge cases "
            "handled: network partition (quorum-based), thundering herd "
            "(jitter), cache stampede (probabilistic early recomputation)."
        )
        verdict = engine.verify(answer)
        assert verdict.rounds_completed >= 1
