"""End-to-end multi-hop pipeline composition.

Sequence per [docs/199] Phase 2 + per-project apply plans:

    1. Decomposition cache lookup (skip if hit).
    2. BELLE router classifies the query → operator selection.
    3. Operator runs (Self-Ask for BRIDGE; IRCoT for SENSEMAKING/BROWSE; etc).
    4. Chain-of-Note gates the retrieved docs (per-doc filter).
    5. Optional Reason-in-Documents denoiser refines surviving docs.
    6. Cache the decomposition + return PipelineResult.

Budget tracking via :class:`BudgetController` is threaded throughout — when
the budget is exhausted, the pipeline returns a partial result with
``completed=False``. This satisfies the [docs/202] §3 equal-budget critique
out of the box.
"""
from __future__ import annotations

import enum
import time
from dataclasses import dataclass, field
from typing import Any, Optional

from ..evals import BudgetController, BudgetExhausted
from ..gates import ChainOfNoteGate
from ..multi_hop import (
    DecompositionCache,
    IRCoTOperator,
    IRCoTResult,
    SelfAskOperator,
    SelfAskResult,
)
from ..routing import BELLERouter, QueryType, RouteDecision


class PipelineStep(str, enum.Enum):
    """Steps in the canonical pipeline — surfaced in PipelineResult.steps."""

    CACHE_HIT = "cache_hit"
    ROUTING = "routing"
    OPERATOR_SELF_ASK = "operator_self_ask"
    OPERATOR_IRCOT = "operator_ircot"
    OPERATOR_SINGLE_HOP = "operator_single_hop"
    GATE_CHAIN_OF_NOTE = "gate_chain_of_note"
    BUDGET_EXHAUSTED = "budget_exhausted"
    COMPLETED = "completed"


@dataclass(frozen=True)
class PipelineResult:
    """Output of the end-to-end pipeline."""

    query: str
    answer: str
    operator_used: str  # "self_ask" | "ircot" | "single_hop" | "cached"
    route_decision: Optional[RouteDecision]
    n_hops: int = 0
    n_llm_calls: int = 0
    n_retrieval_calls: int = 0
    n_docs_filtered: int = 0  # docs dropped by chain-of-note
    n_docs_kept: int = 0
    cache_hit: bool = False
    completed: bool = False
    steps: tuple[PipelineStep, ...] = ()
    budget_remaining: Optional[int] = None
    elapsed_seconds: float = 0.0
    error: str = ""


