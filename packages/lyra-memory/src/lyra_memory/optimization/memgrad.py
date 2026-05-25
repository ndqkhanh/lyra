"""
MemGrad Pipeline — textual gradient descent on agent prompts using
accumulated memory feedback.

Source: MemGrad (GeaPE7iw1V), ICLR 2026 MemAgent Workshop.
"""

from __future__ import annotations

from dataclasses import dataclass, field
from datetime import datetime, timezone
from typing import Protocol
from uuid import uuid4


class LLMClient(Protocol):
    """Protocol for LLM interaction."""

    async def complete(self, prompt: str) -> str: ...


@dataclass
class TextGrad:
    """A single textual gradient — actionable feedback for a specific role."""

    role: str
    gradient: str
    severity: float = 0.5
    pattern: str = "one-off"


@dataclass
class AgentTrajectory:
    """A record of an agent's execution — steps, outcome, and feedback."""

    task: str
    role: str
    outcome: str  # "success" | "partial" | "failure"
    steps: list[str] = field(default_factory=list)
    feedback: str = ""
    id: str = field(default_factory=lambda: uuid4().hex)


@dataclass
class RoleCluster:
    """Gradients grouped by agent role."""

    role: str
    gradients: list[TextGrad] = field(default_factory=list)

    @property
    def average_severity(self) -> float:
        if not self.gradients:
            return 0.0
        return sum(g.severity for g in self.gradients) / len(self.gradients)

    @property
    def recurring_count(self) -> int:
        return sum(1 for g in self.gradients if g.pattern == "recurring")


@dataclass
class FailurePattern:
    """A recognized failure pattern stored in retrospective memory."""

    role: str
    description: str
    frequency: int = 1
    severity: float = 0.5
    last_seen: datetime = field(default_factory=lambda: datetime.now(timezone.utc))
    id: str = field(default_factory=lambda: uuid4().hex)

    def record_occurrence(self) -> None:
        self.frequency += 1
        self.last_seen = datetime.now(timezone.utc)


@dataclass
class MemGradPipeline:
    """Memory-guided optimization via textual gradient descent.

    Decomposes agent trajectory feedback into fine-grained textual gradients,
    clusters them by role, abstracts into retrospective/prospective memories,
    and applies gradients to update agent prompts.
    """

    llm: LLMClient

    async def decompose_feedback(
        self, trajectories: list[AgentTrajectory],
    ) -> list[TextGrad]:
        """Decompose trajectory feedback into fine-grained textual gradients."""
        if not trajectories:
            return []

        formatted = self._format_trajectories(trajectories)
        prompt = f"""Analyze these agent trajectories and decompose each failure or suboptimal
behavior into a textual gradient — a specific, actionable statement of
what went wrong and what should change.

Trajectories:
{formatted}

For each issue found, output JSON array:
[{{
    "role": "planner|executor|reviewer|communicator",
    "gradient": "Specific issue + suggested improvement",
    "severity": <float 0.0-1.0>,
    "pattern": "recurring|one-off"
}}]

If no issues found, output empty array []."""

        response = await self.llm.complete(prompt)
        return self._parse_gradients(response)

    async def cluster_by_role(self, gradients: list[TextGrad]) -> list[RoleCluster]:
        """Cluster gradients by agent role."""
        clusters: dict[str, list[TextGrad]] = {}
        for g in gradients:
            clusters.setdefault(g.role, []).append(g)
        return [RoleCluster(role=r, gradients=gs) for r, gs in clusters.items()]

    async def optimize_prompt(
        self,
        role: str,
        current_prompt: str,
        retrospective: str,
        prospective: str,
    ) -> str:
        """Apply retrospective and prospective memory to update a prompt."""
        if not retrospective and not prospective:
            return current_prompt

        revision_prompt = f"""You are optimizing an AI agent's {role} system prompt.

CURRENT PROMPT:
{current_prompt}

PAST FAILURES TO AVOID:
{retrospective or "None recorded"}

CORRECTIVE INTENTIONS TO INCORPORATE:
{prospective or "None recorded"}

Revise the prompt to address the failures and incorporate the corrective intentions.
Maintain the original purpose and scope. Output the revised prompt only."""

        return await self.llm.complete(revision_prompt)

    @staticmethod
    def _format_trajectories(trajectories: list[AgentTrajectory]) -> str:
        lines = []
        for i, t in enumerate(trajectories):
            lines.append(f"Trajectory {i+1}:")
            lines.append(f"  Task: {t.task[:200]}")
            lines.append(f"  Role: {t.role}")
            lines.append(f"  Outcome: {t.outcome}")
            lines.append(f"  Steps: {len(t.steps)}")
            lines.append(f"  Feedback: {t.feedback[:500]}")
            lines.append("")
        return "\n".join(lines)

    @staticmethod
    def _parse_gradients(response: str) -> list[TextGrad]:
        import json

        try:
            data = json.loads(_extract_json(response))
            if not isinstance(data, list):
                return []
            return [
                TextGrad(
                    role=str(item.get("role", "unknown")),
                    gradient=str(item.get("gradient", "")),
                    severity=float(item.get("severity", 0.5)),
                    pattern=str(item.get("pattern", "one-off")),
                )
                for item in data
            ]
        except (json.JSONDecodeError, TypeError, ValueError):
            return []


def _extract_json(text: str) -> str:
    if "```json" in text:
        start = text.index("```json") + 7
        end = text.index("```", start)
        return text[start:end].strip()
    if "```" in text:
        start = text.index("```") + 3
        end = text.index("```", start)
        return text[start:end].strip()
    brace_start = text.find("[")
    brace_end = text.rfind("]")
    if brace_start >= 0 and brace_end > brace_start:
        return text[brace_start : brace_end + 1]
    return text.strip()
