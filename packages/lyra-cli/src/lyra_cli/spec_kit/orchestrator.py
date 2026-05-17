"""Main orchestrator for Auto-Spec-Kit flow."""

from __future__ import annotations
from typing import Any

from .models import InterceptResult, Verdict
from .detector import Detector
from .state import StateManager


class Orchestrator:
    """Orchestrates the spec-kit flow from detection to execution."""

    def __init__(self, llm_client: Any = None):
        self.detector = Detector(llm_client)
        self.state_manager = StateManager()

    async def maybe_intercept(
        self,
        prompt: str,
        session: Any = None
    ) -> InterceptResult:
        """
        Intercept prompt if spec-worthy.
        Returns InterceptResult(intercepted=False) for non-spec-worthy prompts.
        """
        # Get current phase
        current_phase = self.state_manager.state.phase

        # Classify prompt
        verdict: Verdict = await self.detector.classify(prompt, current_phase)

        # Not spec-worthy - pass through
        if not verdict.spec_worthy:
            return InterceptResult(intercepted=False)

        # Spec-worthy - would start state machine here
        # For Phase 1, just return not intercepted
        return InterceptResult(intercepted=False)
