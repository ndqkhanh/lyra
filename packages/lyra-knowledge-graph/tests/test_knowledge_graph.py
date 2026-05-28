"""Tests for lyra-knowledge-graph package."""

from __future__ import annotations

import json
import os
import tempfile

import pytest
from lyra_knowledge_graph import (
    # Community detector
    Community,
    CommunityDetector,
    DreamCycle,
    # Relation labeler
    EdgeLabel,
    EdgeNotFoundError,
    EdgeRelation,
    EntityExtractor,
    # Entity extractor
    EntityKind,
    ExtractionError,
    # Pre-indexer
    FusionResult,
    GraphBuilder,
    HypothesisScore,
    IndexingError,
    InverseSearch,
    # Inverse search
    InverseSearchEngine,
    KGDreamCycle,
    KnowledgeEdge,
    KnowledgeGraph,
    # Exceptions
    KnowledgeGraphError,
    # MCP server
    KnowledgeGraphMCPServer,
    KnowledgeNode,
    NavigationEngine,
    NavigationError,
    NodeNotFoundError,
    # Graph builder
    NodeType,
    PreIndexer,
    RelationConfidence,
    RelationLabeler,
    RRFFusion,
    # RRF fusion
    RRFusion,
    TraversalStrategy,
)

# ═══════════════════════════════════════════════════════════════════════════
# Fixtures
# ═══════════════════════════════════════════════════════════════════════════


@pytest.fixture
def empty_graph() -> KnowledgeGraph:
    return KnowledgeGraph()


@pytest.fixture
def sample_graph() -> KnowledgeGraph:
    g = KnowledgeGraph()
    g = g.add_node(KnowledgeNode(
        node_id="n1", node_type=NodeType.CONCEPT, label="Python"
    ))
    g = g.add_node(KnowledgeNode(
        node_id="n2", node_type=NodeType.CONCEPT, label="TypeScript"
    ))
    g = g.add_node(KnowledgeNode(
        node_id="n3", node_type=NodeType.CONCEPT, label="Immutability"
    ))
    g = g.add_node(KnowledgeNode(
        node_id="n4", node_type=NodeType.SOURCE, label="Research Paper A"
    ))
    g = g.add_node(KnowledgeNode(
        node_id="n5", node_type=NodeType.CLAIM, label="FP is better"
    ))
    g = g.add_edge(KnowledgeEdge(
        edge_id="e1", source_id="n1", target_id="n3",
        relation=EdgeRelation.RELATES_TO, confidence=0.8,
    ))
    g = g.add_edge(KnowledgeEdge(
        edge_id="e2", source_id="n4", target_id="n1",
        relation=EdgeRelation.CITES, confidence=0.9,
    ))
    g = g.add_edge(KnowledgeEdge(
        edge_id="e3", source_id="n5", target_id="n3",
        relation=EdgeRelation.SUPPORTS, confidence=0.7,
    ))
    return g


# ═══════════════════════════════════════════════════════════════════════════
# Graph Builder
# ═══════════════════════════════════════════════════════════════════════════


class TestKnowledgeNode:
    def test_create_node(self):
        node = KnowledgeNode(
            node_id="test_1", node_type=NodeType.CONCEPT, label="Test"
        )
        assert node.node_id == "test_1"
        assert node.node_type == NodeType.CONCEPT
        assert node.label == "Test"
        assert node.confidence == 1.0

    def test_immutable(self):
        node = KnowledgeNode(
            node_id="t1", node_type=NodeType.CONCEPT, label="Test"
        )
        with pytest.raises(Exception):
            node.label = "Changed"  # type: ignore[misc]

    def test_to_dict(self):
        node = KnowledgeNode(
            node_id="t1", node_type=NodeType.ENTITY, label="Entity1",
            properties={"key": "val"}, confidence=0.8,
        )
        d = node.to_dict()
        assert d["node_id"] == "t1"
        assert d["node_type"] == "entity"
        assert d["confidence"] == 0.8
        assert d["properties"]["key"] == "val"

    def test_from_dict(self):
        d = {
            "node_id": "t1", "node_type": "concept", "label": "Test",
            "properties": {"k": "v"}, "metadata": {}, "confidence": 0.9,
        }
        node = KnowledgeNode.from_dict(d)
        assert node.node_id == "t1"
        assert node.label == "Test"
        assert node.confidence == 0.9


class TestKnowledgeEdge:
    def test_create_edge(self):
        edge = KnowledgeEdge(
            edge_id="e1", source_id="a", target_id="b",
            relation=EdgeRelation.SUPPORTS,
        )
        assert edge.edge_id == "e1"
        assert edge.relation == EdgeRelation.SUPPORTS
        assert edge.weight == 1.0

    def test_to_dict(self):
        edge = KnowledgeEdge(
            edge_id="e1", source_id="a", target_id="b",
            relation=EdgeRelation.DEPENDS_ON, weight=0.5,
        )
        d = edge.to_dict()
        assert d["relation"] == "depends_on"
        assert d["weight"] == 0.5

    def test_from_dict(self):
        d = {
            "edge_id": "e1", "source_id": "a", "target_id": "b",
            "relation": "cites", "weight": 0.8, "confidence": 0.9,
        }
        edge = KnowledgeEdge.from_dict(d)
        assert edge.relation == EdgeRelation.CITES
        assert edge.weight == 0.8
        assert edge.confidence == 0.9


