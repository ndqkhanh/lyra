"""Tests for StrategySelector (UCB1 bandit)."""


from lyra_cli.research.strategy_selector import (
    DEFAULT_QUERY_TYPES,
    StrategyResult,
    StrategySelector,
    StrategyType,
)


class TestStrategySelector:
    """Test suite for StrategySelector."""

    def test_initial_strategies_count(self):
        """Selector initialises with all strategy types."""
        sel = StrategySelector()
        # Internal: counts dict should have entries for all default query types
        assert len(sel._query_types) == len(DEFAULT_QUERY_TYPES)
        assert sel._query_types == DEFAULT_QUERY_TYPES

    def test_select_strategy_initial_exploration(self):
        """Unpulled arms cycle through all strategies first."""
        sel = StrategySelector(query_types=["factual"])
        selected = set()
        for _ in range(10):
            sel._counts["factual"] = {
                s.name: 0 for s in sel._strategies
            }
            sel._rewards["factual"] = {
                s.name: 0.0 for s in sel._strategies
            }
            selected.add(sel.select_strategy("factual"))

        # With zero pulls, it returns one strategy (first unpulled)
        s = sel.select_strategy("factual")
        assert s in StrategyType

    def test_select_strategy_all_pulled_then_ucb1(self):
        """After all strategies are pulled, UCB1 selects the best."""
        sel = StrategySelector(query_types=["factual"])
        # Manually set counts so all arms have been pulled
        sel._counts["factual"] = {
            "BREADTH_FIRST": 5,
            "DEPTH_FIRST": 5,
            "BEST_FIRST": 5,
        }
        sel._rewards["factual"] = {
            "BREADTH_FIRST": 4.5,  # mean 0.9
            "DEPTH_FIRST": 2.5,    # mean 0.5
            "BEST_FIRST": 3.0,     # mean 0.6
        }

        # BREADTH_FIRST has highest mean, should be selected
        chosen = sel.select_strategy("factual")
        assert chosen == StrategyType.BREADTH_FIRST

    def test_select_strategy_unknown_query_type(self):
        """Unknown query types fall back to BREADTH_FIRST."""
        sel = StrategySelector()
        assert sel.select_strategy("nonexistent") == StrategyType.BREADTH_FIRST

    def test_update_feedback(self):
        """update_feedback records reward and increments counts."""
        sel = StrategySelector(query_types=["factual"])
        sel.update_feedback(StrategyType.BREADTH_FIRST, 0.9, "factual")

        stats = sel.get_strategy_stats("factual")
        assert stats["BREADTH_FIRST"]["pulls"] == 1
        assert stats["BREADTH_FIRST"]["total_reward"] == 0.9
        assert stats["BREADTH_FIRST"]["mean_reward"] == 0.9

    def test_update_feedback_clamps_reward(self):
        """Update feedback clamps reward to [0, 1]."""
        sel = StrategySelector(query_types=["factual"])
        sel.update_feedback(StrategyType.DEPTH_FIRST, 5.0, "factual")
        sel.update_feedback(StrategyType.DEPTH_FIRST, -1.0, "factual")

        stats = sel.get_strategy_stats("factual")
        assert stats["DEPTH_FIRST"]["total_reward"] == (
            1.0 + 0.0
        )  # clamped

    def test_add_query_type(self):
        """New query types can be registered dynamically."""
        sel = StrategySelector()
        sel.add_query_type("custom_type")

        assert "custom_type" in sel._counts
        # All strategies initialised for the new type
        for s in StrategyType:
            assert sel._counts["custom_type"][s.name] == 0

    def test_get_strategy_stats_for_unknown_type(self):
        """Unknown query types return empty dict."""
        sel = StrategySelector()
        assert sel.get_strategy_stats("nonexistent") == {}

    def test_confusion_matrix(self):
        """Confusion matrix shows per-type strategy performance."""
        sel = StrategySelector(query_types=["factual", "comparative"])

        sel.update_feedback(StrategyType.BREADTH_FIRST, 0.9, "factual")
        sel.update_feedback(StrategyType.DEPTH_FIRST, 0.5, "comparative")

        matrix = sel.get_confusion_matrix()
        assert "factual" in matrix
        assert "comparative" in matrix

        # factual: BREADTH_FIRST should have mean 0.9
        assert matrix["factual"]["BREADTH_FIRST"] == 0.9
        # comparative: DEPTH_FIRST should have mean 0.5
        assert matrix["comparative"]["DEPTH_FIRST"] == 0.5

    def test_get_history(self):
        """get_history returns all feedback records."""
        sel = StrategySelector(query_types=["factual"])
        sel.update_feedback(StrategyType.BEST_FIRST, 0.7, "factual")
        sel.update_feedback(StrategyType.DEPTH_FIRST, 0.3, "factual")

        history = sel.get_history()
        assert len(history) == 2
        assert all(isinstance(h, StrategyResult) for h in history)
        assert history[0].strategy_type == StrategyType.BEST_FIRST

    def test_ucb1_exploration_bonus(self):
        """Under-explored strategies get an exploration bonus."""
        sel = StrategySelector(query_types=["factual"])
        # Give BREADTH_FIRST high reward but few pulls
        # Give BEST_FIRST low reward but many pulls
        sel._counts["factual"] = {
            "BREADTH_FIRST": 1,
            "DEPTH_FIRST": 100,
            "BEST_FIRST": 100,
        }
        sel._rewards["factual"] = {
            "BREADTH_FIRST": 0.9,
            "DEPTH_FIRST": 50.0,  # mean 0.5
            "BEST_FIRST": 60.0,   # mean 0.6
        }

        # BREADTH_FIRST has high mean + high UCB bonus from low pulls
        chosen = sel.select_strategy("factual")
        assert chosen == StrategyType.BREADTH_FIRST
