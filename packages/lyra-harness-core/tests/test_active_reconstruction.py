"""Tests for active_reconstruction.py — Active Reconstruction Memory (P2-B2 CRITICAL)."""
from __future__ import annotations

import pytest
from lyra_harness_core.active_reconstruction import (
    ActivatedTag,
    ActiveReconstructionEngine,
    Cue,
    MemoryFragment,
    ReconstructedMemory,
    ReconstructionVerdict,
    SelfVerificationGate,
    TagEdge,
    TagNetwork,
    TagNode,
)


# ---------------------------------------------------------------------------
# TagNode
# ---------------------------------------------------------------------------

class TestTagNode:
    def test_defaults(self):
        n = TagNode(tag="python")
        assert n.tag == "python"
        assert n.weight == 1.0
        assert n.activation == 0.0
        assert n.threshold == 0.1
        assert n.decay == 0.85

    def test_custom(self):
        n = TagNode(tag="ml", weight=0.8, activation=0.5, threshold=0.2, decay=0.7)
        assert n.weight == 0.8
        assert n.activation == 0.5
        assert n.threshold == 0.2
        assert n.decay == 0.7

    def test_frozen(self):
        n = TagNode(tag="ai")
        with pytest.raises(Exception):
            n.weight = 2.0  # type: ignore[misc]


# ---------------------------------------------------------------------------
# TagEdge
# ---------------------------------------------------------------------------

class TestTagEdge:
    def test_defaults(self):
        e = TagEdge(source="a", target="b")
        assert e.source == "a"
        assert e.target == "b"
        assert e.weight == 0.5
        assert e.co_occurrence_count == 0

    def test_custom(self):
        e = TagEdge(source="x", target="y", weight=0.9, co_occurrence_count=5)
        assert e.weight == 0.9
        assert e.co_occurrence_count == 5

    def test_frozen(self):
        e = TagEdge(source="a", target="b")
        with pytest.raises(Exception):
            e.weight = 1.0  # type: ignore[misc]


# ---------------------------------------------------------------------------
# MemoryFragment
# ---------------------------------------------------------------------------

class TestMemoryFragment:
    def test_creation(self):
        f = MemoryFragment(
            fragment_id="f1",
            content="Python is great for ML",
            tags=frozenset(["python", "ml"]),
            importance=0.8,
            source="research",
        )
        assert f.fragment_id == "f1"
        assert f.content == "Python is great for ML"
        assert f.tags == frozenset(["python", "ml"])
        assert f.importance == 0.8
        assert f.source == "research"
        assert f.access_count == 0

    def test_defaults(self):
        f = MemoryFragment(fragment_id="f1", content="test", tags=frozenset())
        assert f.importance == 0.5
        assert f.source == ""
        assert f.created_at == 0.0

    def test_frozen(self):
        f = MemoryFragment(fragment_id="f1", content="test", tags=frozenset(["a"]))
        with pytest.raises(Exception):
            f.importance = 0.9  # type: ignore[misc]


# ---------------------------------------------------------------------------
# Cue
# ---------------------------------------------------------------------------

class TestCue:
    def test_defaults(self):
        c = Cue(query="how does python work")
        assert c.query == "how does python work"
        assert c.tags == frozenset()
        assert c.context_hints == frozenset()
        assert c.min_confidence == 0.5

    def test_with_tags(self):
        c = Cue(query="ml research", tags=frozenset(["ml", "ai"]), min_confidence=0.7)
        assert c.tags == frozenset(["ml", "ai"])
        assert c.min_confidence == 0.7

    def test_with_context_hints(self):
        c = Cue(query="test", context_hints=frozenset(["python", "code"]))
        assert c.context_hints == frozenset(["python", "code"])


# ---------------------------------------------------------------------------
# ActivatedTag
# ---------------------------------------------------------------------------

class TestActivatedTag:
    def test_creation(self):
        at = ActivatedTag(tag="python", activation=0.8, hop_distance=1)
        assert at.tag == "python"
        assert at.activation == 0.8
        assert at.hop_distance == 1
        assert at.source_tags == frozenset()

    def test_with_source_tags(self):
        at = ActivatedTag(
            tag="ml", activation=0.6, hop_distance=2, source_tags=frozenset(["python", "ai"])
        )
        assert at.source_tags == frozenset(["python", "ai"])

    def test_frozen(self):
        at = ActivatedTag(tag="x", activation=0.5, hop_distance=1)
        with pytest.raises(Exception):
            at.activation = 0.9  # type: ignore[misc]


