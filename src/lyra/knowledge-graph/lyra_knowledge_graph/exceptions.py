"""Custom exceptions for the Knowledge Graph package."""

from __future__ import annotations


class KnowledgeGraphError(Exception):
    """Base exception for all knowledge graph errors."""


class NodeNotFoundError(KnowledgeGraphError):
    """Raised when a node is not found in the graph."""

    def __init__(self, node_id: str) -> None:
        self.node_id = node_id
        super().__init__(f"Node not found: '{node_id}'")


class EdgeNotFoundError(KnowledgeGraphError):
    """Raised when an edge is not found in the graph."""

    def __init__(self, edge_id: str) -> None:
        self.edge_id = edge_id
        super().__init__(f"Edge not found: '{edge_id}'")


class ExtractionError(KnowledgeGraphError):
    """Raised when entity or relation extraction fails."""

    def __init__(self, reason: str) -> None:
        self.reason = reason
        super().__init__(f"Extraction failed: {reason}")


class IndexingError(KnowledgeGraphError):
    """Raised when file or codebase indexing fails."""

    def __init__(self, path: str, reason: str) -> None:
        self.path = path
        self.reason = reason
        super().__init__(f"Indexing failed for '{path}': {reason}")


class NavigationError(KnowledgeGraphError):
    """Raised when graph navigation encounters an error."""

    def __init__(self, reason: str) -> None:
        self.reason = reason
        super().__init__(f"Navigation error: {reason}")
