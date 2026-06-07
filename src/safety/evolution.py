"""
Self-evolving guardrails for Lyra (P8).

Provides a gated promotion system for safety rules, a fixed evaluation set
to prevent drift, and a human approval gate for safe rule evolution.

Classes
-------
RuleMode:
    Enum: SHADOW, ACTIVE, DISABLED -- lifecycle of a safety rule.
SafetyRule:
    Immutable dataclass describing a single safety rule with promotion state.
RuleEvaluation:
    Result of evaluating a rule against a tool call.
EvalCase:
    A test case for the FrozenEvaluator.
HumanApprovalGate:
    Requires human approval before any evolved rule becomes default.
FrozenEvaluator:
    Fixed evaluation set that never changes (prevents drift).
EvolutionGuard:
    Manages rules through their lifecycle (shadow -> active -> disabled).
"""

from __future__ import annotations

import logging
from dataclasses import dataclass, field
from enum import Enum
from typing import Any, Callable, Dict, List, Optional, Tuple

from src.safety.policy import GateDecision

logger = logging.getLogger(__name__)

# ---------------------------------------------------------------------------
# Type aliases
# ---------------------------------------------------------------------------

RuleEvaluator = Callable[[Dict[str, Any], Dict[str, Any]], bool]
"""Signature for a rule evaluator function.

Takes ``(tool_call, context)`` and returns ``True`` when the rule
has triggered (i.e. detected a condition it was designed to detect).
"""


# ===========================================================================
# RuleMode
# ===========================================================================


class RuleMode(str, Enum):
    """Lifecycle mode for a safety rule.

    SHADOW:
        Rule is evaluated but only logs -- never enforces.  This is the
        default starting mode for all new rules.
    ACTIVE:
        Rule is enforced -- its detection triggers gating decisions.
    DISABLED:
        Rule is skipped entirely during evaluation.
    """

    SHADOW = "shadow"
    ACTIVE = "active"
    DISABLED = "disabled"


# ===========================================================================
# SafetyRule
# ===========================================================================


@dataclass(frozen=True)
class SafetyRule:
    """An immutable safety rule with gated promotion state.

    Attributes:
        name: Unique identifier for this rule.
        description: Human-readable description.
        rule_fn: Evaluator function ``(tool_call, context) -> triggered``.
        mode: Current lifecycle mode (SHADOW / ACTIVE / DISABLED).
        detection_count: Number of times this rule has triggered.
        false_positive_count: Number of confirmed false positives.
        promotion_threshold: Minimum detections *without* FPs needed for
            promotion (N).  Default 5.
        demotion_threshold: False positives before demotion (M).  Default 3.
    """

    name: str
    description: str
    rule_fn: RuleEvaluator
    mode: RuleMode = RuleMode.SHADOW
    detection_count: int = 0
    false_positive_count: int = 0
    promotion_threshold: int = 5
    demotion_threshold: int = 3

    # -- computed properties ------------------------------------------------

    @property
    def precision(self) -> float:
        """Fraction of detections that were *not* false positives.

        Returns 1.0 when there are no detections yet (conservative default).
        """
        if self.detection_count == 0:
            return 1.0
        successful = self.detection_count - self.false_positive_count
        return successful / self.detection_count

    @property
    def is_ready_for_promotion(self) -> bool:
        """Check whether this rule meets the promotion threshold.

        A rule is promotable when all of the following hold:

        * It is currently in SHADOW mode.
        * ``detection_count >= promotion_threshold``.
        * ``false_positive_count`` is zero.
        """
        return (
            self.mode == RuleMode.SHADOW
            and self.detection_count >= self.promotion_threshold
            and self.false_positive_count == 0
        )

    @property
    def is_ready_for_demotion(self) -> bool:
        """Check whether this rule meets the demotion threshold.

        A rule is demotable when both of the following hold:

        * It is currently in ACTIVE mode.
        * ``false_positive_count >= demotion_threshold``.
        """
        return (
            self.mode == RuleMode.ACTIVE
            and self.false_positive_count >= self.demotion_threshold
        )


# ===========================================================================
# RuleEvaluation
# ===========================================================================


