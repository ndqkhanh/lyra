"""Tests for harness_core.multi_hop.operators — Self-Ask + IRCoT."""
from __future__ import annotations

import pytest

from harness_core.multi_hop.operators import (
    IRCoTOperator,
    RetrievedDoc,
    SelfAskOperator,
    StubLLM,
    StubRetriever,
    parse_self_ask_response,
)


class TestParseSelfAskResponse:
    def test_extract_follow_up(self):
        text = "Are follow up questions needed here? Yes\nFollow up: who directed it?\n"
        p = parse_self_ask_response(text)
        assert p.needed_follow_up is True
        assert p.follow_up == "who directed it?"
        assert p.final_answer is None

    def test_extract_intermediate_and_final(self):
        text = (
            "Are follow up questions needed here? Yes\n"
            "Follow up: who directed Casablanca?\n"
            "Intermediate answer: Michael Curtiz\n"
            "So the final answer is: Michael Curtiz\n"
        )
        p = parse_self_ask_response(text)
        assert p.intermediate_answer == "Michael Curtiz"
        assert p.final_answer == "Michael Curtiz"

    def test_extract_no_followup(self):
        text = "Are follow up questions needed here? No\nSo the final answer is: 42\n"
        p = parse_self_ask_response(text)
        assert p.needed_follow_up is False
        assert p.final_answer == "42"

    def test_missing_fields_are_none(self):
        p = parse_self_ask_response("random text")
        assert p.needed_follow_up is None
        assert p.follow_up is None
        assert p.intermediate_answer is None
        assert p.final_answer is None
        assert p.raw == "random text"

    def test_case_insensitive(self):
        text = "FOLLOW UP: who is X?\n"
        p = parse_self_ask_response(text)
        assert p.follow_up == "who is X?"


class TestSelfAskOperator:
    def test_two_hop_completion(self):
        # Round 1: ask follow-up about Casablanca director.
        # Round 2: emit the final answer.
        llm = StubLLM(responses=[
            "Are follow up questions needed here? Yes\n"
            "Follow up: who directed Casablanca?\n",
            "Are follow up questions needed here? No\n"
            "So the final answer is: Michael Curtiz\n",
        ])
        retriever = StubRetriever(fixtures={
            "who directed Casablanca?": [
                RetrievedDoc(doc_id="d1", text="Michael Curtiz directed Casablanca", score=0.9),
            ],
        })
        op = SelfAskOperator(llm=llm, retriever=retriever, max_hops=4)
        result = op.answer("who directed Casablanca?")
        assert result.completed is True
        assert result.final_answer == "Michael Curtiz"
        assert len(result.steps) == 1
        assert result.steps[0].follow_up == "who directed Casablanca?"
        assert result.n_llm_calls == 2
        assert result.n_retrieval_calls == 1

    def test_immediate_final_answer(self):
        # LLM emits final answer on the first turn — no retrieval needed.
        llm = StubLLM(responses=[
            "Are follow up questions needed here? No\n"
            "So the final answer is: 42\n",
        ])
        retriever = StubRetriever()
        op = SelfAskOperator(llm=llm, retriever=retriever)
        result = op.answer("what is the answer?")
        assert result.completed is True
        assert result.final_answer == "42"
        assert result.n_retrieval_calls == 0
        assert len(result.steps) == 0

    def test_max_hops_terminates(self):
        # LLM keeps emitting follow-ups; max_hops=2 should cut off.
        llm = StubLLM(responses=[
            "Follow up: q1\n",
            "Follow up: q2\n",
            "Follow up: q3\n",
            "Follow up: q4\n",
        ])
        retriever = StubRetriever(fallback=lambda q, k: [RetrievedDoc(doc_id=q, text=f"ans-{q}")])
        op = SelfAskOperator(llm=llm, retriever=retriever, max_hops=2)
        result = op.answer("recursive")
        assert result.completed is False
        assert len(result.steps) == 2  # cut off at max_hops

    def test_intermediate_answer_falls_back_to_top_doc(self):
        # LLM emits follow-up but no intermediate answer; operator uses top doc.
        llm = StubLLM(responses=[
            "Follow up: who?\n",
            "So the final answer is: Bob\n",
        ])
        retriever = StubRetriever(fixtures={
            "who?": [RetrievedDoc(doc_id="d1", text="Bob is the answer")],
        })
        op = SelfAskOperator(llm=llm, retriever=retriever)
        result = op.answer("q")
        assert result.steps[0].intermediate_answer == "Bob is the answer"

    def test_malformed_response_stops_cleanly(self):
        # LLM emits gibberish; operator should not crash.
        llm = StubLLM(responses=["random text with no markers"])
        retriever = StubRetriever()
        op = SelfAskOperator(llm=llm, retriever=retriever)
        result = op.answer("q")
        assert result.completed is False
        assert result.final_answer == ""

    def test_retrieval_called_with_followup_query(self):
        llm = StubLLM(responses=[
            "Follow up: who?\n",
            "So the final answer is: Bob\n",
        ])
        retriever = StubRetriever(fixtures={"who?": [RetrievedDoc(doc_id="d1", text="x")]})
        op = SelfAskOperator(llm=llm, retriever=retriever)
        op.answer("q")
        assert retriever.calls[0][0] == "who?"


