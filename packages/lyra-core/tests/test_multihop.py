"""Tests for Phase C: IRCoT multi-hop reasoning engine."""
from __future__ import annotations

import pytest

from lyra_core.multihop import HopRecord, IRCoTEngine, MultiHopAnswer


# ------------------------------------------------------------------ #
# Stub implementations                                                 #
# ------------------------------------------------------------------ #

class FixedRetriever:
    def __init__(self, passages: list[str]) -> None:
        self._passages = passages

    def retrieve(self, query: str, top_k: int = 3) -> list[str]:
        return self._passages[:top_k]


class FixedReasoner:
    """Returns a fixed reasoning step and support score each call."""

    def __init__(self, steps: list[tuple[str, float]]) -> None:
        self._steps = list(steps)
        self._idx = 0

    def reason(self, question, passages, prior_hops):
        if self._idx < len(self._steps):
            reasoning, score = self._steps[self._idx]
            self._idx += 1
        else:
            reasoning, score = "default", 0.0
        return reasoning, score, []


# ------------------------------------------------------------------ #
# HopRecord                                                            #
# ------------------------------------------------------------------ #

class TestHopRecord:
    def test_defaults(self):
        h = HopRecord(hop_index=0, query="q")
        assert h.passages == []
        assert h.support_score == 0.0
        assert h.source_refs == []

    def test_invalid_support_score(self):
        with pytest.raises(ValueError):
            HopRecord(hop_index=0, query="q", support_score=1.5)


# ------------------------------------------------------------------ #
# MultiHopAnswer                                                       #
# ------------------------------------------------------------------ #

class TestMultiHopAnswer:
    def test_mean_support_empty(self):
        ans = MultiHopAnswer(answer="", hops=(), stopped_early=False)
        assert ans.mean_support == 0.0

    def test_mean_support_calculated(self):
        hops = (
            HopRecord(0, "q1", support_score=0.6),
            HopRecord(1, "q2", support_score=0.8),
        )
        ans = MultiHopAnswer(answer="ans", hops=hops, stopped_early=False)
        assert abs(ans.mean_support - 0.7) < 1e-9


# ------------------------------------------------------------------ #
# IRCoTEngine                                                          #
# ------------------------------------------------------------------ #

class TestIRCoTEngine:
    def test_single_hop_low_support(self):
        engine = IRCoTEngine(
            FixedRetriever(["doc1"]),
            FixedReasoner([("step1", 0.3)]),
            max_hops=1,
        )
        result = engine.run("what is x?")
        assert len(result.hops) == 1
        assert not result.stopped_early

    def test_stops_early_on_high_support(self):
        engine = IRCoTEngine(
            FixedRetriever(["doc"]),
            FixedReasoner([("step1", 0.5), ("step2", 0.95)]),
            max_hops=4,
            stop_threshold=0.90,
        )
        result = engine.run("q")
        assert result.stopped_early
        assert len(result.hops) == 2

    def test_stops_early_on_final_answer_phrase(self):
        engine = IRCoTEngine(
            FixedRetriever([]),
            FixedReasoner([("Final answer: 42", 0.1)]),
            max_hops=4,
        )
        result = engine.run("what is the answer?")
        assert result.stopped_early
        assert result.answer == "Final answer: 42"

    def test_runs_max_hops(self):
        engine = IRCoTEngine(
            FixedRetriever(["p"]),
            FixedReasoner([("step", 0.1)] * 10),
            max_hops=3,
            stop_threshold=0.99,
        )
        result = engine.run("q")
        assert len(result.hops) == 3
        assert not result.stopped_early

    def test_passages_passed_to_reasoner(self):
        received: list[list[str]] = []

        class CapturingReasoner:
            def reason(self, question, passages, prior_hops):
                received.append(list(passages))
                return "done", 0.99, []

        engine = IRCoTEngine(
            FixedRetriever(["a", "b", "c"]),
            CapturingReasoner(),
            max_hops=2,
            stop_threshold=0.95,
        )
        engine.run("q")
        assert received[0] == ["a", "b", "c"]

    def test_invalid_max_hops_raises(self):
        with pytest.raises(ValueError):
            IRCoTEngine(FixedRetriever([]), FixedReasoner([]), max_hops=0)

    def test_query_includes_prior_context(self):
        queries: list[str] = []

        class QueryCapturingRetriever:
            def retrieve(self, query: str, top_k: int = 3) -> list[str]:
                queries.append(query)
                return []

        engine = IRCoTEngine(
            QueryCapturingRetriever(),
            FixedReasoner([("step1", 0.1), ("step2", 0.99)]),
            max_hops=3,
        )
        engine.run("original question")
        assert queries[0] == "original question"
        assert "step1" in queries[1]
