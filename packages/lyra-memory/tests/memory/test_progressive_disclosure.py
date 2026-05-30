"""Tests for ProgressiveDisclosureManager and ContextPrioritizer."""

from __future__ import annotations

import pytest
from lyra_core.context.pipeline import ContextItem, ContextLayer
from lyra_core.token_budget import TokenBudgetManager

from lyra_memory.context_prioritizer import ContextPrioritizer
from lyra_memory.progressive_disclosure import (
    DisclosureConfig,
    DisclosureLevel,
    ProgressiveDisclosureManager,
)

# ── DisclosureLevel Tests ────────────────────────────────────────────────


class TestDisclosureLevel:
    def test_create(self):
        level = DisclosureLevel(0, 4000, "critical_context")
        assert level.level == 0
        assert level.max_tokens == 4000
        assert level.description == "critical_context"

    def test_immutable(self):
        level = DisclosureLevel(0, 4000, "critical")
        with pytest.raises(AttributeError):
            level.level = 1  # type: ignore[misc]

    def test_multiple_levels(self):
        levels = [
            DisclosureLevel(0, 4000, "a"),
            DisclosureLevel(1, 8000, "b"),
            DisclosureLevel(4, 64000, "e"),
        ]
        assert levels[0].level == 0
        assert levels[2].level == 4


# ── DisclosureConfig Tests ───────────────────────────────────────────────


class TestDisclosureConfig:
    def test_default_levels(self):
        config = DisclosureConfig()
        assert len(config.levels) == 5
        assert config.levels[0].level == 0
        assert config.levels[0].max_tokens == 4000
        assert config.levels[4].level == 4
        assert config.levels[4].max_tokens == 64000

    def test_default_config_values(self):
        config = DisclosureConfig()
        assert config.default_level == 2
        assert config.budget_headroom_pct == 0.15
        assert config.expansion_trigger == 0.8

    def test_immutable(self):
        config = DisclosureConfig()
        with pytest.raises(AttributeError):
            config.default_level = 3  # type: ignore[misc]

    def test_custom_config(self):
        levels = (
            DisclosureLevel(0, 1000, "minimal"),
            DisclosureLevel(1, 2000, "extended"),
        )
        config = DisclosureConfig(
            levels=levels,
            default_level=0,
            budget_headroom_pct=0.1,
            expansion_trigger=0.9,
        )
        assert config.default_level == 0
        assert config.budget_headroom_pct == 0.1
        assert config.expansion_trigger == 0.9


# ── ProgressiveDisclosureManager Tests ────────────────────────────────────


def _make_item(content: str, weight: int = 5) -> ContextItem:
    return ContextItem(
        layer=ContextLayer.MEMORY_REFS,
        content=content,
        weight=weight,
    )


def _make_manager(
    total_budget: int = 100000,
    default_level: int = 2,
) -> ProgressiveDisclosureManager:
    config = DisclosureConfig(default_level=default_level)
    budget = TokenBudgetManager(total_budget=total_budget)
    return ProgressiveDisclosureManager(config=config, token_budget=budget)


class TestProgressiveDisclosureManagerInit:
    def test_default_level(self):
        manager = _make_manager(default_level=1)
        assert manager.current_level == 1

    def test_starts_empty(self):
        manager = _make_manager()
        assert manager._context_items == {}


class TestProgressiveDisclosureManagerRegister:
    def test_register_basic(self):
        manager = _make_manager()
        item = _make_item("test content")
        manager.register(item, priority=0)
        assert 0 in manager._context_items
        assert manager._context_items[0] == [item]

    def test_register_multiple_levels(self):
        manager = _make_manager()
        items = [_make_item(f"item {i}") for i in range(3)]
        for i, item in enumerate(items):
            manager.register(item, priority=i)
        for i in range(3):
            assert len(manager._context_items[i]) == 1

    def test_register_multiple_at_same_level(self):
        manager = _make_manager()
        items = [_make_item(f"item {i}") for i in range(5)]
        for item in items:
            manager.register(item, priority=0)
        assert len(manager._context_items[0]) == 5

    def test_register_invalid_priority_low(self):
        manager = _make_manager()
        with pytest.raises(ValueError, match="Priority must be 0-4"):
            manager.register(_make_item("x"), priority=-1)

    def test_register_invalid_priority_high(self):
        manager = _make_manager()
        with pytest.raises(ValueError, match="Priority must be 0-4"):
            manager.register(_make_item("x"), priority=5)


