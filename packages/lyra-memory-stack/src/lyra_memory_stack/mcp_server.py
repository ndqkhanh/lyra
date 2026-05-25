"""MCP server — exposes memory stack operations as MCP tools.

Provides search, timeline, and get_observations tools following
the Claude-Mem 3-layer retrieval pattern.
"""

from __future__ import annotations

from dataclasses import dataclass

from .episodic_memory import EpisodicMemory
from .retrieval import IndexEntry, RetrievalPipeline
from .semantic_memory import SemanticMemory


@dataclass(frozen=True)
class MCPSearchResult:
    """Search result returned by the MCP search tool.

    Attributes:
        entry_id: Reference ID.
        summary: One-line summary.
        category: Content category.
        score: Relevance score.
        token_cost: Estimated tokens to fetch full details.
    """

    entry_id: str
    summary: str
    category: str
    score: float
    token_cost: int


class MemoryMCPServer:
    """Exposes memory operations as MCP-compatible tool endpoints.

    Tools:
    - search(query) → Get index with IDs (~50-100 tokens/result)
    - timeline(anchor=ID) → Get context around interesting results
    - get_observations([IDs]) → Fetch full details ONLY for filtered IDs
    """

    def __init__(
        self,
        episodic: EpisodicMemory | None = None,
        semantic: SemanticMemory | None = None,
    ) -> None:
        self._episodic = episodic or EpisodicMemory()
        self._semantic = semantic or SemanticMemory()
        self._pipeline = RetrievalPipeline(self._episodic, self._semantic)

    async def search(
        self, query: str, limit: int = 20
    ) -> tuple[MCPSearchResult, ...]:
        """MCP tool: search memory index.

        Returns compact summaries with token cost estimates.
        Clients should call timeline() for context and
        get_observations() only for filtered results.
        """
        index_results: tuple[IndexEntry, ...] = await self._pipeline.search_index(
            query, limit=limit
        )
        return tuple(
            MCPSearchResult(
                entry_id=r.entry_id,
                summary=r.summary,
                category=r.category,
                score=r.relevance_score,
                token_cost=750,
            )
            for r in index_results
        )

    async def timeline(
        self,
        anchor: str,
        depth_before: int = 2,
        depth_after: int = 2,
    ) -> tuple[dict, ...]:
        """MCP tool: get context around a search result.

        Args:
            anchor: Entry ID from a search result.
            depth_before: Entries before the anchor.
            depth_after: Entries after the anchor.

        Returns:
            Timeline entries with content previews.
        """
        entries = await self._pipeline.get_timeline(
            anchor, depth_before=depth_before, depth_after=depth_after
        )
        return tuple(
            {
                "entry_id": e.entry_id,
                "preview": e.content_preview,
                "timestamp": e.timestamp,
                "context_before": e.context_before,
                "context_after": e.context_after,
            }
            for e in entries
        )

    async def get_observations(
        self, entry_ids: tuple[str, ...]
    ) -> tuple[dict, ...]:
        """MCP tool: fetch full details for filtered IDs.

        Only call after filtering with search() + timeline().
        This is the expensive operation — use sparingly.
        """
        contents = await self._pipeline.get_details(entry_ids)
        return tuple(
            {"entry_id": eid, "content": content}
            for eid, content in zip(entry_ids, contents)
        )

    async def search_events(self, query: str, limit: int = 50) -> tuple[dict, ...]:
        """Direct episodic search."""
        events = await self._episodic.search(query, limit=limit)
        return tuple(
            {
                "event_id": e.event_id,
                "session_id": e.session_id,
                "event_type": e.event_type,
                "content": e.content,
                "tags": e.tags,
                "timestamp": e.timestamp,
            }
            for e in events
        )

    async def count_all(self) -> dict:
        """Get total counts across all memory layers."""
        return {
            "episodic_events": await self._episodic.count(),
            "semantic_facts": self._semantic.size,
        }
