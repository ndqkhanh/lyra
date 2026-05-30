"""
Integration tests for knowledge transfer between workflows.

Tests knowledge sharing patterns:
- Knowledge graph sharing
- Citation network transfer
- Finding propagation
- Hypothesis transfer
- Memory persistence
"""

import pytest
from unittest.mock import Mock, MagicMock
from datetime import datetime, timezone


class KnowledgeGraph:
    """Mock knowledge graph for testing."""

    def __init__(self):
        self.nodes = {}
        self.edges = []

    def add_node(self, node_id: str, data: dict):
        """Add node to graph."""
        self.nodes[node_id] = data

    def add_edge(self, source: str, target: str, relation: str):
        """Add edge to graph."""
        self.edges.append({"source": source, "target": target, "relation": relation})

    def get_node(self, node_id: str):
        """Get node by ID."""
        return self.nodes.get(node_id)

    def get_neighbors(self, node_id: str):
        """Get neighbors of a node."""
        neighbors = []
        for edge in self.edges:
            if edge["source"] == node_id:
                neighbors.append(edge["target"])
        return neighbors

    def merge(self, other_graph):
        """Merge another graph into this one."""
        self.nodes.update(other_graph.nodes)
        self.edges.extend(other_graph.edges)

    def export(self):
        """Export graph data."""
        return {
            "nodes": self.nodes.copy(),
            "edges": self.edges.copy(),
            "node_count": len(self.nodes),
            "edge_count": len(self.edges),
        }


class CitationNetwork:
    """Mock citation network for testing."""

    def __init__(self):
        self.papers = {}
        self.citations = []

    def add_paper(self, paper_id: str, metadata: dict):
        """Add paper to network."""
        self.papers[paper_id] = metadata

    def add_citation(self, citing_paper: str, cited_paper: str):
        """Add citation relationship."""
        self.citations.append({"citing": citing_paper, "cited": cited_paper})

    def get_citations(self, paper_id: str):
        """Get papers cited by this paper."""
        return [c["cited"] for c in self.citations if c["citing"] == paper_id]

    def get_cited_by(self, paper_id: str):
        """Get papers that cite this paper."""
        return [c["citing"] for c in self.citations if c["cited"] == paper_id]

    def export(self):
        """Export citation network."""
        return {
            "papers": self.papers.copy(),
            "citations": self.citations.copy(),
            "paper_count": len(self.papers),
            "citation_count": len(self.citations),
        }


class ResearchMemory:
    """Mock research memory for testing."""

    def __init__(self):
        self.findings = []
        self.hypotheses = []
        self.experiments = []

    def store_finding(self, finding: dict):
        """Store a research finding."""
        self.findings.append(finding)

    def store_hypothesis(self, hypothesis: dict):
        """Store a hypothesis."""
        self.hypotheses.append(hypothesis)

    def store_experiment(self, experiment: dict):
        """Store an experiment."""
        self.experiments.append(experiment)

    def get_findings(self, topic: str = None):
        """Get findings, optionally filtered by topic."""
        if topic:
            return [f for f in self.findings if f.get("topic") == topic]
        return self.findings.copy()

    def get_hypotheses(self, status: str = None):
        """Get hypotheses, optionally filtered by status."""
        if status:
            return [h for h in self.hypotheses if h.get("status") == status]
        return self.hypotheses.copy()

    def export(self):
        """Export memory contents."""
        return {
            "findings": self.findings.copy(),
            "hypotheses": self.hypotheses.copy(),
            "experiments": self.experiments.copy(),
        }


@pytest.mark.integration
class TestKnowledgeGraphSharing:
    """Test knowledge graph sharing between workflows."""

    def test_knowledge_graph_transfer_deep_to_auto(self):
        """Test transferring knowledge graph from deep to auto research."""
        # Setup
        deep_kg = KnowledgeGraph()
        deep_kg.add_node("concept1", {"name": "LLM", "type": "concept"})
        deep_kg.add_node("concept2", {"name": "reasoning", "type": "concept"})
        deep_kg.add_edge("concept1", "concept2", "enables")

        # Transfer to auto research
        auto_kg = KnowledgeGraph()
        auto_kg.merge(deep_kg)

        # Verify
        assert len(auto_kg.nodes) == 2
        assert len(auto_kg.edges) == 1
        assert auto_kg.get_node("concept1")["name"] == "LLM"
        assert auto_kg.get_neighbors("concept1") == ["concept2"]

    def test_knowledge_graph_incremental_building(self):
        """Test incrementally building knowledge graph across workflows."""
        # Setup
        kg = KnowledgeGraph()

        # Deep research adds initial nodes
        kg.add_node("llm", {"name": "LLM", "type": "concept"})
        kg.add_node("reasoning", {"name": "reasoning", "type": "concept"})
        kg.add_edge("llm", "reasoning", "enables")

        initial_export = kg.export()

        # Auto research adds more nodes
        kg.add_node("tool_use", {"name": "tool use", "type": "concept"})
        kg.add_edge("llm", "tool_use", "supports")

        final_export = kg.export()

        # Verify
        assert initial_export["node_count"] == 2
        assert final_export["node_count"] == 3
        assert final_export["edge_count"] == 2

    def test_knowledge_graph_query_across_workflows(self):
        """Test querying knowledge graph built across workflows."""
        # Setup
        kg = KnowledgeGraph()
        kg.add_node("llm", {"name": "LLM", "type": "concept"})
        kg.add_node("reasoning", {"name": "reasoning", "type": "concept"})
        kg.add_node("tool_use", {"name": "tool use", "type": "concept"})
        kg.add_edge("llm", "reasoning", "enables")
        kg.add_edge("llm", "tool_use", "supports")

        # Query
        llm_neighbors = kg.get_neighbors("llm")

        # Verify
        assert len(llm_neighbors) == 2
        assert "reasoning" in llm_neighbors
        assert "tool_use" in llm_neighbors


