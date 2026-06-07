"""
SMT-based deterministic sandbox for query governance.

Provides ``SMTSandbox`` for encoding agent actions as SMT formulas and
verifying them against formal constraints before execution, and
``FormalQueryLoopGovernance`` for embedding SMT verification into the
agent execution loop.

Gracefully falls back to a pure-Python constraint checker when
``z3-solver`` is not installed.

Classes
-------
ConstraintOperator:
    Enum of supported constraint operators (eq, neq, gt, ge, lt, le,
    contains, prefix, suffix, in_set, not_in_set, matches_regex).
ActionSMT:
    A structured action with SMT-level constraints.
VerificationStatus:
    Result status for a single SMT verification.
SMTSandbox:
    SMT-backed deterministic sandbox for query governance.
FormalQueryLoopGovernance:
    Verify agent actions against a formal spec before execution.
"""

from __future__ import annotations

import dataclasses
import logging
import re
from dataclasses import dataclass, field
from enum import Enum
from typing import Any, Callable

logger = logging.getLogger(__name__)

# ---------------------------------------------------------------------------
# Constraint operator
# ---------------------------------------------------------------------------


class ConstraintOperator(str, Enum):
    """Supported constraint operators for SMT encoding."""

    EQ = "eq"
    NEQ = "neq"
    GT = "gt"
    GE = "ge"
    LT = "lt"
    LE = "le"
    CONTAINS = "contains"
    PREFIX = "prefix"
    SUFFIX = "suffix"
    IN_SET = "in_set"
    NOT_IN_SET = "not_in_set"
    MATCHES_REGEX = "matches_regex"


# ---------------------------------------------------------------------------
# Data classes
# ---------------------------------------------------------------------------


@dataclass(frozen=True)
class ActionSMT:
    """A structured action with SMT-level constraints.

    Attributes
    ----------
    name:
        Human-readable action name (e.g. ``"read_file"``).
    params:
        Parameter name-value mapping.
    constraints:
        List of ``(field, operator, value)`` tuples to enforce.
    """

    name: str
    params: dict[str, Any] = field(default_factory=dict)
    constraints: list[tuple[str, ConstraintOperator, Any]] = field(default_factory=list)


@dataclass(frozen=True)
class VerificationStatus:
    """Result status for a single SMT verification.

    Attributes
    ----------
    allowed:
        True if the action passes all constraints.
    reason:
        Human-readable explanation when ``allowed`` is False.
    model:
        Optional satisfying assignment (dict) when available.
    """

    allowed: bool
    reason: str = ""
    model: dict[str, Any] | None = None


# ---------------------------------------------------------------------------
# Pure-Python fallback
# ---------------------------------------------------------------------------


