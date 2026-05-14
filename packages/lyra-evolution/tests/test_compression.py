"""Tests for Phase L — Adaptive compression promotion (the "missing diagonal")."""
import pytest

from lyra_evolution.compression import (
    CompressedArtifact,
    CompressionConfig,
    CompressionLevel,
    CompressionPromoter,
)


def _artifact(
    aid="a1",
    source="trace-1",
    level=CompressionLevel.TRACE,
    content="long enough content for promotion",
    contexts=None,
) -> CompressedArtifact:
    a = CompressedArtifact(
        artifact_id=aid,
        source_id=source,
        level=level,
        content=content,
        context_tags=list(contexts or []),
    )
    return a


class TestCompressionLevel:
    def test_ordering(self):
        assert CompressionLevel.TRACE < CompressionLevel.EPISODIC
        assert CompressionLevel.EPISODIC < CompressionLevel.SKILL
        assert CompressionLevel.SKILL < CompressionLevel.RULE

    def test_values(self):
        assert CompressionLevel.TRACE == 0
        assert CompressionLevel.RULE == 3


class TestCompressedArtifact:
    def test_default_generalization_score(self):
        a = _artifact()
        assert a.generalization_score == 0.0

    def test_context_tags_mutable(self):
        a = _artifact(contexts=["web"])
        a.context_tags.append("cli")
        assert len(a.context_tags) == 2


class TestCompressionPromoterBasic:
    def test_register_and_retrieve(self):
        p = CompressionPromoter()
        a = _artifact("a1")
        p.register(a)
        assert p.artifact("a1") is a

    def test_unknown_artifact_returns_none(self):
        p = CompressionPromoter()
        assert p.artifact("ghost") is None

    def test_artifacts_at_level(self):
        p = CompressionPromoter()
        p.register(_artifact("a1", level=CompressionLevel.TRACE))
        p.register(_artifact("a2", level=CompressionLevel.SKILL))
        traces = p.artifacts_at_level(CompressionLevel.TRACE)
        assert len(traces) == 1
        assert traces[0].artifact_id == "a1"


class TestAddContext:
    def test_add_context_updates_score(self):
        p = CompressionPromoter(CompressionConfig(rule_min_contexts=5))
        a = _artifact("a1")
        p.register(a)
        p.add_context("a1", "web")
        assert a.generalization_score == pytest.approx(1.0 / 5)

    def test_duplicate_context_ignored(self):
        p = CompressionPromoter()
        a = _artifact("a1")
        p.register(a)
        p.add_context("a1", "web")
        p.add_context("a1", "web")
        assert len(a.context_tags) == 1

    def test_score_capped_at_one(self):
        cfg = CompressionConfig(rule_min_contexts=2)
        p = CompressionPromoter(cfg)
        a = _artifact("a1")
        p.register(a)
        for ctx in ["web", "cli", "api", "mobile"]:
            p.add_context("a1", ctx)
        assert a.generalization_score <= 1.0


