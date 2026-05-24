"""Tests for Tier-1 multi-hop primitives — PoG, AnchorRAG, Reason-in-Documents."""
from __future__ import annotations

import pytest

from harness_core.gates import ChainOfNoteGate, DocVerdict, NoteVerdict
from harness_core.multi_hop import (
    AnchorCandidate,
    DenoisedDoc,
    FixedAnchorPredictor,
    NodeStatus,
    PathScore,
    PathScorer,
    PlanOnGraphWalker,
    ReasonInDocuments,
    RetrievedDoc,
    SimpleEdge,
    SimpleGraph,
    SimpleNode,
    StubLLM,
    TargetNodeScorer,
    TokenOverlapAnchorPredictor,
    compose_with_chain_of_note,
    merge_predictors,
)


# --- Plan-on-Graph -------------------------------------------------------


def _diamond_graph():
    """seed → a, b → target. Two paths, both should reach target."""
    g = SimpleGraph.from_pairs([
        ("seed", "a"),
        ("seed", "b"),
        ("a", "target"),
        ("b", "target"),
    ])
    return g


class TestPlanOnGraphWalker:
    def test_finds_target_via_either_path(self):
        g = _diamond_graph()
        walker = PlanOnGraphWalker(graph=g, scorer=TargetNodeScorer(target_node_id="target"))
        result = walker.walk(query="reach target", seeds=["seed"])
        assert result.best_path is not None
        assert result.best_path.completed is True
        assert result.best_path.nodes[-1] == "target"
        assert result.n_score_calls > 0

    def test_no_seed_match_returns_empty(self):
        g = _diamond_graph()
        walker = PlanOnGraphWalker(graph=g, scorer=TargetNodeScorer(target_node_id="target"))
        result = walker.walk(query="q", seeds=["nonexistent"])
        assert result.paths == ()
        assert result.best_path is None

    def test_max_score_calls_caps_budget(self):
        g = _diamond_graph()
        walker = PlanOnGraphWalker(
            graph=g,
            scorer=TargetNodeScorer(target_node_id="target"),
            max_score_calls=1,
        )
        result = walker.walk(query="q", seeds=["seed"])
        assert result.n_score_calls <= 1

    def test_pruning_records_backtrack(self):
        # Scorer that always rejects → all paths get pruned.
        class RejectAll:
            name = "reject"
            def score(self, *, query, path, graph):
                return PathScore(score=0.1, reason="reject")

        g = _diamond_graph()
        walker = PlanOnGraphWalker(graph=g, scorer=RejectAll())
        result = walker.walk(query="q", seeds=["seed"])
        assert result.n_backtracks > 0
        # All terminal records should be pruned.
        for path in result.paths:
            assert path.completed is False

    def test_node_status_tracked(self):
        g = _diamond_graph()
        walker = PlanOnGraphWalker(graph=g, scorer=TargetNodeScorer(target_node_id="target"))
        result = walker.walk(query="q", seeds=["seed"])
        # The seed should be visited.
        assert "seed" in result.visited
        # At least one node should be EXPLORED.
        explored = [r for r in result.visited.values() if r.status == NodeStatus.EXPLORED]
        assert explored


class TestPathScore:
    def test_valid(self):
        s = PathScore(score=0.7, reason="r")
        assert s.score == 0.7

    def test_invalid_score(self):
        with pytest.raises(ValueError):
            PathScore(score=1.5)
        with pytest.raises(ValueError):
            PathScore(score=-0.1)


class TestTargetNodeScorer:
    def test_reaches_target(self):
        scorer = TargetNodeScorer(target_node_id="t")
        s = scorer.score(query="q", path=("a", "t"), graph=SimpleGraph())
        assert s.score == 1.0

    def test_empty_path(self):
        scorer = TargetNodeScorer(target_node_id="t")
        s = scorer.score(query="q", path=(), graph=SimpleGraph())
        assert s.score == 0.0


# --- AnchorRAG predictor -------------------------------------------------


class TestAnchorCandidate:
    def test_make_validates_confidence(self):
        with pytest.raises(ValueError):
            AnchorCandidate.make(node_id="x", confidence=1.5)

    def test_sort_order_descending(self):
        a = AnchorCandidate.make(node_id="a", confidence=0.9)
        b = AnchorCandidate.make(node_id="b", confidence=0.5)
        assert sorted([b, a])[0].node_id == "a"


class TestTokenOverlapAnchorPredictor:
    def _build(self):
        g = SimpleGraph()
        g.add_node(SimpleNode(id="brca1", title="BRCA1 gene tumor suppressor"))
        g.add_node(SimpleNode(id="brca2", title="BRCA2 gene"))
        g.add_node(SimpleNode(id="tp53", title="TP53 protein"))
        g.add_node(SimpleNode(id="empty", title=""))
        return g

    def test_prefix_match_finds_brca(self):
        # 'BRCA' should prefix-match BRCA1/BRCA2 even though the full word
        # 'brca1' isn't in the query.
        p = TokenOverlapAnchorPredictor()
        hits = p.predict("BRCA mutations", graph=self._build(), top_k=5)
        ids = {h.node_id for h in hits}
        assert "brca1" in ids
        assert "brca2" in ids
        assert "tp53" not in ids

    def test_full_token_match(self):
        p = TokenOverlapAnchorPredictor()
        hits = p.predict("TP53 protein", graph=self._build(), top_k=5)
        assert hits[0].node_id == "tp53"

    def test_empty_query(self):
        p = TokenOverlapAnchorPredictor()
        assert p.predict("", graph=self._build(), top_k=5) == []
        assert p.predict("   ", graph=self._build(), top_k=5) == []

    def test_no_matches(self):
        p = TokenOverlapAnchorPredictor()
        # "HRRT" doesn't match any title or id.
        assert p.predict("HRRT pathway", graph=self._build(), top_k=5) == []

    def test_top_k_limits(self):
        p = TokenOverlapAnchorPredictor()
        hits = p.predict("BRCA", graph=self._build(), top_k=1)
        assert len(hits) == 1


