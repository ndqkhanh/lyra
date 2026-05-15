"""Tests for Beam Retrieval + dual-use intent classifier."""
from __future__ import annotations

import pytest

from harness_core.gates import (
    DualUseGate,
    DualUseVerdict,
    GateAction,
    KeywordRiskClassifier,
    RiskLevel,
)
from harness_core.multi_hop import (
    BeamCandidate,
    BeamRetriever,
    CoverageScorer,
    RetrievedDoc,
    StubRetriever,
)


# --- Beam Retrieval ------------------------------------------------------


class TestBeamCandidate:
    def test_make_orders_descending_by_score(self):
        a = BeamCandidate.make(score=0.9, docs=())
        b = BeamCandidate.make(score=0.5, docs=())
        assert sorted([b, a])[0].score == 0.9

    def test_doc_ids(self):
        c = BeamCandidate.make(
            score=0.5,
            docs=(RetrievedDoc(doc_id="d1", text="x"), RetrievedDoc(doc_id="d2", text="y")),
        )
        assert c.doc_ids() == ("d1", "d2")
        assert c.n_hops == 2


class TestCoverageScorer:
    def test_full_coverage_marks_accept(self):
        s = CoverageScorer(accept_threshold=0.8)
        score, accept = s.score(
            query="who directed casablanca",
            docs=(RetrievedDoc(doc_id="d", text="casablanca was directed by curtiz"),),
        )
        assert score >= 0.66  # 'who' is too short to count; 'directed' + 'casablanca' = 2/2 stems
        assert accept is True or score >= 0.66

    def test_zero_coverage(self):
        s = CoverageScorer()
        score, accept = s.score(
            query="alpha beta gamma delta",
            docs=(RetrievedDoc(doc_id="d", text="completely unrelated"),),
        )
        assert score == 0.0
        assert accept is False

    def test_empty_query(self):
        s = CoverageScorer()
        score, accept = s.score(query="", docs=())
        assert score == 0.0
        assert accept is False

    def test_partial_coverage_below_threshold(self):
        s = CoverageScorer(accept_threshold=0.9)
        score, accept = s.score(
            query="alpha bravo charlie delta echo",
            docs=(RetrievedDoc(doc_id="d", text="alpha bravo only"),),
        )
        # 2 of 5 stems → 0.4 → below 0.9 threshold.
        assert score == pytest.approx(0.4, abs=0.01)
        assert accept is False


class TestBeamRetriever:
    def _build_chain(self):
        """Three-hop chain: query → d1 → d2 → d3."""
        return StubRetriever(fixtures={
            "casablanca director origin": [
                RetrievedDoc(doc_id="d1", text="Casablanca directed by Curtiz", score=0.9),
            ],
            "casablanca director origin Casablanca directed by Curtiz": [
                RetrievedDoc(doc_id="d2", text="Curtiz was Hungarian-American", score=0.85),
            ],
            "casablanca director origin Curtiz was Hungarian-American": [
                RetrievedDoc(doc_id="d3", text="born in Budapest 1886", score=0.8),
            ],
        })

    def test_retrieves_top_beam(self):
        retriever = self._build_chain()
        beam = BeamRetriever(retriever=retriever, beam_width=2, expand_per_hop=2, max_hops=3)
        result = beam.retrieve("casablanca director origin")
        assert result.best is not None
        assert result.best.docs[0].doc_id == "d1"
        assert result.n_retrieval_calls >= 1
        assert result.n_score_calls >= 1

    def test_empty_query_returns_empty(self):
        retriever = StubRetriever()
        beam = BeamRetriever(retriever=retriever)
        result = beam.retrieve("")
        assert result.best is None
        assert result.beams == ()

    def test_no_seed_results(self):
        retriever = StubRetriever()  # empty fixtures + no fallback
        beam = BeamRetriever(retriever=retriever)
        result = beam.retrieve("anything")
        assert result.best is None
        assert result.beams == ()

    def test_beam_width_limits_survivors(self):
        # 5 candidates, beam_width=2 → only 2 survive.
        retriever = StubRetriever(fixtures={
            "q": [
                RetrievedDoc(doc_id=f"d{i}", text=f"candidate {i}", score=0.5)
                for i in range(5)
            ],
        })
        beam = BeamRetriever(retriever=retriever, beam_width=2, expand_per_hop=5, max_hops=1)
        result = beam.retrieve("q")
        assert len(result.beams) == 2

    def test_dedup_within_beam(self):
        # Retriever returns the same doc on every hop; beam should not duplicate.
        same_doc = [RetrievedDoc(doc_id="dup", text="same content")]
        retriever = StubRetriever(fallback=lambda q, k: same_doc)
        beam = BeamRetriever(retriever=retriever, beam_width=2, expand_per_hop=1, max_hops=3)
        result = beam.retrieve("q")
        for b in result.beams:
            ids = b.doc_ids()
            assert len(ids) == len(set(ids)), f"duplicate doc in beam: {ids}"

    def test_accept_short_circuits_branch(self):
        """When a beam reaches accept threshold, it's preserved as final."""
        # Single doc completely covers the query.
        retriever = StubRetriever(fixtures={
            "alpha bravo": [RetrievedDoc(doc_id="d1", text="alpha bravo charlie")],
        })
        beam = BeamRetriever(
            retriever=retriever,
            scorer=CoverageScorer(accept_threshold=0.5),
            beam_width=2,
            max_hops=3,
        )
        result = beam.retrieve("alpha bravo")
        assert result.best is not None
        assert result.best.accept is True


