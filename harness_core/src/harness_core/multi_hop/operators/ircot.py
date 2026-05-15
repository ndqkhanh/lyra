"""IRCoT operator (Trivedi et al. 2023, arXiv:2212.10509).

Interleaves chain-of-thought generation with retrieval. Each new CoT sentence
is used as a retrieval query; the retrieved passages condition the next
sentence. Loop terminates when the LLM emits an "Answer:" line or ``max_iters``
is reached.

Headline numbers: up to **+21 retrieval / +15 QA points** over single-shot
retrieve-then-read on HotpotQA / 2WikiMultiHopQA / MuSiQue / IIRC.
"""
from __future__ import annotations

import re
from dataclasses import dataclass

from .protocols import LLMTextGenerator, Retriever, RetrievedDoc

_ANSWER_RE = re.compile(r"Answer\s*:\s*(.+?)(?:\n|$)", re.IGNORECASE)
_DEFAULT_PROMPT_HEADER = (
    "You are a careful reasoner. Build a chain of thought sentence by sentence; "
    "each sentence may use retrieved evidence. When you reach the answer, write "
    "it on a line starting with 'Answer:'.\n\n"
)


@dataclass(frozen=True)
class IRCoTStep:
    """One iteration: emitted sentence + retrieved docs."""

    sentence: str
    retrieved: tuple[RetrievedDoc, ...]


@dataclass(frozen=True)
class IRCoTResult:
    """The full IRCoT trace."""

    question: str
    steps: tuple[IRCoTStep, ...]
    final_answer: str
    n_llm_calls: int
    n_retrieval_calls: int
    completed: bool


@dataclass
class IRCoTOperator:
    """IRCoT loop: emit-sentence → retrieve → repeat → answer.

    Each LLM call returns one new CoT sentence (or, if it's the last, an
    ``Answer:`` line). The sentence is used as the next retrieval query.
    """

    llm: LLMTextGenerator
    retriever: Retriever
    max_iters: int = 6
    top_k: int = 3
    prompt_header: str = _DEFAULT_PROMPT_HEADER

    def answer(self, question: str) -> IRCoTResult:
        steps: list[IRCoTStep] = []
        evidence: list[RetrievedDoc] = []
        final_answer = ""
        completed = False
        n_llm = 0
        n_retr = 0

        for _ in range(self.max_iters):
            prompt = self._build_prompt(question, steps, evidence)
            llm_text = self.llm.generate(prompt, stop=["\n\n"])
            n_llm += 1
            sentence = llm_text.strip()
            if not sentence:
                break

            answer_match = _ANSWER_RE.search(sentence)
            if answer_match:
                final_answer = answer_match.group(1).strip()
                completed = True
                break

            retrieved = self.retriever.retrieve(sentence, top_k=self.top_k)
            n_retr += 1
            steps.append(IRCoTStep(sentence=sentence, retrieved=tuple(retrieved)))
            # Accumulate dedup'd evidence for the next prompt.
            seen_ids = {d.doc_id for d in evidence}
            for d in retrieved:
                if d.doc_id not in seen_ids:
                    evidence.append(d)
                    seen_ids.add(d.doc_id)

        return IRCoTResult(
            question=question,
            steps=tuple(steps),
            final_answer=final_answer,
            n_llm_calls=n_llm,
            n_retrieval_calls=n_retr,
            completed=completed,
        )

    def _build_prompt(
        self,
        question: str,
        steps: list[IRCoTStep],
        evidence: list[RetrievedDoc],
    ) -> str:
        evidence_block = ""
        if evidence:
            evidence_block = "Evidence so far:\n" + "\n".join(f"- {d.text}" for d in evidence) + "\n\n"
        cot_block = ""
        if steps:
            cot_block = "Chain of thought:\n" + "\n".join(s.sentence for s in steps) + "\n"
        return f"{self.prompt_header}Question: {question}\n\n{evidence_block}{cot_block}"


__all__ = ["IRCoTOperator", "IRCoTResult", "IRCoTStep"]
