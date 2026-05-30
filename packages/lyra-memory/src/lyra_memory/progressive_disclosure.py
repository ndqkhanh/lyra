"""Progressive Disclosure Context Manager.

Token-budget-aware progressive context disclosure that incrementally reveals
information based on priority levels and available token budget.

Levels:
    0 - critical_context   (4000 tokens)
    1 - important_context  (8000 tokens)
    2 - relevant_context   (16000 tokens)
    3 - supplementary_context (32000 tokens)
    4 - archival_context   (64000 tokens)

Assembly starts at level 0 and expands outward until the token budget is filled,
reserving headroom for system messages.
"""

from __future__ import annotations

from dataclasses import dataclass

from lyra_core.context.pipeline import ContextItem
from lyra_core.token_budget import TokenBudgetManager


@dataclass(frozen=True)
class DisclosureLevel:
    """A level of information disclosure with a token budget cap."""

    level: int  # 0=critical, 1=important, 2=relevant, 3=supplementary, 4=archival
    max_tokens: int
    description: str


@dataclass(frozen=True)
class DisclosureConfig:
    """Configuration for progressive disclosure levels and triggers."""

    levels: tuple[DisclosureLevel, ...] = (
        DisclosureLevel(0, 4000, "critical_context"),
        DisclosureLevel(1, 8000, "important_context"),
        DisclosureLevel(2, 16000, "relevant_context"),
        DisclosureLevel(3, 32000, "supplementary_context"),
        DisclosureLevel(4, 64000, "archival_context"),
    )
    default_level: int = 2
    budget_headroom_pct: float = 0.15  # 15% reserved for system messages
    expansion_trigger: float = 0.8  # expand when 80% of current level used


class ProgressiveDisclosureManager:
    """Token-budget-aware progressive context disclosure.

    Manages context items at different disclosure levels, assembling context
    progressively from critical (level 0) outward until the token budget is
    exhausted. Supports dynamic expansion and compaction in response to
    budget pressure.
    """

    def __init__(
        self,
        config: DisclosureConfig,
        token_budget: TokenBudgetManager,
    ) -> None:
        self.config = config
        self.budget = token_budget
        self.current_level: int = config.default_level
        self._context_items: dict[int, list[ContextItem]] = {}

    def register(self, item: ContextItem, priority: int) -> None:
        """Register a context item at a priority level.

        Args:
            item: The context item to register.
            priority: Priority level (0=critical, 1=important, 2=relevant,
                      3=supplementary, 4=archival).

        Raises:
            ValueError: If priority is not in 0-4.
        """
        if priority < 0 or priority > 4:
            raise ValueError(f"Priority must be 0-4, got {priority}")
        if priority not in self._context_items:
            self._context_items[priority] = []
        self._context_items[priority].append(item)

    def assemble_context(
        self,
        query: str,
        max_tokens: int | None = None,
    ) -> str:
        """Assemble context progressively within the token budget.

        Starts with critical context (level 0) and adds levels incrementally
        until the token budget is filled. Reserves headroom for system messages.

        Args:
            query: The query to assemble context for (reserved for future
                   query-aware assembly).
            max_tokens: Override for the token budget. Uses the
                        TokenBudgetManager's total budget if None.

        Returns:
            Assembled context as a single string with level-separated sections.
        """
        _ = query  # reserved for future query-aware assembly
        budget = max_tokens or self.budget.total_budget
        headroom = int(budget * self.config.budget_headroom_pct)
        available = budget - headroom

        parts: list[str] = []
        used = 0

        for level in range(self.current_level + 1):
            items = self._context_items.get(level, [])
            # Sort by weight descending within each level
            items = sorted(items, key=lambda it: it.weight, reverse=True)

            level_parts: list[str] = []
            level_used = 0

            for item in items:
                cost = item.estimated_tokens()
                if used + level_used + cost > available:
                    continue
                level_parts.append(item.content)
                level_used += cost

            if level_parts:
                level_def = self.config.levels[level]
                header = f"# {level_def.description}"
                parts.append(header)
                parts.extend(level_parts)
                used += level_used

        return "\n\n".join(parts)

    def should_expand(self, current_usage: int) -> bool:
        """Check if context should be expanded to the next disclosure level.

        Args:
            current_usage: Current token usage count.

        Returns:
            True if usage exceeds the expansion trigger threshold for the
            current level and there is a higher level available.
        """
        if self.current_level >= len(self.config.levels) - 1:
            return False
        level_max = self.config.levels[self.current_level].max_tokens
        return current_usage >= int(level_max * self.config.expansion_trigger)

    def expand(self) -> int:
        """Expand to the next disclosure level.

        Returns:
            The new current level.
        """
        if self.current_level < len(self.config.levels) - 1:
            self.current_level += 1
        return self.current_level

    def compact(self, target_level: int) -> int:
        """Compact context down to the target disclosure level.

        Args:
            target_level: The target level to compact to.

        Returns:
            The new current level (clamped to valid range).
        """
        target = max(0, min(target_level, self.current_level))
        self.current_level = target
        return self.current_level

    def get_stats(self) -> dict:
        """Get statistics about current disclosure state.

        Returns:
            Dictionary with current_level, total_registered items,
            per-level counts, and config values.
        """
        return {
            "current_level": self.current_level,
            "total_registered": sum(len(v) for v in self._context_items.values()),
            "level_counts": {
                level: len(items)
                for level, items in self._context_items.items()
            },
            "config": {
                "default_level": self.config.default_level,
                "headroom_pct": self.config.budget_headroom_pct,
                "expansion_trigger": self.config.expansion_trigger,
            },
        }


__all__ = [
    "DisclosureConfig",
    "DisclosureLevel",
    "ProgressiveDisclosureManager",
]