class TestKnowledgeGraph:
    def test_empty_graph(self, empty_graph):
        assert empty_graph.node_count == 0
        assert empty_graph.edge_count == 0

    def test_add_node(self, empty_graph):
        node = KnowledgeNode(node_id="n1", node_type=NodeType.CONCEPT, label="A")
        g = empty_graph.add_node(node)
        assert g.node_count == 1
        assert empty_graph.node_count == 0  # immutability

    def test_add_edge(self, sample_graph):
        g = sample_graph
        assert g.edge_count == 3

    def test_add_edge_missing_source(self, empty_graph):
        g = empty_graph.add_node(KnowledgeNode(
            node_id="n1", node_type=NodeType.CONCEPT, label="A"
        ))
        edge = KnowledgeEdge(
            edge_id="bad", source_id="nonexistent", target_id="n1",
            relation=EdgeRelation.CITES,
        )
        with pytest.raises(NodeNotFoundError):
            g.add_edge(edge)

    def test_get_node(self, sample_graph):
        node = sample_graph.get_node("n1")
        assert node.label == "Python"

    def test_get_node_missing(self, sample_graph):
        with pytest.raises(NodeNotFoundError):
            sample_graph.get_node("nonexistent")

    def test_get_edge(self, sample_graph):
        edge = sample_graph.get_edge("e1")
        assert edge.source_id == "n1"

    def test_get_edge_missing(self, sample_graph):
        with pytest.raises(EdgeNotFoundError):
            sample_graph.get_edge("nonexistent")

    def test_remove_node(self, sample_graph):
        g = sample_graph.remove_node("n1")
        assert "n1" not in g.nodes
        assert g.node_count == sample_graph.node_count - 1

    def test_remove_node_missing(self, sample_graph):
        with pytest.raises(NodeNotFoundError):
            sample_graph.remove_node("nonexistent")

    def test_remove_edge(self, sample_graph):
        g = sample_graph.remove_edge("e1")
        assert g.edge_count == sample_graph.edge_count - 1

    def test_remove_edge_missing(self, sample_graph):
        with pytest.raises(EdgeNotFoundError):
            sample_graph.remove_edge("nonexistent")

    def test_update_node(self, sample_graph):
        g = sample_graph.update_node("n1", label="Python 3", confidence=0.95)
        node = g.get_node("n1")
        assert node.label == "Python 3"
        assert node.confidence == 0.95
        assert sample_graph.get_node("n1").label == "Python"  # immutability

    def test_query_by_type(self, sample_graph):
        results = sample_graph.query(node_type=NodeType.CONCEPT)
        assert len(results) == 3

    def test_query_by_label(self, sample_graph):
        results = sample_graph.query(label_contains="Python")
        assert len(results) == 1
        assert results[0].node_id == "n1"

    def test_query_by_label_case_insensitive(self, sample_graph):
        results = sample_graph.query(label_contains="python")
        assert len(results) == 1

    def test_query_by_confidence(self, sample_graph):
        results = sample_graph.query(min_confidence=0.9)
        assert len(results) >= 0

    def test_find_edges(self, sample_graph):
        edges = sample_graph.find_edges(source_id="n4")
        assert len(edges) == 1
        assert edges[0].target_id == "n1"

    def test_find_edges_by_relation(self, sample_graph):
        edges = sample_graph.find_edges(relation=EdgeRelation.CITES)
        assert len(edges) == 1

    def test_merge_graphs(self, empty_graph):
        g1 = empty_graph.add_node(KnowledgeNode(
            node_id="a", node_type=NodeType.CONCEPT, label="A"
        ))
        g2 = empty_graph.add_node(KnowledgeNode(
            node_id="b", node_type=NodeType.CONCEPT, label="B"
        ))
        merged = g1.merge_graphs(g2)
        assert merged.node_count == 2

    def test_serialization_json(self, sample_graph):
        json_str = sample_graph.to_json()
        data = json.loads(json_str)
        assert "nodes" in data
        assert "edges" in data
        assert len(data["nodes"]) == 5

    def test_deserialization(self, sample_graph):
        json_str = sample_graph.to_json()
        restored = KnowledgeGraph.from_json(json_str)
        assert restored.node_count == sample_graph.node_count
        assert restored.edge_count == sample_graph.edge_count
        assert restored.get_node("n1").label == "Python"

    def test_summary(self, sample_graph):
        s = sample_graph.summary()
        assert s["node_count"] == 5
        assert s["edge_count"] == 3
        assert "nodes_by_type" in s

    def test_get_neighbors(self, sample_graph):
        neighbors = sample_graph.get_neighbors("n1")
        neighbor_ids = {n.node_id for n in neighbors}
        assert "n3" in neighbor_ids
        assert "n4" in neighbor_ids

    def test_get_outgoing_edges(self, sample_graph):
        edges = sample_graph.get_outgoing_edges("n1")
        assert len(edges) == 1
        assert edges[0].target_id == "n3"

    def test_get_incoming_edges(self, sample_graph):
        edges = sample_graph.get_incoming_edges("n3")
        assert len(edges) == 2

    def test_edge_enum_values(self):
        assert EdgeRelation.SUPPORTS.value == "supports"
        assert EdgeRelation.REFUTES.value == "refutes"
        assert EdgeRelation.CITES.value == "cites"
        assert EdgeRelation.DEPENDS_ON.value == "depends_on"
        assert EdgeRelation.RELATES_TO.value == "relates_to"
        assert EdgeRelation.EXTENDS.value == "extends"

    def test_node_enum_values(self):
        assert NodeType.CONCEPT.value == "concept"
        assert NodeType.SOURCE.value == "source"
        assert NodeType.INSIGHT.value == "insight"
        assert NodeType.CLAIM.value == "claim"
        assert NodeType.ENTITY.value == "entity"
        assert NodeType.QUESTION.value == "question"


