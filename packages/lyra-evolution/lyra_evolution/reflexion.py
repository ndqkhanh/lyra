"""Trace-grounded Reflexion — Phase E of the Lyra 322-326 evolution plan.

Lessons must cite an actual AER span (aer_span_id) rather than
unconstrained self-talk.  This grounding requirement prevents hallucinated
retrospectives and makes lessons auditable via the AER store.

Grounded in:
- arXiv:2303.11366 — Reflexion: Language Agents with Verbal Reinforcement
- Doc 326 §5.3 — Trace-grounded lesson generation
"""
from __future__ import annotations

import time
from dataclasses import dataclass, field


__all__ = [
    "ReflexionLesson",
    "ReflexionEngine",
]


@dataclass
class ReflexionLesson:
    """One grounded lesson produced by Reflexion.

    ``aer_span_id`` is mandatory — lessons without a span reference are
    rejected by ReflexionEngine to prevent ungrounded self-talk.
    """

    aer_span_id: str               # must be non-empty; links to AERStore record
    session_id: str
    turn_index: int
    lesson: str
    improvement_actions: list[str] = field(default_factory=list)
    ts: float = field(default_factory=time.time)

    def __post_init__(self) -> None:
        if not self.aer_span_id:
            raise ValueError("aer_span_id must not be empty — lessons must cite a trace span")
        if not self.lesson.strip():
            raise ValueError("lesson text must not be empty")


class ReflexionEngine:
    """Stores and retrieves trace-grounded Reflexion lessons.

    Usage::

        engine = ReflexionEngine()
        lesson = ReflexionLesson(
            aer_span_id="span-42",
            session_id="sess-1",
            turn_index=5,
            lesson="Tool X always fails on empty input; guard with is_empty check.",
            improvement_actions=["add is_empty guard before calling X"],
        )
        engine.record(lesson)
        past = engine.lessons_for_session("sess-1")
    """

    def __init__(self) -> None:
        self._lessons: list[ReflexionLesson] = []

    def record(self, lesson: ReflexionLesson) -> None:
        self._lessons.append(lesson)

    def lessons_for_session(self, session_id: str) -> list[ReflexionLesson]:
        return [l for l in self._lessons if l.session_id == session_id]

    def lessons_for_span(self, aer_span_id: str) -> list[ReflexionLesson]:
        return [l for l in self._lessons if l.aer_span_id == aer_span_id]

    def all_improvement_actions(self, session_id: str) -> list[str]:
        actions: list[str] = []
        for lesson in self.lessons_for_session(session_id):
            actions.extend(lesson.improvement_actions)
        return actions

    @property
    def total_lessons(self) -> int:
        return len(self._lessons)
