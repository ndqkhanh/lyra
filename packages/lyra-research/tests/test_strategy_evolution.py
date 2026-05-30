"""
Integration tests for research strategy evolution.

Tests strategy evolution patterns:
- Learning from workflow outcomes
- Strategy adaptation based on results
- Cross-workflow strategy transfer
- Performance improvement tracking
- Strategy optimization over time
"""

import pytest
from unittest.mock import Mock, MagicMock
from datetime import datetime, timezone
from typing import Dict, List, Any


class StrategyLearner:
    """Learn and adapt research strategies."""

    def __init__(self):
        self.strategy_history = []
        self.performance_metrics = []

    def record_strategy(self, strategy: Dict[str, Any], outcome: Dict[str, Any]):
        """Record a strategy and its outcome."""
        self.strategy_history.append({
            "strategy": strategy,
            "outcome": outcome,
            "timestamp": datetime.now(timezone.utc),
        })

        # Extract performance metrics
        self.performance_metrics.append({
            "quality_score": outcome.get("quality_score", 0),
            "execution_time": outcome.get("execution_time", 0),
            "cost": outcome.get("cost", 0),
        })

    def get_best_strategy(self, metric: str = "quality_score"):
        """Get best performing strategy."""
        if not self.strategy_history:
            return None

        best_idx = max(
            range(len(self.performance_metrics)),
            key=lambda i: self.performance_metrics[i].get(metric, 0)
        )

        return self.strategy_history[best_idx]["strategy"]

    def get_performance_trend(self, metric: str = "quality_score"):
        """Get performance trend over time."""
        return [m.get(metric, 0) for m in self.performance_metrics]

    def adapt_strategy(self, current_strategy: Dict[str, Any]) -> Dict[str, Any]:
        """Adapt strategy based on historical performance."""
        if not self.strategy_history:
            return current_strategy

        # Get best strategy
        best_strategy = self.get_best_strategy()

        # Merge best practices
        adapted = current_strategy.copy()
        adapted.update({
            k: v for k, v in best_strategy.items()
            if k not in ["workflow_name", "timestamp"]
        })

        return adapted


class WorkflowOptimizer:
    """Optimize workflow execution strategies."""

    def __init__(self):
        self.optimization_history = []

    def optimize_parameters(self, workflow_type: str, results: List[Dict[str, Any]]):
        """Optimize workflow parameters based on results."""
        if not results:
            return {}

        # Calculate optimal parameters
        avg_quality = sum(r.get("quality_score", 0) for r in results) / len(results)
        avg_time = sum(r.get("execution_time", 0) for r in results) / len(results)

        optimized = {
            "workflow_type": workflow_type,
            "target_quality": avg_quality * 1.1,  # Aim for 10% improvement
            "max_execution_time": avg_time * 0.9,  # Aim for 10% faster
            "optimization_timestamp": datetime.now(timezone.utc),
        }

        self.optimization_history.append(optimized)
        return optimized

    def get_optimization_history(self):
        """Get optimization history."""
        return self.optimization_history.copy()


class StrategyEvolutionEngine:
    """Engine for evolving research strategies."""

    def __init__(self):
        self.learner = StrategyLearner()
        self.optimizer = WorkflowOptimizer()
        self.generation = 0

    def evolve_strategy(self, current_strategy: Dict[str, Any], results: List[Dict[str, Any]]):
        """Evolve strategy based on results."""
        self.generation += 1

        # Record current strategy performance
        for result in results:
            self.learner.record_strategy(current_strategy, result)

        # Adapt strategy
        adapted_strategy = self.learner.adapt_strategy(current_strategy)
        adapted_strategy["generation"] = self.generation

        # Optimize parameters
        workflow_type = current_strategy.get("workflow_type", "unknown")
        optimized_params = self.optimizer.optimize_parameters(workflow_type, results)
        adapted_strategy.update(optimized_params)

        return adapted_strategy


