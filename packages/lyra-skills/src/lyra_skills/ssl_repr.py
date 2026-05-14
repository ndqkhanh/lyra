"""SSL skill representation — Phase G of the Lyra skill-curation plan.

Disentangles SKILL.md text into three machine-queryable layers:
  Scheduling  — WHEN to invoke (triggers, preconditions)
  Structural  — HOW the work is organized (execution steps, DAG)
  Logical     — WHAT is used (tools, actions, side effects)

Grounded in:
- arXiv:2604.24026 — From Skill Text to Skill Structure (SSL)
- +12.3% skill discovery MRR@50, +24.4% risk assessment F1 over plain text
"""
from __future__ import annotations

import re
from dataclasses import dataclass, field
from typing import Optional


__all__ = [
    "SSLScheduling",
    "SSLStructural",
    "SSLLogical",
    "SSLSkill",
    "SSLNormalizer",
    "ssl_matches",
]


@dataclass
class SSLScheduling:
    """WHEN should this skill be invoked?"""

    triggers: list[str] = field(default_factory=list)        # keyword/phrase triggers
    preconditions: list[str] = field(default_factory=list)   # required context state
    context_requirements: list[str] = field(default_factory=list)  # env requirements

    def matches_query(self, query: str) -> bool:
        q = query.lower()
        return any(t.lower() in q for t in self.triggers)


@dataclass
class SSLStructural:
    """HOW is the work organized?"""

    execution_steps: list[str] = field(default_factory=list)
    workflow_type: str = "sequential"   # sequential | parallel | conditional | loop
    estimated_turns: int = 1


@dataclass
class SSLLogical:
    """WHAT operations and resources are used?"""

    actions: list[str] = field(default_factory=list)
    tools_required: list[str] = field(default_factory=list)
    side_effects: list[str] = field(default_factory=list)
    state_changes: list[str] = field(default_factory=list)

    @property
    def risk_level(self) -> str:
        destructive = {"delete", "remove", "drop", "overwrite", "truncate", "format"}
        text = " ".join(self.side_effects + self.actions).lower()
        if any(d in text for d in destructive):
            return "high"
        if self.side_effects:
            return "medium"
        return "low"


@dataclass
class SSLSkill:
    """Full SSL-structured skill artifact."""

    skill_id: str
    name: str
    description: str = ""
    scheduling: SSLScheduling = field(default_factory=SSLScheduling)
    structural: SSLStructural = field(default_factory=SSLStructural)
    logical: SSLLogical = field(default_factory=SSLLogical)
    raw_text: str = ""

    def to_frontmatter(self) -> str:
        """Serialize SSL metadata as YAML frontmatter for SKILL.md."""
        lines = [
            "---",
            f"name: {self.name}",
            f"description: {self.description!r}",
            f"ssl_triggers: {self.scheduling.triggers}",
            f"ssl_tools: {self.logical.tools_required}",
            f"ssl_risk: {self.logical.risk_level}",
            f"ssl_workflow: {self.structural.workflow_type}",
            "---",
        ]
        return "\n".join(lines)


class SSLNormalizer:
    """Converts plain SKILL.md text into an SSLSkill via heuristic extraction.

    A full production implementation would use an LLM-based normalizer;
    this version uses deterministic pattern extraction suitable for testing
    and bootstrapping, matching the paper's described normalizer output.
    """

    # Patterns for scheduling extraction
    _TRIGGER_PATTERNS = re.compile(
        r"(?:when|if|trigger|use when|apply when)[:\s]+([^\n.]+)", re.I
    )
    _PRECOND_PATTERNS = re.compile(
        r"(?:requires?|needs?|prerequisite)[:\s]+([^\n.]+)", re.I
    )
    # Patterns for structural extraction
    _STEP_PATTERN = re.compile(r"^\s*(?:\d+[.)]\s*|[-*]\s+)(.+)", re.M)
    # Patterns for logical extraction
    _TOOL_PATTERN = re.compile(
        r"(?:tool|command|call|run|execute|use)[:\s]+`?([a-zA-Z_][a-zA-Z0-9_]*)`?", re.I
    )
    _SIDE_EFFECT_PATTERN = re.compile(
        r"(?:creates?|writes?|deletes?|modifies?|updates?)[:\s]+([^\n.]+)", re.I
    )

    def normalize(self, skill_id: str, name: str, text: str) -> SSLSkill:
        scheduling = SSLScheduling(
            triggers=self._extract(self._TRIGGER_PATTERNS, text),
            preconditions=self._extract(self._PRECOND_PATTERNS, text),
        )
        steps = self._extract(self._STEP_PATTERN, text)
        structural = SSLStructural(
            execution_steps=steps,
            workflow_type=self._infer_workflow(text),
            estimated_turns=max(1, len(steps)),
        )
        logical = SSLLogical(
            tools_required=self._extract(self._TOOL_PATTERN, text),
            side_effects=self._extract(self._SIDE_EFFECT_PATTERN, text),
        )
        description = self._extract_description(text)
        return SSLSkill(
            skill_id=skill_id,
            name=name,
            description=description,
            scheduling=scheduling,
            structural=structural,
            logical=logical,
            raw_text=text,
        )

    @staticmethod
    def _extract(pattern: re.Pattern, text: str) -> list[str]:
        return [m.group(1).strip() for m in pattern.finditer(text)]

    @staticmethod
    def _infer_workflow(text: str) -> str:
        text_l = text.lower()
        if "in parallel" in text_l or "concurrently" in text_l:
            return "parallel"
        if "if " in text_l and "else" in text_l:
            return "conditional"
        if "repeat" in text_l or "until" in text_l or "loop" in text_l:
            return "loop"
        return "sequential"

    @staticmethod
    def _extract_description(text: str) -> str:
        for line in text.splitlines():
            line = line.strip()
            if line and not line.startswith("#") and not line.startswith("---"):
                return line[:200]
        return ""


def ssl_matches(skill: SSLSkill, query: str, risk_cap: Optional[str] = None) -> bool:
    """Return True if the skill is applicable for the query and within risk cap."""
    if not skill.scheduling.matches_query(query):
        return False
    if risk_cap is None:
        return True
    risk_order = {"low": 0, "medium": 1, "high": 2}
    return risk_order.get(skill.logical.risk_level, 0) <= risk_order.get(risk_cap, 2)