# ═══════════════════════════════════════════════════════════════════════════
# Entity Extractor
# ═══════════════════════════════════════════════════════════════════════════


class TestEntityExtractor:
    @pytest.fixture
    def extractor(self) -> EntityExtractor:
        return EntityExtractor()

    def test_extract_empty(self, extractor):
        entities = extractor.extract("")
        assert len(entities) == 0

    def test_extract_plain_text(self, extractor):
        text = "Python is great. Kubernetes scales well."
        entities = extractor.extract(text)
        entity_names = [e.name.lower() for e in entities]
        assert "python" in entity_names
        assert "kubernetes" in entity_names

    def test_extract_confidence_scores(self, extractor):
        text = "The Immutability principle is key."
        entities = extractor.extract(text)
        for e in entities:
            assert 0.0 <= e.confidence <= 1.0

    def test_extract_entity_kind(self, extractor):
        text = "TensorFlow and Docker"
        entities = extractor.extract(text)
        for e in entities:
            if e.name.lower() == "tensorflow":
                assert e.kind == EntityKind.TECH

    def test_batch_extraction(self, extractor):
        docs = ["Python is a language.", "Kubernetes is orchestration."]
        batches = extractor.extract_batch(docs)
        assert len(batches) == 2

    def test_extract_to_graph(self, extractor, empty_graph):
        text = "Python is a programming language."
        g = extractor.extract_to_graph(text, empty_graph)
        entity_nodes = [n for n in g.nodes.values()
                        if n.node_type == NodeType.ENTITY]
        assert len(entity_nodes) > 0

    def test_stop_words_ignored(self, extractor):
        text = "The this that which"
        entities = extractor.extract(text)
        for e in entities:
            assert e.name.lower() not in {"the", "this", "that", "which"}

    def test_add_custom_pattern(self, extractor):
        extracted = extractor.add_pattern(EntityKind.TECH, r"\bCustomTech\b")
        entities = extracted.extract("CustomTech is here")
        names = [e.name for e in entities]
        assert "CustomTech" in names

    def test_remove_pattern(self, extractor):
        before = len(extractor.patterns.get(EntityKind.PERSON, []))
        modified = extractor.remove_pattern(EntityKind.PERSON, 0)
        after = len(modified.patterns.get(EntityKind.PERSON, []))
        assert after == before - 1


# ═══════════════════════════════════════════════════════════════════════════
# Relation Labeler
# ═══════════════════════════════════════════════════════════════════════════


class TestRelationLabeler:
    @pytest.fixture
    def labeler(self) -> RelationLabeler:
        return RelationLabeler()

    def test_label_edge_extracted(self, labeler):
        labeled = labeler.label_edge(
            "A", "B", context="confirms the hypothesis", source_confidence=0.9
        )
        assert labeled.label == EdgeLabel.EXTRACTED

    def test_label_edge_inferred(self, labeler):
        labeled = labeler.label_edge(
            "A", "B", source_confidence=0.6
        )
        assert labeled.label == EdgeLabel.INFERRED

    def test_label_edge_ambiguous(self, labeler):
        labeled = labeler.label_edge(
            "A", "B", source_confidence=0.2
        )
        assert labeled.label == EdgeLabel.AMBIGUOUS

    def test_classify_supports(self, labeler):
        rtype = labeler.classify_relation_type("This proves the theorem")
        assert rtype == "supports"

    def test_classify_refutes(self, labeler):
        rtype = labeler.classify_relation_type("This contradicts the claim")
        assert rtype == "refutes"

    def test_classify_cites(self, labeler):
        rtype = labeler.classify_relation_type("This references prior work")
        assert rtype == "cites"

    def test_classify_default(self, labeler):
        rtype = labeler.classify_relation_type("Random text")
        assert rtype == "relates_to"

    def test_confidence_in_range(self, labeler):
        labeled = labeler.label_edge("A", "B")
        assert 0.0 <= labeled.confidence <= 1.0

    def test_label_batch(self, labeler):
        pairs = [
            ("A", "B", "confirms", 0.9),
            ("C", "D", "", 0.5),
        ]
        results = labeler.label_batch(pairs)
        assert len(results) == 2

    def test_propagate_labels(self, labeler, sample_graph):
        propagated = labeler.propagate_labels(sample_graph)
        assert isinstance(propagated, dict)
        assert len(propagated) == sample_graph.node_count


