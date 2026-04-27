"""5-layer context pipeline.

Layers:
    1. SOUL            — repo persona; *never compacted*
    2. STATIC_CACHED   — shipped system prompts / rules
    3. DYNAMIC         — user turns, tool results (compactable)
    4. COMPACTED       — summaries of older dynamic content
    5. MEMORY_REFS     — pointers into procedural/episodic memory

Token estimation is a rough char-based heuristic so the module stays
zero-dep. Production builds can swap in ``tiktoken`` without contract changes.
"""
from __future__ import annotations

import enum
from dataclasses import dataclass, field


class ContextLayer(str, enum.Enum):
    SOUL = "soul"
    STATIC_CACHED = "static_cached"
    DYNAMIC = "dynamic"
    COMPACTED = "compacted"
    MEMORY_REFS = "memory_refs"


_ORDER = [
    ContextLayer.SOUL,
    ContextLayer.STATIC_CACHED,
    ContextLayer.DYNAMIC,
    ContextLayer.COMPACTED,
    ContextLayer.MEMORY_REFS,
]


def _tok_estimate(text: str) -> int:
    """Cheap token estimate: ~1 token per 4 chars, min 1."""
    return max(1, len(text) // 4)


@dataclass
class ContextItem:
    layer: ContextLayer
    content: str
    pin: bool = False
    weight: int = 0  # higher = more important within its layer

    def estimated_tokens(self) -> int:
        return _tok_estimate(self.content)


@dataclass
class ContextAssembler:
    soul_text: str
    _items: list[ContextItem] = field(default_factory=list)

    def add(self, item: ContextItem) -> None:
        if item.layer is ContextLayer.SOUL:
            raise ValueError(
                "SOUL layer is internal; callers must not add SOUL items directly"
            )
        self._items.append(item)

    def assemble(self, max_tokens: int | None = None) -> list[ContextItem]:
        soul = ContextItem(layer=ContextLayer.SOUL, content=self.soul_text, pin=True)
        items = [soul, *list(self._items)]
        items.sort(key=lambda it: _ORDER.index(it.layer))

        if max_tokens is None:
            return items

        kept: list[ContextItem] = []
        used = 0
        # First pass: always keep SOUL (and other pinned items)
        for it in items:
            if it.layer is ContextLayer.SOUL or it.pin:
                kept.append(it)
                used += it.estimated_tokens()
        for it in items:
            if it in kept:
                continue
            cost = it.estimated_tokens()
            if used + cost > max_tokens:
                continue
            kept.append(it)
            used += cost
        kept.sort(key=lambda it: _ORDER.index(it.layer))
        return kept
