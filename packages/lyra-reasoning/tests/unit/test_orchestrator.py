"""
Unit tests for Reasoning Orchestrator.
"""

import pytest

from lyra_reasoning.orchestrator import (
    ComputeAllocator,
    DifficultyEstimator,
    ReasoningOrchestrator,
    StrategySelector,
)
from lyra_reasoning.types import (
    ComputeBudget,
    DifficultyLevel,
    ReasoningConfig,
    ReasoningDepth,
    ReasoningStrategy,
)


class TestDifficultyEstimator:
    """Test DifficultyEstimator functionality."""
    
    def test_trivial_task(self):
        """Test estimation of trivial task."""
        estimator = DifficultyEstimator()
        estimate = estimator.estimate("What is 2 + 2?")
        
        assert estimate.level in [DifficultyLevel.TRIVIAL, DifficultyLevel.EASY]
        assert 0.0 <= estimate.confidence <= 1.0
        assert estimate.recommended_strategy in ReasoningStrategy
        assert isinstance(estimate.recommended_budget, ComputeBudget)
    
    def test_easy_task(self):
        """Test estimation of easy task."""
        estimator = DifficultyEstimator()
        estimate = estimator.estimate("Explain how photosynthesis works")
        
        assert estimate.level in [DifficultyLevel.EASY, DifficultyLevel.MEDIUM]
        assert estimate.confidence > 0.5
    
    def test_medium_task(self):
        """Test estimation of medium task."""
        estimator = DifficultyEstimator()
        estimate = estimator.estimate(
            "Analyze the trade-offs between different sorting algorithms"
        )
        
        assert estimate.level in [DifficultyLevel.MEDIUM, DifficultyLevel.HARD]
    
    def test_hard_task(self):
        """Test estimation of hard task."""
        estimator = DifficultyEstimator()
        estimate = estimator.estimate(
            "Prove that the sum of two odd numbers is always even, "
            "then derive a general theorem for arithmetic operations"
        )
        
        assert estimate.level in [DifficultyLevel.HARD, DifficultyLevel.VERY_HARD]
    
    def test_very_hard_task(self):
        """Test estimation of very hard task."""
        estimator = DifficultyEstimator()
        estimate = estimator.estimate(
            "Prove the Riemann Hypothesis and explain its implications "
            "for number theory, cryptography, and quantum computing. "
            "Provide step-by-step mathematical derivations."
        )
        
        assert estimate.level in [DifficultyLevel.HARD, DifficultyLevel.VERY_HARD]
    
    def test_budget_scaling(self):
        """Test that budget scales with difficulty."""
        estimator = DifficultyEstimator()
        
        easy_estimate = estimator.estimate("Simple question")
        hard_estimate = estimator.estimate(
            "Complex multi-step proof with derivations and analysis"
        )
        
        # Hard tasks should get more budget
        assert (
            hard_estimate.recommended_budget.max_tokens >=
            easy_estimate.recommended_budget.max_tokens
        )


class TestStrategySelector:
    """Test StrategySelector functionality."""
    
    def test_user_specified_strategy(self):
        """Test that user-specified strategy is respected."""
        selector = StrategySelector()
        
        config = ReasoningConfig(strategy=ReasoningStrategy.TREE_SEARCH)
        estimate = DifficultyEstimator().estimate("Test task")
        
        strategy = selector.select("Test task", estimate, config)
        
        assert strategy == ReasoningStrategy.TREE_SEARCH
    
    def test_auto_strategy_selection(self):
        """Test automatic strategy selection."""
        selector = StrategySelector()
        
        config = ReasoningConfig(strategy=ReasoningStrategy.AUTO)
        estimate = DifficultyEstimator().estimate("Test task")
        
        strategy = selector.select("Test task", estimate, config)
        
        assert strategy in ReasoningStrategy
        assert strategy != ReasoningStrategy.AUTO
    
    def test_hypothesis_task_detection(self):
        """Test detection of hypothesis generation tasks."""
        selector = StrategySelector()
        
        config = ReasoningConfig(strategy=ReasoningStrategy.AUTO)
        estimate = DifficultyEstimator().estimate(
            "Propose novel hypotheses for dark matter composition"
        )
        
        strategy = selector.select(
            "Propose novel hypotheses for dark matter composition",
            estimate,
            config,
        )
        
        # Should recommend hypothesis strategy
        assert strategy == ReasoningStrategy.HYPOTHESIS
    
    def test_performance_recording(self):
        """Test recording strategy performance."""
        selector = StrategySelector()
        
        # Record some performances
        selector.record_performance(
            ReasoningStrategy.CHAIN_OF_THOUGHT,
            success=True,
            tokens=1000,
            duration=10.0,
        )
        
        selector.record_performance(
            ReasoningStrategy.CHAIN_OF_THOUGHT,
            success=False,
            tokens=1500,
            duration=15.0,
        )
        
        # Check history
        assert ReasoningStrategy.CHAIN_OF_THOUGHT in selector.strategy_history
        stats = selector.strategy_history[ReasoningStrategy.CHAIN_OF_THOUGHT]
        assert stats["uses"] == 2
        assert stats["successes"] == 1


