"""Tests for Auto-Compaction with Quality Verification (P2-B7)."""
from __future__ import annotations

import pytest

from lyra_harness_core.auto_compaction import (
    AutoCompactor,
    CompactionCandidate,
    CompactionDecision,
    CompactionResult,
    CompactionStrategy,
    CompactionVerification,
    FillStatus,
    QualitySpotCheck,
    compute_fill_ratio,
)


# ---------------------------------------------------------------------------
# CompactionStrategy
# ---------------------------------------------------------------------------


class TestCompactionStrategy:
    def test_values(self):
        assert CompactionStrategy.SUMMARIZE.value == "summarize"
        assert CompactionStrategy.OFFLOAD.value == "offload"
        assert CompactionStrategy.PRUNE.value == "prune"
        assert CompactionStrategy.HIERARCHICAL.value == "hierarchical"

    def test_all_distinct(self):
        values = [s.value for s in CompactionStrategy]
        assert len(values) == len(set(values))


# ---------------------------------------------------------------------------
# FillStatus
# ---------------------------------------------------------------------------


class TestFillStatus:
    def test_measure_below_threshold(self):
        fs = FillStatus.measure(5000, 10000, threshold=0.8)
        assert fs.current_tokens == 5000
        assert fs.max_tokens == 10000
        assert fs.fill_ratio == 0.5
        assert not fs.is_critical

    def test_measure_at_threshold(self):
        fs = FillStatus.measure(8000, 10000, threshold=0.8)
        assert fs.is_critical

    def test_measure_above_threshold(self):
        fs = FillStatus.measure(9500, 10000, threshold=0.8)
        assert fs.is_critical

    def test_measure_zero_max(self):
        fs = FillStatus.measure(100, 0)
        assert fs.fill_ratio == 0.0
        assert not fs.is_critical

    def test_measure_full(self):
        fs = FillStatus.measure(10000, 10000, threshold=0.8)
        assert fs.fill_ratio == 1.0
        assert fs.is_critical

    def test_frozen(self):
        fs = FillStatus.measure(5000, 10000)
        with pytest.raises(Exception):
            fs.current_tokens = 6000  # type: ignore[misc]


# ---------------------------------------------------------------------------
# CompactionCandidate
# ---------------------------------------------------------------------------


class TestCompactionCandidate:
    def test_defaults(self):
        c = CompactionCandidate("s1", "content", 50, age=5.0)
        assert c.segment_id == "s1"
        assert c.content == "content"
        assert c.token_count == 50
        assert c.age == 5.0
        assert c.priority == 0.5

    def test_custom_priority(self):
        c = CompactionCandidate("s1", "important", 100, age=1.0, priority=0.9)
        assert c.priority == 0.9

    def test_mutable(self):
        c = CompactionCandidate("s1", "content", 50, age=1.0)
        c.priority = 0.3
        assert c.priority == 0.3


# ---------------------------------------------------------------------------
# CompactionDecision
# ---------------------------------------------------------------------------


class TestCompactionDecision:
    def test_default_values(self):
        d = CompactionDecision(CompactionStrategy.SUMMARIZE)
        assert d.strategy == CompactionStrategy.SUMMARIZE
        assert d.candidates == []
        assert d.target_token_reduction == 0
        assert d.reason == ""

    def test_with_candidates(self):
        c = CompactionCandidate("s1", "x", 10, age=1.0)
        d = CompactionDecision(CompactionStrategy.PRUNE, [c], 100, "fill=95%")
        assert len(d.candidates) == 1
        assert d.target_token_reduction == 100
        assert d.reason == "fill=95%"

    def test_frozen(self):
        d = CompactionDecision(CompactionStrategy.SUMMARIZE)
        with pytest.raises(Exception):
            d.strategy = CompactionStrategy.PRUNE  # type: ignore[misc]


# ---------------------------------------------------------------------------
# QualitySpotCheck
# ---------------------------------------------------------------------------


class TestQualitySpotCheck:
    def test_create(self):
        qc = QualitySpotCheck("s1", "abc", "def", True, "ok")
        assert qc.segment_id == "s1"
        assert qc.original_hash == "abc"
        assert qc.compacted_hash == "def"
        assert qc.passed
        assert qc.note == "ok"

    def test_frozen(self):
        qc = QualitySpotCheck("s1", "a", "b", True)
        with pytest.raises(Exception):
            qc.passed = False  # type: ignore[misc]


# ---------------------------------------------------------------------------
# CompactionVerification
# ---------------------------------------------------------------------------


class TestCompactionVerification:
    def test_all_passed_true(self):
        checks = [
            QualitySpotCheck("s1", "a", "b", True),
            QualitySpotCheck("s2", "c", "d", True),
        ]
        cv = CompactionVerification(checks, 2, 2, 0.05)
        assert cv.all_passed
        assert cv.pass_rate == 1.0

    def test_all_passed_false(self):
        checks = [
            QualitySpotCheck("s1", "a", "b", True),
            QualitySpotCheck("s2", "c", "d", False),
        ]
        cv = CompactionVerification(checks, 2, 1, 0.05)
        assert not cv.all_passed
        assert cv.pass_rate == 0.5

    def test_empty(self):
        cv = CompactionVerification([], 0, 0, 0.05)
        assert cv.all_passed
        assert cv.pass_rate == 1.0

    def test_frozen(self):
        cv = CompactionVerification([], 0, 0, 0.05)
        with pytest.raises(Exception):
            cv.total_checks = 5  # type: ignore[misc]


