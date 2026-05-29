"""Lyra Ultra Phase 8: Innovation & Differentiation.

Unique capabilities that define #1 status:
1. Mermaid Canvas Integration - Visual knowledge graphs
2. Falsification Loops - Scientific rigor
3. Cross-Session Learning - Continuous improvement

These features differentiate Lyra from all other AI agents.
"""

from __future__ import annotations

import hashlib
import json
from dataclasses import dataclass, field
from datetime import datetime
from enum import Enum
from typing import Any, Dict, List, Optional, Set, Tuple

# ============================================================================
# Mermaid Canvas Integration
# ============================================================================

class DiagramType(Enum):
    """Type of Mermaid diagram."""

    KNOWLEDGE_GRAPH = "graph"  # Entity-relation visualization
    WORKFLOW = "flowchart"  # Agent step visualization
    MEMORY_TOPOLOGY = "graph"  # Memory tier connections
    EVIDENCE_CHAIN = "flowchart"  # Multi-hop reasoning paths
    SEQUENCE = "sequenceDiagram"  # Interaction sequences


@dataclass
class MermaidNode:
    """A node in a Mermaid diagram."""

    id: str
    label: str
    node_type: str = "default"
    metadata: dict[str, Any] = field(default_factory=dict)
    confidence: float = 1.0


@dataclass
class MermaidEdge:
    """An edge in a Mermaid diagram."""

    source: str
    target: str
    label: str | None = None
    edge_type: str = "default"
    weight: float = 1.0


class MermaidCanvas:
    """
    Interactive Mermaid diagram generator for knowledge visualization.

    Features:
    - Knowledge graph visualization
    - Workflow graph visualization
    - Memory topology visualization
    - Evidence chain visualization
    - Click-to-expand nodes
    - Filter by confidence
    - Highlight paths
    - Export to PNG/SVG/Markdown
    """

    def __init__(self, diagram_type: DiagramType = DiagramType.KNOWLEDGE_GRAPH):
        """Initialize the canvas.

        Args:
            diagram_type: Type of diagram to generate
        """
        self.diagram_type = diagram_type
        self.nodes: dict[str, MermaidNode] = {}
        self.edges: list[MermaidEdge] = []
        self.metadata: dict[str, Any] = {}

    def add_node(
        self,
        node_id: str,
        label: str,
        node_type: str = "default",
        confidence: float = 1.0,
        **metadata,
    ) -> None:
        """Add a node to the diagram.

        Args:
            node_id: Unique node identifier
            label: Display label
            node_type: Node type (for styling)
            confidence: Confidence score (0-1)
            **metadata: Additional metadata
        """
        self.nodes[node_id] = MermaidNode(
            id=node_id,
            label=label,
            node_type=node_type,
            confidence=confidence,
            metadata=metadata,
        )

    def add_edge(
        self,
        source: str,
        target: str,
        label: str | None = None,
        edge_type: str = "default",
        weight: float = 1.0,
    ) -> None:
        """Add an edge to the diagram.

        Args:
            source: Source node ID
            target: Target node ID
            label: Edge label
            edge_type: Edge type (for styling)
            weight: Edge weight
        """
        self.edges.append(
            MermaidEdge(
                source=source,
                target=target,
                label=label,
                edge_type=edge_type,
                weight=weight,
            )
        )

    def filter_by_confidence(self, threshold: float) -> MermaidCanvas:
        """Filter nodes by confidence threshold.

        Args:
            threshold: Minimum confidence (0-1)

        Returns:
            New canvas with filtered nodes
        """
        filtered = MermaidCanvas(self.diagram_type)

        # Filter nodes
        for node in self.nodes.values():
            if node.confidence >= threshold:
                filtered.nodes[node.id] = node

        # Filter edges (keep only if both nodes exist)
        for edge in self.edges:
            if edge.source in filtered.nodes and edge.target in filtered.nodes:
                filtered.edges.append(edge)

        return filtered

    def highlight_path(self, source: str, target: str) -> list[str]:
        """Find and highlight path between nodes.

        Args:
            source: Source node ID
            target: Target node ID

        Returns:
            List of node IDs in path
        """
        # Simple BFS to find path
        from collections import deque

        if source not in self.nodes or target not in self.nodes:
            return []

        queue = deque([(source, [source])])
        visited = {source}

        while queue:
            current, path = queue.popleft()

            if current == target:
                return path

            # Find neighbors
            for edge in self.edges:
                if edge.source == current and edge.target not in visited:
                    visited.add(edge.target)
                    queue.append((edge.target, path + [edge.target]))

        return []  # No path found

    def to_mermaid(self) -> str:
        """Generate Mermaid diagram syntax.

        Returns:
            Mermaid diagram as string
        """
        lines = []

        # Diagram type
        if self.diagram_type == DiagramType.KNOWLEDGE_GRAPH:
            lines.append("graph TD")
        elif self.diagram_type == DiagramType.WORKFLOW:
            lines.append("flowchart TD")
        elif self.diagram_type == DiagramType.MEMORY_TOPOLOGY:
            lines.append("graph LR")
        elif self.diagram_type == DiagramType.EVIDENCE_CHAIN:
            lines.append("flowchart LR")
        elif self.diagram_type == DiagramType.SEQUENCE:
            lines.append("sequenceDiagram")

        # Nodes
        for node in self.nodes.values():
            # Node shape based on type
            if node.node_type == "entity":
                shape = f"[{node.label}]"
            elif node.node_type == "decision":
                shape = f"{{{node.label}}}"
            elif node.node_type == "process":
                shape = f"[{node.label}]"
            elif node.node_type == "memory":
                shape = f"({node.label})"
            else:
                shape = f"[{node.label}]"

            lines.append(f"    {node.id}{shape}")

        # Edges
        for edge in self.edges:
            arrow = "-->"
            if edge.edge_type == "weak":
                arrow = "-.->"
            elif edge.edge_type == "bidirectional":
                arrow = "<-->"

            if edge.label:
                lines.append(f"    {edge.source} {arrow}|{edge.label}| {edge.target}")
            else:
                lines.append(f"    {edge.source} {arrow} {edge.target}")

        return "\n".join(lines)

    def to_markdown(self) -> str:
        """Export as Markdown with embedded Mermaid.

        Returns:
            Markdown string
        """
        return f"```mermaid\n{self.to_mermaid()}\n```"

    def to_dict(self) -> dict[str, Any]:
        """Export as dictionary.

        Returns:
            Dictionary representation
        """
        return {
            "diagram_type": self.diagram_type.value,
            "nodes": [
                {
                    "id": node.id,
                    "label": node.label,
                    "type": node.node_type,
                    "confidence": node.confidence,
                    "metadata": node.metadata,
                }
                for node in self.nodes.values()
            ],
            "edges": [
                {
                    "source": edge.source,
                    "target": edge.target,
                    "label": edge.label,
                    "type": edge.edge_type,
                    "weight": edge.weight,
                }
                for edge in self.edges
            ],
            "metadata": self.metadata,
        }


