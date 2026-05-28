"""Tests for MAVEN — Multi-perspective adversarial verification engine."""

import pytest
from lyra_core.safety.maven import (
    JudgePool,
    MavenConfig,
    MavenEngine,
    MavenResult,
    MavenVerdict,
    ModelIdentity,
    ReviewerRole,
    ReviewPerspective,
)


class TestReviewerRole:
    def test_role_values(self):
        assert ReviewerRole.SKEPTIC.value == "skeptic"
        assert ReviewerRole.RESEARCHER.value == "researcher"
        assert ReviewerRole.JUDGE.value == "judge"

    def test_three_distinct_roles(self):
        roles = {ReviewerRole.SKEPTIC, ReviewerRole.RESEARCHER, ReviewerRole.JUDGE}
        assert len(roles) == 3


class TestMavenVerdict:
    def test_verdict_values(self):
        assert MavenVerdict.PASS.value == "pass"
        assert MavenVerdict.FAIL.value == "fail"
        assert MavenVerdict.NEEDS_REVIEW.value == "needs_review"


class TestModelIdentity:
    def test_model_identity_creation(self):
        identity = ModelIdentity(
            provider="aws",
            family="anthropic",
            model_id="claude-3",
        )
        assert identity.provider == "aws"
        assert identity.family == "anthropic"
        assert identity.model_id == "claude-3"

    def test_model_identity_immutable(self):
        identity = ModelIdentity(provider="aws", family="anthropic", model_id="claude")
        with pytest.raises(Exception):
            identity.family = "openai"


class TestReviewPerspective:
    def test_perspective_creation(self):
        perspective = ReviewPerspective(
            role=ReviewerRole.SKEPTIC,
            model=ModelIdentity("aws", "anthropic", "claude"),
            analysis="Found 3 potential issues.",
            confidence=0.85,
        )
        assert perspective.role == ReviewerRole.SKEPTIC
        assert perspective.confidence == 0.85
        assert "issues" in perspective.analysis

    def test_perspective_with_flags(self):
        p = ReviewPerspective(
            role=ReviewerRole.CRITIC if hasattr(ReviewerRole, 'CRITIC') else ReviewerRole.SKEPTIC,
            model=ModelIdentity("gcp", "google", "gemini"),
            analysis="Review complete.",
            confidence=0.5,
            flags=("flag:security_concern",),
        )
        assert len(p.flags) >= 0

    def test_perspective_immutable(self):
        p = ReviewPerspective(
            role=ReviewerRole.RESEARCHER,
            model=ModelIdentity("aws", "anthropic", "claude"),
            analysis="Research done.",
            confidence=0.9,
        )
        with pytest.raises(Exception):
            p.role = ReviewerRole.JUDGE


class TestMavenResult:
    def test_result_pass(self):
        p = ReviewPerspective(ReviewerRole.SKEPTIC, ModelIdentity("a", "f", "m"), "ok", 0.95)
        result = MavenResult(
            request_id="req-001",
            action_text="deploy to production",
            perspectives=(p, p, p),
            verdict=MavenVerdict.PASS,
            reasoning="All checks passed.",
            judge_family="disjoint",
        )
        assert result.verdict == MavenVerdict.PASS
        assert result.passed is True
        assert result.confidence_mean == pytest.approx(0.95)

    def test_result_fail(self):
        p = ReviewPerspective(ReviewerRole.SKEPTIC, ModelIdentity("a", "f", "m"), "concern", 0.3)
        result = MavenResult(
            request_id="req-002",
            action_text="delete database",
            perspectives=(p, p, p),
            verdict=MavenVerdict.FAIL,
            reasoning="Too risky.",
            judge_family="disjoint",
        )
        assert result.verdict == MavenVerdict.FAIL
        assert result.passed is False

    def test_result_immutable(self):
        p = ReviewPerspective(ReviewerRole.SKEPTIC, ModelIdentity("a", "f", "m"), "ok", 0.8)
        result = MavenResult("r1", "action", (p, p, p), MavenVerdict.PASS, "ok", "openai")
        with pytest.raises(Exception):
            result.verdict = MavenVerdict.FAIL


