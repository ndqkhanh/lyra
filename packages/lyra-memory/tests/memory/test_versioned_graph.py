"""Tests for versioned graph database."""

import tempfile
from pathlib import Path

import pytest

from lyra_memory.eternal.versioned_graph import (
    EdgeType,
    GraphEdge,
    GraphNode,
    GraphVersion,
    NodeType,
    VersionedGraph,
)


@pytest.fixture
def temp_graph_path():
    """Create a temporary directory for graph testing."""
    with tempfile.TemporaryDirectory() as tmpdir:
        yield Path(tmpdir)


@pytest.fixture
def versioned_graph(temp_graph_path):
    """Create a versioned graph instance."""
    return VersionedGraph(base_path=temp_graph_path)


class TestGraphNode:
    """Test GraphNode creation and operations."""

    def test_create_node(self):
        """Test creating a graph node."""
        node = GraphNode.create(
            node_id="node1",
            node_type=NodeType.SEMANTIC,
            content="Python is a programming language",
            metadata={"source": "documentation"},
        )

        assert node.node_id == "node1"
        assert node.node_type == NodeType.SEMANTIC
        assert node.content == "Python is a programming language"
        assert node.content_hash is not None
        assert dict(node.metadata) == {"source": "documentation"}
        assert node.version == 1

    def test_node_immutability(self):
        """Test that nodes are immutable."""
        node = GraphNode.create("node1", NodeType.EPISODIC, "Test content")

        with pytest.raises(AttributeError):
            node.content = "Modified"  # type: ignore[misc]

    def test_node_serialization(self):
        """Test node serialization and deserialization."""
        original = GraphNode.create(
            node_id="node1",
            node_type=NodeType.PROCEDURAL,
            content="How to write tests",
            metadata={"difficulty": "medium"},
        )

        data = original.to_dict()
        restored = GraphNode.from_dict(data)

        assert restored.node_id == original.node_id
        assert restored.node_type == original.node_type
        assert restored.content == original.content
        assert restored.content_hash == original.content_hash
        assert restored.metadata == original.metadata


class TestGraphEdge:
    """Test GraphEdge creation and operations."""

    def test_create_edge(self):
        """Test creating a graph edge."""
        edge = GraphEdge.create(
            source_id="node1",
            target_id="node2",
            edge_type=EdgeType.RELATES_TO,
            weight=0.8,
            metadata={"confidence": "high"},
        )

        assert edge.source_id == "node1"
        assert edge.target_id == "node2"
        assert edge.edge_type == EdgeType.RELATES_TO
        assert edge.weight == 0.8
        assert dict(edge.metadata) == {"confidence": "high"}

    def test_edge_immutability(self):
        """Test that edges are immutable."""
        edge = GraphEdge.create("node1", "node2", EdgeType.DERIVES_FROM)

        with pytest.raises(AttributeError):
            edge.weight = 0.5  # type: ignore[misc]

    def test_edge_serialization(self):
        """Test edge serialization and deserialization."""
        original = GraphEdge.create(
            source_id="node1",
            target_id="node2",
            edge_type=EdgeType.SUPPORTS,
            weight=0.9,
        )

        data = original.to_dict()
        restored = GraphEdge.from_dict(data)

        assert restored.source_id == original.source_id
        assert restored.target_id == original.target_id
        assert restored.edge_type == original.edge_type
        assert restored.weight == original.weight