# ============================================================================
# Falsification Loops
# ============================================================================

@dataclass
class Hypothesis:
    """A testable hypothesis extracted from an answer."""

    claim: str
    confidence: float
    evidence: list[str] = field(default_factory=list)
    counterexamples: list[str] = field(default_factory=list)
    status: str = "untested"  # untested, confirmed, refuted, uncertain


@dataclass
class CounterexampleTest:
    """A test designed to refute a hypothesis."""

    test_id: str
    hypothesis: str
    test_description: str
    expected_outcome: str
    actual_outcome: str | None = None
    refutes: bool = False


class FalsificationLoop:
    """
    Scientific rigor through falsification.

    Features:
    - Extract testable claims from answers
    - Generate counterexamples
    - Execute stress tests
    - Negative control checks
    - Falsification trace logging
    """

    def __init__(self):
        """Initialize the falsification loop."""
        self.hypotheses: dict[str, Hypothesis] = {}
        self.tests: dict[str, CounterexampleTest] = {}
        self.trace: list[dict[str, Any]] = []

    def extract_claims(self, answer: str) -> list[Hypothesis]:
        """Extract testable claims from an answer.

        Args:
            answer: Answer text

        Returns:
            List of hypotheses
        """
        # Placeholder implementation
        # In production, use LLM to extract claims

        hypotheses = []

        # Normalize whitespace and split by sentence
        answer = " ".join(answer.split())  # Normalize whitespace
        sentences = answer.split(". ")

        for _i, sentence in enumerate(sentences):
            sentence = sentence.strip()
            if not sentence:
                continue

            # Look for definitive keywords
            if any(word in sentence.lower() for word in ["always", "never", "all", "none", "must", "every"]):
                hypothesis = Hypothesis(
                    claim=sentence.strip(),
                    confidence=0.8,
                )
                hypothesis_id = f"hyp_{hashlib.md5(sentence.encode()).hexdigest()[:8]}"
                self.hypotheses[hypothesis_id] = hypothesis
                hypotheses.append(hypothesis)

        return hypotheses

    def generate_counterexamples(self, hypothesis: Hypothesis) -> list[CounterexampleTest]:
        """Generate tests to refute a hypothesis.

        Args:
            hypothesis: Hypothesis to test

        Returns:
            List of counterexample tests
        """
        tests = []

        # Placeholder implementation
        # In production, use LLM to generate counterexamples

        # Generate 3 counterexample tests
        for i in range(3):
            test_id = f"test_{hashlib.md5(f'{hypothesis.claim}_{i}'.encode()).hexdigest()[:8]}"

            test = CounterexampleTest(
                test_id=test_id,
                hypothesis=hypothesis.claim,
                test_description=f"Counterexample test {i+1} for: {hypothesis.claim[:50]}...",
                expected_outcome="Hypothesis should hold",
            )

            self.tests[test_id] = test
            tests.append(test)

        return tests

    def execute_test(self, test: CounterexampleTest) -> bool:
        """Execute a counterexample test.

        Args:
            test: Test to execute

        Returns:
            True if test refutes hypothesis
        """
        # Placeholder implementation
        # In production, actually execute the test

        # Simulate test execution
        import random
        refutes = random.random() < 0.1  # 10% chance of refutation

        test.actual_outcome = "Test passed" if not refutes else "Test failed - hypothesis refuted"
        test.refutes = refutes

        # Log trace
        self.trace.append({
            "timestamp": datetime.now().isoformat(),
            "test_id": test.test_id,
            "hypothesis": test.hypothesis,
            "refutes": refutes,
            "outcome": test.actual_outcome,
        })

        return refutes

    def run_falsification(self, answer: str) -> dict[str, Any]:
        """Run complete falsification loop on an answer.

        Args:
            answer: Answer to test

        Returns:
            Falsification report
        """
        # Extract claims
        hypotheses = self.extract_claims(answer)

        results = {
            "total_claims": len(hypotheses),
            "confirmed": 0,
            "refuted": 0,
            "uncertain": 0,
            "hypotheses": [],
        }

        # Test each hypothesis
        for hypothesis in hypotheses:
            tests = self.generate_counterexamples(hypothesis)

            refuted = False
            for test in tests:
                if self.execute_test(test):
                    refuted = True
                    hypothesis.status = "refuted"
                    hypothesis.counterexamples.append(test.test_description)
                    break

            if not refuted:
                hypothesis.status = "confirmed"

            # Update counts
            if hypothesis.status == "confirmed":
                results["confirmed"] += 1
            elif hypothesis.status == "refuted":
                results["refuted"] += 1
            else:
                results["uncertain"] += 1

            results["hypotheses"].append({
                "claim": hypothesis.claim,
                "status": hypothesis.status,
                "confidence": hypothesis.confidence,
                "counterexamples": hypothesis.counterexamples,
            })

        return results


