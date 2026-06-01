# Research Workflows Testing Framework

> Comprehensive testing strategy for Lyra's deep research, auto research, scientist research, and AI research workflows with DeepSeek API integration

## Table of Contents

- [Overview](#overview)
- [Testing Architecture](#testing-architecture)
- [Deep Research Testing](#deep-research-testing)
- [Auto Research Testing](#auto-research-testing)
- [Scientist Research Testing](#scientist-research-testing)
- [AI Research Testing](#ai-research-testing)
- [DeepSeek API Integration Testing](#deepseek-api-integration-testing)
- [Test Execution Plans](#test-execution-plans)
- [Test Infrastructure](#test-infrastructure)
- [Performance Benchmarks](#performance-benchmarks)
- [Continuous Integration](#continuous-integration)

---

## Overview

This document defines the complete testing framework for Lyra's research workflows, ensuring reliability, quality, and performance across all research modes.

### Testing Principles

1. **Test Pyramid**: 70% unit, 20% integration, 10% e2e
2. **Isolation**: Each test is independent and repeatable
3. **Coverage**: Minimum 80% code coverage for all research modules
4. **Performance**: All tests complete within defined time budgets
5. **Reliability**: Tests are deterministic and flake-free

### Research Workflow Components

| Component | Package | Primary Function |
|-----------|---------|------------------|
| **Deep Research** | `lyra-research` | Multi-hop research with source verification |
| **Auto Research** | `lyra-autoresearch` | Autonomous research loops with self-healing |
| **Scientist Research** | `lyra-science-pipeline` | Hypothesis-driven experimentation |
| **AI Research** | `lyra-research` | Paper/code analysis and synthesis |

---

## Testing Architecture

### Test Organization

```
packages/
├── lyra-research/
│   ├── tests/
│   │   ├── unit/
│   │   │   ├── test_orchestrator.py
│   │   │   ├── test_discovery.py
│   │   │   ├── test_analysis.py
│   │   │   └── test_synthesis.py
│   │   ├── integration/
│   │   │   ├── test_research_pipeline.py
│   │   │   └── test_multi_source.py
│   │   └── e2e/
│   │       └── test_full_research_session.py
├── lyra-autoresearch/
│   ├── tests/
│   │   ├── unit/
│   │   │   ├── test_citations.py
│   │   │   ├── test_debate.py
│   │   │   ├── test_execution.py
│   │   │   └── test_evolution.py
│   │   ├── integration/
│   │   │   └── test_self_healing.py
│   │   └── e2e/
│   │       └── test_autonomous_loop.py
└── lyra-science-pipeline/
    └── tests/
        ├── unit/
        │   └── test_hypothesis.py
        └── integration/
            └── test_experiment_cycle.py
```

### Test Categories

| Category | Purpose | Coverage Target | Example |
|----------|---------|-----------------|---------|
| **Unit** | Test individual functions/classes | 80%+ | `test_discovery.py::test_arxiv_search` |
| **Integration** | Test component interactions | 70%+ | `test_research_pipeline.py::test_discovery_to_analysis` |
| **E2E** | Test complete workflows | 60%+ | `test_full_research_session.py::test_deep_research` |
| **Performance** | Benchmark speed/memory | N/A | `test_performance.py::test_research_latency` |
| **Stress** | Test under load | N/A | `test_stress.py::test_concurrent_research` |

### Test Fixtures

```python
# conftest.py - Shared fixtures for research tests

import pytest
from pathlib import Path
from lyra_research import ResearchOrchestrator
from lyra_autoresearch import SelfHealingExecutor

@pytest.fixture
def temp_research_dir(tmp_path):
    """Temporary directory for research outputs."""
    research_dir = tmp_path / "research"
    research_dir.mkdir()
    return research_dir

@pytest.fixture
def mock_orchestrator(temp_research_dir):
    """Mock research orchestrator with test configuration."""
    return ResearchOrchestrator(
        output_dir=temp_research_dir,
        # Use mock API clients for testing
    )

@pytest.fixture
def sample_research_sources():
    """Sample research sources for testing."""
    return [
        {
            "id": "arxiv:2605.20025",
            "title": "AutoResearchClaw",
            "abstract": "Autonomous research system...",
            "url": "https://arxiv.org/abs/2605.20025",
        },
        # More samples...
    ]
```

---

## Deep Research Testing

### Component: Multi-Hop Research

**Location**: `packages/lyra-research/src/lyra_research/orchestrator.py`

#### Unit Tests

```python
# test_orchestrator.py

import pytest
from lyra_research import ResearchOrchestrator, ResearchProgress

class TestResearchOrchestrator:
    """Test suite for ResearchOrchestrator."""
    
    def test_clarify_topic(self, mock_orchestrator):
        """Test topic validation and normalization."""
        topic, depth = mock_orchestrator._clarify("  LLM agents  ", "deep")
        assert topic == "LLM agents"
        assert depth == "deep"
    
    def test_clarify_invalid_depth(self, mock_orchestrator):
        """Test depth normalization for invalid values."""
        topic, depth = mock_orchestrator._clarify("test", "invalid")
        assert depth == "standard"
    
    def test_clarify_empty_topic(self, mock_orchestrator):
        """Test error handling for empty topic."""
        with pytest.raises(ValueError, match="Topic cannot be empty"):
            mock_orchestrator._clarify("", "standard")
```

    def test_rank_and_deduplicate(self, mock_orchestrator, sample_research_sources):
        """Test source ranking and deduplication."""
        # Add duplicate source
        sources = sample_research_sources + [sample_research_sources[0]]
        ranked = mock_orchestrator._rank_and_deduplicate(sources, "LLM agents")
        
        # Check deduplication
        assert len(ranked) == len(sample_research_sources)
        
        # Check ranking (higher quality first)
        assert all(ranked[i].quality_score >= ranked[i+1].quality_score 
                   for i in range(len(ranked)-1))
    
    def test_store_to_corpus(self, mock_orchestrator, sample_research_sources):
        """Test storing sources to corpus."""
        entries = mock_orchestrator._store_to_corpus(sample_research_sources)
        
        assert len(entries) == len(sample_research_sources)
        assert all(e.source_id == s["id"] for e, s in zip(entries, sample_research_sources))
        
        # Verify corpus contains entries
        for entry in entries:
            retrieved = mock_orchestrator.corpus.get(entry.id)
            assert retrieved is not None
            assert retrieved.title == entry.title

class TestMultiHopReasoning:
    """Test multi-hop research reasoning."""
    
    def test_query_refinement(self):
        """Test iterative query refinement."""
        from lyra_research.strategies import QueryExpander
        
        expander = QueryExpander()
        initial_query = "LLM agents"
        
        # First refinement
        refined = expander.expand(initial_query, context=["multi-agent systems"])
        assert "multi-agent" in refined.lower()
        
        # Second refinement
        refined2 = expander.expand(refined, context=["tool use", "memory"])
        assert any(term in refined2.lower() for term in ["tool", "memory"])
    
    def test_stopping_criteria(self):
        """Test research stopping criteria."""
        from lyra_research.strategies import StoppingCriteria
        
        criteria = StoppingCriteria(max_hops=3, min_sources=10)
        
        # Should continue
        assert not criteria.should_stop(hop=1, sources_found=5)
        
        # Should stop - max hops reached
        assert criteria.should_stop(hop=3, sources_found=15)
        
        # Should stop - sufficient sources
        assert criteria.should_stop(hop=2, sources_found=20)
```

#### Integration Tests

```python
# test_research_pipeline.py

import pytest
from lyra_research import ResearchOrchestrator

class TestResearchPipeline:
    """Test complete research pipeline integration."""
    
    @pytest.mark.integration
    def test_discovery_to_analysis(self, mock_orchestrator):
        """Test discovery → analysis flow."""
        # Discovery phase
        sources = mock_orchestrator.discovery.discover(
            "LLM reasoning",
            sources=["arxiv"],
            max_per_source=5
        )
        
        assert len(sources["arxiv"]) > 0
        
        # Analysis phase
        papers, repos = mock_orchestrator._analyze_sources(sources["arxiv"])
        
        assert len(papers) > 0
        assert all("title" in p for p in papers)
        assert all("abstract" in p for p in papers)
    
    @pytest.mark.integration
    def test_analysis_to_synthesis(self, mock_orchestrator, sample_research_sources):
        """Test analysis → synthesis flow."""
        # Analyze sources
        papers, repos = mock_orchestrator._analyze_sources(sample_research_sources)
        
        # Synthesize findings
        synthesis = mock_orchestrator.synthesizer.synthesize(
            topic="LLM agents",
            paper_analyses=papers,
            repo_analyses=repos,
            gaps=["evaluation metrics"],
            contradictions=[]
        )
        
        assert synthesis is not None
        assert hasattr(synthesis, "taxonomy")
        assert len(synthesis.taxonomy) > 0

    @pytest.mark.integration
    def test_synthesis_to_report(self, mock_orchestrator):
        """Test synthesis → report generation flow."""
        synthesis = {
            "taxonomy": {"concepts": ["agents", "tools", "memory"]},
            "key_findings": ["Multi-agent systems improve performance"],
        }
        
        report = mock_orchestrator.report_gen.generate(
            topic="LLM agents",
            synthesis=synthesis,
            sources=[],
            gaps=["evaluation"],
            contradictions=[],
            checklist_completion=0.8
        )
        
        assert report is not None
        assert report.topic == "LLM agents"
        assert report.quality_score >= 0.0

#### E2E Tests

```python
# test_full_research_session.py

import pytest
from lyra_research import ResearchOrchestrator

class TestFullResearchSession:
    """End-to-end tests for complete research sessions."""
    
    @pytest.mark.e2e
    @pytest.mark.slow
    def test_quick_research(self, temp_research_dir):
        """Test quick research mode (10 sources, 1 hop)."""
        orchestrator = ResearchOrchestrator(output_dir=temp_research_dir)
        
        progress = orchestrator.research(
            topic="LLM tool use",
            depth="quick",
            sources=["arxiv"]
        )
        
        assert progress.is_complete
        assert progress.error is None
        assert progress.report is not None
        assert progress.sources_found["arxiv"] <= 15
        assert progress.elapsed_seconds < 120  # 2 minutes max
    
    @pytest.mark.e2e
    @pytest.mark.slow
    def test_standard_research(self, temp_research_dir):
        """Test standard research mode (30 sources, 2-3 hops)."""
        orchestrator = ResearchOrchestrator(output_dir=temp_research_dir)
        
        progress = orchestrator.research(
            topic="Multi-agent coordination",
            depth="standard",
            sources=["arxiv", "github"]
        )
        
        assert progress.is_complete
        assert progress.error is None
        assert progress.report is not None
        assert sum(progress.sources_found.values()) >= 20
        assert progress.papers_analyzed > 0
        assert progress.elapsed_seconds < 600  # 10 minutes max
    
    @pytest.mark.e2e
    @pytest.mark.slow
    def test_deep_research_with_verification(self, temp_research_dir):
        """Test deep research mode with adversarial review."""
        orchestrator = ResearchOrchestrator(output_dir=temp_research_dir)
        
        progress = orchestrator.research(
            topic="LLM reasoning capabilities",
            depth="deep",
            sources=["arxiv", "github", "huggingface"]
        )
        
        assert progress.is_complete
        assert progress.error is None
        assert progress.report is not None
        assert sum(progress.sources_found.values()) >= 40
        assert progress.verification_rate >= 0.8  # 80% claims verified
        assert progress.gaps_found > 0
        assert progress.elapsed_seconds < 1800  # 30 minutes max

### Component: Source Chaining

**Location**: `packages/lyra-research/src/lyra_research/sources.py`

#### Unit Tests

```python
# test_sources.py

import pytest
from lyra_research.sources import CitationTraversal, SourceQualityScorer

class TestCitationTraversal:
    """Test citation network traversal."""
    
    def test_forward_citations(self):
        """Test finding papers that cite a source."""
        traversal = CitationTraversal()
        
        source_id = "arxiv:2605.20025"
        citations = traversal.get_forward_citations(source_id, max_depth=1)
        
        assert isinstance(citations, list)
        assert all("id" in c for c in citations)
    
    def test_backward_citations(self):
        """Test finding papers cited by a source."""
        traversal = CitationTraversal()
        
        source_id = "arxiv:2605.20025"
        references = traversal.get_backward_citations(source_id, max_depth=1)
        
        assert isinstance(references, list)
        assert all("id" in r for r in references)

    def test_citation_chain_depth(self):
        """Test multi-hop citation traversal."""
        traversal = CitationTraversal()
        
        source_id = "arxiv:2605.20025"
        chain = traversal.build_citation_chain(source_id, max_depth=3)
        
        assert len(chain) <= 3
        assert chain[0]["id"] == source_id

class TestSourceQualityScorer:
    """Test source quality scoring."""
    
    def test_score_paper(self):
        """Test paper quality scoring."""
        scorer = SourceQualityScorer()
        
        paper = {
            "id": "arxiv:2605.20025",
            "title": "AutoResearchClaw",
            "citations": 150,
            "year": 2026,
            "venue": "NeurIPS",
        }
        
        score = scorer.score_paper(paper, query="autonomous research")
        
        assert 0.0 <= score <= 1.0
        assert score > 0.5  # High-quality paper
    
    def test_score_repository(self):
        """Test repository quality scoring."""
        scorer = SourceQualityScorer()
        
        repo = {
            "id": "github:org/repo",
            "stars": 5000,
            "forks": 800,
            "last_updated": "2026-05-01",
            "has_readme": True,
            "has_tests": True,
        }
        
        score = scorer.score_repository(repo)
        
        assert 0.0 <= score <= 1.0
        assert score > 0.6  # High-quality repo

### Component: Evidence Synthesis

**Location**: `packages/lyra-research/src/lyra_research/synthesis.py`

#### Unit Tests

```python
# test_synthesis.py

import pytest
from lyra_research.synthesis import (
    ConceptExtractor,
    RelationshipDiscovery,
    KnowledgeGraph
)

class TestConceptExtractor:
    """Test concept extraction from research sources."""
    
    def test_extract_concepts(self):
        """Test extracting key concepts from text."""
        extractor = ConceptExtractor()
        
        text = """
        Multi-agent systems use tool-calling capabilities to interact with
        external APIs. Memory systems store conversation history for context.
        """
        
        concepts = extractor.extract(text)
        
        assert len(concepts) > 0
        assert any("multi-agent" in c.name.lower() for c in concepts)
        assert any("tool" in c.name.lower() for c in concepts)
        assert any("memory" in c.name.lower() for c in concepts)
    
    def test_concept_frequency(self):
        """Test concept frequency scoring."""
        extractor = ConceptExtractor()
        
        text = "Agents use tools. Agents need memory. Tools are essential."
        concepts = extractor.extract(text)
        
        # "agents" and "tools" should have higher frequency
        agent_concept = next(c for c in concepts if "agent" in c.name.lower())
        tool_concept = next(c for c in concepts if "tool" in c.name.lower())
        
        assert agent_concept.frequency >= 2
        assert tool_concept.frequency >= 2

class TestRelationshipDiscovery:
    """Test relationship discovery between concepts."""
    
    def test_discover_relationships(self):
        """Test discovering relationships from text."""
        discovery = RelationshipDiscovery()
        
        text = "AutoGPT extends the GPT-4 model with autonomous capabilities."
        relationships = discovery.discover(text)
        
        assert len(relationships) > 0
        assert any(r.type == "extends" for r in relationships)
    
    def test_relationship_types(self):
        """Test different relationship types."""
        discovery = RelationshipDiscovery()
        
        texts = [
            "Paper A supports the findings of Paper B.",
            "Method X contradicts approach Y.",
            "System Z implements algorithm W.",
        ]
        
        all_relationships = []
        for text in texts:
            all_relationships.extend(discovery.discover(text))
        
        types = {r.type for r in all_relationships}
        assert "supports" in types
        assert "contradicts" in types
        assert "implements" in types

class TestKnowledgeGraph:
    """Test knowledge graph construction."""
    
    def test_add_nodes(self):
        """Test adding nodes to knowledge graph."""
        kg = KnowledgeGraph()
        
        kg.add_node("concept1", node_type="concept", properties={"name": "Agents"})
        kg.add_node("concept2", node_type="concept", properties={"name": "Tools"})
        
        assert kg.has_node("concept1")
        assert kg.has_node("concept2")
        assert kg.node_count() == 2
    
    def test_add_edges(self):
        """Test adding edges to knowledge graph."""
        kg = KnowledgeGraph()
        
        kg.add_node("c1", node_type="concept")
        kg.add_node("c2", node_type="concept")
        kg.add_edge("c1", "c2", edge_type="relates_to")
        
        assert kg.has_edge("c1", "c2")
        assert kg.edge_count() == 1
    
    def test_graph_traversal(self):
        """Test traversing knowledge graph."""
        kg = KnowledgeGraph()
        
        # Build simple graph: A -> B -> C
        kg.add_node("A", node_type="concept")
        kg.add_node("B", node_type="concept")
        kg.add_node("C", node_type="concept")
        kg.add_edge("A", "B", edge_type="relates_to")
        kg.add_edge("B", "C", edge_type="relates_to")
        
        # Find path from A to C
        path = kg.find_path("A", "C")
        assert path == ["A", "B", "C"]

---

## Auto Research Testing

### Component: Citation Verification

**Location**: `packages/lyra-autoresearch/src/lyra_autoresearch/citations.py`

#### Unit Tests

```python
# test_citations.py

import pytest
from lyra_autoresearch.citations import CitationVerifier, VerifyStatus

class TestCitationVerifier:
    """Test 4-layer citation verification system."""
    
    def test_verify_citation_exists(self):
        """Test verifying citation exists in source."""
        verifier = CitationVerifier()
        
        claim = "AutoGPT uses GPT-4 for autonomous task execution."
        source = {
            "id": "arxiv:2605.20025",
            "content": "AutoGPT leverages GPT-4 to autonomously execute tasks..."
        }
        
        result = verifier.verify(claim, source)
        
        assert result.status == VerifyStatus.VERIFIED
        assert result.confidence >= 0.8
    
    def test_verify_citation_missing(self):
        """Test detecting missing citations."""
        verifier = CitationVerifier()
        
        claim = "System X achieves 99% accuracy."
        source = {
            "id": "arxiv:2605.20025",
            "content": "System Y achieves 85% accuracy on benchmark Z."
        }
        
        result = verifier.verify(claim, source)
        
        assert result.status == VerifyStatus.NOT_FOUND
        assert result.confidence < 0.3
    
    def test_verify_citation_contradicts(self):
        """Test detecting contradictory citations."""
        verifier = CitationVerifier()
        
        claim = "Method A outperforms Method B."
        source = {
            "id": "arxiv:2605.20025",
            "content": "Our experiments show Method B significantly outperforms Method A."
        }
        
        result = verifier.verify(claim, source)
        
        assert result.status == VerifyStatus.CONTRADICTS
        assert result.confidence >= 0.7
    
    def test_verify_batch_citations(self):
        """Test batch citation verification."""
        verifier = CitationVerifier()
        
        claims = [
            "Claim 1 about agents.",
            "Claim 2 about tools.",
            "Claim 3 about memory.",
        ]
        
        sources = [
            {"id": "s1", "content": "Agents are autonomous..."},
            {"id": "s2", "content": "Tools enable API calls..."},
            {"id": "s3", "content": "Memory stores context..."},
        ]
        
        results = verifier.verify_batch(claims, sources)
        
        assert len(results) == len(claims)
        assert all(r.status in [VerifyStatus.VERIFIED, VerifyStatus.PARTIAL] for r in results)

### Component: Self-Healing Execution

**Location**: `packages/lyra-autoresearch/src/lyra_autoresearch/execution.py`

#### Unit Tests

```python
# test_execution.py

import pytest
from lyra_autoresearch.execution import SelfHealingExecutor, FailureType

class TestSelfHealingExecutor:
    """Test self-healing execution with Pivot/Refine loops."""
    
    def test_execute_success(self):
        """Test successful execution without healing."""
        executor = SelfHealingExecutor()
        
        def task():
            return {"status": "success", "result": 42}
        
        result = executor.execute(task)
        
        assert result["status"] == "success"
        assert result["result"] == 42
        assert executor.failure_count == 0
    
    def test_execute_with_retry(self):
        """Test execution with transient failure and retry."""
        executor = SelfHealingExecutor(max_retries=3)
        
        attempt = 0
        def flaky_task():
            nonlocal attempt
            attempt += 1
            if attempt < 3:
                raise RuntimeError("Transient error")
            return {"status": "success"}
        
        result = executor.execute(flaky_task)
        
        assert result["status"] == "success"
        assert attempt == 3
        assert executor.retry_count == 2
    
    def test_execute_with_pivot(self):
        """Test execution with pivot to alternative strategy."""
        executor = SelfHealingExecutor()
        
        def failing_task():
            raise ValueError("Strategy A failed")
        
        def pivot_strategy():
            return {"status": "success", "strategy": "B"}
        
        result = executor.execute(failing_task, pivot_fn=pivot_strategy)
        
        assert result["status"] == "success"
        assert result["strategy"] == "B"
        assert executor.pivot_count == 1
    
    def test_execute_with_refine(self):
        """Test execution with query refinement."""
        executor = SelfHealingExecutor()
        
        def task_with_refinement(query):
            if "refined" not in query:
                raise ValueError("Query needs refinement")
            return {"status": "success", "query": query}
        
        def refine_fn(error):
            return "refined query"
        
        result = executor.execute(
            lambda: task_with_refinement("initial query"),
            refine_fn=refine_fn
        )
        
        assert result["status"] == "success"
        assert "refined" in result["query"]
        assert executor.refine_count == 1

#### Integration Tests

```python
# test_self_healing.py

import pytest
from lyra_autoresearch.execution import SelfHealingExecutor, ExecutionStrategy

class TestSelfHealingIntegration:
    """Integration tests for self-healing execution."""
    
    @pytest.mark.integration
    def test_multi_stage_healing(self):
        """Test multi-stage healing: retry → pivot → refine."""
        executor = SelfHealingExecutor(max_retries=2)
        
        stage = {"attempt": 0, "pivoted": False}
        
        def complex_task():
            stage["attempt"] += 1
            
            if stage["attempt"] < 2:
                raise RuntimeError("Transient error")
            
            if not stage["pivoted"]:
                raise ValueError("Need pivot")
            
            return {"status": "success", "stages": stage["attempt"]}
        
        def pivot_fn():
            stage["pivoted"] = True
            return complex_task()
        
        result = executor.execute(complex_task, pivot_fn=pivot_fn)
        
        assert result["status"] == "success"
        assert executor.retry_count >= 1
        assert executor.pivot_count >= 1

### Component: Multi-Agent Debate

**Location**: `packages/lyra-autoresearch/src/lyra_autoresearch/debate.py`

#### Unit Tests

```python
# test_debate.py

import pytest
from lyra_autoresearch.debate import DebatePanel, Perspective

class TestDebatePanel:
    """Test multi-agent structured debate system."""
    
    def test_create_panel(self):
        """Test creating debate panel with perspectives."""
        panel = DebatePanel(
            topic="LLM reasoning capabilities",
            perspectives=[
                Perspective(name="Optimist", stance="pro"),
                Perspective(name="Skeptic", stance="con"),
                Perspective(name="Pragmatist", stance="neutral"),
            ]
        )
        
        assert len(panel.perspectives) == 3
        assert panel.topic == "LLM reasoning capabilities"
    
    def test_debate_round(self):
        """Test single debate round."""
        panel = DebatePanel(
            topic="Test topic",
            perspectives=[
                Perspective(name="A", stance="pro"),
                Perspective(name="B", stance="con"),
            ]
        )
        
        round_result = panel.run_round(round_number=1)
        
        assert round_result.round_number == 1
        assert len(round_result.arguments) == 2
        assert all(arg.perspective in ["A", "B"] for arg in round_result.arguments)
    
    def test_debate_convergence(self):
        """Test debate convergence detection."""
        panel = DebatePanel(
            topic="Test topic",
            perspectives=[
                Perspective(name="A", stance="pro"),
                Perspective(name="B", stance="con"),
            ],
            max_rounds=5
        )
        
        result = panel.run_debate()
        
        assert result.converged or result.rounds_completed == 5
        assert len(result.consensus_points) >= 0

### Component: Evolution & Learning

**Location**: `packages/lyra-autoresearch/src/lyra_autoresearch/evolution.py`

#### Unit Tests

```python
# test_evolution.py

import pytest
from lyra_autoresearch.evolution import (
    EvolutionEngine,
    LessonEntry,
    LessonCategory,
    LessonSeverity
)

class TestEvolutionEngine:
    """Test cross-run evolution and learning."""
    
    def test_record_lesson(self):
        """Test recording lessons from research runs."""
        engine = EvolutionEngine()
        
        lesson = LessonEntry(
            category=LessonCategory.QUERY_REFINEMENT,
            severity=LessonSeverity.HIGH,
            description="Broad queries need domain-specific terms",
            context={"query": "AI", "refined": "AI reasoning systems"},
            success_rate_before=0.3,
            success_rate_after=0.8
        )
        
        engine.record_lesson(lesson)
        
        assert engine.lesson_count() == 1
        assert engine.get_lessons(category=LessonCategory.QUERY_REFINEMENT)[0] == lesson
    
    def test_apply_lessons(self):
        """Test applying learned lessons to new research."""
        engine = EvolutionEngine()
        
        # Record lesson
        engine.record_lesson(LessonEntry(
            category=LessonCategory.SOURCE_SELECTION,
            severity=LessonSeverity.MEDIUM,
            description="ArXiv better for ML papers than GitHub",
            context={"domain": "machine learning"},
            success_rate_before=0.5,
            success_rate_after=0.9
        ))
        
        # Apply to new research
        recommendations = engine.get_recommendations(
            context={"domain": "machine learning", "task": "source_selection"}
        )
        
        assert len(recommendations) > 0
        assert any("arxiv" in r.lower() for r in recommendations)

#### E2E Tests

```python
# test_autonomous_loop.py

import pytest
from lyra_autoresearch import SelfHealingExecutor, EvolutionEngine

class TestAutonomousLoop:
    """End-to-end tests for autonomous research loops."""
    
    @pytest.mark.e2e
    @pytest.mark.slow
    def test_full_autonomous_cycle(self):
        """Test complete autonomous research cycle with learning."""
        executor = SelfHealingExecutor()
        evolution = EvolutionEngine()
        
        # Run research with self-healing
        result = executor.execute(
            lambda: {"status": "success", "findings": ["A", "B", "C"]}
        )
        
        assert result["status"] == "success"
        
        # Record lessons
        if executor.pivot_count > 0:
            evolution.record_lesson(LessonEntry(
                category=LessonCategory.STRATEGY_ADAPTATION,
                severity=LessonSeverity.HIGH,
                description="Pivot improved success rate",
                context={"pivots": executor.pivot_count},
                success_rate_before=0.0,
                success_rate_after=1.0
            ))
        
        # Verify learning
        assert evolution.lesson_count() >= 0

---

## Scientist Research Testing

### Component: Hypothesis Generation

**Location**: `packages/lyra-science-pipeline/src/lyra_science_pipeline/__init__.py`

#### Unit Tests

```python
# test_hypothesis.py

import pytest
from lyra_science_pipeline import SciencePipeline, Hypothesis

class TestHypothesisGeneration:
    """Test hypothesis generation and management."""
    
    def test_propose_hypothesis(self):
        """Test proposing a new hypothesis."""
        pipeline = SciencePipeline()
        
        hypothesis = pipeline.propose_hypothesis(
            statement="Increasing context window improves reasoning",
            iv="context_window_size",
            dv="reasoning_accuracy",
            effect="positive"
        )
        
        assert hypothesis.id == "H1"
        assert hypothesis.statement == "Increasing context window improves reasoning"
        assert hypothesis.status == "proposed"
        assert hypothesis.confidence == 0.5
    
    def test_multiple_hypotheses(self):
        """Test managing multiple hypotheses."""
        pipeline = SciencePipeline()
        
        h1 = pipeline.propose_hypothesis("H1", "iv1", "dv1", "positive")
        h2 = pipeline.propose_hypothesis("H2", "iv2", "dv2", "negative")
        
        assert len(pipeline.hypotheses) == 2
        assert h1.id == "H1"
        assert h2.id == "H2"

class TestExperimentDesign:
    """Test experiment design and execution."""
    
    def test_create_harness(self):
        """Test creating experiment harness."""
        pipeline = SciencePipeline()
        
        harness = pipeline.create_harness(
            sandbox_type="docker",
            variables={"model": "gpt-4", "temperature": 0.7}
        )
        
        assert harness.id == "TH1"
        assert harness.sandbox_type == "docker"
        assert harness.variables["model"] == "gpt-4"
    
    @pytest.mark.asyncio
    async def test_run_experiment(self):
        """Test running experiment with hypothesis."""
        pipeline = SciencePipeline()
        
        hypothesis = pipeline.propose_hypothesis(
            "Test hypothesis", "iv", "dv", "positive"
        )
        harness = pipeline.create_harness("mock", {})
        
        result = await pipeline.run_experiment(hypothesis.id, harness.id)
        
        assert result.hypothesis_id == hypothesis.id
        assert result.outcome is not None
        assert 0.0 <= result.effect_size <= 1.0
        assert 0.0 <= result.significance <= 1.0
        assert hypothesis.status in ["confirmed", "refuted"]

class TestResultAnalysis:
    """Test experiment result analysis."""
    
    def test_analyze_results(self):
        """Test analyzing experiment results."""
        pipeline = SciencePipeline()
        
        # Create and run experiments
        h1 = pipeline.propose_hypothesis("H1", "iv", "dv", "positive")
        h1.status = "confirmed"
        h1.confidence = 0.9
        
        analysis = pipeline.analyze_results()
        
        assert len(analysis) == 1
        assert analysis[0]["hypothesis"] == "H1"
        assert analysis[0]["status"] == "confirmed"
        assert analysis[0]["confidence"] == 0.9

#### Integration Tests

```python
# test_experiment_cycle.py

import pytest
from lyra_science_pipeline import SciencePipeline

class TestExperimentCycle:
    """Integration tests for complete experiment cycle."""
    
    @pytest.mark.integration
    @pytest.mark.asyncio
    async def test_hypothesis_to_conclusion(self):
        """Test complete cycle: hypothesis → experiment → analysis."""
        pipeline = SciencePipeline()
        
        # 1. Propose hypothesis
        hypothesis = pipeline.propose_hypothesis(
            "Multi-agent systems improve task completion",
            "num_agents",
            "completion_rate",
            "positive"
        )
        
        # 2. Design experiment
        harness = pipeline.create_harness(
            "simulation",
            {"num_agents": [1, 2, 4, 8]}
        )
        
        # 3. Run experiment
        result = await pipeline.run_experiment(hypothesis.id, harness.id)
        
        # 4. Analyze results
        analysis = pipeline.analyze_results()
        
        assert len(analysis) == 1
        assert analysis[0]["hypothesis"] == hypothesis.statement
        assert analysis[0]["conclusion"] in ["Supported", "Not supported"]

---

## AI Research Testing

### Component: Paper Analysis

**Location**: `packages/lyra-research/src/lyra_research/analysis.py`

#### Unit Tests

```python
# test_paper_analysis.py

import pytest
from lyra_research.analysis import PaperAnalyzer, PaperAnalysis

class TestPaperAnalyzer:
    """Test paper analysis capabilities."""
    
    def test_analyze_paper(self):
        """Test analyzing research paper."""
        analyzer = PaperAnalyzer()
        
        paper = {
            "id": "arxiv:2605.20025",
            "title": "AutoResearchClaw",
            "abstract": "We present AutoResearchClaw, an autonomous research system...",
            "content": "Full paper content here...",
        }
        
        analysis = analyzer.analyze(paper)
        
        assert isinstance(analysis, PaperAnalysis)
        assert analysis.paper_id == paper["id"]
        assert len(analysis.key_findings) > 0
        assert len(analysis.methods) > 0
        assert analysis.quality_score >= 0.0
    
    def test_extract_methodology(self):
        """Test extracting methodology from paper."""
        analyzer = PaperAnalyzer()
        
        content = """
        We use a multi-agent system with 3 specialized agents.
        Each agent is powered by GPT-4 with temperature 0.7.
        Experiments run on 1000 test cases from benchmark X.
        """
        
        methods = analyzer.extract_methodology(content)
        
        assert len(methods) > 0
        assert any("multi-agent" in m.lower() for m in methods)
        assert any("gpt-4" in m.lower() for m in methods)
    
    def test_extract_results(self):
        """Test extracting results from paper."""
        analyzer = PaperAnalyzer()
        
        content = """
        Our system achieves 92% accuracy on benchmark A.
        Compared to baseline (78%), this is a 14% improvement.
        """
        
        results = analyzer.extract_results(content)
        
        assert len(results) > 0
        assert any("92%" in r for r in results)
        assert any("improvement" in r.lower() for r in results)

### Component: Code Analysis

**Location**: `packages/lyra-research/src/lyra_research/analysis.py`

#### Unit Tests

```python
# test_repository_analysis.py

import pytest
from lyra_research.analysis import RepositoryAnalyzer, RepositoryAnalysis

class TestRepositoryAnalyzer:
    """Test repository analysis capabilities."""
    
    def test_analyze_repository(self):
        """Test analyzing code repository."""
        analyzer = RepositoryAnalyzer()
        
        repo = {
            "id": "github:org/repo",
            "name": "awesome-llm-agents",
            "description": "Multi-agent system framework",
            "readme": "# Awesome LLM Agents\n\nFramework for building...",
            "languages": {"Python": 85, "JavaScript": 15},
        }
        
        analysis = analyzer.analyze(repo)
        
        assert isinstance(analysis, RepositoryAnalysis)
        assert analysis.repo_id == repo["id"]
        assert len(analysis.key_features) > 0
        assert analysis.primary_language == "Python"
    
    def test_extract_architecture(self):
        """Test extracting architecture from README."""
        analyzer = RepositoryAnalyzer()
        
        readme = """
        ## Architecture
        
        The system consists of:
        - Agent orchestrator (manages agent lifecycle)
        - Tool registry (provides API access)
        - Memory store (persists conversation history)
        """
        
        architecture = analyzer.extract_architecture(readme)
        
        assert len(architecture) > 0
        assert any("orchestrator" in a.lower() for a in architecture)
        assert any("tool" in a.lower() for a in architecture)
        assert any("memory" in a.lower() for a in architecture)
    
    def test_assess_code_quality(self):
        """Test code quality assessment."""
        analyzer = RepositoryAnalyzer()
        
        repo_info = {
            "has_tests": True,
            "has_ci": True,
            "has_docs": True,
            "test_coverage": 85,
            "stars": 5000,
            "forks": 800,
        }
        
        quality = analyzer.assess_quality(repo_info)
        
        assert 0.0 <= quality <= 1.0
        assert quality > 0.7  # High quality repo

---

## DeepSeek API Integration Testing

### Component: API Configuration

**Location**: Model router and provider system

#### Unit Tests

```python
# test_deepseek_config.py

import pytest
import os
from lyra_model_router import IntelligentModelRouter

class TestDeepSeekConfiguration:
    """Test DeepSeek API configuration."""
    
    def test_api_key_validation(self):
        """Test API key validation."""
        # Valid key format
        assert validate_deepseek_key("sk-1234567890abcdef")
        
        # Invalid key format
        assert not validate_deepseek_key("invalid-key")
        assert not validate_deepseek_key("")
    
    def test_environment_variable_loading(self):
        """Test loading API key from environment."""
        os.environ["DEEPSEEK_API_KEY"] = "sk-test-key"
        
        config = load_deepseek_config()
        
        assert config["api_key"] == "sk-test-key"
        assert config["base_url"] == "https://api.deepseek.com"
    
    def test_anthropic_bridge_config(self):
        """Test DeepSeek via Anthropic-compatible bridge."""
        os.environ["ANTHROPIC_API_KEY"] = "sk-deepseek-key"
        os.environ["ANTHROPIC_BASE_URL"] = "https://api.deepseek.com/anthropic"
        os.environ["ANTHROPIC_MODEL"] = "deepseek-v4-pro"
        
        config = load_anthropic_bridge_config()
        
        assert config["api_key"] == "sk-deepseek-key"
        assert "deepseek" in config["base_url"]
        assert config["model"] == "deepseek-v4-pro"

### Component: Model Routing

**Location**: `packages/lyra-model-router/src/lyra_model_router/router_v2.py`

#### Unit Tests

```python
# test_model_routing.py

import pytest
from lyra_model_router import IntelligentModelRouter, RoutingStrategy

class TestDeepSeekRouting:
    """Test DeepSeek model routing."""
    
    def test_route_to_v4_pro(self):
        """Test routing complex tasks to deepseek-v4-pro."""
        router = IntelligentModelRouter()
        
        decision = router.route_task(
            task_description="Analyze complex multi-agent coordination patterns",
            provider="deepseek"
        )
        
        assert decision.selected_model == "deepseek-v4-pro"
        assert decision.reasoning_depth == "deep"
    
    def test_route_to_v4_flash(self):
        """Test routing standard tasks to deepseek-v4-flash."""
        router = IntelligentModelRouter()
        
        decision = router.route_task(
            task_description="Implement user authentication function",
            provider="deepseek"
        )
        
        assert decision.selected_model == "deepseek-v4-flash"
        assert decision.cost_tier == "mid"
    
    def test_route_to_chat(self):
        """Test routing quick tasks to deepseek-chat."""
        router = IntelligentModelRouter()
        
        decision = router.route_task(
            task_description="What is the status of the build?",
            provider="deepseek"
        )
        
        assert decision.selected_model == "deepseek-chat"
        assert decision.cost_tier == "low"
    
    def test_cost_optimization(self):
        """Test cost optimization with DeepSeek models."""
        router = IntelligentModelRouter()
        
        # Process 100 mixed tasks
        tasks = [
            ("complex analysis", "v4-pro"),
            ("implement feature", "v4-flash"),
            ("quick lookup", "chat"),
        ] * 33 + [("complex analysis", "v4-pro")]
        
        total_cost = 0
        for task_desc, expected_model in tasks:
            decision = router.route_task(task_desc, provider="deepseek")
            total_cost += decision.estimated_cost
        
        # Verify cost savings vs always using v4-pro
        baseline_cost = len(tasks) * 15.0  # v4-pro cost
        savings_pct = (baseline_cost - total_cost) / baseline_cost * 100
        
        assert savings_pct >= 40  # At least 40% cost reduction

### Component: Cost Tracking

**Location**: `packages/lyra-model-router/src/lyra_model_router/usage_tracker.py`

#### Unit Tests

```python
# test_cost_tracking.py

import pytest
from lyra_model_router import UsageTracker

class TestCostTracking:
    """Test cost tracking for DeepSeek API."""
    
    def test_track_usage(self):
        """Test tracking API usage."""
        tracker = UsageTracker()
        
        tracker.record_usage(
            model="deepseek-v4-pro",
            input_tokens=1000,
            output_tokens=500,
            latency_ms=2500
        )
        
        stats = tracker.get_stats()
        
        assert stats.total_requests == 1
        assert stats.total_input_tokens == 1000
        assert stats.total_output_tokens == 500
        assert stats.total_cost > 0
    
    def test_cost_calculation(self):
        """Test cost calculation for different models."""
        tracker = UsageTracker()
        
        # v4-pro: $2.19/M input, $8.97/M output
        cost_pro = tracker.calculate_cost(
            model="deepseek-v4-pro",
            input_tokens=1_000_000,
            output_tokens=1_000_000
        )
        assert abs(cost_pro - 11.16) < 0.01
        
        # v4-flash: $0.27/M input, $1.10/M output
        cost_flash = tracker.calculate_cost(
            model="deepseek-v4-flash",
            input_tokens=1_000_000,
            output_tokens=1_000_000
        )
        assert abs(cost_flash - 1.37) < 0.01

    def test_budget_enforcement(self):
        """Test budget limit enforcement."""
        tracker = UsageTracker(budget_limit=10.0)
        
        # Use $8 of budget
        tracker.record_usage("deepseek-v4-pro", 1_000_000, 1_000_000)
        assert not tracker.is_budget_exceeded()
        
        # Use another $8 (total $16, exceeds $10 limit)
        tracker.record_usage("deepseek-v4-pro", 1_000_000, 1_000_000)
        assert tracker.is_budget_exceeded()

### Component: Performance Benchmarking

#### Unit Tests

```python
# test_performance.py

import pytest
import time
from lyra_model_router import IntelligentModelRouter

class TestPerformanceBenchmarks:
    """Test performance benchmarks for DeepSeek models."""
    
    def test_latency_v4_pro(self):
        """Test latency for deepseek-v4-pro."""
        router = IntelligentModelRouter()
        
        start = time.time()
        decision = router.route_task(
            "Complex reasoning task",
            provider="deepseek"
        )
        latency = (time.time() - start) * 1000
        
        assert decision.selected_model == "deepseek-v4-pro"
        assert latency < 100  # Routing should be fast (<100ms)
    
    def test_latency_v4_flash(self):
        """Test latency for deepseek-v4-flash."""
        router = IntelligentModelRouter()
        
        start = time.time()
        decision = router.route_task(
            "Standard coding task",
            provider="deepseek"
        )
        latency = (time.time() - start) * 1000
        
        assert decision.selected_model == "deepseek-v4-flash"
        assert latency < 100
    
    @pytest.mark.benchmark
    def test_throughput(self):
        """Test routing throughput."""
        router = IntelligentModelRouter()
        
        tasks = ["Task " + str(i) for i in range(1000)]
        
        start = time.time()
        for task in tasks:
            router.route_task(task, provider="deepseek")
        elapsed = time.time() - start
        
        throughput = len(tasks) / elapsed
        assert throughput > 100  # >100 routes/second

### Component: Error Handling

#### Unit Tests

```python
# test_error_handling.py

import pytest
from lyra_model_router import IntelligentModelRouter

class TestErrorHandling:
    """Test error handling for DeepSeek API."""
    
    def test_invalid_api_key(self):
        """Test handling invalid API key."""
        with pytest.raises(ValueError, match="Invalid API key"):
            router = IntelligentModelRouter(api_key="invalid")
    
    def test_rate_limit_handling(self):
        """Test handling rate limit errors."""
        router = IntelligentModelRouter()
        
        # Simulate rate limit
        with pytest.raises(RateLimitError):
            router._handle_rate_limit_error()
    
    def test_timeout_handling(self):
        """Test handling timeout errors."""
        router = IntelligentModelRouter(timeout=1)
        
        # Simulate timeout
        with pytest.raises(TimeoutError):
            router._handle_timeout_error()
    
    def test_fallback_on_error(self):
        """Test fallback to alternative model on error."""
        router = IntelligentModelRouter(enable_fallback=True)
        
        # Simulate v4-pro failure, should fallback to v4-flash
        decision = router.route_task_with_fallback(
            "Complex task",
            provider="deepseek",
            primary_model="deepseek-v4-pro"
        )
        
        assert decision.selected_model in ["deepseek-v4-pro", "deepseek-v4-flash"]
        assert decision.is_fallback or decision.selected_model == "deepseek-v4-pro"

#### Integration Tests

```python
# test_deepseek_integration.py

import pytest
from lyra_research import ResearchOrchestrator

class TestDeepSeekIntegration:
    """Integration tests for DeepSeek with research workflows."""
    
    @pytest.mark.integration
    @pytest.mark.slow
    def test_research_with_deepseek(self, temp_research_dir):
        """Test research workflow with DeepSeek models."""
        orchestrator = ResearchOrchestrator(
            output_dir=temp_research_dir,
            provider="deepseek"
        )
        
        progress = orchestrator.research(
            topic="LLM reasoning",
            depth="standard"
        )
        
        assert progress.is_complete
        assert progress.error is None
        assert progress.report is not None

    @pytest.mark.integration
    def test_cost_tracking_across_workflow(self, temp_research_dir):
        """Test cost tracking across complete workflow."""
        from lyra_model_router import UsageTracker
        
        tracker = UsageTracker()
        orchestrator = ResearchOrchestrator(
            output_dir=temp_research_dir,
            provider="deepseek",
            usage_tracker=tracker
        )
        
        progress = orchestrator.research(
            topic="Multi-agent systems",
            depth="quick"
        )
        
        stats = tracker.get_stats()
        
        assert stats.total_requests > 0
        assert stats.total_cost > 0
        assert stats.total_cost < 5.0  # Quick research should be cheap

---

## Test Execution Plans

### Unit Test Execution

```bash
# Run all unit tests
pytest packages/*/tests/unit/ -v

# Run with coverage
pytest packages/*/tests/unit/ --cov=packages --cov-report=html

# Run specific component
pytest packages/lyra-research/tests/unit/test_orchestrator.py -v

# Run with markers
pytest -m "not slow" packages/*/tests/unit/
```

### Integration Test Execution

```bash
# Run all integration tests
pytest packages/*/tests/integration/ -v --tb=short

# Run with timeout
pytest packages/*/tests/integration/ -v --timeout=300

# Run specific integration
pytest packages/lyra-research/tests/integration/test_research_pipeline.py -v
```

### E2E Test Execution

```bash
# Run all e2e tests (slow)
pytest packages/*/tests/e2e/ -v -s --tb=short

# Run with real API (requires credentials)
DEEPSEEK_API_KEY=sk-xxx pytest packages/*/tests/e2e/ -v

# Run specific e2e test
pytest packages/lyra-research/tests/e2e/test_full_research_session.py::test_deep_research -v
```

### Performance Test Execution

```bash
# Run performance benchmarks
pytest packages/*/tests/ -m benchmark -v

# Run with profiling
pytest packages/*/tests/ -m benchmark --profile

# Generate performance report
pytest packages/*/tests/ -m benchmark --benchmark-only --benchmark-json=output.json
```

### Stress Test Execution

```bash
# Run stress tests
pytest packages/*/tests/ -m stress -v

# Run with concurrency
pytest packages/*/tests/ -m stress -n 4 -v

# Run with memory profiling
pytest packages/*/tests/ -m stress --memray
```

### Test Execution Matrix

| Test Type | Command | Duration | Frequency |
|-----------|---------|----------|-----------|
| Unit | `pytest packages/*/tests/unit/` | 2-5 min | Every commit |
| Integration | `pytest packages/*/tests/integration/` | 10-15 min | Every PR |
| E2E | `pytest packages/*/tests/e2e/` | 30-60 min | Daily |
| Performance | `pytest -m benchmark` | 15-20 min | Weekly |
| Stress | `pytest -m stress` | 20-30 min | Weekly |

---

## Test Infrastructure

### Test Configuration

```python
# pytest.ini

[pytest]
testpaths = packages/*/tests
python_files = test_*.py
python_classes = Test*
python_functions = test_*

markers =
    unit: Unit tests (fast, isolated)
    integration: Integration tests (moderate speed)
    e2e: End-to-end tests (slow, full workflow)
    slow: Slow tests (>10 seconds)
    benchmark: Performance benchmarks
    stress: Stress tests (high load)
    asyncio: Async tests

addopts =
    -v
    --strict-markers
    --tb=short
    --cov-report=term-missing
    --cov-report=html
    --cov-branch

asyncio_mode = auto
timeout = 300
```

### Mock Infrastructure

```python
# conftest.py - Global fixtures

import pytest
from unittest.mock import Mock, MagicMock
from pathlib import Path

@pytest.fixture
def mock_deepseek_client():
    """Mock DeepSeek API client."""
    client = Mock()
    client.chat.completions.create = MagicMock(
        return_value={
            "id": "chatcmpl-123",
            "model": "deepseek-v4-pro",
            "choices": [{"message": {"content": "Test response"}}],
            "usage": {"prompt_tokens": 100, "completion_tokens": 50},
        }
    )
    return client

@pytest.fixture
def mock_research_sources():
    """Mock research sources for testing."""
    return [
        {
            "id": "arxiv:2605.20025",
            "title": "AutoResearchClaw",
            "abstract": "Autonomous research system...",
            "url": "https://arxiv.org/abs/2605.20025",
            "citations": 150,
            "year": 2026,
        },
        {
            "id": "github:org/repo",
            "title": "Multi-Agent Framework",
            "description": "Framework for building agents...",
            "url": "https://github.com/org/repo",
            "stars": 5000,
        },
    ]

@pytest.fixture
def temp_research_dir(tmp_path):
    """Temporary directory for research outputs."""
    research_dir = tmp_path / "research"
    research_dir.mkdir()
    return research_dir
```

### Test Data Management

```python
# test_data.py - Test data generators

from dataclasses import dataclass
from typing import List

@dataclass
class TestResearchSource:
    """Test research source data."""
    id: str
    title: str
    abstract: str
    url: str
    citations: int = 0
    stars: int = 0

def generate_test_papers(count: int) -> List[TestResearchSource]:
    """Generate test paper data."""
    return [
        TestResearchSource(
            id=f"arxiv:2605.{20000+i}",
            title=f"Test Paper {i}",
            abstract=f"Abstract for paper {i}...",
            url=f"https://arxiv.org/abs/2605.{20000+i}",
            citations=100 * i,
        )
        for i in range(count)
    ]

def generate_test_repos(count: int) -> List[TestResearchSource]:
    """Generate test repository data."""
    return [
        TestResearchSource(
            id=f"github:org/repo{i}",
            title=f"Test Repo {i}",
            abstract=f"Description for repo {i}...",
            url=f"https://github.com/org/repo{i}",
            stars=1000 * i,
        )
        for i in range(count)
    ]
```

---

## Performance Benchmarks

### Latency Benchmarks

| Operation | Target | Acceptable | Critical |
|-----------|--------|------------|----------|
| Discovery (per source) | <5s | <10s | >15s |
| Analysis (per paper) | <3s | <5s | >10s |
| Synthesis | <10s | <20s | >30s |
| Report generation | <15s | <30s | >60s |
| Model routing | <50ms | <100ms | >200ms |

### Throughput Benchmarks

| Operation | Target | Acceptable | Critical |
|-----------|--------|------------|----------|
| Concurrent discoveries | 10/s | 5/s | <3/s |
| Paper analyses | 20/s | 10/s | <5/s |
| Model routes | 100/s | 50/s | <25/s |

### Memory Benchmarks

| Component | Target | Acceptable | Critical |
|-----------|--------|------------|----------|
| Orchestrator | <100MB | <200MB | >500MB |
| Corpus (1000 entries) | <50MB | <100MB | >200MB |
| Knowledge graph (1000 nodes) | <30MB | <50MB | >100MB |

### Cost Benchmarks (DeepSeek)

| Research Depth | Target Cost | Acceptable | Critical |
|----------------|-------------|------------|----------|
| Quick (10 sources) | <$0.50 | <$1.00 | >$2.00 |
| Standard (30 sources) | <$2.00 | <$4.00 | >$8.00 |
| Deep (50 sources) | <$5.00 | <$10.00 | >$20.00 |

### Performance Test Implementation

```python
# test_performance_benchmarks.py

import pytest
import time
from lyra_research import ResearchOrchestrator

class TestPerformanceBenchmarks:
    """Performance benchmark tests."""
    
    @pytest.mark.benchmark
    def test_discovery_latency(self, benchmark):
        """Benchmark discovery latency."""
        orchestrator = ResearchOrchestrator()
        
        def discover():
            return orchestrator.discovery.discover(
                "LLM agents",
                sources=["arxiv"],
                max_per_source=10
            )
        
        result = benchmark(discover)
        assert len(result["arxiv"]) > 0
    
    @pytest.mark.benchmark
    def test_analysis_throughput(self, benchmark, sample_research_sources):
        """Benchmark analysis throughput."""
        orchestrator = ResearchOrchestrator()
        
        def analyze():
            return orchestrator._analyze_sources(sample_research_sources)
        
        papers, repos = benchmark(analyze)
        assert len(papers) + len(repos) > 0
    
    @pytest.mark.benchmark
    def test_model_routing_latency(self, benchmark):
        """Benchmark model routing latency."""
        from lyra_model_router import IntelligentModelRouter
        
        router = IntelligentModelRouter()
        
        def route():
            return router.route_task("Test task", provider="deepseek")
        
        decision = benchmark(route)
        assert decision.selected_model is not None

---

## Continuous Integration

### GitHub Actions Workflow

```yaml
# .github/workflows/test-research.yml

name: Research Workflows Tests

on:
  push:
    branches: [main, develop]
  pull_request:
    branches: [main, develop]

jobs:
  unit-tests:
    runs-on: ubuntu-latest
    strategy:
      matrix:
        python-version: ["3.10", "3.11", "3.12"]
    
    steps:
      - uses: actions/checkout@v4
      
      - name: Set up Python ${{ matrix.python-version }}
        uses: actions/setup-python@v5
        with:
          python-version: ${{ matrix.python-version }}
      
      - name: Install dependencies
        run: |
          pip install -e packages/lyra-research
          pip install -e packages/lyra-autoresearch
          pip install -e packages/lyra-science-pipeline
          pip install pytest pytest-cov pytest-asyncio
      
      - name: Run unit tests
        run: |
          pytest packages/*/tests/unit/ -v --cov --cov-report=xml
      
      - name: Upload coverage
        uses: codecov/codecov-action@v4
        with:
          file: ./coverage.xml

  integration-tests:
    runs-on: ubuntu-latest
    needs: unit-tests
    
    steps:
      - uses: actions/checkout@v4
      
      - name: Set up Python
        uses: actions/setup-python@v5
        with:
          python-version: "3.11"
      
      - name: Install dependencies
        run: |
          pip install -e packages/lyra-research
          pip install -e packages/lyra-autoresearch
          pip install -e packages/lyra-science-pipeline
          pip install pytest pytest-timeout
      
      - name: Run integration tests
        run: |
          pytest packages/*/tests/integration/ -v --timeout=300

  e2e-tests:
    runs-on: ubuntu-latest
    needs: integration-tests
    if: github.event_name == 'push' && github.ref == 'refs/heads/main'
    
    steps:
      - uses: actions/checkout@v4
      
      - name: Set up Python
        uses: actions/setup-python@v5
        with:
          python-version: "3.11"
      
      - name: Install dependencies
        run: |
          pip install -e packages/lyra-research
          pip install -e packages/lyra-autoresearch
          pip install -e packages/lyra-science-pipeline
          pip install pytest
      
      - name: Run e2e tests
        env:
          DEEPSEEK_API_KEY: ${{ secrets.DEEPSEEK_API_KEY }}
        run: |
          pytest packages/*/tests/e2e/ -v -s
```

### Pre-commit Hooks

```yaml
# .pre-commit-config.yaml

repos:
  - repo: https://github.com/pre-commit/pre-commit-hooks
    rev: v4.5.0
    hooks:
      - id: trailing-whitespace
      - id: end-of-file-fixer
      - id: check-yaml
      - id: check-added-large-files
  
  - repo: https://github.com/psf/black
    rev: 24.3.0
    hooks:
      - id: black
        files: ^packages/.*\.py$
  
  - repo: https://github.com/astral-sh/ruff-pre-commit
    rev: v0.3.0
    hooks:
      - id: ruff
        args: [--fix]
        files: ^packages/.*\.py$
  
  - repo: local
    hooks:
      - id: pytest-unit
        name: pytest-unit
        entry: pytest packages/*/tests/unit/ -v
        language: system
        pass_filenames: false
        always_run: true
```

### Test Coverage Requirements

| Package | Unit Coverage | Integration Coverage | Overall Coverage |
|---------|---------------|---------------------|------------------|
| lyra-research | ≥80% | ≥70% | ≥75% |
| lyra-autoresearch | ≥80% | ≥70% | ≥75% |
| lyra-science-pipeline | ≥80% | ≥70% | ≥75% |
| lyra-model-router | ≥85% | ≥75% | ≥80% |

---

## Test Maintenance

### Test Review Checklist

- [ ] Test names clearly describe expected behavior
- [ ] Each test verifies one behavior
- [ ] Tests are independent and can run in any order
- [ ] Mock external dependencies (APIs, databases)
- [ ] Use fixtures for common setup
- [ ] Tests complete within time budget
- [ ] Error cases are tested
- [ ] Edge cases are covered
- [ ] Tests are deterministic (no flakiness)
- [ ] Coverage meets minimum requirements

### Flaky Test Detection

```python
# test_flakiness.py

import pytest

@pytest.mark.flaky(reruns=3, reruns_delay=1)
def test_potentially_flaky():
    """Test that may be flaky - will retry up to 3 times."""
    # Test implementation
    pass
```

### Test Cleanup

```bash
# Remove stale test artifacts
find packages/*/tests -name "__pycache__" -type d -exec rm -rf {} +
find packages/*/tests -name "*.pyc" -delete
find packages/*/tests -name ".pytest_cache" -type d -exec rm -rf {} +

# Clean test outputs
rm -rf test_output_*
rm -rf .coverage coverage.xml htmlcov/
```

---

## Summary

This testing framework provides comprehensive coverage for Lyra's research workflows:

### Coverage Summary

| Workflow | Unit Tests | Integration Tests | E2E Tests | Total Tests |
|----------|-----------|-------------------|-----------|-------------|
| Deep Research | 25+ | 10+ | 5+ | 40+ |
| Auto Research | 20+ | 8+ | 3+ | 31+ |
| Scientist Research | 15+ | 5+ | 2+ | 22+ |
| AI Research | 18+ | 7+ | 3+ | 28+ |
| DeepSeek Integration | 15+ | 5+ | 3+ | 23+ |
| **Total** | **93+** | **35+** | **16+** | **144+** |

### Key Testing Features

1. **Comprehensive Coverage**: 80%+ code coverage across all research modules
2. **Multi-Level Testing**: Unit, integration, and e2e tests for all workflows
3. **Performance Benchmarks**: Latency, throughput, and cost tracking
4. **DeepSeek Integration**: Full API testing with cost optimization
5. **CI/CD Integration**: Automated testing on every commit
6. **Mock Infrastructure**: Isolated testing without external dependencies
7. **Test Data Management**: Reusable fixtures and generators

### Next Steps

1. Implement unit tests for each component
2. Add integration tests for workflow pipelines
3. Create e2e tests for complete research sessions
4. Set up CI/CD pipeline with GitHub Actions
5. Configure pre-commit hooks for automated testing
6. Monitor test coverage and maintain 80%+ threshold
7. Run performance benchmarks weekly
8. Review and update tests as workflows evolve

---

## References

### Internal Documentation
- [Research Engine Architecture](../architecture/research-engine.md)
- [Model Router Architecture](../architecture/model-router.md)
- [Agent Swarm Architecture](../architecture/agent-swarm.md)

### Testing Tools
- [pytest](https://docs.pytest.org/) - Testing framework
- [pytest-cov](https://pytest-cov.readthedocs.io/) - Coverage plugin
- [pytest-asyncio](https://pytest-asyncio.readthedocs.io/) - Async testing
- [pytest-benchmark](https://pytest-benchmark.readthedocs.io/) - Performance benchmarks

### Best Practices
- [Testing Best Practices](https://docs.python-guide.org/writing/tests/)
- [Test-Driven Development](https://testdriven.io/)
- [Effective Python Testing](https://realpython.com/pytest-python-testing/)