# ---------------------------------------------------------------------------
# CompactionResult
# ---------------------------------------------------------------------------


class TestCompactionResult:
    def test_without_verification(self):
        r = CompactionResult(
            CompactionStrategy.SUMMARIZE, 1000, 600, 5, 400, None, 12.5
        )
        assert r.strategy == CompactionStrategy.SUMMARIZE
        assert r.tokens_before == 1000
        assert r.tokens_after == 600
        assert r.segments_removed == 5
        assert r.token_reduction == 400
        assert r.verification is None
        assert r.elapsed_ms == 12.5

    def test_with_verification(self):
        cv = CompactionVerification([], 0, 0, 0.05)
        r = CompactionResult(
            CompactionStrategy.PRUNE, 1000, 400, 10, 600, cv, 8.0
        )
        assert r.verification is cv

    def test_frozen(self):
        r = CompactionResult(
            CompactionStrategy.SUMMARIZE, 100, 50, 1, 50, None, 1.0
        )
        with pytest.raises(Exception):
            r.tokens_after = 200  # type: ignore[misc]


# ---------------------------------------------------------------------------
# compute_fill_ratio
# ---------------------------------------------------------------------------


class TestComputeFillRatio:
    def test_half(self):
        assert compute_fill_ratio(50, 100) == 0.5

    def test_full(self):
        assert compute_fill_ratio(100, 100) == 1.0

    def test_zero(self):
        assert compute_fill_ratio(0, 100) == 0.0

    def test_zero_max(self):
        assert compute_fill_ratio(100, 0) == 0.0


# ---------------------------------------------------------------------------
# AutoCompactor
# ---------------------------------------------------------------------------


