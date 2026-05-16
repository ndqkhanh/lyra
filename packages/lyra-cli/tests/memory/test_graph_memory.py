"""Tests for Graph Memory Layer."""

import pytest
import tempfile
import shutil

from lyra_cli.memory.graph import GraphEntity, GraphRelation, GraphMemoryStore


@pytest.fixture
def temp_dir():
    """Create a temporary directory for tests."""
    temp_path = tempfile.mkdtemp()
    yield temp_path
    shutil.rmtree(temp_path)


@pytest.fixture
def store(temp_dir):
    """Create a graph memory store."""
    return GraphMemoryStore(data_dir=temp_dir)


def test_add_entity(store):
    """Test adding entities."""
    entity = GraphEntity(
        entity_id="e001",
        name="Python",
        entity_type="programming_language",
    )

    entity_id = store.add_entity(entity)
    assert entity_id == "e001"

    retrieved = store.get_entity("e001")
    assert retrieved is not None
    assert retrieved.name == "Python"


def test_add_relation(store):
    """Test adding relations."""
    # Add entities first
    e1 = GraphEntity(entity_id="e001", name="Python", entity_type="language")
    e2 = GraphEntity(entity_id="e002", name="Django", entity_type="framework")

    store.add_entity(e1)
    store.add_entity(e2)

    # Add relation
    rel = GraphRelation(
        relation_id="r001",
        source_id="e001",
        target_id="e002",
        relation_type="has_framework",
        confidence=0.9,
    )

    relation_id = store.add_relation(rel)
    assert relation_id == "r001"

    retrieved = store.get_relation("r001")
    assert retrieved is not None
    assert retrieved.confidence == 0.9


def test_get_neighbors(store):
    """Test getting neighboring entities."""
    # Create a small graph: Python -> Django, Python -> Flask
    entities = [
        GraphEntity(entity_id="e001", name="Python", entity_type="language"),
        GraphEntity(entity_id="e002", name="Django", entity_type="framework"),
        GraphEntity(entity_id="e003", name="Flask", entity_type="framework"),
    ]

    for e in entities:
        store.add_entity(e)

    relations = [
        GraphRelation(
            relation_id="r001",
            source_id="e001",
            target_id="e002",
            relation_type="has_framework",
        ),
        GraphRelation(
            relation_id="r002",
            source_id="e001",
            target_id="e003",
            relation_type="has_framework",
        ),
    ]

    for r in relations:
        store.add_relation(r)

    # Get outgoing neighbors
    neighbors = store.get_neighbors("e001", direction="outgoing")
    assert len(neighbors) == 2

    # Get incoming neighbors
    neighbors = store.get_neighbors("e002", direction="incoming")
    assert len(neighbors) == 1
    assert neighbors[0][0].entity_id == "e001"


def test_find_entities(store):
    """Test finding entities by pattern."""
    entities = [
        GraphEntity(entity_id="e001", name="Python", entity_type="language"),
        GraphEntity(entity_id="e002", name="JavaScript", entity_type="language"),
        GraphEntity(entity_id="e003", name="Django", entity_type="framework"),
    ]

    for e in entities:
        store.add_entity(e)

    # Find by name pattern
    results = store.find_entities(name_pattern="Python")
    assert len(results) == 1
    assert results[0].name == "Python"

    # Find by type
    results = store.find_entities(entity_type="language")
    assert len(results) == 2


def test_multi_hop_search(store):
    """Test multi-hop search with PageRank."""
    # Create a chain: A -> B -> C
    entities = [
        GraphEntity(entity_id="e001", name="A", entity_type="concept"),
        GraphEntity(entity_id="e002", name="B", entity_type="concept"),
        GraphEntity(entity_id="e003", name="C", entity_type="concept"),
    ]

    for e in entities:
        store.add_entity(e)

    relations = [
        GraphRelation(
            relation_id="r001",
            source_id="e001",
            target_id="e002",
            relation_type="related_to",
            confidence=0.9,
        ),
        GraphRelation(
            relation_id="r002",
            source_id="e002",
            target_id="e003",
            relation_type="related_to",
            confidence=0.8,
        ),
    ]

    for r in relations:
        store.add_relation(r)

    # Multi-hop search from A
    results = store.multi_hop_search("e001", max_hops=3)

    # Should find B and C
    assert len(results) >= 2
    entity_ids = [r[0].entity_id for r in results]
    assert "e002" in entity_ids
    assert "e003" in entity_ids


