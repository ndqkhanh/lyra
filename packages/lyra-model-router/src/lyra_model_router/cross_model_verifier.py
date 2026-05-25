"""Cross-model family verification for review workflows.

Ensures that the reviewer model is from a different family than the generator
model, providing independent verification. Supports multi-reviewer consensus
and verification strength scoring based on family diversity.
"""

from __future__ import annotations

from dataclasses import dataclass, field
from enum import Enum
from typing import Sequence


class ModelFamily(Enum):
    """Model families for cross-model verification."""
    ANTHROPIC = "anthropic"
    DEEPSEEK = "deepseek"
    OPENAI = "openai"
    GOOGLE = "google"
    META = "meta"
    MISTRAL = "mistral"
    COHERE = "cohere"
    OTHER = "other"


# Model family detection patterns
_MODEL_FAMILY_PATTERNS: dict[ModelFamily, tuple[str, ...]] = {
    ModelFamily.ANTHROPIC: ("claude",),
    ModelFamily.DEEPSEEK: ("deepseek",),
    ModelFamily.OPENAI: ("gpt", "o1", "o3"),
    ModelFamily.GOOGLE: ("gemini", "palm"),
    ModelFamily.META: ("llama",),
    ModelFamily.MISTRAL: ("mistral", "mixtral"),
    ModelFamily.COHERE: ("command", "cohere"),
    ModelFamily.OTHER: (),
}


@dataclass(frozen=True)
class ValidationResult:
    """Result of cross-model verification."""
    passed: bool
    generator_family: ModelFamily
    reviewer_family: ModelFamily
    diversity_score: float  # 0.0-1.0
    message: str
    recommendations: tuple[str, ...] = field(default_factory=tuple)


@dataclass(frozen=True)
class ConsensusResult:
    """Result of multi-reviewer consensus verification."""
    passed: bool
    generator_family: ModelFamily
    reviewer_families: tuple[ModelFamily, ...]
    consensus_score: float  # 0.0-1.0
    individual_results: tuple[ValidationResult, ...] = field(default_factory=tuple)
    message: str = ""


