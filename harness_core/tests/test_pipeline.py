"""Tests for harness_core.pipeline.MultiHopPipeline — end-to-end composition."""
from __future__ import annotations

import pytest

from harness_core.evals import BudgetController
from harness_core.gates import ChainOfNoteGate, DocVerdict, NoteVerdict
from harness_core.multi_hop import (
    DecompositionCache,
    IRCoTOperator,
    RetrievedDoc,
    SelfAskOperator,
    StubLLM,
    StubRetriever,
)
from harness_core.pipeline import MultiHopPipeline, PipelineResult, PipelineStep
from harness_core.routing import BELLERouter, QueryType


def _self_ask_with_immediate_answer(answer: str = "42") -> SelfAskOperator:
    """Self-Ask that returns final answer on the first turn."""
    llm = StubLLM(responses=[
        f"Are follow up questions needed here? No\nSo the final answer is: {answer}\n",
    ])
    retriever = StubRetriever()
    return SelfAskOperator(llm=llm, retriever=retriever, max_hops=2)


def _self_ask_with_one_hop(answer: str = "Curtiz") -> SelfAskOperator:
    """Self-Ask that asks one follow-up then answers."""
    llm = StubLLM(responses=[
        "Are follow up questions needed here? Yes\nFollow up: who directed it?\n",
        f"Are follow up questions needed here? No\nSo the final answer is: {answer}\n",
    ])
    retriever = StubRetriever(fixtures={
        "who directed it?": [RetrievedDoc(doc_id="d1", text="Curtiz directed Casablanca")],
    })
    return SelfAskOperator(llm=llm, retriever=retriever, max_hops=2)


def _ircot_with_two_steps(answer: str = "ok") -> IRCoTOperator:
    llm = StubLLM(responses=[
        "First sentence.",
        "Second sentence.",
        f"Answer: {answer}",
    ])
    retriever = StubRetriever(fallback=lambda q, k: [RetrievedDoc(doc_id="d1", text="x")])
    return IRCoTOperator(llm=llm, retriever=retriever, max_iters=4)


# --- Smoke tests --------------------------------------------------------


class TestPipelineSmoke:
    def test_single_hop_via_self_ask(self):
        pipeline = MultiHopPipeline(
            router=BELLERouter(),
            self_ask=_self_ask_with_immediate_answer("42"),
            ircot=_ircot_with_two_steps(),
        )
        result = pipeline.answer("paris france capital")
        assert result.completed is True
        assert result.answer == "42"
        # Single-hop query → operator_self_ask via fallback path.
        assert result.operator_used == "self_ask"
        assert PipelineStep.COMPLETED in result.steps

    def test_bridge_query_routes_to_self_ask(self):
        pipeline = MultiHopPipeline(
            router=BELLERouter(),
            self_ask=_self_ask_with_one_hop(),
            ircot=_ircot_with_two_steps(),
        )
        result = pipeline.answer("who directed Casablanca")
        assert result.route_decision.query_type == QueryType.MULTI_HOP_BRIDGE
        assert result.operator_used == "self_ask"
        assert result.completed is True
        assert PipelineStep.OPERATOR_SELF_ASK in result.steps

    def test_global_sensemaking_routes_to_ircot(self):
        pipeline = MultiHopPipeline(
            router=BELLERouter(),
            self_ask=_self_ask_with_immediate_answer(),
            ircot=_ircot_with_two_steps("done"),
        )
        result = pipeline.answer("summarize the main themes across the corpus")
        assert result.route_decision.query_type == QueryType.GLOBAL_SENSEMAKING
        assert result.operator_used == "ircot"
        assert PipelineStep.OPERATOR_IRCOT in result.steps


# --- Cache integration --------------------------------------------------


class TestPipelineCache:
    def test_cache_miss_then_hit(self):
        cache = DecompositionCache()
        pipeline = MultiHopPipeline(
            router=BELLERouter(),
            self_ask=_self_ask_with_one_hop("answer-1"),
            ircot=_ircot_with_two_steps(),
            decomposition_cache=cache,
        )
        first = pipeline.answer("who directed Casablanca")
        assert first.cache_hit is False
        assert first.completed is True
        # Second call should hit the cache.
        # Replace the operator so we'd fail without cache hit.
        pipeline.self_ask = _self_ask_with_immediate_answer("would-hit-this")
        second = pipeline.answer("who directed Casablanca")
        assert second.cache_hit is True
        assert second.operator_used == "cached"
        assert PipelineStep.CACHE_HIT in second.steps

    def test_cache_namespace_isolation(self):
        cache = DecompositionCache()
        pipeline = MultiHopPipeline(
            router=BELLERouter(),
            self_ask=_self_ask_with_one_hop("answer"),
            ircot=_ircot_with_two_steps(),
            decomposition_cache=cache,
        )
        pipeline.answer("who directed Casablanca", namespace="proj-A")
        # Different namespace should miss.
        # Reset operator so a hit would surface a different answer.
        pipeline.self_ask = _self_ask_with_immediate_answer("different")
        result = pipeline.answer("who directed Casablanca", namespace="proj-B")
        assert result.cache_hit is False
        assert result.answer == "different"

    def test_no_cache_doesnt_break(self):
        pipeline = MultiHopPipeline(
            router=BELLERouter(),
            self_ask=_self_ask_with_immediate_answer(),
            ircot=_ircot_with_two_steps(),
            decomposition_cache=None,
        )
        result = pipeline.answer("anything")
        assert result.cache_hit is False
        assert result.completed is True


