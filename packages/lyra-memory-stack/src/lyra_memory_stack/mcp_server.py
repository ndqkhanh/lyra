"""MCP server tools for memory access.

Provides Model Context Protocol (MCP) tools for querying the memory stack:
- search_memory: Layer 1 index search
- get_observation: Layer 3 full detail retrieval
- get_timeline: Layer 2 timeline context
- get_stats: Memory statistics overview
"""

from __future__ import annotations

from typing import Any

from lyra_memory_stack.retrieval import RetrievalManager


class MCPServer:
    """MCP tool server for memory stack access.

    Provides tool-like methods that can be exposed via the MCP protocol.
    Each method returns a dict with tool-like interface (content, metadata).
    """

    _retrieval_manager: RetrievalManager

    def __init__(self, retrieval_manager: RetrievalManager) -> None:
        self._retrieval_manager = retrieval_manager

    def search_memory(
        self,
        query: str,
        include_types: tuple[str, ...] = ("episodic", "semantic", "procedural", "working"),
        limit_per_type: int = 5,
    ) -> dict[str, Any]:
        """Layer 1: Search across all memory layers.

        Args:
            query: Search query string
            include_types: Memory types to search
            limit_per_type: Max results per memory type

        Returns:
            Dict with tool-call-style response (content, metadata).
        """
        results = self._retrieval_manager.search_index(
            query=query,
            include_types=include_types,
            limit_per_type=limit_per_type,
        )

        return {
            "content": [
                {
                    "entry_id": r.entry_id,
                    "title": r.title,
                    "type": r.entry_type,
                    "date": r.date,
                    "score": r.relevance_score,
                }
                for r in results
            ],
            "metadata": {
                "total_results": len(results),
                "query": query,
            },
        }

    def get_observation(
        self,
        entry_id: str,
        entry_type: str = "",
    ) -> dict[str, Any]:
        """Layer 3: Retrieve full observation detail.

        Args:
            entry_id: The ID of the entry to retrieve
            entry_type: Optional type hint for faster lookup

        Returns:
            Dict with full entry detail.
        """
        detail = self._retrieval_manager.get_detail(entry_id, entry_type)
        if detail is None:
            return {
                "content": None,
                "metadata": {"error": f"Entry '{entry_id}' not found"},
            }

        return {
            "content": {
                "entry_id": detail.entry_id,
                "type": detail.entry_type,
                "content": detail.content,
                "metadata": detail.metadata,
            },
            "metadata": {"entry_id": entry_id, "entry_type": detail.entry_type},
        }

    def get_timeline(
        self,
        entry_id: str,
        entry_type: str = "",
        depth: int = 3,
    ) -> dict[str, Any]:
        """Layer 2: Get timeline context around an entry.

        Args:
            entry_id: The ID of the entry
            entry_type: Optional type hint
            depth: Number of surrounding entries to include

        Returns:
            Dict with timeline context.
        """
        timeline = self._retrieval_manager.get_timeline(entry_id, entry_type, depth)
        if timeline is None:
            return {
                "content": None,
                "metadata": {"error": f"Timeline for '{entry_id}' not found"},
            }

        return {
            "content": {
                "entry_id": timeline.entry_id,
                "title": timeline.title,
                "type": timeline.entry_type,
                "context_summary": timeline.context_summary,
                "surrounding": [
                    {
                        "entry_id": s.entry_id,
                        "title": s.title,
                        "type": s.entry_type,
                        "date": s.date,
                    }
                    for s in timeline.surrounding_entries
                ],
            },
            "metadata": {
                "entry_id": entry_id,
                "depth": depth,
                "surrounding_count": len(timeline.surrounding_entries),
            },
        }

    def get_stats(self) -> dict[str, Any]:
        """Get aggregated memory statistics across all layers.

        Returns:
            Dict with memory stats.
        """
        stats = self._retrieval_manager.get_memory_stats()
        return {
            "content": stats,
            "metadata": {"layers": list(stats.keys())},
        }

    def list_tools(self) -> list[dict[str, Any]]:
        """List available MCP tools with descriptions and parameter schemas.

        Returns:
            List of tool definitions.
        """
        return [
            {
                "name": "search_memory",
                "description": "Search across all memory layers (episodic, semantic, procedural, working)",
                "input_schema": {
                    "type": "object",
                    "properties": {
                        "query": {"type": "string", "description": "Search query string"},
                        "include_types": {
                            "type": "array",
                            "items": {"type": "string", "enum": ["episodic", "semantic", "procedural", "working"]},
                            "description": "Memory types to search",
                        },
                        "limit_per_type": {
                            "type": "integer",
                            "description": "Max results per memory type",
                        },
                    },
                    "required": ["query"],
                },
            },
            {
                "name": "get_observation",
                "description": "Retrieve full detail for a specific memory entry",
                "input_schema": {
                    "type": "object",
                    "properties": {
                        "entry_id": {"type": "string", "description": "Entry ID to retrieve"},
                        "entry_type": {
                            "type": "string",
                            "enum": ["", "episodic", "semantic", "procedural", "working"],
                            "description": "Optional type hint",
                        },
                    },
                    "required": ["entry_id"],
                },
            },
            {
                "name": "get_timeline",
                "description": "Get timeline context around a memory entry",
                "input_schema": {
                    "type": "object",
                    "properties": {
                        "entry_id": {"type": "string", "description": "Entry ID"},
                        "entry_type": {
                            "type": "string",
                            "enum": ["", "episodic", "semantic", "procedural", "working"],
                            "description": "Optional type hint",
                        },
                        "depth": {
                            "type": "integer",
                            "description": "Number of surrounding entries",
                        },
                    },
                    "required": ["entry_id"],
                },
            },
            {
                "name": "get_stats",
                "description": "Get aggregated memory statistics",
                "input_schema": {
                    "type": "object",
                    "properties": {},
                },
            },
        ]