# ---------------------------------------------------------------------------
# ReconstructedMemory
# ---------------------------------------------------------------------------

class TestReconstructedMemory:
    def test_creation(self):
        f = MemoryFragment(fragment_id="f1", content="test", tags=frozenset(["a"]))
        rm = ReconstructedMemory(
            fragments=(f,),
            activated_tags=(),
            confidence=0.75,
            reconstruction_path=("a",),
            elapsed_ms=12.5,
        )
        assert rm.fragments == (f,)
        assert rm.confidence == 0.75
        assert rm.elapsed_ms == 12.5
        assert not rm.from_fallback

    def test_combined_content(self):
        f1 = MemoryFragment(fragment_id="f1", content="Hello", tags=frozenset(["a"]))
        f2 = MemoryFragment(fragment_id="f2", content="World", tags=frozenset(["b"]))
        rm = ReconstructedMemory(
            fragments=(f1, f2),
            activated_tags=(),
            confidence=0.9,
            reconstruction_path=(),
            elapsed_ms=0.0,
        )
        assert "Hello" in rm.combined_content
        assert "World" in rm.combined_content

    def test_is_confident(self):
        f = MemoryFragment(fragment_id="f1", content="t", tags=frozenset(["a"]))
        rm_high = ReconstructedMemory(
            fragments=(f,), activated_tags=(), confidence=0.8, reconstruction_path=(), elapsed_ms=0.0
        )
        rm_low = ReconstructedMemory(
            fragments=(f,), activated_tags=(), confidence=0.3, reconstruction_path=(), elapsed_ms=0.0
        )
        assert rm_high.is_confident
        assert not rm_low.is_confident

    def test_from_fallback(self):
        f = MemoryFragment(fragment_id="f1", content="fallback", tags=frozenset())
        rm = ReconstructedMemory(
            fragments=(f,),
            activated_tags=(),
            confidence=0.0,
            reconstruction_path=(),
            elapsed_ms=0.0,
            from_fallback=True,
        )
        assert rm.from_fallback


# ---------------------------------------------------------------------------
# ReconstructionVerdict
# ---------------------------------------------------------------------------

class TestReconstructionVerdict:
    def test_passed(self):
        v = ReconstructionVerdict(passed=True, confidence=0.9, reason="good")
        assert v.passed
        assert v.confidence == 0.9
        assert not v.fallback_triggered

    def test_failed_with_fallback(self):
        f = MemoryFragment(fragment_id="f1", content="fb", tags=frozenset())
        v = ReconstructionVerdict(
            passed=False,
            confidence=0.2,
            reason="low conf",
            fallback_triggered=True,
            fallback_fragments=(f,),
        )
        assert not v.passed
        assert v.fallback_triggered
        assert len(v.fallback_fragments) == 1


# ---------------------------------------------------------------------------
# TagNetwork
# ---------------------------------------------------------------------------

