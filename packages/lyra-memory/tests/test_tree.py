"""Tests for Memory Tree."""

from datetime import datetime, timedelta

from lyra_memory.tree import MemoryTree, TreeNode


def test_tree_node_creation():
    """Test creating a tree node."""
    node = TreeNode(
        content="Test memory content",
        summary="Test summary",
        level=0,
    )

    assert node.content == "Test memory content"
    assert node.summary == "Test summary"
    assert node.level == 0
    assert len(node.children) == 0
    assert node.parent is None


def test_add_memory():
    """Test adding a memory to the tree."""
    tree = MemoryTree(max_tokens_per_node=3000)

    node = tree.add_memory(
        content="Found vulnerability CVE-2021-44228 on 192.168.1.100",
        metadata={"severity": "CRITICAL"},
    )

    assert node.content == "Found vulnerability CVE-2021-44228 on 192.168.1.100"
    assert node.metadata["severity"] == "CRITICAL"
    assert node.id in tree.nodes


def test_add_large_memory_chunks():
    """Test adding a large memory that gets chunked."""
    tree = MemoryTree(max_tokens_per_node=100)  # Small limit for testing

    # Create content larger than limit
    large_content = "A" * 500  # ~125 tokens

    node = tree.add_memory(content=large_content)

    # Should create parent with children
    assert len(node.children) > 0
    assert node.level == 1

    # Children should be in tree
    for child_id in node.children:
        assert child_id in tree.nodes


def test_retrieve_memories():
    """Test retrieving memories by query."""
    tree = MemoryTree()

    # Add some memories
    tree.add_memory("Found SQL injection in login form")
    tree.add_memory("Discovered XSS vulnerability in search")
    tree.add_memory("Port 22 SSH service running")

    # Search for SQL injection
    results = tree.retrieve("SQL injection", max_nodes=5)

    assert len(results) > 0
    assert any("SQL injection" in node.content for node in results)


def test_temporal_decay():
    """Test temporal decay in retrieval."""
    tree = MemoryTree()

    # Add old memory
    old_node = tree.add_memory("Old finding")
    old_node.created_at = datetime.now() - timedelta(days=30)

    # Add recent memory
    recent_node = tree.add_memory("Recent finding")

    # Both should match "finding"
    results = tree.retrieve("finding", max_nodes=10, temporal_decay=0.1)

    # Recent should be ranked higher
    assert results[0].id == recent_node.id


def test_access_frequency():
    """Test access frequency affects ranking."""
    tree = MemoryTree()

    node1 = tree.add_memory("Important finding")
    node2 = tree.add_memory("Another finding")

    # Access node1 multiple times by searching for "Important"
    for _ in range(5):
        tree.retrieve("Important", max_nodes=1)

    # node1 should have higher access count since only it matches "Important"
    assert tree.nodes[node1.id].access_count > tree.nodes[node2.id].access_count


def test_compress_node():
    """Test compressing a node with children."""
    tree = MemoryTree(max_tokens_per_node=100)

    # Add large memory that creates parent with children
    large_content = "A" * 500
    parent = tree.add_memory(content=large_content)

    # Compress parent
    compressed = tree.compress(parent.id)

    assert compressed.summary != ""
    # Summary should exist and be reasonable (accounting for "\n\n" between chunks)
    assert len(compressed.summary) > 0
    assert len(compressed.summary) <= 600  # Allow for separators


def test_prune_old_memories():
    """Test pruning old, rarely accessed memories."""
    tree = MemoryTree()

    # Add old memory
    old_node = tree.add_memory("Old memory")
    old_node.created_at = datetime.now() - timedelta(days=60)
    old_node.last_accessed = datetime.now() - timedelta(days=60)
    old_node.access_count = 0

    # Add recent memory
    recent_node = tree.add_memory("Recent memory")

    # Prune memories older than 30 days
    pruned_count = tree.prune_old_memories(days=30)

    assert pruned_count == 1
    assert old_node.id not in tree.nodes
    assert recent_node.id in tree.nodes


def test_get_context():
    """Test getting compressed context for LLM."""
    tree = MemoryTree()

    # Add several memories
    for i in range(10):
        node = tree.add_memory(f"Finding {i}: Some vulnerability details")
        node.access_count = i  # Vary access counts

    # Get context
    context = tree.get_context(max_tokens=1000)

    assert len(context) > 0
    # Should include most accessed memories first
    assert "Finding 9" in context


def test_hierarchical_retrieval():
    """Test retrieving with children included."""
    tree = MemoryTree(max_tokens_per_node=100)

    # Add large memory with children
    large_content = "Parent content " + "A" * 500
    parent = tree.add_memory(content=large_content)

    # Retrieve with children
    results = tree.retrieve("Parent", max_nodes=2, include_children=True)

    # Should include parent and children
    assert len(results) > 1
    assert any(node.id == parent.id for node in results)


def test_metadata_preservation():
    """Test that metadata is preserved."""
    tree = MemoryTree()

    metadata = {
        "target": "192.168.1.100",
        "severity": "HIGH",
        "cve": "CVE-2021-44228",
    }

    node = tree.add_memory("Test finding", metadata=metadata)

    assert node.metadata == metadata
    assert tree.nodes[node.id].metadata == metadata
