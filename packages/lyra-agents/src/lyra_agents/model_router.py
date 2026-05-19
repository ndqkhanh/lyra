"""
Model Router - Intelligent model selection based on task complexity.

Features:
- Automatic model selection (Haiku, Sonnet, Opus)
- Task complexity analysis
- Cost optimization
- Performance tracking
"""

from dataclasses import dataclass
from enum import Enum
from typing import Dict, List, Optional

import tiktoken


class ModelTier(Enum):
    """Model tier for different use cases."""

    HAIKU = "claude-haiku-4-5"  # Fast, cheap
    SONNET = "claude-sonnet-4-6"  # Balanced
    OPUS = "claude-opus-4-7"  # Powerful, expensive


@dataclass
class ModelCapability:
    """Model capability profile."""

    tier: ModelTier
    cost_per_1m_tokens: float
    max_tokens: int
    speed_multiplier: float  # Relative to Opus
    reasoning_score: int  # 1-10
    coding_score: int  # 1-10
    vision_capable: bool = False


# Model profiles
MODEL_PROFILES = {
    ModelTier.HAIKU: ModelCapability(
        tier=ModelTier.HAIKU,
        cost_per_1m_tokens=0.25,
        max_tokens=200000,
        speed_multiplier=3.0,
        reasoning_score=7,
        coding_score=8,
    ),
    ModelTier.SONNET: ModelCapability(
        tier=ModelTier.SONNET,
        cost_per_1m_tokens=3.0,
        max_tokens=200000,
        speed_multiplier=1.5,
        reasoning_score=9,
        coding_score=10,
    ),
    ModelTier.OPUS: ModelCapability(
        tier=ModelTier.OPUS,
        cost_per_1m_tokens=15.0,
        max_tokens=200000,
        speed_multiplier=1.0,
        reasoning_score=10,
        coding_score=10,
    ),
}


class TaskComplexity(Enum):
    """Task complexity levels."""

    SIMPLE = "simple"  # Haiku
    MODERATE = "moderate"  # Sonnet
    COMPLEX = "complex"  # Opus


@dataclass
class RoutingDecision:
    """Model routing decision."""

    selected_model: ModelTier
    reasoning: str
    estimated_cost: float
    estimated_time_seconds: float
    complexity: TaskComplexity


class ModelRouter:
    """
    Intelligent model router.

    Routes tasks to appropriate model based on:
    - Task complexity
    - Token count
    - Required capabilities
    - Cost constraints
    """

    def __init__(self, cost_budget: Optional[float] = None):
        """
        Initialize router.

        Args:
            cost_budget: Maximum cost per request (USD)
        """
        self.cost_budget = cost_budget
        self.encoding = tiktoken.encoding_for_model("gpt-4")

    def route(
        self,
        prompt: str,
        task_type: str = "general",
        require_reasoning: bool = False,
        require_vision: bool = False,
    ) -> RoutingDecision:
        """
        Route task to appropriate model.

        Args:
            prompt: Task prompt
            task_type: Type of task (coding, reasoning, general)
            require_reasoning: Requires deep reasoning
            require_vision: Requires vision capability

        Returns:
            Routing decision
        """
        # Analyze complexity
        complexity = self._analyze_complexity(prompt, task_type)

        # Select model
        if require_vision:
            # Only Opus supports vision currently
            selected = ModelTier.OPUS
            reasoning = "Vision capability required"
        elif require_reasoning or complexity == TaskComplexity.COMPLEX:
            selected = ModelTier.OPUS
            reasoning = "Complex reasoning required"
        elif complexity == TaskComplexity.MODERATE:
            selected = ModelTier.SONNET
            reasoning = "Moderate complexity, balanced performance"
        else:
            selected = ModelTier.HAIKU
            reasoning = "Simple task, optimizing for speed and cost"

        # Check cost budget
        if self.cost_budget:
            token_count = len(self.encoding.encode(prompt))
            estimated_cost = self._estimate_cost(selected, token_count)

            if estimated_cost > self.cost_budget:
                # Downgrade to cheaper model
                if selected == ModelTier.OPUS:
                    selected = ModelTier.SONNET
                    reasoning = "Downgraded to Sonnet due to cost budget"
                elif selected == ModelTier.SONNET:
                    selected = ModelTier.HAIKU
                    reasoning = "Downgraded to Haiku due to cost budget"

        # Calculate estimates
        token_count = len(self.encoding.encode(prompt))
        estimated_cost = self._estimate_cost(selected, token_count)
        estimated_time = self._estimate_time(selected, token_count)

        return RoutingDecision(
            selected_model=selected,
            reasoning=reasoning,
            estimated_cost=estimated_cost,
            estimated_time_seconds=estimated_time,
            complexity=complexity,
        )

    def _analyze_complexity(self, prompt: str, task_type: str) -> TaskComplexity:
        """
        Analyze task complexity.

        Args:
            prompt: Task prompt
            task_type: Task type

        Returns:
            Complexity level
        """
        # Token count
        token_count = len(self.encoding.encode(prompt))

        # Complexity indicators
        complex_keywords = [
            "analyze",
            "design",
            "architect",
            "optimize",
            "refactor",
            "debug complex",
            "multi-step",
            "reasoning",
        ]

        moderate_keywords = [
            "implement",
            "write",
            "create",
            "fix",
            "update",
            "modify",
        ]

        # Check keywords
        prompt_lower = prompt.lower()
        has_complex = any(kw in prompt_lower for kw in complex_keywords)
        has_moderate = any(kw in prompt_lower for kw in moderate_keywords)

        # Determine complexity
        if token_count > 10000 or has_complex or task_type == "reasoning":
            return TaskComplexity.COMPLEX
        elif token_count > 2000 or has_moderate or task_type == "coding":
            return TaskComplexity.MODERATE
        else:
            return TaskComplexity.SIMPLE

    def _estimate_cost(self, model: ModelTier, token_count: int) -> float:
        """
        Estimate cost for model and token count.

        Args:
            model: Model tier
            token_count: Number of tokens

        Returns:
            Estimated cost in USD
        """
        profile = MODEL_PROFILES[model]
        # Assume 2x tokens for output
        total_tokens = token_count * 3
        return (total_tokens / 1_000_000) * profile.cost_per_1m_tokens

    def _estimate_time(self, model: ModelTier, token_count: int) -> float:
        """
        Estimate execution time.

        Args:
            model: Model tier
            token_count: Number of tokens

        Returns:
            Estimated time in seconds
        """
        profile = MODEL_PROFILES[model]
        # Base time: ~1 second per 1000 tokens for Opus
        base_time = token_count / 1000
        return base_time / profile.speed_multiplier

    def get_model_stats(self) -> Dict[str, Dict]:
        """
        Get model statistics.

        Returns:
            Model profiles
        """
        return {
            tier.value: {
                "cost_per_1m": profile.cost_per_1m_tokens,
                "max_tokens": profile.max_tokens,
                "speed_multiplier": profile.speed_multiplier,
                "reasoning_score": profile.reasoning_score,
                "coding_score": profile.coding_score,
            }
            for tier, profile in MODEL_PROFILES.items()
        }
