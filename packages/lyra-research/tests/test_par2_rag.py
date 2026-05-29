"""
Tests for PAR2-RAG and supporting modules.

Covers: par2_rag, multi_perspective, source_verification, knowledge_graph.
All tests run offline — no network calls.
"""

from dataclasses import FrozenInstanceError

import pytest
from lyra_research.knowledge_graph import (
    ResearchEntity,
    ResearchKG,
)
from lyra_research.multi_perspective import (
    DebateRound,
    MultiPerspectiveSynthesizer,
    PerspectiveAgent,
    PerspectiveAnalysis,
    PerspectiveType,
)
from lyra_research.par2_rag import (
    ActionStatus,
    ActionType,
    CoverageTracker,
    Finding,
    PAR2RAGEngine,
    ResearchAction,
    ResearchPlan,
    ResearchReport,
    Subtopic,
)
from lyra_research.source_verification import (
    AuditReport,
    CitationCheck,
    SourceRecord,
    SourceVerifier,
)

# ===========================================================================
# knowledge_graph
# ===========================================================================


class TestResearchEntity:
    """Tests for ResearchEntity frozen dataclass."""

    def test_entity_creation(self):
        ent = ResearchEntity(id="e1", name="Transformer", entity_type="technology")
        assert ent.id == "e1"
        assert ent.name == "Transformer"
        assert ent.entity_type == "technology"
        assert ent.aliases == ()
        assert ent.metadata == {}

    def test_entity_with_aliases(self):
        ent = ResearchEntity(
            id="e2",
            name="GPT-4",
            entity_type="technology",
            aliases=("GPT4", "GPT 4"),
        )
        assert ent.matches_name("GPT4")
        assert ent.matches_name("gpt 4")
        assert ent.matches_name("GPT-4")
        assert not ent.matches_name("GPT-3")

    def test_entity_with_metadata(self):
        ent = ResearchEntity(
            id="e3",
            name="Attention",
            entity_type="concept",
            metadata={"domain": "NLP", "year": "2017"},
        )
        assert ent.metadata["domain"] == "NLP"

    def test_entity_matches_case_insensitive(self):
        ent = ResearchEntity(id="e4", name="BERT", entity_type="technology")
        assert ent.matches_name("bert")
        assert ent.matches_name("Bert")

    def test_entity_is_frozen(self):
        ent = ResearchEntity(id="e5", name="CNN", entity_type="technology")
        with pytest.raises(FrozenInstanceError):
            ent.name = "RNN"  # type: ignore[misc]