@dataclass(frozen=True)
class RuleEvaluation:
    """Result of evaluating one rule against a single tool call.

    Attributes:
        rule_name: Name of the evaluated rule.
        triggered: Whether the rule's evaluator returned ``True``.
        mode: The rule's mode at the time of evaluation.
        details: Optional contextual details about the evaluation.
    """

    rule_name: str
    triggered: bool
    mode: RuleMode = RuleMode.SHADOW
    details: str = ""


# ===========================================================================
# EvalCase
# ===========================================================================


@dataclass(frozen=True)
class EvalCase:
    """A single test case for the FrozenEvaluator.

    Note: while the dataclass itself is frozen (field references cannot be
    reassigned), the ``tool_call`` and ``context`` dicts remain mutable in
    content.  Consumers should treat them as read-only.

    Attributes:
        tool_call: The tool invocation dict to evaluate.
        expected: The expected ``GateDecision``.
        context: Optional additional context for evaluation.
        description: Human-readable description of this case.
    """

    tool_call: Dict[str, Any]
    expected: GateDecision
    context: Dict[str, Any] = field(default_factory=dict)
    description: str = ""


# ===========================================================================
# HumanApprovalGate
# ===========================================================================


class HumanApprovalGate:
    """Requires human approval before any evolved rule becomes default.

    Tracks a queue of rules awaiting human review.  A rule must be
    approved before it can be promoted to ACTIVE mode.

    Usage::

        gate = HumanApprovalGate()
        gate.request_approval(rule)

        # Later, a human reviews and approves (or rejects):
        gate.approve("rule_name")
        gate.reject("rule_name")
    """

    @dataclass(frozen=True)
    class PendingApproval:
        """A single rule awaiting human review."""

        rule_name: str
        description: str
        stats: Dict[str, Any]

    def __init__(self) -> None:
        self._pending: Dict[str, HumanApprovalGate.PendingApproval] = {}
        self._approved: set[str] = set()
        self._rejected: set[str] = set()

    # ------------------------------------------------------------------
    # Request / approve / reject
    # ------------------------------------------------------------------

    def request_approval(self, rule: SafetyRule) -> None:
        """Queue a rule for human approval.

        If the rule has already been approved or rejected this is a no-op.
        """
        if rule.name in self._approved or rule.name in self._rejected:
            return
        self._pending[rule.name] = HumanApprovalGate.PendingApproval(
            rule_name=rule.name,
            description=rule.description,
            stats={
                "detection_count": rule.detection_count,
                "false_positive_count": rule.false_positive_count,
                "precision": rule.precision,
                "mode": rule.mode.value,
            },
        )

    def approve(self, rule_name: str) -> bool:
        """Mark a pending rule as approved.

        Returns ``True`` if the rule was found and approved, ``False``
        if no pending rule with that name exists.
        """
        if rule_name not in self._pending:
            return False
        self._approved.add(rule_name)
        self._pending.pop(rule_name, None)
        logger.info("HumanApprovalGate: approved rule '%s'", rule_name)
        return True

    def reject(self, rule_name: str) -> bool:
        """Mark a pending rule as rejected.

        Returns ``True`` if the rule was found and rejected, ``False``
        if no pending rule with that name exists.
        """
        if rule_name not in self._pending:
            return False
        self._rejected.add(rule_name)
        self._pending.pop(rule_name, None)
        logger.info("HumanApprovalGate: rejected rule '%s'", rule_name)
        return True

    # ------------------------------------------------------------------
    # Queries
    # ------------------------------------------------------------------

    def is_approved(self, rule_name: str) -> bool:
        """Return ``True`` if the rule has been approved."""
        return rule_name in self._approved

    def is_rejected(self, rule_name: str) -> bool:
        """Return ``True`` if the rule has been rejected."""
        return rule_name in self._rejected

    @property
    def pending(self) -> Tuple[PendingApproval, ...]:
        """Rules currently awaiting human approval."""
        return tuple(self._pending.values())

    def clear(self, rule_name: str) -> None:
        """Reset approval / rejection status for a rule so it can be re-reviewed."""
        self._approved.discard(rule_name)
        self._rejected.discard(rule_name)
        self._pending.pop(rule_name, None)