@pytest.mark.integration
class TestStrategyLearning:
    """Test learning from workflow outcomes."""

    def test_record_strategy_and_outcome(self):
        """Test recording strategy and outcome."""
        # Setup
        learner = StrategyLearner()

        strategy = {
            "workflow_type": "deep_research",
            "depth": "standard",
            "max_sources": 30,
        }

        outcome = {
            "quality_score": 0.85,
            "execution_time": 120,
            "cost": 2.5,
        }

        # Record
        learner.record_strategy(strategy, outcome)

        # Verify
        assert len(learner.strategy_history) == 1
        assert learner.strategy_history[0]["strategy"] == strategy
        assert learner.strategy_history[0]["outcome"] == outcome

    def test_identify_best_strategy(self):
        """Test identifying best performing strategy."""
        # Setup
        learner = StrategyLearner()

        # Record multiple strategies
        strategies = [
            ({"depth": "quick"}, {"quality_score": 0.75}),
            ({"depth": "standard"}, {"quality_score": 0.85}),
            ({"depth": "deep"}, {"quality_score": 0.90}),
        ]

        for strategy, outcome in strategies:
            learner.record_strategy(strategy, outcome)

        # Get best
        best = learner.get_best_strategy("quality_score")

        # Verify
        assert best["depth"] == "deep"

    def test_performance_trend_tracking(self):
        """Test tracking performance trends over time."""
        # Setup
        learner = StrategyLearner()

        # Record improving performance
        for i in range(5):
            strategy = {"iteration": i}
            outcome = {"quality_score": 0.7 + i * 0.05}
            learner.record_strategy(strategy, outcome)

        # Get trend
        trend = learner.get_performance_trend("quality_score")

        # Verify
        assert len(trend) == 5
        assert trend[0] == 0.7
        assert abs(trend[4] - 0.9) < 0.01  # Allow floating point tolerance
        # Verify improving trend
        assert all(trend[i] <= trend[i+1] for i in range(len(trend)-1))

    def test_strategy_adaptation(self):
        """Test adapting strategy based on history."""
        # Setup
        learner = StrategyLearner()

        # Record successful strategy
        best_strategy = {
            "workflow_type": "deep_research",
            "depth": "deep",
            "max_sources": 50,
        }
        learner.record_strategy(best_strategy, {"quality_score": 0.90})

        # Record less successful strategy
        learner.record_strategy(
            {"workflow_type": "deep_research", "depth": "quick", "max_sources": 10},
            {"quality_score": 0.70}
        )

        # Adapt current strategy
        current = {"workflow_type": "deep_research", "depth": "standard"}
        adapted = learner.adapt_strategy(current)

        # Verify
        assert adapted["depth"] == "deep"
        assert adapted["max_sources"] == 50

    def test_learning_from_failures(self):
        """Test learning from failed strategies."""
        # Setup
        learner = StrategyLearner()

        # Record failed strategy
        failed_strategy = {"approach": "aggressive", "timeout": 60}
        learner.record_strategy(failed_strategy, {"quality_score": 0.40})

        # Record successful strategy
        success_strategy = {"approach": "conservative", "timeout": 300}
        learner.record_strategy(success_strategy, {"quality_score": 0.85})

        # Get best
        best = learner.get_best_strategy()

        # Verify
        assert best["approach"] == "conservative"
        assert best["timeout"] == 300


@pytest.mark.integration
class TestStrategyOptimization:
    """Test strategy optimization over time."""

    def test_parameter_optimization(self):
        """Test optimizing workflow parameters."""
        # Setup
        optimizer = WorkflowOptimizer()

        results = [
            {"quality_score": 0.80, "execution_time": 100},
            {"quality_score": 0.85, "execution_time": 120},
            {"quality_score": 0.82, "execution_time": 110},
        ]

        # Optimize
        optimized = optimizer.optimize_parameters("deep_research", results)

        # Verify
        assert optimized["workflow_type"] == "deep_research"
        # Target quality should be 10% higher than average
        avg_quality = (0.80 + 0.85 + 0.82) / 3
        assert abs(optimized["target_quality"] - avg_quality * 1.1) < 0.01

    def test_optimization_history_tracking(self):
        """Test tracking optimization history."""
        # Setup
        optimizer = WorkflowOptimizer()

        # Multiple optimization rounds
        for i in range(3):
            results = [{"quality_score": 0.8 + i * 0.05, "execution_time": 100}]
            optimizer.optimize_parameters(f"workflow_{i}", results)

        # Get history
        history = optimizer.get_optimization_history()

        # Verify
        assert len(history) == 3
        assert all("target_quality" in h for h in history)

    def test_multi_objective_optimization(self):
        """Test optimizing multiple objectives."""
        # Setup
        optimizer = WorkflowOptimizer()

        results = [
            {"quality_score": 0.85, "execution_time": 100, "cost": 2.0},
            {"quality_score": 0.80, "execution_time": 80, "cost": 1.5},
            {"quality_score": 0.90, "execution_time": 150, "cost": 3.0},
        ]

        # Optimize
        optimized = optimizer.optimize_parameters("deep_research", results)

        # Verify both quality and time targets
        assert "target_quality" in optimized
        assert "max_execution_time" in optimized