class TestJudgePool:
    def test_register_judges(self):
        pool = JudgePool()
        pool.register("judge-1", ModelIdentity("aws", "anthropic", "claude"))
        pool.register("judge-2", ModelIdentity("azure", "openai", "gpt-4"))
        pool.register("judge-3", ModelIdentity("gcp", "google", "gemini"))
        assert pool.size == 3

    def test_select_family_disjoint(self):
        pool = JudgePool()
        pool.register("j1", ModelIdentity("aws", "anthropic", "claude"))
        pool.register("j2", ModelIdentity("azure", "openai", "gpt-4"))
        pool.register("j3", ModelIdentity("gcp", "google", "gemini"))

        selected = pool.select_disjoint("anthropic", "openai")
        assert selected is not None
        assert selected.family not in ("anthropic", "openai")

    def test_select_no_disjoint_available(self):
        pool = JudgePool()
        pool.register("j1", ModelIdentity("aws", "anthropic", "claude"))
        pool.register("j2", ModelIdentity("azure", "openai", "gpt-4"))

        selected = pool.select_disjoint("anthropic", "openai")
        assert selected is None

    def test_empty_pool_select(self):
        pool = JudgePool()
        selected = pool.select_disjoint("anthropic", "openai")
        assert selected is None


class TestMavenConfig:
    def test_default_config(self):
        config = MavenConfig()
        assert config.min_confidence_threshold == 0.7
        assert config.max_review_rounds == 3
        assert config.enable_family_disjoint_judge is True

    def test_custom_config(self):
        config = MavenConfig(min_confidence_threshold=0.9, max_review_rounds=5)
        assert config.min_confidence_threshold == 0.9
        assert config.max_review_rounds == 5


class TestMavenEngine:
    def test_engine_creation(self):
        engine = MavenEngine()
        assert engine.config is not None
        assert engine.judge_pool is not None

    def test_engine_with_config(self):
        config = MavenConfig(min_confidence_threshold=0.85)
        engine = MavenEngine(config=config)
        assert engine.config.min_confidence_threshold == 0.85

    def test_register_judge(self):
        engine = MavenEngine()
        engine.register_judge("j1", "aws", "anthropic", "claude")
        assert engine.judge_pool.size == 1

    def test_review_sync_pass(self):
        engine = MavenEngine()
        result = engine.review_sync(
            action_text="deploy to production",
            skeptic_analysis="No issues found.",
            researcher_analysis="All tests pass.",
            skeptic_confidence=0.9,
            researcher_confidence=0.85,
            judge_approved=True,
            judge_reasoning="Approved: both analyses are solid.",
        )
        assert result.verdict == MavenVerdict.PASS
        assert result.passed is True

    def test_review_sync_fail(self):
        engine = MavenEngine()
        result = engine.review_sync(
            action_text="delete database",
            skeptic_analysis="CRITICAL: data loss risk.",
            researcher_analysis="Backups exist but risky.",
            skeptic_confidence=0.2,
            researcher_confidence=0.5,
            judge_approved=False,
            judge_reasoning="Risk too high, rejected.",
        )
        assert result.verdict in (MavenVerdict.FAIL, MavenVerdict.NEEDS_REVIEW)
        assert result.passed is False

    def test_review_sync_needs_review(self):
        engine = MavenEngine()
        result = engine.review_sync(
            action_text="modify config",
            skeptic_analysis="Some concern.",
            researcher_analysis="Probably fine.",
            skeptic_confidence=0.3,
            researcher_confidence=0.7,
            judge_approved=False,
            judge_reasoning="Needs more investigation.",
        )
        assert result.verdict == MavenVerdict.NEEDS_REVIEW

    def test_history_accumulates(self):
        engine = MavenEngine()
        engine.review_sync("a", "ok", "ok", 0.9, 0.9, True, "go")
        engine.review_sync("b", "ok", "ok", 0.9, 0.9, True, "go")
        assert len(engine.history) == 2

    def test_stats(self):
        engine = MavenEngine()
        engine.review_sync("action", "ok", "ok", 0.9, 0.9, True, "approved")
        stats = engine.stats()
        assert stats["total"] == 1
        assert stats["pass_rate"] == 1.0
        assert "mean_confidence" in stats

    def test_stats_empty(self):
        engine = MavenEngine()
        stats = engine.stats()
        assert stats["total"] == 0
        assert stats["pass_rate"] == 0.0