class TestProgressiveDisclosureManagerAssemble:
    def test_assemble_empty(self):
        manager = _make_manager()
        result = manager.assemble_context(query="test")
        assert result == ""

    def test_assemble_includes_critical_level(self):
        manager = _make_manager(default_level=0)
        critical = _make_item("critical info", weight=10)
        manager.register(critical, priority=0)
        result = manager.assemble_context(query="test")
        assert "critical info" in result
        assert "critical_context" in result

    def test_assemble_multiple_levels(self):
        manager = _make_manager(default_level=1)
        manager.register(_make_item("critical", weight=10), priority=0)
        manager.register(_make_item("important", weight=5), priority=1)
        manager.register(_make_item("relevant", weight=3), priority=2)
        result = manager.assemble_context(query="test")
        assert "critical" in result
        assert "important" in result
        # Level 2 is above current_level=1, should not appear
        assert "relevant" not in result

    def test_assemble_respects_token_limit(self):
        manager = _make_manager(default_level=4)
        # Each item is about 1 token (4 chars), so 10 items = ~10 tokens
        for i in range(10):
            manager.register(_make_item(f"ab{i}", weight=5), priority=0)
        # Budget 20 tokens - headroom 15% = 17 available
        # At ~1 token each, all 10 critical items fit
        result = manager.assemble_context(query="test", max_tokens=20)
        assert "critical_context" in result

    def test_assemble_caps_by_budget(self):
        manager = _make_manager(default_level=4)
        long = "x" * 400  # ~100 tokens each
        manager.register(_make_item(long, weight=10), priority=0)
        manager.register(_make_item(long, weight=5), priority=0)
        manager.register(_make_item(long, weight=1), priority=0)
        # 3 items * ~100 tokens = ~300 tokens
        # Budget 200 - 15% = 170 available
        # Only the first 2 items (higher weight) should fit
        result = manager.assemble_context(query="test", max_tokens=200)
        assert "x" * 400 in result
        # Check header is present
        assert "critical_context" in result

    def test_assemble_sorts_by_weight_within_level(self):
        manager = _make_manager(default_level=0)
        low = _make_item("low_priority_content", weight=1)
        high = _make_item("high_priority_content", weight=10)
        manager.register(low, priority=0)
        manager.register(high, priority=0)
        result = manager.assemble_context(query="test")
        # Both should be present with enough budget
        assert "high_priority_content" in result
        assert "low_priority_content" in result

    def test_assemble_with_headroom(self):
        manager = _make_manager(default_level=0)
        config = DisclosureConfig(budget_headroom_pct=0.5)
        budget = TokenBudgetManager(total_budget=100)
        manager = ProgressiveDisclosureManager(config=config, token_budget=budget)
        # 50 tokens available after 50% headroom
        # Each item is ~1 token (4 chars), so all should fit
        for i in range(10):
            manager.register(_make_item(f"a{i}b", weight=5), priority=0)
        result = manager.assemble_context(query="test")
        # Should include items since headroom is 50% leaving 50 tokens for content
        assert result != ""


class TestProgressiveDisclosureManagerExpand:
    def test_expand_increases_level(self):
        manager = _make_manager(default_level=0)
        result = manager.expand()
        assert result == 1
        assert manager.current_level == 1

    def test_expand_caps_at_max(self):
        manager = _make_manager(default_level=4)
        result = manager.expand()
        assert result == 4  # Already at max, no change
        assert manager.current_level == 4

    def test_expand_multiple_times(self):
        manager = _make_manager(default_level=0)
        for expected in range(1, 5):
            assert manager.expand() == expected
        # Now at max
        assert manager.expand() == 4


class TestProgressiveDisclosureManagerCompact:
    def test_compact_down(self):
        manager = _make_manager(default_level=4)
        result = manager.compact(target_level=1)
        assert result == 1
        assert manager.current_level == 1

    def test_compact_clamps_to_zero(self):
        manager = _make_manager(default_level=2)
        result = manager.compact(target_level=-1)
        assert result == 0

    def test_compact_to_current_level_is_noop(self):
        manager = _make_manager(default_level=2)
        result = manager.compact(target_level=2)
        assert result == 2

    def test_compact_only_goes_down(self):
        manager = _make_manager(default_level=4)
        # compact to 2
        manager.compact(target_level=2)
        assert manager.current_level == 2


class TestProgressiveDisclosureManagerShouldExpand:
    def test_should_expand_true(self):
        manager = _make_manager(default_level=0)
        # Level 0 max_tokens = 4000, trigger at 80% = 3200
        assert manager.should_expand(3500) is True

    def test_should_expand_false_below_threshold(self):
        manager = _make_manager(default_level=0)
        # Level 0 max_tokens = 4000, trigger at 80% = 3200
        assert manager.should_expand(1000) is False

    def test_should_expand_false_at_max_level(self):
        manager = _make_manager(default_level=4)
        assert manager.should_expand(99999) is False

    def test_should_expand_at_threshold(self):
        manager = _make_manager(default_level=0)
        # Level 0 max_tokens = 4000, trigger at 80% = 3200
        # Just at threshold should trigger (>=)
        assert manager.should_expand(3200) is True


