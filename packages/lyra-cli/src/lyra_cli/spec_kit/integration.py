"""Simple integration hook for Auto-Spec-Kit."""

from typing import Any
from lyra_cli.spec_kit.orchestrator import Orchestrator


class SpecKitIntegration:
    """Integration layer between agent loop and spec-kit."""

    def __init__(self, llm_client: Any = None):
        self.orchestrator = Orchestrator(llm_client)

    async def intercept_prompt(self, prompt: str, session: Any = None):
        """
        Intercept prompt before agent processing.
        Returns (should_intercept, feature_id, error).
        """
        result = await self.orchestrator.maybe_intercept(prompt, session)
        return result.intercepted, result.feature_id, result.error