class TestAutoCompactor:
    @pytest.fixture
    def compactor(self):
        return AutoCompactor(max_tokens=100_000)

    # --- check_fill -----------------------------------------------------------

    def test_check_fill_below_threshold(self, compactor):
        fs = compactor.check_fill(70_000)
        assert not fs.is_critical

    def test_check_fill_above_threshold(self, compactor):
        fs = compactor.check_fill(85_000)
        assert fs.is_critical

    def test_should_compact_false(self, compactor):
        assert not compactor.should_compact(70_000)

    def test_should_compact_true(self, compactor):
        assert compactor.should_compact(85_000)

    # --- select_strategy ------------------------------------------------------

    def test_select_summarize_at_85_percent(self, compactor):
        fs = compactor.check_fill(85_000)
        decision = compactor.select_strategy([], fs)
        assert decision.strategy == CompactionStrategy.SUMMARIZE

    def test_select_offload_at_92_percent(self, compactor):
        fs = compactor.check_fill(92_000)
        decision = compactor.select_strategy([], fs)
        assert decision.strategy == CompactionStrategy.OFFLOAD

    def test_select_prune_at_96_percent(self, compactor):
        fs = compactor.check_fill(96_000)
        decision = compactor.select_strategy([], fs)
        assert decision.strategy == CompactionStrategy.PRUNE

    def test_strategy_hint_overrides(self, compactor):
        fs = compactor.check_fill(85_000)  # would be SUMMARIZE
        decision = compactor.select_strategy(
            [], fs, strategy_hint=CompactionStrategy.HIERARCHICAL
        )
        assert decision.strategy == CompactionStrategy.HIERARCHICAL

    def test_target_token_reduction(self, compactor):
        fs = compactor.check_fill(90_000)  # excess = 90k - 80k = 10k
        decision = compactor.select_strategy([], fs)
        assert decision.target_token_reduction >= 1

    def test_decision_includes_candidates(self, compactor):
        fs = compactor.check_fill(85_000)
        c = CompactionCandidate("s1", "content", 100, age=1.0)
        decision = compactor.select_strategy([c], fs)
        assert len(decision.candidates) == 1

    # --- verify ---------------------------------------------------------------

    def test_verify_empty(self, compactor):
        result = compactor.verify({}, {})
        assert result.total_checks == 0
        assert result.all_passed

    def test_verify_no_overlap(self, compactor):
        result = compactor.verify({"a": "x"}, {"b": "y"})
        assert result.total_checks == 0

    def test_verify_passing(self, compactor):
        orig = {"s1": "the system architecture uses a modular design pattern"}
        compacted = {"s1": "system architecture uses modular design"}
        result = compactor.verify(orig, compacted)
        assert result.total_checks >= 1
        assert result.all_passed

    def test_verify_failing(self, compactor):
        orig = {"s1": "the system uses a sophisticated neural network architecture"}
        compacted = {"s1": "the system uses stuff"}
        result = compactor.verify(orig, compacted)
        assert not result.all_passed

    def test_verify_respects_sample_rate(self, compactor):
        """With many segments, should sample ~5%."""
        orig = {f"s{i}": f"segment {i} contains important data" for i in range(100)}
        compacted = {f"s{i}": f"segment {i} data" for i in range(100)}
        result = compactor.verify(orig, compacted)
        # 5% of 100 = 5, but min_spot_checks = 3
        assert result.total_checks >= compactor.min_spot_checks

    def test_verify_min_spot_checks(self, compactor):
        """With enough segments, sample at least min_spot_checks."""
        n = 100
        orig = {f"s{i}": "alpha beta gamma delta epsilon" for i in range(n)}
        compacted = {f"s{i}": "alpha beta gamma delta epsilon" for i in range(n)}
        result = compactor.verify(orig, compacted)
        assert result.total_checks >= compactor.min_spot_checks

    def test_verify_sample_rate_stored(self, compactor):
        result = compactor.verify({"a": "hello world"}, {"a": "hello"})
        assert result.sample_rate == compactor.spot_check_rate

    # --- _check_segment -------------------------------------------------------

    def test_check_segment_preserves_key_terms(self):
        assert AutoCompactor._check_segment(
            "the authentication module requires secure token storage",
            "authentication requires secure token storage",
        )

    def test_check_segment_loss_of_key_terms(self):
        assert not AutoCompactor._check_segment(
            "the authentication module requires secure token storage",
            "the module requires stuff",
        )

    def test_check_segment_empty_original(self):
        assert AutoCompactor._check_segment("", "")

    def test_check_segment_no_key_terms(self):
        # Short words (<4 chars) are not key terms
        assert AutoCompactor._check_segment("it is a test", "it is a test")

    def test_check_segment_no_key_terms_original_empty_compacted(self):
        # Original has no key terms, compacted is empty → fails
        assert not AutoCompactor._check_segment("a b c", "")

    # --- build_result ---------------------------------------------------------

    def test_build_result(self, compactor):
        orig = {"s1": "system architecture uses modular design patterns"}
        compacted = {"s1": "system architecture modular design"}
        result = compactor.build_result(
            CompactionStrategy.SUMMARIZE,
            tokens_before=1000,
            tokens_after=600,
            segments_removed=3,
            original_segments=orig,
            compacted_segments=compacted,
        )
        assert result.strategy == CompactionStrategy.SUMMARIZE
        assert result.tokens_before == 1000
        assert result.tokens_after == 600
        assert result.segments_removed == 3
        assert result.token_reduction == 400
        assert result.verification is not None
        assert result.verification.all_passed
        assert result.elapsed_ms > 0

    # --- custom threshold -----------------------------------------------------

    def test_custom_threshold(self):
        compactor = AutoCompactor(max_tokens=100_000, fill_threshold=0.7)
        fs = compactor.check_fill(75_000)
        assert fs.is_critical  # 75% > 70%

    def test_custom_spot_check_rate(self):
        compactor = AutoCompactor(max_tokens=1000, spot_check_rate=0.5, min_spot_checks=1)
        orig = {f"s{i}": "alpha beta gamma delta" for i in range(4)}
        compacted = {f"s{i}": "alpha beta gamma delta" for i in range(4)}
        result = compactor.verify(orig, compacted)
        # 50% of 4 = 2
        assert result.total_checks == 2


# ---------------------------------------------------------------------------
# Full pipeline integration test
# ---------------------------------------------------------------------------


class TestCompactionPipeline:
    def test_end_to_end(self):
        compactor = AutoCompactor(max_tokens=10_000)

        # Simulate a context approaching capacity
        current_tokens = 8_500
        assert compactor.should_compact(current_tokens)

        fs = compactor.check_fill(current_tokens)
        assert fs.fill_ratio == 0.85

        # Simulate content segments
        candidates = [
            CompactionCandidate("sys", "System prompt here", 200, age=100.0, priority=1.0),
            CompactionCandidate("msg1", "Old message about architecture", 500, age=80.0, priority=0.2),
            CompactionCandidate("msg2", "Another old message about design patterns", 500, age=75.0, priority=0.2),
            CompactionCandidate("msg3", "Recent message about the current task", 500, age=5.0, priority=0.9),
        ]

        decision = compactor.select_strategy(candidates, fs)
        assert decision.strategy == CompactionStrategy.SUMMARIZE

        # Simulate compaction (keep high-priority, summarize low-priority)
        original = {"msg1": "Old message about architecture", "msg2": "Another old message about design patterns"}
        compacted = {"msg1": "architecture message", "msg2": "design patterns message"}

        result = compactor.build_result(
            decision.strategy,
            tokens_before=1700,
            tokens_after=800,
            segments_removed=0,
            original_segments=original,
            compacted_segments=compacted,
        )

        assert result.strategy == CompactionStrategy.SUMMARIZE
        assert result.token_reduction == 900
        assert result.verification is not None
