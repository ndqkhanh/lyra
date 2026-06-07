from __future__ import annotations

import time
from dataclasses import dataclass, field
from datetime import datetime, timezone
from typing import Any, Protocol


@dataclass(frozen=True)
class ReActStep:
    thought: str
    action: str
    observation: str
    tool_calls: tuple[str, ...] = ()
    timestamp: datetime = field(default_factory=lambda: datetime.now(timezone.utc))


@dataclass(frozen=True)
class ReActTrace:
    steps: tuple[ReActStep, ...]
    completed: bool = False
    total_duration_ms: float = 0.0


@dataclass(frozen=True)
class AuditResult:
    issues_found: list[str] = field(default_factory=list)
    suggestions: list[str] = field(default_factory=list)


class ToolFunction(Protocol):
    async def __call__(self, action: str, **kwargs: Any) -> str: ...


class EnhancedReActLoop:
    """Enhanced ReAct loop with standard Reason-Act-Observe cycle and tool-call auditing."""

    def __init__(self) -> None:
        self._trace_history: dict[str, ReActTrace] = {}

    async def run(
        self,
        task: str,
        tools: dict[str, ToolFunction] | None = None,
        max_iterations: int = 10,
    ) -> ReActTrace:
        tools = tools or {}
        steps: list[ReActStep] = []
        start = time.time()
        completed = False

        for i in range(max_iterations):
            if self._should_stop(task, steps):
                completed = True
                break

            thought = self._generate_thought(task, steps, i)
            action, tool_calls = self._decide_action(thought, tools)
            observation = await self._execute_action(action, tools)
            step = ReActStep(
                thought=thought,
                action=action,
                observation=observation,
                tool_calls=tuple(tool_calls),
            )
            steps.append(step)

        duration = (time.time() - start) * 1000
        trace = ReActTrace(steps=tuple(steps), completed=completed, total_duration_ms=duration)
        self._trace_history[task] = trace
        return trace

    def _should_stop(self, task: str, steps: list[ReActStep]) -> bool:
        if not steps:
            return False
        last = steps[-1]
        return "answer:" in last.action.lower() or "final:" in last.action.lower()

    def _generate_thought(self, task: str, steps: list[ReActStep], step_num: int) -> str:
        if not steps:
            return f"Analyzing task: {task[:60]}"
        last = steps[-1]
        return f"Based on observation: {last.observation[:40]}..."

    def _decide_action(
        self, thought: str, tools: dict[str, ToolFunction]
    ) -> tuple[str, list[str]]:
        if not tools:
            return f"final: completed thought - {thought[:40]}", []
        tool_name = next(iter(tools.keys()))
        return f"{tool_name}: process", [tool_name]

    async def _execute_action(
        self, action: str, tools: dict[str, ToolFunction]
    ) -> str:
        if "final:" in action.lower() or "answer:" in action.lower():
            return f"Completed: {action}"
        for tool_name, tool_func in tools.items():
            if action.startswith(tool_name):
                result = await tool_func(action, arg="test")
                return result
        return f"Executed: {action}"

    def audit_tool_calls(self, trace: ReActTrace) -> AuditResult:
        issues: list[str] = []
        suggestions: list[str] = []

        all_calls: list[str] = []
        for step in trace.steps:
            all_calls.extend(step.tool_calls)

        # Check for missing tool calls.
        if not all_calls:
            issues.append("No tool calls made during the trace")

        # Check for redundant tool calls.
        seen: set[str] = set()
        for call in all_calls:
            if call in seen:
                issues.append(f"Redundant tool call: {call}")
                suggestions.append(f"Consider caching result of {call}")
            seen.add(call)

        # Check for completed trace with no answer/terminal action.
        if trace.completed and trace.steps:
            last_action = trace.steps[-1].action.lower()
            if "answer" not in last_action and "final" not in last_action:
                issues.append("Trace completed without a final answer action")

        return AuditResult(issues_found=issues, suggestions=suggestions)