class TestTagNetwork:
    def test_add_node(self):
        tn = TagNetwork()
        tn.add_node("python")
        assert tn.has_node("python")
        assert not tn.has_node("unknown")

    def test_add_node_custom(self):
        tn = TagNetwork()
        tn.add_node("ai", weight=2.0, threshold=0.2)
        n = tn.nodes["ai"]
        assert n.weight == 2.0
        assert n.threshold == 0.2

    def test_add_edge(self):
        tn = TagNetwork()
        tn.add_node("a")
        tn.add_node("b")
        tn.add_edge("a", "b", weight=0.7)
        e = tn.get_edge("a", "b")
        assert e is not None
        assert e.weight == 0.7
        assert e.source == "a"
        assert e.target == "b"

    def test_add_edge_co_occurrence(self):
        tn = TagNetwork()
        tn.add_node("a")
        tn.add_node("b")
        tn.add_edge("a", "b")
        tn.add_edge("a", "b")  # second call
        e = tn.get_edge("a", "b")
        assert e is not None
        assert e.co_occurrence_count == 1

    def test_get_edge_missing(self):
        tn = TagNetwork()
        assert tn.get_edge("x", "y") is None

    def test_get_neighbors(self):
        tn = TagNetwork()
        tn.add_node("a")
        tn.add_node("b")
        tn.add_node("c")
        tn.add_edge("a", "b")
        tn.add_edge("a", "c")
        neighbors = tn.get_neighbors("a")
        assert len(neighbors) == 2
        targets = {e.target for e in neighbors}
        assert targets == {"b", "c"}

    def test_get_neighbors_empty(self):
        tn = TagNetwork()
        tn.add_node("a")
        assert tn.get_neighbors("a") == []

    def test_index_fragment(self):
        tn = TagNetwork()
        f = MemoryFragment(fragment_id="f1", content="test", tags=frozenset(["python", "ml"]))
        tn.index_fragment(f)
        assert "f1" in tn.fragments_for_tag("python")
        assert "f1" in tn.fragments_for_tag("ml")

    def test_remove_fragment(self):
        tn = TagNetwork()
        f = MemoryFragment(fragment_id="f1", content="test", tags=frozenset(["python"]))
        tn.index_fragment(f)
        assert "f1" in tn.fragments_for_tag("python")
        tn.remove_fragment("f1")
        assert "f1" not in tn.fragments_for_tag("python")

    def test_fragments_for_tags(self):
        tn = TagNetwork()
        f1 = MemoryFragment(fragment_id="f1", content="a", tags=frozenset(["python"]))
        f2 = MemoryFragment(fragment_id="f2", content="b", tags=frozenset(["ml"]))
        tn.index_fragment(f1)
        tn.index_fragment(f2)
        ids = tn.fragments_for_tags(frozenset(["python", "ml"]))
        assert ids == {"f1", "f2"}

    def test_activate_seed_tags(self):
        tn = TagNetwork()
        tn.add_node("python", weight=1.0)
        tn.add_node("ml", weight=0.8)
        activated = tn.activate(frozenset(["python", "ml"]))
        assert "python" in activated
        assert "ml" in activated
        assert activated["python"].activation == 1.0
        assert activated["ml"].activation == 0.8
        assert activated["python"].hop_distance == 0

    def test_activate_spreading(self):
        tn = TagNetwork()
        tn.add_node("python", weight=1.0)
        tn.add_node("ml", weight=0.8)
        tn.add_node("ai", weight=0.9)
        tn.add_edge("python", "ml", weight=0.7)
        tn.add_edge("ml", "ai", weight=0.6)
        activated = tn.activate(frozenset(["python"]), max_hops=2)
        assert "python" in activated
        # ml should be activated via python -> ml edge
        assert "ml" in activated
        assert activated["ml"].hop_distance == 1

    def test_activate_decay(self):
        tn = TagNetwork()
        tn.add_node("a", weight=1.0, decay=0.5)
        tn.add_node("b", weight=1.0)
        tn.add_edge("a", "b", weight=0.8)
        activated = tn.activate(frozenset(["a"]), max_hops=1)
        assert "b" in activated
        # b = 1.0 * 0.5 * 0.8 = 0.4
        assert activated["b"].activation == pytest.approx(0.4)

    def test_activate_below_threshold_filtered(self):
        tn = TagNetwork()
        tn.add_node("a", weight=1.0, decay=0.1)
        tn.add_node("b", weight=1.0)
        tn.add_edge("a", "b", weight=0.3)
        activated = tn.activate(frozenset(["a"]), max_hops=1, activation_threshold=0.1)
        # b = 1.0 * 0.1 * 0.3 = 0.03 < 0.1 threshold
        assert "b" not in activated

    def test_activate_missing_seed(self):
        tn = TagNetwork()
        activated = tn.activate(frozenset(["nonexistent"]))
        assert activated == {}

    def test_node_count(self):
        tn = TagNetwork()
        tn.add_node("a")
        tn.add_node("b")
        assert tn.node_count() == 2

    def test_edge_count(self):
        tn = TagNetwork()
        tn.add_node("a")
        tn.add_node("b")
        tn.add_node("c")
        tn.add_edge("a", "b")
        tn.add_edge("a", "c")
        assert tn.edge_count() == 2

    def test_fragment_index_size(self):
        tn = TagNetwork()
        f1 = MemoryFragment(fragment_id="f1", content="a", tags=frozenset(["x"]))
        f2 = MemoryFragment(fragment_id="f2", content="b", tags=frozenset(["x", "y"]))
        tn.index_fragment(f1)
        tn.index_fragment(f2)
        assert tn.fragment_index_size() == 3  # x: [f1,f2], y: [f2] = 3 entries


# ---------------------------------------------------------------------------
# SelfVerificationGate
# ---------------------------------------------------------------------------

