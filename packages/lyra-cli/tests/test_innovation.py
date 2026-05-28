"""Tests for Lyra Ultra Phase 8: Innovation & Differentiation."""


from lyra_cli.innovation import (
    CounterexampleTest,
    # Cross-Session Learning
    CrossSessionLearner,
    # Mermaid Canvas
    DiagramType,
    FalsificationLoop,
    # Falsification
    Hypothesis,
    MermaidCanvas,
)

# ============================================================================
# Mermaid Canvas Tests
# ============================================================================

def test_mermaid_canvas_creation():
    """Test creating a Mermaid canvas."""
    canvas = MermaidCanvas(DiagramType.KNOWLEDGE_GRAPH)

    assert canvas.diagram_type == DiagramType.KNOWLEDGE_GRAPH
    assert len(canvas.nodes) == 0
    assert len(canvas.edges) == 0


def test_mermaid_canvas_add_node():
    """Test adding nodes to canvas."""
    canvas = MermaidCanvas()

    canvas.add_node("n1", "Node 1", node_type="entity", confidence=0.9)

    assert "n1" in canvas.nodes
    assert canvas.nodes["n1"].label == "Node 1"
    assert canvas.nodes["n1"].confidence == 0.9


def test_mermaid_canvas_add_edge():
    """Test adding edges to canvas."""
    canvas = MermaidCanvas()

    canvas.add_node("n1", "Node 1")
    canvas.add_node("n2", "Node 2")
    canvas.add_edge("n1", "n2", label="connects to")

    assert len(canvas.edges) == 1
    assert canvas.edges[0].source == "n1"
    assert canvas.edges[0].target == "n2"
    assert canvas.edges[0].label == "connects to"


def test_mermaid_canvas_filter_by_confidence():
    """Test filtering nodes by confidence."""
    canvas = MermaidCanvas()

    canvas.add_node("n1", "High confidence", confidence=0.9)
    canvas.add_node("n2", "Low confidence", confidence=0.3)
    canvas.add_node("n3", "Medium confidence", confidence=0.7)

    filtered = canvas.filter_by_confidence(0.6)

    assert len(filtered.nodes) == 2
    assert "n1" in filtered.nodes
    assert "n3" in filtered.nodes
    assert "n2" not in filtered.nodes


def test_mermaid_canvas_highlight_path():
    """Test finding path between nodes."""
    canvas = MermaidCanvas()

    canvas.add_node("n1", "Start")
    canvas.add_node("n2", "Middle")
    canvas.add_node("n3", "End")

    canvas.add_edge("n1", "n2")
    canvas.add_edge("n2", "n3")

    path = canvas.highlight_path("n1", "n3")

    assert path == ["n1", "n2", "n3"]


def test_mermaid_canvas_to_mermaid():
    """Test generating Mermaid syntax."""
    canvas = MermaidCanvas(DiagramType.KNOWLEDGE_GRAPH)

    canvas.add_node("n1", "Node 1")
    canvas.add_node("n2", "Node 2")
    canvas.add_edge("n1", "n2", label="connects")

    mermaid = canvas.to_mermaid()

    assert "graph TD" in mermaid
    assert "n1[Node 1]" in mermaid
    assert "n2[Node 2]" in mermaid
    assert "n1 -->|connects| n2" in mermaid


def test_mermaid_canvas_to_markdown():
    """Test exporting as Markdown."""
    canvas = MermaidCanvas()

    canvas.add_node("n1", "Node 1")

    markdown = canvas.to_markdown()

    assert "```mermaid" in markdown
    assert "```" in markdown
    assert "n1[Node 1]" in markdown


def test_mermaid_canvas_to_dict():
    """Test exporting as dictionary."""
    canvas = MermaidCanvas()

    canvas.add_node("n1", "Node 1", confidence=0.9)
    canvas.add_edge("n1", "n2")

    data = canvas.to_dict()

    assert "nodes" in data
    assert "edges" in data
    assert len(data["nodes"]) == 1
    assert len(data["edges"]) == 1


