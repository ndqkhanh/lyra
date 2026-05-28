"""
Tests for multi-graph knowledge store.
"""

import pytest

from lyra_memory.multi_graph import (
    CausalRelation,
    EntityRelation,
    GraphType,
    MultiGraphStore,
    SemanticRelation,
    TemporalRelation,
)


class TestMultiGraphStore:
    """Test multi-graph knowledge store functionality."""

    def setup_method(self):
        """Set up test fixtures."""
        self.store = MultiGraphStore()

    def test_add_semantic_edge(self):
        """Test adding semantic relationships."""
        edge = self.store.add_edge(
            graph_type=GraphType.SEMANTIC,
            source_id="mem1",
            target_id="mem2",
            relation=SemanticRelation.IS_A.value,
            weight=1.0,
        )

        assert edge.source_id == "mem1"
        assert edge.target_id == "mem2"
        assert edge.relation == SemanticRelation.IS_A.value

    def test_get_outbound_neighbors(self):
        """Test getting outbound neighbors."""
        self.store.add_edge(
            graph_type=GraphType.SEMANTIC,
            source_id="mem1",
            target_id="mem2",
            relation=SemanticRelation.RELATED_TO.value,
        )
        self.store.add_edge(
            graph_type=GraphType.SEMANTIC,
            source_id="mem1",
            target_id="mem3",
            relation=SemanticRelation.PART_OF.value,
        )

        neighbors = self.store.get_neighbors(
            memory_id="mem1",
            graph_type=GraphType.SEMANTIC,
            direction="outbound",
        )

        assert len(neighbors) == 2
        target_ids = {e.target_id for e in neighbors}
        assert target_ids == {"mem2", "mem3"}

    def test_get_inbound_neighbors(self):
        """Test getting inbound neighbors."""
        self.store.add_edge(
            graph_type=GraphType.TEMPORAL,
            source_id="mem1",
            target_id="mem2",
            relation=TemporalRelation.BEFORE.value,
        )

        neighbors = self.store.get_neighbors(
            memory_id="mem2",
            graph_type=GraphType.TEMPORAL,
            direction="inbound",
        )

        assert len(neighbors) == 1
        assert neighbors[0].source_id == "mem1"

    def test_relation_filter(self):
        """Test filtering by relation type."""
        self.store.add_edge(
            graph_type=GraphType.CAUSAL,
            source_id="mem1",
            target_id="mem2",
            relation=CausalRelation.CAUSES.value,
        )
        self.store.add_edge(
            graph_type=GraphType.CAUSAL,
            source_id="mem1",
            target_id="mem3",
            relation=CausalRelation.ENABLES.value,
        )

        causes_edges = self.store.get_neighbors(
            memory_id="mem1",
            graph_type=GraphType.CAUSAL,
            direction="outbound",
            relation_filter=CausalRelation.CAUSES.value,
        )

        assert len(causes_edges) == 1
        assert causes_edges[0].target_id == "mem2"

    def test_traverse_graph(self):
        """Test graph traversal."""
        # Create a chain: mem1 -> mem2 -> mem3 -> mem4
        self.store.add_edge(
            graph_type=GraphType.SEMANTIC,
            source_id="mem1",
            target_id="mem2",
            relation=SemanticRelation.RELATED_TO.value,
        )
        self.store.add_edge(
            graph_type=GraphType.SEMANTIC,
            source_id="mem2",
            target_id="mem3",
            relation=SemanticRelation.RELATED_TO.value,
        )
        self.store.add_edge(
            graph_type=GraphType.SEMANTIC,
            source_id="mem3",
            target_id="mem4",
            relation=SemanticRelation.RELATED_TO.value,
        )

        # Traverse with depth 2
        reachable = self.store.traverse(
            start_id="mem1",
            graph_type=GraphType.SEMANTIC,
            max_depth=2,
        )

        assert "mem2" in reachable
        assert "mem3" in reachable
        assert "mem4" not in reachable  # Beyond depth 2

    def test_find_path(self):
        """Test finding shortest path."""
        # Create a graph
        self.store.add_edge(
            graph_type=GraphType.SEMANTIC,
            source_id="mem1",
            target_id="mem2",
            relation=SemanticRelation.RELATED_TO.value,
        )
        self.store.add_edge(
            graph_type=GraphType.SEMANTIC,
            source_id="mem2",
            target_id="mem3",
            relation=SemanticRelation.RELATED_TO.value,
        )

        path = self.store.find_path(
            start_id="mem1",
            end_id="mem3",
            graph_type=GraphType.SEMANTIC,
        )

        assert path == ["mem1", "mem2", "mem3"]

    def test_get_related_memories(self):
        """Test getting related memories across all graphs."""
        # Add edges in different graphs
        self.store.add_edge(
            graph_type=GraphType.SEMANTIC,
            source_id="mem1",
            target_id="mem2",
            relation=SemanticRelation.RELATED_TO.value,
            weight=1.0,
        )
        self.store.add_edge(
            graph_type=GraphType.TEMPORAL,
            source_id="mem1",
            target_id="mem3",
            relation=TemporalRelation.BEFORE.value,
            weight=1.0,
        )
        self.store.add_edge(
            graph_type=GraphType.CAUSAL,
            source_id="mem1",
            target_id="mem4",
            relation=CausalRelation.CAUSES.value,
            weight=1.0,
        )

        related = self.store.get_related_memories(
            memory_id="mem1",
            max_results=10,
        )

        assert len(related) == 3
        memory_ids = {mem_id for mem_id, _ in related}
        assert memory_ids == {"mem2", "mem3", "mem4"}

    def test_multiple_graph_types(self):
        """Test that different graph types are independent."""
        # Add same edge in different graphs
        self.store.add_edge(
            graph_type=GraphType.SEMANTIC,
            source_id="mem1",
            target_id="mem2",
            relation=SemanticRelation.RELATED_TO.value,
        )
        self.store.add_edge(
            graph_type=GraphType.ENTITY,
            source_id="mem1",
            target_id="mem2",
            relation=EntityRelation.USES.value,
        )

        semantic_neighbors = self.store.get_neighbors(
            memory_id="mem1",
            graph_type=GraphType.SEMANTIC,
            direction="outbound",
        )

        entity_neighbors = self.store.get_neighbors(
            memory_id="mem1",
            graph_type=GraphType.ENTITY,
            direction="outbound",
        )

        assert len(semantic_neighbors) == 1
        assert len(entity_neighbors) == 1
        assert semantic_neighbors[0].relation != entity_neighbors[0].relation


if __name__ == "__main__":
    pytest.main([__file__, "-v"])
