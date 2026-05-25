"""
Dual Memory Structures — Retrospective (failure patterns) and
Prospective (corrective intentions) memory for self-optimization.

Source: MemGrad (GeaPE7iw1V), ICLR 2026 MemAgent Workshop.
"""

from __future__ import annotations

import re
from dataclasses import dataclass, field
from datetime import datetime, timezone
from typing import TYPE_CHECKING, Protocol
from uuid import uuid4

if TYPE_CHECKING:
    from lyra_memory.optimization.memgrad import FailurePattern


class LLMClient(Protocol):
    """Protocol for LLM interaction."""

    async def complete(self, prompt: str) -> str: ...


@dataclass
class CorrectiveIntention:
    """A prospective memory entry — what to do differently in the future."""

    role: str
    intention: str
    source_gradient: str = ""
    confidence: float = 0.7
    created_at: datetime = field(default_factory=lambda: datetime.now(timezone.utc))
    id: str = field(default_factory=lambda: uuid4().hex)


@dataclass
class RetrospectiveMemory:
    """Stores failure patterns: what went wrong and why.

    Accumulates patterns from gradient decomposition, merging similar
    failures and tracking frequency for severity assessment.
    """

    patterns: dict[str, list[FailurePattern]] = field(default_factory=dict)

    def update(self, role: str, gradients: list) -> None:
        """Store severe failure gradients as patterns, merging duplicates."""
        from lyra_memory.optimization.memgrad import FailurePattern

        for g in gradients:
            if g.severity < 0.5:
                continue
            pattern = FailurePattern(
                role=role,
                description=g.gradient,
                severity=g.severity,
            )
            existing = self._find_similar(role, pattern)
            if existing:
                existing.record_occurrence()
            else:
                self.patterns.setdefault(role, []).append(pattern)

    def get(self, role: str, limit: int = 10) -> str:
        """Get formatted failure patterns for a role."""
        role_patterns = self.patterns.get(role, [])
        sorted_patterns = sorted(
            role_patterns,
            key=lambda p: (p.frequency * p.severity),
            reverse=True,
        )
        if not sorted_patterns:
            return ""
        lines = ["Past failure patterns:"]
        for p in sorted_patterns[:limit]:
            lines.append(
                f"- [{p.severity:.1f} severity, {p.frequency}x] {p.description}"
            )
        return "\n".join(lines)

    def get_top_patterns(self, role: str, n: int = 5) -> list[FailurePattern]:
        """Return the top-N failure patterns for a role."""
        role_patterns = self.patterns.get(role, [])
        return sorted(
            role_patterns,
            key=lambda p: (p.frequency * p.severity),
            reverse=True,
        )[:n]

    @property
    def total_patterns(self) -> int:
        return sum(len(ps) for ps in self.patterns.values())

    def clear(self) -> None:
        self.patterns.clear()

    def _find_similar(self, role: str, pattern: FailurePattern) -> FailurePattern | None:
        """Check if a similar pattern already exists via keyword overlap."""
        new_words = set(re.findall(r"\b\w+\b", pattern.description.lower()))
        existing = self.patterns.get(role, [])

        for ep in existing:
            ep_words = set(re.findall(r"\b\w+\b", ep.description.lower()))
            overlap = new_words & ep_words
            if len(overlap) >= 3:
                return ep
        return None


@dataclass
class ProspectiveMemory:
    """Stores corrective intentions: what to do differently.

    Converts failure gradients into specific action-oriented intentions
    with trigger conditions and rationales.
    """

    llm: LLMClient
    intentions: dict[str, list[CorrectiveIntention]] = field(default_factory=dict)

    async def update(self, role: str, gradients: list) -> None:
        """Convert failure gradients into corrective intentions."""
        for g in gradients:
            intention_prompt = f"""Given this failure gradient: "{g.gradient}"

Formulate a specific corrective intention in the format:
"When [trigger condition], [specific alternative action] because [rationale]."

Output the intention only."""

            intention_text = await self.llm.complete(intention_prompt)
            intention = CorrectiveIntention(
                role=role,
                intention=intention_text.strip(),
                source_gradient=g.gradient,
            )
            self.intentions.setdefault(role, []).append(intention)

    def get(self, role: str, limit: int = 5) -> str:
        """Get formatted corrective intentions for a role."""
        role_intentions = self.intentions.get(role, [])
        sorted_intentions = sorted(
            role_intentions,
            key=lambda i: i.confidence,
            reverse=True,
        )
        if not sorted_intentions:
            return ""
        lines = ["Corrective intentions:"]
        for i in sorted_intentions[:limit]:
            lines.append(f"- {i.intention}")
        return "\n".join(lines)

    @property
    def total_intentions(self) -> int:
        return sum(len(ins) for ins in self.intentions.values())

    def clear(self) -> None:
        self.intentions.clear()