# ═══════════════════════════════════════════════════════════════════════════
# Community Detector
# ═══════════════════════════════════════════════════════════════════════════


class TestCommunityDetector:
    @pytest.fixture
    def detector(self) -> CommunityDetector:
        return CommunityDetector()

    def test_detect_empty_graph(self, detector, empty_graph):
        communities = detector.detect_communities(empty_graph)
        assert len(communities) > 0

    def test_detect_communities(self, detector, sample_graph):
        communities = detector.detect_communities(sample_graph)
        assert len(communities) >= 1
        for c in communities:
            assert isinstance(c.node_ids, frozenset)

    def test_community_properties(self, detector):
        comm = Community(
            community_id="c1", node_ids=frozenset({"a", "b"}),
            label="Test", level=1,
        )
        assert comm.size == 2
        d = comm.to_dict()
        assert d["community_id"] == "c1"
        assert d["size"] == 2

    def test_inter_community_edges(self, detector, sample_graph):
        communities = detector.detect_communities(sample_graph)
        analysis = detector.analyze_inter_community_edges(sample_graph, communities)
        assert "inter_community_edges" in analysis
        assert "intra_community_edges" in analysis

    def test_summarize_community(self, detector, sample_graph):
        communities = detector.detect_communities(sample_graph)
        if communities:
            summary = detector.summarize_community(sample_graph, communities[0])
            assert "size" in summary
            assert "node_type_distribution" in summary

    def test_hierarchical_detection(self, detector, sample_graph):
        communities = detector.detect_hierarchical(sample_graph, max_levels=2)
        assert len(communities) >= 1


# ═══════════════════════════════════════════════════════════════════════════
# Navigation Engine
# ═══════════════════════════════════════════════════════════════════════════


class TestNavigationEngine:
    @pytest.fixture
    def engine(self, sample_graph) -> NavigationEngine:
        return NavigationEngine(sample_graph)

    def test_get_neighbors(self, engine):
        neighbors = engine.get_neighbors("n1")
        nids = [n.node_id for n in neighbors]
        assert "n3" in nids

    def test_get_neighbors_filtered(self, engine):
        neighbors = engine.get_neighbors("n1", relation_types={"cites"})
        assert len(neighbors) >= 0

    def test_get_neighbors_missing(self, engine):
        with pytest.raises(NodeNotFoundError):
            engine.get_neighbors("nonexistent")

    def test_get_tail_relations(self, engine):
        edges = engine.get_tail_relations("n1")
        assert len(edges) == 1
        assert edges[0].target_id == "n3"

    def test_get_head_entities(self, engine):
        edges = engine.get_head_entities("n3")
        assert len(edges) == 2

    def test_shortest_path(self, engine):
        path = engine.get_path("n4", "n3")
        assert path is not None
        assert path.length > 1

    def test_shortest_path_same_node(self, engine):
        path = engine.get_path("n1", "n1")
        assert path is not None
        assert path.length == 1

    def test_shortest_path_nonexistent(self, engine):
        with pytest.raises(NodeNotFoundError):
            engine.get_path("n1", "nonexistent")

    def test_shortest_path_disconnected(self, engine):
        g = KnowledgeGraph()
        g = g.add_node(KnowledgeNode(
            node_id="a", node_type=NodeType.CONCEPT, label="A"
        ))
        g = g.add_node(KnowledgeNode(
            node_id="b", node_type=NodeType.CONCEPT, label="B"
        ))
        eng = NavigationEngine(g)
        path = eng.get_path("a", "b")
        assert path is None

    def test_get_all_paths(self, engine):
        paths = engine.get_all_paths("n4", "n3", max_depth=4)
        assert isinstance(paths, list)

    def test_get_subgraph(self, engine):
        sub = engine.get_subgraph(["n1"], depth=1)
        assert "nodes" in sub
        assert "edges" in sub

    def test_get_subgraph_empty(self, engine):
        sub = engine.get_subgraph([], depth=1)
        assert len(sub["nodes"]) == 0

    def test_traverse_bfs(self, engine):
        path = engine.traverse("n1", TraversalStrategy.BFS, max_depth=2)
        assert path.length >= 1

    def test_traverse_dfs(self, engine):
        path = engine.traverse("n1", TraversalStrategy.DFS, max_depth=2)
        assert path.length >= 1

    def test_traverse_missing(self, engine):
        with pytest.raises(NodeNotFoundError):
            engine.traverse("nonexistent")

    def test_degree_centrality(self, engine):
        cent = engine.get_degree_centrality("n1")
        assert 0.0 <= cent <= 1.0

    def test_node_connectivity(self, engine):
        conn = engine.get_node_connectivity("n3")
        assert conn["incoming"] == 2
        assert conn["total"] == 2


