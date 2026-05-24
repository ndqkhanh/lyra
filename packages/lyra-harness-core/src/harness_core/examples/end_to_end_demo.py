"""End-to-end demo: graph → retrieval → operators → gates → pipeline → program.

A self-contained, deterministic example that composes 12+ harness_core
modules into one working multi-hop research workflow. Run as a script
(``python -m harness_core.examples.end_to_end_demo``) or import +
``run_research_demo()``. The integration test ``test_end_to_end_demo.py``
asserts the canonical trajectory.
"""
from __future__ import annotations

from dataclasses import dataclass, field
from typing import Any, Optional

from ..constitution import Constitution, ConstitutionRegistry, Principle
from ..evals import BudgetController
from ..gates import ChainOfNoteGate, DocVerdict, NoteVerdict
from ..multi_hop import (
    HippoRAGRetriever,
    IRCoTOperator,
    RetrievedDoc,
    SelfAskOperator,
    SimpleDocument,
    SimpleEdge,
    SimpleGraph,
    SimpleNode,
    StubLLM,
    StubRetriever,
)
from ..pipeline import MultiHopPipeline, PipelineResult
from ..programs import (
    BootstrapFewShot,
    Example,
    MultiHopProgram,
    Signature,
)
from ..routing import BELLERouter


@dataclass
class DemoOutput:
    """The full output of a demo run — everything an integration test wants."""

    pipeline_result: PipelineResult
    program_output: Any  # ProgramOutput; typed loosely to avoid circular import
    constitution: Constitution
    budget_remaining: int


# --- Substrate construction --------------------------------------------


def build_demo_graph() -> SimpleGraph:
    """A 5-node Casablanca-themed graph for demo purposes."""
    return SimpleGraph.from_pairs(
        edges=[
            ("alice", "bob"),
            ("bob", "casablanca"),
            ("casablanca", "1942"),
            ("casablanca", "warner-bros"),
            ("warner-bros", "1923"),
        ],
        titles={
            "alice": "Alice",
            "bob": "Bob Curtiz (director)",
            "casablanca": "Casablanca (film)",
            "1942": "1942 release year",
            "warner-bros": "Warner Bros (studio)",
            "1923": "1923 founding year",
        },
    )


def build_demo_documents() -> list[SimpleDocument]:
    """Five documents anchored to the demo graph nodes."""
    return [
        SimpleDocument(
            doc_id="d1",
            text="Alice is married to Bob Curtiz the director.",
            anchor_node_id="alice",
        ),
        SimpleDocument(
            doc_id="d2",
            text="Bob Curtiz directed the film Casablanca.",
            anchor_node_id="bob",
        ),
        SimpleDocument(
            doc_id="d3",
            text="Casablanca was released in 1942 by Warner Bros.",
            anchor_node_id="casablanca",
        ),
        SimpleDocument(
            doc_id="d4",
            text="Warner Bros was founded in 1923.",
            anchor_node_id="warner-bros",
        ),
        SimpleDocument(
            doc_id="d5",
            text="Unrelated coffee-shop trivia about espresso machines.",
            anchor_node_id=None,
        ),
    ]


def build_demo_retriever() -> HippoRAGRetriever:
    """Build + index a HippoRAG retriever over the demo substrate."""
    retriever = HippoRAGRetriever(graph=build_demo_graph())
    retriever.build_index(build_demo_documents())
    return retriever


# --- Stub LM / retriever for deterministic demo ------------------------


def _build_stub_llm_for_self_ask() -> StubLLM:
    """Scripted Self-Ask trajectory: one follow-up then final answer."""
    return StubLLM(responses=[
        "Are follow up questions needed here? Yes\n"
        "Follow up: who directed Casablanca?\n",
        "Are follow up questions needed here? No\n"
        "So the final answer is: Bob Curtiz\n",
    ])


def _build_stub_llm_for_ircot() -> StubLLM:
    """Scripted IRCoT trajectory."""
    return StubLLM(responses=[
        "Casablanca was directed by Bob Curtiz.",
        "Curtiz worked for Warner Bros.",
        "Answer: Bob Curtiz",
    ])


def _build_demo_retriever_stub() -> StubRetriever:
    """Stub retriever returning the indexed docs by query."""
    return StubRetriever(fixtures={
        "who directed Casablanca?": [
            RetrievedDoc(
                doc_id="d2",
                text="Bob Curtiz directed the film Casablanca.",
                score=0.95,
                source="demo",
            ),
        ],
    }, fallback=lambda q, k: [
        RetrievedDoc(doc_id="d3", text="Casablanca was released in 1942 by Warner Bros.", score=0.6),
    ])


