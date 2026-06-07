"""Summarizers — render a group of MemoryItems as one summary string.

The built-in :class:`ExtractiveSummarizer` is deterministic, dependency-free,
and good enough for compaction within a single agent's lifetime: it picks
the highest-importance item as the headline and bullets the rest by
recency. Production wires an LLM-backed summarizer via the
:class:`Summarizer` Protocol.
"""
from __future__ import annotations

from dataclasses import dataclass

from ..memory_store import MemoryItem


@dataclass
class ExtractiveSummarizer:
    """Pick the headline + bullet the rest.

    Algorithm:
        1. Sort group by ``importance`` desc, then ``accessed_at`` desc.
        2. Take the highest-ranked item's content as the headline.
        3. Bullet the next ``max_bullets`` items by truncated content
           (``max_bullet_chars`` per bullet).
        4. If the group is larger than ``max_bullets + 1``, append a
           ``"+ N more"`` line.

    The result is deterministic given identical input ordering.

    >>> s = ExtractiveSummarizer(max_bullets=2)
    >>> s.max_bullets
    2
    """

    max_bullets: int = 5
    max_bullet_chars: int = 80
    headline_prefix: str = "Consolidated summary"

    def __post_init__(self) -> None:
        if self.max_bullets < 0:
            raise ValueError(f"max_bullets must be >= 0, got {self.max_bullets}")
        if self.max_bullet_chars < 1:
            raise ValueError(
                f"max_bullet_chars must be >= 1, got {self.max_bullet_chars}"
            )

    def summarize(self, items: list[MemoryItem]) -> str:
        if not items:
            return ""
        ranked = sorted(
            items,
            key=lambda it: (-it.importance, -it.accessed_at, it.item_id),
        )
        headline_item = ranked[0]
        rest = ranked[1:]
        lines = [
            f"{self.headline_prefix} ({len(items)} items): {headline_item.content}",
        ]
        bulleted = rest[: self.max_bullets]
        for it in bulleted:
            content = it.content
            if len(content) > self.max_bullet_chars:
                content = content[: self.max_bullet_chars - 3] + "..."
            lines.append(f"- {content}")
        remaining = len(rest) - len(bulleted)
        if remaining > 0:
            lines.append(f"- (+ {remaining} more)")
        return "\n".join(lines)


__all__ = ["ExtractiveSummarizer"]