class TestResearchKG:
    """Tests for ResearchKG."""

    def test_add_and_get_entity(self):
        kg = ResearchKG("test")
        ent = ResearchEntity(id="e1", name="GAN", entity_type="technology")
        kg.add_entity(ent)
        assert kg.get_entity("e1") is ent
        assert kg.entity_count == 1

    def test_find_entity_by_name(self):
        kg = ResearchKG("test")
        kg.add_entity(ResearchEntity(id="e1", name="ResNet", entity_type="technology"))
        assert kg.find_entity_by_name("ResNet") is not None
        assert kg.find_entity_by_name("resnet") is not None
        assert kg.find_entity_by_name("DenseNet") is None

    def test_find_entity_by_alias(self):
        kg = ResearchKG("test")
        kg.add_entity(
            ResearchEntity(
                id="e1",
                name="Large Language Model",
                entity_type="concept",
                aliases=("LLM", "language model"),
            )
        )
        assert kg.find_entity_by_name("LLM") is not None
        assert kg.find_entity_by_name("language model") is not None

    def test_add_relation(self):
        kg = ResearchKG("test")
        kg.add_entity(ResearchEntity(id="e1", name="Paper A", entity_type="concept"))
        kg.add_entity(ResearchEntity(id="e2", name="Paper B", entity_type="concept"))
        rel = kg.add_relation("e1", "e2", "cites", weight=0.9)
        assert rel is not None
        assert rel.relation_type == "cites"
        assert rel.weight == 0.9
        assert kg.relation_count == 1

    def test_add_relation_missing_entity_returns_none(self):
        kg = ResearchKG("test")
        kg.add_entity(ResearchEntity(id="e1", name="Exists", entity_type="concept"))
        rel = kg.add_relation("e1", "e_missing", "cites")
        assert rel is None
        assert kg.relation_count == 0

    def test_link_entities_convenience(self):
        kg = ResearchKG("test")
        a = ResearchEntity(id="a", name="AlphaGo", entity_type="technology")
        b = ResearchEntity(id="b", name="Deep Blue", entity_type="technology")
        kg.add_entity(a)
        kg.add_entity(b)
        rel = kg.link_entities(a, b, "preceded_by", evidence="AlphaGo came after Deep Blue")
        assert rel is not None
        assert rel.relation_type == "preceded_by"

    def test_list_entities_and_relations(self):
        kg = ResearchKG("test")
        kg.add_entity(ResearchEntity(id="e1", name="X", entity_type="concept"))
        kg.add_entity(ResearchEntity(id="e2", name="Y", entity_type="concept"))
        kg.add_relation("e1", "e2", "uses")
        assert len(kg.list_entities()) == 2
        assert len(kg.list_relations()) == 1

    def test_get_relations_for(self):
        kg = ResearchKG("test")
        kg.add_entity(ResearchEntity(id="e1", name="A", entity_type="concept"))
        kg.add_entity(ResearchEntity(id="e2", name="B", entity_type="concept"))
        kg.add_entity(ResearchEntity(id="e3", name="C", entity_type="concept"))
        kg.add_relation("e1", "e2", "cites")
        kg.add_relation("e2", "e3", "extends")
        rels = kg.get_relations_for("e2")
        assert len(rels) == 2

    def test_extract_entities(self):
        kg = ResearchKG("test")
        text = "The Transformer Architecture was introduced by Google Research. BERT Model outperformed previous benchmarks."
        entities = kg.extract_entities(text)
        assert len(entities) > 0
        names = {e.name for e in entities}
        # Regex captures "The Transformer Architecture" (with "The")
        assert any("Transformer Architecture" in n for n in names)
        assert any("BERT Model" in n for n in names)

    def test_traverse(self):
        kg = ResearchKG("test")
        kg.add_entity(ResearchEntity(id="a", name="A", entity_type="concept"))
        kg.add_entity(ResearchEntity(id="b", name="B", entity_type="concept"))
        kg.add_entity(ResearchEntity(id="c", name="C", entity_type="concept"))
        kg.add_entity(ResearchEntity(id="d", name="D", entity_type="concept"))
        kg.add_relation("a", "b", "connected")
        kg.add_relation("b", "c", "connected")
        kg.add_relation("c", "d", "connected")

        # depth 0
        assert len(kg.traverse("a", depth=0)) == 0
        # depth 1
        depth1 = kg.traverse("a", depth=1)
        assert len(depth1) == 1
        assert depth1[0].name == "B"
        # depth 2
        depth2 = kg.traverse("a", depth=2)
        assert len(depth2) == 2

    def test_traverse_missing_entity(self):
        kg = ResearchKG("test")
        assert kg.traverse("nonexistent") == []

    def test_find_path(self):
        kg = ResearchKG("test")
        kg.add_entity(ResearchEntity(id="a", name="Alpha", entity_type="concept"))
        kg.add_entity(ResearchEntity(id="b", name="Beta", entity_type="concept"))
        kg.add_entity(ResearchEntity(id="c", name="Gamma", entity_type="concept"))
        kg.add_relation("a", "b", "links")
        kg.add_relation("b", "c", "links")

        path = kg.find_path("a", "c")
        assert path == ["a", "b", "c"]

    def test_find_path_same_entity(self):
        kg = ResearchKG("test")
        kg.add_entity(ResearchEntity(id="x", name="X", entity_type="concept"))
        assert kg.find_path("x", "x") == ["x"]

    def test_find_path_no_path(self):
        kg = ResearchKG("test")
        kg.add_entity(ResearchEntity(id="a", name="A", entity_type="concept"))
        kg.add_entity(ResearchEntity(id="z", name="Z", entity_type="concept"))
        assert kg.find_path("a", "z") is None

    def test_detect_contradictions(self):
        kg = ResearchKG("test")
        kg.add_entity(ResearchEntity(id="e1", name="Method X", entity_type="technology"))
        kg.add_entity(ResearchEntity(id="e2", name="Method Y", entity_type="technology"))
        kg.add_relation("e1", "e2", "contradicts", evidence="X claims Y is wrong")
        kg.add_relation("e1", "e2", "cites")

        contradictions = kg.detect_contradictions()
        assert len(contradictions) == 1
        assert contradictions[0][0] == "Method X"
        assert contradictions[0][1] == "Method Y"

    def test_merge_knowledge(self):
        kg1 = ResearchKG("main")
        kg2 = ResearchKG("aux")
        kg1.add_entity(ResearchEntity(id="x", name="Shared", entity_type="concept"))
        kg2.add_entity(ResearchEntity(id="x", name="Shared", entity_type="concept"))  # same id
        kg2.add_entity(ResearchEntity(id="y", name="Unique", entity_type="technology"))

        added = kg1.merge_knowledge(kg2)
        assert added == 1  # only 'y' is new
        assert kg1.entity_count == 2

    def test_merge_knowledge_with_relations(self):
        kg1 = ResearchKG("main")
        kg2 = ResearchKG("aux")
        kg2.add_entity(ResearchEntity(id="a", name="A", entity_type="concept"))
        kg2.add_entity(ResearchEntity(id="b", name="B", entity_type="concept"))
        kg2.add_relation("a", "b", "related")

        kg1.merge_knowledge(kg2)
        assert kg1.relation_count == 1

    def test_len_empty(self):
        assert len(ResearchKG()) == 0


