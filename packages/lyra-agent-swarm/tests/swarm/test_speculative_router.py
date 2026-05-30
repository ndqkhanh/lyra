"""Tests for speculative execution router."""

from __future__ import annotations

import pytest

from lyra_agent_swarm.speculative_router import (
    CandidateResult,
    DispatchStrategy,
    ExecutionPlan,
    ModelCandidate,
    SpeculativeRouter,
    SpeculativeRouterConfig,
    VoteResult,
)


# ── Fixtures ──────────────────────────────────────────────────


@pytest.fixture
def router():
    return SpeculativeRouter()


@pytest.fixture
def candidates():
    return [
        ModelCandidate(model_id="opus-4.7", capability_score=0.95, cost_per_token=15.0),
        ModelCandidate(model_id="sonnet-4.6", capability_score=0.85, cost_per_token=3.0),
        ModelCandidate(model_id="haiku-4.5", capability_score=0.75, cost_per_token=1.0),
    ]


# ── TestModelCandidate ────────────────────────────────────────


class TestModelCandidate:
    def test_candidate_creation(self):
        c = ModelCandidate(
            model_id="opus-4.7",
            capability_score=0.95,
            cost_per_token=15.0,
        )
        assert c.model_id == "opus-4.7"
        assert c.capability_score == 0.95

    def test_candidate_immutability(self):
        c = ModelCandidate(model_id="opus", capability_score=0.9, cost_per_token=10.0)
        with pytest.raises(Exception):
            c.capability_score = 1.0

    def test_candidate_properties(self):
        c = ModelCandidate(
            model_id="haiku",
            capability_score=0.75,
            cost_per_token=1.0,
            latency_ms=200.0,
        )
        assert c.latency_ms == 200.0
        assert c.is_available is True

    def test_candidate_unavailable(self):
        c = ModelCandidate(
            model_id="opus",
            capability_score=0.95,
            cost_per_token=15.0,
            is_available=False,
        )
        assert not c.is_available


class TestSpeculativeRouterConfig:
    def test_default_config(self):
        cfg = SpeculativeRouterConfig()
        assert cfg.max_parallel_candidates == 3
        assert cfg.timeout_ms == 5000.0
        assert cfg.min_agreement_threshold == 0.6

    def test_custom_config(self):
        cfg = SpeculativeRouterConfig(
            max_parallel_candidates=5,
            timeout_ms=10000.0,
            min_agreement_threshold=0.8,
        )
        assert cfg.max_parallel_candidates == 5


# ── TestSpeculativeRouterBasic ─────────────────────────────────


class TestSpeculativeRouterBasic:
    def test_empty_router(self, router):
        assert router.candidate_count == 0

    def test_register_candidate(self, router):
        c = ModelCandidate(model_id="opus", capability_score=0.95, cost_per_token=15.0)
        router.register_candidate(c)
        assert router.candidate_count == 1

    def test_register_duplicate(self, router):
        c = ModelCandidate(model_id="opus", capability_score=0.95, cost_per_token=15.0)
        router.register_candidate(c)
        with pytest.raises(ValueError, match="already registered"):
            router.register_candidate(c)

    def test_unregister_candidate(self, router):
        c = ModelCandidate(model_id="opus", capability_score=0.95, cost_per_token=15.0)
        router.register_candidate(c)
        router.unregister_candidate("opus")
        assert router.candidate_count == 0

    def test_get_candidate(self, router):
        c = ModelCandidate(model_id="sonnet", capability_score=0.85, cost_per_token=3.0)
        router.register_candidate(c)
        result = router.get_candidate("sonnet")
        assert result is not None
        assert result.model_id == "sonnet"

    def test_get_candidate_missing(self, router):
        assert router.get_candidate("nonexistent") is None


# ── TestSpeculativeRouterDispatch ──────────────────────────────


