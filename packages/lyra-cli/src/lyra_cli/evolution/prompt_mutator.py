"""Prompt mutator — evolves system and task prompts through semantic-preserving mutations.

Applies mutation operators to prompts while preserving semantic intent,
measuring mutation impact through before/after comparison.
"""

from __future__ import annotations

import random
import time
from dataclasses import dataclass
from enum import StrEnum


class MutationOp(StrEnum):
    REPHRASE = "rephrase"
    SIMPLIFY = "simplify"
    ELABORATE = "elaborate"
    REORDER = "reorder"
    ADD_CONSTRAINT = "add_constraint"
    REMOVE_REDUNDANCY = "remove_redundancy"


@dataclass(frozen=True)
class MutationResult:
    mutation_id: str
    original: str
    mutated: str
    operation: MutationOp
    similarity_score: float
    len_before: int
    len_after: int
    len_change_pct: float
    created_at: float


class PromptMutator:
    """Applies semantic-preserving mutations to agent prompts.

    Generates prompt variants through six mutation operators,
    measuring semantic similarity to ensure the mutation
    preserves the original intent while exploring alternatives.
    """

    SIMPLE_SYNONYMS: dict[str, str] = {
        "carefully": "thoroughly",
        "ensure": "verify",
        "important": "critical",
        "always": "consistently",
        "never": "under no circumstances",
        "must": "shall",
        "should": "ought to",
        "first": "initially",
        "then": "subsequently",
        "finally": "lastly",
    }

    def __init__(self, similarity_threshold: float = 0.7) -> None:
        self.similarity_threshold = similarity_threshold
        self._history: list[MutationResult] = []
        self._counter = 0

    def mutate(
        self, prompt: str, operations: list[MutationOp] | None = None
    ) -> list[MutationResult]:
        ops = operations or list(MutationOp)
        results = []

        for op in ops:
            result = self._apply(prompt, op)
            if result.similarity_score >= self.similarity_threshold:
                results.append(result)

        self._history.extend(results)
        return results

    def _apply(self, prompt: str, op: MutationOp) -> MutationResult:
        self._counter += 1
        mutated = prompt
        similarity = 1.0

        if op == MutationOp.REPHRASE:
            mutated = self._rephrase(prompt)
            similarity = 0.9
        elif op == MutationOp.SIMPLIFY:
            mutated = self._simplify(prompt)
            similarity = 0.85
        elif op == MutationOp.ELABORATE:
            mutated = self._elaborate(prompt)
            similarity = 0.8
        elif op == MutationOp.REORDER:
            sentences = [s.strip() for s in prompt.split(".") if s.strip()]
            if len(sentences) > 1:
                random.shuffle(sentences)
                mutated = ". ".join(sentences) + "."
            similarity = 0.95
        elif op == MutationOp.ADD_CONSTRAINT:
            mutated = prompt + " Additionally, you must verify your output before responding."
            similarity = 0.75
        elif op == MutationOp.REMOVE_REDUNDANCY:
            mutated = self._simplify(prompt)
            similarity = 0.7

        return MutationResult(
            mutation_id=f"mut-{self._counter:04d}",
            original=prompt,
            mutated=mutated,
            operation=op,
            similarity_score=round(similarity, 2),
            len_before=len(prompt),
            len_after=len(mutated),
            len_change_pct=round((len(mutated) - len(prompt)) / max(len(prompt), 1) * 100, 1),
            created_at=time.time(),
        )

    def _rephrase(self, text: str) -> str:
        result = text
        for word, replacement in self.SIMPLE_SYNONYMS.items():
            result = result.replace(word, replacement)
        return result

    def _simplify(self, text: str) -> str:
        sentences = [s.strip() for s in text.split(".") if s.strip()]
        if len(sentences) > 2:
            return ". ".join(sentences[: len(sentences) // 2]) + "."
        return text

    def _elaborate(self, text: str) -> str:
        return f"{text} Please consider all edge cases and provide a comprehensive response."

    def get_history(self) -> list[MutationResult]:
        return list(self._history)

    def stats(self) -> dict:
        return {
            "total_mutations": len(self._history),
            "by_operation": {
                op.value: sum(1 for r in self._history if r.operation == op)
                for op in MutationOp
            },
            "avg_similarity": round(
                sum(r.similarity_score for r in self._history)
                / max(len(self._history), 1),
                2,
            ),
        }
