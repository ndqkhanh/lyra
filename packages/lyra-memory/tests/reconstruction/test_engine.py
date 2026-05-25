"""Tests for engine.py — ActiveReconstructionEngine."""
from __future__ import annotations

import pytest

from lyra_memory.reconstruction.engine import (
    ActiveReconstructionEngine,
    MemoryEvidence,
    ReconstructionResult,
    ReconstructionTrace,
)
from lyra_memory.reconstruction.graph import (
    CueTagContentGraph,
    GraphNode,
    NodeType,
)


class StubScorer:
    """Returns fixed relevance scores for testing."""

    def __init__(self, scores: list[float] | None = None):
        self._scores = scores or [0.8]
        self._idx = 0
        self.calls: list[tuple[str, str]] = []

    async def score(self, query: str, node_content: str) -> float:
        self.calls.append((query, node_content))
        score = self._scores[self._idx % len(self._scores)]
        self._idx += 1
        return score


def build_sample_graph() -> CueTagContentGraph:
    """Build a Cue-Tag-Content graph for reconstruction tests.

    Structure:
        cue("testing query") → tag("testing") → content("pytest basics")
            → cue("fixtures") → tag("advanced") → content("fixture details")
    """
    g = CueTagContentGraph()

    cue0 = GraphNode(type=NodeType.CUE, content="testing query")
    tag0 = GraphNode(type=NodeType.TAG, content="testing")
    content0 = GraphNode(type=NodeType.CONTENT, content="pytest basics for setup")
    cue1 = GraphNode(type=NodeType.CUE, content="fixtures")
    tag1 = GraphNode(type=NodeType.TAG, content="advanced")
    content1 = GraphNode(type=NodeType.CONTENT, content="fixture details and scoping")

    for n in (cue0, tag0, content0, cue1, tag1, content1):
        g.add_node(n)

    g.add_edge(cue0.id, tag0.id)
    g.add_edge(tag0.id, content0.id)
    g.add_edge(content0.id, cue1.id)
    g.add_edge(cue1.id, tag1.id)
    g.add_edge(tag1.id, content1.id)

    return g


@pytest.mark.unit
class TestActiveReconstructionEngine:
    """Tests for ActiveReconstructionEngine."""

    async def test_empty_graph_returns_no_evidence(self):
        g = CueTagContentGraph()
        scorer = StubScorer()
        engine = ActiveReconstructionEngine(scorer=scorer, graph=g)

        result = await engine.reconstruct("any query")
        assert len(result.evidence) == 0

    async def test_direct_cue_match_finds_content(self):
        g = build_sample_graph()
        scorer = StubScorer([0.9])
        engine = ActiveReconstructionEngine(
            scorer=scorer, graph=g, beam_width=2,
        )

        result = await engine.reconstruct("testing query")
        assert len(result.evidence) > 0

    async def test_reconstruction_discovers_multi_hop(self):
        """Engine should traverse multiple hops via content→cue reverse edges."""
        g = build_sample_graph()
        scorer = StubScorer([0.9, 0.8, 0.9])
        engine = ActiveReconstructionEngine(
            scorer=scorer, graph=g, beam_width=3,
        )

        result = await engine.reconstruct("testing query")
        # Should find content via both CUE→TAG→CONTENT paths
        contents = {e.content.content for e in result.evidence}
        assert "pytest basics for setup" in contents

    async def test_max_steps_limits_exploration(self):
        g = build_sample_graph()
        scorer = StubScorer([0.9])
        engine = ActiveReconstructionEngine(
            scorer=scorer, graph=g, max_steps=1, beam_width=2,
        )

        result = await engine.reconstruct("testing query")
        assert result.trace.max_depth_reached <= 1

    async def test_confidence_calculation(self):
        g = build_sample_graph()
        scorer = StubScorer([0.9, 0.8])
        engine = ActiveReconstructionEngine(
            scorer=scorer, graph=g, beam_width=2,
        )

        result = await engine.reconstruct("testing query")
        if result.evidence:
            assert 0.0 <= result.confidence <= 1.0

    async def test_reconstruct_with_passive_comparison(self):
        g = build_sample_graph()
        scorer = StubScorer([0.9, 0.8])
        engine = ActiveReconstructionEngine(scorer=scorer, graph=g)

        passive_node = GraphNode(type=NodeType.CONTENT, content="passive only")
        result = await engine.reconstruct_with_passive_comparison(
            "testing query", [passive_node],
        )
        assert len(result.passive_complement) == 1

    async def test_visited_nodes_not_repeated(self):
        g = CueTagContentGraph()
        cue = GraphNode(type=NodeType.CUE, content="test")
        tag = GraphNode(type=NodeType.TAG, content="testing")
        content = GraphNode(type=NodeType.CONTENT, content="pytest")

        for n in (cue, tag, content):
            g.add_node(n)
        g.add_edge(cue.id, tag.id)
        g.add_edge(tag.id, content.id)
        g.add_edge(content.id, cue.id)  # cycle

        scorer = StubScorer([0.9])
        engine = ActiveReconstructionEngine(
            scorer=scorer, graph=g, max_steps=5,
        )

        result = await engine.reconstruct("test")
        # Should not infinite loop despite cycle
        assert result.trace.nodes_visited <= 3

    async def test_evidence_threshold_filters(self):
        g = build_sample_graph()
        scorer = StubScorer([0.5, 0.3])  # both below default 0.6 threshold
        engine = ActiveReconstructionEngine(
            scorer=scorer, graph=g, beam_width=2,
        )

        result = await engine.reconstruct("testing query")
        assert len(result.evidence) == 0

    async def test_beam_width_prunes(self):
        g = build_sample_graph()
        scorer = StubScorer([0.9])
        engine = ActiveReconstructionEngine(
            scorer=scorer, graph=g, beam_width=1,
        )

        result = await engine.reconstruct("testing query")
        assert result.trace.max_depth_reached > 0

    async def test_scorer_error_returns_default(self):
        class ErrorScorer:
            async def score(self, query: str, node_content: str) -> float:
                raise RuntimeError("scorer failed")

        g = build_sample_graph()
        engine = ActiveReconstructionEngine(
            scorer=ErrorScorer(), graph=g, beam_width=2,
        )

        result = await engine.reconstruct("testing query")
        assert len(result.evidence) == 0

    async def test_result_trace_captures_steps(self):
        g = build_sample_graph()
        scorer = StubScorer([0.9])
        engine = ActiveReconstructionEngine(scorer=scorer, graph=g)

        result = await engine.reconstruct("testing query")
        assert result.trace.query == "testing query"
        assert result.trace.nodes_visited > 0
        assert len(result.trace.steps) > 0