# --- Chain-of-Note gate -------------------------------------------------


class TestPipelineGate:
    def _con_writer_passes_match(self, *, query, doc_id, content):
        v = NoteVerdict.RELEVANT if "match" in content else NoteVerdict.IRRELEVANT
        score = 1.0 if v == NoteVerdict.RELEVANT else 0.0
        return DocVerdict(doc_id=doc_id, verdict=v, note="", score=score)

    def test_gate_filters_irrelevant_docs(self):
        gate = ChainOfNoteGate(note_writer=self._con_writer_passes_match, threshold=0.5)
        pipeline = MultiHopPipeline(
            router=BELLERouter(),
            self_ask=_self_ask_with_one_hop(),
            ircot=_ircot_with_two_steps(),
            chain_of_note=gate,
        )
        # The fixture in _self_ask_with_one_hop provides a single doc whose text
        # contains "Casablanca" but not "match" — gate will drop it.
        result = pipeline.answer("who directed Casablanca")
        # 1 retrieved, 0 with "match" → all filtered.
        assert result.n_docs_filtered == 1
        assert result.n_docs_kept == 0

    def test_no_gate_keeps_all_docs(self):
        pipeline = MultiHopPipeline(
            router=BELLERouter(),
            self_ask=_self_ask_with_one_hop(),
            ircot=_ircot_with_two_steps(),
            chain_of_note=None,
        )
        result = pipeline.answer("who directed Casablanca")
        assert result.n_docs_filtered == 0
        assert result.n_docs_kept == 1


# --- Budget controller --------------------------------------------------


class TestPipelineBudget:
    def test_budget_tracked_in_result(self):
        budget = BudgetController(budget_tokens=10_000)
        pipeline = MultiHopPipeline(
            router=BELLERouter(),
            self_ask=_self_ask_with_immediate_answer(),
            ircot=_ircot_with_two_steps(),
            budget=budget,
        )
        result = pipeline.answer("anything")
        assert result.budget_remaining is not None
        assert result.budget_remaining < 10_000

    def test_budget_exhausted_returns_partial(self):
        budget = BudgetController(budget_tokens=100)  # tiny budget
        pipeline = MultiHopPipeline(
            router=BELLERouter(),
            self_ask=_self_ask_with_immediate_answer(),
            ircot=_ircot_with_two_steps(),
            budget=budget,
            estimated_tokens_per_llm_call=1000,  # way over budget
        )
        result = pipeline.answer("anything")
        assert result.completed is False
        assert PipelineStep.BUDGET_EXHAUSTED in result.steps
        assert "tokens" in result.error.lower()


# --- Edge cases ---------------------------------------------------------


class TestPipelineEdgeCases:
    def test_no_operators_wired(self):
        pipeline = MultiHopPipeline(router=BELLERouter())
        result = pipeline.answer("anything")
        assert result.completed is False
        assert result.error == "no operator wired"
        assert result.operator_used == "none"

    def test_only_ircot_wired_handles_bridge(self):
        # No self_ask → bridge query falls through to ircot.
        pipeline = MultiHopPipeline(
            router=BELLERouter(),
            self_ask=None,
            ircot=_ircot_with_two_steps("answer"),
        )
        result = pipeline.answer("who directed Casablanca")
        assert result.operator_used == "ircot"
        assert result.completed is True

    def test_only_self_ask_wired_handles_sensemaking(self):
        pipeline = MultiHopPipeline(
            router=BELLERouter(),
            self_ask=_self_ask_with_immediate_answer("via-self-ask"),
            ircot=None,
        )
        result = pipeline.answer("summarize the main themes across the corpus")
        # ircot wasn't wired, so falls through to self_ask via SINGLE_HOP path.
        assert result.operator_used == "self_ask"
        assert result.answer == "via-self-ask"

    def test_elapsed_time_recorded(self):
        pipeline = MultiHopPipeline(
            router=BELLERouter(),
            self_ask=_self_ask_with_immediate_answer(),
            ircot=_ircot_with_two_steps(),
        )
        result = pipeline.answer("anything")
        assert result.elapsed_seconds >= 0
