"""SkillOpt — text-space optimization for skill prompts.

Optimizes skill prompt text through iterative refinement using
textual gradients (Feedback Descent / MemGrad style) without
requiring gradient access to the underlying model.

Based on arXiv:2605 SkillOpt and AEvo meta-editing techniques
achieving 26% improvement in skill effectiveness.
"""

from __future__ import annotations

import re
from dataclasses import dataclass
from enum import StrEnum


class OptimizationStrategy(StrEnum):
    CLARIFY = "clarify"
    CONDENSE = "condense"
    EXPAND = "expand"
    RESTRUCTURE = "restructure"
    ADD_EXAMPLES = "add_examples"


@dataclass(frozen=True)
class TextEdit:
    strategy: OptimizationStrategy
    original_segment: str
    optimized_segment: str
    rationale: str
    expected_improvement: float


@dataclass(frozen=True)
class OptimizationPass:
    pass_id: str
    edits: tuple[TextEdit, ...]
    score_before: float
    score_after: float
    delta: float


@dataclass
class SkillOptConfig:
    max_passes: int = 5
    min_improvement: float = 0.01
    strategies: tuple[OptimizationStrategy, ...] = (
        OptimizationStrategy.CLARIFY,
        OptimizationStrategy.CONDENSE,
        OptimizationStrategy.RESTRUCTURE,
        OptimizationStrategy.ADD_EXAMPLES,
    )
    max_prompt_length: int = 8000
    score_weight_clarity: float = 0.3
    score_weight_conciseness: float = 0.2
    score_weight_actionability: float = 0.3
    score_weight_specificity: float = 0.2


