"""Multi-axis verifier composer + canonical built-in verifiers.

The composer model:

    1. Each verifier exposes a typed :class:`VerifierAxis`.
    2. The composer runs them in declared order over a typed action dict.
    3. Each verifier returns an :class:`AxisVerdict` with passed/severity/note.
    4. The composer aggregates into a :class:`CompositeVerdict` exposing
       the per-axis verdicts + an overall pass/fail/severity.

Failure modes:
    - ``fail_fast=True``: stop at the first non-passing axis (cheap path).
    - ``fail_fast=False``: run all axes (full audit; default).
    - ``blocking_severity=Severity.ERROR``: passes-vs-blocking is decided
      by the maximum-severity axis verdict.

The built-in stub verifiers are intentionally minimal — they implement the
shape correctly with deterministic rules. Production wires real verifiers
(test runner, lint engine, AWS dry-run API, etc.) through the same Protocol.
"""
from __future__ import annotations

import enum
from dataclasses import dataclass, field
from typing import Any, Optional, Protocol


class VerifierAxis(str, enum.Enum):
    """The verification axis a verifier covers."""

    DRY_RUN = "dry_run"
    DIFF = "diff"
    POLICY = "policy"
    PERMISSION = "permission"
    HITL = "hitl"
    TEST = "test"
    LINT = "lint"
    TYPE_CHECK = "type_check"
    SECURITY_SCAN = "security_scan"
    CUSTOM = "custom"


class Severity(str, enum.Enum):
    """Severity ladder; ordered from least to most severe."""

    INFO = "info"
    WARNING = "warning"
    ERROR = "error"
    CRITICAL = "critical"


_SEVERITY_ORDER = (Severity.INFO, Severity.WARNING, Severity.ERROR, Severity.CRITICAL)


def _max_severity(severities: list[Severity]) -> Severity:
    """Return the maximum severity from a list. Empty → INFO."""
    if not severities:
        return Severity.INFO
    indices = [_SEVERITY_ORDER.index(s) for s in severities]
    return _SEVERITY_ORDER[max(indices)]


@dataclass(frozen=True)
class AxisVerdict:
    """One verifier's verdict on an action."""

    axis: VerifierAxis
    passed: bool
    severity: Severity = Severity.INFO
    note: str = ""
    details: dict[str, Any] = field(default_factory=dict)


@dataclass(frozen=True)
class CompositeVerdict:
    """Aggregated verdict from running N axis verifiers."""

    axis_verdicts: tuple[AxisVerdict, ...]
    passed: bool  # all axes returned passed=True
    blocking: bool  # at least one axis returned passed=False at >= blocking_severity
    severity: Severity  # max severity across axes

    def by_axis(self, axis: VerifierAxis) -> Optional[AxisVerdict]:
        for v in self.axis_verdicts:
            if v.axis == axis:
                return v
        return None

    def failed_axes(self) -> list[VerifierAxis]:
        return [v.axis for v in self.axis_verdicts if not v.passed]


class Verifier(Protocol):
    """Single-axis verifier. Production wires real implementations here."""

    axis: VerifierAxis

    def verify(self, *, action: dict[str, Any]) -> AxisVerdict: ...


# --- Composer ------------------------------------------------------------


@dataclass
class VerifierComposer:
    """Run N verifiers; aggregate into a CompositeVerdict.

    >>> dry_run = StubDryRunVerifier(should_pass=True)
    >>> policy = StubPolicyVerifier(should_pass=True)
    >>> composer = VerifierComposer(verifiers=[dry_run, policy])
    >>> verdict = composer.verify(action={"op": "write_file", "path": "/tmp/x"})
    >>> verdict.passed
    True
    """

    verifiers: list[Verifier] = field(default_factory=list)
    fail_fast: bool = False
    blocking_severity: Severity = Severity.ERROR

    def __post_init__(self) -> None:
        # Reject duplicate axes — each axis should appear at most once.
        seen: set[VerifierAxis] = set()
        for v in self.verifiers:
            if v.axis in seen:
                raise ValueError(
                    f"duplicate verifier axis: {v.axis.value!r}; "
                    f"each axis may appear at most once"
                )
            seen.add(v.axis)

    def verify(self, *, action: dict[str, Any]) -> CompositeVerdict:
        verdicts: list[AxisVerdict] = []
        all_passed = True
        blocking = False
        for v in self.verifiers:
            axis_verdict = v.verify(action=action)
            verdicts.append(axis_verdict)
            if not axis_verdict.passed:
                all_passed = False
                if self._is_blocking_severity(axis_verdict.severity):
                    blocking = True
            if self.fail_fast and not axis_verdict.passed:
                break

        composite_severity = _max_severity([v.severity for v in verdicts])
        return CompositeVerdict(
            axis_verdicts=tuple(verdicts),
            passed=all_passed,
            blocking=blocking,
            severity=composite_severity,
        )

    def _is_blocking_severity(self, severity: Severity) -> bool:
        return _SEVERITY_ORDER.index(severity) >= _SEVERITY_ORDER.index(
            self.blocking_severity
        )


# --- Built-in stub verifiers --------------------------------------------