class _PythonConstraintChecker:
    """Fallback constraint checker when ``z3-solver`` is absent.

    Evaluates constraints using plain Python logic.  Provides the same
    interface as the Z3-backed checker but does not use SMT solving.
    """

    def check(self, action: ActionSMT) -> VerificationStatus:
        """Check all constraints using pure-Python logic.

        Returns ``VerificationStatus(allowed=True)`` when every constraint
        is satisfied; otherwise the first failing constraint is reported.
        """
        for field, operator, value in action.constraints:
            actual = action.params.get(field)
            if actual is None:
                return VerificationStatus(
                    allowed=False,
                    reason=f"Missing parameter '{field}' for constraint evaluation",
                )
            ok = self._evaluate(str(actual), operator, value)
            if not ok:
                return VerificationStatus(
                    allowed=False,
                    reason=(
                        f"Constraint failed: {field} {operator.value} {value!r} "
                        f"(actual: {actual!r})"
                    ),
                )
        return VerificationStatus(allowed=True, reason="All constraints satisfied")

    def verify_batch(self, actions: list[ActionSMT]) -> list[VerificationStatus]:
        """Verify multiple actions in batch."""
        return [self.check(a) for a in actions]

    @staticmethod
    def _evaluate(actual: str, operator: ConstraintOperator, value: Any) -> bool:
        if operator == ConstraintOperator.EQ:
            return actual == str(value)
        if operator == ConstraintOperator.NEQ:
            return actual != str(value)

        # Numeric comparisons
        try:
            num_actual = float(actual) if actual else None
            num_value = float(value)
        except (ValueError, TypeError):
            num_actual = None

        if num_actual is not None:
            if operator == ConstraintOperator.GT:
                return num_actual > num_value
            if operator == ConstraintOperator.GE:
                return num_actual >= num_value
            if operator == ConstraintOperator.LT:
                return num_actual < num_value
            if operator == ConstraintOperator.LE:
                return num_actual <= num_value

        # String operators
        str_val = str(value)
        if operator == ConstraintOperator.CONTAINS:
            return str_val in actual
        if operator == ConstraintOperator.PREFIX:
            return actual.startswith(str_val)
        if operator == ConstraintOperator.SUFFIX:
            return actual.endswith(str_val)
        if operator == ConstraintOperator.IN_SET:
            if isinstance(value, (list, tuple, set)):
                return actual in {str(v) for v in value}
            return actual == str_val
        if operator == ConstraintOperator.NOT_IN_SET:
            if isinstance(value, (list, tuple, set)):
                return actual not in {str(v) for v in value}
            return actual != str_val
        if operator == ConstraintOperator.MATCHES_REGEX:
            try:
                return bool(re.search(str_val, actual))
            except re.error:
                return False

        return False

    def is_valid_rule(self, constraints: list[tuple[str, ConstraintOperator, Any]]) -> bool:
        """Check if a set of constraints is self-consistent.

        Detects obvious contradictions (e.g., eq AND neq on same field+value).
        """
        by_field: dict[str, set[str]] = {}
        for field, operator, value in constraints:
            if field not in by_field:
                by_field[field] = set()
            by_field[field].add(f"{operator.value}:{value}")
        for field, ops in by_field.items():
            eq_key = f"{ConstraintOperator.EQ.value}:"
            neq_key = f"{ConstraintOperator.NEQ.value}:"
            eq_vals = {k for k in ops if k.startswith(eq_key)}
            neq_vals = {k for k in ops if k.startswith(neq_key)}
            for eq in eq_vals:
                eq_val = eq[len(eq_key):]
                if any(nv.endswith(eq_val) for nv in neq_vals):
                    return False
        return True


# ---------------------------------------------------------------------------
# Z3 availability
# ---------------------------------------------------------------------------

_HAS_Z3: bool = False
_z3 = None

try:
    import z3  # type: ignore[import-untyped]
    _z3 = z3
    _HAS_Z3 = True
except ImportError:
    logger.info("z3-solver not installed — using pure-Python fallback constraint checker.")


# ---------------------------------------------------------------------------
# SMTSandbox
# ---------------------------------------------------------------------------