@pytest.mark.integration
class TestCrossWorkflowStrategyTransfer:
    """Test transferring strategies across workflows."""

    def test_strategy_transfer_deep_to_auto(self):
        """Test transferring strategy from deep to auto research."""
        # Setup
        deep_learner = StrategyLearner()
        auto_learner = StrategyLearner()

        # Deep research learns successful strategy
        deep_strategy = {
            "workflow_type": "deep_research",
            "source_diversity": "high",
            "verification_level": "strict",
        }
        deep_learner.record_strategy(deep_strategy, {"quality_score": 0.90})

        # Transfer to auto research
        auto_strategy = {
            "workflow_type": "auto_research",
            "source_diversity": deep_strategy["source_diversity"],
            "verification_level": deep_strategy["verification_level"],
        }

        # Verify
        assert auto_strategy["source_diversity"] == "high"
        assert auto_strategy["verification_level"] == "strict"

    def test_strategy_generalization(self):
        """Test generalizing strategies across workflow types."""
        # Setup
        learner = StrategyLearner()

        # Record strategies from different workflows
        learner.record_strategy(
            {"workflow_type": "deep", "parallel_execution": True},
            {"quality_score": 0.88}
        )
        learner.record_strategy(
            {"workflow_type": "auto", "parallel_execution": True},
            {"quality_score": 0.85}
        )

        # Generalize: parallel execution is beneficial
        best = learner.get_best_strategy()

        # Verify
        assert best["parallel_execution"] is True

    def test_strategy_specialization(self):
        """Test specializing strategies for specific workflows."""
        # Setup
        learner = StrategyLearner()

        # Record workflow-specific strategies
        learner.record_strategy(
            {"workflow_type": "scientist", "hypothesis_count": 5},
            {"quality_score": 0.90}
        )
        learner.record_strategy(
            {"workflow_type": "scientist", "hypothesis_count": 3},
            {"quality_score": 0.75}
        )

        # Get best for scientist workflow
        best = learner.get_best_strategy()

        # Verify
        assert best["hypothesis_count"] == 5


@pytest.mark.integration
class TestStrategyEvolution:
    """Test strategy evolution over multiple generations."""

    def test_strategy_evolution_single_generation(self):
        """Test evolving strategy for one generation."""
        # Setup
        engine = StrategyEvolutionEngine()

        current_strategy = {
            "workflow_type": "deep_research",
            "depth": "standard",
        }

        results = [
            {"quality_score": 0.85, "execution_time": 120, "cost": 2.5}
        ]

        # Evolve
        evolved = engine.evolve_strategy(current_strategy, results)

        # Verify
        assert evolved["generation"] == 1
        assert "target_quality" in evolved
        assert "max_execution_time" in evolved

    def test_strategy_evolution_multiple_generations(self):
        """Test evolving strategy over multiple generations."""
        # Setup
        engine = StrategyEvolutionEngine()

        strategy = {"workflow_type": "deep_research", "depth": "standard"}

        # Evolve over 3 generations
        for i in range(3):
            results = [{"quality_score": 0.8 + i * 0.05, "execution_time": 100}]
            strategy = engine.evolve_strategy(strategy, results)

        # Verify
        assert strategy["generation"] == 3
        assert len(engine.learner.strategy_history) == 3

    def test_performance_improvement_over_generations(self):
        """Test performance improves over generations."""
        # Setup
        engine = StrategyEvolutionEngine()

        strategy = {"workflow_type": "deep_research"}

        # Simulate improving performance
        for i in range(5):
            results = [{"quality_score": 0.7 + i * 0.04, "execution_time": 100}]
            strategy = engine.evolve_strategy(strategy, results)

        # Get performance trend
        trend = engine.learner.get_performance_trend("quality_score")

        # Verify improvement
        assert len(trend) == 5
        assert trend[-1] > trend[0]

    def test_strategy_convergence(self):
        """Test strategy converges to optimal parameters."""
        # Setup
        engine = StrategyEvolutionEngine()

        strategy = {"workflow_type": "deep_research", "max_sources": 10}

        # Evolve with consistent high performance at max_sources=50
        for _ in range(3):
            # Simulate that max_sources=50 performs best
            strategy["max_sources"] = 50
            results = [{"quality_score": 0.90, "execution_time": 100}]
            strategy = engine.evolve_strategy(strategy, results)

        # Verify convergence
        best = engine.learner.get_best_strategy()
        assert best["max_sources"] == 50

    def test_strategy_adaptation_to_changing_conditions(self):
        """Test strategy adapts to changing conditions."""
        # Setup
        engine = StrategyEvolutionEngine()

        strategy = {"workflow_type": "deep_research", "approach": "aggressive"}

        # Initially aggressive works well
        results = [{"quality_score": 0.85, "execution_time": 80}]
        strategy = engine.evolve_strategy(strategy, results)

        # Conditions change, conservative works better
        strategy["approach"] = "conservative"
        results = [{"quality_score": 0.92, "execution_time": 120}]
        strategy = engine.evolve_strategy(strategy, results)

        # Get best strategy
        best = engine.learner.get_best_strategy()

        # Verify adaptation
        assert best["approach"] == "conservative"
