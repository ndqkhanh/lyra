"""
Cross-model verification for adversarial result checking.

Uses different model families to verify results, reducing single-model bias
and improving reliability through diverse perspectives.
"""

from dataclasses import dataclass
from typing import Any, Optional


@dataclass
class VerificationResult:
    """Result of cross-model verification."""

    verified: bool
    confidence: float
    verification_model: str
    discrepancies: list[str]
    verification_output: Optional[str] = None


class CrossModelVerifier:
    """Verify results using different models for adversarial checking."""

    def __init__(self, model_router):
        """
        Initialize cross-model verifier.

        Args:
            model_router: ModelRouter instance for model selection
        """
        self.model_router = model_router

    def get_verification_model(self, primary_model: str) -> str:
        """
        Get verification model from different family.

        Args:
            primary_model: The primary model used for generation

        Returns:
            Verification model from different family
        """
        primary_family = self.model_router.get_model_family(primary_model)

        if primary_family == "claude":
            return "gpt-4o"
        elif primary_family == "gpt":
            return "claude-sonnet-4-6"
        else:
            return "claude-sonnet-4-6"

    async def verify_with_different_model(
        self,
        result: Any,
        primary_model: str,
        verification_prompt: str
    ) -> VerificationResult:
        """
        Use different model family to verify results.

        Args:
            result: The result to verify
            primary_model: Model that generated the result
            verification_prompt: Prompt for verification task

        Returns:
            VerificationResult with verification outcome
        """
        verification_model = self.get_verification_model(primary_model)

        # Placeholder for actual LLM call
        # In production, this would call the verification model
        # For now, return a mock result
        return VerificationResult(
            verified=True,
            confidence=0.95,
            verification_model=verification_model,
            discrepancies=[],
            verification_output=None
        )

    def create_verification_prompt(
        self,
        original_task: str,
        result: Any,
        verification_criteria: list[str]
    ) -> str:
        """
        Create verification prompt for cross-model checking.

        Args:
            original_task: The original task description
            result: The result to verify
            verification_criteria: List of criteria to check

        Returns:
            Formatted verification prompt
        """
        criteria_text = "\n".join(f"- {c}" for c in verification_criteria)

        prompt = f"""Verify the following result against the original task.

Original Task:
{original_task}

Result to Verify:
{result}

Verification Criteria:
{criteria_text}

Provide:
1. Whether the result satisfies all criteria (yes/no)
2. Confidence level (0.0-1.0)
3. List any discrepancies or issues found
"""
        return prompt

    def compare_results(
        self,
        primary_result: Any,
        verification_result: Any
    ) -> list[str]:
        """
        Compare primary and verification results to find discrepancies.

        Args:
            primary_result: Result from primary model
            verification_result: Result from verification model

        Returns:
            List of discrepancies found
        """
        discrepancies = []

        # Simple string comparison for now
        if str(primary_result) != str(verification_result):
            discrepancies.append("Results differ between models")

        return discrepancies
