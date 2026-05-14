"""Voyager skill accumulation — Phase E of the Lyra 322-326 evolution plan.

New skills are proposed as code strings, run through a sandbox test gate,
then stored in the verified skill library only if the verifier approves.
This matches the Voyager paper's propose → execute → verify → store loop.

Grounded in:
- arXiv:2305.16291 — Voyager: An Open-Ended Embodied Agent with LLMs
- Doc 326 §5.2 — Skill accumulation gate
"""
from __future__ import annotations

from dataclasses import dataclass, field
from typing import Optional, Protocol


__all__ = [
    "SkillCandidate",
    "SkillVerifier",
    "SkillLibrary",
    "VoyagerAccumulator",
]


@dataclass
class SkillCandidate:
    """A proposed skill before it passes the verification gate."""

    name: str
    code: str
    description: str = ""
    tags: list[str] = field(default_factory=list)


class SkillVerifier(Protocol):
    """Runs a candidate skill in a sandbox and returns (passed, feedback)."""

    def verify(self, candidate: SkillCandidate) -> tuple[bool, str]: ...


class SkillLibrary:
    """Append-only store of verified skills, keyed by name."""

    def __init__(self) -> None:
        self._skills: dict[str, SkillCandidate] = {}

    def add(self, skill: SkillCandidate) -> None:
        self._skills[skill.name] = skill

    def get(self, name: str) -> Optional[SkillCandidate]:
        return self._skills.get(name)

    def list(self) -> list[SkillCandidate]:
        return list(self._skills.values())

    @property
    def size(self) -> int:
        return len(self._skills)


class VoyagerAccumulator:
    """Orchestrates the propose → verify → store loop.

    Usage::

        library = SkillLibrary()
        accumulator = VoyagerAccumulator(library, verifier)
        passed, feedback = accumulator.submit(candidate)
    """

    def __init__(self, library: SkillLibrary, verifier: SkillVerifier) -> None:
        self._library = library
        self._verifier = verifier
        self.attempts: int = 0
        self.accepted: int = 0
        self.rejected: int = 0

    def submit(self, candidate: SkillCandidate) -> tuple[bool, str]:
        """Run the verification gate. Store and return True on success."""
        self.attempts += 1
        passed, feedback = self._verifier.verify(candidate)
        if passed:
            self._library.add(candidate)
            self.accepted += 1
        else:
            self.rejected += 1
        return passed, feedback

    @property
    def acceptance_rate(self) -> float:
        if self.attempts == 0:
            return 0.0
        return self.accepted / self.attempts
