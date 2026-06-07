"""
ReAct (Reasoning + Acting) Engine.

Implements the ReAct pattern that interleaves reasoning and acting:
1. Thought: Reason about the current state
2. Action: Execute a tool/action
3. Observation: Observe the result
4. Repeat until final answer

Reference: Yao et al. "ReAct: Synergizing Reasoning and Acting in Language Models"
"""

import re
import time
from dataclasses import dataclass
from typing import Any

from anthropic import Anthropic

from ..types import (
    ComputeBudget,
    ReasoningConfig,
    ReasoningStep,
    ReasoningTrace,
    StepType,
)


@dataclass
class ToolCall:
    """Represents a tool call to be executed."""

    tool_name: str
    parameters: dict[str, Any]
    reasoning: str | None = None


@dataclass
class ToolResult:
    """Result of a tool execution."""

    tool_name: str
    output: str
    success: bool
    error: str | None = None


class ReActEngine:
    """
    ReAct reasoning engine that interleaves reasoning and acting.

    Features:
    - Thought-Action-Observation loop
    - Tool integration
    - Error recovery
    - Multi-step reasoning with actions
    """

    def __init__(
        self,
        api_key: str | None = None,
        tools: dict[str, dict[str, Any]] | None = None,
    ):
        """
        Initialize ReAct engine.

        Args:
            api_key: Anthropic API key
            tools: Dictionary of available tools
                Format: {
                    "tool_name": {
                        "description": "Tool description",
                        "parameters": {"param": "type"},
                        "function": callable
                    }
                }
        """
        self.client = Anthropic(api_key=api_key) if api_key else Anthropic()
        self.tools = tools or {}

    def reason(
        self,
        task: str,
        budget: ComputeBudget,
        config: ReasoningConfig,
    ) -> ReasoningTrace:
        """
        Execute ReAct reasoning loop.

        Args:
            task: The task to reason about
            budget: Compute budget
            config: Reasoning configuration

        Returns:
            Complete reasoning trace with actions and observations
        """
        start_time = time.time()
        trace = ReasoningTrace(
            task=task,
            strategy=config.strategy,
            steps=[],
        )

        iteration = 0
        history: list[ReasoningStep] = []

        while budget.has_budget() and iteration < config.max_steps:
            # Generate next thought/action
            response = self._generate_step(task, history, config)

            if response is None:
                break

            # Check if this is a final answer
            if self._is_final_answer(response):
                # Extract final answer
                answer = self._extract_answer(response)
                step = ReasoningStep(
                    content=answer,
                    step_type=StepType.CONCLUSION,
                )
                trace.add_step(step)
                history.append(step)
                break

            # Extract thought
            thought = self._extract_thought(response)
            if thought:
                thought_step = ReasoningStep(
                    content=f"Thought: {thought}",
                    step_type=StepType.HYPOTHESIS,
                )
                trace.add_step(thought_step)
                history.append(thought_step)
                budget.use_step()

            # Check for action
            tool_call = self._parse_action(response)
            if tool_call:
                # Record action
                action_step = ReasoningStep(
                    content=(
                        f"Action: {tool_call.tool_name}({self._format_params(tool_call.parameters)}"
                        f")"
                    ),
                    step_type=StepType.ANALYSIS,
                )
                trace.add_step(action_step)
                history.append(action_step)

                # Execute tool
                result = self._execute_tool(tool_call)

                # Record observation
                if result.success:
                    observation = f"Observation: {result.output}"
                else:
                    observation = f"Observation: Error - {result.error}"

                obs_step = ReasoningStep(
                    content=observation,
                    step_type=StepType.EVIDENCE,
                )
                trace.add_step(obs_step)
                history.append(obs_step)
                budget.use_step()

            budget.use_tokens(len(response.split()) * 2)
            iteration += 1

        # Finalize trace
        trace.duration = time.time() - start_time
        trace.token_count = budget.tokens_used
        trace.outcome = "success" if trace.get_conclusion() else "incomplete"

        return trace

    def _generate_step(
        self,
        task: str,
        history: list[ReasoningStep],
        config: ReasoningConfig,
    ) -> str | None:
        """Generate next reasoning step."""
        context = self._build_context(task, history)
        prompt = self._build_prompt(context)

        try:
            response = self.client.messages.create(
                model=config.model,
                max_tokens=500,
                temperature=config.temperature,
                messages=[{"role": "user", "content": prompt}],
            )

            return response.content[0].text
        except Exception as e:
            # Return error message
            return f"Error: {str(e)}"

    def _build_context(self, task: str, history: list[ReasoningStep]) -> str:
        """Build context from task and history."""
        lines = [f"Task: {task}\n"]

        # Add tool descriptions
        if self.tools:
            lines.append("Available tools:")
            lines.append(self._build_tool_descriptions())
            lines.append("")

        # Add history
        if history:
            lines.append("History:")
            for step in history[-10:]:  # Last 10 steps
                lines.append(step.content)
            lines.append("")

        return "\n".join(lines)

    def _build_prompt(self, context: str) -> str:
        """Build prompt for next step."""
        return f"""{context}

You are using the ReAct (Reasoning + Acting) pattern. Follow this format:

Thought: [Your reasoning about what to do next]
Action: [tool_name(param1='value1', param2='value2')] OR skip if no action needed
Observation: [Will be provided after action execution]

When you have enough information, provide:
Answer: [Your final answer]

Continue reasoning:"""

    def _build_tool_descriptions(self) -> str:
        """Build formatted tool descriptions."""
        lines = []
        for name, tool in self.tools.items():
            params = ", ".join(f"{k}: {v}" for k, v in tool.get("parameters", {}).items())
            lines.append(f"- {name}({params}): {tool.get('description', 'No description')}")
        return "\n".join(lines)

    def _parse_action(self, text: str) -> ToolCall | None:
        """
        Parse action from text.

        Expected format: Action: tool_name(param1='value1', param2='value2')
        """
        # Look for Action: pattern
        action_match = re.search(r"Action:\s*(\w+)\((.*?)\)", text, re.IGNORECASE)
        if not action_match:
            return None

        tool_name = action_match.group(1)
        params_str = action_match.group(2)

        # Parse parameters
        parameters = {}
        if params_str.strip():
            # Simple parameter parsing (handles key='value' or key="value")
            param_pattern = r"(\w+)\s*=\s*['\"]([^'\"]*)['\"]|(\w+)\s*=\s*(\d+)"
            for match in re.finditer(param_pattern, params_str):
                if match.group(1):
                    parameters[match.group(1)] = match.group(2)
                elif match.group(3):
                    parameters[match.group(3)] = int(match.group(4))

        # Extract reasoning if present
        thought_match = re.search(r"Thought:\s*(.+?)(?=Action:|$)", text, re.IGNORECASE | re.DOTALL)
        reasoning = thought_match.group(1).strip() if thought_match else None

        return ToolCall(
            tool_name=tool_name,
            parameters=parameters,
            reasoning=reasoning,
        )

    def _execute_tool(self, tool_call: ToolCall) -> ToolResult:
        """Execute a tool call."""
        # Check if tool exists
        if tool_call.tool_name not in self.tools:
            return ToolResult(
                tool_name=tool_call.tool_name,
                output="",
                success=False,
                error=f"Tool '{tool_call.tool_name}' not found",
            )

        tool = self.tools[tool_call.tool_name]
        function = tool.get("function")

        if not function:
            return ToolResult(
                tool_name=tool_call.tool_name,
                output="",
                success=False,
                error="Tool has no function defined",
            )

        # Execute tool
        try:
            output = function(**tool_call.parameters)
            return ToolResult(
                tool_name=tool_call.tool_name,
                output=str(output),
                success=True,
            )
        except Exception as e:
            return ToolResult(
                tool_name=tool_call.tool_name,
                output="",
                success=False,
                error=str(e),
            )

    def _is_final_answer(self, text: str) -> bool:
        """Check if text contains a final answer."""
        final_markers = ["answer:", "final answer:", "conclusion:"]
        text_lower = text.lower()
        return any(marker in text_lower for marker in final_markers)

    def _extract_answer(self, text: str) -> str:
        """Extract final answer from text."""
        # Look for Answer: or Final Answer: or Conclusion:
        match = re.search(
            r"(?:Answer|Final Answer|Conclusion):\s*(.+)",
            text,
            re.IGNORECASE | re.DOTALL,
        )
        if match:
            return match.group(1).strip()
        return text

    def _extract_thought(self, text: str) -> str:
        """Extract thought from text."""
        # Look for Thought: pattern
        match = re.search(
            r"Thought:\s*(.+?)(?=\n(?:Action|Observation|Answer)|$)",
            text,
            re.IGNORECASE | re.DOTALL,
        )
        if match:
            return match.group(1).strip()

        # If no explicit thought marker, return first line
        lines = text.strip().split("\n")
        return lines[0] if lines else text

    def _format_params(self, parameters: dict[str, Any]) -> str:
        """Format parameters for display."""
        if not parameters:
            return ""
        parts = []
        for key, value in parameters.items():
            if isinstance(value, str):
                parts.append(f"{key}='{value}'")
            else:
                parts.append(f"{key}={value}")
        return ", ".join(parts)