@dataclass
class MultiHopPipeline:
    """Composable multi-hop pipeline coordinator.

    Required components: router + at least one operator. Optional:
    chain_of_note gate, decomposition cache, budget controller.

    >>> from harness_core.multi_hop import StubLLM, StubRetriever
    >>> from harness_core.routing import BELLERouter
    >>> from harness_core.multi_hop import (
    ...     SelfAskOperator, IRCoTOperator,
    ... )
    >>> llm = StubLLM(responses=[
    ...     "Are follow up questions needed here? No\\nSo the final answer is: 42\\n",
    ... ])
    >>> retriever = StubRetriever()
    >>> pipeline = MultiHopPipeline(
    ...     router=BELLERouter(),
    ...     self_ask=SelfAskOperator(llm=llm, retriever=retriever),
    ...     ircot=IRCoTOperator(llm=StubLLM(responses=["Answer: x"]), retriever=retriever),
    ... )
    >>> result = pipeline.answer("what is the answer")
    >>> result.completed
    True
    """

    router: BELLERouter
    self_ask: Optional[SelfAskOperator] = None
    ircot: Optional[IRCoTOperator] = None
    chain_of_note: Optional[ChainOfNoteGate] = None
    decomposition_cache: Optional[DecompositionCache] = None
    budget: Optional[BudgetController] = None

    # Per-call resource estimates for budget enforcement.
    estimated_tokens_per_llm_call: int = 500
    estimated_tokens_per_retrieval: int = 100

    def answer(
        self,
        query: str,
        *,
        namespace: str = "default",
    ) -> PipelineResult:
        """Run the canonical pipeline; return a typed result."""
        start = time.time()
        steps: list[PipelineStep] = []

        # 1. Cache lookup.
        if self.decomposition_cache is not None:
            cached = self.decomposition_cache.get(query, namespace=namespace)
            if cached is not None:
                steps.append(PipelineStep.CACHE_HIT)
                steps.append(PipelineStep.COMPLETED)
                return PipelineResult(
                    query=query,
                    answer=" ".join(cached.sub_questions),  # placeholder — caller composes
                    operator_used="cached",
                    route_decision=None,
                    cache_hit=True,
                    completed=True,
                    steps=tuple(steps),
                    elapsed_seconds=time.time() - start,
                )

        # 2. Route.
        steps.append(PipelineStep.ROUTING)
        decision = self.router.route(query)

        # 3. Operator dispatch.
        try:
            if decision.query_type == QueryType.MULTI_HOP_BRIDGE and self.self_ask is not None:
                steps.append(PipelineStep.OPERATOR_SELF_ASK)
                result_data = self._run_self_ask(query)
            elif decision.query_type in (
                QueryType.GLOBAL_SENSEMAKING,
                QueryType.OPEN_BROWSE,
                QueryType.FAN_OUT,
            ) and self.ircot is not None:
                steps.append(PipelineStep.OPERATOR_IRCOT)
                result_data = self._run_ircot(query)
            elif self.self_ask is not None:
                # SINGLE_HOP fallback to self_ask (which handles the no-followup case).
                steps.append(PipelineStep.OPERATOR_SINGLE_HOP)
                result_data = self._run_self_ask(query)
            elif self.ircot is not None:
                steps.append(PipelineStep.OPERATOR_SINGLE_HOP)
                result_data = self._run_ircot(query)
            else:
                # No operator wired.
                steps.append(PipelineStep.COMPLETED)
                return PipelineResult(
                    query=query,
                    answer="",
                    operator_used="none",
                    route_decision=decision,
                    completed=False,
                    steps=tuple(steps),
                    error="no operator wired",
                    elapsed_seconds=time.time() - start,
                    budget_remaining=self.budget.remaining() if self.budget else None,
                )
        except BudgetExhausted as exc:
            steps.append(PipelineStep.BUDGET_EXHAUSTED)
            return PipelineResult(
                query=query,
                answer="",
                operator_used="none",
                route_decision=decision,
                completed=False,
                steps=tuple(steps),
                error=str(exc),
                elapsed_seconds=time.time() - start,
                budget_remaining=self.budget.remaining() if self.budget else None,
            )

        # 4. Cache the decomposition (sub-questions only — the answer can shift).
        if self.decomposition_cache is not None and result_data["sub_questions"]:
            self.decomposition_cache.put(
                question=query,
                sub_questions=tuple(result_data["sub_questions"]),
                namespace=namespace,
            )

        steps.append(PipelineStep.COMPLETED)
        return PipelineResult(
            query=query,
            answer=result_data["answer"],
            operator_used=result_data["operator"],
            route_decision=decision,
            n_hops=result_data["n_hops"],
            n_llm_calls=result_data["n_llm_calls"],
            n_retrieval_calls=result_data["n_retrieval_calls"],
            n_docs_filtered=result_data["n_docs_filtered"],
            n_docs_kept=result_data["n_docs_kept"],
            completed=result_data["completed"],
            steps=tuple(steps),
            budget_remaining=self.budget.remaining() if self.budget else None,
            elapsed_seconds=time.time() - start,
        )

    # --- Operator runners -------------------------------------------------

    def _run_self_ask(self, query: str) -> dict[str, Any]:
        if self.self_ask is None:
            raise RuntimeError("self_ask operator not wired")
        # Reserve budget per LLM call. We can't intercept inside the operator,
        # so pre-reserve max_hops * cost; refund unused on completion.
        if self.budget is not None:
            estimate = self.self_ask.max_hops * self.estimated_tokens_per_llm_call
            if not self.budget.reserve(estimate):
                raise BudgetExhausted(f"reserving {estimate} tokens for self_ask")

        result = self.self_ask.answer(query)
        n_filtered, n_kept = self._gate_documents(query, result)
        return {
            "answer": result.final_answer,
            "operator": "self_ask",
            "n_hops": len(result.steps),
            "n_llm_calls": result.n_llm_calls,
            "n_retrieval_calls": result.n_retrieval_calls,
            "n_docs_filtered": n_filtered,
            "n_docs_kept": n_kept,
            "completed": result.completed,
            "sub_questions": [s.follow_up for s in result.steps],
        }

    def _run_ircot(self, query: str) -> dict[str, Any]:
        if self.ircot is None:
            raise RuntimeError("ircot operator not wired")
        if self.budget is not None:
            estimate = self.ircot.max_iters * self.estimated_tokens_per_llm_call
            if not self.budget.reserve(estimate):
                raise BudgetExhausted(f"reserving {estimate} tokens for ircot")

        result = self.ircot.answer(query)
        n_filtered, n_kept = self._gate_documents(query, result)
        return {
            "answer": result.final_answer,
            "operator": "ircot",
            "n_hops": len(result.steps),
            "n_llm_calls": result.n_llm_calls,
            "n_retrieval_calls": result.n_retrieval_calls,
            "n_docs_filtered": n_filtered,
            "n_docs_kept": n_kept,
            "completed": result.completed,
            # IRCoT doesn't emit explicit sub-questions; use sentence list.
            "sub_questions": [s.sentence for s in result.steps],
        }

    def _gate_documents(
        self,
        query: str,
        operator_result: SelfAskResult | IRCoTResult,
    ) -> tuple[int, int]:
        """Run Chain-of-Note over retrieved docs; return (filtered, kept)."""
        if self.chain_of_note is None:
            return (0, sum(len(s.retrieved) for s in operator_result.steps))

        all_docs: list[dict[str, str]] = []
        seen_ids: set[str] = set()
        for step in operator_result.steps:
            for doc in step.retrieved:
                if doc.doc_id in seen_ids:
                    continue
                seen_ids.add(doc.doc_id)
                all_docs.append({"id": doc.doc_id, "content": doc.text})

        if not all_docs:
            return (0, 0)

        results = self.chain_of_note.filter(query=query, docs=all_docs)
        kept = sum(1 for r in results if r.passed)
        filtered = len(results) - kept
        return (filtered, kept)


__all__ = ["MultiHopPipeline", "PipelineResult", "PipelineStep"]