def test_mermaid_canvas_different_diagram_types():
    """Test different diagram types."""
    types = [
        DiagramType.KNOWLEDGE_GRAPH,
        DiagramType.WORKFLOW,
        DiagramType.MEMORY_TOPOLOGY,
        DiagramType.EVIDENCE_CHAIN,
    ]

    for diagram_type in types:
        canvas = MermaidCanvas(diagram_type)
        canvas.add_node("n1", "Node")
        mermaid = canvas.to_mermaid()

        assert len(mermaid) > 0


# ============================================================================
# Falsification Loop Tests
# ============================================================================

def test_falsification_loop_creation():
    """Test creating a falsification loop."""
    loop = FalsificationLoop()

    assert len(loop.hypotheses) == 0
    assert len(loop.tests) == 0
    assert len(loop.trace) == 0


def test_falsification_extract_claims():
    """Test extracting claims from answer."""
    loop = FalsificationLoop()

    answer = "All users must authenticate. The system never stores passwords in plaintext."

    hypotheses = loop.extract_claims(answer)

    assert len(hypotheses) > 0
    # Should extract claims with "must" and "never"


def test_falsification_generate_counterexamples():
    """Test generating counterexamples."""
    loop = FalsificationLoop()

    hypothesis = Hypothesis(
        claim="All users must authenticate",
        confidence=0.9,
    )

    tests = loop.generate_counterexamples(hypothesis)

    assert len(tests) > 0
    for test in tests:
        assert test.hypothesis == hypothesis.claim


def test_falsification_execute_test():
    """Test executing a counterexample test."""
    loop = FalsificationLoop()

    test = CounterexampleTest(
        test_id="test_1",
        hypothesis="All users must authenticate",
        test_description="Test unauthenticated access",
        expected_outcome="Should be blocked",
    )

    refutes = loop.execute_test(test)

    assert isinstance(refutes, bool)
    assert test.actual_outcome is not None
    assert len(loop.trace) == 1


def test_falsification_run_complete():
    """Test running complete falsification loop."""
    loop = FalsificationLoop()

    answer = "All users must authenticate. The system always validates input."

    results = loop.run_falsification(answer)

    assert "total_claims" in results
    assert "confirmed" in results
    assert "refuted" in results
    assert "hypotheses" in results
    assert results["total_claims"] > 0


def test_falsification_hypothesis_status():
    """Test hypothesis status tracking."""
    hypothesis = Hypothesis(
        claim="Test claim",
        confidence=0.8,
    )

    assert hypothesis.status == "untested"

    hypothesis.status = "confirmed"
    assert hypothesis.status == "confirmed"


# ============================================================================
# Cross-Session Learning Tests
# ============================================================================

def test_cross_session_learner_creation():
    """Test creating a cross-session learner."""
    learner = CrossSessionLearner()

    assert len(learner.patterns) == 0
    assert len(learner.session_history) == 0


def test_cross_session_add_session():
    """Test adding session to history."""
    learner = CrossSessionLearner()

    session = {
        "session_id": "s1",
        "workflow": "code_review",
        "duration": 120,
    }

    learner.add_session(session)

    assert len(learner.session_history) == 1


def test_cross_session_extract_patterns():
    """Test extracting patterns from history."""
    learner = CrossSessionLearner()

    # Add multiple sessions with same workflow
    for i in range(5):
        learner.add_session({
            "session_id": f"s{i}",
            "workflow": "code_review",
        })

    patterns = learner.extract_patterns()

    assert len(patterns) > 0
    # Should detect "code_review" as frequent pattern


def test_cross_session_pattern_frequency():
    """Test pattern frequency tracking."""
    learner = CrossSessionLearner()

    # Add sessions
    for i in range(3):
        learner.add_session({"workflow": "debug"})

    patterns = learner.extract_patterns()

    if patterns:
        pattern = patterns[0]
        assert pattern.frequency >= 3


def test_cross_session_get_recommendations():
    """Test getting recommendations."""
    learner = CrossSessionLearner()

    # Add sessions and extract patterns
    for i in range(5):
        learner.add_session({"workflow": "test"})

    learner.extract_patterns()

    recommendations = learner.get_recommendations({"workflow": "test"})

    # Should have recommendations based on patterns
    assert isinstance(recommendations, list)


