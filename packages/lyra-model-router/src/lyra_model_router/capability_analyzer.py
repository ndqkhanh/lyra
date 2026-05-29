"""Task requirements analysis — classify tasks and estimate complexity."""

from __future__ import annotations

from dataclasses import dataclass


@dataclass(frozen=True)
class TaskRequirements:
    """Analyzed requirements for a task to be routed.

    Attributes:
        category: Task category from the predefined set.
        complexity_score: Estimated complexity 0.0-1.0.
        required_capabilities: Tuple of capability tags needed.
    """
    category: str
    complexity_score: float
    required_capabilities: tuple[str, ...]


# Keywords that hint at task categories
_CATEGORY_KEYWORDS: dict[str, tuple[str, ...]] = {
    "architecture": ("architecture", "design", "system", "plan", "overview", "trade-off", "decision"),
    "coding": ("code", "implement", "function", "class", "write", "program", "script", "debug", "refactor"),
    "review": ("review", "audit", "check", "inspect", "verify", "validate", "quality"),
    "research": ("research", "analyze", "investigate", "explore", "survey", "compare", "deep dive"),
    "lookup": ("lookup", "find", "search", "retrieve", "get", "fetch", "simple query"),
    "execution": ("execute", "run", "batch", "process", "transform", "convert", "translate"),
}


class CapabilityAnalyzer:
    """Analyzes task descriptions to determine routing requirements.

    Classifies tasks into categories and estimates complexity based on
    description length, context usage, and number of tools required.
    """

    async def analyze_task(
        self,
        description: str,
        context_tokens: int = 0,
        tools_required: int = 0,
    ) -> TaskRequirements:
        """Analyze a task description and return routing requirements.

        Args:
            description: Natural language description of the task.
            context_tokens: Estimated context tokens needed.
            tools_required: Number of tools the task requires.

        Returns:
            A TaskRequirements dataclass with category, complexity, and capabilities.
        """
        category = self._classify_task(description)
        complexity = self._compute_complexity(description, context_tokens, tools_required)
        capabilities = self._derive_capabilities(category, complexity)
        return TaskRequirements(
            category=category,
            complexity_score=complexity,
            required_capabilities=capabilities,
        )

    def _classify_task(self, description: str) -> str:
        """Classify a task into a category based on keyword matching."""
        lower = description.lower()
        best_category = "execution"
        best_score = 0

        for category, keywords in _CATEGORY_KEYWORDS.items():
            score = sum(1 for kw in keywords if kw in lower)
            if score > best_score:
                best_score = score
                best_category = category

        return best_category

    @staticmethod
    def _compute_complexity(description: str, context_tokens: int, tools_required: int) -> float:
        """Compute a complexity score 0.0-1.0.

        Factors:
        - Description length (longer = more complex): up to 0.4
        - Context tokens (more = more complex): up to 0.3
        - Tools required (more = more complex): up to 0.3
        """
        length_score = min(1.0, len(description) / 500.0) * 0.4
        context_score = min(1.0, context_tokens / 100000.0) * 0.3
        tools_score = min(1.0, tools_required / 5.0) * 0.3
        raw = length_score + context_score + tools_score
        return round(min(1.0, raw), 4)

    @staticmethod
    def _derive_capabilities(category: str, complexity: float) -> tuple[str, ...]:
        """Derive required capability tags from category and complexity."""
        base: list[str] = []

        if category == "architecture":
            base = ["reasoning", "planning", "design"]
        elif category == "coding":
            base = ["coding", "debugging", "reasoning"]
        elif category == "review":
            base = ["review", "analysis", "verification"]
        elif category == "research":
            base = ["research", "reasoning", "analysis"]
        elif category == "lookup":
            base = ["simple_query", "retrieval"]
        elif category == "execution":
            base = ["execution", "batch_processing"]

        if complexity >= 0.7:
            base.append("deep_reasoning")
        if complexity >= 0.9:
            base.append("architectural")

        return tuple(base)