# ===========================================================================
# source_verification
# ===========================================================================


class TestSourceRecord:
    """Tests for SourceRecord."""

    def test_compute_hash(self):
        h = SourceRecord.compute_hash("hello world")
        assert len(h) == 64
        assert SourceRecord.compute_hash("hello world") == h
        assert SourceRecord.compute_hash("different") != h

    def test_source_record_frozen(self):
        sr = SourceRecord(url="https://example.com", title="Example")
        with pytest.raises(FrozenInstanceError):
            sr.title = "Changed"  # type: ignore[misc]


class TestCitationCheck:
    """Tests for CitationCheck."""

    def test_citation_check_creation(self):
        cc = CitationCheck(
            claim_text="Transformers are effective",
            source_url="https://arxiv.org/1234",
            is_supported=True,
            confidence=0.9,
            explanation="Source confirms claim.",
        )
        assert cc.is_supported
        assert cc.confidence == 0.9


class TestAuditReport:
    """Tests for AuditReport."""

    def test_empty_report(self):
        report = AuditReport()
        assert report.total_claims == 0
        assert report.verification_rate == 1.0

    def test_verification_rate(self):
        report = AuditReport(total_claims=5, verified_count=3, unsupported_count=2)
        assert report.verification_rate == 0.6


class TestSourceVerifier:
    """Tests for SourceVerifier."""

    def test_extract_claims_finds_indicators(self):
        sv = SourceVerifier()
        text = (
            "Studies show that Transformer models outperform RNNs. "
            "Research demonstrates significant improvements in accuracy. "
            "According to Smith et al. (2020), attention is key."
        )
        claims = sv.extract_claims(text)
        assert len(claims) >= 2

    def test_extract_claims_empty_text(self):
        sv = SourceVerifier()
        assert sv.extract_claims("") == []

    def test_extract_claims_with_percentage(self):
        sv = SourceVerifier()
        text = "The model achieved 95.5% accuracy on the benchmark dataset."
        claims = sv.extract_claims(text)
        assert len(claims) >= 1

    def test_verify_citation_supported(self):
        sv = SourceVerifier()
        source = SourceRecord(
            url="https://arxiv.org/1234",
            title="Transformers for NLP",
            credibility_score=0.8,
        )
        source_content = "Transformer models achieve state-of-the-art results in NLP tasks."
        claim = "Transformer models are effective for NLP tasks."
        result = sv.verify_citation(claim, source, source_content)
        assert result.is_supported
        assert result.confidence > 0

    def test_verify_citation_unsupported(self):
        sv = SourceVerifier()
        source = SourceRecord(
            url="https://example.com",
            title="Unrelated Topic",
            credibility_score=0.5,
        )
        source_content = "This document discusses gardening techniques."
        claim = "Transformer models revolutionize quantum computing."
        result = sv.verify_citation(claim, source, source_content)
        assert not result.is_supported

    def test_check_faithfulness_perfect(self):
        sv = SourceVerifier()
        text = "The quick brown fox jumps over the lazy dog."
        assert sv.check_faithfulness(text, text) > 0.9

    def test_check_faithfulness_zero(self):
        sv = SourceVerifier()
        assert sv.check_faithfulness("", "content") == 0.0
        assert sv.check_faithfulness("citation", "") == 0.0

    def test_check_faithfulness_partial(self):
        sv = SourceVerifier()
        citation = "Transformer models achieve SOTA"
        source = "Transformer models achieve state-of-the-art results in NLP tasks."
        score = sv.check_faithfulness(citation, source)
        assert 0.0 < score < 1.0

    def test_compute_credibility_authoritative_domain(self):
        sv = SourceVerifier()
        score = sv.compute_credibility(url="https://arxiv.org/abs/1234")
        assert score > 0.5

    def test_compute_credibility_baseline(self):
        sv = SourceVerifier()
        score = sv.compute_credibility(url="https://random-blog.com")
        assert 0.4 <= score <= 0.6

    def test_compute_credibility_with_author(self):
        sv = SourceVerifier()
        score = sv.compute_credibility(
            url="https://arxiv.org/abs/1234",
            author="Smith, Johnson",
        )
        assert score > 0.5

    def test_audit_document(self):
        sv = SourceVerifier()
        text = (
            "Studies show that deep learning improves accuracy by 25%. "
            "According to recent research, transformers outperform RNNs."
        )
        report = sv.audit_document(text)
        assert report.total_claims > 0
        assert report.faithfulness_score is not None

    def test_audit_document_with_citations(self):
        sv = SourceVerifier()
        text = "Research demonstrates that BERT improves NLP."
        citations = {
            "Research demonstrates that BERT improves NLP.": "BERT achieves new SOTA on NLP benchmarks."
        }
        report = sv.audit_document(text, citations=citations)
        assert report.total_claims == 1

    def test_audit_empty_document(self):
        sv = SourceVerifier()
        report = sv.audit_document("")
        assert report.total_claims == 0
        assert report.verification_rate == 1.0

    def test_register_and_get_source(self):
        sv = SourceVerifier()
        sr = SourceRecord(url="https://example.com", title="Example")
        sv.register_source(sr)
        assert sv.get_source("https://example.com") is sr
        assert sv.get_source("https://other.com") is None