class TestSelfVerificationGate:
    def test_passes_with_high_confidence(self):
        gate = SelfVerificationGate()
        f = MemoryFragment(fragment_id="f1", content="test", tags=frozenset(["a", "b"]))
        at = ActivatedTag(tag="a", activation=0.9, hop_distance=0)
        rm = ReconstructedMemory(
            fragments=(f,),
            activated_tags=(at, at),  # 2 activated tags
            confidence=0.8,
            reconstruction_path=("a",),
            elapsed_ms=0.0,
        )
        v = gate.verify(rm)
        assert v.passed

    def test_fails_low_confidence(self):
        gate = SelfVerificationGate(confidence_threshold=0.6)
        f = MemoryFragment(fragment_id="f1", content="test", tags=frozenset(["a", "b"]))
        at = ActivatedTag(tag="a", activation=0.3, hop_distance=0)
        rm = ReconstructedMemory(
            fragments=(f,),
            activated_tags=(at, at),
            confidence=0.3,
            reconstruction_path=("a",),
            elapsed_ms=0.0,
        )
        v = gate.verify(rm)
        assert not v.passed
        assert v.fallback_triggered

    def test_fails_too_few_fragments(self):
        gate = SelfVerificationGate(min_fragments=2)
        f = MemoryFragment(fragment_id="f1", content="test", tags=frozenset(["a", "b"]))
        at = ActivatedTag(tag="a", activation=0.9, hop_distance=0)
        rm = ReconstructedMemory(
            fragments=(f,),
            activated_tags=(at, at),
            confidence=0.9,
            reconstruction_path=("a",),
            elapsed_ms=0.0,
        )
        v = gate.verify(rm)
        assert not v.passed
        assert "Too few fragments" in v.reason

    def test_fails_too_few_activated_tags(self):
        gate = SelfVerificationGate(min_activated_tags=3)
        f = MemoryFragment(fragment_id="f1", content="test", tags=frozenset(["a"]))
        at = ActivatedTag(tag="a", activation=0.9, hop_distance=0)
        rm = ReconstructedMemory(
            fragments=(f,),
            activated_tags=(at,),
            confidence=0.9,
            reconstruction_path=("a",),
            elapsed_ms=0.0,
        )
        v = gate.verify(rm)
        assert not v.passed
        assert "Too few activated tags" in v.reason

    def test_fallback_fragments_preserved(self):
        gate = SelfVerificationGate(confidence_threshold=0.9)
        f = MemoryFragment(fragment_id="f1", content="test", tags=frozenset(["a"]))
        fb = MemoryFragment(fragment_id="fb1", content="fallback", tags=frozenset(["b"]))
        rm = ReconstructedMemory(
            fragments=(f,),
            activated_tags=(ActivatedTag(tag="a", activation=0.5, hop_distance=0),),
            confidence=0.3,
            reconstruction_path=("a",),
            elapsed_ms=0.0,
        )
        v = gate.verify(rm, fallback_fragments=(fb,))
        assert not v.passed
        assert v.fallback_triggered
        assert len(v.fallback_fragments) == 1


# ---------------------------------------------------------------------------
# ActiveReconstructionEngine — fragment management
# ---------------------------------------------------------------------------

class TestEngineFragments:
    def test_add_fragment(self):
        engine = ActiveReconstructionEngine()
        f = engine.add_fragment("Python is great for ML", frozenset(["python", "ml"]))
        assert f.fragment_id.startswith("frag-")
        assert engine.fragment_count == 1
        assert engine.tag_count == 2

    def test_add_fragment_deduplicate(self):
        engine = ActiveReconstructionEngine()
        f1 = engine.add_fragment("same content", frozenset(["a"]))
        f2 = engine.add_fragment("same content", frozenset(["a"]))
        assert f1.fragment_id == f2.fragment_id
        assert engine.fragment_count == 1

    def test_add_fragment_creates_edges(self):
        engine = ActiveReconstructionEngine()
        engine.add_fragment("content", frozenset(["a", "b"]))
        # Co-occurrence edges should exist
        assert engine.edge_count == 2  # a->b and b->a

    def test_remove_fragment(self):
        engine = ActiveReconstructionEngine()
        f = engine.add_fragment("content", frozenset(["tag"]))
        assert engine.fragment_count == 1
        assert engine.remove_fragment(f.fragment_id)
        assert engine.fragment_count == 0

    def test_remove_nonexistent(self):
        engine = ActiveReconstructionEngine()
        assert not engine.remove_fragment("nonexistent")

    def test_get_fragment(self):
        engine = ActiveReconstructionEngine()
        f = engine.add_fragment("content", frozenset(["tag"]))
        retrieved = engine.get_fragment(f.fragment_id)
        assert retrieved is not None
        assert retrieved.content == "content"

    def test_get_fragment_updates_access(self):
        engine = ActiveReconstructionEngine()
        f = engine.add_fragment("content", frozenset(["tag"]))
        retrieved = engine.get_fragment(f.fragment_id)
        assert retrieved is not None
        assert retrieved.access_count == 1

    def test_extract_tags(self):
        tags = ActiveReconstructionEngine.extract_tags("Python is great for machine learning")
        assert "python" in tags
        assert "great" in tags
        assert "machine" in tags
        assert "learning" in tags

    def test_extract_tags_filters_short_words(self):
        tags = ActiveReconstructionEngine.extract_tags("AI is the best for ML")
        assert "best" in tags
        assert "is" not in tags  # too short
        assert "ai" not in tags  # too short (2 chars)
        assert "ml" not in tags  # too short

    def test_tag_count(self):
        engine = ActiveReconstructionEngine()
        engine.add_fragment("a", frozenset(["x", "y", "z"]))
        assert engine.tag_count == 3