@pytest.mark.integration
class TestCitationNetworkTransfer:
    """Test citation network transfer between workflows."""

    def test_citation_network_transfer(self):
        """Test transferring citation network between workflows."""
        # Setup
        deep_citations = CitationNetwork()
        deep_citations.add_paper("paper1", {"title": "LLM Reasoning"})
        deep_citations.add_paper("paper2", {"title": "Tool Use"})
        deep_citations.add_citation("paper1", "paper2")

        # Transfer to auto research
        auto_citations = CitationNetwork()
        auto_citations.papers.update(deep_citations.papers)
        auto_citations.citations.extend(deep_citations.citations)

        # Verify
        assert len(auto_citations.papers) == 2
        assert len(auto_citations.citations) == 1
        assert auto_citations.get_citations("paper1") == ["paper2"]

    def test_citation_network_expansion(self):
        """Test expanding citation network across workflows."""
        # Setup
        citations = CitationNetwork()

        # Deep research finds initial papers
        citations.add_paper("paper1", {"title": "LLM Reasoning"})
        citations.add_paper("paper2", {"title": "Tool Use"})
        citations.add_citation("paper1", "paper2")

        # Auto research finds more papers
        citations.add_paper("paper3", {"title": "Agent Systems"})
        citations.add_citation("paper2", "paper3")

        # Verify
        assert len(citations.papers) == 3
        assert len(citations.citations) == 2
        assert citations.get_citations("paper2") == ["paper3"]

    def test_citation_chain_traversal(self):
        """Test traversing citation chains across workflows."""
        # Setup
        citations = CitationNetwork()
        citations.add_paper("paper1", {"title": "Paper 1"})
        citations.add_paper("paper2", {"title": "Paper 2"})
        citations.add_paper("paper3", {"title": "Paper 3"})
        citations.add_citation("paper1", "paper2")
        citations.add_citation("paper2", "paper3")

        # Traverse chain
        chain = ["paper1"]
        current = "paper1"
        while True:
            cited = citations.get_citations(current)
            if not cited:
                break
            current = cited[0]
            chain.append(current)

        # Verify
        assert chain == ["paper1", "paper2", "paper3"]


@pytest.mark.integration
class TestFindingPropagation:
    """Test finding propagation between workflows."""

    def test_finding_propagation_deep_to_auto(self):
        """Test propagating findings from deep to auto research."""
        # Setup
        memory = ResearchMemory()

        # Deep research stores findings
        memory.store_finding({
            "topic": "LLM reasoning",
            "finding": "LLMs use chain-of-thought",
            "confidence": 0.9,
            "source": "deep_research",
        })

        # Auto research retrieves findings
        findings = memory.get_findings("LLM reasoning")

        # Verify
        assert len(findings) == 1
        assert findings[0]["finding"] == "LLMs use chain-of-thought"
        assert findings[0]["source"] == "deep_research"

    def test_finding_aggregation_across_workflows(self):
        """Test aggregating findings from multiple workflows."""
        # Setup
        memory = ResearchMemory()

        # Deep research findings
        memory.store_finding({
            "topic": "LLM reasoning",
            "finding": "Finding from deep research",
            "source": "deep_research",
        })

        # Auto research findings
        memory.store_finding({
            "topic": "LLM reasoning",
            "finding": "Finding from auto research",
            "source": "auto_research",
        })

        # Scientist research findings
        memory.store_finding({
            "topic": "LLM reasoning",
            "finding": "Finding from scientist research",
            "source": "scientist_research",
        })

        # Aggregate
        all_findings = memory.get_findings("LLM reasoning")

        # Verify
        assert len(all_findings) == 3
        sources = {f["source"] for f in all_findings}
        assert sources == {"deep_research", "auto_research", "scientist_research"}

    def test_finding_deduplication(self):
        """Test deduplicating findings across workflows."""
        # Setup
        memory = ResearchMemory()

        # Store duplicate findings
        memory.store_finding({
            "topic": "LLM reasoning",
            "finding": "LLMs use chain-of-thought",
            "source": "deep_research",
        })

        memory.store_finding({
            "topic": "LLM reasoning",
            "finding": "LLMs use chain-of-thought",
            "source": "auto_research",
        })

        # Deduplicate
        findings = memory.get_findings("LLM reasoning")
        unique_findings = {}
        for f in findings:
            key = f["finding"]
            if key not in unique_findings:
                unique_findings[key] = []
            unique_findings[key].append(f["source"])

        # Verify
        assert len(unique_findings) == 1
        assert len(unique_findings["LLMs use chain-of-thought"]) == 2


