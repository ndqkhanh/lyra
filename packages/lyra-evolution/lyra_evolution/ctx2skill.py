"""Ctx2Skill — context-to-skill extraction — Phase H of the Lyra curation plan.

Transforms execution traces into reusable skill drafts.  Each successful
novel task completion becomes a candidate for the skill library instead of
being discarded at session end.  A Cross-Time Replay check validates that
the extracted skill generalises across at least two distinct contexts before
library admission.

Grounded in:
- arXiv:2604.27660 — From Context to Skills (Ctx2Skill)
- 5-agent adversarial loop: Challenger → Reasoner → Judge → Proposer → Generator
"""
from __future__ import annotations

from dataclasses import dataclass, field
from typing import Optional


__all__ = [
    "TraceRecord",
    "SkillDraft",
    "ExtractionResult",
    "Ctx2SkillExtractor",
    "CrossTimeReplayValidator",
]


@dataclass
class TraceRecord:
    """One execution trace — a sequence of steps with an outcome."""

    trace_id: str
    task_description: str
    steps: list[str] = field(default_factory=list)
    tools_used: list[str] = field(default_factory=list)
    outcome: str = "unknown"    # "success" | "failure" | "unknown"
    context_tag: str = ""       # domain/environment label for cross-time replay

    @property
    def succeeded(self) -> bool:
        return self.outcome.lower() == "success"


@dataclass
class SkillDraft:
    """A candidate skill extracted from one or more traces."""

    name: str
    description: str
    instructions: list[str] = field(default_factory=list)
    triggers: list[str] = field(default_factory=list)
    tools_required: list[str] = field(default_factory=list)
    source_traces: list[str] = field(default_factory=list)  # trace IDs
    generalisation_score: float = 0.0   # 0 = single context; 1 = fully general

    def to_skill_md(self) -> str:
        lines = [
            f"# {self.name}",
            "",
            self.description,
            "",
            "## Instructions",
        ]
        for i, step in enumerate(self.instructions, 1):
            lines.append(f"{i}. {step}")
        if self.triggers:
            lines.extend(["", "## When to use", *[f"- {t}" for t in self.triggers]])
        return "\n".join(lines)


@dataclass(frozen=True)
class ExtractionResult:
    """Outcome of one Ctx2Skill extraction attempt."""

    draft: Optional[SkillDraft]
    accepted: bool
    reason: str


class Ctx2SkillExtractor:
    """Extracts SkillDrafts from execution traces.

    In production, the Challenger/Reasoner/Judge/Proposer/Generator agents
    would be LLM-backed.  This implementation provides the deterministic
    structural layer that those agents plug into — the protocol, not the
    intelligence.

    Usage::

        extractor = Ctx2SkillExtractor()
        draft = extractor.extract(trace)
        result = extractor.try_admit(draft, validator)
    """

    def __init__(self, min_steps: int = 2) -> None:
        self._min_steps = min_steps
        self._pending: list[SkillDraft] = []

    def extract(self, trace: TraceRecord) -> Optional[SkillDraft]:
        """Heuristically extract a SkillDraft from a successful trace."""
        if not trace.succeeded:
            return None
        if len(trace.steps) < self._min_steps:
            return None

        name = self._derive_name(trace.task_description)
        triggers = self._derive_triggers(trace.task_description)
        draft = SkillDraft(
            name=name,
            description=trace.task_description[:200],
            instructions=list(trace.steps),
            triggers=triggers,
            tools_required=list(set(trace.tools_used)),
            source_traces=[trace.trace_id],
        )
        self._pending.append(draft)
        return draft

    def try_admit(
        self,
        draft: SkillDraft,
        validator: "CrossTimeReplayValidator",
    ) -> ExtractionResult:
        """Run Cross-Time Replay validation; return accepted/rejected result."""
        passed, reason = validator.validate(draft)
        if passed:
            return ExtractionResult(draft=draft, accepted=True, reason=reason)
        return ExtractionResult(draft=None, accepted=False, reason=reason)

    @staticmethod
    def _derive_name(description: str) -> str:
        words = description.lower().split()[:5]
        return "-".join(w for w in words if len(w) > 2)[:40] or "extracted-skill"

    @staticmethod
    def _derive_triggers(description: str) -> list[str]:
        triggers = []
        for kw in ("when", "if", "to", "for"):
            if kw in description.lower():
                idx = description.lower().index(kw)
                fragment = description[idx:idx + 60].split(".")[0]
                if len(fragment) > 5:
                    triggers.append(fragment.strip())
                    break
        return triggers or [description[:50]]


class CrossTimeReplayValidator:
    """Validates that a SkillDraft generalises across multiple context tags.

    Maintains a registry of context tags in which a candidate has been
    observed to succeed.  A draft passes when it has been confirmed in at
    least *min_contexts* distinct contexts.
    """

    def __init__(self, min_contexts: int = 2) -> None:
        self._min_contexts = min_contexts
        self._context_registry: dict[str, set[str]] = {}   # draft name → contexts

    def record_success(self, draft_name: str, context_tag: str) -> None:
        self._context_registry.setdefault(draft_name, set()).add(context_tag)

    def validate(self, draft: SkillDraft) -> tuple[bool, str]:
        contexts = self._context_registry.get(draft.name, set())
        if len(contexts) >= self._min_contexts:
            return True, f"validated across {len(contexts)} contexts: {sorted(contexts)}"
        needed = self._min_contexts - len(contexts)
        return False, f"only {len(contexts)} context(s); need {needed} more for cross-time replay"

    def context_count(self, draft_name: str) -> int:
        return len(self._context_registry.get(draft_name, set()))
