"""Progressive disclosure pipeline — claude-mem 3-layer pattern.

Loads memory in 3 levels of increasing detail to achieve ~10x token
savings compared to loading full content for all results.
"""

from __future__ import annotations

import time
from dataclasses import dataclass
from enum import StrEnum


class DisclosureLevel(StrEnum):
    METADATA = "metadata"
    TRIGGERS = "triggers"
    FULL_CONTENT = "full_content"


@dataclass(frozen=True)
class DisclosedMemory:
    memory_id: str
    level: DisclosureLevel
    title: str
    excerpt: str
    tags: list[str]
    timestamp: float
    token_estimate: int
    full_content: str = ""


@dataclass(frozen=True)
class DisclosureBatch:
    items: list[DisclosedMemory]
    total_tokens: int
    level: DisclosureLevel
    elapsed_ms: float


class ProgressiveDisclosure:
    """3-layer progressive disclosure for memory retrieval results.

    Level 1 (Metadata): title, type, timestamp — ~500 tokens per query
    Level 2 (Triggers): excerpts, entity mentions — ~1K per match
    Level 3 (Full Content): complete memory — ~5K per match
    """

    DEFAULT_EXCERPT_LEN = 150

    def disclose_metadata(self, items: list[DisclosedMemory]) -> DisclosureBatch:
        start = time.perf_counter()
        metadata_items = [
            DisclosedMemory(
                memory_id=item.memory_id,
                level=DisclosureLevel.METADATA,
                title=item.title,
                excerpt=item.excerpt[:80] if item.excerpt else "",
                tags=item.tags,
                timestamp=item.timestamp,
                token_estimate=len(item.title.split()) + len(item.tags) * 2,
                full_content="",
            )
            for item in items
        ]
        total = sum(i.token_estimate for i in metadata_items)
        elapsed = (time.perf_counter() - start) * 1000
        return DisclosureBatch(
            items=metadata_items,
            total_tokens=total,
            level=DisclosureLevel.METADATA,
            elapsed_ms=round(elapsed, 2),
        )

    def disclose_triggers(self, items: list[DisclosedMemory]) -> DisclosureBatch:
        start = time.perf_counter()
        trigger_items = [
            DisclosedMemory(
                memory_id=item.memory_id,
                level=DisclosureLevel.TRIGGERS,
                title=item.title,
                excerpt=item.excerpt[: self.DEFAULT_EXCERPT_LEN],
                tags=item.tags,
                timestamp=item.timestamp,
                token_estimate=len(item.excerpt[: self.DEFAULT_EXCERPT_LEN].split())
                + len(item.tags) * 3,
                full_content="",
            )
            for item in items
        ]
        total = sum(i.token_estimate for i in trigger_items)
        elapsed = (time.perf_counter() - start) * 1000
        return DisclosureBatch(
            items=trigger_items,
            total_tokens=total,
            level=DisclosureLevel.TRIGGERS,
            elapsed_ms=round(elapsed, 2),
        )

    def disclose_full(self, items: list[DisclosedMemory]) -> DisclosureBatch:
        start = time.perf_counter()
        full_items = [
            DisclosedMemory(
                memory_id=item.memory_id,
                level=DisclosureLevel.FULL_CONTENT,
                title=item.title,
                excerpt=item.full_content if item.full_content else item.excerpt,
                tags=item.tags,
                timestamp=item.timestamp,
                token_estimate=len((item.full_content or item.excerpt).split()),
                full_content=item.full_content,
            )
            for item in items
        ]
        total = sum(i.token_estimate for i in full_items)
        elapsed = (time.perf_counter() - start) * 1000
        return DisclosureBatch(
            items=full_items,
            total_tokens=total,
            level=DisclosureLevel.FULL_CONTENT,
            elapsed_ms=round(elapsed, 2),
        )

    def select_for_context(
        self,
        metadata: DisclosureBatch,
        selected_ids: list[str],
    ) -> DisclosureBatch:
        """Progressively disclose only selected items to full content."""
        selected = [item for item in metadata.items if item.memory_id in selected_ids]
        return self.disclose_full(selected)

    def stats(self) -> dict:
        return {
            "disclosure_levels": [level.value for level in DisclosureLevel],
            "default_excerpt_len": self.DEFAULT_EXCERPT_LEN,
        }