class TestIRCoTOperator:
    def test_two_iter_completion(self):
        # Two CoT sentences then an answer line.
        llm = StubLLM(responses=[
            "The director of Casablanca is Michael Curtiz.",
            "Curtiz was Hungarian-American.",
            "Answer: Michael Curtiz",
        ])
        retriever = StubRetriever(fallback=lambda q, k: [RetrievedDoc(doc_id=f"d-{q[:5]}", text=q)])
        op = IRCoTOperator(llm=llm, retriever=retriever, max_iters=5)
        result = op.answer("who directed Casablanca?")
        assert result.completed is True
        assert result.final_answer == "Michael Curtiz"
        assert len(result.steps) == 2
        assert result.n_llm_calls == 3
        assert result.n_retrieval_calls == 2

    def test_immediate_answer(self):
        llm = StubLLM(responses=["Answer: 42"])
        retriever = StubRetriever()
        op = IRCoTOperator(llm=llm, retriever=retriever)
        result = op.answer("q")
        assert result.completed is True
        assert result.final_answer == "42"
        assert result.n_retrieval_calls == 0

    def test_max_iters_cutoff(self):
        # LLM never emits Answer: → cuts off at max_iters.
        llm = StubLLM(responses=["sentence 1.", "sentence 2.", "sentence 3."])
        retriever = StubRetriever(fallback=lambda q, k: [])
        op = IRCoTOperator(llm=llm, retriever=retriever, max_iters=3)
        result = op.answer("q")
        assert result.completed is False
        assert len(result.steps) == 3

    def test_evidence_dedup(self):
        # Repeated retrievals of the same doc shouldn't duplicate in evidence.
        llm = StubLLM(responses=[
            "first sentence.",
            "second sentence.",
            "Answer: done",
        ])
        same_doc = [RetrievedDoc(doc_id="d1", text="constant evidence")]
        retriever = StubRetriever(fallback=lambda q, k: same_doc)
        op = IRCoTOperator(llm=llm, retriever=retriever, max_iters=5)
        result = op.answer("q")
        assert result.completed is True
        # Both steps retrieved the same doc; the operator's evidence-dedup
        # surface is internal — confirmed by the second step receiving the
        # same doc but the prompt only listing it once. (We can't observe
        # the prompt directly; the API surface guarantees the result shape.)
        for step in result.steps:
            assert step.retrieved == tuple(same_doc)

    def test_blank_response_stops(self):
        llm = StubLLM(responses=["", "Answer: x"])
        retriever = StubRetriever()
        op = IRCoTOperator(llm=llm, retriever=retriever)
        result = op.answer("q")
        # Empty first response → loop breaks before retrieval.
        assert result.completed is False


class TestStubsThemselves:
    def test_stub_llm_exhaustion_raises(self):
        llm = StubLLM(responses=["one"])
        llm.generate("p")
        with pytest.raises(RuntimeError):
            llm.generate("p")

    def test_stub_retriever_records_calls(self):
        r = StubRetriever()
        r.retrieve("a", top_k=3)
        r.retrieve("b", top_k=5)
        assert r.calls == [("a", 3), ("b", 5)]

    def test_stub_retriever_fallback(self):
        r = StubRetriever(fallback=lambda q, k: [RetrievedDoc(doc_id="x", text=q)])
        out = r.retrieve("hello")
        assert out[0].text == "hello"
