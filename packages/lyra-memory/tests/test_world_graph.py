"""
Tests for WorldDB-style Graph-of-Worlds Memory Engine.

Covers:
- World creation and management
- Entity (node) addition, retrieval, and filtering
- Relation (edge) management with typed connections
- Cross-world edges
- Temporal snapshots
- World merging with conflict detection
- Export functionality
- Semantic and substring search
"""

from datetime import datetime, timedelta

import pytest

from lyra_memory.world_graph import (
    CrossWorldEdge,
    World,
    WorldGraph,
    WorldGraphMemory,
    WorldNode,
    WorldNodeType,
    WorldRelation,
    WorldRelationType,
)


class TestWorldNode:
    """Tests for WorldNode frozen dataclass."""

    def test_create_node_with_defaults(self):
        node = WorldNode(label="test_node")
        assert node.label == "test_node"
        assert node.node_type == WorldNodeType.ENTITY
        assert node.properties == {}
        assert node.embedding is None

    def test_create_node_with_all_fields(self):
        node = WorldNode(
            label="MyClass",
            node_type=WorldNodeType.CLASS,
            properties={"language": "python", "lines": 150},
            embedding=[0.1, 0.2, 0.3],
        )
        assert node.label == "MyClass"
        assert node.node_type == WorldNodeType.CLASS
        assert node.properties["language"] == "python"
        assert node.embedding == [0.1, 0.2, 0.3]

    def test_node_immutable(self):
        node = WorldNode(label="test")
        with pytest.raises(Exception):
            node.label = "changed"  # type: ignore[misc]

    def test_node_unique_ids(self):
        node_a = WorldNode(label="a")
        node_b = WorldNode(label="b")
        assert node_a.id != node_b.id


class TestWorldRelation:
    """Tests for WorldRelation frozen dataclass."""

    def test_create_relation(self):
        rel = WorldRelation(
            source_id="node1",
            target_id="node2",
            relation_type=WorldRelationType.DEPENDS_ON,
            weight=0.8,
        )
        assert rel.source_id == "node1"
        assert rel.target_id == "node2"
        assert rel.relation_type == WorldRelationType.DEPENDS_ON
        assert rel.weight == 0.8

    def test_relation_weight_validation(self):
        with pytest.raises(ValueError, match="Weight must be"):
            WorldRelation(source_id="a", target_id="b", weight=2.0)

    def test_relation_default_weight(self):
        rel = WorldRelation(source_id="a", target_id="b")
        assert rel.weight == 1.0

    def test_relation_immutable(self):
        rel = WorldRelation(source_id="a", target_id="b")
        with pytest.raises(Exception):
            rel.weight = 0.5  # type: ignore[misc]


class TestWorld:
    """Tests for World frozen dataclass."""

    def test_create_world(self):
        world = World(name="Project Alpha", description="AI research project")
        assert world.name == "Project Alpha"
        assert "AI research" in world.description

    def test_world_unique_ids(self):
        w1 = World(name="w1")
        w2 = World(name="w2")
        assert w1.id != w2.id


