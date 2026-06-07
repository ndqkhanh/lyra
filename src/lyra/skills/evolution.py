"""
Skill evolution engine — GEPA-style reflective prompt evolution with
population-based optimization and a five-dimension quality rubric.

Inspired by the Generative Evolutionary Prompt Architecture (GEPA)
paradigm: each skill is treated as a genome, variants are generated via
reflective prompts, and the population is evolved over generations using
tournament selection.
"""

from __future__ import annotations

import copy
import random
from dataclasses import dataclass, field
from typing import Any, Callable

from .skill import Skill

# ---------------------------------------------------------------------------
# Configuration
# ---------------------------------------------------------------------------


@dataclass
class EvolutionConfig:
    """Configuration for the skill evolution loop.

    Attributes:
        generations: Number of evolution generations to run.
        population_size: Number of variants per generation.
        mutation_rate: Probability (0-1) of applying a mutation to a variant.
        crossover_rate: Probability (0-1) of applying crossover between two parents.
        elite_ratio: Fraction of top-performing variants preserved unchanged (elitism).
        seed: Random seed for reproducibility.
    """

    generations: int = 5
    population_size: int = 8
    mutation_rate: float = 0.3
    crossover_rate: float = 0.5
    elite_ratio: float = 0.25
    seed: int | None = None

    def __post_init__(self) -> None:
        if self.seed is not None:
            random.seed(self.seed)
        if not 0 < self.population_size <= 64:
            raise ValueError("population_size must be in (0, 64]")
        if not 0.0 <= self.mutation_rate <= 1.0:
            raise ValueError("mutation_rate must be in [0.0, 1.0]")
        if not 0.0 <= self.crossover_rate <= 1.0:
            raise ValueError("crossover_rate must be in [0.0, 1.0]")
        if not 0.0 <= self.elite_ratio <= 1.0:
            raise ValueError("elite_ratio must be in [0.0, 1.0]")

    def to_dict(self) -> dict[str, Any]:
        return {
            "generations": self.generations,
            "population_size": self.population_size,
            "mutation_rate": self.mutation_rate,
            "crossover_rate": self.crossover_rate,
            "elite_ratio": self.elite_ratio,
            "seed": self.seed,
        }

    @classmethod
    def from_dict(cls, data: dict[str, Any]) -> EvolutionConfig:
        return cls(
            generations=data.get("generations", 5),
            population_size=data.get("population_size", 8),
            mutation_rate=data.get("mutation_rate", 0.3),
            crossover_rate=data.get("crossover_rate", 0.5),
            elite_ratio=data.get("elite_ratio", 0.25),
            seed=data.get("seed"),
        )


# ---------------------------------------------------------------------------
# Quality Rubric
# ---------------------------------------------------------------------------


class RubricDimension(str):
    """Named rubric dimension — used for type safety in dimension lookups."""


CORRECTNESS = RubricDimension("correctness")
COMPLETENESS = RubricDimension("completeness")
CLARITY = RubricDimension("clarity")
EFFICIENCY = RubricDimension("efficiency")
SAFETY = RubricDimension("safety")

RUBRIC_DIMENSIONS: tuple[RubricDimension, ...] = (
    CORRECTNESS,
    COMPLETENESS,
    CLARITY,
    EFFICIENCY,
    SAFETY,
)

DIMENSION_WEIGHTS: dict[RubricDimension, float] = {
    CORRECTNESS: 0.30,
    COMPLETENESS: 0.25,
    CLARITY: 0.20,
    EFFICIENCY: 0.15,
    SAFETY: 0.10,
}