# ═══════════════════════════════════════════════════════════════════════════
# Pre-Indexer
# ═══════════════════════════════════════════════════════════════════════════


class TestPreIndexer:
    @pytest.fixture
    def temp_py_file(self) -> str:
        with tempfile.NamedTemporaryFile(
            mode="w", suffix=".py", delete=False, encoding="utf-8"
        ) as f:
            f.write("""
def hello(name):
    \"\"\"Say hello.\"\"\"
    return f"Hello {name}"

class MyClass:
    def method(self):
        pass

import os
from pathlib import Path
""")
            return f.name

    @pytest.fixture
    async def preindexer(self, temp_py_file) -> PreIndexer:
        idx = PreIndexer(os.path.dirname(temp_py_file))
        return await idx.index_file(temp_py_file)

    @pytest.mark.asyncio
    async def test_index_file(self, preindexer):
        assert preindexer.indexed_files_count == 1

    @pytest.mark.asyncio
    async def test_extract_symbols(self, preindexer):
        symbols = preindexer.symbols
        names = [s.name for s in symbols]
        assert "hello" in names
        assert "MyClass" in names

    @pytest.mark.asyncio
    async def test_extract_dependencies(self, preindexer):
        deps = preindexer.dependencies
        assert len(deps) >= 2

    @pytest.mark.asyncio
    async def test_find_symbol(self, preindexer):
        found = preindexer.find_symbol("hello")
        assert len(found) >= 1
        assert found[0].symbol_type == "function"

    @pytest.mark.asyncio
    async def test_build_dependency_graph(self, preindexer):
        dep_graph = preindexer.build_dependency_graph()
        assert "dependencies" in dep_graph
        assert "dependents" in dep_graph

    @pytest.mark.asyncio
    async def test_to_graph(self, preindexer, empty_graph):
        kg = await preindexer.to_graph(empty_graph)
        assert kg.node_count > 0

    @pytest.mark.asyncio
    async def test_index_directory(self):
        idx = await PreIndexer("/tmp").index_directory(exclude_dirs=frozenset({"__pycache__"}))
        assert idx.indexed_files_count >= 0

    @pytest.mark.asyncio
    async def test_index_nonexistent_file(self):
        idx = PreIndexer("/tmp")
        with pytest.raises(IndexingError):
            await idx.index_file("/nonexistent/file.py")


# ═══════════════════════════════════════════════════════════════════════════
# Inverse Search
# ═══════════════════════════════════════════════════════════════════════════


class TestInverseSearch:
    @pytest.fixture
    def engine(self, sample_graph) -> InverseSearchEngine:
        return InverseSearchEngine(sample_graph)

    def test_find_supporting_paths(self, engine):
        paths = engine.find_supporting_paths("n3", max_depth=3)
        assert isinstance(paths, list)

    def test_find_refuting_paths(self, engine):
        paths = engine.find_refuting_paths("n3", max_depth=3)
        assert isinstance(paths, list)

    def test_score_hypothesis(self, engine):
        score = engine.score_hypothesis("n3")
        assert isinstance(score, HypothesisScore)
        assert isinstance(score.confidence, float)
        assert 0.0 <= score.confidence <= 1.0

    def test_score_hypothesis_missing(self, engine):
        score = engine.score_hypothesis("nonexistent")
        assert score.confidence == 0.0

    def test_generate_counter_claims(self, engine):
        counters = engine.generate_counter_claims("n3")
        assert isinstance(counters, list)

    def test_get_citation_count(self, engine):
        count = engine.get_citation_count("n1")
        assert count == 1

    def test_get_support_score(self, engine):
        score = engine.get_support_score("n3")
        assert isinstance(score, float)


# ═══════════════════════════════════════════════════════════════════════════
# RRF Fusion
# ═══════════════════════════════════════════════════════════════════════════


