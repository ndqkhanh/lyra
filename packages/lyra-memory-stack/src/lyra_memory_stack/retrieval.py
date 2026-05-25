"""3-layer retrieval pipeline — index→timeline→detail (Claude-Mem pattern).

Progressive disclosure: cheap index search first, timeline for context,
full detail only for filtered candidates. 10x token savings.
"""

from __future__ import annotations

from dataclasses import dataclass

from .episodic_memory import EpisodicMemory
from .semantic_memory import SemanticFact, SemanticMemory


@dataclass(frozen=True)
class IndexEntry:
    """Lightweight index summary (~50-100 tokens).

    Attributes:
        entry_id: Reference ID for fetching details.
        summary: One-line summary of the content.
        category: Content category.
        relevance_score: Initial relevance estimate.
    """

    entry_id: str
    summary: str
    category: str
    relevance_score: float


@dataclass(frozen=True)
class TimelineEntry:
    """Medium-weight context (~200-500 tokens).

    Attributes:
        entry_id: Reference ID.
        content_preview: Truncated content preview.
        timestamp: When this was recorded.
        context_before: ID of preceding entry for context chaining.
        context_after: ID of following entry for context chaining.
    """

    entry_id: str
    content_preview: str
    timestamp: float
    context_before: str | None
    context_after: str | None


class RetrievalPipeline:
    """3-layer retrieval with progressive disclosure.

    Layer 1 (Index): Cheap keyword/semantic match → compact summaries.
    Layer 2 (Timeline): Context window around matches → medium detail.
    Layer 3 (Detail): Full content fetch → only for filtered candidates.
    """

    def __init__(
        self,
        episodic: EpisodicMemory | None = None,
        semantic: SemanticMemory | None = None,
    ) -> None:
        self._episodic = episodic or EpisodicMemory()
        self._semantic = semantic or SemanticMemory()

    async def search_index(
        self, query: str, limit: int = 20
    ) -> tuple[IndexEntry, ...]:
        """Layer 1: Cheap index search returning compact summaries.

        Args:
            query: Search query.
            limit: Max results.

        Returns:
            Lightweight IndexEntry summaries.
        """
        events = await self._episodic.search(query, limit=limit)
        results: list[IndexEntry] = []
        for event in events:
            summary = event.content[:120] + "..." if len(event.content) > 120 else event.content
            results.append(
                IndexEntry(
                    entry_id=f"ep-{event.event_id}",
                    summary=summary,
                    category=event.event_type,
                    relevance_score=1.0,
                )
            )
        return tuple(results)

    async def get_timeline(
        self, entry_id: str, depth_before: int = 2, depth_after: int = 2
    ) -> tuple[TimelineEntry, ...]:
        """Layer 2: Context window around a matched entry.

        Args:
            entry_id: The anchor entry reference.
            depth_before: Entries to include before the anchor.
            depth_after: Entries to include after the anchor.

        Returns:
            TimelineEntry objects in chronological order.
        """
        if not entry_id.startswith("ep-"):
            return ()

        event_id = int(entry_id.replace("ep-", ""))
        recent = await self._episodic.get_recent(limit=100)

        anchor_idx = None
        for i, e in enumerate(recent):
            if e.event_id == event_id:
                anchor_idx = i
                break

        if anchor_idx is None:
            return ()

        start = max(0, anchor_idx - depth_before)
        end = min(len(recent), anchor_idx + depth_after + 1)
        window = recent[start:end]

        results: list[TimelineEntry] = []
        for i, event in enumerate(window):
            prev_id = f"ep-{window[i - 1].event_id}" if i > 0 else None
            next_id = (
                f"ep-{window[i + 1].event_id}" if i < len(window) - 1 else None
            )
            preview = (
                event.content[:200] + "..."
                if len(event.content) > 200
                else event.content
            )
            results.append(
                TimelineEntry(
                    entry_id=f"ep-{event.event_id}",
                    content_preview=preview,
                    timestamp=event.timestamp,
                    context_before=prev_id,
                    context_after=next_id,
                )
            )
        return tuple(results)

    async def get_details(self, entry_ids: tuple[str, ...]) -> tuple[str, ...]:
        """Layer 3: Full content fetch for filtered candidates.

        Args:
            entry_ids: The entry references to fetch in full.

        Returns:
            Full content strings.
        """
        results: list[str] = []
        for eid in entry_ids:
            if eid.startswith("ep-"):
                event_id = int(eid.replace("ep-", ""))
                recent = await self._episodic.get_recent(limit=1000)
                for e in recent:
                    if e.event_id == event_id:
                        results.append(e.content)
                        break
            elif eid.startswith("fact-"):
                try:
                    fact: SemanticFact = await self._semantic.get_fact(eid)
                    results.append(fact.content)
                except KeyError:
                    pass
        return tuple(results)

    async def estimate_token_cost(
        self, index_count: int, timeline_count: int, detail_count: int
    ) -> dict[str, int]:
        """Estimate token cost for a retrieval plan.

        Args:
            index_count: Number of index entries to fetch.
            timeline_count: Number of timeline entries.
            detail_count: Number of full details to fetch.

        Returns:
            Token cost breakdown.
        """
        return {
            "index_tokens": index_count * 75,
            "timeline_tokens": timeline_count * 300,
            "detail_tokens": detail_count * 750,
            "total": index_count * 75 + timeline_count * 300 + detail_count * 750,
        }
