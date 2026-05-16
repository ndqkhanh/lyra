"""
Model Routing by Task Slot - Route tasks to appropriate models.

Routes tasks to Haiku/Sonnet/Opus based on complexity and requirements.
Target: 40% cost reduction through intelligent routing.
"""

from dataclasses import dataclass, field
from datetime import datetime
from typing import List, Optional, Dict, Any
from enum import Enum


class ModelTier(Enum):
    """Model tiers for routing."""

    HAIKU = "haiku"  # Fast, cheap, 90% of Sonnet capability
    SONNET = "sonnet"  # Best coding model, balanced
    OPUS = "opus"  # Deepest reasoning, most expensive


@dataclass
class TaskComplexity:
    """Complexity assessment for a task."""

    complexity_score: float  # 0.0 to 1.0
    reasoning_depth: str  # "shallow", "medium", "deep"
    code_size: str  # "small", "medium", "large"
    requires_creativity: bool
    requires_precision: bool


@dataclass
class RoutingDecision:
    """A model routing decision."""

    decision_id: str
    task_description: str
    complexity: TaskComplexity
    selected_model: ModelTier
    reason: str
    estimated_cost: float
    timestamp: str = field(default_factory=lambda: datetime.now().isoformat())


class ModelRouter:
    """
    Routes tasks to appropriate models based on complexity.

    Features:
    - Complexity assessment
    - Cost-aware routing
    - Performance tracking per model
    - Automatic fallback on failure
    """

    def __init__(self):
        # Model costs (relative, Haiku = 1.0)
        self.model_costs = {
            ModelTier.HAIKU: 1.0,
            ModelTier.SONNET: 3.0,
            ModelTier.OPUS: 15.0,
        }

        # Model capabilities (0.0 to 1.0)
        self.model_capabilities = {
            ModelTier.HAIKU: 0.9,  # 90% of Sonnet
            ModelTier.SONNET: 1.0,  # Baseline
            ModelTier.OPUS: 1.2,  # 20% better reasoning
        }

        # Routing decisions
        self.decisions: List[RoutingDecision] = []

        # Statistics
        self.stats = {
            "total_routes": 0,
            "haiku_routes": 0,
            "sonnet_routes": 0,
            "opus_routes": 0,
            "total_cost": 0.0,
            "cost_saved": 0.0,
        }

    def assess_complexity(
        self,
        task_description: str,
        context: Optional[Dict[str, Any]] = None
    ) -> TaskComplexity:
        """
        Assess task complexity.

        Args:
            task_description: Description of the task
            context: Optional context information

        Returns:
            TaskComplexity assessment
        """
        context = context or {}

        # Simple heuristic-based complexity assessment
        desc_lower = task_description.lower()

        # Reasoning depth indicators
        deep_reasoning_keywords = [
            "architecture", "design", "complex", "optimize",
            "refactor", "analyze", "debug", "investigate"
        ]
        medium_reasoning_keywords = [
            "implement", "add", "create", "modify", "update"
        ]

        deep_count = sum(1 for kw in deep_reasoning_keywords if kw in desc_lower)
        medium_count = sum(1 for kw in medium_reasoning_keywords if kw in desc_lower)

        if deep_count >= 2:
            reasoning_depth = "deep"
            complexity_score = 0.8
        elif deep_count >= 1 or medium_count >= 2:
            reasoning_depth = "medium"
            complexity_score = 0.5
        else:
            reasoning_depth = "shallow"
            complexity_score = 0.2

        # Code size indicators
        large_code_keywords = ["refactor", "rewrite", "migrate", "multiple files"]
        medium_code_keywords = ["implement", "add feature", "modify"]

        if any(kw in desc_lower for kw in large_code_keywords):
            code_size = "large"
            complexity_score = max(complexity_score, 0.7)
        elif any(kw in desc_lower for kw in medium_code_keywords):
            code_size = "medium"
            complexity_score = max(complexity_score, 0.4)
        else:
            code_size = "small"

        # Creativity indicators
        creativity_keywords = ["design", "creative", "novel", "innovative"]
        requires_creativity = any(kw in desc_lower for kw in creativity_keywords)

        # Precision indicators
        precision_keywords = ["security", "critical", "production", "precise"]
        requires_precision = any(kw in desc_lower for kw in precision_keywords)

        # Adjust complexity based on context
        if context.get("is_critical", False):
            complexity_score = min(complexity_score + 0.2, 1.0)
            requires_precision = True

        if context.get("requires_deep_reasoning", False):
            reasoning_depth = "deep"
            complexity_score = min(complexity_score + 0.3, 1.0)

        return TaskComplexity(
            complexity_score=complexity_score,
            reasoning_depth=reasoning_depth,
            code_size=code_size,
            requires_creativity=requires_creativity,
            requires_precision=requires_precision,
        )

    def route_task(
        self,
        task_description: str,
        context: Optional[Dict[str, Any]] = None
    ) -> RoutingDecision:
        """
        Route a task to the appropriate model.

        Args:
            task_description: Description of the task
            context: Optional context information

        Returns:
            RoutingDecision with selected model
        """
        # Assess complexity
        complexity = self.assess_complexity(task_description, context)

        # Routing logic
        selected_model = self._select_model(complexity, context)

        # Calculate estimated cost
        estimated_cost = self.model_costs[selected_model]

        # Calculate cost saved (vs always using Opus)
        cost_saved = self.model_costs[ModelTier.OPUS] - estimated_cost

        # Create decision
        decision = RoutingDecision(
            decision_id=f"route_{len(self.decisions):06d}",
            task_description=task_description,
            complexity=complexity,
            selected_model=selected_model,
            reason=self._get_routing_reason(complexity, selected_model),
            estimated_cost=estimated_cost,
        )

        self.decisions.append(decision)

        # Update statistics
        self.stats["total_routes"] += 1
        self.stats[f"{selected_model.value}_routes"] += 1
        self.stats["total_cost"] += estimated_cost
        self.stats["cost_saved"] += cost_saved

        return decision

    def _select_model(
        self,
        complexity: TaskComplexity,
        context: Optional[Dict[str, Any]] = None
    ) -> ModelTier:
        """
        Select the appropriate model based on complexity.

        Routing rules:
        - Haiku: Simple tasks, low complexity (<0.3)
        - Sonnet: Standard tasks, medium complexity (0.3-0.7)
        - Opus: Complex tasks, high complexity (>0.7) or requires deep reasoning
        """
        context = context or {}

        # Force Opus for critical tasks
        if context.get("force_opus", False):
            return ModelTier.OPUS

        # Force Haiku for simple tasks
        if context.get("force_haiku", False):
            return ModelTier.HAIKU

        # Complexity-based routing
        if complexity.complexity_score >= 0.7:
            return ModelTier.OPUS

        if complexity.complexity_score >= 0.3:
            # Use Sonnet for medium complexity
            # But use Opus if requires deep reasoning or creativity
            if complexity.reasoning_depth == "deep" or complexity.requires_creativity:
                return ModelTier.OPUS
            return ModelTier.SONNET

        # Low complexity - use Haiku
        # But use Sonnet if requires precision
        if complexity.requires_precision:
            return ModelTier.SONNET

        return ModelTier.HAIKU

    def _get_routing_reason(
        self,
        complexity: TaskComplexity,
        selected_model: ModelTier
    ) -> str:
        """Generate human-readable routing reason."""
        reasons = []

        if selected_model == ModelTier.HAIKU:
            reasons.append("Low complexity task")
            reasons.append(f"Complexity score: {complexity.complexity_score:.2f}")
        elif selected_model == ModelTier.SONNET:
            reasons.append("Medium complexity task")
            reasons.append(f"Complexity score: {complexity.complexity_score:.2f}")
        else:  # OPUS
            reasons.append("High complexity task")
            reasons.append(f"Complexity score: {complexity.complexity_score:.2f}")

        if complexity.reasoning_depth == "deep":
            reasons.append("Requires deep reasoning")

        if complexity.requires_creativity:
            reasons.append("Requires creativity")

        if complexity.requires_precision:
            reasons.append("Requires precision")

        if complexity.code_size == "large":
            reasons.append("Large code changes")

        return "; ".join(reasons)

    def get_cost_reduction(self) -> float:
        """
        Calculate cost reduction percentage.

        Compares actual cost vs. always using Opus.
        """
        if self.stats["total_routes"] == 0:
            return 0.0

        # Cost if always using Opus
        opus_cost = self.stats["total_routes"] * self.model_costs[ModelTier.OPUS]

        # Actual cost
        actual_cost = self.stats["total_cost"]

        if opus_cost == 0:
            return 0.0

        return (opus_cost - actual_cost) / opus_cost

    def get_stats(self) -> Dict[str, Any]:
        """Get routing statistics."""
        cost_reduction = self.get_cost_reduction()

        return {
            **self.stats,
            "cost_reduction_pct": cost_reduction * 100,
            "avg_cost_per_task": (
                self.stats["total_cost"] / self.stats["total_routes"]
                if self.stats["total_routes"] > 0
                else 0.0
            ),
        }