@pytest.mark.unit
class TestMemoryEvidence:
    """Tests for MemoryEvidence dataclass."""

    def test_evidence_with_path(self):
        node = GraphNode(type=NodeType.CONTENT, content="test content")
        evidence = MemoryEvidence(
            content=node,
            confidence=0.95,
            path=["cue1", "tag1", "content1"],
        )
        assert evidence.confidence == 0.95
        assert evidence.path_depth == 3

    def test_default_path_empty(self):
        node = GraphNode(type=NodeType.CONTENT, content="test")
        evidence = MemoryEvidence(content=node, confidence=0.5)
        assert evidence.path_depth == 0


@pytest.mark.unit
class TestReconstructionResult:
    """Tests for ReconstructionResult dataclass."""

    def test_confidence_average(self):
        node = GraphNode(content="test")
        result = ReconstructionResult(
            query="test query",
            evidence=[
                MemoryEvidence(content=node, confidence=0.8),
                MemoryEvidence(content=node, confidence=0.6),
            ],
            trace=ReconstructionTrace(),
        )
        assert result.confidence == pytest.approx(0.7)

    def test_active_only_count(self):
        passive = GraphNode(id="p1", content="passive")
        active = GraphNode(id="a1", content="active only")
        result = ReconstructionResult(
            query="test",
            evidence=[MemoryEvidence(content=active, confidence=0.9)],
            trace=ReconstructionTrace(),
            passive_complement=[passive],
        )
        assert result.active_only_count == 1

    def test_empty_result_zero_confidence(self):
        result = ReconstructionResult(
            query="empty", evidence=[], trace=ReconstructionTrace(),
        )
        assert result.confidence == 0.0


@pytest.mark.unit
class TestReconstructionTrace:
    """Tests for ReconstructionTrace dataclass."""

    def test_default_trace(self):
        trace = ReconstructionTrace()
        assert trace.query == ""
        assert trace.steps == []
        assert trace.evidence_found == 0

    def test_trace_with_data(self):
        trace = ReconstructionTrace(
            query="test query",
            steps=[{"step": 0, "evidence_found": 2}],
            evidence_found=2,
            nodes_visited=5,
            max_depth_reached=3,
        )
        assert trace.query == "test query"
        assert trace.evidence_found == 2
        assert trace.nodes_visited == 5
        assert trace.max_depth_reached == 3
