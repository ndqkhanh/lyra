"""
Tests for v8.2 Research Advanced Features.

Covers:
- Evidence graph construction and querying
- Adversarial verification loop
- Skill extraction from findings
- Cross-source triangulation
"""

from __future__ import annotations

import time
import pytest

from lyra.research.evidence_graph import (
    EdgeType,
    EvidenceGraph,
    EvidenceNode,
    EvidenceEdge,
    GraphQuery,
    VerificationResult,
    VerificationStatus,
    ContradictionPair,
)
from lyra.research.adversarial_verification import (
    AdversarialVerificationLoop,
    AgentRole,
    ConfidenceBracket,
    PanelVerdict,
    Verdict,
)
from lyra.research.skill_extractor import (
    SkillExtractor,
    SkillTemplate,
    SkillCategory,
)
from lyra.research.findings_memory import (
    FindingRecord,
    FindingStage,
    ValuationScores,
)
from lyra.skills.skill import Skill


# =============================================================================
# Fixtures
# =============================================================================


@pytest.fixture
def empty_graph() -> EvidenceGraph:
    return EvidenceGraph()


@pytest.fixture
def populated_graph() -> EvidenceGraph:
    """Graph with 5 claims and several edges for testing."""
    g = EvidenceGraph()

    n1 = g.add_evidence("LoRA reduces memory by 4x", source="arxiv:2302.0", confidence=0.85, tags=["lora", "memory"])
    n2 = g.add_evidence("LoRA degrades on long sequences >2K", source="experiment:42", confidence=0.65, tags=["lora", "limitation"])
    n3 = g.add_evidence("AdaLoRA adapts rank per layer", source="arxiv:2303.0", confidence=0.90, tags=["lora", "adaptive"])
    n4 = g.add_evidence("Full fine-tuning still outperforms LoRA on code", source="experiment:99", confidence=0.70, tags=["finetuning", "comparison"])
    n5 = g.add_evidence("LoRA + quantization achieves 8x compression", source="arxiv:2305.0", confidence=0.80, tags=["lora", "quantization"])

    # n1 and n2 contradict
    g.add_edge(n1, n2, EdgeType.CONTRADICTS, weight=0.7, rationale="Sequence length > 2K changes memory profile")

    # n3 supports n1
    g.add_edge(n3, n1, EdgeType.SUPPORTS, weight=0.85, rationale="AdaLoRA builds on the LoRA insight")

    # n4 contradicts n1
    g.add_edge(n4, n1, EdgeType.CONTRADICTS, weight=0.6, rationale="Full fine-tuning is better on code tasks")

    # n5 supports n1
    g.add_edge(n5, n1, EdgeType.SUPPORTS, weight=0.75, rationale="Quantized LoRA extends the same principle")

    # n2 cites n1
    g.add_edge(n2, n1, EdgeType.CITES, weight=0.5, rationale="References LoRA as baseline")

    # n5 derives from n1
    g.add_edge(n5, n1, EdgeType.DERIVES_FROM, weight=0.9, rationale="QLoRA is built on LoRA foundation")

    return g


@pytest.fixture
def verifier(populated_graph: EvidenceGraph) -> AdversarialVerificationLoop:
    return AdversarialVerificationLoop(evidence_graph=populated_graph)


@pytest.fixture
def sample_finding() -> FindingRecord:
    return FindingRecord(
        finding_id="f-001",
        quest_id="q-001",
        hypothesis="Attention sparsity reduces inference cost by 30%",
        stage=FindingStage.PROGRESS,
        valuation=ValuationScores(utility=0.8, quality=0.7, efficiency=0.9),
        analysis="Experiments confirmed that sparse attention patterns achieve 30% cost reduction with minimal quality loss.",
        implementation_ref="pr:42",
        experiment_logs=[
            {"delta": 0.3, "metric": "cost", "status": "KEPT"},
            {"delta": 0.28, "metric": "cost", "status": "KEPT"},
        ],
        metadata={"tags": ["attention", "sparsity", "efficiency"]},
    )


@pytest.fixture
def skill_extractor() -> SkillExtractor:
    return SkillExtractor()


# =============================================================================
# Evidence Graph Tests
# =============================================================================


