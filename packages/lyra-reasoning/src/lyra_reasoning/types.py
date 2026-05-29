"""
Core data models for the Deep Reasoning Research Agent.
"""

from dataclasses import dataclass, field
from datetime import datetime
from enum import Enum
from typing import Any, Dict, List, Optional

from pydantic import BaseModel, Field


class ReasoningStrategy(str, Enum):
    """Available reasoning strategies."""

    AUTO = "auto"
    CHAIN_OF_THOUGHT = "cot"
    TREE_SEARCH = "tree_search"
    TREE_OF_THOUGHTS = "tot"  # Alias for tree_search
    REACT = "react"  # Reasoning + Acting
    DEBATE = "debate"
    HYPOTHESIS = "hypothesis"


class ReasoningDepth(str, Enum):
    """Reasoning depth levels."""

    QUICK = "quick"
    STANDARD = "standard"
    COMPREHENSIVE = "comprehensive"


class StepType(str, Enum):
    """Types of reasoning steps."""

    HYPOTHESIS = "hypothesis"
    EVIDENCE = "evidence"
    ANALYSIS = "analysis"
    CONCLUSION = "conclusion"
    VERIFICATION = "verification"
    BACKTRACK = "backtrack"


class DifficultyLevel(str, Enum):
    """Task difficulty levels."""

    TRIVIAL = "trivial"
    EASY = "easy"
    MEDIUM = "medium"
    HARD = "hard"
    VERY_HARD = "very_hard"


@dataclass
class ReasoningStep:
    """A single step in a reasoning trace."""

    content: str
    step_type: StepType
    verification_score: float = 0.0
    alternatives_considered: List[str] = field(default_factory=list)
    timestamp: datetime = field(default_factory=datetime.now)
    metadata: Dict[str, Any] = field(default_factory=dict)


@dataclass
class VerificationResult:
    """Result of reasoning verification."""

    overall_score: float
    step_scores: List[float]
    trace_score: float
    external_scores: List[float]
    cross_agent_scores: List[float]
    passed: bool
    details: Dict[str, Any] = field(default_factory=dict)


@dataclass
class ReasoningTrace:
    """Complete reasoning trace for a task."""

    task: str
    strategy: ReasoningStrategy
    steps: List[ReasoningStep]
    verification: Optional[VerificationResult] = None
    outcome: str = "pending"  # success/failure/pending
    duration: float = 0.0
    token_count: int = 0
    timestamp: datetime = field(default_factory=datetime.now)
    metadata: Dict[str, Any] = field(default_factory=dict)

    def add_step(self, step: ReasoningStep) -> None:
        """Add a reasoning step to the trace."""
        self.steps.append(step)

    def get_conclusion(self) -> Optional[str]:
        """Get the final conclusion from the trace."""
        conclusion_steps = [s for s in self.steps if s.step_type == StepType.CONCLUSION]
        return conclusion_steps[-1].content if conclusion_steps else None


class ReasoningConfig(BaseModel):
    """Configuration for reasoning execution."""

    strategy: ReasoningStrategy = Field(default=ReasoningStrategy.AUTO)
    depth: ReasoningDepth = Field(default=ReasoningDepth.STANDARD)
    max_tokens: int = Field(default=10000, ge=100, le=100000)
    max_steps: int = Field(default=50, ge=1, le=500)
    verification_threshold: float = Field(default=0.7, ge=0.0, le=1.0)
    enable_backtracking: bool = Field(default=True)
    enable_verification: bool = Field(default=True)
    temperature: float = Field(default=0.7, ge=0.0, le=2.0)
    model: str = Field(default="claude-3-5-sonnet-20241022")


@dataclass
class ComputeBudget:
    """Compute budget for reasoning."""

    max_tokens: int
    max_time_seconds: float = 300.0  # Default 5 minutes
    max_steps: int = 50
    tokens_used: int = 0
    time_used: float = 0.0
    steps_used: int = 0

    def has_budget(self) -> bool:
        """Check if budget remains."""
        return (
            self.tokens_used < self.max_tokens
            and self.time_used < self.max_time_seconds
            and self.steps_used < self.max_steps
        )

    def use_tokens(self, count: int) -> None:
        """Use tokens from budget."""
        self.tokens_used += count

    def use_time(self, seconds: float) -> None:
        """Use time from budget."""
        self.time_used += seconds

    def use_step(self) -> None:
        """Use a step from budget."""
        self.steps_used += 1


@dataclass
class DifficultyEstimate:
    """Estimated difficulty of a task."""

    level: DifficultyLevel
    confidence: float
    reasoning: str
    recommended_strategy: ReasoningStrategy
    recommended_budget: ComputeBudget


class ReasoningResult(BaseModel):
    """Final result of reasoning execution."""

    task: str
    conclusion: str
    reasoning_trace: Optional[Dict[str, Any]] = None
    verification_score: float
    strategy_used: ReasoningStrategy
    tokens_used: int
    duration: float
    success: bool
    metadata: Dict[str, Any] = Field(default_factory=dict)


@dataclass
class ReasoningPattern:
    """A learned reasoning pattern."""

    name: str
    description: str
    pattern_type: str
    success_rate: float
    usage_count: int
    avg_tokens: float
    avg_duration: float
    applicable_tasks: List[str]
    steps_template: List[StepType]
    metadata: Dict[str, Any] = field(default_factory=dict)


@dataclass
class StrategyPerformance:
    """Performance metrics for a reasoning strategy."""

    strategy: ReasoningStrategy
    total_uses: int
    success_count: int
    failure_count: int
    avg_tokens: float
    avg_duration: float
    avg_verification_score: float

    @property
    def success_rate(self) -> float:
        """Calculate success rate."""
        if self.total_uses == 0:
            return 0.0
        return self.success_count / self.total_uses