def test_cross_session_pattern_confidence():
    """Test pattern confidence calculation."""
    learner = CrossSessionLearner()

    # Add many sessions
    for i in range(10):
        learner.add_session({"workflow": "deploy"})

    patterns = learner.extract_patterns()

    if patterns:
        pattern = patterns[0]
        assert 0 <= pattern.confidence <= 1.0


# ============================================================================
# Integration Tests
# ============================================================================

def test_mermaid_canvas_knowledge_graph():
    """Test creating a knowledge graph."""
    canvas = MermaidCanvas(DiagramType.KNOWLEDGE_GRAPH)

    # Add entities
    canvas.add_node("user", "User", node_type="entity")
    canvas.add_node("auth", "Authentication", node_type="process")
    canvas.add_node("db", "Database", node_type="entity")

    # Add relationships
    canvas.add_edge("user", "auth", label="authenticates via")
    canvas.add_edge("auth", "db", label="queries")

    # Generate diagram
    mermaid = canvas.to_mermaid()

    assert "graph TD" in mermaid
    assert len(canvas.nodes) == 3
    assert len(canvas.edges) == 2


def test_falsification_with_multiple_claims():
    """Test falsification with multiple claims."""
    loop = FalsificationLoop()

    answer = """
    All users must authenticate.
    The system never stores passwords in plaintext.
    All data is always encrypted.
    """

    results = loop.run_falsification(answer)

    assert results["total_claims"] >= 3
    assert results["confirmed"] + results["refuted"] + results["uncertain"] == results["total_claims"]


def test_cross_session_learning_workflow():
    """Test complete cross-session learning workflow."""
    learner = CrossSessionLearner()

    # Simulate multiple sessions
    workflows = ["code_review", "debug", "code_review", "test", "code_review", "debug"]

    for i, workflow in enumerate(workflows):
        learner.add_session({
            "session_id": f"s{i}",
            "workflow": workflow,
            "success": True,
        })

    # Extract patterns
    patterns = learner.extract_patterns()

    # Should find "code_review" as most frequent
    assert len(patterns) > 0

    # Get recommendations
    recommendations = learner.get_recommendations({"workflow": "code_review"})

    assert isinstance(recommendations, list)


def test_mermaid_canvas_workflow_visualization():
    """Test workflow visualization."""
    canvas = MermaidCanvas(DiagramType.WORKFLOW)

    # Add workflow steps
    canvas.add_node("start", "Start", node_type="process")
    canvas.add_node("analyze", "Analyze Code", node_type="process")
    canvas.add_node("test", "Run Tests", node_type="process")
    canvas.add_node("deploy", "Deploy", node_type="process")
    canvas.add_node("end", "End", node_type="process")

    # Add flow
    canvas.add_edge("start", "analyze")
    canvas.add_edge("analyze", "test")
    canvas.add_edge("test", "deploy")
    canvas.add_edge("deploy", "end")

    mermaid = canvas.to_mermaid()

    assert "flowchart TD" in mermaid
    assert len(canvas.nodes) == 5


# ============================================================================
# Performance Tests
# ============================================================================

def test_mermaid_canvas_large_graph():
    """Test canvas with large graph."""
    canvas = MermaidCanvas()

    # Add many nodes
    for i in range(100):
        canvas.add_node(f"n{i}", f"Node {i}")

    # Add edges
    for i in range(99):
        canvas.add_edge(f"n{i}", f"n{i+1}")

    # Should handle large graphs
    assert len(canvas.nodes) == 100
    assert len(canvas.edges) == 99

    mermaid = canvas.to_mermaid()
    assert len(mermaid) > 0


def test_falsification_performance():
    """Test falsification loop performance."""
    import time

    loop = FalsificationLoop()

    answer = "All users must authenticate. " * 10

    start = time.time()
    results = loop.run_falsification(answer)
    duration = time.time() - start

    # Should complete quickly
    assert duration < 1.0


def test_cross_session_learning_performance():
    """Test cross-session learning performance."""
    import time

    learner = CrossSessionLearner()

    # Add many sessions
    for i in range(100):
        learner.add_session({"workflow": f"workflow_{i % 10}"})

    start = time.time()
    patterns = learner.extract_patterns()
    duration = time.time() - start

    # Should complete quickly
    assert duration < 1.0
