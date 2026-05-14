"""Tests for Phase C: HopTrace + GreedySearchPolicy."""
from __future__ import annotations

import pytest

from lyra_research.hop_trace import GreedySearchPolicy, HopTrace, MultiHopResult


class TestHopTrace:
    def test_defaults(self):
        h = HopTrace(hop_index=0, query="q")
        assert h.passages == []
        assert h.support_score == 0.0
        assert h.source_refs == []

    def test_invalid_support_score(self):
        with pytest.raises(ValueError):
            HopTrace(hop_index=0, query="q", support_score=-0.1)


class TestMultiHopResult:
    def test_mean_support_empty(self):
        r = MultiHopResult(answer="", hops=(), terminated_early=False, total_hops=0)
        assert r.mean_support == 0.0

    def test_weakest_hop(self):
        hops = (
            HopTrace(0, "q", support_score=0.8),
            HopTrace(1, "q", support_score=0.3),
        )
        r = MultiHopResult("ans", hops, terminated_early=False, total_hops=2)
        weak = r.weakest_hop()
        assert weak is not None
        assert weak.support_score == 0.3

    def test_weakest_hop_empty(self):
        r = MultiHopResult("", (), terminated_early=False, total_hops=0)
        assert r.weakest_hop() is None


class TestGreedySearchPolicy:
    def test_first_query_is_question(self):
        policy = GreedySearchPolicy()
        q = policy.next_query("what is x?", [])
        assert q == "what is x?"

    def test_subsequent_query_includes_context(self):
        policy = GreedySearchPolicy()
        hops = [HopTrace(0, "q", reasoning_step="x is a module")]
        q = policy.next_query("what is x?", hops)
        assert "x is a module" in q

    def test_no_stop_on_low_score(self):
        policy = GreedySearchPolicy(stop_threshold=0.9)
        hops = [HopTrace(0, "q", support_score=0.5)]
        assert not policy.should_stop(hops)

    def test_stop_on_high_score(self):
        policy = GreedySearchPolicy(stop_threshold=0.85)
        hops = [HopTrace(0, "q", support_score=0.95)]
        assert policy.should_stop(hops)

    def test_stop_on_final_answer_phrase(self):
        policy = GreedySearchPolicy()
        hops = [HopTrace(0, "q", reasoning_step="Final answer: 42", support_score=0.1)]
        assert policy.should_stop(hops)

    def test_no_stop_on_empty_hops(self):
        policy = GreedySearchPolicy()
        assert not policy.should_stop([])

    def test_invalid_threshold_raises(self):
        with pytest.raises(ValueError):
            GreedySearchPolicy(stop_threshold=1.5)