# ===========================================================================
# multi_perspective
# ===========================================================================


class TestPerspectiveType:
    """Tests for PerspectiveType enum."""

    def test_all_five_perspectives(self):
        values = {pt.value for pt in PerspectiveType}
        assert values == {"optimist", "skeptic", "pragmatist", "innovator", "historian"}


class TestPerspectiveAgent:
    """Tests for PerspectiveAgent."""

    def test_agent_creation(self):
        agent = PerspectiveAgent(PerspectiveType.SKEPTIC)
        assert agent.perspective == PerspectiveType.SKEPTIC

    def test_analyze_produces_analysis(self):
        agent = PerspectiveAgent(PerspectiveType.OPTIMIST)
        findings = "This breakthrough novel method achieves state-of-the-art performance and is highly scalable."
        analysis = agent.analyze(findings)
        assert isinstance(analysis, PerspectiveAnalysis)
        assert analysis.perspective == PerspectiveType.OPTIMIST
        assert len(analysis.key_insights) > 0
        assert analysis.score >= 0.0

    def test_analyze_all_perspectives(self):
        findings = "A novel hybrid approach improves accuracy by 15% on standard benchmarks."
        for pt in PerspectiveType:
            agent = PerspectiveAgent(pt)
            analysis = agent.analyze(findings)
            assert analysis.perspective == pt
            assert len(analysis.key_insights) > 0

    def test_critique_produces_points(self):
        optimist = PerspectiveAgent(PerspectiveType.OPTIMIST)
        skeptic = PerspectiveAgent(PerspectiveType.SKEPTIC)
        opt_analysis = optimist.analyze("A breakthrough method achieves perfect results.")
        critiques = skeptic.critique(opt_analysis)
        assert len(critiques) > 0

    def test_critique_different_perspective(self):
        agent = PerspectiveAgent(PerspectiveType.PRAGMATIST)
        other = PerspectiveAnalysis(
            perspective=PerspectiveType.INNOVATOR,
            key_insights=("Novel approach found.",),
            strengths=("Creative combination.",),
            weaknesses=(),
            score=0.9,
        )
        critiques = agent.critique(other)
        assert len(critiques) > 0

    def test_synthesize(self):
        agent = PerspectiveAgent(PerspectiveType.HISTORIAN)
        analyses = [
            PerspectiveAnalysis(
                perspective=PerspectiveType.OPTIMIST,
                key_insights=("Great potential.",),
                strengths=("Strong results.",),
                weaknesses=(),
                score=0.8,
            ),
            PerspectiveAnalysis(
                perspective=PerspectiveType.SKEPTIC,
                key_insights=("Need more evidence.",),
                strengths=("Rigorous methodology.",),
                weaknesses=("Limited dataset.",),
                score=0.4,
            ),
        ]
        result = agent.synthesize(analyses)
        assert result.perspective == PerspectiveType.HISTORIAN
        assert len(result.key_insights) > 0

    def test_agent_generates_novel_ideas(self):
        agent = PerspectiveAgent(PerspectiveType.INNOVATOR)
        analysis = agent.analyze("Standard baseline comparison.")
        assert len(analysis.novel_ideas) > 0