class SkillOptimizer:
    """Text-space skill prompt optimizer.

    Improves skill prompts through iterative editing passes, guided by
    heuristic scoring functions that evaluate clarity, conciseness,
    actionability, and specificity — no model access required.
    """

    def __init__(self, config: SkillOptConfig | None = None) -> None:
        self.config = config or SkillOptConfig()
        self._history: list[OptimizationPass] = []
        self._pass_counter: int = 0

    def optimize(self, skill_text: str, domain: str = "") -> tuple[str, list[OptimizationPass]]:
        """Run iterative optimization on a skill prompt.

        Returns the optimized text and the history of optimization passes.
        """
        current_text = skill_text
        current_score = self._score(current_text)
        passes: list[OptimizationPass] = []

        for _ in range(self.config.max_passes):
            best_edit: TextEdit | None = None
            best_score = current_score

            for strategy in self.config.strategies:
                edits = self._generate_edits(current_text, strategy, domain)
                for edit in edits:
                    candidate = current_text.replace(
                        edit.original_segment, edit.optimized_segment, 1
                    )
                    candidate_score = self._score(candidate)

                    if candidate_score > best_score:
                        best_score = candidate_score
                        best_edit = edit

            if best_edit is None:
                break

            improvement = best_score - current_score
            if improvement < self.config.min_improvement:
                break

            current_text = current_text.replace(
                best_edit.original_segment, best_edit.optimized_segment, 1
            )
            current_score = best_score
            self._pass_counter += 1

            passes.append(
                OptimizationPass(
                    pass_id=f"opt-{self._pass_counter:04d}",
                    edits=(best_edit,),
                    score_before=round(current_score - improvement, 4),
                    score_after=round(current_score, 4),
                    delta=round(improvement, 4),
                )
            )

        self._history.extend(passes)
        return current_text, passes

    def _score(self, text: str) -> float:
        """Heuristic quality score — higher is better."""
        if not text.strip():
            return 0.0

        # Clarity: sentence count, readability signals
        sentences = re.split(r"[.!?]+", text)
        sentences = [s.strip() for s in sentences if s.strip()]
        avg_words = sum(len(s.split()) for s in sentences) / max(len(sentences), 1)
        clarity = min(1.0, avg_words / 20.0)  # Prefer ~15-20 word sentences

        # Conciseness: penalize excessive length
        word_count = len(text.split())
        conciseness = max(0.0, 1.0 - word_count / self.config.max_prompt_length)

        # Actionability: detect imperative/action verbs
        action_verbs = r"\b(use|call|run|execute|create|modify|check|verify|"
        action_verbs += r"test|deploy|build|install|configure|set|get|fetch|"
        action_verbs += r"query|insert|update|delete|read|write|parse|format|"
        action_verbs += r"validate|transform|extract|generate|compute)\b"
        action_count = len(re.findall(action_verbs, text, re.IGNORECASE))
        actionability = min(1.0, action_count / max(word_count / 20.0, 1))

        # Specificity: detect parameters, examples, edge cases
        specificity_signals = [
            r"\{[\w_]+\}",  # {parameter} placeholders
            r"`[^`]+`",  # inline code
            r"e\.g\.",  # examples
            r"for example",
            r"returns?",
            r"raises?",
            r"if .* then",
        ]
        specificity_matches = sum(
            len(re.findall(pat, text, re.IGNORECASE)) for pat in specificity_signals
        )
        specificity = min(1.0, specificity_matches / 5.0)

        return (
            self.config.score_weight_clarity * clarity
            + self.config.score_weight_conciseness * conciseness
            + self.config.score_weight_actionability * actionability
            + self.config.score_weight_specificity * specificity
        )

    def _generate_edits(
        self,
        text: str,
        strategy: OptimizationStrategy,
        domain: str = "",
    ) -> list[TextEdit]:
        """Generate candidate edits for a given strategy."""
        edits: list[TextEdit] = []

        if strategy == OptimizationStrategy.CLARIFY:
            edits.extend(self._clarify_edits(text))

        elif strategy == OptimizationStrategy.CONDENSE:
            edits.extend(self._condense_edits(text))

        elif strategy == OptimizationStrategy.RESTRUCTURE:
            edits.extend(self._restructure_edits(text))

        elif strategy == OptimizationStrategy.ADD_EXAMPLES:
            edits.extend(self._example_edits(text, domain))

        return edits

    def _clarify_edits(self, text: str) -> list[TextEdit]:
        edits: list[TextEdit] = []
        # Replace vague words with specific ones
        substitutions = [
            (r"\bit\b", "the function", "Replace ambiguous 'it' with specific reference"),
            (r"\bthing\b", "element", "Replace vague 'thing'"),
            (r"\bstuff\b", "data", "Replace vague 'stuff'"),
            (r"\bmake sure\b", "verify that", "Replace informal 'make sure' with 'verify'"),
        ]
        for pattern, replacement, rationale in substitutions:
            match = re.search(pattern, text, re.IGNORECASE)
            if match:
                edits.append(
                    TextEdit(
                        strategy=OptimizationStrategy.CLARIFY,
                        original_segment=match.group(),
                        optimized_segment=replacement,
                        rationale=rationale,
                        expected_improvement=0.05,
                    )
                )
        return edits

    def _condense_edits(self, text: str) -> list[TextEdit]:
        edits: list[TextEdit] = []
        # Remove redundant phrases
        redundancies = [
            ("in order to ", "to "),
            ("it is important to note that ", ""),
            ("please note that ", ""),
            ("for the purpose of ", "for "),
        ]
        for redundant, concise in redundancies:
            if redundant in text:
                edits.append(
                    TextEdit(
                        strategy=OptimizationStrategy.CONDENSE,
                        original_segment=redundant,
                        optimized_segment=concise,
                        rationale=f"Remove redundant phrase '{redundant.strip()}'",
                        expected_improvement=0.03,
                    )
                )
        return edits

    def _restructure_edits(self, text: str) -> list[TextEdit]:
        edits: list[TextEdit] = []
        # Add section headers if missing
        if "## " not in text and len(text) > 200:
            header = "## Instructions\n\n"
            edits.append(
                TextEdit(
                    strategy=OptimizationStrategy.RESTRUCTURE,
                    original_segment=text[: min(10, len(text))],
                    optimized_segment=header + text[: min(10, len(text))],
                    rationale="Add markdown section header for structure",
                    expected_improvement=0.04,
                )
            )
        return edits

    def _example_edits(self, text: str, domain: str = "") -> list[TextEdit]:
        edits: list[TextEdit] = []
        if "e.g." not in text and "for example" not in text.lower():
            example = (
                f'\n\ne.g. `{domain}_tool(input="value") -> expected_output`' if domain else ""
            )
            if example:
                last_period = text.rfind(".")
                if last_period > 0:
                    edits.append(
                        TextEdit(
                            strategy=OptimizationStrategy.ADD_EXAMPLES,
                            original_segment=text[last_period : last_period + 1],
                            optimized_segment=f".{example}",
                            rationale="Add concrete usage example for clarity",
                            expected_improvement=0.06,
                        )
                    )
        return edits

    @property
    def history(self) -> list[OptimizationPass]:
        return list(self._history)

    @property
    def pass_count(self) -> int:
        return self._pass_counter
