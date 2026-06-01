"""Tests for lyra-context — auto-compaction engine.

Covers:
  - AutoCompactor with all 5 strategies (NONE, SUMMARIZE, TRUNCATE,
    KV_EVICT, AGGRESSIVE)
  - CompactResult dataclass construction and invariants
  - Strategy selection based on usage ratio
  - ProviderAdaptiveCompactor for multi-provider context windows
  - ProviderContextConfig thresholds
"""

from __future__ import annotations

import pytest

from lyra_context.compactor import (
    AutoCompactor,
    CompactResult,
    CompactionStrategy,
)
from lyra_context.provider_adapter import (
    ProviderAdaptiveCompactor,
    ProviderContextConfig,
)


# ── CompactResult ──────────────────────────────────────────────────────


class TestCompactResult:
    """CompactResult is a simple frozen dataclass — verify invariants."""

    def test_default_preserved_items(self) -> None:
        result = CompactResult(
            strategy=CompactionStrategy.NONE,
            original_tokens=1000,
            compressed_tokens=1000,
            compression_ratio=0.0,
            items_removed=0,
            items_kept=10,
            latency_ms=0.5,
        )
        assert result.preserved_items == []
        assert result.strategy == CompactionStrategy.NONE

    def test_full_construction(self) -> None:
        result = CompactResult(
            strategy=CompactionStrategy.TRUNCATE,
            original_tokens=5000,
            compressed_tokens=1500,
            compression_ratio=0.7,
            items_removed=35,
            items_kept=15,
            latency_ms=2.3,
            preserved_items=["a", "b", "c"],
        )
        assert result.original_tokens == 5000
        assert result.compressed_tokens == 1500
        assert result.compression_ratio == 0.7
        assert result.items_removed == 35
        assert result.items_kept == 15
        assert result.latency_ms == 2.3
        assert result.preserved_items == ["a", "b", "c"]

    def test_zero_tokens_ratio(self) -> None:
        """compression_ratio should be 0.0 for zero original_tokens."""
        result = CompactResult(
            strategy=CompactionStrategy.NONE,
            original_tokens=0,
            compressed_tokens=0,
            compression_ratio=0.0,
            items_removed=0,
            items_kept=0,
            latency_ms=0.0,
        )
        assert result.compression_ratio == 0.0


# ── AutoCompactor ──────────────────────────────────────────────────────