# ===========================================================================
# FrozenEvaluator
# ===========================================================================


class FrozenEvaluator:
    """Fixed evaluation set that never changes (prevents drift).

    Holds an immutable collection of ``EvalCase`` instances.  Call
    ``evaluate(gate, policy)`` to run every case against a
    ToolGate + Policy combination and receive a pass/fail report.

    Once constructed the test cases **cannot** be modified -- this ensures
    the evaluation criteria remain constant over time, preventing gradual
    drift in safety standards.
    """

    def __init__(self, cases: List[EvalCase]) -> None:
        """Store a snapshot of the evaluation cases.

        Args:
            cases: Test cases.  Stored as a tuple inside the evaluator
                to guarantee structural immutability.
        """
        self._cases: Tuple[EvalCase, ...] = tuple(cases)

    @property
    def cases(self) -> Tuple[EvalCase, ...]:
        """Immutable view of all registered evaluation cases."""
        return self._cases

    def evaluate(
        self,
        gate: Any,
        policy: Any,
    ) -> Dict[str, Any]:
        """Run all test cases against the given *gate* and *policy*.

        Args:
            gate: An object with a ``validate(tool_call, policy)`` method
                that returns a ``GateDecision`` (e.g. ``ToolGate``).
            policy: A ``Policy`` to pass to ``gate.validate()``.

        Returns:
            A dict with keys:

            * ``total`` (int) -- number of cases.
            * ``passed`` (int) -- cases where ``actual == expected``.
            * ``failed`` (int) -- cases where ``actual != expected``.
            * ``results`` (list[dict]) -- per-case details.
        """
        results: List[Dict[str, Any]] = []
        passed = 0
        failed = 0

        for case in self._cases:
            try:
                decision = gate.validate(case.tool_call, policy)
            except Exception:
                logger.exception(
                    "FrozenEvaluator: exception evaluating case '%s'",
                    case.description or "(unnamed)",
                )
                decision = None

            is_pass = decision == case.expected
            if is_pass:
                passed += 1
            else:
                failed += 1

            results.append(
                {
                    "description": case.description,
                    "expected": case.expected.value if case.expected else None,
                    "actual": decision.value if decision else "error",
                    "passed": is_pass,
                }
            )

        return {
            "total": len(self._cases),
            "passed": passed,
            "failed": failed,
            "results": results,
        }


# ===========================================================================
# EvolutionGuard
# ===========================================================================