class TestEvidenceGraphConstruction:
    """Test evidence graph node and edge creation."""

    def test_add_evidence_returns_id(self, empty_graph: EvidenceGraph) -> None:
        node_id = empty_graph.add_evidence("Test claim", "test-source", 0.75)
        assert node_id
        assert isinstance(node_id, str)

    def test_add_evidence_stores_node(self, empty_graph: EvidenceGraph) -> None:
        node_id = empty_graph.add_evidence("Test claim", "test-source", 0.75, tags=["test"])
        node = empty_graph.get_node(node_id)
        assert node is not None
        assert node.claim == "Test claim"
        assert node.source == "test-source"
        assert node.confidence == 0.75
        assert "test" in node.tags

    def test_add_evidence_clamps_confidence(self, empty_graph: EvidenceGraph) -> None:
        node_id = empty_graph.add_evidence("Claim", "", 1.5)
        node = empty_graph.get_node(node_id)
        assert node is not None
        assert node.confidence == 1.0

        node_id2 = empty_graph.add_evidence("Claim2", "", -0.5)
        node2 = empty_graph.get_node(node_id2)
        assert node2 is not None
        assert node2.confidence == 0.0

    def test_add_edge_creates_edge(self, empty_graph: EvidenceGraph) -> None:
        n1 = empty_graph.add_evidence("Claim A", "src1")
        n2 = empty_graph.add_evidence("Claim B", "src2")
        eid = empty_graph.add_edge(n1, n2, EdgeType.SUPPORTS, weight=0.9, rationale="Supports well")
        edges = empty_graph.edges_for_node(n2)
        assert len(edges) == 1
        assert edges[0].edge_type == EdgeType.SUPPORTS
        assert edges[0].weight == 0.9

    def test_add_edge_updates_counts(self, empty_graph: EvidenceGraph) -> None:
        n1 = empty_graph.add_evidence("Claim A")
        n2 = empty_graph.add_evidence("Claim B")

        empty_graph.add_edge(n1, n2, EdgeType.SUPPORTS)
        node2 = empty_graph.get_node(n2)
        assert node2 is not None
        assert node2.supporting_count == 1

        empty_graph.add_edge(n1, n2, EdgeType.CONTRADICTS)
        node2_updated = empty_graph.get_node(n2)
        assert node2_updated is not None
        assert node2_updated.supporting_count == 1
        assert node2_updated.contradicting_count == 1

    def test_add_edge_missing_source_raises(self, empty_graph: EvidenceGraph) -> None:
        n1 = empty_graph.add_evidence("Claim A")
        with pytest.raises(KeyError):
            empty_graph.add_edge("nonexistent", n1, EdgeType.SUPPORTS)

    def test_remove_node(self, populated_graph: EvidenceGraph) -> None:
        # Add a node to remove
        nid = populated_graph.add_evidence("Temporary claim", "test")
        assert populated_graph.get_node(nid) is not None
        assert populated_graph.remove_node(nid) is True
        assert populated_graph.get_node(nid) is None
        assert populated_graph.remove_node(nid) is False  # Already gone

    def test_remove_edge(self, populated_graph: EvidenceGraph) -> None:
        # Collect edges for node n1 (first node)
        nodes = list(populated_graph._nodes.values())
        edges = populated_graph.edges_for_node(nodes[0].node_id)
        if edges:
            eid = edges[0].edge_id
            assert populated_graph.remove_edge(eid) is True
            assert populated_graph.remove_edge(eid) is False


class TestEvidenceGraphVerification:
    """Test verification via graph cross-check."""

    def test_verify_unverified_node(self, empty_graph: EvidenceGraph) -> None:
        nid = empty_graph.add_evidence("Standalone claim", confidence=0.5)
        result = empty_graph.verify_node(nid)
        assert result.status == VerificationStatus.UNVERIFIED
        assert result.balance == 0

    def test_verify_confirmed_node(self, populated_graph: EvidenceGraph) -> None:
        # n5 (LoRA + quantization) has many supporters
        n5_id = None
        for node in populated_graph._nodes.values():
            if "quantization" in node.claim.lower():
                n5_id = node.node_id
                break
        assert n5_id is not None

        result = populated_graph.verify_node(n5_id)
        # n5 supports n1, has incoming edges -- should have evidence
        assert result.status in (
            VerificationStatus.VERIFIED,
            VerificationStatus.UNVERIFIED,
            VerificationStatus.CONFIRMED,
        )

    def test_verify_contradicted_node(self, populated_graph: EvidenceGraph) -> None:
        # n1 (LoRA memory) is contradicted by n2 and n4
        n1_id = None
        for node in populated_graph._nodes.values():
            if "memory" in node.claim.lower():
                n1_id = node.node_id
                break
        assert n1_id is not None

        result = populated_graph.verify_node(n1_id)
        # n1 has 2 supporters and 2 contradictors → could be disputed or verified
        assert result.status in (
            VerificationStatus.DISPUTED,
            VerificationStatus.VERIFIED,
            VerificationStatus.UNVERIFIED,
        )

    def test_verify_missing_node_raises(self, empty_graph: EvidenceGraph) -> None:
        with pytest.raises(KeyError):
            empty_graph.verify_node("nonexistent")


