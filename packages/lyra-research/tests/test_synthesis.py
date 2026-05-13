"""
Tests for knowledge synthesis.
"""

from lyra_research.synthesis import (
    CitationNetworkBuilder,
    Concept,
    ConceptExtractor,
    KnowledgeEdge,
    KnowledgeGraph,
    KnowledgeNode,
    RelationshipDiscovery,
)


def test_concept_extractor():
    """Test concept extraction."""
    extractor = ConceptExtractor()

    content = """
    We use a transformer architecture with attention mechanisms.
    The model is evaluated on ImageNet and COCO datasets.
    We report accuracy, precision, and F1 scores.
    """

    concepts = extractor.extract(content, "paper1")

    assert len(concepts) > 0
    # Should find methods, datasets, and metrics
    categories = {c.category for c in concepts}
    assert 'method' in categories or 'dataset' in categories or 'metric' in categories


def test_citation_network_builder():
    """Test citation network building."""
    builder = CitationNetworkBuilder()

    # Add papers
    builder.add_paper("paper1", "Deep Learning", {"citations": 100})
    builder.add_paper("paper2", "Neural Networks", {"citations": 50})
    builder.add_paper("paper3", "Transformers", {"citations": 200})

    # Add citations
    builder.add_citation("paper2", "paper1")  # paper2 cites paper1
    builder.add_citation("paper3", "paper1")  # paper3 cites paper1

    assert len(builder.nodes) == 3
    assert len(builder.edges) == 2

    # Get influential papers
    influential = builder.get_influential_papers(top_k=2)
    assert len(influential) <= 2
    # paper1 should be most influential (2 citations)
    if influential:
        assert influential[0][0] == "paper1"
        assert influential[0][1] == 2


def test_citation_chain():
    """Test citation chain extraction."""
    builder = CitationNetworkBuilder()

    builder.add_paper("paper1", "Original", {})
    builder.add_paper("paper2", "Cites Original", {})
    builder.add_paper("paper3", "Cites Cites Original", {})

    builder.add_citation("paper2", "paper1")
    builder.add_citation("paper3", "paper2")

    chain = builder.get_citation_chain("paper1", max_depth=2)
    assert "paper2" in chain
    # paper3 might be in chain depending on depth


def test_relationship_discovery():
    """Test relationship discovery."""
    discovery = RelationshipDiscovery()

    papers = [
        {"id": "paper1", "title": "Paper 1"},
        {"id": "paper2", "title": "Paper 2"},
    ]

    concepts = {
        "paper1": [
            Concept(name="transformer", category="method", sources=["paper1"]),
            Concept(name="imagenet", category="dataset", sources=["paper1"]),
        ],
        "paper2": [
            Concept(name="transformer", category="method", sources=["paper2"]),
            Concept(name="coco", category="dataset", sources=["paper2"]),
        ],
    }

    relationships = discovery.discover_paper_relationships(papers, concepts)

    assert len(relationships) > 0
    # Should find shared "transformer" concept
    assert relationships[0].relationship_type == "shares_concepts"
    assert relationships[0].strength > 0.0


def test_consensus_identification():
    """Test consensus identification."""
    discovery = RelationshipDiscovery()

    papers = [
        {"id": "paper1"},
        {"id": "paper2"},
        {"id": "paper3"},
    ]

    concepts = {
        "paper1": [Concept(name="transformer", category="method", sources=["paper1"])],
        "paper2": [Concept(name="transformer", category="method", sources=["paper2"])],
        "paper3": [Concept(name="transformer", category="method", sources=["paper3"])],
    }

    consensus = discovery.identify_consensus(papers, concepts)

    # "transformer" should have consensus (3 papers)
    assert "transformer" in consensus
    assert len(consensus["transformer"]) == 3


def test_knowledge_graph():
    """Test knowledge graph construction."""
    graph = KnowledgeGraph()

    # Add nodes
    node1 = KnowledgeNode(id="paper1", type="paper", label="Deep Learning")
    node2 = KnowledgeNode(id="paper2", type="paper", label="Neural Networks")

    graph.add_node(node1)
    graph.add_node(node2)

    # Add edge
    edge = KnowledgeEdge(source="paper1", target="paper2", type="cites")
    graph.add_edge(edge)

    assert len(graph.nodes) == 2
    assert len(graph.edges) == 1

    # Get neighbors
    neighbors = graph.get_neighbors("paper1")
    assert "paper2" in neighbors


def test_knowledge_graph_concepts():
    """Test concept management in knowledge graph."""
    graph = KnowledgeGraph()

    # Add concepts
    concept1 = Concept(name="transformer", category="method", mentions=5, sources=["paper1"])
    concept2 = Concept(name="transformer", category="method", mentions=3, sources=["paper2"])

    graph.add_concept(concept1)
    graph.add_concept(concept2)

    # Should merge concepts with same name
    assert len(graph.concepts) == 1
    assert graph.concepts["transformer"].mentions == 8
    assert len(graph.concepts["transformer"].sources) == 2


def test_knowledge_graph_subgraph():
    """Test subgraph extraction."""
    graph = KnowledgeGraph()

    # Create a small graph
    for i in range(5):
        node = KnowledgeNode(id=f"node{i}", type="paper", label=f"Paper {i}")
        graph.add_node(node)

    # Add edges: 0->1->2->3->4
    for i in range(4):
        edge = KnowledgeEdge(source=f"node{i}", target=f"node{i+1}", type="cites")
        graph.add_edge(edge)

    # Extract subgraph around node0 with max_hops=2
    subgraph = graph.get_subgraph(["node0"], max_hops=2)

    # Should include node0, node1, node2
    assert len(subgraph.nodes) >= 3
    assert "node0" in subgraph.nodes
    assert "node1" in subgraph.nodes


def test_knowledge_graph_stats():
    """Test graph statistics."""
    graph = KnowledgeGraph()

    # Add nodes of different types
    graph.add_node(KnowledgeNode(id="paper1", type="paper", label="Paper 1"))
    graph.add_node(KnowledgeNode(id="repo1", type="repository", label="Repo 1"))
    graph.add_node(KnowledgeNode(id="author1", type="author", label="Author 1"))

    # Add edges of different types
    graph.add_edge(KnowledgeEdge(source="paper1", target="repo1", type="implements"))
    graph.add_edge(KnowledgeEdge(source="author1", target="paper1", type="authored"))

    stats = graph.get_stats()

    assert stats['num_nodes'] == 3
    assert stats['num_edges'] == 2
    assert 'paper' in stats['node_types']
    assert 'implements' in stats['edge_types']