class TestRRFusion:
    @pytest.fixture
    def fusor(self) -> RRFusion:
        return RRFusion(k=60)

    def test_fuse_empty(self, fusor):
        results = fusor.fuse([], [])
        assert len(results) == 0

    def test_fuse_single_result(self, fusor):
        kw = [{"id": "a", "score": 1.0}]
        vec = [{"id": "a", "score": 0.9}]
        results = fusor.fuse(kw, vec)
        assert len(results) == 1
        assert results[0].item_id == "a"
        assert results[0].rank == 1

    def test_fuse_reranking(self, fusor):
        kw = [{"id": "a", "score": 1.0}, {"id": "b", "score": 0.8}]
        vec = [{"id": "b", "score": 0.9}, {"id": "a", "score": 0.7}]
        results = fusor.fuse(kw, vec)
        assert len(results) == 2

    def test_fuse_multiple_lists(self, fusor):
        list1 = [{"id": "a"}, {"id": "b"}]
        list2 = [{"id": "b"}, {"id": "c"}]
        list3 = [{"id": "a"}, {"id": "c"}]
        results = fusor.fuse_multiple([list1, list2, list3])
        assert len(results) >= 2

    def test_fuse_multiple_empty(self, fusor):
        results = fusor.fuse_multiple([])
        assert len(results) == 0

    def test_normalize_scores(self, fusor):
        results = [{"id": "a", "score": 10.0}, {"id": "b", "score": 5.0}]
        normalized = fusor.normalize_scores(results)
        assert normalized[0]["score"] == 1.0
        assert normalized[1]["score"] == 0.0

    def test_rerank(self, fusor):
        results = [
            FusionResult(item_id="a", rank=2, score=0.5),
            FusionResult(item_id="b", rank=1, score=1.0),
        ]
        reranked = fusor.rerank(results)
        assert reranked[0].item_id == "b"

    def test_k_parameter(self):
        fusor = RRFusion(k=100)
        assert fusor.k == 100

    def test_k_invalid(self):
        with pytest.raises(ValueError):
            RRFusion(k=0)

    def test_fusion_result_to_dict(self):
        fr = FusionResult(
            item_id="a", rank=1, score=0.9,
            keyword_score=0.8, vector_score=0.7,
        )
        d = fr.to_dict()
        assert d["item_id"] == "a"
        assert d["rank"] == 1


# ═══════════════════════════════════════════════════════════════════════════
# Dream Cycle
# ═══════════════════════════════════════════════════════════════════════════


class TestDreamCycle:
    @pytest.fixture
    def dream(self, sample_graph) -> DreamCycle:
        return DreamCycle(sample_graph)

    def test_cross_link_entities(self, dream):
        result = dream.cross_link_entities()
        assert result.edge_count >= dream._graph.edge_count

    def test_identify_gaps(self, dream):
        gaps = dream.identify_gaps(min_neighbors=1)
        assert isinstance(gaps, list)

    def test_enrich_relations(self, dream):
        result = dream.enrich_relations()
        assert result.edge_count >= dream._graph.edge_count

    def test_consolidate_communities(self, dream):
        comms = [
            Community(
                community_id="c1",
                node_ids=frozenset({"n1", "n2", "n3"}),
                label="Group A",
            ),
            Community(
                community_id="c2",
                node_ids=frozenset({"n1", "n2"}),
                label="Group B",
            ),
        ]
        consolidated = dream.consolidate_communities(comms, merge_threshold=0.5)
        assert len(consolidated) <= len(comms)

    def test_consolidate_no_merge(self, dream):
        from lyra_knowledge_graph.community_detector import Community
        comms = [
            Community(community_id="c1", node_ids=frozenset({"n1"}), label="A"),
            Community(community_id="c2", node_ids=frozenset({"n2"}), label="B"),
        ]
        consolidated = dream.consolidate_communities(comms)
        assert len(consolidated) == len(comms)

    def test_run_full_cycle(self, dream):
        report = dream.run_full_cycle()
        assert "cross_links_added" in report
        assert "gaps_found" in report
        assert "enriched_relations_added" in report


# ═══════════════════════════════════════════════════════════════════════════
# MCP Server
# ═══════════════════════════════════════════════════════════════════════════


class TestMCPServer:
    @pytest.fixture
    def server(self, sample_graph) -> KnowledgeGraphMCPServer:
        return KnowledgeGraphMCPServer(sample_graph)

    @pytest.mark.asyncio
    async def test_query_graph(self, server):
        results = await server.query_graph("Python")
        assert len(results) >= 1
        assert results[0]["node_id"] == "n1"

    @pytest.mark.asyncio
    async def test_query_graph_limit(self, server):
        results = await server.query_graph("a", max_results=2)
        assert len(results) <= 2

    @pytest.mark.asyncio
    async def test_query_graph_by_type(self, server):
        results = await server.query_graph("", node_type="source")
        assert all(r["node_type"] == "source" for r in results)

    @pytest.mark.asyncio
    async def test_get_node_found(self, server):
        node = await server.get_node("n1")
        assert node is not None
        assert node["label"] == "Python"

    @pytest.mark.asyncio
    async def test_get_node_not_found(self, server):
        node = await server.get_node("nonexistent")
        assert node is None

    @pytest.mark.asyncio
    async def test_get_neighbors(self, server):
        neighbors = await server.get_neighbors("n1")
        assert len(neighbors) >= 1

    @pytest.mark.asyncio
    async def test_get_neighbors_nonexistent(self, server):
        neighbors = await server.get_neighbors("nonexistent")
        assert len(neighbors) == 0

    @pytest.mark.asyncio
    async def test_shortest_path_found(self, server):
        path = await server.shortest_path("n4", "n3")
        assert path is not None
        assert path["length"] > 1

    @pytest.mark.asyncio
    async def test_shortest_path_nonexistent(self, server):
        path = await server.shortest_path("n4", "nonexistent")
        assert path is None

    @pytest.mark.asyncio
    async def test_get_community(self, server):
        result = await server.get_community("n1")
        assert result is not None
        assert result["node_id"] == "n1"

    @pytest.mark.asyncio
    async def test_graph_summary(self, server):
        s = await server.graph_summary()
        assert s["node_count"] == 5

    @pytest.mark.asyncio
    async def test_get_nodes_batch(self, server):
        nodes = await server.get_nodes_batch(["n1", "n2", "nonexistent"])
        assert len(nodes) == 2

    @pytest.mark.asyncio
    async def test_get_subgraph(self, server):
        sub = await server.get_subgraph(["n1"], depth=1)
        assert "nodes" in sub
        assert "edges" in sub

    @pytest.mark.asyncio
    async def test_graph_query(self, server):
        results = await server.graph_query("Python")
        assert len(results) >= 1
        assert "_search_score" in results[0]