def test_confidence_filtering(store):
    """Test filtering by confidence."""
    entities = [
        GraphEntity(entity_id="e001", name="A", entity_type="concept"),
        GraphEntity(entity_id="e002", name="B", entity_type="concept"),
        GraphEntity(entity_id="e003", name="C", entity_type="concept"),
    ]

    for e in entities:
        store.add_entity(e)

    relations = [
        GraphRelation(
            relation_id="r001",
            source_id="e001",
            target_id="e002",
            relation_type="related_to",
            confidence=0.9,  # High confidence
        ),
        GraphRelation(
            relation_id="r002",
            source_id="e001",
            target_id="e003",
            relation_type="related_to",
            confidence=0.2,  # Low confidence
        ),
    ]

    for r in relations:
        store.add_relation(r)

    # Search with high confidence threshold
    results = store.multi_hop_search("e001", min_confidence=0.5)

    # Should find B (high confidence)
    entity_ids = [r[0].entity_id for r in results]
    assert "e002" in entity_ids

    # B should have higher score than C due to confidence weighting
    scores = {r[0].entity_id: r[1] for r in results}
    if "e003" in scores:
        assert scores["e002"] > scores["e003"]


def test_persistence(temp_dir):
    """Test that graph persists across store instances."""
    store1 = GraphMemoryStore(data_dir=temp_dir)

    entity = GraphEntity(entity_id="e001", name="Python", entity_type="language")
    store1.add_entity(entity)

    # Create new store instance
    store2 = GraphMemoryStore(data_dir=temp_dir)

    retrieved = store2.get_entity("e001")
    assert retrieved is not None
    assert retrieved.name == "Python"


def test_get_stats(store):
    """Test graph statistics."""
    entities = [
        GraphEntity(entity_id="e001", name="Python", entity_type="language"),
        GraphEntity(entity_id="e002", name="Django", entity_type="framework"),
    ]

    for e in entities:
        store.add_entity(e)

    rel = GraphRelation(
        relation_id="r001",
        source_id="e001",
        target_id="e002",
        relation_type="has_framework",
    )
    store.add_relation(rel)

    stats = store.get_stats()
    assert stats["num_entities"] == 2
    assert stats["num_relations"] == 1
    assert "language" in stats["entity_types"]
    assert "has_framework" in stats["relation_types"]


def test_relation_type_filtering(store):
    """Test filtering neighbors by relation type."""
    entities = [
        GraphEntity(entity_id="e001", name="Python", entity_type="language"),
        GraphEntity(entity_id="e002", name="Django", entity_type="framework"),
        GraphEntity(entity_id="e003", name="NumPy", entity_type="library"),
    ]

    for e in entities:
        store.add_entity(e)

    relations = [
        GraphRelation(
            relation_id="r001",
            source_id="e001",
            target_id="e002",
            relation_type="has_framework",
        ),
        GraphRelation(
            relation_id="r002",
            source_id="e001",
            target_id="e003",
            relation_type="has_library",
        ),
    ]

    for r in relations:
        store.add_relation(r)

    # Get only framework neighbors
    neighbors = store.get_neighbors("e001", relation_type="has_framework")
    assert len(neighbors) == 1
    assert neighbors[0][0].name == "Django"


def test_bidirectional_neighbors(store):
    """Test getting neighbors in both directions."""
    entities = [
        GraphEntity(entity_id="e001", name="A", entity_type="concept"),
        GraphEntity(entity_id="e002", name="B", entity_type="concept"),
        GraphEntity(entity_id="e003", name="C", entity_type="concept"),
    ]

    for e in entities:
        store.add_entity(e)

    relations = [
        GraphRelation(
            relation_id="r001",
            source_id="e001",
            target_id="e002",
            relation_type="related_to",
        ),
        GraphRelation(
            relation_id="r002",
            source_id="e003",
            target_id="e002",
            relation_type="related_to",
        ),
    ]

    for r in relations:
        store.add_relation(r)

    # Get neighbors in both directions
    neighbors = store.get_neighbors("e002", direction="both")
    assert len(neighbors) == 2

    entity_ids = {n[0].entity_id for n in neighbors}
    assert "e001" in entity_ids
    assert "e003" in entity_ids