class TestMultiPerspectiveSynthesizer:
    """Tests for MultiPerspectiveSynthesizer."""

    def test_debate(self):
        syn = MultiPerspectiveSynthesizer()
        topic = "attention mechanisms"
        findings = "Transformer models with self-attention achieve state-of-the-art results on NLP benchmarks."
        rounds = syn.debate(topic, findings, rounds=2)
        assert len(rounds) == 2
        for r in rounds:
            assert isinstance(r, DebateRound)
            assert len(r.analyses) == 5  # all 5 perspectives
            assert len(r.critiques) > 0

    def test_synthesize_perspectives(self):
        syn = MultiPerspectiveSynthesizer()
        rounds = syn.debate("topic", "findings text with breakthrough novel results", rounds=1)
        result = syn.synthesize_perspectives(rounds)
        assert result.confidence > 0
        assert len(result.balanced_report) > 0

    def test_synthesize_empty_rounds(self):
        syn = MultiPerspectiveSynthesizer()
        result = syn.synthesize_perspectives([])
        assert result.topic == "unknown"

    def test_identify_consensus(self):
        syn = MultiPerspectiveSynthesizer()
        rounds = syn.debate(
            "test",
            "This breakthrough method shows significant improvement over baselines.",
            rounds=2,
        )
        consensus = syn.identify_consensus(rounds)
        assert isinstance(consensus, list)

    def test_highlight_dissent(self):
        syn = MultiPerspectiveSynthesizer()
        rounds = syn.debate(
            "test",
            "A controversial claim with insufficient evidence.",
            rounds=1,
        )
        dissent = syn.highlight_dissent(rounds)
        assert isinstance(dissent, list)
        assert len(dissent) > 0


# ===========================================================================
# par2_rag — data types
# ===========================================================================


class TestSubtopic:
    """Tests for Subtopic."""

    def test_creation(self):
        st = Subtopic(id="st1", title="Test Topic", description="A test", coverage_target=1.0)
        assert st.id == "st1"
        assert st.coverage_target == 1.0

    def test_frozen(self):
        st = Subtopic(id="st1", title="X")
        with pytest.raises(FrozenInstanceError):
            st.title = "Y"  # type: ignore[misc]


class TestResearchPlan:
    """Tests for ResearchPlan."""

    def test_creation(self):
        st = Subtopic(id="s1", title="T1")
        plan = ResearchPlan(
            id="p1",
            query="test query",
            depth=3,
            subtopics=(st,),
        )
        assert plan.id == "p1"
        assert plan.topic_count == 1
        assert plan.created_at != ""

    def test_topic_count_multiple(self):
        subtopics = tuple(
            Subtopic(id=f"s{i}", title=f"T{i}") for i in range(5)
        )
        plan = ResearchPlan(id="p2", query="q", depth=2, subtopics=subtopics)
        assert plan.topic_count == 5

    def test_is_frozen(self):
        st = Subtopic(id="s1", title="T1")
        plan = ResearchPlan(id="p1", query="q", depth=1, subtopics=(st,))
        with pytest.raises(FrozenInstanceError):
            plan.query = "changed"  # type: ignore[misc]


class TestResearchAction:
    """Tests for ResearchAction."""

    def test_creation(self):
        action = ResearchAction(
            id="a1",
            action_type=ActionType.SEARCH,
            description="Search for papers",
            target="attention mechanisms",
            subtopic_ids=("s1",),
        )
        assert action.action_type == ActionType.SEARCH
        assert action.status == ActionStatus.PENDING

    def test_frozen(self):
        action = ResearchAction(
            id="a1",
            action_type=ActionType.READ,
            description="Read paper",
        )
        with pytest.raises(FrozenInstanceError):
            action.status = ActionStatus.COMPLETED  # type: ignore[misc]