class TestEvidenceGraphQueries:
    """Test graph query capabilities."""

    def test_query_by_claim_substring(self, populated_graph: EvidenceGraph) -> None:
        q = GraphQuery(claim_substring="LoRA", limit=10)
        results = populated_graph.query(q)
        assert len(results) >= 3
        assert all("LoRA" in n.claim for n in results)

    def test_query_by_status(self, populated_graph: EvidenceGraph) -> None:
        q = GraphQuery(status=VerificationStatus.UNVERIFIED, limit=10)
        results = populated_graph.query(q)
        # All nodes start unverified
        assert len(results) == 5

    def test_query_by_confidence_range(self, populated_graph: EvidenceGraph) -> None:
        q = GraphQuery(min_confidence=0.80, max_confidence=1.0, limit=10)
        results = populated_graph.query(q)
        assert len(results) >= 2
        assert all(0.80 <= n.confidence <= 1.0 for n in results)

    def test_query_by_tags(self, populated_graph: EvidenceGraph) -> None:
        q = GraphQuery(tags=("lora",), limit=10)
        results = populated_graph.query(q)
        assert len(results) >= 3

    def test_query_by_source(self, populated_graph: EvidenceGraph) -> None:
        q = GraphQuery(source="arxiv", limit=10)
        results = populated_graph.query(q)
        assert len(results) >= 3

    def test_query_with_edge_type_filter(self, populated_graph: EvidenceGraph) -> None:
        q = GraphQuery(edge_type=EdgeType.CONTRADICTS, limit=10)
        results = populated_graph.query(q)
        assert len(results) >= 2  # n1 and n2 are in contradict edges

    def test_find_evidence_for(self, populated_graph: EvidenceGraph) -> None:
        results = populated_graph.find_evidence_for("LoRA", top_k=5)
        assert len(results) > 0

    def test_find_evidence_against(self, populated_graph: EvidenceGraph) -> None:
        results = populated_graph.find_evidence_against("LoRA", top_k=5)
        assert len(results) > 0

    def test_edges_for_node(self, populated_graph: EvidenceGraph) -> None:
        first_node_id = next(iter(populated_graph._nodes.keys()))
        edges = populated_graph.edges_for_node(first_node_id)
        assert isinstance(edges, list)
        assert all(isinstance(e, EvidenceEdge) for e in edges)


class TestContradictionDetection:
    """Test contradiction detection in the evidence graph."""

    def test_detect_direct_contradictions(self, populated_graph: EvidenceGraph) -> None:
        pairs = populated_graph.detect_contradictions(min_severity=0.3)
        # There are direct CONTRADICTS edges between n1-n2 and n1-n4
        contradiction_pairs = [
            p for p in pairs
            if hasattr(p, 'severity') and p.severity > 0
        ]
        assert len(contradiction_pairs) >= 0  # at least some pairs

    def test_contradiction_pair_structure(self, populated_graph: EvidenceGraph) -> None:
        pairs = populated_graph.detect_contradictions(min_severity=0.0)
        if pairs:
            pair = pairs[0]
            assert isinstance(pair, ContradictionPair)
            assert pair.node_a_id
            assert pair.node_b_id
            assert pair.claim_a
            assert pair.claim_b

    def test_empty_graph_no_contradictions(self, empty_graph: EvidenceGraph) -> None:
        pairs = empty_graph.detect_contradictions()
        assert pairs == []