class TestWorldGraph:
    """Tests for WorldGraph core graph operations."""

    def setup_method(self):
        self.graph = WorldGraph()

    def test_add_world(self):
        world = World(name="TestWorld", description="A test world")
        world_id = self.graph.add_world(world)
        assert world_id == world.id
        assert self.graph.get_world(world_id) is world

    def test_list_worlds(self):
        self.graph.add_world(World(name="World A"))
        self.graph.add_world(World(name="World B"))
        assert len(self.graph.list_worlds()) == 2

    def test_remove_world(self):
        world = World(name="ToDelete")
        world_id = self.graph.add_world(world)
        assert self.graph.remove_world(world_id) is True
        assert self.graph.get_world(world_id) is None
        assert self.graph.remove_world("nonexistent") is False

    def test_add_node_to_world(self):
        world_id = self.graph.add_world(World(name="W"))
        node = WorldNode(label="function_a", node_type=WorldNodeType.FUNCTION)
        node_id = self.graph.add_node(world_id, node)

        retrieved = self.graph.get_node(world_id, node_id)
        assert retrieved is not None
        assert retrieved.label == "function_a"

    def test_add_node_to_nonexistent_world(self):
        node = WorldNode(label="orphan")
        with pytest.raises(ValueError, match="not found"):
            self.graph.add_node("nonexistent", node)

    def test_list_nodes_by_type(self):
        world_id = self.graph.add_world(World(name="W"))
        self.graph.add_node(world_id, WorldNode(label="f1", node_type=WorldNodeType.FUNCTION))
        self.graph.add_node(world_id, WorldNode(label="f2", node_type=WorldNodeType.FUNCTION))
        self.graph.add_node(world_id, WorldNode(label="c1", node_type=WorldNodeType.CLASS))

        functions = self.graph.list_nodes(world_id, node_type=WorldNodeType.FUNCTION)
        classes = self.graph.list_nodes(world_id, node_type=WorldNodeType.CLASS)

        assert len(functions) == 2
        assert len(classes) == 1

    def test_remove_node(self):
        world_id = self.graph.add_world(World(name="W"))
        node_id = self.graph.add_node(world_id, WorldNode(label="temp"))
        assert self.graph.remove_node(world_id, node_id) is True
        assert self.graph.get_node(world_id, node_id) is None
        assert self.graph.remove_node(world_id, "nonexistent") is False

    def test_add_relation(self):
        world_id = self.graph.add_world(World(name="W"))
        n1 = self.graph.add_node(world_id, WorldNode(label="A"))
        n2 = self.graph.add_node(world_id, WorldNode(label="B"))

        rel = WorldRelation(
            source_id=n1,
            target_id=n2,
            relation_type=WorldRelationType.CALLS,
        )
        rel_id = self.graph.add_relation(world_id, rel)
        assert rel_id is not None
        assert self.graph.get_relation(world_id, rel_id) is not None

    def test_add_relation_missing_node(self):
        world_id = self.graph.add_world(World(name="W"))
        rel = WorldRelation(source_id="ghost", target_id="phantom")
        with pytest.raises(ValueError):
            self.graph.add_relation(world_id, rel)

    def test_list_relations_by_type(self):
        world_id = self.graph.add_world(World(name="W"))
        n1 = self.graph.add_node(world_id, WorldNode(label="A"))
        n2 = self.graph.add_node(world_id, WorldNode(label="B"))
        n3 = self.graph.add_node(world_id, WorldNode(label="C"))

        self.graph.add_relation(world_id, WorldRelation(
            source_id=n1, target_id=n2, relation_type=WorldRelationType.DEPENDS_ON,
        ))
        self.graph.add_relation(world_id, WorldRelation(
            source_id=n1, target_id=n3, relation_type=WorldRelationType.CALLS,
        ))

        depends = self.graph.list_relations(world_id, relation_type=WorldRelationType.DEPENDS_ON)
        calls = self.graph.list_relations(world_id, relation_type=WorldRelationType.CALLS)
        assert len(depends) == 1
        assert len(calls) == 1

    def test_remove_relation(self):
        world_id = self.graph.add_world(World(name="W"))
        n1 = self.graph.add_node(world_id, WorldNode(label="A"))
        n2 = self.graph.add_node(world_id, WorldNode(label="B"))
        rel = WorldRelation(source_id=n1, target_id=n2)
        rel_id = self.graph.add_relation(world_id, rel)

        assert self.graph.remove_relation(world_id, rel_id) is True
        assert self.graph.get_relation(world_id, rel_id) is None

    def test_get_neighbors_both_directions(self):
        world_id = self.graph.add_world(World(name="W"))
        n1 = self.graph.add_node(world_id, WorldNode(label="Center"))
        n2 = self.graph.add_node(world_id, WorldNode(label="Outbound"))
        n3 = self.graph.add_node(world_id, WorldNode(label="Inbound"))

        self.graph.add_relation(world_id, WorldRelation(
            source_id=n1, target_id=n2, relation_type=WorldRelationType.CALLS,
        ))
        self.graph.add_relation(world_id, WorldRelation(
            source_id=n3, target_id=n1, relation_type=WorldRelationType.DEPENDS_ON,
        ))

        neighbors = self.graph.get_neighbors(world_id, n1, direction="both")
        neighbor_labels = {n[0].label for n in neighbors}
        assert "Outbound" in neighbor_labels
        assert "Inbound" in neighbor_labels

    def test_get_neighbors_filtered(self):
        world_id = self.graph.add_world(World(name="W"))
        n1 = self.graph.add_node(world_id, WorldNode(label="A"))
        n2 = self.graph.add_node(world_id, WorldNode(label="B"))
        n3 = self.graph.add_node(world_id, WorldNode(label="C"))

        self.graph.add_relation(world_id, WorldRelation(
            source_id=n1, target_id=n2, relation_type=WorldRelationType.CALLS,
        ))
        self.graph.add_relation(world_id, WorldRelation(
            source_id=n1, target_id=n3, relation_type=WorldRelationType.DEPENDS_ON,
        ))

        filtered = self.graph.get_neighbors(
            world_id, n1, direction="outbound",
            relation_type=WorldRelationType.CALLS,
        )
        assert len(filtered) == 1
        assert filtered[0][0].label == "B"

    def test_cross_world_edges(self):
        w1 = self.graph.add_world(World(name="World A"))
        w2 = self.graph.add_world(World(name="World B"))
        n1 = self.graph.add_node(w1, WorldNode(label="Node A1"))
        n2 = self.graph.add_node(w2, WorldNode(label="Node B1"))

        edge = CrossWorldEdge(
            source_world_id=w1,
            source_node_id=n1,
            target_world_id=w2,
            target_node_id=n2,
            relation_type=WorldRelationType.ANALOGY,
        )
        self.graph.add_cross_world_edge(edge)

        edges = self.graph.list_cross_world_edges()
        assert len(edges) == 1

        edges_filtered = self.graph.list_cross_world_edges(
            relation_type=WorldRelationType.ANALOGY,
        )
        assert len(edges_filtered) == 1

    def test_cross_world_edge_validation(self):
        with pytest.raises(ValueError, match="Weight"):
            CrossWorldEdge(
                source_world_id="x", source_node_id="n1",
                target_world_id="y", target_node_id="n2",
                weight=1.5,
            )

    def test_snapshot(self):
        world_id = self.graph.add_world(World(name="W"))
        self.graph.add_node(world_id, WorldNode(label="A"))
        self.graph.add_node(world_id, WorldNode(label="B"))

        snap = self.graph.snapshot(world_id, metadata={"version": "v1"})
        assert snap.world_id == world_id
        assert len(snap.node_ids) == 2
        assert snap.metadata["version"] == "v1"

        snapshots = self.graph.get_snapshots(world_id)
        assert len(snapshots) == 1

    def test_snapshot_nonexistent_world(self):
        with pytest.raises(ValueError, match="not found"):
            self.graph.snapshot("ghost")

    def test_get_snapshot_at_timestamp(self):
        world_id = self.graph.add_world(World(name="W"))
        self.graph.add_node(world_id, WorldNode(label="A"))
        self.graph.snapshot(world_id)
        t1 = datetime.now()

        self.graph.add_node(world_id, WorldNode(label="B"))
        self.graph.snapshot(world_id)
        t2 = datetime.now()

        snap_at_t1 = self.graph.get_snapshot_at(world_id, t1)
        assert snap_at_t1 is not None
        assert len(snap_at_t1.node_ids) == 1

        snap_at_t2 = self.graph.get_snapshot_at(world_id, t2)
        assert snap_at_t2 is not None
        assert len(snap_at_t2.node_ids) == 2

    def test_get_snapshot_at_when_no_snapshots(self):
        world_id = self.graph.add_world(World(name="W"))
        result = self.graph.get_snapshot_at(world_id, datetime.now())
        assert result is None

    def test_stats(self):
        self.graph.add_world(World(name="W1"))
        self.graph.add_world(World(name="W2"))
        stats = self.graph.stats
        assert stats["worlds"] == 2
        assert stats["nodes"] == 0
        assert stats["relations"] == 0

    def test_export_graph(self):
        w1 = self.graph.add_world(World(name="World A"))
        n1 = self.graph.add_node(w1, WorldNode(label="Node1"))
        n2 = self.graph.add_node(w1, WorldNode(label="Node2"))
        self.graph.add_relation(w1, WorldRelation(
            source_id=n1, target_id=n2, relation_type=WorldRelationType.DEPENDS_ON,
        ))

        exported = self.graph.export_graph()
        assert "nodes" in exported
        assert "edges" in exported
        assert "worlds" in exported
        assert len(exported["nodes"]) == 2
        assert len(exported["edges"]) == 1
        assert len(exported["worlds"]) == 1

    def test_remove_world_cleans_up_cross_world_edges(self):
        w1 = self.graph.add_world(World(name="A"))
        w2 = self.graph.add_world(World(name="B"))
        n1 = self.graph.add_node(w1, WorldNode(label="n1"))
        n2 = self.graph.add_node(w2, WorldNode(label="n2"))

        self.graph.add_cross_world_edge(CrossWorldEdge(
            source_world_id=w1, source_node_id=n1,
            target_world_id=w2, target_node_id=n2,
        ))
        self.graph.remove_world(w1)
        assert len(self.graph.list_cross_world_edges()) == 0


