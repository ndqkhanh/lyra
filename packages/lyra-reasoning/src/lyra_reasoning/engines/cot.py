"""
Chain-of-Thought Reasoning Engine.
"""

import time
from typing import List, Optional

from anthropic import Anthropic

from ..types import (
    ComputeBudget,
    ReasoningConfig,
    ReasoningStep,
    ReasoningTrace,
    StepType,
)


class ChainOfThoughtEngine:
    """
    Extended chain-of-thought reasoning with verification and backtracking.

    Features:
    - Step-by-step reasoning
    - Self-verification at each step
    - Backtracking on errors
    - Adaptive depth
    """

    def __init__(self, api_key: Optional[str] = None):
        self.client = Anthropic(api_key=api_key) if api_key else Anthropic()

    def reason(
        self,
        task: str,
        budget: ComputeBudget,
        config: ReasoningConfig,
    ) -> ReasoningTrace:
        """
        Execute chain-of-thought reasoning.

        Args:
            task: The task to reason about
            budget: Compute budget
            config: Reasoning configuration

        Returns:
            Complete reasoning trace
        """
        start_time = time.time()
        trace = ReasoningTrace(
            task=task,
            strategy=config.strategy,
            steps=[],
        )

        current_state = task
        step_count = 0

        while budget.has_budget() and step_count < config.max_steps:
            # Generate next reasoning step
            step = self._generate_step(current_state, trace.steps, config)

            if step is None:
                break

            # Verify step if enabled
            if config.enable_verification:
                verification_score = self._verify_step(step, current_state, trace.steps)
                step.verification_score = verification_score

                # Backtrack if verification fails
                if verification_score < config.verification_threshold and config.enable_backtracking:
                    if len(trace.steps) > 0:
                        # Remove last step and try alternative
                        removed_step = trace.steps.pop()
                        backtrack_step = ReasoningStep(
                            content=f"Backtracking from: {removed_step.content[:100]}...",
                            step_type=StepType.BACKTRACK,
                            verification_score=1.0,
                        )
                        trace.add_step(backtrack_step)
                        budget.use_step()
                        continue

            # Add step to trace
            trace.add_step(step)
            budget.use_step()
            budget.use_tokens(len(step.content.split()) * 2)  # Rough estimate
            step_count += 1

            # Update current state
            current_state = self._update_state(current_state, step)

            # Check if we've reached a conclusion
            if step.step_type == StepType.CONCLUSION:
                break

        # Finalize trace
        trace.duration = time.time() - start_time
        trace.token_count = budget.tokens_used
        trace.outcome = "success" if trace.get_conclusion() else "incomplete"

        return trace

    def _generate_step(
        self,
        current_state: str,
        previous_steps: List[ReasoningStep],
        config: ReasoningConfig,
    ) -> Optional[ReasoningStep]:
        """Generate the next reasoning step."""
        # Build context from previous steps
        context = self._build_context(current_state, previous_steps)

        # Determine step type
        step_type = self._determine_step_type(previous_steps)

        # Generate step content
        prompt = self._build_prompt(context, step_type)

        try:
            response = self.client.messages.create(
                model=config.model,
                max_tokens=500,
                temperature=config.temperature,
                messages=[{"role": "user", "content": prompt}],
            )

            content = response.content[0].text

            return ReasoningStep(
                content=content,
                step_type=step_type,
            )
        except Exception as e:
            # Return error step
            return ReasoningStep(
                content=f"Error generating step: {str(e)}",
                step_type=StepType.ANALYSIS,
                verification_score=0.0,
            )

    def _verify_step(
        self,
        step: ReasoningStep,
        current_state: str,
        previous_steps: List[ReasoningStep],
    ) -> float:
        """
        Verify a reasoning step.

        Returns:
            Verification score (0.0 to 1.0)
        """
        # Simple heuristic verification
        score = 0.5  # Base score

        # Check for logical consistency
        if len(step.content) > 20:
            score += 0.2

        # Check for evidence/reasoning
        reasoning_indicators = ["because", "therefore", "thus", "since", "given"]
        if any(ind in step.content.lower() for ind in reasoning_indicators):
            score += 0.2

        # Check for contradictions with previous steps
        if previous_steps:
            # Simple check: no direct contradictions
            if "not" in step.content.lower() and "not" not in previous_steps[-1].content.lower():
                score -= 0.1

        return min(1.0, max(0.0, score))

    def _build_context(
        self,
        current_state: str,
        previous_steps: List[ReasoningStep],
    ) -> str:
        """Build context from current state and previous steps."""
        context = f"Task: {current_state}\n\n"

        if previous_steps:
            context += "Previous reasoning steps:\n"
            for i, step in enumerate(previous_steps[-5:], 1):  # Last 5 steps
                context += f"{i}. [{step.step_type.value}] {step.content[:200]}\n"

        return context

    def _determine_step_type(self, previous_steps: List[ReasoningStep]) -> StepType:
        """Determine the type of the next step."""
        if not previous_steps:
            return StepType.HYPOTHESIS

        last_step = previous_steps[-1]

        # Progression: hypothesis → evidence → analysis → conclusion
        if last_step.step_type == StepType.HYPOTHESIS:
            return StepType.EVIDENCE
        elif last_step.step_type == StepType.EVIDENCE:
            return StepType.ANALYSIS
        elif last_step.step_type == StepType.ANALYSIS:
            # Check if we have enough analysis
            analysis_count = sum(1 for s in previous_steps if s.step_type == StepType.ANALYSIS)
            if analysis_count >= 2:
                return StepType.CONCLUSION
            return StepType.EVIDENCE
        elif last_step.step_type == StepType.BACKTRACK:
            return StepType.HYPOTHESIS
        else:
            return StepType.CONCLUSION

    def _build_prompt(self, context: str, step_type: StepType) -> str:
        """Build prompt for step generation."""
        prompts = {
            StepType.HYPOTHESIS: "Based on the task, what is your initial hypothesis or approach? Be specific and clear.",
            StepType.EVIDENCE: "What evidence or information supports or refutes the current reasoning? Provide concrete details.",
            StepType.ANALYSIS: "Analyze the evidence and reasoning so far. What conclusions can you draw?",
            StepType.CONCLUSION: "Based on all the reasoning above, what is your final conclusion? Be definitive.",
        }

        instruction = prompts.get(step_type, "Continue reasoning about this task.")

        return f"{context}\n\n{instruction}\n\nProvide your reasoning step:"

    def _update_state(self, current_state: str, step: ReasoningStep) -> str:
        """Update reasoning state with new step."""
        # For now, just append the step
        return f"{current_state}\n\n{step.content}"