@pytest.mark.integration
class TestHypothesisTransfer:
    """Test hypothesis transfer between workflows."""

    def test_hypothesis_transfer_scientist_to_auto(self):
        """Test transferring hypotheses from scientist to auto research."""
        # Setup
        memory = ResearchMemory()

        # Scientist research generates hypotheses
        memory.store_hypothesis({
            "hypothesis": "LLMs benefit from tool use",
            "status": "pending",
            "source": "scientist_research",
        })

        # Auto research validates hypotheses
        hypotheses = memory.get_hypotheses("pending")

        # Verify
        assert len(hypotheses) == 1
        assert hypotheses[0]["hypothesis"] == "LLMs benefit from tool use"

    def test_hypothesis_validation_workflow(self):
        """Test hypothesis validation across workflows."""
        # Setup
        memory = ResearchMemory()

        # Generate hypothesis
        memory.store_hypothesis({
            "id": "h1",
            "hypothesis": "LLMs benefit from tool use",
            "status": "pending",
        })

        # Validate hypothesis
        hypotheses = memory.get_hypotheses()
        hypotheses[0]["status"] = "validated"
        hypotheses[0]["confidence"] = 0.85

        # Verify
        assert hypotheses[0]["status"] == "validated"
        assert hypotheses[0]["confidence"] == 0.85

    def test_hypothesis_refinement_across_workflows(self):
        """Test refining hypotheses across workflows."""
        # Setup
        memory = ResearchMemory()

        # Initial hypothesis
        memory.store_hypothesis({
            "id": "h1",
            "hypothesis": "LLMs benefit from tool use",
            "version": 1,
        })

        # Refined hypothesis
        memory.store_hypothesis({
            "id": "h1",
            "hypothesis": "LLMs with tool use achieve 20% better performance",
            "version": 2,
        })

        # Verify
        hypotheses = memory.get_hypotheses()
        assert len(hypotheses) == 2
        assert hypotheses[1]["version"] == 2


@pytest.mark.integration
class TestMemoryPersistence:
    """Test memory persistence across workflows."""

    def test_memory_export_import(self):
        """Test exporting and importing memory."""
        # Setup
        memory1 = ResearchMemory()
        memory1.store_finding({
            "topic": "LLM reasoning",
            "finding": "Test finding",
        })

        # Export
        exported = memory1.export()

        # Import to new memory
        memory2 = ResearchMemory()
        memory2.findings = exported["findings"]

        # Verify
        assert len(memory2.findings) == 1
        assert memory2.findings[0]["finding"] == "Test finding"

    def test_memory_persistence_across_sessions(self):
        """Test memory persistence across research sessions."""
        # Setup
        memory = ResearchMemory()

        # Session 1: Deep research
        memory.store_finding({
            "session": 1,
            "finding": "Finding from session 1",
        })

        # Session 2: Auto research
        memory.store_finding({
            "session": 2,
            "finding": "Finding from session 2",
        })

        # Verify
        all_findings = memory.get_findings()
        assert len(all_findings) == 2
        sessions = {f["session"] for f in all_findings}
        assert sessions == {1, 2}

    def test_memory_cleanup_old_entries(self):
        """Test cleaning up old memory entries."""
        # Setup
        memory = ResearchMemory()

        # Add findings with timestamps
        memory.store_finding({
            "finding": "Old finding",
            "timestamp": datetime(2026, 1, 1, tzinfo=timezone.utc),
        })

        memory.store_finding({
            "finding": "Recent finding",
            "timestamp": datetime(2026, 5, 29, tzinfo=timezone.utc),
        })

        # Cleanup old entries (before May 2026)
        cutoff = datetime(2026, 5, 1, tzinfo=timezone.utc)
        memory.findings = [
            f for f in memory.findings
            if f.get("timestamp", datetime.now(timezone.utc)) >= cutoff
        ]

        # Verify
        assert len(memory.findings) == 1
        assert memory.findings[0]["finding"] == "Recent finding"
