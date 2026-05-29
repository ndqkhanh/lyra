"""Tests for lyra_context_profiler.strategies module."""


from lyra_context_profiler.strategies import (
    CompactionStrategy,
    StrategyParameters,
    StrategyPresets,
    StrategyRecord,
    StrategyRegistry,
)

# ── StrategyParameters ──────────────────────────────────────────────────────────


class TestStrategyParameters:
    def test_default_values_are_reasonable(self):
        p = StrategyParameters()
        assert 0 <= p.drop_threshold <= 1.0
        assert p.drop_threshold < p.compact_threshold < p.keep_threshold
        assert p.min_retained_elements > 0

    def test_to_dict_and_from_dict_roundtrip(self):
        original = StrategyParameters(
            drop_threshold=0.2,
            compact_threshold=0.6,
            keep_threshold=0.8,
            compression_target=0.4,
        )
        d = original.to_dict()
        restored = StrategyParameters.from_dict(d)
        assert restored.drop_threshold == original.drop_threshold
        assert restored.compact_threshold == original.compact_threshold
        assert restored.keep_threshold == original.keep_threshold
        assert restored.compression_target == original.compression_target

    def test_from_dict_ignores_extra_keys(self):
        data = {"drop_threshold": 0.3, "invalid_key": 999}
        p = StrategyParameters.from_dict(data)
        assert p.drop_threshold == 0.3

    def test_all_zero_from_dict_uses_defaults(self):
        p = StrategyParameters.from_dict({})
        assert isinstance(p, StrategyParameters)


# ── StrategyPresets ─────────────────────────────────────────────────────────────


class TestStrategyPresets:
    def test_aggressive_preset(self):
        p = StrategyPresets.aggressive()
        assert p.drop_threshold > 0.1
        assert p.compression_target < 0.5  # Aggressive compression

    def test_conservative_preset(self):
        p = StrategyPresets.conservative()
        assert p.drop_threshold < 0.1
        assert p.compression_target > 0.7  # Conservative keeps more
        assert p.enable_fuzzy_dedup is False  # Conservative doesn't risk fuzzy matches

    def test_balanced_preset(self):
        p = StrategyPresets.balanced()
        assert 0.1 <= p.drop_threshold <= 0.3
        assert 0.4 <= p.compression_target <= 0.7

    def test_adaptive_preset(self):
        p = StrategyPresets.adaptive()
        assert p.learning_rate > 0.05  # Adaptive learns faster


# ── StrategyRegistry ────────────────────────────────────────────────────────────


class TestStrategyRegistry:
    def test_initializes_all_strategies(self):
        registry = StrategyRegistry()
        for strategy in CompactionStrategy:
            params = registry.get_parameters(strategy)
            assert isinstance(params, StrategyParameters)

    def test_configure_updates_parameters(self):
        registry = StrategyRegistry()
        new_params = StrategyParameters(drop_threshold=0.42)
        registry.configure(CompactionStrategy.BALANCED, new_params)
        assert registry.get_parameters(CompactionStrategy.BALANCED).drop_threshold == 0.42

    def test_record_result_updates_stats(self):
        registry = StrategyRegistry()
        record = StrategyRecord(
            strategy=CompactionStrategy.BALANCED,
            tokens_freed=5000,
            quality_loss=0.1,
            task_success=True,
            user_satisfaction=0.8,
            duration_ms=50.0,
            context_before_utilization=0.85,
            context_after_utilization=0.60,
        )
        registry.record_result(CompactionStrategy.BALANCED, record)
        stats = registry.get_strategy_stats()
        assert stats["BALANCED"]["applications"] == 1

    def test_best_strategy_no_history_uses_heuristic(self):
        registry = StrategyRegistry()
        best = registry.best_strategy_for(95.0)
        assert best == CompactionStrategy.AGGRESSIVE

        best = registry.best_strategy_for(60.0)
        assert best == CompactionStrategy.ADAPTIVE

        best = registry.best_strategy_for(95.0, prioritize_quality=True)
        assert best == CompactionStrategy.BALANCED

    def test_best_strategy_with_history(self):
        registry = StrategyRegistry()
        # Record good results for BALANCED
        for _ in range(5):
            registry.record_result(CompactionStrategy.BALANCED, StrategyRecord(
                strategy=CompactionStrategy.BALANCED,
                tokens_freed=8000,
                quality_loss=0.08,
                task_success=True,
                user_satisfaction=0.9,
                duration_ms=30.0,
                context_before_utilization=0.85,
                context_after_utilization=0.55,
            ))
        best = registry.best_strategy_for(80.0)
        assert isinstance(best, CompactionStrategy)

    def test_adapt_parameters(self):
        registry = StrategyRegistry()
        results = [
            StrategyRecord(
                strategy=CompactionStrategy.ADAPTIVE,
                tokens_freed=1000,  # Low freed tokens
                quality_loss=0.35,   # High quality loss
                task_success=False,
                user_satisfaction=0.3,
                duration_ms=100.0,
                context_before_utilization=0.85,
                context_after_utilization=0.80,
            )
        ]
        new_params = registry.adapt_parameters(CompactionStrategy.ADAPTIVE, results)
        # Quality loss above max should raise thresholds
        assert isinstance(new_params, StrategyParameters)

    def test_clear_history_resets(self):
        registry = StrategyRegistry()
        registry.record_result(CompactionStrategy.BALANCED, StrategyRecord(
            strategy=CompactionStrategy.BALANCED,
            tokens_freed=5000,
            quality_loss=0.1,
            task_success=True,
            user_satisfaction=0.8,
            duration_ms=50.0,
            context_before_utilization=0.85,
            context_after_utilization=0.60,
        ))
        registry.clear_history()
        assert registry.total_applications == 0

    def test_get_strategy_stats_all_strategies(self):
        registry = StrategyRegistry()
        stats = registry.get_strategy_stats()
        for name in ["AGGRESSIVE", "CONSERVATIVE", "BALANCED", "ADAPTIVE"]:
            assert name in stats