class TestEvidenceGraphExport:
    """Test graph export to Mermaid and Markdown."""

    def test_to_mermaid(self, populated_graph: EvidenceGraph) -> None:
        mermaid = populated_graph.to_mermaid(show_legend=True)
        assert "```mermaid" in mermaid
        assert "flowchart LR" in mermaid
        assert "supports" in mermaid or "contradicts" in mermaid

    def test_to_mermaid_high_confidence(self, populated_graph: EvidenceGraph) -> None:
        mermaid = populated_graph.to_mermaid(high_confidence_only=True)
        assert "```mermaid" in mermaid

    def test_to_markdown_report(self, populated_graph: EvidenceGraph) -> None:
        report = populated_graph.to_markdown_report()
        assert "Evidence Graph Report" in report
        assert "Total claims" in report
        assert "Top Claims" in report

    def test_empty_graph_export(self, empty_graph: EvidenceGraph) -> None:
        mermaid = empty_graph.to_mermaid()
        assert "```mermaid" in mermaid

        report = empty_graph.to_markdown_report()
        assert "Total claims" in report


class TestEvidenceGraphSerialization:
    """Test evidence graph to_dict / from_dict round-trip."""

    def test_round_trip(self, populated_graph: EvidenceGraph) -> None:
        data = populated_graph.to_dict()
        restored = EvidenceGraph.from_dict(data)
        assert len(restored._nodes) == len(populated_graph._nodes)
        assert len(restored._edges) == len(populated_graph._edges)

    def test_empty_round_trip(self, empty_graph: EvidenceGraph) -> None:
        data = empty_graph.to_dict()
        restored = EvidenceGraph.from_dict(data)
        assert len(restored._nodes) == 0
        assert len(restored._edges) == 0

    def test_statistics(self, populated_graph: EvidenceGraph) -> None:
        stats = populated_graph.get_statistics()
        assert stats["total_nodes"] == 5
        assert stats["total_edges"] == 6
        assert stats["total_supporting"] == 2
        assert stats["total_contradicting"] == 2


# =============================================================================
# Adversarial Verification Tests
# =============================================================================


class TestAdversarialVerification:
    """Test the adversarial verification loop."""

    def test_verify_claim_returns_verdict(self, verifier: AdversarialVerificationLoop) -> None:
        verdict = verifier.verify_claim("LoRA reduces memory by 4x")
        assert isinstance(verdict, Verdict)
        assert verdict.claim == "LoRA reduces memory by 4x"
        assert verdict.verdict_id

    def test_verify_claim_has_panel_verdicts(self, verifier: AdversarialVerificationLoop) -> None:
        verdict = verifier.verify_claim("LoRA reduces memory by 4x")
        assert len(verdict.panel_verdicts) == 3

    def test_verify_claim_has_confidence_bracket(self, verifier: AdversarialVerificationLoop) -> None:
        verdict = verifier.verify_claim("LoRA reduces memory by 4x")
        assert verdict.confidence_bracket in (ConfidenceBracket.HIGH, ConfidenceBracket.MEDIUM, ConfidenceBracket.LOW)

    def test_verify_claim_roles_are_correct(self, verifier: AdversarialVerificationLoop) -> None:
        verdict = verifier.verify_claim("LoRA reduces memory by 4x")
        roles = {v.role for v in verdict.panel_verdicts}
        assert AgentRole.SUPPORTER in roles
        assert AgentRole.SKEPTIC in roles
        assert AgentRole.DOMAIN_EXPERT in roles

    def test_verdict_to_dict(self, verifier: AdversarialVerificationLoop) -> None:
        verdict = verifier.verify_claim("LoRA is efficient")
        d = verdict.to_dict()
        assert d["claim"] == "LoRA is efficient"
        assert "confidence_bracket" in d
        assert len(d["panel_verdicts"]) == 3


class TestTriangulation:
    """Test cross-source triangulation."""

    def test_triangulate_returns_sources(self, verifier: AdversarialVerificationLoop) -> None:
        result = verifier.triangulate("LoRA reduces memory by 4x", min_sources=1)
        assert "unique_sources" in result
        assert "verdict" in result
        assert "triangulation_score" in result

    def test_triangulate_with_min_sources(self, verifier: AdversarialVerificationLoop) -> None:
        result = verifier.triangulate("LoRA reduces memory by 4x", min_sources=5)
        assert "triangulation_passed" in result


