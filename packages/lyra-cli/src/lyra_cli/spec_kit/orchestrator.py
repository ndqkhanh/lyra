"""Main orchestrator for Auto-Spec-Kit flow."""

from __future__ import annotations
from typing import Any

from .models import InterceptResult, Verdict
from .detector import Detector
from .state import StateManager
from .drafter import Drafter
from .writer import Writer


class Orchestrator:
    """Orchestrates the spec-kit flow from detection to execution."""

    def __init__(self, llm_client: Any = None, event_bus: Any = None):
        self.detector = Detector(llm_client)
        self.state_manager = StateManager()
        self.drafter = Drafter(llm_client, event_bus)
        self.writer = Writer(event_bus)

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

        # Spec-worthy - start state machine
        try:
            feature_id = await self._run_state_machine(prompt)
            return InterceptResult(intercepted=True, feature_id=feature_id)
        except Exception as e:
            return InterceptResult(intercepted=False, error=str(e))

    async def _run_state_machine(self, prompt: str) -> str:
        """Run the full spec-kit state machine."""
        # Store original prompt
        self.state_manager.state.original_prompt = prompt

        # Phase 1: Constitution check (skip for now)
        self.state_manager.update_phase("constitution_check")
        # Would check constitution here

        # Phase 2: Draft spec
        self.state_manager.update_phase("drafting_spec")
        spec = await self.drafter.draft_spec(prompt)
        self.state_manager.update_draft("spec", spec)
        # Would wait for approval here

        # Phase 3: Draft plan
        self.state_manager.update_phase("drafting_plan")
        plan = await self.drafter.draft_plan(spec)
        self.state_manager.update_draft("plan", plan)
        # Would wait for approval here

        # Phase 4: Draft tasks
        self.state_manager.update_phase("drafting_tasks")
        tasks = await self.drafter.draft_tasks(plan)
        self.state_manager.update_draft("tasks", tasks)
        # Would wait for approval here

        # Phase 5: Write to disk
        self.state_manager.update_phase("writing_disk")
        feature_id = self.writer.generate_feature_id(prompt)
        await self.writer.write_artifacts(feature_id, spec, plan, tasks)

        # Phase 6: Executing
        self.state_manager.update_phase("executing")

        return feature_id