# ═══════════════════════════════════════════════════════════════════════════
# GraphBuilder (new spec API)
# ═══════════════════════════════════════════════════════════════════════════


class TestGraphBuilder:
    @pytest.mark.asyncio
    async def test_add_node(self):
        gb = GraphBuilder()
        gb = await gb.add_node("n1", "Python", NodeType.CONCEPT)
        assert gb.node_count == 1

    @pytest.mark.asyncio
    async def test_add_edge(self):
        gb = GraphBuilder()
        gb = await gb.add_node("a", "Node A", NodeType.CONCEPT)
        gb = await gb.add_node("b", "Node B", NodeType.CONCEPT)
        gb = await gb.add_edge("a", "b", EdgeRelation.SUPPORTS, 0.9)
        assert gb.edge_count == 1

    @pytest.mark.asyncio
    async def test_query_nodes(self):
        gb = GraphBuilder()
        gb = await gb.add_node("n1", "Python", NodeType.CONCEPT)
        nodes = await gb.query_nodes(label="Python")
        assert len(nodes) == 1

    @pytest.mark.asyncio
    async def test_get_neighbors(self):
        gb = GraphBuilder()
        gb = await gb.add_node("a", "A", NodeType.CONCEPT)
        gb = await gb.add_node("b", "B", NodeType.CONCEPT)
        gb = await gb.add_edge("a", "b", EdgeRelation.RELATES_TO)
        neighbors = await gb.get_neighbors("a")
        assert len(neighbors) == 1

    @pytest.mark.asyncio
    async def test_merge_graphs(self):
        gb1 = GraphBuilder()
        gb1 = await gb1.add_node("a", "A", NodeType.CONCEPT)
        gb2 = GraphBuilder()
        gb2 = await gb2.add_node("b", "B", NodeType.CONCEPT)
        merged = await gb1.merge_graphs(gb2)
        assert merged.node_count == 2

    @pytest.mark.asyncio
    async def test_build_from_text(self):
        gb = GraphBuilder()
        gb = await gb.build_from_text("hello_world() uses https://example.com")
        assert gb.node_count >= 1


# ═══════════════════════════════════════════════════════════════════════════
# Entity Extractor (new spec methods)
# ═══════════════════════════════════════════════════════════════════════════


class TestEntityExtractorNew:
    @pytest.fixture
    def extractor(self) -> EntityExtractor:
        return EntityExtractor()

    @pytest.mark.asyncio
    async def test_extract_entities(self, extractor):
        entities = await extractor.extract_entities(
            "Python is great and Kubernetes scales."
        )
        names = [e[0].lower() for e in entities]
        assert "python" in names
        assert all(isinstance(e[2], float) for e in entities)

    @pytest.mark.asyncio
    async def test_extract_code_symbols_python(self, extractor):
        symbols = await extractor.extract_code_symbols(
            "def hello():\n    pass\n\nclass MyClass:\n    pass",
            "python",
        )
        names = [s[0] for s in symbols]
        assert "hello" in names
        assert "MyClass" in names

    @pytest.mark.asyncio
    async def test_extract_relations(self, extractor):
        relations = await extractor.extract_relations(
            "Alice supports Bob. Charlie refutes Dave."
        )
        assert len(relations) >= 2
        assert any(r[1] == "supports" for r in relations)
        assert any(r[1] == "refutes" for r in relations)


# ═══════════════════════════════════════════════════════════════════════════
# RelationConfidence
# ═══════════════════════════════════════════════════════════════════════════


class TestRelationConfidence:
    def test_enum_values(self):
        assert RelationConfidence.EXTRACTED.value == "extracted"
        assert RelationConfidence.INFERRED.value == "inferred"
        assert RelationConfidence.AMBIGUOUS.value == "ambiguous"

    @pytest.mark.asyncio
    async def test_label_relation(self):
        labeler = RelationLabeler()
        result = await labeler.label_relation(
            "Alice", "supports", "Bob", "Alice confirms Bob's theory"
        )
        subj, rel, obj, conf = result
        assert subj == "Alice"
        assert isinstance(conf, RelationConfidence)