class TestWorldGraphMemory:
    """Tests for the WorldGraphMemory high-level engine."""

    def setup_method(self):
        self.memory = WorldGraphMemory()

    def test_add_world(self):
        world_id = self.memory.add_world("Project X", "A test project")
        assert world_id is not None
        world = self.memory.graph.get_world(world_id)
        assert world.name == "Project X"

    def test_add_entity(self):
        world_id = self.memory.add_world("Test World")
        node_id = self.memory.add_entity(
            world_id,
            label="my_function",
            node_type=WorldNodeType.FUNCTION,
            properties={"language": "python"},
        )
        node = self.memory.graph.get_node(world_id, node_id)
        assert node is not None
        assert node.label == "my_function"
        assert node.node_type == WorldNodeType.FUNCTION
        assert node.properties["language"] == "python"

    def test_add_relation(self):
        world_id = self.memory.add_world("Test World")
        n1 = self.memory.add_entity(world_id, label="A")
        n2 = self.memory.add_entity(world_id, label="B")

        rel_id = self.memory.add_relation(
            world_id, n1, n2,
            rel_type=WorldRelationType.CALLS,
            weight=0.9,
        )
        assert rel_id is not None
        relation = self.memory.graph.get_relation(world_id, rel_id)
        assert relation.weight == 0.9

    def test_create_snapshot(self):
        world_id = self.memory.add_world("W")
        self.memory.add_entity(world_id, label="entity1")
        snap = self.memory.create_snapshot(world_id, metadata={"tag": "v1"})
        assert snap.world_id == world_id
        assert len(snap.node_ids) == 1

    def test_get_temporal_snapshot(self):
        world_id = self.memory.add_world("W")
        self.memory.add_entity(world_id, label="e1")
        self.memory.create_snapshot(world_id)

        later = datetime.now() + timedelta(hours=1)
        snap = self.memory.get_temporal_snapshot(world_id, timestamp=later)
        assert snap is not None
        assert len(snap.node_ids) == 1

    def test_cross_world_search_no_embedder(self):
        w1 = self.memory.add_world("Python Project")
        w2 = self.memory.add_world("Rust Project")
        self.memory.add_entity(w1, label="auth_module")
        self.memory.add_entity(w2, label="auth_crate")

        results = self.memory.cross_world_search("auth", top_k=5)
        assert len(results) == 2
        labels = {r[0].label for r in results}
        assert "auth_module" in labels
        assert "auth_crate" in labels

    def test_query_world_no_embedder(self):
        world_id = self.memory.add_world("W")
        self.memory.add_entity(world_id, label="database_connector")
        self.memory.add_entity(world_id, label="cache_layer")
        self.memory.add_entity(world_id, label="api_handler")

        results = self.memory.query_world(world_id, "database", top_k=3)
        assert len(results) == 3
        assert results[0][0].label == "database_connector"
        assert results[0][1] == 1.0  # exact match score

    def test_query_world_empty(self):
        world_id = self.memory.add_world("Empty")
        results = self.memory.query_world(world_id, "anything")
        assert results == []

    def test_merge_worlds_success(self):
        w1 = self.memory.add_world("Project A")
        w2 = self.memory.add_world("Project B")
        self.memory.add_entity(w1, label="utils")
        self.memory.add_entity(w1, label="config")
        self.memory.add_entity(w2, label="config")
        self.memory.add_entity(w2, label="server")

        merged_id = self.memory.merge_worlds(w1, w2, new_name="Merged")

        merged_world = self.memory.graph.get_world(merged_id)
        assert merged_world is not None
        assert "Merged" in merged_world.name

        nodes = self.memory.graph.list_nodes(merged_id)
        assert len(nodes) == 3  # utils, config (merged), server

        conflicts = self.memory.get_merge_conflicts(merged_id)
        assert len(conflicts) == 1
        assert "config" in conflicts[0]

    def test_merge_worlds_nonexistent(self):
        self.memory.add_world("A")
        with pytest.raises(ValueError, match="not found"):
            self.memory.merge_worlds("nonexistent", "also_fake")

    def test_merge_worlds_preserves_originals(self):
        w1 = self.memory.add_world("A")
        w2 = self.memory.add_world("B")
        self.memory.add_entity(w1, label="shared")
        self.memory.add_entity(w2, label="unique")

        self.memory.merge_worlds(w1, w2)

        assert len(self.memory.graph.list_nodes(w1)) == 1
        assert len(self.memory.graph.list_nodes(w2)) == 1

    def test_export_graph(self):
        world_id = self.memory.add_world("W")
        self.memory.add_entity(world_id, label="e1")
        self.memory.add_entity(world_id, label="e2")

        exported = self.memory.export_graph()
        assert len(exported["nodes"]) == 2
        assert len(exported["worlds"]) == 1

    def test_stats(self):
        self.memory.add_world("W1")
        self.memory.add_world("W2")
        assert self.memory.stats["worlds"] == 2

    def test_world_count(self):
        assert self.memory.world_count == 0
        self.memory.add_world("W1")
        assert self.memory.world_count == 1

    def test_query_world_with_node_type_filter(self):
        world_id = self.memory.add_world("W")
        self.memory.add_entity(world_id, label="f1", node_type=WorldNodeType.FUNCTION)
        self.memory.add_entity(world_id, label="c1", node_type=WorldNodeType.CLASS)

        results = self.memory.query_world(world_id, "f", node_type=WorldNodeType.FUNCTION)
        assert len(results) == 1
        assert results[0][0].label == "f1"

    def test_cross_world_search_empty(self):
        results = self.memory.cross_world_search("nothing")
        assert results == []

    def test_semantic_search_with_embedder(self):
        class MockEmbedder:
            def encode(self, text):
                return [0.1, 0.2, 0.3]

        memory = WorldGraphMemory(embedder=MockEmbedder())
        world_id = memory.add_world("W")
        memory.add_entity(world_id, label="test_entity", content="embed this")

        results = memory.query_world(world_id, "search query", top_k=5)
        assert len(results) == 1

    def test_cross_world_search_no_match(self):
        w1 = self.memory.add_world("W1")
        self.memory.add_entity(w1, label="foo")
        results = self.memory.cross_world_search("zzzzzz")
        assert all(score == 0.0 for _, _, score in results)


