"""TDD phase state machine.

The agent loop moves through six phases:

    IDLE → PLAN → RED → GREEN → REFACTOR → SHIP

In **strict mode** each transition requires a typed evidence
artefact (e.g. a ``PlanArtifact`` with at least one step, a
``RedFailureArtifact`` pinned to a file + test name, and so on).
In **lenient mode** the machine records a warning and advances
anyway — useful for exploratory sessions where the user is
deliberately skipping a step.

Two surface APIs are exposed side-by-side:

* :meth:`TDDStateMachine.advance` — evidence-driven, strict-by-default.
  This is what the Wave-F loop integrations call.
* :meth:`TDDStateMachine.transition` — reason-driven, lightweight,
  used by the REPL's ``/phase`` command and by older integrations.

The whole module is pure stdlib + dataclasses; no HIR coupling,
no slash-command coupling. The REPL-side ``/phase`` command is a
thin wrapper that delegates to :class:`TDDStateMachine`.
"""
from __future__ import annotations

from dataclasses import dataclass, field
from enum import Enum
from typing import Any


__all__ = [
    "GreenPassArtifact",
    "IllegalTDDTransition",
    "PlanArtifact",
    "RedFailureArtifact",
    "RefactorArtifact",
    "ShipArtifact",
    "HistoryEntry",
    "TDDPhase",
    "TDDState",
    "TDDStateMachine",
    "TransitionError",
]


class TDDPhase(Enum):
    """Phases the agent-loop state machine can be in."""

    IDLE = "idle"
    PLAN = "plan"
    RED = "red"
    GREEN = "green"
    REFACTOR = "refactor"
    SHIP = "ship"


TDDState = TDDPhase


class TransitionError(RuntimeError):
    """Raised when a strict-mode transition lacks the required evidence
    or attempts an illegal phase jump."""


IllegalTDDTransition = TransitionError


# ---- history entry -------------------------------------------------
#
# Tuple-subclass so existing tuple-unpacking tests (``for src, dst in
# sm.history``) and attribute-access tests (``h.to_state``,
# ``h.reason``) both work. We keep the tuple payload at length 2 so
# equality against ``(src, dst)`` tuples still holds.


class HistoryEntry(tuple):
    """Two-tuple ``(from_state, to_state)`` with a trailing ``reason`` attr.

    Supports both:
        src, dst = entry                 # tuple unpacking
        entry.from_state, entry.to_state # attribute access
        entry.reason                     # transition justification
        entry == (from, to)              # plain tuple equality
    """

    def __new__(
        cls,
        from_state: "TDDPhase",
        to_state: "TDDPhase",
        reason: str = "",
    ) -> "HistoryEntry":
        instance = super().__new__(cls, (from_state, to_state))
        instance._reason = reason
        return instance

    @property
    def from_state(self) -> "TDDPhase":
        return self[0]

    @property
    def to_state(self) -> "TDDPhase":
        return self[1]

    @property
    def reason(self) -> str:
        return getattr(self, "_reason", "")


# ---- evidence artefacts --------------------------------------------
#
# Each artefact is the smallest non-trivial proof the loop owes the
# state machine. Keeping them dataclasses (rather than free-form
# dicts) lets the machine enforce shape without re-parsing JSON on
# every transition.


@dataclass(frozen=True)
class PlanArtifact:
    """Evidence for ``IDLE → PLAN``."""

    steps: tuple[str, ...]

    def validate(self) -> None:
        if len(self.steps) < 1:
            raise TransitionError(
                "PLAN requires at least 1 step; got an empty plan"
            )


@dataclass(frozen=True)
class RedFailureArtifact:
    """Evidence for ``PLAN → RED`` — a failing test on disk."""

    test_file: str
    test_name: str
    failure_message: str

    def validate(self) -> None:
        if not self.test_file.strip():
            raise TransitionError("RED requires a non-empty test_file")
        if not self.test_name.strip():
            raise TransitionError("RED requires a non-empty test_name")
        if not self.failure_message.strip():
            raise TransitionError(
                "RED requires a non-empty failure_message (run the test!)"
            )


@dataclass(frozen=True)
class GreenPassArtifact:
    """Evidence for ``RED → GREEN`` — the previously-RED test passes."""

    test_file: str
    test_name: str
    all_tests_passed: bool

    def validate(self) -> None:
        if not self.all_tests_passed:
            raise TransitionError(
                "GREEN requires all tests to pass (got all_tests_passed=False)"
            )


@dataclass(frozen=True)
class RefactorArtifact:
    """Evidence for ``GREEN → REFACTOR`` — diff applied, tests stay green."""

    diff_summary: str
    tests_still_green: bool

    def validate(self) -> None:
        if not self.diff_summary.strip():
            raise TransitionError("REFACTOR requires a non-empty diff_summary")
        if not self.tests_still_green:
            raise TransitionError(
                "REFACTOR rejected: tests_still_green is False "
                "— revert or fix before advancing"
            )


@dataclass(frozen=True)
class ShipArtifact:
    """Evidence for ``REFACTOR → SHIP`` — packaged change ready to merge."""

    commit_sha: str | None = None
    pr_url: str | None = None
    summary: str = ""

    def validate(self) -> None:
        if not (self.commit_sha or self.pr_url or self.summary.strip()):
            raise TransitionError(
                "SHIP requires at least one of commit_sha / pr_url / summary"
            )


# ---- state machine -------------------------------------------------