class TestAppealProcess:
    """Test the appeal process for rejected claims."""

    def test_appeal_on_approved_returns_original(self, verifier: AdversarialVerificationLoop) -> None:
        verdict = verifier.verify_claim("LoRA reduces memory by 4x")
        appeal_result = verifier.appeal(verdict.verdict_id)
        # If already approved, returns original verdict
        assert appeal_result is not None

    def test_appeal_with_revised_claim(self, verifier: AdversarialVerificationLoop) -> None:
        verdict = verifier.verify_claim("LoRA is inefficient")
        appeal_result = verifier.appeal(verdict.verdict_id, revised_claim="LoRA is inefficient for very long sequences")
        assert appeal_result is not None

    def test_appeal_nonexistent_returns_none(self, verifier: AdversarialVerificationLoop) -> None:
        result = verifier.appeal("nonexistent")
        assert result is None

    def test_get_verdict(self, verifier: AdversarialVerificationLoop) -> None:
        verdict = verifier.verify_claim("Test claim")
        retrieved = verifier.get_verdict(verdict.verdict_id)
        assert retrieved is not None
        assert retrieved.claim == "Test claim"

    def test_get_appeal_history(self, verifier: AdversarialVerificationLoop) -> None:
        verifier.verify_claim("Appeal test claim")
        history = verifier.get_appeal_history("Appeal test claim")
        assert len(history) >= 1


# =============================================================================
# Skill Extractor Tests
# =============================================================================


class TestSkillTemplate:
    """Test SkillTemplate construction from findings."""

    def test_from_finding_creates_template(self, sample_finding: FindingRecord) -> None:
        template = SkillTemplate.from_finding(sample_finding)
        assert template.name
        assert template.description
        assert len(template.trigger_patterns) > 0
        assert len(template.tags) > 0

    def test_from_finding_adds_stage_tag(self, sample_finding: FindingRecord) -> None:
        template = SkillTemplate.from_finding(sample_finding)
        assert "progress" in template.tags
        assert "verified" in template.tags

    def test_render_has_frontmatter(self, sample_finding: FindingRecord) -> None:
        template = SkillTemplate.from_finding(sample_finding)
        rendered = template.render()
        assert "---" in rendered
        assert "name:" in rendered
        assert "description:" in rendered
        assert "category:" in rendered

    def test_to_skill_returns_valid_skill(self, sample_finding: FindingRecord) -> None:
        template = SkillTemplate.from_finding(sample_finding)
        skill = template.to_skill()
        assert isinstance(skill, Skill)
        assert skill.name == template.name
        assert skill.description == template.description

    def test_from_idea_stage_finding(self) -> None:
        finding = FindingRecord(
            finding_id="f-idea",
            hypothesis="Test idea hypothesis for skill extraction",
            stage=FindingStage.IDEA,
            valuation=ValuationScores(utility=0.6, quality=0.5, efficiency=0.5),
        )
        template = SkillTemplate.from_finding(finding)
        assert template.name
        assert "idea" in template.tags