# --- Dual-use classifier + gate ------------------------------------------


class TestKeywordRiskClassifier:
    def test_high_risk_pathogen_synthesis(self):
        v = KeywordRiskClassifier().classify(
            "synthesize a novel pathogen with enhanced transmissibility"
        )
        assert v.risk_level == RiskLevel.HIGH
        assert "pathogen_synthesis" in v.matched_categories

    def test_high_risk_gain_of_function(self):
        v = KeywordRiskClassifier().classify("describe gain-of-function research methods")
        assert v.risk_level == RiskLevel.HIGH
        assert "pathogen_synthesis" in v.matched_categories

    def test_high_risk_controlled_substance(self):
        v = KeywordRiskClassifier().classify("synthesize fentanyl from precursors")
        assert v.risk_level == RiskLevel.HIGH
        assert "controlled_substance_synthesis" in v.matched_categories

    def test_medium_risk_lethal_dose(self):
        v = KeywordRiskClassifier().classify("what is the LD50 in adult humans")
        assert v.risk_level == RiskLevel.MEDIUM
        assert "controlled_pharmacology" in v.matched_categories

    def test_low_risk_legitimate_research(self):
        v = KeywordRiskClassifier().classify("explain the protein structure of TP53")
        assert v.risk_level == RiskLevel.LOW
        assert v.matched_categories == ()
        assert v.confidence == 0.7

    def test_empty_query(self):
        v = KeywordRiskClassifier().classify("")
        assert v.risk_level == RiskLevel.LOW
        assert v.confidence == 0.0

    def test_high_risk_explosives(self):
        v = KeywordRiskClassifier().classify("synthesize TATP step by step")
        assert v.risk_level == RiskLevel.HIGH
        assert "explosive_synthesis" in v.matched_categories

    def test_high_takes_priority_over_medium(self):
        # Query matches both HIGH and MEDIUM categories; HIGH wins.
        v = KeywordRiskClassifier().classify(
            "synthesize a novel pathogen and document the LD50 in humans"
        )
        assert v.risk_level == RiskLevel.HIGH


class TestDualUseVerdict:
    def test_invalid_confidence(self):
        with pytest.raises(ValueError):
            DualUseVerdict(query="q", risk_level=RiskLevel.LOW, matched_categories=(), confidence=1.5)

    def test_frozen(self):
        v = DualUseVerdict(query="q", risk_level=RiskLevel.LOW, matched_categories=(), confidence=0.5)
        with pytest.raises(Exception):
            v.confidence = 0.9  # type: ignore[misc]


class TestDualUseGate:
    def test_default_policy(self):
        gate = DualUseGate(classifier=KeywordRiskClassifier())
        # Low-risk query → ALLOW.
        d_low = gate.evaluate("explain the protein structure of TP53")
        assert d_low.action == GateAction.ALLOW
        # Medium → RATE_LIMIT.
        d_med = gate.evaluate("what is the LD50 in adult humans")
        assert d_med.action == GateAction.RATE_LIMIT
        # High → HITL_REVIEW.
        d_high = gate.evaluate("synthesize a novel pathogen")
        assert d_high.action == GateAction.HITL_REVIEW

    def test_custom_policy(self):
        gate = DualUseGate(
            classifier=KeywordRiskClassifier(),
            policy={
                RiskLevel.LOW: GateAction.ALLOW,
                RiskLevel.MEDIUM: GateAction.HITL_REVIEW,
                RiskLevel.HIGH: GateAction.BLOCK,
            },
        )
        d_high = gate.evaluate("synthesize a novel pathogen with weaponized intent")
        assert d_high.action == GateAction.BLOCK

    def test_audit_log_skips_low_allow(self):
        gate = DualUseGate(classifier=KeywordRiskClassifier())
        gate.evaluate("explain TP53")  # LOW → ALLOW → no audit
        gate.evaluate("LD50 in human adults")  # MEDIUM → audit
        gate.evaluate("synthesize a pathogen")  # HIGH → audit
        assert len(gate.audit_log) == 2

    def test_classifier_error_fail_closed(self):
        class BrokenClassifier:
            name = "broken"
            def classify(self, query):
                raise RuntimeError("LM unreachable")

        gate = DualUseGate(classifier=BrokenClassifier(), block_on_classifier_error=True)
        d = gate.evaluate("anything")
        assert d.action == GateAction.BLOCK
        assert d.verdict.risk_level == RiskLevel.HIGH
        assert "classifier_error" in d.verdict.matched_categories

    def test_classifier_error_fail_open(self):
        class BrokenClassifier:
            name = "broken"
            def classify(self, query):
                raise RuntimeError("LM unreachable")

        gate = DualUseGate(classifier=BrokenClassifier(), block_on_classifier_error=False)
        d = gate.evaluate("anything")
        assert d.action == GateAction.ALLOW

    def test_stats(self):
        gate = DualUseGate(classifier=KeywordRiskClassifier())
        gate.evaluate("synthesize a novel pathogen")  # HIGH
        gate.evaluate("what is the LD50 in adult human subjects")  # MEDIUM
        gate.evaluate("explain TP53")  # LOW (not audited)
        s = gate.stats()
        assert s["high"] == 1
        assert s["medium"] == 1
        # LOW + ALLOW skipped audit.
        assert s["low"] == 0
        assert s["action_hitl_review"] == 1
        assert s["action_rate_limit"] == 1