@dataclass
class StubDryRunVerifier:
    """Stub: simulate a dry-run check.

    Production wires AWS CLI ``--dry-run`` / kubectl ``--dry-run`` / etc.
    """

    axis: VerifierAxis = VerifierAxis.DRY_RUN
    should_pass: bool = True
    severity_on_fail: Severity = Severity.ERROR
    note: str = "dry-run stub"

    def verify(self, *, action: dict[str, Any]) -> AxisVerdict:
        if self.should_pass:
            return AxisVerdict(
                axis=self.axis,
                passed=True,
                severity=Severity.INFO,
                note=self.note,
                details={"action_op": action.get("op", "")},
            )
        return AxisVerdict(
            axis=self.axis,
            passed=False,
            severity=self.severity_on_fail,
            note=self.note,
            details={"action_op": action.get("op", "")},
        )


@dataclass
class StubDiffVerifier:
    """Stub: check that the action's projected diff is within bounds."""

    axis: VerifierAxis = VerifierAxis.DIFF
    max_lines_changed: int = 100
    severity_on_overflow: Severity = Severity.WARNING

    def verify(self, *, action: dict[str, Any]) -> AxisVerdict:
        diff_lines = int(action.get("diff_lines", 0))
        if diff_lines <= self.max_lines_changed:
            return AxisVerdict(
                axis=self.axis,
                passed=True,
                severity=Severity.INFO,
                note=f"diff {diff_lines} lines within {self.max_lines_changed} cap",
                details={"diff_lines": diff_lines},
            )
        return AxisVerdict(
            axis=self.axis,
            passed=False,
            severity=self.severity_on_overflow,
            note=f"diff {diff_lines} lines exceeds {self.max_lines_changed} cap",
            details={"diff_lines": diff_lines, "cap": self.max_lines_changed},
        )


@dataclass
class StubPolicyVerifier:
    """Stub: deny ops in a forbidden-ops set, allow otherwise."""

    axis: VerifierAxis = VerifierAxis.POLICY
    forbidden_ops: frozenset[str] = frozenset()
    severity_on_violation: Severity = Severity.CRITICAL
    should_pass: bool = True  # back-compat for tests passing should_pass directly

    def verify(self, *, action: dict[str, Any]) -> AxisVerdict:
        op = str(action.get("op", ""))
        # Either explicit forbidden_ops or override via should_pass=False.
        denied = (op in self.forbidden_ops) or (not self.should_pass)
        if denied:
            return AxisVerdict(
                axis=self.axis,
                passed=False,
                severity=self.severity_on_violation,
                note=f"policy denies op {op!r}" if op in self.forbidden_ops else "policy denies",
                details={"op": op},
            )
        return AxisVerdict(
            axis=self.axis,
            passed=True,
            severity=Severity.INFO,
            note=f"policy allows op {op!r}",
            details={"op": op},
        )


@dataclass
class StubPermissionVerifier:
    """Stub: check the agent has all required scopes for the action."""

    axis: VerifierAxis = VerifierAxis.PERMISSION
    granted_scopes: frozenset[str] = frozenset()
    severity_on_missing: Severity = Severity.ERROR

    def verify(self, *, action: dict[str, Any]) -> AxisVerdict:
        required = frozenset(action.get("required_scopes", ()))
        missing = required - self.granted_scopes
        if not missing:
            return AxisVerdict(
                axis=self.axis,
                passed=True,
                severity=Severity.INFO,
                note=f"all {len(required)} required scopes granted",
                details={"required": sorted(required)},
            )
        return AxisVerdict(
            axis=self.axis,
            passed=False,
            severity=self.severity_on_missing,
            note=f"missing scopes: {sorted(missing)}",
            details={"missing": sorted(missing), "required": sorted(required)},
        )


@dataclass
class HITLVerifier:
    """Human-in-the-loop verifier — escalates high-severity actions to a human.

    Default policy: actions with ``severity >= require_review_above`` need a
    review approval token in ``action["hitl_approval"]``. Without it,
    returns ``passed=False`` with ``Severity.WARNING`` (NEEDS_REVIEW).
    """

    axis: VerifierAxis = VerifierAxis.HITL
    require_review_above: Severity = Severity.WARNING
    needs_review_severity: Severity = Severity.WARNING

    def verify(self, *, action: dict[str, Any]) -> AxisVerdict:
        action_severity_str = str(action.get("severity", "info"))
        try:
            action_severity = Severity(action_severity_str)
        except ValueError:
            action_severity = Severity.INFO
        approval = action.get("hitl_approval")

        # Below the threshold → HITL not required, auto-pass.
        if _SEVERITY_ORDER.index(action_severity) < _SEVERITY_ORDER.index(
            self.require_review_above
        ):
            return AxisVerdict(
                axis=self.axis,
                passed=True,
                severity=Severity.INFO,
                note="below HITL threshold; auto-approved",
                details={"action_severity": action_severity.value},
            )

        # At or above threshold → approval required.
        if approval:
            return AxisVerdict(
                axis=self.axis,
                passed=True,
                severity=Severity.INFO,
                note=f"HITL approved by {approval}",
                details={"approval_token": approval},
            )
        return AxisVerdict(
            axis=self.axis,
            passed=False,
            severity=self.needs_review_severity,
            note="HITL approval required; no approval token in action",
            details={"action_severity": action_severity.value},
        )


__all__ = [
    "AxisVerdict",
    "CompositeVerdict",
    "HITLVerifier",
    "Severity",
    "StubDiffVerifier",
    "StubDryRunVerifier",
    "StubPermissionVerifier",
    "StubPolicyVerifier",
    "Verifier",
    "VerifierAxis",
    "VerifierComposer",
]