class CrossModelVerifier:
    """Verifies that reviewers are from different model families than generators.

    Detects model families from model IDs, validates cross-family review,
    scores verification strength based on family diversity, and supports
    multi-reviewer consensus workflows.
    """

    def __init__(self) -> None:
        self._family_patterns = _MODEL_FAMILY_PATTERNS.copy()

    def detect_family(self, model_id: str) -> ModelFamily:
        """Detect the model family from a model ID string."""
        lower_id = model_id.lower()
        for family, patterns in self._family_patterns.items():
            for pattern in patterns:
                if lower_id.startswith(pattern):
                    return family
        return ModelFamily.OTHER

    def register_family_pattern(self, family: ModelFamily, prefix: str) -> None:
        """Register an additional model ID prefix for a family."""
        current = list(self._family_patterns.get(family, ()))
        if prefix not in current:
            current.append(prefix)
        self._family_patterns[family] = tuple(current)

    def verify(self, generator_model: str, reviewer_model: str) -> ValidationResult:
        """Verify that the reviewer is from a different family than the generator.

        Returns a ValidationResult with pass/fail, diversity score, and
        recommendations.
        """
        gen_family = self.detect_family(generator_model)
        rev_family = self.detect_family(reviewer_model)

        if gen_family == rev_family:
            return ValidationResult(
                passed=False,
                generator_family=gen_family,
                reviewer_family=rev_family,
                diversity_score=0.0,
                message=(
                    f"Reviewer '{reviewer_model}' ({rev_family.value}) is same family "
                    f"as generator '{generator_model}' ({gen_family.value})"
                ),
                recommendations=(
                    f"Use a non-{gen_family.value} model for review",
                    f"Recommended alternatives: {self._suggest_alternatives(gen_family)}",
                ),
            )

        diversity_score = self._compute_diversity_score(gen_family, rev_family)
        return ValidationResult(
            passed=True,
            generator_family=gen_family,
            reviewer_family=rev_family,
            diversity_score=diversity_score,
            message=(
                f"Reviewer '{reviewer_model}' ({rev_family.value}) is different family "
                f"from generator '{generator_model}' ({gen_family.value}) "
                f"[diversity={diversity_score:.2f}]"
            ),
            recommendations=(),
        )

    def multi_reviewer_consensus(
        self,
        generator_model: str,
        reviewer_models: Sequence[str],
        min_diversity: float = 0.3,
    ) -> ConsensusResult:
        """Run verification across multiple reviewers and compute consensus."""
        results: list[ValidationResult] = []
        for reviewer in reviewer_models:
            results.append(self.verify(generator_model, reviewer))

        passed_results = [r for r in results if r.passed]
        gen_family = results[0].generator_family if results else ModelFamily.OTHER
        reviewer_families = tuple(r.reviewer_family for r in results)
        consensus_score = sum(r.diversity_score for r in passed_results) / max(len(reviewer_models), 1)

        passed = consensus_score >= min_diversity
        total_reviewers = len(reviewer_models)
        passed_count = len(passed_results)
        message = (
            f"Consensus: {passed_count}/{total_reviewers} reviewers passed "
            f"(consensus_score={consensus_score:.2f}, min_diversity={min_diversity})"
        )

        return ConsensusResult(
            passed=passed,
            generator_family=gen_family,
            reviewer_families=reviewer_families,
            consensus_score=round(consensus_score, 4),
            individual_results=tuple(results),
            message=message,
        )

    def suggest_reviewer_families(
        self,
        generator_model: str,
        min_diversity: float = 0.3,
    ) -> list[ModelFamily]:
        """Suggest reviewer families that provide sufficient diversity."""
        gen_family = self.detect_family(generator_model)
        suggestions: list[ModelFamily] = []
        for family in ModelFamily:
            if family == gen_family or family == ModelFamily.OTHER:
                continue
            diversity = self._compute_diversity_score(gen_family, family)
            if diversity >= min_diversity:
                suggestions.append(family)
        return suggestions

    def _compute_diversity_score(
        self,
        family_a: ModelFamily,
        family_b: ModelFamily,
    ) -> float:
        """Compute diversity score between two families (0.0-1.0)."""
        if family_a == family_b:
            return 0.0
        # Different companies entirely = high diversity
        high_diversity_pairs: set[tuple[ModelFamily, ModelFamily]] = {
            (ModelFamily.ANTHROPIC, ModelFamily.DEEPSEEK),
            (ModelFamily.ANTHROPIC, ModelFamily.OPENAI),
            (ModelFamily.ANTHROPIC, ModelFamily.GOOGLE),
            (ModelFamily.ANTHROPIC, ModelFamily.META),
            (ModelFamily.DEEPSEEK, ModelFamily.OPENAI),
            (ModelFamily.DEEPSEEK, ModelFamily.ANTHROPIC),
            (ModelFamily.OPENAI, ModelFamily.ANTHROPIC),
            (ModelFamily.OPENAI, ModelFamily.DEEPSEEK),
            (ModelFamily.OPENAI, ModelFamily.GOOGLE),
            (ModelFamily.GOOGLE, ModelFamily.ANTHROPIC),
            (ModelFamily.GOOGLE, ModelFamily.DEEPSEEK),
        }
        if (family_a, family_b) in high_diversity_pairs:
            return 0.85
        if family_a == ModelFamily.OTHER or family_b == ModelFamily.OTHER:
            return 0.5
        # Related models (e.g., Meta + Mistral as open-source) = medium diversity
        return 0.6

    @staticmethod
    def _suggest_alternatives(gen_family: ModelFamily) -> str:
        """Suggest alternative model families for review."""
        suggestions = {
            ModelFamily.ANTHROPIC: "deepseek-*, gpt-*, gemini-*",
            ModelFamily.DEEPSEEK: "claude-*, gpt-*",
            ModelFamily.OPENAI: "claude-*, deepseek-*, gemini-*",
            ModelFamily.GOOGLE: "claude-*, gpt-*, deepseek-*",
            ModelFamily.META: "claude-*, gpt-*, deepseek-*",
            ModelFamily.MISTRAL: "claude-*, gpt-*",
            ModelFamily.COHERE: "claude-*, gpt-*, deepseek-*",
            ModelFamily.OTHER: "claude-*, gpt-*, deepseek-*",
        }
        return suggestions.get(gen_family, "claude-*, gpt-*, deepseek-*")