class TestVersionedGraph:
    """Test VersionedGraph operations."""

    def test_graph_initialization(self, temp_graph_path):
        """Test graph initialization."""
        graph = VersionedGraph(base_path=temp_graph_path / "test_graph")
        assert (temp_graph_path / "test_graph").exists()
        assert graph.node_count == 0
        assert graph.edge_count == 0

    def test_add_node(self, versioned_graph):
        """Test adding nodes to graph."""
        node = GraphNode.create("node1", NodeType.SEMANTIC, "Test content")
        version_id = versioned_graph.add_node(node, description="Added test node")

        assert version_id == 0
        assert versioned_graph.node_count == 1

        retrieved = versioned_graph.get_node("node1")
        assert retrieved is not None
        assert retrieved.content == "Test content"

    def test_add_edge(self, versioned_graph):
        """Test adding edges to graph."""
        node1 = GraphNode.create("node1", NodeType.SEMANTIC, "Content 1")
        node2 = GraphNode.create("node2", NodeType.SEMANTIC, "Content 2")

        versioned_graph.add_node(node1)
        versioned_graph.add_node(node2)

        edge = GraphEdge.create("node1", "node2", EdgeType.RELATES_TO)
        version_id = versioned_graph.add_edge(edge)

        assert versioned_graph.edge_count == 1

        retrieved = versioned_graph.get_edge(edge.edge_id)
        assert retrieved is not None
        assert retrieved.source_id == "node1"
        assert retrieved.target_id == "node2"

    def test_get_neighbors(self, versioned_graph):
        """Test getting neighbor nodes."""
        # Create nodes
        node1 = GraphNode.create("node1", NodeType.SEMANTIC, "Central node")
        node2 = GraphNode.create("node2", NodeType.SEMANTIC, "Neighbor 1")
        node3 = GraphNode.create("node3", NodeType.SEMANTIC, "Neighbor 2")

        versioned_graph.add_node(node1)
        versioned_graph.add_node(node2)
        versioned_graph.add_node(node3)

        # Create edges
        edge1 = GraphEdge.create("node1", "node2", EdgeType.RELATES_TO)
        edge2 = GraphEdge.create("node1", "node3", EdgeType.SUPPORTS)

        versioned_graph.add_edge(edge1)
        versioned_graph.add_edge(edge2)

        # Get all neighbors
        neighbors = versioned_graph.get_neighbors("node1")
        assert len(neighbors) == 2

        # Filter by edge type
        related = versioned_graph.get_neighbors("node1", edge_type=EdgeType.RELATES_TO)
        assert len(related) == 1
        assert related[0].node_id == "node2"

    def test_search_nodes(self, versioned_graph):
        """Test searching nodes by content."""
        node1 = GraphNode.create("node1", NodeType.SEMANTIC, "Python programming")
        node2 = GraphNode.create("node2", NodeType.SEMANTIC, "JavaScript development")
        node3 = GraphNode.create("node3", NodeType.SEMANTIC, "Python testing")

        versioned_graph.add_node(node1)
        versioned_graph.add_node(node2)
        versioned_graph.add_node(node3)

        results = versioned_graph.search_nodes("Python")
        assert len(results) == 2
        assert all("Python" in r.content for r in results)

    def test_search_nodes_by_type(self, versioned_graph):
        """Test searching nodes filtered by type."""
        node1 = GraphNode.create("node1", NodeType.SEMANTIC, "Fact about Python")
        node2 = GraphNode.create("node2", NodeType.EPISODIC, "Event with Python")
        node3 = GraphNode.create("node3", NodeType.SEMANTIC, "Another Python fact")

        versioned_graph.add_node(node1)
        versioned_graph.add_node(node2)
        versioned_graph.add_node(node3)

        semantic_results = versioned_graph.search_nodes("Python", node_type=NodeType.SEMANTIC)
        assert len(semantic_results) == 2
        assert all(r.node_type == NodeType.SEMANTIC for r in semantic_results)

    def test_get_subgraph(self, versioned_graph):
        """Test extracting a subgraph."""
        # Create a small graph: node1 -> node2 -> node3
        node1 = GraphNode.create("node1", NodeType.SEMANTIC, "Root")
        node2 = GraphNode.create("node2", NodeType.SEMANTIC, "Child")
        node3 = GraphNode.create("node3", NodeType.SEMANTIC, "Grandchild")

        versioned_graph.add_node(node1)
        versioned_graph.add_node(node2)
        versioned_graph.add_node(node3)

        edge1 = GraphEdge.create("node1", "node2", EdgeType.DERIVES_FROM)
        edge2 = GraphEdge.create("node2", "node3", EdgeType.DERIVES_FROM)

        versioned_graph.add_edge(edge1)
        versioned_graph.add_edge(edge2)

        # Extract subgraph with depth 1
        nodes, edges = versioned_graph.get_subgraph("node1", depth=1)
        assert len(nodes) == 2  # node1 and node2
        assert len(edges) >= 1  # At least edge1 (may include edge2 depending on traversal)

        # Extract subgraph with depth 2
        nodes, edges = versioned_graph.get_subgraph("node1", depth=2)
        assert len(nodes) == 3  # node1, node2, node3
        assert len(edges) == 2  # edge1, edge2


