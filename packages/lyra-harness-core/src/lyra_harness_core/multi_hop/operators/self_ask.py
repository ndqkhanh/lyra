"""Self-Ask operator (Press et al. 2022, arXiv:2210.03350).

The model emits an explicit sequence:

    Are follow up questions needed here? Yes.
    Follow up: <sub-question>
    Intermediate answer: <fact>
    Follow up: <next sub-question>
    Intermediate answer: <fact>
    ...
    So the final answer is: <answer>

Each ``Follow up:`` is a retrieval query; each ``Intermediate answer:`` is
either parsed from the LLM output OR injected from a retriever call. The
operator runs the loop until the LLM emits ``So the final answer is:`` or
``max_hops`` is reached.

Closes the [docs/201](../../../../../../../research/harness-engineering/docs/201-compositionality-gap-canon.md)
compositionality gap by materialising the bridge entity as a token rather than
relying on latent multi-hop reasoning.
"""
from __future__ import annotations

import re
from dataclasses import dataclass, field
from typing import Optional

from .protocols import LLMTextGenerator, Retriever, RetrievedDoc

_FOLLOW_UP_RE = re.compile(r"Follow\s*up\s*:\s*(.+?)(?:\n|$)", re.IGNORECASE)
_FINAL_RE = re.compile(r"So\s+the\s+final\s+answer\s+is\s*:\s*(.+?)(?:\n|$)", re.IGNORECASE)
_INTER_RE = re.compile(r"Intermediate\s+answer\s*:\s*(.+?)(?:\n|$)", re.IGNORECASE)
_NEEDED_RE = re.compile(r"Are\s+follow\s*up\s+questions\s+needed\s+here\?\s*(\w+)", re.IGNORECASE)

_DEFAULT_PROMPT_HEADER = (
    "You are a careful researcher. To answer multi-hop questions, decompose "
    "into follow-up sub-questions. Use this exact format:\n"
    "Are follow up questions needed here? Yes\n"
    "Follow up: <next sub-question>\n"
    "Intermediate answer: <fact retrieved>\n"
    "Follow up: <next sub-question>\n"
    "Intermediate answer: <fact retrieved>\n"
    "So the final answer is: <answer>\n"
    "If no follow-ups are needed, write 'Are follow up questions needed here? No' "
    "then 'So the final answer is: <answer>'.\n\n"
)


@dataclass(frozen=True)
class SelfAskStep:
    """One follow-up cycle: question → retrieved docs → intermediate answer."""

    follow_up: str
    retrieved: tuple[RetrievedDoc, ...]
    intermediate_answer: str


@dataclass(frozen=True)
class SelfAskResult:
    """The full Self-Ask trace + final answer."""

    question: str
    steps: tuple[SelfAskStep, ...]
    final_answer: str
    n_llm_calls: int
    n_retrieval_calls: int
    completed: bool  # True if the LLM emitted "So the final answer is:" within max_hops


@dataclass
class ParsedResponse:
    """One LLM response parsed into its Self-Ask components."""

    needed_follow_up: Optional[bool]  # None if not present
    follow_up: Optional[str]
    intermediate_answer: Optional[str]
    final_answer: Optional[str]
    raw: str


def parse_self_ask_response(text: str) -> ParsedResponse:
    """Pull the Self-Ask fields out of an LLM response.

    Tolerant: missing fields are ``None``; extra text is ignored.
    """
    needed_match = _NEEDED_RE.search(text)
    needed: Optional[bool]
    if needed_match is None:
        needed = None
    else:
        word = needed_match.group(1).strip().lower()
        if word.startswith("y"):
            needed = True
        elif word.startswith("n"):
            needed = False
        else:
            needed = None

    follow_up_match = _FOLLOW_UP_RE.search(text)
    inter_match = _INTER_RE.search(text)
    final_match = _FINAL_RE.search(text)

    return ParsedResponse(
        needed_follow_up=needed,
        follow_up=follow_up_match.group(1).strip() if follow_up_match else None,
        intermediate_answer=inter_match.group(1).strip() if inter_match else None,
        final_answer=final_match.group(1).strip() if final_match else None,
        raw=text,
    )


@dataclass
class SelfAskOperator:
    """Self-Ask multi-hop QA loop.

    Default behaviour: each LLM turn proposes one follow-up; the operator
    retrieves docs for it, summarises into an intermediate answer (taken from
    the LLM's own output OR composed from retrieved-doc text), feeds back into
    the next turn, until the LLM emits a final answer or ``max_hops`` is hit.
    """

    llm: LLMTextGenerator
    retriever: Retriever
    max_hops: int = 4
    top_k: int = 3
    prompt_header: str = _DEFAULT_PROMPT_HEADER

    def answer(self, question: str) -> SelfAskResult:
        steps: list[SelfAskStep] = []
        context = ""  # transcript built turn-by-turn
        final_answer = ""
        completed = False
        n_llm = 0
        n_retr = 0

        for hop in range(self.max_hops + 1):  # +1 to allow one no-followup turn
            prompt = self._build_prompt(question, context)
            llm_text = self.llm.generate(prompt, stop=["So the final answer is:"])
            n_llm += 1
            parsed = parse_self_ask_response(llm_text)

            if parsed.final_answer:
                final_answer = parsed.final_answer
                completed = True
                break

            if parsed.needed_follow_up is False and parsed.follow_up is None:
                # LLM said no follow-up needed but didn't produce a final
                # answer — ask once more for the answer.
                final_answer = parsed.intermediate_answer or ""
                completed = bool(final_answer)
                break

            if not parsed.follow_up:
                # No follow-up extracted; treat as malformed and stop.
                break

            if hop >= self.max_hops:
                # Budget hit before final answer.
                break

            # Retrieve evidence for the follow-up; build intermediate answer.
            retrieved = self.retriever.retrieve(parsed.follow_up, top_k=self.top_k)
            n_retr += 1
            intermediate = parsed.intermediate_answer
            if not intermediate and retrieved:
                # Compose a deterministic intermediate from the top doc.
                intermediate = retrieved[0].text

            step = SelfAskStep(
                follow_up=parsed.follow_up,
                retrieved=tuple(retrieved),
                intermediate_answer=intermediate or "",
            )
            steps.append(step)
            context = self._extend_context(context, step)

        return SelfAskResult(
            question=question,
            steps=tuple(steps),
            final_answer=final_answer,
            n_llm_calls=n_llm,
            n_retrieval_calls=n_retr,
            completed=completed,
        )

    def _build_prompt(self, question: str, transcript: str) -> str:
        return f"{self.prompt_header}Question: {question}\n{transcript}"

    @staticmethod
    def _extend_context(context: str, step: SelfAskStep) -> str:
        evidence = "\n".join(d.text for d in step.retrieved[:1])  # one for prompt budget
        addition = (
            f"Follow up: {step.follow_up}\n"
            f"{('Evidence: ' + evidence + chr(10)) if evidence else ''}"
            f"Intermediate answer: {step.intermediate_answer}\n"
        )
        return context + addition


__all__ = [
    "ParsedResponse",
    "SelfAskOperator",
    "SelfAskResult",
    "SelfAskStep",
    "parse_self_ask_response",
]