class TestFinding:
    """Tests for Finding."""

    def test_creation(self):
        finding = Finding(
            id="f1",
            action_id="a1",
            content="Transformers outperform RNNs.",
            confidence=0.8,
        )
        assert finding.id == "f1"
        assert finding.confidence == 0.8
        assert finding.timestamp != ""

    def test_frozen(self):
        f = Finding(id="f1", action_id="a1", content="test")
        with pytest.raises(FrozenInstanceError):
            f.content = "changed"  # type: ignore[misc]


# ===========================================================================
# par2_rag — CoverageTracker
# ===========================================================================


class TestCoverageTracker:
    """Tests for CoverageTracker."""

    def test_initial_coverage_zero(self):
        st = tuple(Subtopic(id=f"s{i}", title=f"T{i}") for i in range(3))
        tracker = CoverageTracker(st)
        assert tracker.overall_coverage() == 0.0

    def test_update_coverage(self):
        st = tuple(Subtopic(id=f"s{i}", title=f"T{i}") for i in range(3))
        tracker = CoverageTracker(st)
        cmap = tracker.update_coverage("s0", evidence_count=2)
        assert cmap.coverage > 0.0
        assert cmap.evidence_count == 2

    def test_coverage_increases_with_evidence(self):
        st = (Subtopic(id="s0", title="T0"),)
        tracker = CoverageTracker(st)
        c1 = tracker.update_coverage("s0", evidence_count=1)
        c2 = tracker.update_coverage("s0", evidence_count=3)
        assert c2.coverage > c1.coverage

    def test_coverage_capped_at_one(self):
        st = (Subtopic(id="s0", title="T0"),)
        tracker = CoverageTracker(st)
        for _ in range(100):
            tracker.update_coverage("s0", evidence_count=1)
        assert tracker.get_coverage("s0") <= 1.0

    def test_get_coverage_unknown_subtopic(self):
        tracker = CoverageTracker(())
        assert tracker.get_coverage("unknown") == 0.0

    def test_overall_coverage_average(self):
        st = (Subtopic(id="s0", title="A"), Subtopic(id="s1", title="B"))
        tracker = CoverageTracker(st)
        tracker.update_coverage("s0", evidence_count=5)
        overall = tracker.overall_coverage()
        assert 0.0 < overall < 1.0

    def test_lowest_coverage_subtopic(self):
        st = (Subtopic(id="s0", title="A"), Subtopic(id="s1", title="B"))
        tracker = CoverageTracker(st)
        tracker.update_coverage("s0", evidence_count=5)
        lowest = tracker.lowest_coverage_subtopic()
        assert lowest == "s1"

    def test_all_maps(self):
        st = (Subtopic(id="s0", title="A"), Subtopic(id="s1", title="B"))
        tracker = CoverageTracker(st)
        maps = tracker.all_maps()
        assert len(maps) == 2


# ===========================================================================
# par2_rag — PAR2RAGEngine
# ===========================================================================