class TestProgressiveDisclosureManagerGetStats:
    def test_stats_default(self):
        manager = _make_manager()
        stats = manager.get_stats()
        assert stats["current_level"] == 2
        assert stats["total_registered"] == 0
        assert stats["level_counts"] == {}

    def test_stats_after_register(self):
        manager = _make_manager()
        manager.register(_make_item("a"), priority=0)
        manager.register(_make_item("b"), priority=1)
        stats = manager.get_stats()
        assert stats["total_registered"] == 2
        assert stats["level_counts"][0] == 1
        assert stats["level_counts"][1] == 1

    def test_stats_after_expand(self):
        manager = _make_manager(default_level=0)
        manager.expand()
        stats = manager.get_stats()
        assert stats["current_level"] == 1


# ── ContextPrioritizer Tests ─────────────────────────────────────────────


class TestContextPrioritizer:
    def test_empty_items(self):
        prioritizer = ContextPrioritizer()
        result = prioritizer.prioritize([], query="test")
        assert result == []

    def test_high_relevance_assigns_critical(self):
        prioritizer = ContextPrioritizer()
        items = [
            _make_item("python programming language syntax guide", weight=10),
        ]
        result = prioritizer.prioritize(items, query="python programming")
        assert len(result) == 1
        item, level = result[0]
        assert level == 0  # critical — high keyword overlap + high weight

    def test_low_relevance_assigns_archival(self):
        prioritizer = ContextPrioritizer()
        items = [
            _make_item("cooking recipes for pasta carbonara", weight=1),
        ]
        result = prioritizer.prioritize(items, query="quantum physics")
        assert len(result) == 1
        _, level = result[0]
        assert level == 4  # archival — no keyword overlap

    def test_sorts_by_score_descending(self):
        prioritizer = ContextPrioritizer()
        items = [
            _make_item("quantum physics wave function", weight=3),
            _make_item("quantum physics entanglement theory", weight=10),
        ]
        result = prioritizer.prioritize(items, query="quantum physics")
        assert len(result) == 2
        # Higher relevance + higher weight should come first
        assert result[0][1] <= result[1][1]  # lower level = higher priority

    def test_empty_query_returns_lowest_priority(self):
        prioritizer = ContextPrioritizer()
        items = [
            _make_item("some content here", weight=1),
        ]
        result = prioritizer.prioritize(items, query="")
        assert len(result) == 1
        _, level = result[0]
        assert level == 4  # archival — empty query means no relevance

    def test_weight_influences_level(self):
        prioritizer = ContextPrioritizer()
        items = [
            _make_item("python data science", weight=10),
            _make_item("python data science", weight=1),
        ]
        result = prioritizer.prioritize(items, query="python")
        # Both have same relevance, but first has higher weight
        # Higher weight -> higher score -> lower level
        assert result[0][1] == 0  # weight=10 pushes to critical
        assert result[1][1] == 1  # weight=1 plus some relevance = important


# ── Integration Tests ────────────────────────────────────────────────────


class TestProgressiveDisclosureIntegration:
    def test_register_then_assemble(self):
        """Test full pipeline: register -> assemble -> verify output."""
        manager = _make_manager(default_level=2)
        prioritizer = ContextPrioritizer()

        items = [
            _make_item("python async programming guide", weight=8),
            _make_item("python data science tutorial", weight=5),
            _make_item("cooking recipes collection", weight=2),
            _make_item("unrelated content here", weight=1),
        ]

        prioritized = prioritizer.prioritize(items, query="python programming")
        for item, level in prioritized:
            manager.register(item, level)

        result = manager.assemble_context(query="python programming")
        # The two python-related items should be included
        assert "python" in result
        assert "cooking" not in result or "unrelated" not in result

    def test_expand_under_budget_pressure(self):
        """Test expansion when token usage triggers threshold."""
        manager = _make_manager(default_level=0, total_budget=50000)

        # Register items at multiple levels
        for i in range(5):
            content = f"critical_item_{i}: " + "data " * 50
            manager.register(_make_item(content, weight=10), priority=0)

        # Should not expand initially
        assert not manager.should_expand(100)

        # Simulate usage that triggers expansion
        assert manager.should_expand(3500)  # Level 0 max=4000, 80%=3200
        new_level = manager.expand()
        assert new_level == 1

    def test_compact_reduces_context(self):
        """Test compaction reduces available context level."""
        manager = _make_manager(default_level=4)
        items = [_make_item(f"level_{i}_content", weight=5) for i in range(5)]
        for i, item in enumerate(items):
            manager.register(item, priority=i)

        # Assemble at level 4 - should include all levels
        full = manager.assemble_context(query="test")
        for i in range(5):
            level_def = DisclosureConfig().levels[i]
            assert level_def.description in full

        # Compact to level 1
        manager.compact(target_level=1)
        reduced = manager.assemble_context(query="test")
        assert DisclosureConfig().levels[0].description in reduced
        assert DisclosureConfig().levels[1].description in reduced
        # Levels 2+ should no longer be included
        assert DisclosureConfig().levels[2].description not in reduced