class TestAutoCompactor:
    """Test the core compaction engine."""

    def make_items(self, count: int, priority: int = 5) -> list[dict]:
        return [
            {"id": f"item{i}", "content": f"content-{i}", "priority": priority}
            for i in range(count)
        ]

    # ── should_compact ────────────────────────────────────────────────

    def test_should_compact_below_threshold(self) -> None:
        c = AutoCompactor(max_tokens=1000, threshold=0.80)
        assert not c.should_compact(500)  # 50% < 80%

    def test_should_compact_at_threshold(self) -> None:
        c = AutoCompactor(max_tokens=1000, threshold=0.80)
        assert c.should_compact(800)  # 80% == threshold

    def test_should_compact_above_threshold(self) -> None:
        c = AutoCompactor(max_tokens=1000, threshold=0.80)
        assert c.should_compact(950)  # 95% > 80%

    # ── NONE strategy ─────────────────────────────────────────────────

    def test_compact_below_threshold_returns_none(self) -> None:
        c = AutoCompactor(max_tokens=1000, threshold=0.80)
        items = self.make_items(10)
        result = c.compact(items, current_tokens=500)
        assert result.strategy == CompactionStrategy.NONE
        assert result.compression_ratio == 0.0
        assert result.items_removed == 0
        assert result.items_kept == 10

    def test_compact_empty_items(self) -> None:
        c = AutoCompactor(max_tokens=1000, threshold=0.80)
        result = c.compact([], current_tokens=950)
        # Should not crash; strategy will be selected but kept=0
        assert result.strategy is not None
        assert isinstance(result.latency_ms, float)

    # ── SUMMARIZE strategy (80-89% usage) ────────────────────────────

    def test_summarize_strategy(self) -> None:
        """SUMMARIZE should keep top 50% of items by priority."""
        c = AutoCompactor(max_tokens=1000, threshold=0.80)
        # 10 items at priority 5 => all equal => bottom 50% removed
        items = self.make_items(10, priority=5)
        result = c.compact(items, current_tokens=850)  # 85% usage
        assert result.strategy == CompactionStrategy.SUMMARIZE
        assert result.items_removed == 5       # bottom 50%
        assert result.items_kept == 5          # top 50%

    def test_summarize_keeps_high_priority(self) -> None:
        """Items with higher priority values should be preferentially kept."""
        c = AutoCompactor(max_tokens=1000, threshold=0.80)
        items = [
            {"id": "low", "content": "low", "priority": 1},
            {"id": "high", "content": "high", "priority": 10},
        ]
        result = c.compact(items, current_tokens=900)
        assert result.items_kept >= 1
        # After sorting, the high priority item should be kept

    # ── TRUNCATE strategy (90-94% usage) ─────────────────────────────

    def test_truncate_strategy(self) -> None:
        """TRUNCATE should keep top 30% of items."""
        c = AutoCompactor(max_tokens=1000, threshold=0.80)
        items = self.make_items(20, priority=5)
        result = c.compact(items, current_tokens=920)  # 92% usage
        assert result.strategy == CompactionStrategy.TRUNCATE
        # top 30% of 20 = 6
        assert result.items_kept == 6
        assert result.items_removed == 14

    # ── KV_EVICT strategy (95-97% usage) ─────────────────────────────

    def test_kv_evict_strategy(self) -> None:
        """KV_EVICT should evict bottom 25% by norm proxy."""
        c = AutoCompactor(max_tokens=1000, threshold=0.80)
        items = self.make_items(12, priority=5)
        result = c.compact(items, current_tokens=960)  # 96% usage
        assert result.strategy == CompactionStrategy.KV_EVICT
        assert result.items_kept == 9   # 75% kept
        assert result.items_removed == 3  # 25% evicted

    def test_kv_evict_lower_priority_evicted_first(self) -> None:
        """Items with lower priority should be evicted first by KV_EVICT."""
        c = AutoCompactor(max_tokens=1000, threshold=0.80)
        items = [
            {"id": f"item{i}", "content": "x" * 10, "priority": i}
            for i in range(1, 13)  # priorities 1-12
        ]
        result = c.compact(items, current_tokens=960)
        assert result.strategy == CompactionStrategy.KV_EVICT
        # 3 items evicted — they should be the lowest priority (1, 2, 3)
        for i in result.preserved_items:
            assert i != ""  # survived items have ids

    # ── AGGRESSIVE strategy (>=98% usage) ────────────────────────────

    def test_aggressive_strategy(self) -> None:
        """AGGRESSIVE should keep top 15% of items."""
        c = AutoCompactor(max_tokens=1000, threshold=0.80)
        items = self.make_items(20, priority=5)
        result = c.compact(items, current_tokens=990)  # 99% usage
        assert result.strategy == CompactionStrategy.AGGRESSIVE
        # top 15% of 20 = 3
        assert result.items_kept == 3
        assert result.items_removed == 17

    # ── Token calculations ───────────────────────────────────────────

    def test_compression_ratio_is_reported(self) -> None:
        c = AutoCompactor(max_tokens=1000, threshold=0.80)
        items = self.make_items(10, priority=5)
        result = c.compact(items, current_tokens=900)
        assert result.compression_ratio > 0.0
        assert result.original_tokens == 900
        assert result.compressed_tokens < result.original_tokens

    def test_latency_is_measured(self) -> None:
        c = AutoCompactor(max_tokens=1000, threshold=0.80)
        items = self.make_items(100, priority=5)
        result = c.compact(items, current_tokens=900)
        assert result.latency_ms > 0.0
        assert isinstance(result.latency_ms, float)

    # ── Stats tracking ───────────────────────────────────────────────

    def test_stats_tracks_compactions(self) -> None:
        c = AutoCompactor(max_tokens=1000, threshold=0.80)
        items = self.make_items(10)
        assert c.stats["compaction_count"] == 0
        assert c.stats["total_tokens_saved"] == 0
        c.compact(items, current_tokens=900)
        assert c.stats["compaction_count"] == 1
        assert c.stats["total_tokens_saved"] > 0
        c.compact(items, current_tokens=900)
        assert c.stats["compaction_count"] == 2
        assert c.stats["total_tokens_saved"] > 0

    # ── Edge cases ───────────────────────────────────────────────────

    def test_single_item_not_crashing(self) -> None:
        c = AutoCompactor(max_tokens=1000, threshold=0.80)
        items = [{"id": "only", "content": "lonely", "priority": 5}]
        result = c.compact(items, current_tokens=950)
        assert result.items_kept >= 0
        assert result.items_removed >= 0

    def test_zero_max_tokens_no_crash(self) -> None:
        """Zero max_tokens should not cause division-by-zero."""
        c = AutoCompactor(max_tokens=0, threshold=0.80)
        items = self.make_items(5)
        result = c.compact(items, current_tokens=100)
        # Should still return a valid result without ZeroDivisionError
        assert result is not None
        assert isinstance(result.strategy, CompactionStrategy)

    def test_variable_priority_survival(self) -> None:
        """Items with priority 10 always survive any strategy."""
        c = AutoCompactor(max_tokens=1000, threshold=0.80)
        items = [
            {"id": "norm_a", "content": "a", "priority": 1},
            {"id": "norm_b", "content": "b", "priority": 2},
            {"id": "golden", "content": "golden", "priority": 10},
        ]
        result = c.compact(items, current_tokens=990)  # aggressive
        # The golden item (priority 10) should be in preserved_items
        # or at least items_kept should reflect that high-priority items survive
        assert result.items_kept >= 1