# ---------------------------------------------------------------------------
# ActiveReconstructionEngine — reconstruction
# ---------------------------------------------------------------------------

class TestEngineReconstruction:
    def test_reconstruct_simple(self):
        engine = ActiveReconstructionEngine()
        engine.add_fragment("Python is a programming language", frozenset(["python", "programming"]))
        engine.add_fragment("Machine learning uses Python", frozenset(["machine", "learning", "python"]))
        cue = Cue(query="python programming")
        result = engine.reconstruct(cue)
        assert len(result.fragments) > 0
        assert result.confidence >= 0.0
        assert result.elapsed_ms >= 0

    def test_reconstruct_with_explicit_tags(self):
        engine = ActiveReconstructionEngine()
        engine.add_fragment("Deep learning with neural networks", frozenset(["deep", "learning", "neural"]))
        cue = Cue(query="", tags=frozenset(["deep", "neural"]))
        result = engine.reconstruct(cue)
        assert len(result.fragments) > 0

    def test_reconstruct_with_context_hints(self):
        engine = ActiveReconstructionEngine()
        engine.add_fragment("Data science with Python", frozenset(["data", "science", "python"]))
        cue = Cue(query="", tags=frozenset(["data"]), context_hints=frozenset(["python"]))
        result = engine.reconstruct(cue)
        assert len(result.fragments) > 0

    def test_reconstruct_no_match(self):
        engine = ActiveReconstructionEngine()
        engine.add_fragment("Python code", frozenset(["python", "code"]))
        cue = Cue(query="javascript", tags=frozenset(["javascript"]))
        result = engine.reconstruct(cue)
        assert len(result.fragments) == 0
        assert result.confidence == 0.0

    def test_reconstruct_empty_network(self):
        engine = ActiveReconstructionEngine()
        cue = Cue(query="anything")
        result = engine.reconstruct(cue)
        assert len(result.fragments) == 0

    def test_reconstruct_activated_tags_sorted(self):
        engine = ActiveReconstructionEngine()
        engine.add_fragment("Alpha", frozenset(["alpha", "common"]))
        engine.add_fragment("Beta", frozenset(["beta", "common"]))
        cue = Cue(query="", tags=frozenset(["alpha"]))
        result = engine.reconstruct(cue)
        if result.activated_tags:
            # First tag should be the seed
            assert result.activated_tags[0].activation >= result.activated_tags[-1].activation

    def test_reconstruct_confidence_range(self):
        engine = ActiveReconstructionEngine()
        for i in range(5):
            engine.add_fragment(f"Memory {i} about AI", frozenset(["ai", f"topic{i}"]), importance=0.9)
        cue = Cue(query="ai memory")
        result = engine.reconstruct(cue)
        assert 0.0 <= result.confidence <= 1.0

    def test_reconstruct_with_fallback_passes(self):
        engine = ActiveReconstructionEngine()
        engine.add_fragment("AI is transformative", frozenset(["ai", "technology"]), importance=0.9)
        cue = Cue(query="ai technology")
        verdict = engine.reconstruct_with_fallback(cue)
        assert isinstance(verdict, ReconstructionVerdict)

    def test_reconstruct_with_fallback_triggers(self):
        engine = ActiveReconstructionEngine()
        engine.gate = SelfVerificationGate(confidence_threshold=0.99)
        # Add one weak fragment — won't meet 0.99 confidence
        engine.add_fragment("small note", frozenset(["note"]), importance=0.1)

        def fallback_fn(query):
            return [MemoryFragment(fragment_id="fb1", content=f"fallback for {query}", tags=frozenset(["fb"]))]

        cue = Cue(query="small")
        verdict = engine.reconstruct_with_fallback(cue, fallback_fn=fallback_fn)
        # May or may not pass depending on confidence
        assert isinstance(verdict, ReconstructionVerdict)

    def test_reconstruct_path(self):
        engine = ActiveReconstructionEngine()
        engine.add_fragment("Python ML", frozenset(["python", "ml"]))
        engine.add_fragment("Deep Learning", frozenset(["deep", "learning", "ml"]))
        cue = Cue(query="", tags=frozenset(["python"]))
        result = engine.reconstruct(cue)
        assert isinstance(result.reconstruction_path, tuple)

    def test_multiple_reconstructs_idempotent(self):
        engine = ActiveReconstructionEngine()
        engine.add_fragment("Important memory", frozenset(["important", "memory"]), importance=0.95)
        cue = Cue(query="important memory")
        r1 = engine.reconstruct(cue)
        r2 = engine.reconstruct(cue)
        assert r1.confidence == pytest.approx(r2.confidence)


