"""Agent orchestrator for delegating tasks to specialized agents."""

from __future__ import annotations

import re
from collections.abc import Callable
from dataclasses import dataclass
from typing import Any

from .agent_registry import AgentRegistry


@dataclass(frozen=True)
class AgentResult:
    success: bool
    output: str
    error: str | None = None
    agent_name: str = ""
    duration_ms: float = 0.0


class AgentOrchestrator:
    """Delegates tasks to specialized agents with keyword-based auto-selection."""

    _DEFAULT_CAPABILITIES: dict[str, list[str]] = {
        "explore": ["search", "find", "locate", "grep", "file", "directory"],
        "code-reviewer": ["review", "audit", "inspect", "check", "quality", "lint"],
        "debugger": ["debug", "fix", "error", "bug", "crash", "trace", "stack"],
        "architect": ["design", "architecture", "system", "structure", "pattern"],
        "planner": ["plan", "roadmap", "milestone", "estimate", "schedule"],
        "tdd-guide": ["test", "tdd", "coverage", "unittest", "pytest", "mock"],
        "executor": ["implement", "build", "create", "add", "write", "generate"],
        "document-specialist": ["doc", "readme", "documentation", "explain", "guide"],
        "security-reviewer": ["security", "vulnerability", "auth", "xss", "sql", "csrf"],
        "test-engineer": ["integration", "e2e", "end-to-end", "acceptance", "scenario"],
        "designer": ["ui", "ux", "design", "style", "css", "theme", "layout"],
    }

    def __init__(self, registry: AgentRegistry) -> None:
        self._registry = registry
        self._executor: Callable[[str, str, dict[str, Any] | None], AgentResult] | None = None

    def delegate(
        self, agent_name: str, task: str, context: dict[str, Any] | None = None
    ) -> AgentResult:
        agent = self._registry.get_agent(agent_name)
        if not agent:
            return AgentResult(success=False, output="", error=f"Agent '{agent_name}' not found")

        if self._executor:
            return self._executor(agent.name, task, context)

        return AgentResult(
            success=True,
            output=f"Agent '{agent_name}' queued for: {task}",
            agent_name=agent.name,
        )

    def auto_delegate(self, task: str, context: dict[str, Any] | None = None) -> AgentResult:
        agents = self._registry.list_agents()
        if not agents:
            return AgentResult(success=False, output="", error="No agents registered")

        task_lower = task.lower()
        scores: dict[str, int] = {}

        for agent in agents:
            score = 0
            capabilities = self._DEFAULT_CAPABILITIES.get(agent.name, [])
            for keyword in capabilities:
                if re.search(rf"\b{re.escape(keyword)}\b", task_lower):
                    score += 1
            desc_words = set(agent.description.lower().split())
            task_words = set(task_lower.split())
            score += len(desc_words & task_words)
            scores[agent.name] = score

        best = max(scores, key=lambda k: scores[k]) if scores else ""
        if not best or scores.get(best, 0) == 0:
            return AgentResult(
                success=False, output="", error="No suitable agent found for task"
            )

        return self.delegate(best, task, context)

    def set_executor(
        self, executor: Callable[[str, str, dict[str, Any] | None], AgentResult]
    ) -> None:
        self._executor = executor