class TestVersioning:
    """Test graph versioning functionality."""

    def test_version_creation(self, versioned_graph):
        """Test that adding nodes/edges creates versions."""
        assert versioned_graph.version_count == 0

        node1 = GraphNode.create("node1", NodeType.SEMANTIC, "Content 1")
        versioned_graph.add_node(node1, description="Added node1")

        assert versioned_graph.version_count == 1

        node2 = GraphNode.create("node2", NodeType.SEMANTIC, "Content 2")
        versioned_graph.add_node(node2, description="Added node2")

        assert versioned_graph.version_count == 2

    def test_get_version(self, versioned_graph):
        """Test retrieving specific versions."""
        node1 = GraphNode.create("node1", NodeType.SEMANTIC, "Content 1")
        versioned_graph.add_node(node1)

        version = versioned_graph.get_version(0)
        assert version is not None
        assert version.version_id == 0
        assert len(version.nodes) == 1

    def test_get_current_version(self, versioned_graph):
        """Test getting the current version."""
        node1 = GraphNode.create("node1", NodeType.SEMANTIC, "Content 1")
        versioned_graph.add_node(node1)

        node2 = GraphNode.create("node2", NodeType.SEMANTIC, "Content 2")
        versioned_graph.add_node(node2)

        current = versioned_graph.get_current_version()
        assert current is not None
        assert current.version_id == 1
        assert len(current.nodes) == 2

    def test_restore_version(self, versioned_graph):
        """Test restoring graph to a previous version."""
        # Add nodes in sequence
        node1 = GraphNode.create("node1", NodeType.SEMANTIC, "Content 1")
        versioned_graph.add_node(node1)

        node2 = GraphNode.create("node2", NodeType.SEMANTIC, "Content 2")
        versioned_graph.add_node(node2)

        node3 = GraphNode.create("node3", NodeType.SEMANTIC, "Content 3")
        versioned_graph.add_node(node3)

        assert versioned_graph.node_count == 3

        # Restore to version 1 (only 2 nodes)
        success = versioned_graph.restore_version(1)
        assert success is True
        assert versioned_graph.node_count == 2

        # Restore to version 0 (only 1 node)
        success = versioned_graph.restore_version(0)
        assert success is True
        assert versioned_graph.node_count == 1

    def test_version_parent_chain(self, versioned_graph):
        """Test that versions maintain parent relationships."""
        node1 = GraphNode.create("node1", NodeType.SEMANTIC, "Content 1")
        versioned_graph.add_node(node1)

        node2 = GraphNode.create("node2", NodeType.SEMANTIC, "Content 2")
        versioned_graph.add_node(node2)

        version0 = versioned_graph.get_version(0)
        version1 = versioned_graph.get_version(1)

        assert version0 is not None
        assert version1 is not None
        assert version0.parent_version is None
        assert version1.parent_version == 0


class TestPersistence:
    """Test graph persistence to disk."""

    def test_save_and_load(self, temp_graph_path):
        """Test saving and loading graph from disk."""
        # Create graph and add data
        graph1 = VersionedGraph(base_path=temp_graph_path / "persistent")

        node1 = GraphNode.create("node1", NodeType.SEMANTIC, "Persistent content")
        graph1.add_node(node1)

        node2 = GraphNode.create("node2", NodeType.SEMANTIC, "More content")
        graph1.add_node(node2)

        # Create new graph instance with same path
        graph2 = VersionedGraph(base_path=temp_graph_path / "persistent")

        # Should load existing data
        assert graph2.node_count == 2
        assert graph2.version_count == 2

        retrieved = graph2.get_node("node1")
        assert retrieved is not None
        assert retrieved.content == "Persistent content"

    def test_version_files_created(self, temp_graph_path):
        """Test that version files are created on disk."""
        graph = VersionedGraph(base_path=temp_graph_path / "versioned")

        node = GraphNode.create("node1", NodeType.SEMANTIC, "Content")
        graph.add_node(node)

        # Check that version file exists
        version_files = list((temp_graph_path / "versioned").glob("version_*.json"))
        assert len(version_files) == 1