_LEGAL_TRANSITIONS: dict[TDDPhase, tuple[TDDPhase, ...]] = {
    TDDPhase.IDLE:     (TDDPhase.PLAN,),
    TDDPhase.PLAN:     (TDDPhase.RED, TDDPhase.IDLE),
    TDDPhase.RED:      (TDDPhase.GREEN, TDDPhase.PLAN),
    TDDPhase.GREEN:    (TDDPhase.REFACTOR, TDDPhase.RED),
    TDDPhase.REFACTOR: (TDDPhase.SHIP, TDDPhase.RED),
    TDDPhase.SHIP:     (TDDPhase.IDLE,),
}


_EVIDENCE_FOR_ENTERING: dict[TDDPhase, type[Any] | None] = {
    TDDPhase.IDLE:     None,
    TDDPhase.PLAN:     PlanArtifact,
    TDDPhase.RED:      RedFailureArtifact,
    TDDPhase.GREEN:    GreenPassArtifact,
    TDDPhase.REFACTOR: RefactorArtifact,
    TDDPhase.SHIP:     ShipArtifact,
}


_IN_TDD = frozenset(
    {TDDPhase.PLAN, TDDPhase.RED, TDDPhase.GREEN, TDDPhase.REFACTOR}
)


class TDDStateMachine:
    """Strict/lenient finite state machine for the TDD loop.

    ``strict=True`` — illegal transitions and missing evidence raise
    :class:`TransitionError`. This is the production default.

    ``strict=False`` — the machine still records warnings but
    advances anyway so scripted sessions don't hard-fail mid-run.

    ``initial`` — starting phase for the machine (defaults to ``IDLE``).
    Used by the v0 ``/phase`` path and by tests that want to exercise
    a specific illegal transition without first walking the happy path.
    """

    def __init__(
        self,
        *,
        strict: bool = True,
        initial: TDDPhase = TDDPhase.IDLE,
    ) -> None:
        self.strict = strict
        self._phase: TDDPhase = initial
        self.history: list[HistoryEntry] = []
        self.warnings: list[str] = []
        self.evidence_ledger: list[Any] = []

    # ---- read-only API ------------------------------------------

    @property
    def phase(self) -> TDDPhase:
        return self._phase

    # v0 compatibility: the older REPL code path uses ``state``.
    @property
    def state(self) -> TDDPhase:
        return self._phase

    def legal_next(self) -> tuple[TDDPhase, ...]:
        return _LEGAL_TRANSITIONS[self._phase]

    def is_legal(self, target: TDDPhase) -> bool:
        return target in _LEGAL_TRANSITIONS[self._phase]

    def in_tdd_phase(self) -> bool:
        """Quick predicate hooks use to gate TDD-only behaviours."""
        return self._phase in _IN_TDD

    # ---- evidence-driven transition (Wave-F) -------------------

    def advance(
        self,
        target: TDDPhase,
        *,
        evidence: Any | None = None,
        reason: str = "",
    ) -> TDDPhase:
        """Move to *target*. Raises :class:`TransitionError` in strict mode."""
        if not self.is_legal(target):
            msg = (
                f"illegal transition {self._phase.value} → {target.value}; "
                f"legal next: {[p.value for p in self.legal_next()]}"
            )
            if self.strict:
                raise TransitionError(msg)
            self.warnings.append(msg)

        expected_type = _EVIDENCE_FOR_ENTERING[target]
        if expected_type is not None:
            if evidence is None:
                msg = (
                    f"transition {self._phase.value} → {target.value} "
                    f"requires evidence of type {expected_type.__name__}"
                )
                if self.strict:
                    raise TransitionError(msg)
                self.warnings.append(msg)
            elif not isinstance(evidence, expected_type):
                msg = (
                    f"wrong evidence type for {target.value}: "
                    f"expected {expected_type.__name__}, "
                    f"got {type(evidence).__name__}"
                )
                if self.strict:
                    raise TransitionError(msg)
                self.warnings.append(msg)
            else:
                try:
                    evidence.validate()
                except TransitionError:
                    if self.strict:
                        raise
                    self.warnings.append(
                        f"weak evidence accepted in lenient mode for {target.value}"
                    )
                self.evidence_ledger.append(evidence)

        from_phase = self._phase
        self.history.append(HistoryEntry(from_phase, target, reason))
        self._phase = target
        return self._phase

    # ---- reason-driven transition (v0 /phase) ------------------

    def transition(self, target: TDDPhase, *, reason: str) -> TDDPhase:
        """Lightweight reason-driven transition.

        Unlike :meth:`advance`, this path does not require evidence
        artefacts — it's the surface the ``/phase`` slash command and
        older tests exercise. Strict-mode legality is still enforced.
        ``reason`` is mandatory and must be non-empty.
        """
        if not reason:
            raise ValueError("transition requires a non-empty reason")
        if not self.is_legal(target):
            msg = (
                f"illegal transition {self._phase.value} → {target.value}; "
                f"legal next: {[p.value for p in self.legal_next()]}"
            )
            if self.strict:
                raise IllegalTDDTransition(msg)
            self.warnings.append(msg)

        from_phase = self._phase
        self.history.append(HistoryEntry(from_phase, target, reason))
        self._phase = target
        return self._phase

    def reset(self, *, reason: str = "") -> None:
        """Return the machine to ``IDLE`` without wiping history."""
        self.history.append(HistoryEntry(self._phase, TDDPhase.IDLE, reason))
        self._phase = TDDPhase.IDLE
