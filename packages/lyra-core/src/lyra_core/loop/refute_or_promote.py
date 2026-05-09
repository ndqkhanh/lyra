"""Refute-or-Promote adversarial stage (SWE-TRACE shape).

After the main loop proposes a solution, a sub-agent takes the
opposite side: it tries to refute the solution with a concrete
counter-example or counter-argument. If the refute succeeds the
solution loops back to PLAN. If ``max_attempts`` refute passes
fail to land a blow the solution is promoted.

Why codify this as a dataclass/callable split rather than a
single function? Two reasons:

1. The adversary is a regular ``AdversaryCallable`` — easy to mock
   in tests, swap in production, or wire to a different model
   generation than the main loop.
2. The stage owns the loop's bookkeeping (attempts, history of
   passes, effort budget) so the caller can inspect why a verdict
   was reached rather than just receiving a boolean.
"""
from __future__ import annotations

from dataclasses import dataclass, field
from typing import Callable, Protocol


__all__ = [
    "AdversaryCallable",
    "RefuteError",
    "RefuteOrPromoteResult",
    "RefutePass",
    "RefutePromoteStage",
    "refute_or_promote",
]


class RefuteError(RuntimeError):
    """Raised when the adversary misbehaves (e.g. returns a non-dict)."""


class AdversaryCallable(Protocol):
    """An adversary takes the proposed solution + prior passes and
    either returns a refute, or admits defeat."""

    def __call__(
        self,
        *,
        solution: str,
        attempt: int,
        history: tuple["RefutePass", ...],
    ) -> "RefutePass": ...


@dataclass(frozen=True)
class RefutePass:
    """One adversarial attempt."""

    attempt: int
    refuted: bool
    counter_example: str = ""
    argument: str = ""

    def to_dict(self) -> dict[str, object]:
        return {
            "attempt": self.attempt,
            "refuted": self.refuted,
            "counter_example": self.counter_example,
            "argument": self.argument,
        }


@dataclass(frozen=True)
class RefuteOrPromoteResult:
    """Aggregate outcome."""

    promoted: bool
    passes: tuple[RefutePass, ...]
    verdict: str           # ``"promoted"`` or ``"refuted"``
    winning_pass: RefutePass | None = None

    def to_dict(self) -> dict[str, object]:
        return {
            "promoted": self.promoted,
            "verdict": self.verdict,
            "attempts": len(self.passes),
            "passes": [p.to_dict() for p in self.passes],
            "winning_pass": (
                self.winning_pass.to_dict() if self.winning_pass else None
            ),
        }


@dataclass
class RefutePromoteStage:
    """Re-usable stage with configurable cap + adversary."""

    adversary: AdversaryCallable
    max_attempts: int = 3

    def run(self, *, solution: str) -> RefuteOrPromoteResult:
        if self.max_attempts < 1:
            raise RefuteError("max_attempts must be >= 1")
        history: list[RefutePass] = []
        for attempt in range(1, self.max_attempts + 1):
            rp = self.adversary(
                solution=solution,
                attempt=attempt,
                history=tuple(history),
            )
            if not isinstance(rp, RefutePass):
                raise RefuteError(
                    f"adversary returned {type(rp).__name__}, expected RefutePass"
                )
            if rp.attempt != attempt:
                raise RefuteError(
                    f"adversary produced attempt={rp.attempt}, expected {attempt}"
                )
            history.append(rp)
            if rp.refuted:
                return RefuteOrPromoteResult(
                    promoted=False,
                    passes=tuple(history),
                    verdict="refuted",
                    winning_pass=rp,
                )
        return RefuteOrPromoteResult(
            promoted=True,
            passes=tuple(history),
            verdict="promoted",
            winning_pass=None,
        )


def refute_or_promote(
    *,
    solution: str,
    adversary: AdversaryCallable,
    max_attempts: int = 3,
) -> RefuteOrPromoteResult:
    """Convenience wrapper so simple callers don't instantiate the stage."""
    stage = RefutePromoteStage(adversary=adversary, max_attempts=max_attempts)
    return stage.run(solution=solution)