class TestSpeculativeRouterDispatch:
    def test_build_plan_single(self, router, candidates):
        for c in candidates:
            router.register_candidate(c)

        plan = router.build_plan(
            task="Fix simple typo in README",
            complexity=0.1,
            risk_level=0.05,
            strategy=DispatchStrategy.COST_OPTIMIZED,
        )
        assert plan is not None
        assert len(plan.candidates) == 1
        assert plan.candidates[0].model_id == "haiku-4.5"

    def test_build_plan_parallel(self, router, candidates):
        for c in candidates:
            router.register_candidate(c)

        plan = router.build_plan(
            task="Implement authentication system with RBAC",
            complexity=0.7,
            risk_level=0.6,
            strategy=DispatchStrategy.PARALLEL_VERIFIED,
        )
        assert plan is not None
        assert len(plan.candidates) >= 2

    def test_build_plan_quality(self, router, candidates):
        for c in candidates:
            router.register_candidate(c)

        plan = router.build_plan(
            task="Design distributed consensus architecture",
            complexity=0.95,
            risk_level=0.8,
            strategy=DispatchStrategy.QUALITY_FIRST,
        )
        assert plan is not None
        assert plan.candidates[0].model_id == "opus-4.7"

    def test_select_candidates_filters_unavailable(self, router):
        router.register_candidate(
            ModelCandidate(model_id="opus", capability_score=0.95, cost_per_token=15.0)
        )
        router.register_candidate(
            ModelCandidate(model_id="sonnet", capability_score=0.85, cost_per_token=3.0,
                           is_available=False)
        )
        router.register_candidate(
            ModelCandidate(model_id="haiku", capability_score=0.75, cost_per_token=1.0)
        )
        available = router._select_candidates(
            complexity=0.5, risk=0.3, strategy=DispatchStrategy.COST_OPTIMIZED
        )
        model_ids = {c.model_id for c in available}
        assert "sonnet" not in model_ids

    def test_vote_simple_majority(self, router):
        results = [
            CandidateResult(model_id="opus", output="Approved the implementation looks correct and safe", confidence=0.9),
            CandidateResult(model_id="sonnet", output="Approved the implementation looks correct and safe", confidence=0.85),
            CandidateResult(model_id="haiku", output="Rejected found security vulnerability in code", confidence=0.7),
        ]
        vote = router.vote(results)
        assert vote.outcome == "approved"
        assert vote.agree_count == 2

    def test_vote_split(self, router):
        results = [
            CandidateResult(model_id="opus", output="Rejected: bug", confidence=0.95),
            CandidateResult(model_id="sonnet", output="Approved: works", confidence=0.8),
        ]
        vote = router.vote(results)
        assert vote.outcome in ("approved", "rejected")

    def test_vote_empty(self, router):
        vote = router.vote([])
        assert vote.outcome == "abstained"
        assert vote.agree_count == 0

    def test_compare_results_identical(self, router):
        r1 = CandidateResult(model_id="a", output="The implementation looks correct and follows all best practices", confidence=0.9)
        r2 = CandidateResult(model_id="b", output="The implementation looks correct and follows all best practices", confidence=0.85)
        similarity = router.compare_results(r1, r2)
        assert similarity == 1.0

    def test_compare_results_different(self, router):
        r1 = CandidateResult(model_id="a", output="function add(a,b) { return a+b }", confidence=0.9)
        r2 = CandidateResult(model_id="b", output="SELECT * FROM users", confidence=0.85)
        similarity = router.compare_results(r1, r2)
        assert similarity < 0.3

    def test_tie_break_by_confidence(self, router):
        r1 = CandidateResult(model_id="opus", output="OK", confidence=0.95)
        r2 = CandidateResult(model_id="sonnet", output="OK", confidence=0.8)
        winner = router.tie_break(r1, r2)
        assert winner.model_id == "opus"

    def test_tie_break_by_capability(self, router):
        r1 = CandidateResult(model_id="sonnet", output="OK", confidence=0.9)
        r2 = CandidateResult(model_id="haiku", output="OK", confidence=0.9)
        router.register_candidate(
            ModelCandidate(model_id="sonnet", capability_score=0.85, cost_per_token=3.0)
        )
        router.register_candidate(
            ModelCandidate(model_id="haiku", capability_score=0.75, cost_per_token=1.0)
        )
        winner = router.tie_break(r1, r2)
        assert winner.model_id == "sonnet"

    def test_get_result_summary(self, router):
        results = [
            CandidateResult(model_id="opus", output="A", confidence=0.95, latency_ms=500.0),
            CandidateResult(model_id="sonnet", output="A", confidence=0.85, latency_ms=200.0),
        ]
        vote = router.vote(results)
        summary = router.get_result_summary(results, vote)
        assert summary["total_candidates"] == 2
        assert summary["outcome"] == vote.outcome
        assert "total_cost" in summary

    def test_reset(self, router, candidates):
        for c in candidates:
            router.register_candidate(c)
        router.reset()
        assert router.candidate_count == 0


# ── TestDispatchStrategy ───────────────────────────────────────


class TestDispatchStrategy:
    def test_strategy_values(self):
        assert DispatchStrategy.PARALLEL_VERIFIED is not None
        assert DispatchStrategy.COST_OPTIMIZED is not None
        assert DispatchStrategy.QUALITY_FIRST is not None
        assert DispatchStrategy.SINGLE_BEST is not None


# ── TestCandidateResult ────────────────────────────────────────


class TestCandidateResult:
    def test_result_creation(self):
        r = CandidateResult(
            model_id="sonnet",
            output="console.log('test')",
            confidence=0.9,
            latency_ms=450.0,
        )
        assert r.model_id == "sonnet"
        assert r.confidence == 0.9
        assert r.latency_ms == 450.0

    def test_result_immutability(self):
        r = CandidateResult(model_id="sonnet", output="test", confidence=0.8)
        with pytest.raises(Exception):
            r.confidence = 1.0


# ── TestVoteResult ─────────────────────────────────────────────


class TestVoteResult:
    def test_vote_result_creation(self):
        v = VoteResult(
            outcome="approved",
            agree_count=3,
            total_count=4,
            agreement_ratio=0.75,
        )
        assert v.outcome == "approved"
        assert v.agreement_ratio == 0.75

    def test_vote_result_is_consensus(self):
        strong = VoteResult(outcome="approved", agree_count=4, total_count=4, agreement_ratio=1.0)
        weak = VoteResult(outcome="approved", agree_count=2, total_count=4, agreement_ratio=0.5)
        assert strong.is_consensus
        assert not weak.is_consensus


# ── TestExecutionPlan ──────────────────────────────────────────


class TestExecutionPlan:
    def test_plan_creation(self):
        plan = ExecutionPlan(
            plan_id="ep-1",
            candidates=(
                ModelCandidate(model_id="opus", capability_score=0.95, cost_per_token=15.0),
            ),
            strategy=DispatchStrategy.QUALITY_FIRST,
            timeout_ms=5000.0,
        )
        assert plan.candidate_count == 1

    def test_plan_immutability(self):
        plan = ExecutionPlan(
            plan_id="ep-1",
            candidates=(),
            strategy=DispatchStrategy.COST_OPTIMIZED,
            timeout_ms=1000.0,
        )
        with pytest.raises(Exception):
            plan.strategy = DispatchStrategy.QUALITY_FIRST