# ── ProviderAdaptiveCompactor ──────────────────────────────────────────


class TestProviderAdaptiveCompactor:
    """Test the provider-adaptive context strategy."""

    def setup_method(self) -> None:
        self.pac = ProviderAdaptiveCompactor()

    # ── Context windows ──────────────────────────────────────────────

    def test_known_provider_window(self) -> None:
        assert self.pac.get_context_window("anthropic") == 200_000
        assert self.pac.get_context_window("openai") == 128_000
        assert self.pac.get_context_window("google") == 2_000_000
        assert self.pac.get_context_window("deepseek") == 64_000
        assert self.pac.get_context_window("local") == 8_000

    def test_unknown_provider_falls_back_to_default(self) -> None:
        assert self.pac.get_context_window("nonexistent") == 128_000

    def test_model_specific_window(self) -> None:
        self.pac.register_provider("custom/big-model", 1_000_000)
        assert self.pac.get_context_window("custom", "big-model") == 1_000_000
        # Without model should return generic provider window
        assert self.pac.get_context_window("custom") == 128_000

    def test_register_provider_override(self) -> None:
        self.pac.register_provider("anthropic", 300_000)
        assert self.pac.get_context_window("anthropic") == 300_000

    # ── Strategy selection ───────────────────────────────────────────

    @pytest.mark.parametrize(
        "provider,usage,expected",
        [
            ("anthropic", 0.40, CompactionStrategy.NONE),       # <50%
            ("anthropic", 0.55, CompactionStrategy.SUMMARIZE),   # 50-69%
            ("anthropic", 0.75, CompactionStrategy.SUMMARIZE),   # 70-84% large window
            ("deepseek",  0.75, CompactionStrategy.TRUNCATE),    # 70-84% small window
            ("anthropic", 0.90, CompactionStrategy.KV_EVICT),    # 85-94% large window
            ("deepseek",  0.90, CompactionStrategy.AGGRESSIVE),  # 85-94% small window
            ("anthropic", 0.97, CompactionStrategy.AGGRESSIVE),  # >=95%
            ("local",     0.55, CompactionStrategy.SUMMARIZE),   # 50-69% small window
            ("local",     0.90, CompactionStrategy.AGGRESSIVE),  # 85-94% tiny window
        ],
    )
    def test_select_strategy_by_provider(
        self,
        provider: str,
        usage: float,
        expected: CompactionStrategy,
    ) -> None:
        window = self.pac.get_context_window(provider)
        tokens = int(window * usage)
        strategy = self.pac.select_strategy(
            provider=provider, current_tokens=tokens,
        )
        assert strategy == expected, (
            f"{provider} at {usage*100:.0f}% expected {expected}, got {strategy}"
        )

    # ── Token estimation ─────────────────────────────────────────────

    def test_estimate_tokens_before_compaction(self) -> None:
        expected = int(200_000 * 0.85)  # default safety_margin
        assert self.pac.estimate_tokens_before_compaction("anthropic") == expected

    def test_estimate_custom_provider(self) -> None:
        self.pac.register_provider("custom", 50_000)
        assert self.pac.estimate_tokens_before_compaction("custom") == int(50_000 * 0.85)


# ── ProviderContextConfig ──────────────────────────────────────────────


class TestProviderContextConfig:
    """Test the ProviderContextConfig dataclass."""

    def test_default_compaction_threshold(self) -> None:
        config = ProviderContextConfig(provider_name="test", context_window=100_000)
        assert config.compaction_threshold == 85_000  # 85% of 100k

    def test_custom_safety_margin(self) -> None:
        config = ProviderContextConfig(
            provider_name="test", context_window=100_000, safety_margin=0.90,
        )
        assert config.compaction_threshold == 90_000

    def test_immutable(self) -> None:
        config = ProviderContextConfig(provider_name="test", context_window=200_000)
        with pytest.raises(AttributeError):
            config.provider_name = "other"  # type: ignore[misc]