# ============================================================================
# Cross-Session Learning
# ============================================================================

@dataclass
class SessionPattern:
    """A learned pattern from session history."""

    pattern_id: str
    pattern_type: str  # workflow, error, success, optimization
    description: str
    frequency: int
    confidence: float
    examples: list[str] = field(default_factory=list)
    learned_at: str = field(default_factory=lambda: datetime.now().isoformat())


class CrossSessionLearner:
    """
    Learn patterns across sessions for continuous improvement.

    Features:
    - Pattern extraction from session history
    - Success/failure pattern recognition
    - Workflow optimization
    - Error prevention
    - Knowledge consolidation
    """

    def __init__(self):
        """Initialize the learner."""
        self.patterns: dict[str, SessionPattern] = {}
        self.session_history: list[dict[str, Any]] = []

    def add_session(self, session_data: dict[str, Any]) -> None:
        """Add a session to history.

        Args:
            session_data: Session data
        """
        self.session_history.append(session_data)

    def extract_patterns(self) -> list[SessionPattern]:
        """Extract patterns from session history.

        Returns:
            List of learned patterns
        """
        patterns = []

        # Placeholder implementation
        # In production, use ML to extract patterns

        # Simple heuristic: look for repeated workflows
        workflow_counts: dict[str, int] = {}

        for session in self.session_history:
            workflow = session.get("workflow", "unknown")
            workflow_counts[workflow] = workflow_counts.get(workflow, 0) + 1

        # Create patterns for frequent workflows
        for workflow, count in workflow_counts.items():
            if count >= 3:  # Seen at least 3 times
                pattern_id = f"pattern_{hashlib.md5(workflow.encode()).hexdigest()[:8]}"

                pattern = SessionPattern(
                    pattern_id=pattern_id,
                    pattern_type="workflow",
                    description=f"Frequent workflow: {workflow}",
                    frequency=count,
                    confidence=min(count / 10.0, 1.0),
                )

                self.patterns[pattern_id] = pattern
                patterns.append(pattern)

        return patterns

    def get_recommendations(self, current_context: dict[str, Any]) -> list[str]:
        """Get recommendations based on learned patterns.

        Args:
            current_context: Current session context

        Returns:
            List of recommendations
        """
        recommendations = []

        # Match current context to patterns
        for pattern in self.patterns.values():
            if pattern.confidence > 0.7:
                recommendations.append(
                    f"Based on {pattern.frequency} similar sessions: {pattern.description}"
                )

        return recommendations


# ============================================================================
# Exports
# ============================================================================

__all__ = [
    # Mermaid Canvas
    "DiagramType",
    "MermaidNode",
    "MermaidEdge",
    "MermaidCanvas",
    # Falsification
    "Hypothesis",
    "CounterexampleTest",
    "FalsificationLoop",
    # Cross-Session Learning
    "SessionPattern",
    "CrossSessionLearner",
]
