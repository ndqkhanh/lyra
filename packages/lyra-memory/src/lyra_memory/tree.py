"""
Memory Tree - Hierarchical summarization inspired by OpenHuman.

Implements tree-based memory compression and retrieval:
- Hierarchical summarization (≤3k tokens per chunk)
- Auto-compression of scan results, logs, reports
- Tree-based retrieval for context
- Temporal decay for relevance scoring
"""

from dataclasses import dataclass, field
from datetime import datetime
from typing import Any, Dict, List, Optional
from uuid import uuid4

import numpy as np


@dataclass
class TreeNode:
    """A node in the memory tree."""

    id: str = field(default_factory=lambda: str(uuid4()))
    content: str = ""
    summary: str = ""
    level: int = 0  # 0 = leaf, higher = more abstract
    children: List[str] = field(default_factory=list)
    parent: Optional[str] = None
    created_at: datetime = field(default_factory=datetime.now)
    last_accessed: datetime = field(default_factory=datetime.now)
    access_count: int = 0
    metadata: Dict[str, Any] = field(default_factory=dict)
    embedding: Optional[np.ndarray] = None


class MemoryTree:
    """
    Hierarchical memory tree for efficient context retrieval.

    Architecture:
    - Leaf nodes: Raw memories (≤3k tokens)
    - Internal nodes: Summaries of children
    - Root: High-level overview
    - Temporal decay: Recent memories weighted higher
    """

    def __init__(self, max_tokens_per_node: int = 3000):
        """
        Initialize memory tree.

        Args:
            max_tokens_per_node: Maximum tokens per node
        """
        self.max_tokens = max_tokens_per_node
        self.nodes: Dict[str, TreeNode] = {}
        self.root_id: Optional[str] = None

    def add_memory(
        self,
        content: str,
        metadata: Optional[Dict[str, Any]] = None,
        parent_id: Optional[str] = None,
    ) -> TreeNode:
        """
        Add a memory to the tree.

        Args:
            content: Memory content
            metadata: Additional metadata
            parent_id: Parent node ID (None for root-level)

        Returns:
            Created TreeNode
        """
        # Estimate tokens (rough: 1 token ≈ 4 chars)
        estimated_tokens = len(content) // 4

        if estimated_tokens > self.max_tokens:
            # Split into chunks
            return self._add_chunked_memory(content, metadata, parent_id)

        # Create leaf node
        node = TreeNode(
            content=content,
            summary=self._generate_summary(content),
            level=0,
            parent=parent_id,
            metadata=metadata or {},
        )

        self.nodes[node.id] = node

        # Update parent
        if parent_id and parent_id in self.nodes:
            self.nodes[parent_id].children.append(node.id)
        elif not self.root_id:
            self.root_id = node.id

        return node

    def _add_chunked_memory(
        self,
        content: str,
        metadata: Optional[Dict[str, Any]],
        parent_id: Optional[str],
    ) -> TreeNode:
        """Add large memory by chunking."""
        # Split into chunks of ~3k tokens
        chunk_size = self.max_tokens * 4  # chars
        chunks = [content[i : i + chunk_size] for i in range(0, len(content), chunk_size)]

        # Create parent node for chunks
        parent = TreeNode(
            content="",
            summary=self._generate_summary(content[:1000]),  # Summary from first 1k chars
            level=1,
            parent=parent_id,
            metadata=metadata or {},
        )
        self.nodes[parent.id] = parent

        # Add chunks as children
        for chunk in chunks:
            child = TreeNode(
                content=chunk,
                summary=self._generate_summary(chunk),
                level=0,
                parent=parent.id,
                metadata=metadata or {},
            )
            self.nodes[child.id] = child
            parent.children.append(child.id)

        return parent

    def _generate_summary(self, content: str, max_length: int = 200) -> str:
        """
        Generate summary of content.

        TODO: Replace with LLM-based summarization
        """
        if len(content) <= max_length:
            return content

        # Simple truncation for now
        return content[:max_length] + "..."

    def retrieve(
        self,
        query: str,
        max_nodes: int = 10,
        include_children: bool = True,
        temporal_decay: float = 0.1,
    ) -> List[TreeNode]:
        """
        Retrieve relevant nodes from tree.

        Args:
            query: Search query
            max_nodes: Maximum nodes to return
            include_children: Whether to include child nodes
            temporal_decay: Decay factor for temporal relevance

        Returns:
            List of relevant TreeNodes
        """
        # TODO: Implement semantic search with embeddings
        # For now, simple keyword matching
        results = []
        query_lower = query.lower()

        for node in self.nodes.values():
            # Calculate relevance score
            content_match = query_lower in node.content.lower()
            summary_match = query_lower in node.summary.lower()

            if content_match or summary_match:
                # Apply temporal decay
                age_days = (datetime.now() - node.created_at).days
                temporal_score = np.exp(-temporal_decay * age_days)

                # Access frequency bonus
                access_bonus = min(node.access_count * 0.1, 1.0)

                # Combined score
                base_score = 1.0 if content_match else 0.5
                score = base_score * temporal_score * (1 + access_bonus)

                results.append((score, node))

                # Update access stats
                node.last_accessed = datetime.now()
                node.access_count += 1

        # Sort by score
        results.sort(key=lambda x: x[0], reverse=True)

        # Return top nodes
        top_nodes = [node for _, node in results[:max_nodes]]

        # Include children if requested
        if include_children:
            expanded = []
            for node in top_nodes:
                expanded.append(node)
                for child_id in node.children:
                    if child_id in self.nodes:
                        expanded.append(self.nodes[child_id])
            return expanded[:max_nodes * 2]

        return top_nodes

    def compress(self, node_id: str) -> TreeNode:
        """
        Compress a node and its children into a summary.

        Args:
            node_id: Node to compress

        Returns:
            Compressed parent node
        """
        if node_id not in self.nodes:
            raise ValueError(f"Node {node_id} not found")

        node = self.nodes[node_id]

        if not node.children:
            return node  # Already a leaf

        # Gather all child content
        child_content = []
        for child_id in node.children:
            if child_id in self.nodes:
                child = self.nodes[child_id]
                child_content.append(child.content or child.summary)

        # Generate compressed summary
        combined = "\n\n".join(child_content)
        node.summary = self._generate_summary(combined, max_length=500)

        return node

    def prune_old_memories(self, days: int = 30) -> int:
        """
        Prune memories older than specified days.

        Args:
            days: Age threshold in days

        Returns:
            Number of nodes pruned
        """
        cutoff = datetime.now() - timedelta(days=days)
        to_remove = []

        for node_id, node in self.nodes.items():
            if node.last_accessed < cutoff and node.access_count < 5:
                to_remove.append(node_id)

        for node_id in to_remove:
            del self.nodes[node_id]

        return len(to_remove)

    def get_context(self, max_tokens: int = 10000) -> str:
        """
        Get compressed context for LLM.

        Args:
            max_tokens: Maximum tokens to return

        Returns:
            Compressed context string
        """
        # Start from most accessed nodes
        nodes = sorted(
            self.nodes.values(),
            key=lambda n: (n.access_count, n.last_accessed),
            reverse=True,
        )

        context_parts = []
        current_tokens = 0

        for node in nodes:
            content = node.summary or node.content
            tokens = len(content) // 4

            if current_tokens + tokens > max_tokens:
                break

            context_parts.append(f"[{node.level}] {content}")
            current_tokens += tokens

        return "\n\n".join(context_parts)


# Helper function for datetime import
from datetime import timedelta
