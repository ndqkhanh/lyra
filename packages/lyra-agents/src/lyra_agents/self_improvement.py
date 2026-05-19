"""
Self-Improvement Loop - Learn from execution feedback.

Features:
- Execution feedback collection
- Prompt refinement based on results
- Performance tracking
- A/B testing for prompts
"""

from dataclasses import dataclass, field
from datetime import datetime
from typing import Dict, List, Optional


@dataclass
class ExecutionFeedback:
    """Feedback from task execution."""

    task_id: str
    prompt: str
    result: str
    success: bool
    execution_time: float
    token_count: int
    error: Optional[str] = None
    timestamp: datetime = field(default_factory=datetime.now)


@dataclass
class PromptVariant:
    """Prompt variant for A/B testing."""

    variant_id: str
    prompt_template: str
    success_rate: float = 0.0
    avg_execution_time: float = 0.0
    total_executions: int = 0


class SelfImprovementLoop:
    """
    Self-improvement system.

    Learns from execution feedback to improve prompts.
    """

    def __init__(self, learning_rate: float = 0.1):
        """
        Initialize self-improvement loop.

        Args:
            learning_rate: How quickly to adapt (0.0-1.0)
        """
        self.learning_rate = learning_rate
        self.feedback_history: List[ExecutionFeedback] = []
        self.prompt_variants: Dict[str, PromptVariant] = {}

    def record_feedback(self, feedback: ExecutionFeedback):
        """
        Record execution feedback.

        Args:
            feedback: Execution feedback
        """
        self.feedback_history.append(feedback)

        # Update prompt variant stats if applicable
        for variant in self.prompt_variants.values():
            # Check if prompt contains variant template pattern
            template_key = variant.prompt_template.split(":")[0] if ":" in variant.prompt_template else variant.prompt_template
            if template_key in feedback.prompt:
                variant.total_executions += 1
                if feedback.success:
                    # Update success rate with exponential moving average
                    variant.success_rate = (
                        self.learning_rate * 1.0
                        + (1 - self.learning_rate) * variant.success_rate
                    )
                else:
                    variant.success_rate = (
                        self.learning_rate * 0.0
                        + (1 - self.learning_rate) * variant.success_rate
                    )

                # Update execution time
                variant.avg_execution_time = (
                    self.learning_rate * feedback.execution_time
                    + (1 - self.learning_rate) * variant.avg_execution_time
                )
                break  # Only match one variant per feedback

    def register_variant(self, variant_id: str, prompt_template: str):
        """
        Register prompt variant for A/B testing.

        Args:
            variant_id: Variant identifier
            prompt_template: Prompt template
        """
        self.prompt_variants[variant_id] = PromptVariant(
            variant_id=variant_id,
            prompt_template=prompt_template,
        )

    def get_best_variant(self) -> Optional[PromptVariant]:
        """
        Get best performing variant.

        Returns:
            Best variant or None
        """
        if not self.prompt_variants:
            return None

        # Filter variants with enough data
        viable_variants = [
            v for v in self.prompt_variants.values() if v.total_executions >= 5
        ]

        if not viable_variants:
            return None

        # Sort by success rate, then by execution time
        return max(
            viable_variants,
            key=lambda v: (v.success_rate, -v.avg_execution_time),
        )

    def get_insights(self) -> Dict[str, any]:
        """
        Get improvement insights.

        Returns:
            Insights dictionary
        """
        if not self.feedback_history:
            return {}

        total_executions = len(self.feedback_history)
        successful = sum(1 for f in self.feedback_history if f.success)
        failed = total_executions - successful

        avg_time = sum(f.execution_time for f in self.feedback_history) / total_executions
        avg_tokens = sum(f.token_count for f in self.feedback_history) / total_executions

        # Common error patterns
        errors = [f.error for f in self.feedback_history if f.error]
        error_counts = {}
        for error in errors:
            error_type = error.split(":")[0] if ":" in error else error
            error_counts[error_type] = error_counts.get(error_type, 0) + 1

        return {
            "total_executions": total_executions,
            "success_rate": successful / total_executions if total_executions > 0 else 0,
            "failed_count": failed,
            "avg_execution_time": avg_time,
            "avg_token_count": avg_tokens,
            "common_errors": error_counts,
            "variant_count": len(self.prompt_variants),
        }

    def suggest_improvements(self) -> List[str]:
        """
        Suggest improvements based on feedback.

        Returns:
            List of improvement suggestions
        """
        suggestions = []
        insights = self.get_insights()

        if not insights:
            return suggestions

        # Low success rate
        if insights["success_rate"] < 0.7:
            suggestions.append(
                "Success rate is low. Consider using more detailed prompts or upgrading model tier."
            )

        # High token usage
        if insights["avg_token_count"] > 5000:
            suggestions.append(
                "High token usage detected. Consider using token compression or breaking tasks into smaller chunks."
            )

        # Slow execution
        if insights["avg_execution_time"] > 10.0:
            suggestions.append(
                "Slow execution times. Consider using Haiku for simple tasks or optimizing prompts."
            )

        # Common errors
        if insights["common_errors"]:
            top_error = max(insights["common_errors"].items(), key=lambda x: x[1])
            suggestions.append(
                f"Most common error: {top_error[0]} ({top_error[1]} occurrences). Review error handling."
            )

        return suggestions