class EvolutionGuard:
    """Gated promotion system for safety rules.

    Manages a set of ``SafetyRule`` instances through their lifecycle::

        SHADOW  -->  ACTIVE  -->  SHADOW / DISABLED

    * Rules start in SHADOW mode (evaluated but only log -- no enforcement).
    * After N successful detections without false positives a rule is ready
      for promotion to ACTIVE (full enforcement).
    * After M false positives a rule is demoted back to SHADOW or DISABLED.

    When a ``HumanApprovalGate`` is configured, promotion requires explicit
    human approval -- the rule stays in SHADOW until ``approve()`` is called.
    """

    def __init__(
        self,
        rules: Optional[List[SafetyRule]] = None,
        approval_gate: Optional[HumanApprovalGate] = None,
    ) -> None:
        """Initialise the guard.

        Args:
            rules: Initial set of safety rules.  Starts empty if ``None``.
            approval_gate: An optional ``HumanApprovalGate`` to gate
                promotions behind human review.
        """
        self._rules: Dict[str, SafetyRule] = {}
        self._approval_gate = approval_gate
        if rules is not None:
            for rule in rules:
                self._rules[rule.name] = rule

    # ------------------------------------------------------------------
    # Rule management
    # ------------------------------------------------------------------

    def add_rule(self, rule: SafetyRule) -> None:
        """Register a new safety rule.

        Args:
            rule: The ``SafetyRule`` to add.
        """
        self._rules[rule.name] = rule

    def get_rule(self, name: str) -> Optional[SafetyRule]:
        """Look up a rule by name.

        Args:
            name: The rule's unique identifier.

        Returns:
            The ``SafetyRule`` if found, or ``None``.
        """
        return self._rules.get(name)

    @property
    def rules(self) -> Tuple[SafetyRule, ...]:
        """All registered rules (immutable snapshot)."""
        return tuple(self._rules.values())

    @property
    def active_rules(self) -> Tuple[SafetyRule, ...]:
        """Rules currently in ACTIVE mode."""
        return tuple(r for r in self._rules.values() if r.mode == RuleMode.ACTIVE)

    @property
    def shadow_rules(self) -> Tuple[SafetyRule, ...]:
        """Rules currently in SHADOW mode."""
        return tuple(r for r in self._rules.values() if r.mode == RuleMode.SHADOW)

    @property
    def disabled_rules(self) -> Tuple[SafetyRule, ...]:
        """Rules currently in DISABLED mode."""
        return tuple(r for r in self._rules.values() if r.mode == RuleMode.DISABLED)

    # ------------------------------------------------------------------
    # Evaluation
    # ------------------------------------------------------------------

    def evaluate(
        self,
        tool_call: Dict[str, Any],
        context: Optional[Dict[str, Any]] = None,
    ) -> List[RuleEvaluation]:
        """Run every non-disabled rule against the given *tool_call*.

        Shadow-mode rules are evaluated but only log -- they never produce
        enforcement decisions.  Active-mode rules are also evaluated and
        their results are returned in the same list.

        Args:
            tool_call: The tool invocation dict (expected keys: ``name``,
                ``args``).
            context: Optional extra data passed to each rule's evaluator
                function.

        Returns:
            A list of ``RuleEvaluation`` instances, one per rule that was
            actually evaluated (disabled rules are skipped entirely).
        """
        ctx: Dict[str, Any] = context or {}
        results: List[RuleEvaluation] = []

        for rule in self._rules.values():
            if rule.mode == RuleMode.DISABLED:
                continue

            try:
                triggered = rule.rule_fn(tool_call, ctx)
            except Exception:
                logger.exception(
                    "EvolutionGuard: rule '%s' raised an exception during evaluation",
                    rule.name,
                )
                triggered = False

            results.append(
                RuleEvaluation(
                    rule_name=rule.name,
                    triggered=triggered,
                    mode=rule.mode,
                )
            )

            if triggered:
                logger.info(
                    "EvolutionGuard: [%s] rule '%s' triggered",
                    rule.mode.value.upper(),
                    rule.name,
                )

        return results

    # ------------------------------------------------------------------
    # Feedback & lifecycle transitions
    # ------------------------------------------------------------------

    def record_feedback(
        self,
        rule_name: str,
        was_false_positive: bool,
    ) -> SafetyRule:
        """Record human feedback about a rule firing.

        This follows the immutable pattern: a **new** ``SafetyRule`` with
        updated counts is created and stored inside the guard.  The original
        rule object is not mutated.

        Args:
            rule_name: Name of the rule to update.
            was_false_positive: ``True`` if this detection was a false
                positive, ``False`` if it was a correct detection.

        Returns:
            The new (updated) ``SafetyRule``.

        Raises:
            KeyError: If no rule with *rule_name* is registered.
        """
        rule = self._rules[rule_name]

        new_rule = SafetyRule(
            name=rule.name,
            description=rule.description,
            rule_fn=rule.rule_fn,
            mode=rule.mode,
            detection_count=rule.detection_count + 1,
            false_positive_count=(
                rule.false_positive_count + 1
                if was_false_positive
                else rule.false_positive_count
            ),
            promotion_threshold=rule.promotion_threshold,
            demotion_threshold=rule.demotion_threshold,
        )
        self._rules[rule_name] = new_rule
        return new_rule

    def maybe_promote(self, rule_name: str) -> SafetyRule:
        """Attempt to promote a rule from SHADOW to ACTIVE.

        Promotion succeeds only when all of the following hold:

        1. The rule's ``is_ready_for_promotion`` property is ``True``.
        2. If a ``HumanApprovalGate`` is configured, the rule has been
           explicitly approved (otherwise approval is requested and the
           rule stays in SHADOW).

        Args:
            rule_name: Name of the rule to promote.

        Returns:
            The (possibly updated) ``SafetyRule``.

        Raises:
            KeyError: If no rule with *rule_name* is registered.
        """
        rule = self._rules[rule_name]

        if not rule.is_ready_for_promotion:
            return rule

        # Gate behind human approval when configured
        if self._approval_gate is not None:
            if not self._approval_gate.is_approved(rule_name):
                self._approval_gate.request_approval(rule)
                return rule

        promoted = SafetyRule(
            name=rule.name,
            description=rule.description,
            rule_fn=rule.rule_fn,
            mode=RuleMode.ACTIVE,
            detection_count=rule.detection_count,
            false_positive_count=rule.false_positive_count,
            promotion_threshold=rule.promotion_threshold,
            demotion_threshold=rule.demotion_threshold,
        )
        self._rules[rule_name] = promoted
        logger.info("EvolutionGuard: promoted rule '%s' to ACTIVE", rule_name)
        return promoted

    def maybe_demote(self, rule_name: str) -> SafetyRule:
        """Attempt to demote a rule from ACTIVE.

        * If ``false_positive_count >= demotion_threshold`` the rule is
          demoted to **SHADOW**.
        * If ``false_positive_count >= 2 * demotion_threshold`` the rule
          is demoted all the way to **DISABLED**.

        Args:
            rule_name: Name of the rule to demote.

        Returns:
            The (possibly updated) ``SafetyRule``.

        Raises:
            KeyError: If no rule with *rule_name* is registered.
        """
        rule = self._rules[rule_name]

        if not rule.is_ready_for_demotion:
            return rule

        new_mode: RuleMode
        if rule.false_positive_count >= rule.demotion_threshold * 2:
            new_mode = RuleMode.DISABLED
        else:
            new_mode = RuleMode.SHADOW

        demoted = SafetyRule(
            name=rule.name,
            description=rule.description,
            rule_fn=rule.rule_fn,
            mode=new_mode,
            detection_count=rule.detection_count,
            false_positive_count=rule.false_positive_count,
            promotion_threshold=rule.promotion_threshold,
            demotion_threshold=rule.demotion_threshold,
        )
        self._rules[rule_name] = demoted
        logger.info(
            "EvolutionGuard: demoted rule '%s' from ACTIVE to %s",
            rule_name,
            new_mode.value.upper(),
        )
        return demoted

    def reset_counts(self, rule_name: str) -> SafetyRule:
        """Zero the detection and false-positive counts for a rule.

        The rule's mode and thresholds are preserved.

        Args:
            rule_name: Name of the rule to reset.

        Returns:
            The new ``SafetyRule`` with zeroed counts.

        Raises:
            KeyError: If no rule with *rule_name* is registered.
        """
        rule = self._rules[rule_name]
        reset = SafetyRule(
            name=rule.name,
            description=rule.description,
            rule_fn=rule.rule_fn,
            mode=rule.mode,
            detection_count=0,
            false_positive_count=0,
            promotion_threshold=rule.promotion_threshold,
            demotion_threshold=rule.demotion_threshold,
        )
        self._rules[rule_name] = reset
        return reset


# ===========================================================================
# Built-in rule evaluators
# ===========================================================================


def _dangerous_bash_evaluator(
    tool_call: Dict[str, Any],
    context: Dict[str, Any],
) -> bool:
    """Built-in evaluator: trigger on dangerous Bash commands.

    Matches commands that start with a known dangerous prefix:
    ``rm``, ``sudo``, ``dd``, ``mkfs``, ``chmod``, ``chown``.
    """
    if tool_call.get("name") != "Bash":
        return False
    command: str = (
        tool_call.get("args", {}).get("command")
        or tool_call.get("args", {}).get("cmd")
        or ""
    )
    # Note: mkfs intentionally has no trailing space because the actual
    # binary is mkfs.ext4, mkfs.xfs, mkfs.btrfs, etc.
    dangerous_prefixes: Tuple[str, ...] = (
        "rm ",
        "sudo ",
        "dd ",
        "mkfs",
        "chmod ",
        "chown ",
    )
    stripped = command.strip()
    return any(stripped.startswith(p) for p in dangerous_prefixes)