class TestExport:
    """Test graph export functionality."""

    def test_export_dot(self, versioned_graph):
        """Test exporting graph to DOT format."""
        node1 = GraphNode.create("node1", NodeType.SEMANTIC, "Node 1")
        node2 = GraphNode.create("node2", NodeType.SEMANTIC, "Node 2")

        versioned_graph.add_node(node1)
        versioned_graph.add_node(node2)

        edge = GraphEdge.create("node1", "node2", EdgeType.RELATES_TO)
        versioned_graph.add_edge(edge)

        dot_content = versioned_graph.export_dot()

        assert "digraph EternalMemory" in dot_content
        assert "node1" in dot_content
        assert "node2" in dot_content
        assert "relates_to" in dot_content

    def test_export_dot_to_file(self, versioned_graph, temp_graph_path):
        """Test exporting DOT to file."""
        node = GraphNode.create("node1", NodeType.SEMANTIC, "Content")
        versioned_graph.add_node(node)

        output_path = temp_graph_path / "graph.dot"
        dot_content = versioned_graph.export_dot(output_path)

        assert output_path.exists()
        assert output_path.read_text() == dot_content


class TestEdgeTypes:
    """Test different edge types."""

    def test_all_edge_types(self, versioned_graph):
        """Test creating edges with all edge types."""
        nodes = []
        for i in range(7):
            node = GraphNode.create(f"node{i}", NodeType.SEMANTIC, f"Content {i}")
            versioned_graph.add_node(node)
            nodes.append(node)

        edge_types = [
            EdgeType.DERIVES_FROM,
            EdgeType.RELATES_TO,
            EdgeType.CONTRADICTS,
            EdgeType.SUPERSEDES,
            EdgeType.SUPPORTS,
            EdgeType.TEMPORAL_NEXT,
        ]

        for i, edge_type in enumerate(edge_types):
            edge = GraphEdge.create(f"node{i}", f"node{i+1}", edge_type)
            versioned_graph.add_edge(edge)

        assert versioned_graph.edge_count == len(edge_types)


class TestNodeTypes:
    """Test different node types."""

    def test_all_node_types(self, versioned_graph):
        """Test creating nodes with all node types."""
        node_types = [
            NodeType.EPISODIC,
            NodeType.SEMANTIC,
            NodeType.PROCEDURAL,
            NodeType.META,
            NodeType.ETERNAL,
        ]

        for i, node_type in enumerate(node_types):
            node = GraphNode.create(f"node{i}", node_type, f"Content {i}")
            versioned_graph.add_node(node)

        assert versioned_graph.node_count == len(node_types)

        # Verify each type
        for i, node_type in enumerate(node_types):
            node = versioned_graph.get_node(f"node{i}")
            assert node is not None
            assert node.node_type == node_type


class TestIntegration:
    """Integration tests for versioned graph."""

    def test_full_workflow(self, versioned_graph):
        """Test complete workflow: create, query, version, restore."""
        # Create nodes
        node1 = GraphNode.create("node1", NodeType.SEMANTIC, "Python programming")
        node2 = GraphNode.create("node2", NodeType.SEMANTIC, "Testing in Python")
        node3 = GraphNode.create("node3", NodeType.PROCEDURAL, "How to write tests")

        versioned_graph.add_node(node1, description="Added Python node")
        versioned_graph.add_node(node2, description="Added testing node")
        versioned_graph.add_node(node3, description="Added procedural node")

        # Create relationships
        edge1 = GraphEdge.create("node1", "node2", EdgeType.RELATES_TO, weight=0.9)
        edge2 = GraphEdge.create("node2", "node3", EdgeType.DERIVES_FROM, weight=0.8)

        versioned_graph.add_edge(edge1, description="Linked Python and testing")
        versioned_graph.add_edge(edge2, description="Linked testing and procedure")

        # Search
        python_nodes = versioned_graph.search_nodes("Python")
        assert len(python_nodes) == 2

        # Get neighbors
        neighbors = versioned_graph.get_neighbors("node1")
        assert len(neighbors) == 1
        assert neighbors[0].node_id == "node2"

        # Get subgraph
        nodes, edges = versioned_graph.get_subgraph("node1", depth=2)
        assert len(nodes) == 3
        assert len(edges) == 2

        # Check versions
        assert versioned_graph.version_count == 5

        # Restore to earlier version
        versioned_graph.restore_version(2)
        assert versioned_graph.node_count == 3
        assert versioned_graph.edge_count == 0

        # Restore to latest
        versioned_graph.restore_version(4)
        assert versioned_graph.node_count == 3
        assert versioned_graph.edge_count == 2
