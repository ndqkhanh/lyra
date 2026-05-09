"""In-session skill synthesizer.

When the router returns :data:`RouterDecision.SYNTHESISE`, the
synthesiser:

1. Drafts a :class:`Skill` from the user query, a description,
   and (optionally) the LLM's proposed trigger phrases.
2. Registers it with ``synthesised=True`` so downstream telemetry
   can distinguish hand-authored skills from loop-minted ones.
3. Returns the new :class:`Skill` + a :class:`SynthesisReport`.

The synthesiser never calls a model directly — the caller passes
in ``draft_triggers`` (e.g. from the agent-loop's sub-model that
just generated them). Keeping I/O at the edges lets us test the
whole thing without stubbing a provider.
"""
from __future__ import annotations

import re
from dataclasses import dataclass
from typing import Sequence

from .registry import Skill, SkillRegistry


__all__ = [
    "SynthesisError",
    "SynthesisReport",
    "SkillSynthesizer",
]


_ID_RE = re.compile(r"[^a-z0-9]+")


class SynthesisError(RuntimeError):
    pass


def _slugify(query: str) -> str:
    slug = _ID_RE.sub("-", query.lower()).strip("-")
    return slug[:48] or "skill"


@dataclass(frozen=True)
class SynthesisReport:
    skill: Skill
    collision_resolved_with_suffix: int = 0

    def to_dict(self) -> dict[str, object]:
        return {
            "skill_id": self.skill.id,
            "triggers": list(self.skill.triggers),
            "synthesised": self.skill.synthesised,
            "collision_resolved_with_suffix": self.collision_resolved_with_suffix,
        }


@dataclass
class SkillSynthesizer:
    registry: SkillRegistry

    def synthesise(
        self,
        *,
        user_query: str,
        description: str,
        draft_triggers: Sequence[str] | None = None,
    ) -> SynthesisReport:
        triggers: list[str] = []
        if draft_triggers:
            for t in draft_triggers:
                if t and t not in triggers:
                    triggers.append(t)
        if not triggers:
            triggers.append(user_query.lower().strip())
        if not all(t.strip() for t in triggers):
            raise SynthesisError("synthesiser received empty trigger(s)")
        if not description.strip():
            raise SynthesisError("synthesiser requires a non-empty description")

        base_id = _slugify(user_query) or "skill"
        skill_id = base_id
        suffix = 0
        while skill_id in self.registry:
            suffix += 1
            skill_id = f"{base_id}-{suffix}"

        skill = Skill(
            id=skill_id,
            description=description.strip(),
            triggers=tuple(triggers),
            synthesised=True,
        )
        self.registry.register(skill)
        return SynthesisReport(
            skill=skill,
            collision_resolved_with_suffix=suffix,
        )