class TestFixedAnchorPredictor:
    def test_returns_only_present_nodes(self):
        g = SimpleGraph()
        g.add_node(SimpleNode(id="a", title="A"))
        p = FixedAnchorPredictor(fixed=[("a", 0.9), ("missing", 0.8)])
        hits = p.predict("q", graph=g, top_k=5)
        assert {h.node_id for h in hits} == {"a"}


class TestMergePredictors:
    def test_merges_by_max_confidence(self):
        g = SimpleGraph()
        g.add_node(SimpleNode(id="x", title=""))
        p1 = FixedAnchorPredictor(fixed=[("x", 0.5)])
        p2 = FixedAnchorPredictor(fixed=[("x", 0.9)])
        merged = merge_predictors([p1, p2], query="q", graph=g, top_k=5)
        assert len(merged) == 1
        # max-confidence wins
        assert merged[0].confidence == pytest.approx(0.9)

    def test_weights_apply(self):
        g = SimpleGraph()
        g.add_node(SimpleNode(id="x", title=""))
        g.add_node(SimpleNode(id="y", title=""))
        p1 = FixedAnchorPredictor(fixed=[("x", 1.0)])
        p2 = FixedAnchorPredictor(fixed=[("y", 1.0)])
        # Weight p1 lower → x's score halved → y wins.
        merged = merge_predictors([p1, p2], query="q", graph=g, weights=[0.5, 1.0], top_k=5)
        assert merged[0].node_id == "y"

    def test_weights_length_mismatch_raises(self):
        with pytest.raises(ValueError):
            merge_predictors([FixedAnchorPredictor()], query="q", graph=SimpleGraph(), weights=[1.0, 2.0])


# --- Reason-in-Documents -------------------------------------------------


class TestReasonInDocuments:
    def test_relevant_docs_kept(self):
        llm = StubLLM(responses=["Bob directed Casablanca in 1942."])
        rid = ReasonInDocuments(llm=llm)
        docs = [RetrievedDoc(doc_id="d1", text="long doc text...")]
        out = rid.denoise(query="who directed Casablanca?", docs=docs)
        assert len(out) == 1
        assert out[0].is_relevant is True
        assert "Bob" in out[0].refined_text

    def test_irrelevant_dropped_when_flagged(self):
        llm = StubLLM(responses=["NONE"])
        rid = ReasonInDocuments(llm=llm, drop_irrelevant=True)
        docs = [RetrievedDoc(doc_id="d1", text="trivia")]
        out = rid.denoise(query="q", docs=docs)
        assert out == []

    def test_irrelevant_kept_with_flag_when_not_dropping(self):
        llm = StubLLM(responses=["NONE"])
        rid = ReasonInDocuments(llm=llm, drop_irrelevant=False)
        docs = [RetrievedDoc(doc_id="d1", text="trivia")]
        out = rid.denoise(query="q", docs=docs)
        assert len(out) == 1
        assert out[0].is_relevant is False
        assert out[0].refined_text == ""

    def test_to_retrieved_filters_irrelevant(self):
        llm = StubLLM(responses=["fact A", "NONE"])
        rid = ReasonInDocuments(llm=llm)
        docs = [
            RetrievedDoc(doc_id="d1", text="..."),
            RetrievedDoc(doc_id="d2", text="..."),
        ]
        out = rid.denoise_to_retrieved(query="q", docs=docs)
        assert len(out) == 1
        assert out[0].doc_id == "d1"
        assert out[0].source.startswith("rid")

    def test_llm_error_fail_open(self):
        class BrokenLLM:
            name = "broken"
            def generate(self, prompt, *, max_tokens=512, stop=None):
                raise RuntimeError("network failure")

        rid = ReasonInDocuments(llm=BrokenLLM())
        docs = [RetrievedDoc(doc_id="d1", text="original")]
        out = rid.denoise(query="q", docs=docs)
        # Fail-open: original kept, marked relevant, no crash.
        assert out[0].is_relevant is True
        assert out[0].refined_text == "original"

    def test_empty_input(self):
        rid = ReasonInDocuments(llm=StubLLM())
        assert rid.denoise(query="q", docs=[]) == []


class TestComposeWithChainOfNote:
    def test_con_drops_then_rid_refines(self):
        # CoN drops d2 (no 'match'); RiD refines d1.
        def con_writer(*, query, doc_id, content):
            v = NoteVerdict.RELEVANT if "match" in content else NoteVerdict.IRRELEVANT
            score = 1.0 if v == NoteVerdict.RELEVANT else 0.0
            return DocVerdict(doc_id=doc_id, verdict=v, note="", score=score)

        gate = ChainOfNoteGate(note_writer=con_writer, threshold=0.5)
        rid = ReasonInDocuments(llm=StubLLM(responses=["refined fact"]))
        docs = [
            RetrievedDoc(doc_id="d1", text="match here"),
            RetrievedDoc(doc_id="d2", text="no signal"),
        ]
        out = compose_with_chain_of_note(rid=rid, chain_of_note_gate=gate, query="q", docs=docs)
        assert len(out) == 1
        assert out[0].doc_id == "d1"
        assert out[0].text == "refined fact"
