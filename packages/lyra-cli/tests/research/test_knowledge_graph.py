"""Tests for ResearchKnowledgeGraph."""

import pytest

from lyra_cli.research.knowledge_graph import (
    Finding,
    FindingRelation,
    ResearchKnowledgeGraph,
    KnowledgeGap,
)


class TestResearchKnowledgeGraph:
    """Test suite for ResearchKnowledgeGraph."""

    def test_add_and_get_finding(self):
        """Adding a finding and retrieving it by ID works."""
        kg = ResearchKnowledgeGraph()
        finding = Finding(
            finding_id="f_001",
            content="Transformers are effective for NLP",
            confidence=0.9,
            sources=("src_001",),
            tags=("nlp", "transformer"),
        )
        kg.add_finding(finding)

        retrieved = kg.get_finding("f_001")
        assert retrieved is not None
        assert retrieved.content == "Transformers are effective for NLP"
        assert "nlp" in retrieved.tags

    def test_add_relation(self):
        """Adding a relation between two findings works."""
        kg = ResearchKnowledgeGraph()
        kg.add_finding(Finding(finding_id="f_1", content="A"))
        kg.add_finding(Finding(finding_id="f_2", content="B"))

        rel = FindingRelation(
            relation_id="r_001",
            source_id="f_1",
            target_id="f_2",
            relation_type="supports",
            strength=0.8,
        )
        kg.add_relation(rel)

        assert kg.get_relation_count() == 1

    def test_add_relation_missing_source_raises(self):
        """Adding a relation with a non-existent source raises KeyError."""
        kg = ResearchKnowledgeGraph()
        kg.add_finding(Finding(finding_id="f_2", content="B"))

        rel = FindingRelation(
            relation_id="r_001",
            source_id="f_missing",
            target_id="f_2",
            relation_type="supports",
        )
        with pytest.raises(KeyError, match="f_missing"):
            kg.add_relation(rel)

    def test_add_relation_missing_target_raises(self):
        """Adding a relation with a non-existent target raises KeyError."""
        kg = ResearchKnowledgeGraph()
        kg.add_finding(Finding(finding_id="f_1", content="A"))

        rel = FindingRelation(
            relation_id="r_001",
            source_id="f_1",
            target_id="f_missing",
            relation_type="supports",
        )
        with pytest.raises(KeyError, match="f_missing"):
            kg.add_relation(rel)

    def test_get_neighbors(self):
        """get_neighbors returns connected findings."""
        kg = ResearchKnowledgeGraph()
        f_a = Finding(finding_id="f_a", content="A")
        f_b = Finding(finding_id="f_b", content="B")
        f_c = Finding(finding_id="f_c", content="C")
        kg.add_finding(f_a)
        kg.add_finding(f_b)
        kg.add_finding(f_c)
        kg.add_relation(FindingRelation("r_ab", "f_a", "f_b", "supports"))
        kg.add_relation(FindingRelation("r_ac", "f_a", "f_c", "relates_to"))

        neighbors = kg.get_neighbors("f_a")
        neighbor_ids = {n.finding_id for n, _ in neighbors}
        assert neighbor_ids == {"f_b", "f_c"}

    def test_get_neighbors_outgoing_only(self):
        """get_neighbors respects direction filter."""
        kg = ResearchKnowledgeGraph()
        kg.add_finding(Finding(finding_id="f_a", content="A"))
        kg.add_finding(Finding(finding_id="f_b", content="B"))
        kg.add_finding(Finding(finding_id="f_c", content="C"))
        kg.add_relation(FindingRelation("r_ab", "f_a", "f_b", "supports"))
        kg.add_relation(FindingRelation("r_ca", "f_c", "f_a", "supports"))

        outgoing = kg.get_neighbors("f_a", direction="outgoing")
        outgoing_ids = {n.finding_id for n, _ in outgoing}
        assert outgoing_ids == {"f_b"}

        incoming = kg.get_neighbors("f_a", direction="incoming")
        incoming_ids = {n.finding_id for n, _ in incoming}
        assert incoming_ids == {"f_c"}

    def test_find_findings_by_tag(self):
        """find_findings_by_tag returns matching findings."""
        kg = ResearchKnowledgeGraph()
        kg.add_finding(Finding(
            finding_id="f_1", content="A",
            tags=("nlp", "transformer"),
        ))
        kg.add_finding(Finding(
            finding_id="f_2", content="B",
            tags=("nlp", "attention"),
        ))
        kg.add_finding(Finding(
            finding_id="f_3", content="C",
            tags=("vision", "cnn"),
        ))

        nlp_findings = kg.find_findings_by_tag("nlp")
        assert len(nlp_findings) == 2

        cnn_findings = kg.find_findings_by_tag("cnn")
        assert len(cnn_findings) == 1
        assert cnn_findings[0].finding_id == "f_3"

    def test_ppr_scores(self):
        """PPR ranks query findings higher and propagates to neighbors."""
        kg = ResearchKnowledgeGraph()
        kg.add_finding(Finding(finding_id="f_q", content="Query topic"))
        kg.add_finding(Finding(finding_id="f_a", content="Related A"))
        kg.add_finding(Finding(finding_id="f_b", content="Related B"))
        kg.add_finding(Finding(finding_id="f_c", content="Unrelated C"))
        kg.add_relation(FindingRelation("r_qa", "f_q", "f_a", "supports", 0.9))
        kg.add_relation(FindingRelation("r_qb", "f_q", "f_b", "supports", 0.7))

        ppr = kg.compute_ppr(query_finding_ids=["f_q"])
        assert "f_q" in ppr
        # Query node should have highest score
        assert ppr["f_q"] >= ppr.get("f_a", 0)
        assert ppr["f_q"] >= ppr.get("f_c", 0)

    def test_get_relevant_findings(self):
        """get_relevant_findings returns top-k results excluding query."""
        kg = ResearchKnowledgeGraph()
        kg.add_finding(Finding(finding_id="f_q", content="Query"))
        kg.add_finding(Finding(finding_id="f_a", content="Related A"))
        kg.add_finding(Finding(finding_id="f_b", content="Related B"))
        kg.add_relation(FindingRelation("r_qa", "f_q", "f_a", "supports"))
        kg.add_relation(FindingRelation("r_qb", "f_q", "f_b", "supports"))

        relevant = kg.get_relevant_findings(
            query_finding_ids=["f_q"], top_k=5
        )
        result_ids = {f.finding_id for f, _ in relevant}
        assert "f_q" not in result_ids
        assert "f_a" in result_ids
        assert "f_b" in result_ids

    def test_find_knowledge_gaps_orphans(self):
        """Orphan findings (no relations) are detected as gaps."""
        kg = ResearchKnowledgeGraph()
        kg.add_finding(Finding(finding_id="f_orphan", content="Orphan finding"))
        kg.add_finding(Finding(finding_id="f_connected", content="Connected"))
        kg.add_finding(Finding(finding_id="f_other", content="Other"))
        kg.add_relation(FindingRelation(
            "r_conn", "f_connected", "f_other", "supports",
        ))

        gaps = kg.find_knowledge_gaps()

        orphan_gaps = [g for g in gaps if "orphan" in g.gap_id]
        assert len(orphan_gaps) >= 1
        assert any("Orphan finding" in g.description for g in orphan_gaps)

    def test_find_knowledge_gaps_contradictions(self):
        """Contradictory relations are reported as knowledge gaps."""
        kg = ResearchKnowledgeGraph()
        kg.add_finding(Finding(finding_id="f_a", content="Claim A"))
        kg.add_finding(Finding(finding_id="f_b", content="Claim B"))
        kg.add_relation(FindingRelation(
            "r_contra", "f_a", "f_b", "contradicts",
        ))

        gaps = kg.find_knowledge_gaps()
        contra_gaps = [g for g in gaps if "contradiction" in g.gap_id]
        assert len(contra_gaps) >= 1

    def test_empty_graph(self):
        """Empty graph returns empty results."""
        kg = ResearchKnowledgeGraph()
        assert kg.get_finding_count() == 0
        assert kg.get_relation_count() == 0
        assert kg.compute_ppr(["f_nonexistent"]) == {}
        assert kg.find_knowledge_gaps() == []