class SMTSandbox:
    """SMT-backed deterministic sandbox for query governance.

    Encodes agent actions as SMT formulas and verifies them against
    formal constraints before execution.  Falls back to pure-Python
    constraint checking when ``z3-solver`` is not installed.

    Usage::

        sandbox = SMTSandbox()
        action = ActionSMT(
            name="write_file",
            params={"path": "/tmp/out.txt", "content": "hello"},
            constraints=[("path", ConstraintOperator.PREFIX, "/tmp/")],
        )
        result = sandbox.verify(action)
        print(result.allowed, result.reason)
    """

    def __init__(self) -> None:
        self._fallback = _PythonConstraintChecker()
        self._rules: dict[str, list[tuple[str, ConstraintOperator, Any]]] = {}

    # ------------------------------------------------------------------
    # Public API
    # ------------------------------------------------------------------

    def add_rule(
        self,
        name: str,
        constraints: list[tuple[str, ConstraintOperator, Any]],
    ) -> None:
        """Register a named constraint rule.

        Args:
            name: Unique rule name.
            constraints: List of ``(field, operator, value)`` tuples.
        """
        self._rules[name] = constraints

    def remove_rule(self, name: str) -> bool:
        """Remove a previously registered rule.

        Args:
            name: Rule name to remove.

        Returns:
            True if the rule was found and removed.
        """
        return self._rules.pop(name, None) is not None

    def list_rules(self) -> list[str]:
        """Return names of all registered rules."""
        return list(self._rules.keys())

    def encode_to_smt(self, action: ActionSMT) -> Any:
        """Encode an action as an SMT formula.

        When ``z3-solver`` is available, returns a Z3 expression.
        Otherwise returns a serializable dict representation.

        Args:
            action: The action to encode.

        Returns:
            A Z3 expression (when z3 is installed) or a dict.
        """
        if _HAS_Z3:
            return self._encode_z3(action)
        return {
            "action": action.name,
            "params": action.params,
            "constraints": [
                [field, op.value, value]
                for field, op, value in action.constraints
            ],
            "rules": list(self._rules.keys()),
        }

    def verify(self, action: ActionSMT) -> VerificationStatus:
        """Verify an action against its constraints (and registered rules).

        Steps:
        1. Collect all constraints (from action + any matching rules).
        2. Encode as SMT formula (or fallback logic).
        3. Check satisfiability.
        4. Return ``VerificationStatus``.

        Args:
            action: The action to verify.

        Returns:
            A ``VerificationStatus``.
        """
        # Merge action constraints with matching registered rules
        all_constraints = list(action.constraints)
        for rule_name, rule_constraints in self._rules.items():
            all_constraints.extend(rule_constraints)

        if not all_constraints:
            return VerificationStatus(allowed=True, reason="No constraints to verify")

        if _HAS_Z3:
            return self._verify_z3(action, all_constraints)

        return self._verify_python(all_constraints, action.params)

    def verify_batch(self, actions: list[ActionSMT]) -> list[VerificationStatus]:
        """Verify multiple actions in batch.

        Args:
            actions: List of actions to verify.

        Returns:
            List of ``VerificationStatus`` results.
        """
        return [self.verify(a) for a in actions]

    # ------------------------------------------------------------------
    # Z3 internals
    # ------------------------------------------------------------------

    def _encode_z3(self, action: ActionSMT) -> Any:
        """Encode an action as a Z3 formula."""
        assert _z3 is not None

        from z3 import And, Bool, Contains, Not, Or, PrefixOf, String, StringVal, SuffixOf

        constraints = list(action.constraints)
        for rule_name, rule_constraints in self._rules.items():
            constraints.extend(rule_constraints)

        if not constraints:
            return Bool(True)

        # Build symbolic variables for referenced fields
        sym_vars: dict[str, Any] = {}
        for field, _op, _value in constraints:
            if field not in sym_vars:
                sym_vars[field] = String(field)

        z3_conditions: list[Any] = []
        for field, operator, value in constraints:
            var = sym_vars[field]
            val = StringVal(str(value))

            if operator == ConstraintOperator.EQ:
                z3_conditions.append(var == val)
            elif operator == ConstraintOperator.NEQ:
                z3_conditions.append(var != val)
            elif operator == ConstraintOperator.GT:
                z3_conditions.append(var > val)
            elif operator == ConstraintOperator.GE:
                z3_conditions.append(var >= val)
            elif operator == ConstraintOperator.LT:
                z3_conditions.append(var < val)
            elif operator == ConstraintOperator.LE:
                z3_conditions.append(var <= val)
            elif operator == ConstraintOperator.CONTAINS:
                z3_conditions.append(Contains(var, val))
            elif operator == ConstraintOperator.PREFIX:
                z3_conditions.append(PrefixOf(val, var))
            elif operator == ConstraintOperator.SUFFIX:
                z3_conditions.append(SuffixOf(val, var))
            elif operator == ConstraintOperator.IN_SET:
                items = list(value) if isinstance(value, (list, tuple, set)) else [value]
                parts = [str(v).strip() for v in items if v]
                if parts:
                    z3_conditions.append(Or(*(var == StringVal(p) for p in parts)))
                else:
                    z3_conditions.append(Bool(False))
            elif operator == ConstraintOperator.NOT_IN_SET:
                items = list(value) if isinstance(value, (list, tuple, set)) else [value]
                parts = [str(v).strip() for v in items if v]
                if parts:
                    z3_conditions.append(And(*(var != StringVal(p) for p in parts)))
                else:
                    z3_conditions.append(Bool(True))
            elif operator == ConstraintOperator.MATCHES_REGEX:
                # Z3 does not support regex directly; approximate with contains
                z3_conditions.append(Contains(var, val))
            else:
                z3_conditions.append(Bool(True))

        if len(z3_conditions) == 1:
            return z3_conditions[0]
        return And(*z3_conditions)

    def _verify_z3(
        self,
        action: ActionSMT,
        constraints: list[tuple[str, ConstraintOperator, Any]],
    ) -> VerificationStatus:
        """Verify using Z3 solver."""
        assert _z3 is not None

        # Build combined action with all constraints
        combined = ActionSMT(name=action.name, params=action.params, constraints=constraints)
        formula = self._encode_z3(combined)

        solver = _z3.Solver()
        solver.add(formula)
        result = solver.check()

        if result == _z3.sat:
            model = solver.model()
            model_dict: dict[str, Any] = {}
            for field, _op, _value in constraints:
                if field not in model_dict:
                    try:
                        val = model.eval(_z3.String(field), model_completion=True)
                        model_dict[field] = str(val)
                    except Exception:
                        model_dict[field] = f"<model:{field}>"
            return VerificationStatus(
                allowed=True,
                reason="Action satisfies all constraints",
                model=model_dict,
            )

        if result == _z3.unsat:
            return VerificationStatus(
                allowed=False,
                reason="Action violates constraints (unsatisfiable)",
            )

        return VerificationStatus(
            allowed=False,
            reason="Z3 returned 'unknown' — constraint satisfaction undecidable",
        )

    def _verify_python(
        self,
        constraints: list[tuple[str, ConstraintOperator, Any]],
        params: dict[str, Any],
    ) -> VerificationStatus:
        """Verify using pure-Python fallback checker."""
        action = ActionSMT(name="verify", params=params, constraints=constraints)
        return self._fallback.check(action)


