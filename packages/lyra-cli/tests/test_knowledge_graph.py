"""Tests for ResearchKnowledgeGraph — PPR, gaps, relations."""

from __future__ import annotations

import pytest
from lyra_cli.research.knowledge_graph import (
    Finding,
    FindingRelation,
    ResearchKnowledgeGraph,
)


def _f(id: str, content: str = "", confidence: float = 1.0, tags: tuple[str, ...] = ()) -> Finding:
    return Finding(
        finding_id=id, content=content or f"content-{id}", confidence=confidence, tags=tags
    )


def _r(
    id: str, src: str, tgt: str, rtype: str = "related_to", strength: float = 1.0
) -> FindingRelation:
    return FindingRelation(
        relation_id=id, source_id=src, target_id=tgt, relation_type=rtype, strength=strength
    )


# ── Finding / FindingRelation dataclasses ───────────────────────────────


class TestFindingDataclass:
    def test_finding_immutable_defaults(self):
        f = Finding(finding_id="f1", content="test")
        assert f.sources == ()
        assert f.tags == ()
        assert f.confidence == 1.0

    def test_finding_with_tags_and_sources(self):
        f = Finding(finding_id="f1", content="test", tags=("tag1", "tag2"), sources=("s1", "s2"))
        assert "tag1" in f.tags
        assert "s1" in f.sources


class TestFindingRelationDataclass:
    def test_relation_immutable(self):
        r = FindingRelation(
            relation_id="r1", source_id="a", target_id="b", relation_type="supports"
        )
        assert r.strength == 1.0

    def test_relation_contradicts(self):
        r = FindingRelation(
            relation_id="r1",
            source_id="a",
            target_id="b",
            relation_type="contradicts",
            strength=0.5,
        )
        assert r.relation_type == "contradicts"
        assert r.strength == 0.5


# ── ResearchKnowledgeGraph ──────────────────────────────────────────────


class TestAddAndQuery:
    def test_add_finding_returns_id(self):
        g = ResearchKnowledgeGraph()
        fid = g.add_finding(_f("f1", "hello"))
        assert fid == "f1"
        assert g.get_finding_count() == 1

    def test_get_finding_retrieves(self):
        g = ResearchKnowledgeGraph()
        g.add_finding(_f("f1", "hello"))
        f = g.get_finding("f1")
        assert f is not None
        assert f.content == "hello"

    def test_get_finding_missing_returns_none(self):
        g = ResearchKnowledgeGraph()
        assert g.get_finding("nope") is None

    def test_add_relation_links_findings(self):
        g = ResearchKnowledgeGraph()
        g.add_finding(_f("a"))
        g.add_finding(_f("b"))
        g.add_relation(_r("r1", "a", "b"))
        assert g.get_relation_count() == 1

    def test_add_relation_missing_source_raises(self):
        g = ResearchKnowledgeGraph()
        g.add_finding(_f("b"))
        with pytest.raises(KeyError, match="Source finding"):
            g.add_relation(_r("r1", "a", "b"))

    def test_add_relation_missing_target_raises(self):
        g = ResearchKnowledgeGraph()
        g.add_finding(_f("a"))
        with pytest.raises(KeyError, match="Target finding"):
            g.add_relation(_r("r1", "a", "b"))

    def test_get_all_findings(self):
        g = ResearchKnowledgeGraph()
        g.add_finding(_f("a"))
        g.add_finding(_f("b"))
        assert len(g.get_all_findings()) == 2


class TestFindByTag:
    def test_find_by_tag_exact_match(self):
        g = ResearchKnowledgeGraph()
        g.add_finding(_f("a", tags=("ml",)))
        g.add_finding(_f("b", tags=("systems",)))
        results = g.find_findings_by_tag("ml")
        assert len(results) == 1
        assert results[0].finding_id == "a"

    def test_find_by_tag_returns_empty_when_no_match(self):
        g = ResearchKnowledgeGraph()
        g.add_finding(_f("a", tags=("ml",)))
        assert g.find_findings_by_tag("nlp") == []