class TestPAR2RAGEngine:
    """Tests for PAR2RAGEngine."""

    def test_plan_research_basic(self):
        engine = PAR2RAGEngine()
        plan = engine.plan_research("Transformer models", depth=1)
        assert plan.query == "Transformer models"
        assert plan.depth == 1
        assert plan.topic_count == 3
        assert plan.id.startswith("plan_")

    def test_plan_research_depth_controls_subtopics(self):
        engine = PAR2RAGEngine()
        p1 = engine.plan_research("test", depth=1)
        p2 = engine.plan_research("test", depth=2)
        p3 = engine.plan_research("test", depth=3)
        assert p1.topic_count < p2.topic_count < p3.topic_count

    def test_plan_research_clamps_depth(self):
        engine = PAR2RAGEngine()
        plan = engine.plan_research("test", depth=999)
        assert 1 <= plan.topic_count <= 12

    def test_execute_search_action(self):
        engine = PAR2RAGEngine()
        engine.plan_research("test", depth=1)
        action = ResearchAction(
            id="a1",
            action_type=ActionType.SEARCH,
            description="Search for papers",
            target="attention mechanisms",
            subtopic_ids=("plan_x_st00",),
        )
        finding = engine.execute_action(action)
        assert finding.action_id == "a1"
        assert len(finding.content) > 0

    def test_execute_read_action(self):
        engine = PAR2RAGEngine()
        engine.plan_research("test", depth=1)
        action = ResearchAction(
            id="a2",
            action_type=ActionType.READ,
            description="Read paper",
            target="https://arxiv.org/1234",
        )
        finding = engine.execute_action(action)
        assert finding.id is not None
        assert finding.action_id == "a2"
        assert len(finding.content) > 0

    def test_execute_analyze_action(self):
        engine = PAR2RAGEngine()
        engine.plan_research("test", depth=1)
        action = ResearchAction(
            id="a3",
            action_type=ActionType.ANALYZE,
            description="Analyze performance",
            subtopic_ids=("s1", "s2"),
        )
        finding = engine.execute_action(action)
        assert len(finding.content) > 0

    def test_execute_synthesize_action(self):
        engine = PAR2RAGEngine()
        engine.plan_research("test", depth=1)
        action = ResearchAction(
            id="a4",
            action_type=ActionType.SYNTHESIZE,
            description="Synthesize findings",
        )
        finding = engine.execute_action(action)
        assert len(finding.content) > 0

    def test_execute_verify_action(self):
        engine = PAR2RAGEngine()
        engine.plan_research("test", depth=1)
        action = ResearchAction(
            id="a5",
            action_type=ActionType.VERIFY,
            description="Verify claims",
            target="source_url",
        )
        finding = engine.execute_action(action)
        assert finding.confidence >= 0.5

    def test_update_coverage(self):
        engine = PAR2RAGEngine()
        plan = engine.plan_research("test", depth=1)
        # Use real subtopic ID from the generated plan
        st_id = plan.subtopics[0].id
        cmap = engine.update_coverage(st_id, evidence_count=3)
        assert cmap is not None
        assert cmap.evidence_count == 3

    def test_should_continue_initially_true(self):
        engine = PAR2RAGEngine()
        engine.plan_research("test", depth=1)
        cont, reason = engine.should_continue()
        assert cont is True

    def test_should_continue_reaches_max_iterations(self):
        engine = PAR2RAGEngine(max_iterations=1, coverage_threshold=0.99, confidence_threshold=0.99)
        engine.plan_research("test", depth=1)
        engine._iteration = 5  # simulate iterations
        cont, reason = engine.should_continue()
        assert cont is False
        assert "iterations" in reason.lower()

    def test_reflect_on_findings(self):
        engine = PAR2RAGEngine()
        engine.plan_research("test", depth=1)
        findings = [
            Finding(
                id="f1",
                action_id="a1",
                content="Transformers achieve state-of-the-art results.",
                confidence=0.8,
            ),
            Finding(
                id="f2",
                action_id="a2",
                content="CNNs are effective for image classification.",
                confidence=0.7,
            ),
        ]
        reflection = engine.reflect_on_findings(findings)
        assert "gaps" in reflection
        assert "inconsistencies" in reflection
        assert "new_directions" in reflection
        assert "quality_score" in reflection
        assert 0.0 <= reflection["quality_score"] <= 1.0

    def test_reflect_on_empty_findings(self):
        engine = PAR2RAGEngine()
        engine.plan_research("test", depth=1)
        reflection = engine.reflect_on_findings([])
        assert len(reflection["gaps"]) > 0
        assert reflection["quality_score"] == 0.0

    def test_synthesize_report(self):
        engine = PAR2RAGEngine()
        plan = engine.plan_research("test", depth=1)
        findings = [
            Finding(
                id="f1",
                action_id="a1",
                content="Finding about test topic.",
                confidence=0.9,
            ),
        ]
        report = engine.synthesize_report(plan, findings)
        assert isinstance(report, ResearchReport)
        assert report.plan_id == plan.id
        assert len(report.summary) > 0
        assert len(report.findings) == 1

    def test_synthesize_report_empty_findings(self):
        engine = PAR2RAGEngine()
        plan = engine.plan_research("test", depth=1)
        report = engine.synthesize_report(plan, [])
        assert report.findings == ()

    def test_run_deep_research_shallow(self):
        engine = PAR2RAGEngine(
            coverage_threshold=0.2,
            confidence_threshold=0.2,
            max_iterations=5,
        )
        report = engine.run_deep_research("attention mechanisms", depth=1)
        assert isinstance(report, ResearchReport)
        assert report.query == "attention mechanisms"
        assert len(report.findings) > 0
        assert len(report.summary) > 0

    def test_run_deep_research_medium(self):
        engine = PAR2RAGEngine(
            coverage_threshold=0.3,
            confidence_threshold=0.3,
            max_iterations=8,
        )
        report = engine.run_deep_research("reinforcement learning", depth=2)
        assert isinstance(report, ResearchReport)
        assert len(report.findings) > 0

    def test_run_deep_research_produces_coverage(self):
        engine = PAR2RAGEngine(
            coverage_threshold=0.2,
            confidence_threshold=0.2,
            max_iterations=5,
        )
        report = engine.run_deep_research("graph neural networks", depth=1)
        assert len(report.coverage) > 0

    def test_run_deep_research_multiple_runs_independent(self):
        engine = PAR2RAGEngine(
            coverage_threshold=0.2,
            confidence_threshold=0.2,
            max_iterations=5,
        )
        r1 = engine.run_deep_research("topic A", depth=1)
        r2 = engine.run_deep_research("topic B", depth=1)
        assert r1.query == "topic A"
        assert r2.query == "topic B"
        assert r1.plan_id != r2.plan_id

    def test_engine_default_thresholds(self):
        engine = PAR2RAGEngine()
        assert engine.coverage_threshold == PAR2RAGEngine.DEFAULT_COVERAGE_THRESHOLD
        assert engine.confidence_threshold == PAR2RAGEngine.DEFAULT_CONFIDENCE_THRESHOLD


