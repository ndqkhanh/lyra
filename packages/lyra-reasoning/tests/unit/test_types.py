"""
Unit tests for core types and data models.
"""

import pytest
from datetime import datetime

from lyra_reasoning.types import (
    ComputeBudget,
    DifficultyLevel,
    ReasoningConfig,
    ReasoningDepth,
    ReasoningStep,
    ReasoningStrategy,
    ReasoningTrace,
    StepType,
)


class TestComputeBudget:
    """Test ComputeBudget functionality."""
    
    def test_initialization(self):
        """Test budget initialization."""
        budget = ComputeBudget(
            max_tokens=1000,
            max_time_seconds=60,
            max_steps=10,
        )
        
        assert budget.max_tokens == 1000
        assert budget.max_time_seconds == 60
        assert budget.max_steps == 10
        assert budget.tokens_used == 0
        assert budget.time_used == 0.0
        assert budget.steps_used == 0
    
    def test_has_budget(self):
        """Test budget checking."""
        budget = ComputeBudget(
            max_tokens=1000,
            max_time_seconds=60,
            max_steps=10,
        )
        
        assert budget.has_budget() is True
        
        # Exhaust token budget
        budget.tokens_used = 1000
        assert budget.has_budget() is False
    
    def test_use_tokens(self):
        """Test token usage."""
        budget = ComputeBudget(
            max_tokens=1000,
            max_time_seconds=60,
            max_steps=10,
        )
        
        budget.use_tokens(100)
        assert budget.tokens_used == 100
        
        budget.use_tokens(200)
        assert budget.tokens_used == 300
    
    def test_use_time(self):
        """Test time usage."""
        budget = ComputeBudget(
            max_tokens=1000,
            max_time_seconds=60,
            max_steps=10,
        )
        
        budget.use_time(10.5)
        assert budget.time_used == 10.5
        
        budget.use_time(5.5)
        assert budget.time_used == 16.0
    
    def test_use_step(self):
        """Test step usage."""
        budget = ComputeBudget(
            max_tokens=1000,
            max_time_seconds=60,
            max_steps=10,
        )
        
        budget.use_step()
        assert budget.steps_used == 1
        
        budget.use_step()
        assert budget.steps_used == 2


class TestReasoningStep:
    """Test ReasoningStep functionality."""
    
    def test_initialization(self):
        """Test step initialization."""
        step = ReasoningStep(
            content="This is a hypothesis",
            step_type=StepType.HYPOTHESIS,
        )
        
        assert step.content == "This is a hypothesis"
        assert step.step_type == StepType.HYPOTHESIS
        assert step.verification_score == 0.0
        assert step.alternatives_considered == []
        assert isinstance(step.timestamp, datetime)
    
    def test_with_verification(self):
        """Test step with verification score."""
        step = ReasoningStep(
            content="This is evidence",
            step_type=StepType.EVIDENCE,
            verification_score=0.85,
        )
        
        assert step.verification_score == 0.85
    
    def test_with_alternatives(self):
        """Test step with alternatives."""
        step = ReasoningStep(
            content="Main reasoning",
            step_type=StepType.ANALYSIS,
            alternatives_considered=["Alt 1", "Alt 2"],
        )
        
        assert len(step.alternatives_considered) == 2