class TestIncrementalPromotion:
    def test_trace_to_episodic(self):
        cfg = CompressionConfig(episodic_min_contexts=2, skill_min_contexts=3, rule_min_contexts=5)
        p = CompressionPromoter(cfg)
        a = _artifact("a1")
        p.register(a)
        p.add_context("a1", "web")
        p.add_context("a1", "cli")
        new_level = p.promote("a1")
        assert new_level == CompressionLevel.EPISODIC
        assert a.level == CompressionLevel.EPISODIC

    def test_episodic_to_skill(self):
        cfg = CompressionConfig(episodic_min_contexts=2, skill_min_contexts=3, rule_min_contexts=5)
        p = CompressionPromoter(cfg)
        a = _artifact("a1", level=CompressionLevel.EPISODIC)
        p.register(a)
        for ctx in ["web", "cli", "api"]:
            p.add_context("a1", ctx)
        new_level = p.promote("a1")
        assert new_level == CompressionLevel.SKILL

    def test_skill_to_rule(self):
        cfg = CompressionConfig(rule_min_contexts=3, diagonal_threshold=0.99)
        p = CompressionPromoter(cfg)
        a = _artifact("a1", level=CompressionLevel.SKILL)
        p.register(a)
        for ctx in ["web", "cli", "api"]:
            p.add_context("a1", ctx)
        new_level = p.promote("a1")
        assert new_level == CompressionLevel.RULE

    def test_no_promotion_insufficient_contexts(self):
        p = CompressionPromoter()
        a = _artifact("a1")
        p.register(a)
        p.add_context("a1", "web")  # only 1, need 2
        result = p.promote("a1")
        assert result is None
        assert a.level == CompressionLevel.TRACE

    def test_rule_not_promoted_further(self):
        p = CompressionPromoter()
        a = _artifact("a1", level=CompressionLevel.RULE)
        p.register(a)
        for ctx in ["a", "b", "c", "d", "e", "f"]:
            p.add_context("a1", ctx)
        result = p.promote("a1")
        assert result is None

    def test_stub_content_not_promoted(self):
        cfg = CompressionConfig(min_content_length=20, episodic_min_contexts=1)
        p = CompressionPromoter(cfg)
        a = _artifact("a1", content="short")
        p.register(a)
        p.add_context("a1", "web")
        result = p.promote("a1")
        assert result is None


class TestDiagonalPromotion:
    def test_diagonal_trace_to_rule(self):
        cfg = CompressionConfig(
            rule_min_contexts=3,
            diagonal_threshold=0.80,
        )
        p = CompressionPromoter(cfg)
        a = _artifact("a1", level=CompressionLevel.TRACE)
        p.register(a)
        for ctx in ["web", "cli", "api"]:
            p.add_context("a1", ctx)
        # generalization_score = 3/3 = 1.0 ≥ 0.80 → diagonal to RULE
        new_level = p.promote("a1")
        assert new_level == CompressionLevel.RULE

    def test_diagonal_episodic_to_rule(self):
        cfg = CompressionConfig(
            rule_min_contexts=3,
            diagonal_threshold=0.80,
        )
        p = CompressionPromoter(cfg)
        a = _artifact("a1", level=CompressionLevel.EPISODIC)
        p.register(a)
        for ctx in ["web", "cli", "api"]:
            p.add_context("a1", ctx)
        new_level = p.promote("a1")
        assert new_level == CompressionLevel.RULE

    def test_no_diagonal_when_score_below_threshold(self):
        cfg = CompressionConfig(
            episodic_min_contexts=2,
            rule_min_contexts=5,
            diagonal_threshold=0.95,
        )
        p = CompressionPromoter(cfg)
        a = _artifact("a1", level=CompressionLevel.TRACE)
        p.register(a)
        for ctx in ["web", "cli"]:
            p.add_context("a1", ctx)
        # score = 2/5 = 0.4, below diagonal threshold → incremental only
        new_level = p.promote("a1")
        assert new_level == CompressionLevel.EPISODIC


class TestPromotionLog:
    def test_promotion_log_records_transitions(self):
        cfg = CompressionConfig(episodic_min_contexts=2, rule_min_contexts=5)
        p = CompressionPromoter(cfg)
        a = _artifact("a1")
        p.register(a)
        p.add_context("a1", "web")
        p.add_context("a1", "cli")
        p.promote("a1")
        log = p.promotion_log
        assert len(log) == 1
        aid, frm, to = log[0]
        assert aid == "a1"
        assert frm == CompressionLevel.TRACE
        assert to == CompressionLevel.EPISODIC

    def test_promote_all_returns_promoted_list(self):
        cfg = CompressionConfig(episodic_min_contexts=1, rule_min_contexts=5)
        p = CompressionPromoter(cfg)
        p.register(_artifact("a1"))
        p.register(_artifact("a2"))
        p.add_context("a1", "web")
        p.add_context("a2", "cli")
        results = p.promote_all()
        assert len(results) == 2
        for _aid, _frm, to in results:
            assert to == CompressionLevel.EPISODIC