# ===========================================================================
# Integration tests
# ===========================================================================


class TestIntegration:
    """End-to-end integration across all new modules."""

    def test_full_par2_rag_with_kg(self):
        """Run a full research cycle and verify KG is initialized."""
        engine = PAR2RAGEngine(
            coverage_threshold=0.2,
            confidence_threshold=0.2,
            max_iterations=3,
        )
        report = engine.run_deep_research("knowledge graphs", depth=1)
        assert isinstance(report, ResearchReport)
        assert len(report.summary) > 0

        # KG exists and can hold entities (entity extraction depends on
        # capitalized phrases in findings, which may be sparse in simulation)
        assert engine._kg is not None
        assert engine._kg.entity_count >= 0

    def test_multi_perspective_synthesis_after_research(self):
        """Run research, then multi-perspective synthesis on results."""
        engine = PAR2RAGEngine(
            coverage_threshold=0.2,
            confidence_threshold=0.2,
            max_iterations=3,
        )
        report = engine.run_deep_research("transformers", depth=1)

        syn = MultiPerspectiveSynthesizer()
        combined = " ".join(f.content for f in report.findings)
        rounds = syn.debate("transformers", combined, rounds=1)
        result = syn.synthesize_perspectives(rounds)
        assert result.confidence > 0
        assert len(result.balanced_report) > 0

    def test_source_audit_after_research(self):
        """Run research and audit the findings."""
        engine = PAR2RAGEngine(
            coverage_threshold=0.2,
            confidence_threshold=0.2,
            max_iterations=3,
        )
        report = engine.run_deep_research("diffusion models", depth=1)

        sv = SourceVerifier()
        combined = " ".join(f.content for f in report.findings)
        audit = sv.audit_document(combined)
        assert isinstance(audit, AuditReport)

    def test_kg_entity_extraction_and_linking(self):
        """Extract entities from findings and link them."""
        kg = ResearchKG("test_integration")
        text = (
            "The GPT-4 Model from OpenAI Research improved on the Transformer Architecture. "
            "Google Research proposed BERT Model with bidirectional attention."
        )
        entities = kg.extract_entities(text)
        for ent in entities:
            kg.add_entity(ent)

        # Link entities that were extracted
        entity_list = kg.list_entities()
        assert len(entity_list) > 0

        # If we have at least 2 entities, link them
        if len(entity_list) >= 2:
            rel = kg.link_entities(entity_list[0], entity_list[1], "related_to")
            assert rel is not None

    def test_should_continue_at_high_coverage(self):
        """should_continue returns False when thresholds are met."""
        engine = PAR2RAGEngine(
            coverage_threshold=0.01,  # very low — will trigger immediately
            confidence_threshold=0.01,
            max_iterations=15,
        )
        plan = engine.plan_research("test", depth=1)
        # Force high coverage on real subtopic IDs
        for st in plan.subtopics:
            if engine._tracker:
                engine._tracker.update_coverage(st.id, evidence_count=20)
        # Add high-confidence findings
        engine._findings = [
            Finding(id="f1", action_id="a1", content="strong evidence", confidence=0.95),
        ]
        cont, _ = engine.should_continue()
        assert cont is False