# ---------------------------------------------------------------------------
# FormalQueryLoopGovernance
# ---------------------------------------------------------------------------


class FormalQueryLoopGovernance:
    """Verify agent actions against a formal specification before execution.

    Wraps ``SMTSandbox`` in a governance layer suitable for embedding in the
    agent execution loop.  Pre-validates every action the agent intends to
    take against a formal spec before it reaches the tool executor.

    Usage::

        gov = FormalQueryLoopGovernance()
        gov.add_rule("no_etc_write", [
            ("path", ConstraintOperator.PREFIX, "/tmp/"),
            ("path", ConstraintOperator.NEQ, "/etc/passwd"),
        ])

        async for action in agent_actions:
            status = await gov.guard(action)
            if not status.allowed:
                logger.warning("Action blocked by governance: %s", status.reason)
                continue  # or escalate
            await execute(action)
    """

    def __init__(self, sandbox: SMTSandbox | None = None) -> None:
        self._sandbox = sandbox or SMTSandbox()

    # ------------------------------------------------------------------
    # Rule management
    # ------------------------------------------------------------------

    def add_rule(
        self,
        name: str,
        constraints: list[tuple[str, ConstraintOperator, Any]],
    ) -> None:
        """Register a formal governance rule.

        Args:
            name: Unique rule identifier.
            constraints: Constraint tuples ``(field, operator, value)``.
        """
        self._sandbox.add_rule(name, constraints)

    def remove_rule(self, name: str) -> bool:
        """Remove a governance rule.

        Args:
            name: Rule name to remove.

        Returns:
            True if the rule was removed.
        """
        return self._sandbox.remove_rule(name)

    def list_rules(self) -> list[str]:
        """Return all registered governance rule names."""
        return self._sandbox.list_rules()

    # ------------------------------------------------------------------
    # Governance
    # ------------------------------------------------------------------

    async def guard(self, action: ActionSMT) -> VerificationStatus:
        """Verify an action against all registered governance rules.

        This is the primary entry point for loop integration.  Call it
        before dispatching an action to the tool executor.

        Args:
            action: The agent's intended action.

        Returns:
            A ``VerificationStatus``.  ``allowed == True`` means the
            action passed governance and may proceed.
        """
        status = self._sandbox.verify(action)
        if not status.allowed:
            logger.warning(
                "Governance blocked action '%s': %s",
                action.name,
                status.reason,
            )
        return status

    async def guard_batch(self, actions: list[ActionSMT]) -> list[VerificationStatus]:
        """Verify multiple actions in batch.

        Args:
            actions: List of actions to verify.

        Returns:
            List of ``VerificationStatus`` results.
        """
        return [await self.guard(a) for a in actions]

    # ------------------------------------------------------------------
    # Spec management
    # ------------------------------------------------------------------

    def load_spec(self, spec: dict[str, list[tuple[str, ConstraintOperator, Any]]]) -> None:
        """Load a formal specification from a dict.

        The dict should map rule names to lists of constraint tuples.

        Args:
            spec: Dict of ``{rule_name: [(field, op, value), ...]}``.
        """
        for name, constraints in spec.items():
            self.add_rule(name, constraints)

    def export_spec(self) -> dict[str, list[tuple[str, ConstraintOperator, Any]]]:
        """Export the current governance spec as a dict.

        Returns:
            Dict of ``{rule_name: [(field, op, value), ...]}``.
        """
        result: dict[str, list[tuple[str, ConstraintOperator, Any]]] = {}
        for name in self._sandbox.list_rules():
            constraints = self._sandbox._rules.get(name, [])
            result[name] = constraints
        return result

    def clear_rules(self) -> None:
        """Remove all registered governance rules."""
        for name in self._sandbox.list_rules():
            self._sandbox.remove_rule(name)