class TestReasoningTrace:
    """Test ReasoningTrace functionality."""
    
    def test_initialization(self):
        """Test trace initialization."""
        trace = ReasoningTrace(
            task="Test task",
            strategy=ReasoningStrategy.CHAIN_OF_THOUGHT,
            steps=[],
        )
        
        assert trace.task == "Test task"
        assert trace.strategy == ReasoningStrategy.CHAIN_OF_THOUGHT
        assert trace.steps == []
        assert trace.outcome == "pending"
    
    def test_add_step(self):
        """Test adding steps to trace."""
        trace = ReasoningTrace(
            task="Test task",
            strategy=ReasoningStrategy.CHAIN_OF_THOUGHT,
            steps=[],
        )
        
        step1 = ReasoningStep(
            content="Step 1",
            step_type=StepType.HYPOTHESIS,
        )
        trace.add_step(step1)
        
        assert len(trace.steps) == 1
        assert trace.steps[0] == step1
    
    def test_get_conclusion(self):
        """Test getting conclusion from trace."""
        trace = ReasoningTrace(
            task="Test task",
            strategy=ReasoningStrategy.CHAIN_OF_THOUGHT,
            steps=[],
        )
        
        # No conclusion yet
        assert trace.get_conclusion() is None
        
        # Add non-conclusion steps
        trace.add_step(ReasoningStep(
            content="Hypothesis",
            step_type=StepType.HYPOTHESIS,
        ))
        assert trace.get_conclusion() is None
        
        # Add conclusion
        trace.add_step(ReasoningStep(
            content="Final conclusion",
            step_type=StepType.CONCLUSION,
        ))
        assert trace.get_conclusion() == "Final conclusion"


class TestReasoningConfig:
    """Test ReasoningConfig functionality."""
    
    def test_default_config(self):
        """Test default configuration."""
        config = ReasoningConfig()
        
        assert config.strategy == ReasoningStrategy.AUTO
        assert config.depth == ReasoningDepth.STANDARD
        assert config.max_tokens == 10000
        assert config.max_steps == 50
        assert config.verification_threshold == 0.7
        assert config.enable_backtracking is True
        assert config.enable_verification is True
    
    def test_custom_config(self):
        """Test custom configuration."""
        config = ReasoningConfig(
            strategy=ReasoningStrategy.TREE_SEARCH,
            depth=ReasoningDepth.COMPREHENSIVE,
            max_tokens=20000,
            max_steps=100,
        )
        
        assert config.strategy == ReasoningStrategy.TREE_SEARCH
        assert config.depth == ReasoningDepth.COMPREHENSIVE
        assert config.max_tokens == 20000
        assert config.max_steps == 100
    
    def test_validation(self):
        """Test configuration validation."""
        # Valid config
        config = ReasoningConfig(max_tokens=1000)
        assert config.max_tokens == 1000
        
        # Invalid configs should raise validation errors
        with pytest.raises(Exception):
            ReasoningConfig(max_tokens=50)  # Too low
        
        with pytest.raises(Exception):
            ReasoningConfig(verification_threshold=1.5)  # Too high


class TestEnums:
    """Test enum types."""
    
    def test_reasoning_strategy(self):
        """Test ReasoningStrategy enum."""
        assert ReasoningStrategy.AUTO.value == "auto"
        assert ReasoningStrategy.CHAIN_OF_THOUGHT.value == "cot"
        assert ReasoningStrategy.TREE_SEARCH.value == "tree_search"
        assert ReasoningStrategy.DEBATE.value == "debate"
        assert ReasoningStrategy.HYPOTHESIS.value == "hypothesis"
    
    def test_reasoning_depth(self):
        """Test ReasoningDepth enum."""
        assert ReasoningDepth.QUICK.value == "quick"
        assert ReasoningDepth.STANDARD.value == "standard"
        assert ReasoningDepth.COMPREHENSIVE.value == "comprehensive"
    
    def test_step_type(self):
        """Test StepType enum."""
        assert StepType.HYPOTHESIS.value == "hypothesis"
        assert StepType.EVIDENCE.value == "evidence"
        assert StepType.ANALYSIS.value == "analysis"
        assert StepType.CONCLUSION.value == "conclusion"
        assert StepType.VERIFICATION.value == "verification"
        assert StepType.BACKTRACK.value == "backtrack"
    
    def test_difficulty_level(self):
        """Test DifficultyLevel enum."""
        assert DifficultyLevel.TRIVIAL.value == "trivial"
        assert DifficultyLevel.EASY.value == "easy"
        assert DifficultyLevel.MEDIUM.value == "medium"
        assert DifficultyLevel.HARD.value == "hard"
        assert DifficultyLevel.VERY_HARD.value == "very_hard"
