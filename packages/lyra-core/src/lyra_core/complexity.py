"""
Task Complexity Scoring for Lyra

Based on research from gstack and Ruflo.
Calculates task complexity (0-1 scale) for intelligent agent routing.
"""

from dataclasses import dataclass
from typing import List, Optional


@dataclass
class TaskComplexity:
    """Task complexity analysis result."""
    score: float  # 0-1 scale
    factors: dict
    recommendation: str
    reasoning: str


# Task type complexity weights
TYPE_COMPLEXITY = {
    "refactor": 0.20,
    "implement": 0.15,
    "debug": 0.15,
    "design": 0.25,
    "test": 0.10,
    "document": 0.05,
    "review": 0.10,
    "optimize": 0.20
}

# Priority multipliers
PRIORITY_MULTIPLIERS = {
    1: 1.2,  # High priority
    2: 1.0,  # Normal priority
    3: 0.8   # Low priority
}


def calculate_complexity(
    task: str,
    subtasks: Optional[List[str]] = None,
    dependencies: Optional[List[str]] = None,
    priority: int = 2,
    task_type: Optional[str] = None
) -> TaskComplexity:
    """
    Calculate task complexity on 0-1 scale.

    Args:
        task: Task description
        subtasks: List of subtask descriptions
        dependencies: List of dependency IDs
        priority: Priority level (1=high, 2=normal, 3=low)
        task_type: Type of task (refactor, implement, etc.)

    Returns:
        TaskComplexity with score and recommendation
    """
    subtasks = subtasks or []
    dependencies = dependencies or []

    # Base complexity
    complexity = 0.3

    # Factor 1: Subtask count (0.1 per subtask, max 0.3)
    subtask_factor = min(len(subtasks) * 0.1, 0.3)
    complexity += subtask_factor

    # Factor 2: Dependencies (0.05 per dependency, max 0.2)
    dependency_factor = min(len(dependencies) * 0.05, 0.2)
    complexity += dependency_factor

    # Factor 3: Task type
    if task_type and task_type in TYPE_COMPLEXITY:
        complexity += TYPE_COMPLEXITY[task_type]
    else:
        # Infer from task description
        task_lower = task.lower()
        for type_name, weight in TYPE_COMPLEXITY.items():
            if type_name in task_lower:
                complexity += weight
                task_type = type_name
                break

    # Factor 4: Priority multiplier
    priority_mult = PRIORITY_MULTIPLIERS.get(priority, 1.0)
    complexity *= priority_mult

    # Factor 5: Task length (longer descriptions = more complex)
    if len(task) > 200:
        complexity += 0.1
    elif len(task) > 500:
        complexity += 0.15

    # Clamp to 0-1
    complexity = min(max(complexity, 0.0), 1.0)

    # Generate recommendation
    if complexity < 0.4:
        recommendation = "Use fast model (Haiku/Flash)"
        reasoning = "Low complexity task suitable for fast model"
    elif complexity < 0.7:
        recommendation = "Use standard model (Sonnet/Pro)"
        reasoning = "Medium complexity requires balanced capability"
    else:
        recommendation = "Use smart model (Opus/Max)"
        reasoning = "High complexity requires deep reasoning"

    return TaskComplexity(
        score=complexity,
        factors={
            "base": 0.3,
            "subtasks": subtask_factor,
            "dependencies": dependency_factor,
            "type": TYPE_COMPLEXITY.get(task_type, 0.0),
            "priority_mult": priority_mult,
            "length": 0.1 if len(task) > 200 else 0.0
        },
        recommendation=recommendation,
        reasoning=reasoning
    )


def get_model_for_complexity(complexity_score: float) -> str:
    """
    Get recommended model based on complexity score.

    Args:
        complexity_score: Complexity score (0-1)

    Returns:
        Model name
    """
    if complexity_score < 0.4:
        return "haiku"
    elif complexity_score < 0.7:
        return "sonnet"
    else:
        return "opus"


def estimate_duration(complexity_score: float) -> int:
    """
    Estimate task duration in seconds based on complexity.

    Args:
        complexity_score: Complexity score (0-1)

    Returns:
        Estimated duration in seconds
    """
    # Base: 30 seconds
    # Max: 300 seconds (5 minutes)
    base = 30
    max_duration = 300

    duration = base + (max_duration - base) * complexity_score
    return int(duration)


# Export for use in other modules
__all__ = [
    "TaskComplexity",
    "calculate_complexity",
    "get_model_for_complexity",
    "estimate_duration",
    "TYPE_COMPLEXITY",
    "PRIORITY_MULTIPLIERS"
]
