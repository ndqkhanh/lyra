"""Loop-layer extensions (refute-or-promote, auto-review, reflexion)."""
from __future__ import annotations

from .reflexion import (
    LessonGenerator,
    Reflection,
    ReflectionMemory,
    inject_reflections,
    make_reflection,
    naive_lesson,
)
from .refute_or_promote import (
    RefuteError,
    RefuteOrPromoteResult,
    RefutePass,
    RefutePromoteStage,
    refute_or_promote,
)

__all__ = [
    "LessonGenerator",
    "Reflection",
    "ReflectionMemory",
    "RefuteError",
    "RefuteOrPromoteResult",
    "RefutePass",
    "RefutePromoteStage",
    "inject_reflections",
    "make_reflection",
    "naive_lesson",
    "refute_or_promote",
]