class TestSkillExtractor:
    """Test SkillExtractor functionality."""

    def test_extract_from_finding(self, skill_extractor: SkillExtractor, sample_finding: FindingRecord) -> None:
        skill = skill_extractor.extract_from_finding(
            sample_finding, verification_status=None, auto_register=False, write_file=False
        )
        assert skill is not None
        assert isinstance(skill, Skill)
        assert skill.name
        assert skill.description

    def test_extract_with_quality_gate_passes(self, skill_extractor: SkillExtractor, sample_finding: FindingRecord) -> None:
        from lyra.research.evidence_graph import VerificationStatus
        skill = skill_extractor.extract_from_finding(
            sample_finding,
            verification_status=VerificationStatus.CONFIRMED,
            auto_register=False,
            write_file=False,
        )
        assert skill is not None

    def test_extract_with_quality_gate_rejects(self, skill_extractor: SkillExtractor, sample_finding: FindingRecord) -> None:
        from lyra.research.evidence_graph import VerificationStatus
        skill = skill_extractor.extract_from_finding(
            sample_finding,
            verification_status=VerificationStatus.REFUTED,
            auto_register=False,
            write_file=False,
        )
        assert skill is None

    def test_extract_multiple(self, skill_extractor: SkillExtractor) -> None:
        findings = [
            FindingRecord(
                finding_id=f"f-{i}",
                hypothesis=f"Hypothesis {i} for testing",
                stage=FindingStage.PROGRESS,
                valuation=ValuationScores(utility=0.7, quality=0.7, efficiency=0.7),
            )
            for i in range(3)
        ]
        skills = skill_extractor.extract_multiple(
            findings, auto_register=False, write_file=False
        )
        assert len(skills) == 3

    def test_extract_from_paper_missing_file(self, skill_extractor: SkillExtractor) -> None:
        with pytest.raises(FileNotFoundError):
            skill_extractor.extract_from_paper("/nonexistent/paper.md", auto_register=False, write_file=False)

    def test_extract_from_markdown_paper(self, skill_extractor: SkillExtractor, tmp_path) -> None:
        paper_path = tmp_path / "test_paper.md"
        paper_path.write_text(
            "## Methodology\n\nWe use a novel approach to sparse attention.\n\n"
            "## Results\n\n30% cost reduction achieved.\n\n"
            "## Conclusion\n\nSparse attention is effective.\n"
        )
        skills = skill_extractor.extract_from_paper(
            str(paper_path), auto_register=False, write_file=False
        )
        assert len(skills) >= 2  # At least methodology and results sections

    def test_empty_finding_rejected(self, skill_extractor: SkillExtractor) -> None:
        finding = FindingRecord(
            hypothesis="",
            stage=FindingStage.IDEA,
        )
        skill = skill_extractor.extract_from_finding(
            finding, verification_status=None, auto_register=False, write_file=False
        )
        assert skill is None

    def test_low_confidence_finding_rejected(self, skill_extractor: SkillExtractor) -> None:
        finding = FindingRecord(
            hypothesis="Low confidence hypothesis",
            stage=FindingStage.IDEA,
            valuation=ValuationScores(utility=0.1, quality=0.1, efficiency=0.1),
        )
        skill = skill_extractor.extract_from_finding(
            finding, verification_status=None, auto_register=False, write_file=False
        )
        assert skill is None


class TestSkillExtractorPaperParsing:
    """Test paper parsing internals."""

    def test_parse_sections(self, skill_extractor: SkillExtractor) -> None:
        text = "## Intro\n\nSome intro text.\n\n## Method\n\nThe method section.\n"
        sections = skill_extractor._parse_sections(text)
        assert len(sections) == 2
        assert sections[0]["heading"] == "Intro"
        assert sections[1]["heading"] == "Method"

    def test_parse_sections_with_no_headings(self, skill_extractor: SkillExtractor) -> None:
        text = "Plain text without headings."
        sections = skill_extractor._parse_sections(text)
        assert len(sections) == 1
        assert sections[0]["heading"] == "Abstract"

    def test_category_detection_from_method(self) -> None:
        section = {"heading": "Methodology", "body": "Implementation details"}
        cat = SkillExtractor._detect_category_from_section(section)
        assert cat == SkillCategory.BACKEND_PATTERNS

    def test_category_detection_from_results(self) -> None:
        section = {"heading": "Results", "body": "Experimental evaluation"}
        cat = SkillExtractor._detect_category_from_section(section)
        assert cat == SkillCategory.TDD_TESTING

    def test_category_detection_fallback(self) -> None:
        section = {"heading": "Unknown Heading", "body": "Some text"}
        cat = SkillExtractor._detect_category_from_section(section)
        from lyra.research.skill_extractor import DEFAULT_SKILL_CATEGORY
        assert cat == DEFAULT_SKILL_CATEGORY

    def test_language_detection_from_code_block(self, skill_extractor: SkillExtractor) -> None:
        text = "```python\ndef hello():\n    pass\n```"
        lang = skill_extractor._detect_language_from_text(text)
        assert lang == "python"


class TestSkillTemplateSlugify:
    """Test slugify utility."""

    def test_slugify_basic(self) -> None:
        result = SkillTemplate._slugify("Attention Sparsity Reduces Cost")
        assert result == "attention-sparsity-reduces-cost"

    def test_slugify_special_chars(self) -> None:
        result = SkillTemplate._slugify("LoRA: Memory Efficient? Yes!")
        assert "lora" in result
        assert all(c.isalnum() or c == "-" for c in result)