@dataclass
class EvalScore:
    """Five-dimension quality score for a skill.

    Each dimension is scored 0.0 — 1.0.
    """

    correctness: float = 0.0
    completeness: float = 0.0
    clarity: float = 0.0
    efficiency: float = 0.0
    safety: float = 0.0

    def __post_init__(self) -> None:
        for dim in RUBRIC_DIMENSIONS:
            val = getattr(self, dim)
            if not 0.0 <= val <= 1.0:
                raise ValueError(f"{dim} score must be in [0.0, 1.0], got {val}")

    @property
    def weighted_score(self) -> float:
        """Return the weighted aggregate score across all five dimensions."""
        return sum(
            getattr(self, dim) * DIMENSION_WEIGHTS[dim]
            for dim in RUBRIC_DIMENSIONS
        )

    @property
    def average(self) -> float:
        """Return the unweighted average across all five dimensions."""
        n = len(RUBRIC_DIMENSIONS)
        return sum(getattr(self, dim) for dim in RUBRIC_DIMENSIONS) / n

    def to_dict(self) -> dict[str, float]:
        return {dim: getattr(self, dim) for dim in RUBRIC_DIMENSIONS}

    @classmethod
    def from_dict(cls, data: dict[str, float]) -> EvalScore:
        return cls(
            correctness=data.get("correctness", 0.0),
            completeness=data.get("completeness", 0.0),
            clarity=data.get("clarity", 0.0),
            efficiency=data.get("efficiency", 0.0),
            safety=data.get("safety", 0.0),
        )


@dataclass
class EvalResult:
    """Result of evaluating a skill against one or more test cases."""

    skill_name: str
    score: EvalScore
    test_case_results: list[dict[str, Any]] = field(default_factory=list)
    feedback: str = ""

    @property
    def passed(self) -> bool:
        """Return True if the weighted score is above the passing threshold (0.5)."""
        return self.score.weighted_score >= 0.5

    def to_dict(self) -> dict[str, Any]:
        return {
            "skill_name": self.skill_name,
            "score": self.score.to_dict(),
            "weighted_score": self.score.weighted_score,
            "test_case_results": self.test_case_results,
            "feedback": self.feedback,
            "passed": self.passed,
        }


# ---------------------------------------------------------------------------
# Evolution Engine
# ---------------------------------------------------------------------------


ScorerFn = Callable[[Skill], EvalScore]
"""Signature for a custom scoring function that evaluates a skill variant."""