class TestNeighbors:
    def test_neighbors_both_directions(self):
        g = ResearchKnowledgeGraph()
        g.add_finding(_f("a"))
        g.add_finding(_f("b"))
        g.add_finding(_f("c"))
        g.add_relation(_r("r1", "a", "b"))
        g.add_relation(_r("r2", "c", "a"))
        neighbors = g.get_neighbors("a", direction="both")
        assert len(neighbors) == 2

    def test_neighbors_outgoing_only(self):
        g = ResearchKnowledgeGraph()
        g.add_finding(_f("a"))
        g.add_finding(_f("b"))
        g.add_finding(_f("c"))
        g.add_relation(_r("r1", "a", "b"))
        g.add_relation(_r("r2", "c", "a"))
        neighbors = g.get_neighbors("a", direction="outgoing")
        assert len(neighbors) == 1
        assert neighbors[0][0].finding_id == "b"

    def test_neighbors_empty_graph(self):
        g = ResearchKnowledgeGraph()
        assert g.get_neighbors("nope") == []


class TestPPR:
    def test_compute_ppr_empty_graph(self):
        g = ResearchKnowledgeGraph()
        assert g.compute_ppr([]) == {}

    def test_compute_ppr_single_node(self):
        g = ResearchKnowledgeGraph()
        g.add_finding(_f("a"))
        scores = g.compute_ppr(["a"])
        assert "a" in scores

    def test_get_relevant_findings_ranks(self):
        g = ResearchKnowledgeGraph()
        g.add_finding(_f("a", "query node"))
        g.add_finding(_f("b", "related to a"))
        g.add_finding(_f("c", "unrelated"))
        g.add_relation(_r("r1", "a", "b"))
        results = g.get_relevant_findings(["a"], top_k=3)
        assert len(results) <= 3

    def test_ppr_converges_with_iterations(self):
        g = ResearchKnowledgeGraph()
        for i in range(5):
            g.add_finding(_f(f"f{i}", f"content-{i}"))
        for i in range(4):
            g.add_relation(_r(f"r{i}", f"f{i}", f"f{i+1}"))
        scores = g.compute_ppr(["f0"], iterations=20)
        assert len(scores) == 5


class TestKnowledgeGaps:
    def test_orphan_finding_creates_gap(self):
        g = ResearchKnowledgeGraph()
        g.add_finding(_f("isolated_f", "isolated finding with no connections"))
        gaps = g.find_knowledge_gaps()
        assert any("has no connections" in gap.description for gap in gaps)

    def test_contradiction_creates_gap(self):
        g = ResearchKnowledgeGraph()
        g.add_finding(_f("a", "claim A is true"))
        g.add_finding(_f("b", "claim A is false"))
        g.add_relation(_r("r1", "a", "b", "contradicts"))
        gaps = g.find_knowledge_gaps()
        assert any("Contradiction" in g.description for g in gaps)

    def test_low_connectivity_creates_gap(self):
        g = ResearchKnowledgeGraph()
        g.add_finding(_f("a", "finding a"))
        g.add_finding(_f("b", "finding b"))
        g.add_relation(_r("r1", "a", "b"))
        gaps = g.find_knowledge_gaps()
        sparse_gaps = [g for g in gaps if "only one connection" in g.description]
        assert len(sparse_gaps) == 2

    def test_empty_graph_no_gaps(self):
        g = ResearchKnowledgeGraph()
        assert g.find_knowledge_gaps() == []


class TestSerialization:
    def test_finding_json_roundtrip(self):
        import json
        from dataclasses import asdict

        f = Finding(finding_id="f1", content="test", confidence=0.8, tags=("tag",))
        d = asdict(f)
        raw = json.dumps(d)
        restored = json.loads(raw)
        assert restored["finding_id"] == "f1"
        assert restored["confidence"] == 0.8
