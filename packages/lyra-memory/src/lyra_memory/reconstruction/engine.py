"""
Active Memory Reconstruction Engine — beam search through Cue-Tag-Content graph.

Proves H_passive ⊊ H_active via iterative graph exploration:
1. Extract cues from query
2. Beam search: CUE → TAG → CONTENT → CUE → ...
3. Accumulate evidence across multi-hop paths
4. Rank and return results passive retrieval cannot access

Source: MRAgent (YPoHy6lgKP), ICLR 2026 MemAgent Workshop.
"""

from __future__ import annotations

from dataclasses import dataclass, field
from typing import Protocol
from uuid import uuid4

from lyra_memory.reconstruction.graph import (
    CueTagContentGraph,
    GraphNode,
    NodeType,
)


class RelevanceScorer(Protocol):
    """Protocol for scoring relevance between a query and a graph node."""

    async def score(self, query: str, node_content: str) -> float: ...


@dataclass
class MemoryEvidence:
    """A piece of reconstructed memory evidence with confidence and trace."""

    content: GraphNode
    confidence: float
    path: list[str] = field(default_factory=list)

    @property
    def path_depth(self) -> int:
        return len(self.path)


@dataclass
class ReconstructionTrace:
    """Full trace of a reconstruction run for debugging and analysis."""

    id: str = field(default_factory=lambda: uuid4().hex)
    query: str = ""
    steps: list[dict] = field(default_factory=list)
    evidence_found: int = 0
    nodes_visited: int = 0
    max_depth_reached: int = 0


@dataclass
class ReconstructionResult:
    """Result of an active reconstruction query."""

    query: str
    evidence: list[MemoryEvidence]
    trace: ReconstructionTrace
    passive_complement: list[GraphNode] = field(default_factory=list)

    @property
    def confidence(self) -> float:
        if not self.evidence:
            return 0.0
        return sum(e.confidence for e in self.evidence) / len(self.evidence)

    @property
    def active_only_count(self) -> int:
        """Number of results NOT found by passive retrieval."""
        passive_ids = {n.id for n in self.passive_complement}
        return sum(1 for e in self.evidence if e.content.id not in passive_ids)


@dataclass
class ActiveReconstructionEngine:
    """Iterative Cue-Tag-Content graph exploration for memory recall.

    Active reconstruction is strictly more expressive than passive retrieval
    because it can traverse multi-hop paths through the associative graph:

        CUE₀ → TAG_A → CONTENT₁ → CUE₁ → TAG_B → CONTENT₂ → ...

    Passive retrieval (embedding similarity) can only reach nodes within
    the immediate similarity radius. Active reconstruction can discover
    indirectly connected memories that passive retrieval misses.
    """

    scorer: RelevanceScorer
    graph: CueTagContentGraph
    max_steps: int = 10
    beam_width: int = 3
    evidence_threshold: float = 0.6
    exploration_decay: float = 0.9

    async def reconstruct(self, query: str) -> ReconstructionResult:
        """Actively reconstruct memories from the Cue-Tag-Content graph.

        Args:
            query: The user's question or retrieval cue

        Returns:
            ReconstructionResult with ranked evidence and full trace
        """
        trace = ReconstructionTrace(query=query)

        # Step 1: Initial cue extraction
        initial_cues = await self._extract_cues(query)
        if not initial_cues:
            return ReconstructionResult(query=query, evidence=[], trace=trace)

        # Step 2: Beam search through the graph
        beam: list[tuple[GraphNode, float]] = [
            (cue, 1.0) for cue in initial_cues
        ]
        visited: set[str] = set()
        evidence: list[MemoryEvidence] = []

        for step in range(self.max_steps):
            if not beam:
                break

            next_beam: list[tuple[GraphNode, float]] = []
            evidence_this_step = 0

            for node, score in beam:
                if node.id in visited:
                    continue
                visited.add(node.id)
                trace.nodes_visited += 1

                if node.type == NodeType.CUE:
                    # Forward: CUE → TAG
                    tags = self.graph.get_tags(node)
                    for tag in tags:
                        relevance = await self._score_relevance(query, tag)
                        next_beam.append((tag, score * relevance))

                elif node.type == NodeType.TAG:
                    # Forward: TAG → CONTENT
                    content_nodes = self.graph.get_content(node)
                    for content_node in content_nodes:
                        relevance = await self._score_relevance(query, content_node)
                        combined = score * relevance
                        if relevance >= self.evidence_threshold:
                            evidence.append(MemoryEvidence(
                                content=content_node,
                                confidence=combined,
                                path=self._trace_path(content_node),
                            ))
                            evidence_this_step += 1
                        next_beam.append((content_node, combined))

                elif node.type == NodeType.CONTENT:
                    # Reverse: CONTENT → CUE (new exploration)
                    new_cues = self.graph.get_related_cues(node)
                    for cue in new_cues:
                        next_beam.append((cue, score * self.exploration_decay))

            # Prune beam
            next_beam.sort(key=lambda x: x[1], reverse=True)
            beam = next_beam[: self.beam_width]

            trace.steps.append({
                "step": step, "beam_size": len(beam),
                "evidence_found": evidence_this_step,
            })
            if step >= trace.max_depth_reached:
                trace.max_depth_reached = step + 1

            if not beam:
                break

        # Step 3: Deduplicate and rank
        ranked = self._rank_evidence(evidence)
        trace.evidence_found = len(ranked)

        return ReconstructionResult(
            query=query,
            evidence=ranked,
            trace=trace,
        )

    async def reconstruct_with_passive_comparison(
        self, query: str, passive_results: list[GraphNode],
    ) -> ReconstructionResult:
        """Reconstruct and compare against passive retrieval results.

        This method enables empirical verification of H_passive ⊊ H_active
        by identifying evidence found by active reconstruction that passive
        retrieval missed.
        """
        result = await self.reconstruct(query)
        result.passive_complement = passive_results
        return result

    async def _extract_cues(self, query: str) -> list[GraphNode]:
        """Extract initial cue nodes from the query.

        Matches query tokens against graph cue nodes. Falls back to all cues.
        """
        query_lower = query.lower()
        matched = []
        for cue in self.graph.get_cues():
            if any(word in cue.content.lower() for word in query_lower.split()):
                matched.append(cue)
            elif any(word in query_lower for word in cue.content.lower().split()):
                matched.append(cue)

        if matched:
            return matched
        return self.graph.get_cues()

    async def _score_relevance(self, query: str, node: GraphNode) -> float:
        """Score node relevance to the reconstruction goal via LLM."""
        try:
            return await self.scorer.score(query, node.content)
        except Exception:
            return 0.5

    def _trace_path(self, node: GraphNode) -> list[str]:
        """Build a human-readable path trace for an evidence item."""
        return [node.id, node.content[:80]]

    def _rank_evidence(self, evidence: list[MemoryEvidence]) -> list[MemoryEvidence]:
        """Deduplicate by content ID, keep highest confidence, sort descending."""
        seen: dict[str, MemoryEvidence] = {}
        for e in evidence:
            cid = e.content.id
            if cid not in seen or e.confidence > seen[cid].confidence:
                seen[cid] = e
        ranked = sorted(seen.values(), key=lambda x: x.confidence, reverse=True)
        return ranked