class TestWorldGraphMemoryWithRelations:
    """Integration tests with entities and relations."""

    def setup_method(self):
        self.memory = WorldGraphMemory()

    def test_full_workflow(self):
        world_id = self.memory.add_world("Codebase Graph")
        n1 = self.memory.add_entity(world_id, label="auth.py", node_type=WorldNodeType.FILE)
        n2 = self.memory.add_entity(world_id, label="login", node_type=WorldNodeType.FUNCTION)
        n3 = self.memory.add_entity(world_id, label="db.py", node_type=WorldNodeType.FILE)
        n4 = self.memory.add_entity(world_id, label="connect", node_type=WorldNodeType.FUNCTION)

        self.memory.add_relation(world_id, n1, n2, WorldRelationType.CONTAINS)
        self.memory.add_relation(world_id, n3, n4, WorldRelationType.CONTAINS)
        self.memory.add_relation(world_id, n2, n4, WorldRelationType.CALLS)
        self.memory.add_relation(world_id, n1, n3, WorldRelationType.IMPORTS)

        neighbors = self.memory.graph.get_neighbors(world_id, n1, direction="outbound")
        assert len(neighbors) == 2

        self.memory.create_snapshot(world_id)
        snapshots = self.memory.graph.get_snapshots(world_id)
        assert len(snapshots) == 1
        assert len(snapshots[0].node_ids) == 4
        assert len(snapshots[0].relation_ids) == 4

        exported = self.memory.export_graph()
        assert len(exported["nodes"]) == 4
        assert len(exported["edges"]) == 4


if __name__ == "__main__":
    pytest.main([__file__, "-v"])