def _build_chain_of_note_gate() -> ChainOfNoteGate:
    """Deterministic Chain-of-Note gate: docs containing 'Casablanca' or
    'Curtiz' or 'Warner' are RELEVANT; others IRRELEVANT."""
    def note_writer(*, query, doc_id, content):
        relevant_terms = ("casablanca", "curtiz", "warner")
        is_relevant = any(t in content.lower() for t in relevant_terms)
        if is_relevant:
            return DocVerdict(
                doc_id=doc_id,
                verdict=NoteVerdict.RELEVANT,
                note="contains demo-relevant term",
                score=1.0,
            )
        return DocVerdict(
            doc_id=doc_id,
            verdict=NoteVerdict.IRRELEVANT,
            note="off-topic",
            score=0.0,
        )
    return ChainOfNoteGate(note_writer=note_writer, threshold=0.5)


# --- Pipeline construction ---------------------------------------------


def build_demo_pipeline(
    *,
    budget_tokens: Optional[int] = 10_000,
) -> MultiHopPipeline:
    """Compose the canonical pipeline for the demo.

    Wires: BELLE router + Self-Ask + IRCoT + Chain-of-Note + budget.
    """
    self_ask = SelfAskOperator(
        llm=_build_stub_llm_for_self_ask(),
        retriever=_build_demo_retriever_stub(),
        max_hops=2,
    )
    ircot = IRCoTOperator(
        llm=_build_stub_llm_for_ircot(),
        retriever=_build_demo_retriever_stub(),
        max_iters=4,
    )
    pipeline = MultiHopPipeline(
        router=BELLERouter(),
        self_ask=self_ask,
        ircot=ircot,
        chain_of_note=_build_chain_of_note_gate(),
        budget=BudgetController(budget_tokens=budget_tokens) if budget_tokens else None,
    )
    return pipeline


def build_demo_program(
    *,
    pipeline: Optional[MultiHopPipeline] = None,
    budget_tokens: Optional[int] = 10_000,
) -> MultiHopProgram:
    """Wrap the pipeline in a typed program with a Signature."""
    if pipeline is None:
        pipeline = build_demo_pipeline(budget_tokens=budget_tokens)
    sig = Signature(
        instruction=(
            "You are a research assistant. Answer the multi-hop question with "
            "a precise factual response, citing the bridge entity used."
        ),
        inputs=("question",),
        output="answer",
    )
    return MultiHopProgram(pipeline=pipeline, signature=sig)


# --- Running the demo --------------------------------------------------


def _build_constitution() -> Constitution:
    """Demo user constitution — three principles."""
    return Constitution(
        user_id="demo-user",
        principles=(
            Principle(text="Always cite the source for factual claims.", weight=2.0),
            Principle(text="Prefer verifiable answers over speculation.", weight=1.5),
            Principle(text="Be terse — single sentence when possible.", weight=1.0),
        ),
    )


def run_research_demo(
    *,
    question: str = "who directed Casablanca",
    budget_tokens: int = 10_000,
) -> DemoOutput:
    """Run the canonical demo end-to-end. Returns a typed output for inspection.

    >>> out = run_research_demo()
    >>> out.pipeline_result.completed
    True
    >>> "Bob" in out.pipeline_result.answer or "Curtiz" in out.pipeline_result.answer
    True
    """
    # 1. Build the program (wires substrate + operators + gates + budget).
    program = build_demo_program(budget_tokens=budget_tokens)

    # 2. Set up a constitution registry + retrieve the demo user's constitution.
    registry = ConstitutionRegistry()
    constitution = _build_constitution()
    registry.put(constitution)

    # 3. Run the program (uncompiled — single-shot baseline).
    output = program(question=question)

    # 4. Surface the budget remaining for cost-accounting integration.
    budget_remaining = (
        program.pipeline.budget.remaining()
        if program.pipeline.budget is not None
        else 0
    )

    return DemoOutput(
        pipeline_result=output.pipeline_result,
        program_output=output,
        constitution=constitution,
        budget_remaining=budget_remaining,
    )


def main() -> None:
    """Entry point for ``python -m harness_core.examples.end_to_end_demo``."""
    out = run_research_demo()
    print("=" * 60)
    print("harness_core end-to-end demo")
    print("=" * 60)
    print(f"Question:      who directed Casablanca")
    print(f"Answer:        {out.pipeline_result.answer}")
    print(f"Operator used: {out.pipeline_result.operator_used}")
    print(f"Hops:          {out.pipeline_result.n_hops}")
    print(f"LLM calls:     {out.pipeline_result.n_llm_calls}")
    print(f"Retrievals:    {out.pipeline_result.n_retrieval_calls}")
    print(f"Docs filtered: {out.pipeline_result.n_docs_filtered}")
    print(f"Docs kept:     {out.pipeline_result.n_docs_kept}")
    print(f"Completed:     {out.pipeline_result.completed}")
    print(f"Budget left:   {out.budget_remaining}")
    print(f"Steps:         {[s.value for s in out.pipeline_result.steps]}")
    print()
    print("User constitution:")
    print(out.constitution.render())


__all__ = [
    "DemoOutput",
    "build_demo_graph",
    "build_demo_documents",
    "build_demo_pipeline",
    "build_demo_program",
    "build_demo_retriever",
    "run_research_demo",
    "main",
]


if __name__ == "__main__":
    main()
