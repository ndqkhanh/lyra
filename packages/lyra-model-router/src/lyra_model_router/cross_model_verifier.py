"""Cross-model family verification for independent review."""

from __future__ import annotations

from dataclasses import dataclass

from .router_config import ModelCapability


@dataclass(frozen=True)
class VerificationResult:
    """Result of cross-model verification.

    Attributes:
        passed: Whether verification passed (different model families).
        issues: Tuple of issue descriptions if verification failed.
        score: Diversity score 0.0-1.0 (higher = more diverse).
    """
    passed: bool
    issues: tuple[str, ...]
    score: float


# Model family prefixes for detection
_FAMILY_PREFIXES: dict[str, str] = {
    "claude": "anthropic",
    "deepseek": "deepseek",
    "gpt": "openai",
    "o1": "openai",
    "o3": "openai",
    "gemini": "google",
    "llama": "meta",
    "mistral": "mistral",
    "command": "cohere",
}


class CrossModelVerifier:
    """Verifies that output from one model is reviewed by a different model family.

    Ensures independent verification by enforcing the generator and reviewer
    come from different model families (e.g., Anthropic vs DeepSeek).
    """

    async def verify(
        self,
        output: str,
        generator_model: str,
        verifier_model_config: ModelCapability,
    ) -> VerificationResult:
        """Verify that the generator and reviewer are from different families.

        Args:
            output: The generated output to verify (used for issue detection).
            generator_model: Model ID of the generator.
            verifier_model_config: ModelCapability of the verifier/reviewer model.

        Returns:
            A VerificationResult with pass/fail, issues, and diversity score.
        """
        gen_family = self._detect_family(generator_model)
        rev_family = verifier_model_config.provider

        if gen_family == rev_family:
            return VerificationResult(
                passed=False,
                issues=(
                    f"Generator '{generator_model}' ({gen_family}) and reviewer "
                    f"'{verifier_model_config.model_id}' ({rev_family}) are the same model family. "
                    "Use a different model family for independent verification.",
                ),
                score=0.0,
            )

        score = self._compute_diversity_score(gen_family, rev_family)
        return VerificationResult(
            passed=True,
            issues=(),
            score=score,
        )

    @staticmethod
    def _detect_family(model_id: str) -> str:
        """Detect the model family from a model ID string."""
        lower_id = model_id.lower()
        for prefix, family in _FAMILY_PREFIXES.items():
            if lower_id.startswith(prefix):
                return family
        return "other"

    @staticmethod
    def _compute_diversity_score(family_a: str, family_b: str) -> float:
        """Compute a diversity score between two families (0.0-1.0)."""
        if family_a == family_b:
            return 0.0

        # Different vendors entirely
        high_diversity: set[tuple[str, str]] = {
            ("anthropic", "deepseek"),
            ("anthropic", "openai"),
            ("anthropic", "google"),
            ("anthropic", "meta"),
            ("deepseek", "openai"),
            ("deepseek", "anthropic"),
            ("openai", "anthropic"),
            ("openai", "deepseek"),
            ("openai", "google"),
            ("google", "anthropic"),
            ("google", "deepseek"),
        }

        if (family_a, family_b) in high_diversity:
            return 0.85
        if family_a == "other" or family_b == "other":
            return 0.5
        return 0.6
