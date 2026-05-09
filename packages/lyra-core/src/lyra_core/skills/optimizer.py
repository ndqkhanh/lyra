"""Trigger-description auto-optimizer.

When a skill is mis-triggered (matches a query the user rejects)
or missed (user explicitly wanted it and the router synthesised
instead), the optimizer mutates the skill's trigger set:

* **miss** ⇒ add the user's phrasing as a new trigger.
* **false-positive** ⇒ narrow the overly-broad trigger to the
  part that actually applied.

The optimizer is rule-based (no LLM needed). Swap in a smarter
learner later — the interface is stable.
"""
from __future__ import annotations

from dataclasses import dataclass, field
from typing import Iterable

from .registry import Skill, SkillRegistry


__all__ = [
    "OptimizationReport",
    "TriggerOptimizer",
]


_STOP_WORDS = frozenset(
    {
        "the", "a", "an", "for", "of", "and", "to", "in", "on",
        "at", "is", "are", "was", "were", "my", "your", "our",
        "this", "that", "these", "those", "i", "you", "we",
    }
)


@dataclass(frozen=True)
class OptimizationReport:
    skill_id: str
    added_triggers: tuple[str, ...]
    removed_triggers: tuple[str, ...]

    def to_dict(self) -> dict[str, object]:
        return {
            "skill_id": self.skill_id,
            "added_triggers": list(self.added_triggers),
            "removed_triggers": list(self.removed_triggers),
        }


def _keywords(phrase: str) -> list[str]:
    return [w for w in phrase.lower().split() if w not in _STOP_WORDS]


def _normalise(phrase: str) -> str:
    return " ".join(_keywords(phrase))


@dataclass
class TriggerOptimizer:
    """Mutate skill triggers based on user feedback."""

    registry: SkillRegistry
    min_trigger_words: int = 2

    # ---- individual moves ---------------------------------------

    def on_miss(self, *, skill_id: str, user_query: str) -> OptimizationReport:
        """User wanted *skill_id* but the router didn't pick it.

        We add a normalised version of ``user_query`` as a new
        trigger so next time the same phrasing routes cleanly. We
        skip if the candidate's token set either duplicates, is a
        subset of, or is a superset of any existing trigger's
        token set — otherwise the registry bloats with near-
        duplicates that destabilise the router.
        """
        skill = self.registry.get(skill_id)
        normalised = _normalise(user_query).strip()
        candidate_tokens = set(normalised.split())
        added: list[str] = []
        should_add = (
            bool(normalised)
            and len(normalised.split()) >= self.min_trigger_words
        )
        if should_add:
            for trigger in skill.triggers:
                existing_tokens = set(_keywords(trigger))
                if not existing_tokens:
                    continue
                if (
                    candidate_tokens == existing_tokens
                    or candidate_tokens.issubset(existing_tokens)
                    or existing_tokens.issubset(candidate_tokens)
                ):
                    should_add = False
                    break
        if should_add:
            new_triggers = tuple(list(skill.triggers) + [normalised])
            self.registry.update(
                Skill(
                    id=skill.id,
                    description=skill.description,
                    triggers=new_triggers,
                    success_count=skill.success_count,
                    miss_count=skill.miss_count + 1,
                    synthesised=skill.synthesised,
                )
            )
            added.append(normalised)
        else:
            self.registry.record_miss(skill_id)
        return OptimizationReport(
            skill_id=skill_id,
            added_triggers=tuple(added),
            removed_triggers=(),
        )

    def on_false_positive(
        self,
        *,
        skill_id: str,
        misfiring_query: str,
    ) -> OptimizationReport:
        """Router picked *skill_id* but user rejected it.

        We remove any trigger that the misfiring query matched on,
        as long as doing so doesn't empty the trigger set.
        """
        skill = self.registry.get(skill_id)
        query_tokens = set(_keywords(misfiring_query))
        removed: list[str] = []
        kept: list[str] = []
        for trigger in skill.triggers:
            trigger_tokens = set(_keywords(trigger))
            if trigger_tokens and trigger_tokens.issubset(query_tokens):
                removed.append(trigger)
            else:
                kept.append(trigger)

        # Never fully delete — always leave at least the most
        # specific remaining trigger so the skill is still
        # reachable.
        if not kept:
            kept = list(skill.triggers[:1])
            removed = []

        self.registry.update(
            Skill(
                id=skill.id,
                description=skill.description,
                triggers=tuple(kept),
                success_count=skill.success_count,
                miss_count=skill.miss_count + 1,
                synthesised=skill.synthesised,
            )
        )
        return OptimizationReport(
            skill_id=skill_id,
            added_triggers=(),
            removed_triggers=tuple(removed),
        )