class SkillEvolutionEngine:
    """Population-based skill evolution using GEPA-style reflective generation.

    The engine treats each Skill as a genome. A generation creates variants
    via prompt-level mutations and crossovers, evaluates them against a
    quality rubric, and selects the best performers for the next round.
    """

    def __init__(
        self,
        config: EvolutionConfig | None = None,
        scorer: ScorerFn | None = None,
    ):
        self.config = config or EvolutionConfig()
        self._scorer = scorer or self._default_scorer
        self._history: list[EvolutionRound] = []

    # ------------------------------------------------------------------
    # Public API
    # ------------------------------------------------------------------

    def generate_variants(self, skill: Skill, n: int = 4) -> list[Skill]:
        """Generate *n* variants of *skill* using GEPA-style reflective prompts.

        Each variant applies a random combination of:
        - Rephrase the description
        - Add / remove trigger patterns
        - Expand or condense content
        - Shift tone (instructional vs. conversational)

        Args:
            skill: The base skill to generate variants from.
            n: Number of variants to generate.

        Returns:
            A list of new Skill objects (variants of *skill*).
        """
        variants: list[Skill] = []
        mutation_ops = [
            self._mutate_description,
            self._mutate_trigger_patterns,
            self._mutate_content_expand,
            self._mutate_content_condense,
            self._mutate_tone_instructional,
            self._mutate_tone_conversational,
        ]

        for _ in range(n):
            variant = copy.deepcopy(skill)
            # Apply 1-3 random mutations
            k = random.randint(1, min(3, len(mutation_ops)))
            ops = random.sample(mutation_ops, k)
            for op in ops:
                op(variant)
            variant.name = f"{skill.name}-variant-{random.randint(1000, 9999)}"
            variants.append(variant)

        return variants

    def evaluate(
        self,
        skill: Skill,
        test_cases: list[dict[str, Any]] | None = None,
    ) -> EvalResult:
        """Run the quality rubric against *skill*.

        The scorer inspects the skill's description, content, trigger
        patterns, tags, and dependencies, and returns a 5-dimension
        EvalScore.

        Args:
            skill: The skill to evaluate.
            test_cases: Optional list of test-case dicts for fine-grained
                result tracking. Each dict may contain ``"name"``,
                ``"input"``, and ``"expected"`` keys.

        Returns:
            An EvalResult with the rubric score and per-case breakdown.
        """
        score = self._scorer(skill)
        case_results: list[dict[str, Any]] = []
        for tc in (test_cases or []):
            case_results.append({
                "name": tc.get("name", "unnamed"),
                "input": tc.get("input", ""),
                "expected": tc.get("expected", ""),
                "actual": self._evaluate_case(skill, tc),
            })
        feedback = self._build_feedback(skill, score)
        return EvalResult(
            skill_name=skill.name,
            score=score,
            test_case_results=case_results,
            feedback=feedback,
        )

    def evolve(
        self,
        skill: Skill,
        generations: int | None = None,
        population_size: int | None = None,
    ) -> Skill:
        """Run a full population-based evolution loop.

        Each generation:
        1. Generate variants from the current population.
        2. Score every variant with the quality rubric.
        3. Keep the elite unchanged.
        4. Breed the remainder via crossover + mutation.
        5. Record the best performer.

        Args:
            skill: The seed skill.
            generations: Override config.generations for this run.
            population_size: Override config.population_size for this run.

        Returns:
            The single highest-scoring Skill across all generations.
        """
        gen = generations if generations is not None else self.config.generations
        pop_size = population_size if population_size is not None else self.config.population_size

        # Seed population
        population: list[tuple[Skill, EvalScore]] = [
            (skill, self._scorer(skill)),
        ]
        population.extend(
            (v, self._scorer(v))
            for v in self.generate_variants(skill, pop_size - 1)
        )

        best_skill: Skill = skill
        best_score: float = 0.0

        for generation in range(gen):
            # Sort descending by weighted score
            population.sort(key=lambda x: x[1].weighted_score, reverse=True)

            current_best_skill, current_best_score = population[0]
            if current_best_score.weighted_score > best_score:
                best_skill = current_best_skill
                best_score = current_best_score.weighted_score

            # Record round
            round_data = EvolutionRound(
                generation=generation,
                best_skill_name=current_best_skill.name,
                best_score=current_best_score.weighted_score,
                population_scores=[s.weighted_score for _, s in population],
            )
            self._history.append(round_data)

            # Elitism: carry over top performers unchanged
            elite_count = max(1, int(pop_size * self.config.elite_ratio))
            next_population: list[tuple[Skill, EvalScore]] = population[:elite_count]

            # Breed remaining slots
            remaining = pop_size - elite_count
            for _ in range(remaining):
                parent_a, parent_b = self._tournament_select(population, k=2)
                child = self._crossover(parent_a, parent_b)
                if random.random() < self.config.mutation_rate:
                    child = self._mutate(child)
                child_score = self._scorer(child)
                next_population.append((child, child_score))

            population = next_population

        return best_skill

    def keep_best(
        self,
        population: list[tuple[Skill, EvalScore]],
        top_k: int = 1,
    ) -> list[Skill]:
        """Tournament selection: return the *top_k* highest-scoring skills.

        Args:
            population: List of (skill, eval_score) pairs.
            top_k: Number of top performers to return.

        Returns:
            The *top_k* highest-scoring skills.
        """
        sorted_pop = sorted(population, key=lambda x: x[1].weighted_score, reverse=True)
        return [skill for skill, _ in sorted_pop[:top_k]]

    # ------------------------------------------------------------------
    # Properties
    # ------------------------------------------------------------------

    @property
    def history(self) -> list[EvolutionRound]:
        """Return the record of all evolution rounds."""
        return list(self._history)

    # ------------------------------------------------------------------
    # Internal: mutation operators
    # ------------------------------------------------------------------

    @staticmethod
    def _mutate_description(skill: Skill) -> None:
        """Rephrase the description with a reflective variation."""
        original = skill.description
        prefixes = [
            "Reflective analysis of ",
            "Expert guidance on ",
            "Comprehensive overview of ",
            "Pattern-driven approach to ",
            "Systematic methodology for ",
        ]
        if original:
            prefix = random.choice(prefixes)
            skill.description = prefix + original[0].lower() + original[1:]

    @staticmethod
    def _mutate_trigger_patterns(skill: Skill) -> None:
        """Add or remove a trigger pattern."""
        additions_pool = [
            "how to", "guide", "tutorial", "reference",
            "pattern", "example", "best practice", "cheatsheet",
        ]
        if skill.trigger_patterns and random.random() < 0.4:
            # Remove one
            removed = random.choice(skill.trigger_patterns)
            skill.trigger_patterns.remove(removed)
        else:
            # Add a new one
            new_pattern = random.choice(additions_pool)
            if new_pattern not in skill.trigger_patterns:
                skill.trigger_patterns.append(new_pattern)

    @staticmethod
    def _mutate_content_expand(skill: Skill) -> None:
        """Append an elaboration paragraph to the content."""
        elaborations = [
            "\n\n## Implementation Notes\n\n"
            "When applying this pattern, consider the specific context "
            "of your domain. Adapt the general principles to match your "
            "team's workflow and technology stack.",
            "\n\n## Example\n\n"
            "```\n# Example usage\nresult = apply_pattern(input)\n```\n\n"
            "This demonstrates the recommended approach in practice.",
            "\n\n## Common Pitfalls\n\n"
            "- Over-engineering: apply only what is needed.\n"
            "- Premature abstraction: wait for the third occurrence.\n"
            "- Ignoring team conventions: consistency matters more than perfection.",
        ]
        skill.content += random.choice(elaborations)

    @staticmethod
    def _mutate_content_condense(skill: Skill) -> None:
        """Truncate content to a concise summary (first 200 chars)."""
        lines = skill.content.strip().split("\n")
        # Keep only the first paragraph or two
        condensed = "\n".join(lines[:3]).strip()
        if len(condensed) > 200:
            condensed = condensed[:200]
        if len(condensed) < len(skill.content):
            skill.content = condensed + "\n\n*(Condensed variant)*"

    @staticmethod
    def _mutate_tone_instructional(skill: Skill) -> None:
        """Shift tone toward imperative, instructional language."""
        skill.content = (
            "## Instructions\n\n"
            "Follow these steps precisely:\n\n"
            f"{skill.content.strip()[:300]}"
        )

    @staticmethod
    def _mutate_tone_conversational(skill: Skill) -> None:
        """Shift tone toward conversational, explanatory language."""
        skill.content = (
            "Let me walk you through this pattern.\n\n"
            f"{skill.content.strip()[:300]}"
        )

    # ------------------------------------------------------------------
    # Internal: evaluator helpers
    # ------------------------------------------------------------------

    @staticmethod
    def _default_scorer(skill: Skill) -> EvalScore:
        """Heuristic scorer that analyses static properties of the skill.

        This is a fallback used when no external scorer is provided. Real
        usage should supply a custom scorer (e.g., an LLM call or test
        execution harness).
        """
        content_len = len(skill.content)
        desc_len = len(skill.description)
        has_tags = len(skill.tags) > 0
        has_triggers = len(skill.trigger_patterns) > 0

        # Correctness: heuristic based on structural completeness
        correctness = min(1.0, max(0.1,
            (0.3 if desc_len > 10 else 0.1) +
            (0.3 if content_len > 50 else 0.1) +
            (0.2 if has_tags else 0.0) +
            (0.2 if has_triggers else 0.0)
        ))

        # Completeness: coverage of description, content, metadata
        completeness = min(1.0, max(0.1,
            (0.25 if desc_len > 20 else 0.05) +
            (0.25 if content_len > 200 else 0.05) +
            (0.2 if has_tags else 0.0) +
            (0.15 if has_triggers else 0.0) +
            (0.15 if skill.language else 0.0)
        ))

        # Clarity: based on structure (newlines, sections)
        clarity = min(1.0, max(0.1,
            (0.3 if content_len > 100 else 0.1) +
            (0.2 if "\n" in skill.content else 0.0) +
            (0.2 if skill.content.startswith("#") or skill.content.startswith("##") else 0.0) +
            (0.15 if "---" in skill.content or "- " in skill.content else 0.0) +
            (0.15 if desc_len > 15 else 0.05)
        ))

        # Efficiency: conciseness of content relative to description
        ratio = content_len / max(desc_len, 1)
        if 5 <= ratio <= 50:
            efficiency = 0.8
        elif ratio < 5:
            efficiency = 0.4  # too terse
        else:
            efficiency = 0.5  # likely too verbose
        efficiency = min(1.0, efficiency)

        # Safety: checks for dangerous patterns in content
        safety = 1.0
        danger_signals = [
            "exec(", "eval(", "__import__", "subprocess",
            "rm -rf", "DROP TABLE", "DELETE FROM",
        ]
        for signal in danger_signals:
            if signal in skill.content:
                safety -= 0.2
        safety = max(0.1, safety)

        return EvalScore(
            correctness=round(correctness, 2),
            completeness=round(completeness, 2),
            clarity=round(clarity, 2),
            efficiency=round(efficiency, 2),
            safety=round(safety, 2),
        )

    @staticmethod
    def _evaluate_case(skill: Skill, test_case: dict[str, Any]) -> str:
        """Run a single test case against the skill.

        Default implementation checks whether the skill content or
        description contains the expected string.
        """
        expected = test_case.get("expected", "")
        if not expected:
            return "no-expected"
        combined = f"{skill.name} {skill.description} {skill.content}".lower()
        return "pass" if expected.lower() in combined else "fail"

    @staticmethod
    def _build_feedback(skill: Skill, score: EvalScore) -> str:
        """Generate human-readable feedback from the rubric scores."""
        parts = []
        if score.correctness < 0.5:
            parts.append(f"Correctness ({score.correctness}): skill structure is weak")
        if score.completeness < 0.5:
            parts.append(f"Completeness ({score.completeness}): missing metadata or thin content")
        if score.clarity < 0.5:
            parts.append(f"Clarity ({score.clarity}): content lacks structure")
        if score.efficiency < 0.5:
            parts.append(f"Efficiency ({score.efficiency}): content-to-description ratio is off")
        if score.safety < 0.8:
            parts.append(f"Safety ({score.safety}): potentially dangerous patterns detected")
        if not parts:
            return "All dimensions meet quality thresholds."
        return "; ".join(parts)

    # ------------------------------------------------------------------
    # Internal: genetic operators
    # ------------------------------------------------------------------

    @staticmethod
    def _crossover(parent_a: Skill, parent_b: Skill) -> Skill:
        """Single-point crossover: swap content between two parents."""
        child = copy.deepcopy(parent_a)
        split = len(child.content) // 2
        child.content = child.content[:split] + parent_b.content[split:]
        child.name = f"{parent_a.name}-crossover-{random.randint(1000, 9999)}"
        return child

    @staticmethod
    def _mutate(skill: Skill) -> Skill:
        """Apply a random mutation to a skill."""
        mutation_ops = [
            SkillEvolutionEngine._mutate_description,
            SkillEvolutionEngine._mutate_trigger_patterns,
            SkillEvolutionEngine._mutate_content_expand,
            SkillEvolutionEngine._mutate_content_condense,
        ]
        op = random.choice(mutation_ops)
        op(skill)
        return skill

    @staticmethod
    def _tournament_select(
        population: list[tuple[Skill, EvalScore]],
        k: int = 2,
    ) -> tuple[Skill, Skill]:
        """Select two parents via k-way tournament."""
        def _pick_one() -> Skill:
            candidates = random.sample(population, min(k, len(population)))
            candidates.sort(key=lambda x: x[1].weighted_score, reverse=True)
            return candidates[0][0]

        return _pick_one(), _pick_one()


@dataclass
class EvolutionRound:
    """Record of a single evolution generation."""

    generation: int
    best_skill_name: str
    best_score: float
    population_scores: list[float] = field(default_factory=list)
    metadata: dict[str, Any] = field(default_factory=dict)

    def to_dict(self) -> dict[str, Any]:
        return {
            "generation": self.generation,
            "best_skill_name": self.best_skill_name,
            "best_score": self.best_score,
            "population_scores": self.population_scores,
            "metadata": self.metadata,
        }