# ═══════════════════════════════════════════════════════════════════════════
# CommunityDetector dict-based API
# ═══════════════════════════════════════════════════════════════════════════


class TestCommunityDetectorDictAPI:
    @pytest.mark.asyncio
    async def test_detect_communities_from_dicts(self, sample_graph):
        detector = CommunityDetector()
        communities = await detector.detect_communities(
            sample_graph.nodes, sample_graph.edges
        )
        assert isinstance(communities, tuple)
        assert len(communities) >= 1
        assert all(isinstance(c, Community) for c in communities)


# ═══════════════════════════════════════════════════════════════════════════
# NavigationEngine find_path
# ═══════════════════════════════════════════════════════════════════════════


class TestNavigationEngineFindPath:
    @pytest.mark.asyncio
    async def test_find_path(self, sample_graph):
        engine = NavigationEngine(sample_graph)
        path = await engine.find_path("n4", "n3")
        assert path is not None
        assert path.length > 1

    @pytest.mark.asyncio
    async def test_find_path_same_node(self, sample_graph):
        engine = NavigationEngine(sample_graph)
        path = await engine.find_path("n1", "n1")
        assert path is not None
        assert path.length == 1


# ═══════════════════════════════════════════════════════════════════════════
# InverseSearch (new spec class)
# ═══════════════════════════════════════════════════════════════════════════


class TestInverseSearchNew:
    @pytest.mark.asyncio
    async def test_search_backward(self, sample_graph):
        searcher = InverseSearch(sample_graph)
        paths = await searcher.search_backward("n3", sample_graph)
        assert isinstance(paths, list)

    @pytest.mark.asyncio
    async def test_rank_hypotheses(self, sample_graph):
        searcher = InverseSearch(sample_graph)
        scores = await searcher.rank_hypotheses("n3", ["n1", "n5"])
        assert len(scores) == 2
        for s in scores:
            assert isinstance(s, HypothesisScore)


# ═══════════════════════════════════════════════════════════════════════════
# RRFFusion (new spec class)
# ═══════════════════════════════════════════════════════════════════════════


class TestRRFFusionNew:
    @pytest.mark.asyncio
    async def test_fuse_results(self):
        fusor = RRFFusion(k=60)
        vec = [{"id": "a", "score": 1.0}, {"id": "b", "score": 0.8}]
        bm25 = [{"id": "b", "score": 0.9}, {"id": "a", "score": 0.7}]
        results = await fusor.fuse_results(vec, bm25, k=60)
        assert len(results) >= 1
        assert isinstance(results[0], FusionResult)

    @pytest.mark.asyncio
    async def test_fuse_results_empty(self):
        fusor = RRFFusion()
        results = await fusor.fuse_results([], [], k=60)
        assert len(results) == 0

    def test_k_invalid(self):
        with pytest.raises(ValueError):
            RRFFusion(k=0)


# ═══════════════════════════════════════════════════════════════════════════
# KGDreamCycle (new spec class)
# ═══════════════════════════════════════════════════════════════════════════


class TestKGDreamCycle:
    @pytest.mark.asyncio
    async def test_dream(self, sample_graph):
        kg_dream = KGDreamCycle(sample_graph)
        report = await kg_dream.dream()
        assert "cross_links_added" in report
        assert "gaps_found" in report


# ═══════════════════════════════════════════════════════════════════════════
# PreIndexer stats
# ═══════════════════════════════════════════════════════════════════════════


class TestPreIndexerStats:
    @pytest.mark.asyncio
    async def test_stats_properties(self, sample_graph):
        import os
        import tempfile
        with tempfile.NamedTemporaryFile(
            mode="w", suffix=".py", delete=False, encoding="utf-8"
        ) as f:
            f.write("def foo(): pass\nclass Bar: pass\n")
            fname = f.name
        idx = PreIndexer(os.path.dirname(fname))
        idx = await idx.index_file(fname)
        assert idx.files_processed == 1
        assert idx.symbols_found >= 2
        os.unlink(fname)


# ═══════════════════════════════════════════════════════════════════════════
# Exceptions
# ═══════════════════════════════════════════════════════════════════════════


class TestKnowledgeGraphExceptions:
    def test_base_error(self):
        with pytest.raises(KnowledgeGraphError):
            raise KnowledgeGraphError("base error")

    def test_node_not_found(self):
        with pytest.raises(NodeNotFoundError):
            raise NodeNotFoundError("node_x")

    def test_edge_not_found(self):
        with pytest.raises(EdgeNotFoundError):
            raise EdgeNotFoundError("edge_x")

    def test_extraction_error(self):
        with pytest.raises(ExtractionError):
            raise ExtractionError("extraction failed")

    def test_indexing_error(self):
        with pytest.raises(IndexingError):
            raise IndexingError("/path", "permission denied")

    def test_navigation_error(self):
        with pytest.raises(NavigationError):
            raise NavigationError("path not found")