class TestComputeAllocator:
    """Test ComputeAllocator functionality."""
    
    def test_base_allocation(self):
        """Test base compute allocation."""
        allocator = ComputeAllocator()
        
        estimate = DifficultyEstimator().estimate("Medium task")
        config = ReasoningConfig(depth=ReasoningDepth.STANDARD)
        
        budget = allocator.allocate(estimate, config)
        
        assert isinstance(budget, ComputeBudget)
        assert budget.max_tokens > 0
        assert budget.max_time_seconds > 0
        assert budget.max_steps > 0
    
    def test_depth_scaling(self):
        """Test that budget scales with depth."""
        allocator = ComputeAllocator()
        estimate = DifficultyEstimator().estimate("Test task")
        
        quick_config = ReasoningConfig(depth=ReasoningDepth.QUICK)
        standard_config = ReasoningConfig(depth=ReasoningDepth.STANDARD)
        comprehensive_config = ReasoningConfig(depth=ReasoningDepth.COMPREHENSIVE)
        
        quick_budget = allocator.allocate(estimate, quick_config)
        standard_budget = allocator.allocate(estimate, standard_config)
        comprehensive_budget = allocator.allocate(estimate, comprehensive_config)
        
        # Budget should increase with depth
        assert quick_budget.max_tokens < standard_budget.max_tokens
        assert standard_budget.max_tokens < comprehensive_budget.max_tokens
    
    def test_user_limits_respected(self):
        """Test that user-specified limits are respected."""
        allocator = ComputeAllocator()
        estimate = DifficultyEstimator().estimate("Test task")
        
        config = ReasoningConfig(
            depth=ReasoningDepth.COMPREHENSIVE,
            max_tokens=500,  # Very low limit
            max_steps=5,
        )
        
        budget = allocator.allocate(estimate, config)
        
        # Should not exceed user limits
        assert budget.max_tokens <= 500
        assert budget.max_steps <= 5


class TestReasoningOrchestrator:
    """Test ReasoningOrchestrator functionality."""
    
    def test_initialization(self):
        """Test orchestrator initialization."""
        orchestrator = ReasoningOrchestrator()
        
        assert orchestrator.difficulty_estimator is not None
        assert orchestrator.strategy_selector is not None
        assert orchestrator.compute_allocator is not None
    
    def test_prepare(self):
        """Test preparation for reasoning."""
        orchestrator = ReasoningOrchestrator()
        
        strategy, budget, difficulty = orchestrator.prepare("Test task")
        
        assert strategy in ReasoningStrategy
        assert isinstance(budget, ComputeBudget)
        assert difficulty.level in DifficultyLevel
    
    def test_prepare_with_config(self):
        """Test preparation with custom config."""
        orchestrator = ReasoningOrchestrator()
        
        config = ReasoningConfig(
            strategy=ReasoningStrategy.DEBATE,
            depth=ReasoningDepth.COMPREHENSIVE,
        )
        
        strategy, budget, difficulty = orchestrator.prepare("Test task", config)
        
        assert strategy == ReasoningStrategy.DEBATE
        assert budget.max_tokens > 5000  # Comprehensive depth
    
    def test_should_stop_budget_exhausted(self):
        """Test early stopping when budget exhausted."""
        orchestrator = ReasoningOrchestrator()
        
        budget = ComputeBudget(
            max_tokens=100,
            max_time_seconds=10,
            max_steps=5,
        )
        budget.tokens_used = 100  # Exhausted
        
        should_stop = orchestrator.should_stop(budget, 3, 0.5)
        
        assert should_stop is True
    
    def test_should_stop_high_confidence(self):
        """Test early stopping with high confidence."""
        orchestrator = ReasoningOrchestrator()
        
        budget = ComputeBudget(
            max_tokens=10000,
            max_time_seconds=100,
            max_steps=50,
        )
        
        should_stop = orchestrator.should_stop(
            budget,
            steps_count=10,
            current_score=0.95,
            threshold=0.8,
        )
        
        assert should_stop is True
    
    def test_should_not_stop_early(self):
        """Test that reasoning doesn't stop too early."""
        orchestrator = ReasoningOrchestrator()
        
        budget = ComputeBudget(
            max_tokens=10000,
            max_time_seconds=100,
            max_steps=50,
        )
        
        should_stop = orchestrator.should_stop(
            budget,
            steps_count=2,  # Too few steps
            current_score=0.6,
        )
        
        assert should_stop is False
    
    def test_record_execution(self):
        """Test recording execution results."""
        orchestrator = ReasoningOrchestrator()
        
        # Should not raise any errors
        orchestrator.record_execution(
            ReasoningStrategy.CHAIN_OF_THOUGHT,
            success=True,
            tokens=1000,
            duration=10.0,
        )