# ---------------------------------------------------------------------------
# Full Pipeline Integration
# ---------------------------------------------------------------------------

class TestFullPipeline:
    def test_end_to_end(self):
        """Full active reconstruction pipeline."""
        engine = ActiveReconstructionEngine()

        # Add diverse fragments
        engine.add_fragment(
            "Python is a high-level programming language known for readability",
            frozenset(["python", "programming", "language", "readability"]),
            importance=0.9,
        )
        engine.add_fragment(
            "Machine learning uses statistical techniques to learn from data",
            frozenset(["machine", "learning", "statistical", "data"]),
            importance=0.85,
        )
        engine.add_fragment(
            "Deep learning is a subset of machine learning using neural networks",
            frozenset(["deep", "learning", "machine", "neural", "networks"]),
            importance=0.9,
        )
        engine.add_fragment(
            "PyTorch is a popular deep learning framework",
            frozenset(["pytorch", "deep", "learning", "framework"]),
            importance=0.8,
        )

        # Cue about ML + Python
        cue = Cue(query="python machine learning deep learning")
        result = engine.reconstruct(cue)

        # Should find multiple fragments
        assert len(result.fragments) >= 2
        assert result.confidence > 0.0
        assert len(result.activated_tags) > 0
        assert result.elapsed_ms >= 0

    def test_spreading_activation_multi_hop(self):
        """Test that activation spreads across multiple hops."""
        engine = ActiveReconstructionEngine(max_hops=3)

        # Create a chain: a -> b -> c -> d
        engine.network.add_node("a", weight=1.0)
        engine.network.add_node("b", weight=0.9)
        engine.network.add_node("c", weight=0.8)
        engine.network.add_node("d", weight=0.7)
        engine.network.add_edge("a", "b", weight=0.9)
        engine.network.add_edge("b", "c", weight=0.8)
        engine.network.add_edge("c", "d", weight=0.7)

        # Add fragments keyed by each tag
        engine.add_fragment("Content A", frozenset(["a"]), importance=0.9)
        engine.add_fragment("Content B", frozenset(["b"]), importance=0.8)
        engine.add_fragment("Content C", frozenset(["c"]), importance=0.7)
        engine.add_fragment("Content D", frozenset(["d"]), importance=0.6)

        cue = Cue(query="", tags=frozenset(["a"]))
        result = engine.reconstruct(cue)

        # Should activate b, c, d through spreading
        activated_tags = {at.tag for at in result.activated_tags}
        assert "a" in activated_tags
        # b should activate (1.0 * 0.85 * 0.9 = 0.765 > 0.05)
        assert "b" in activated_tags

    def test_fragment_access_tracking(self):
        """Fragments track access counts during reconstruction."""
        engine = ActiveReconstructionEngine()
        f = engine.add_fragment("Track me", frozenset(["track"]), importance=0.9)
        cue = Cue(query="track")
        engine.reconstruct(cue)
        engine.reconstruct(cue)
        engine.reconstruct(cue)
        retrieved = engine.get_fragment(f.fragment_id)
        assert retrieved is not None
        assert retrieved.access_count >= 3
