"""MCP tools for knowledge graph access.

Provides query_graph, get_node, get_neighbors, shortest_path,
and get_community tool implementations for MCP integration.
"""

from __future__ import annotations

from typing import Any


class KnowledgeGraphMCPServer:
    """MCP-compatible server exposing knowledge graph operations as tools.

    Provides query, node access, neighbor lookup, shortest path,
    and community information via structured tool handlers.
    """

    def __init__(self, graph: Any) -> None:
        self._graph = graph

    # ── Tool Definitions ───────────────────────────────────────────────────

    async def query_graph(self, query_text: str,
                           node_type: str | None = None,
                           max_results: int = 20) -> list[dict[str, Any]]:
        """Search the graph for nodes matching a text query.

        Args:
            query_text: Text to search for in node labels and properties.
            node_type: Optional node type filter (concept, source, etc.).
            max_results: Maximum number of results to return.

        Returns:
            List of matching node dictionaries.
        """
        results: list[dict[str, Any]] = []

        for node in self._graph.nodes.values():
            if len(results) >= max_results:
                break
            if node_type and node.node_type.value != node_type:
                continue
            if self._matches_query(node, query_text):
                results.append(node.to_dict())

        return results

    async def get_node(self, node_id: str) -> dict[str, Any] | None:
        """Get detailed information about a specific node.

        Args:
            node_id: The ID of the node to retrieve.

        Returns:
            Node dict or None if not found.
        """
        try:
            node = self._graph.get_node(node_id)
            return node.to_dict()
        except Exception:
            return None

    async def get_neighbors(self, node_id: str,
                      max_results: int = 50) -> list[dict[str, Any]]:
        """Get all nodes directly connected to a given node.

        Args:
            node_id: The ID of the node.
            max_results: Maximum number of neighbor nodes to return.

        Returns:
            List of neighbor node dictionaries.
        """
        try:
            neighbors = self._graph.get_neighbors(node_id)
        except Exception:
            return []

        return [n.to_dict() for n in neighbors[:max_results]]

    async def shortest_path(self, from_id: str,
                      to_id: str) -> dict[str, Any] | None:
        """Find the shortest path between two nodes.

        Args:
            from_id: Starting node ID.
            to_id: Target node ID.

        Returns:
            Path dict with node_ids list and length, or None.
        """
        from .navigation_engine import NavigationEngine

        engine = NavigationEngine(self._graph)
        try:
            path = engine.get_path(from_id, to_id)
        except Exception:
            return None

        if path is None:
            return None
        return path.to_dict()

    async def get_community(self, node_id: str) -> dict[str, Any] | None:
        """Get community information for a node.

        Args:
            node_id: The ID of the node.

        Returns:
            Community info dict or None.
        """
        try:
            node = self._graph.get_node(node_id)
        except Exception:
            return None

        community_id = node.community_id
        if not community_id:
            return {"node_id": node_id, "community_id": None}

        community_members: list[dict[str, Any]] = []
        for n in self._graph.nodes.values():
            if n.community_id == community_id:
                community_members.append(n.to_dict())

        return {
            "node_id": node_id,
            "community_id": community_id,
            "member_count": len(community_members),
            "members": community_members[:20],
        }

    async def graph_summary(self) -> dict[str, Any]:
        """Get a summary of the entire knowledge graph.

        Returns:
            Dict with node/edge counts, type breakdowns, and sample nodes.
        """
        return self._graph.summary()

    # ── Batch Operations ──────────────────────────────────────────────────

    async def get_nodes_batch(self, node_ids: list[str]) -> list[dict[str, Any]]:
        """Get multiple nodes by their IDs."""
        results: list[dict[str, Any]] = []
        for nid in node_ids:
            try:
                node = self._graph.get_node(nid)
                results.append(node.to_dict())
            except Exception:
                continue
        return results

    async def get_subgraph(self, node_ids: list[str],
                     depth: int = 1) -> dict[str, Any]:
        """Get a subgraph expanded around given nodes."""
        from .navigation_engine import NavigationEngine

        engine = NavigationEngine(self._graph)
        try:
            sub = engine.get_subgraph(node_ids, depth)
        except Exception:
            return {"nodes": {}, "edges": []}

        return {
            "nodes": {nid: n.to_dict() for nid, n in sub["nodes"].items()},
            "edges": [e.to_dict() for e in sub["edges"]],
        }

    # ── Query Support ──────────────────────────────────────────────────────

    async def graph_query(self, query_text: str) -> list[dict[str, Any]]:
        """Search graph nodes by label, type, and properties.

        More comprehensive than query_graph — also searches properties.

        Args:
            query_text: Search query.

        Returns:
            List of matching node dictionaries.
        """
        results: list[dict[str, Any]] = []
        q_lower = query_text.lower()

        for node in self._graph.nodes.values():
            score = 0

            # Label match
            if q_lower in node.label.lower():
                score += 10
                # Exact label match
                if node.label.lower() == q_lower:
                    score += 20

            # Type match
            if q_lower == node.node_type.value:
                score += 5

            # Property value match
            for val in node.properties.values():
                if isinstance(val, str) and q_lower in val.lower():
                    score += 3

            if score > 0:
                n_dict = node.to_dict()
                n_dict["_search_score"] = score
                results.append(n_dict)

        results.sort(key=lambda x: x["_search_score"], reverse=True)
        return results

    # ── Internal ──────────────────────────────────────────────────────────

    def _matches_query(self, node: Any, query: str) -> bool:
        """Check if a node matches a text query."""
        q_lower = query.lower()
        if q_lower in node.label.lower():
            return True
        for val in node.properties.values():
            if isinstance(val, str) and q_lower in val.lower():
                return True
            if isinstance(val, (int, float)) and q_lower in str(val).lower():
                return True
        return False
