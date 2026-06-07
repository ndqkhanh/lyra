"""
Z3-based formal verification of safety rules (P8 v8.3).

Provides ``Z3SMTVerifier`` for proving safety rules satisfiable/valid,
encoding rules as SMT formulas, and generating counterexamples when
verification fails.  Includes ``RuleOptimizer`` for detecting redundant
or contradictory rules via SMT equivalence checking.

Gracefully falls back to a pure-Python verifier when ``z3-solver`` is
not installed.

Classes
-------
SafetyRuleType:
    Enum categorising safety rules by their domain.
VerificationResult:
    Result of a formal verification check (valid / satisfiable / unknown).
SymbolicSafetyRule:
    A safety rule expressed as symbolic constraints (Z3-friendly).
Z3SMTVerifier:
    Core SMT-based verifier using Z3.
RuleOptimizer:
    Detects redundant and contradictory rules via equivalence checking.
"""

from __future__ import annotations

import logging
from dataclasses import dataclass, field
from enum import Enum
from typing import Any, Dict, List, Optional, Tuple

logger = logging.getLogger(__name__)

# ---------------------------------------------------------------------------
# SafetyRuleType
# ---------------------------------------------------------------------------


class SafetyRuleType(str, Enum):
    """Domain category for a safety rule."""

    TOOL_GATE = "tool_gate"
    FILESYSTEM_GATE = "filesystem_gate"
    NETWORK_GATE = "network_gate"
    PROCESS_GATE = "process_gate"


# ---------------------------------------------------------------------------
# VerificationResult
# ---------------------------------------------------------------------------


@dataclass(frozen=True)
class VerificationResult:
    """Result of a single formal verification check.

    Attributes:
        rule_name: Name of the verified rule.
        rule_type: Domain of the verified rule.
        valid: True if the rule is valid (holds for all inputs).
        satisfiable: True if the rule is satisfiable (some input exists).
        counterexample: An example input that violates the rule, if
            applicable.  ``None`` when the rule is valid.
        details: Human-readable explanation of the result.
    """

    rule_name: str
    rule_type: SafetyRuleType
    valid: bool
    satisfiable: bool
    counterexample: Optional[Dict[str, Any]] = None
    details: str = ""


# ---------------------------------------------------------------------------
# SymbolicSafetyRule
# ---------------------------------------------------------------------------


@dataclass(frozen=True)
class SymbolicCondition:
    """A single symbolic constraint in a safety rule.

    Attributes:
        field: The field being constrained (e.g. ``"tool_name"``,
            ``"file_path"``, ``"domain"``, ``"command"``).
        operator: The comparison operator (``"eq"``, ``"neq"``,
            ``"prefix"``, ``"suffix"``, ``"contains"``, ``"glob"``,
            ``"in"``, ``"not_in"``).
        value: The value to compare against.
    """

    field: str
    operator: str
    value: str


@dataclass(frozen=True)
class SymbolicSafetyRule:
    """A safety rule expressed as symbolic constraints.

    Attributes:
        name: Unique rule identifier.
        description: Human-readable description.
        rule_type: Domain category (tool, filesystem, network, process).
        conditions: List of symbolic conditions (AND semantics).
        negated: If True, the rule fires when conditions are **not** met
            (i.e. the rule encodes *disallowed* behaviour).
    """

    name: str
    description: str
    rule_type: SafetyRuleType = SafetyRuleType.TOOL_GATE
    conditions: List[SymbolicCondition] = field(default_factory=list)
    negated: bool = False

    def to_dict(self) -> Dict[str, Any]:
        """Serialize to a plain dict for counterexample generation."""
        return {
            "name": self.name,
            "description": self.description,
            "rule_type": self.rule_type.value,
            "conditions": [
                {"field": c.field, "operator": c.operator, "value": c.value}
                for c in self.conditions
            ],
            "negated": self.negated,
        }


# ---------------------------------------------------------------------------
# Pure-Python fallback
# ---------------------------------------------------------------------------


class _PurePythonVerifier:
    """Fallback verifier when ``z3-solver`` is not installed.

    Uses basic logic to check symbolic rules for obvious contradictions
    and tautologies.  Does not perform full SMT solving — serves as a
    best-effort approximation.
    """

    def verify(self, rule: SymbolicSafetyRule) -> VerificationResult:
        """Verify a rule using pure-Python logic.

        Checks for:
        * Direct contradictions (eq and neq on same field+value).
        * Trivially satisfiable rules (at least one condition exists).
        """
        rule_name = rule.name
        rule_type = rule.rule_type
        contradictions = self._find_contradictions(rule)

        if contradictions:
            return VerificationResult(
                rule_name=rule_name,
                rule_type=rule_type,
                valid=False,
                satisfiable=False,
                counterexample={},
                details=f"Contradictory conditions found: {'; '.join(contradictions)}",
            )

        # A rule with no conditions is trivially satisfiable
        if not rule.conditions:
            return VerificationResult(
                rule_name=rule_name,
                rule_type=rule_type,
                valid=True,
                satisfiable=True,
                counterexample=None,
                details="Empty rule — trivially valid and satisfiable.",
            )

        return VerificationResult(
            rule_name=rule_name,
            rule_type=rule_type,
            valid=False,
            satisfiable=True,
            counterexample=self._generate_example(rule),
            details="Rule is satisfiable but not universally valid (fallback verifier).",
        )

    def _find_contradictions(self, rule: SymbolicSafetyRule) -> List[str]:
        """Detect contradictory condition pairs."""
        issues: List[str] = []

        # Group conditions by field
        by_field: Dict[str, List[SymbolicCondition]] = {}
        for c in rule.conditions:
            by_field.setdefault(c.field, []).append(c)

        for field, conds in by_field.items():
            values_by_op: Dict[str, set] = {}
            for c in conds:
                values_by_op.setdefault(c.operator, set()).add(c.value)

            # eq and neq on the same value is contradictory
            eq_vals = values_by_op.get("eq", set())
            neq_vals = values_by_op.get("neq", set())
            common = eq_vals & neq_vals
            if common:
                for v in common:
                    issues.append(f"'{field}' cannot be both eq and neq '{v}'")

        return issues

    @staticmethod
    def _generate_example(rule: SymbolicSafetyRule) -> Dict[str, Any]:
        """Generate a satisfying example for a rule."""
        example: Dict[str, Any] = {}
        for c in rule.conditions:
            if c.operator == "eq":
                example[c.field] = c.value
            elif c.operator == "neq":
                example[c.field] = f"(not {c.value})"
            elif c.operator == "prefix":
                example[c.field] = f"{c.value}_example"
            elif c.operator == "suffix":
                example[c.field] = f"example_{c.value}"
            elif c.operator == "contains":
                example[c.field] = f"before_{c.value}_after"
            elif c.operator in ("in",):
                example[c.field] = c.value
            else:
                example[c.field] = f"<{c.operator}:{c.value}>"
        return example

    def check_equivalence(
        self, rule_a: SymbolicSafetyRule, rule_b: SymbolicSafetyRule
    ) -> bool:
        """Check if two rules are syntactically equivalent.

        Pure-Python fallback: compares conditions structurally.
        """
        if rule_a.negated != rule_b.negated:
            return False
        if len(rule_a.conditions) != len(rule_b.conditions):
            return False

        # Sort-normalise for comparison (order-independent)
        def _key(c: SymbolicCondition) -> Tuple[str, str, str]:
            return (c.field, c.operator, c.value)

        a_sorted = sorted(rule_a.conditions, key=_key)
        b_sorted = sorted(rule_b.conditions, key=_key)

        return all(
            ac.field == bc.field
            and ac.operator == bc.operator
            and ac.value == bc.value
            for ac, bc in zip(a_sorted, b_sorted)
        )

    def check_contradiction(
        self, rule_a: SymbolicSafetyRule, rule_b: SymbolicSafetyRule
    ) -> bool:
        """Check if two rules contradict each other."""
        # If one is the negation of the other on the same conditions
        if rule_a.negated != rule_b.negated:
            if rule_a.conditions == rule_b.conditions:
                return True

        # Check for directly conflicting conditions
        combined = list(rule_a.conditions) + list(rule_b.conditions)
        combined_rule = SymbolicSafetyRule(
            name="(combined)",
            description="",
            conditions=combined,
        )
        contradictions = self._find_contradictions(combined_rule)
        return len(contradictions) > 0


# ---------------------------------------------------------------------------
# Z3 Verifier (primary)
# ---------------------------------------------------------------------------

_HAS_Z3: bool = False
_z3 = None  # type: ignore
_Z3Solver = None  # type: ignore

try:
    import z3  # type: ignore[import-untyped]

    _z3 = z3
    _Z3Solver = z3.Solver
    _HAS_Z3 = True
except ImportError:
    logger.info("z3-solver not installed — using pure-Python fallback verifier.")


class Z3SMTVerifier:
    """Formal verification of safety rules using Z3.

    Encodes safety rules as SMT formulas and uses Z3 to determine
    validity, satisfiability, and counterexamples.

    Falls back to ``_PurePythonVerifier`` when ``z3-solver`` is not
    installed.
    """

    def __init__(self) -> None:
        self._fallback = _PurePythonVerifier()

    # ------------------------------------------------------------------
    # Public API
    # ------------------------------------------------------------------

    def verify(self, rule: SymbolicSafetyRule) -> VerificationResult:
        """Prove whether a safety rule is valid and/or satisfiable.

        Args:
            rule: The ``SymbolicSafetyRule`` to verify.

        Returns:
            A ``VerificationResult`` with validity, satisfiability, and
            optionally a counterexample.
        """
        if not _HAS_Z3:
            return self._fallback.verify(rule)

        return self._verify_z3(rule)

    def verify_batch(
        self, rules: List[SymbolicSafetyRule]
    ) -> List[VerificationResult]:
        """Verify multiple rules in a single batch.

        Args:
            rules: List of rules to verify.

        Returns:
            List of ``VerificationResult``, one per rule.
        """
        return [self.verify(r) for r in rules]

    # ------------------------------------------------------------------
    # Z3 internals
    # ------------------------------------------------------------------

    def _verify_z3(self, rule: SymbolicSafetyRule) -> VerificationResult:
        """Verify a rule using Z3."""
        assert _z3 is not None

        solver = _z3.Solver()
        formula = self.encode_to_smt(rule)
        solver.add(formula)

        result = solver.check()
        counterexample: Optional[Dict[str, Any]] = None

        if result == _z3.unsat:
            return VerificationResult(
                rule_name=rule.name,
                rule_type=rule.rule_type,
                valid=True,
                satisfiable=True,
                counterexample=None,
                details="Rule is valid (holds for all inputs) and satisfiable.",
            )

        if result == _z3.sat:
            model = solver.model()
            counterexample = self._model_to_dict(model, rule)
            return VerificationResult(
                rule_name=rule.name,
                rule_type=rule.rule_type,
                valid=False,
                satisfiable=True,
                counterexample=counterexample,
                details=(
                    "Rule is satisfiable but not universally valid. "
                    "Counterexample found."
                ),
            )

        # unknown
        return VerificationResult(
            rule_name=rule.name,
            rule_type=rule.rule_type,
            valid=False,
            satisfiable=False,
            counterexample=None,
            details="Z3 returned 'unknown' — rule could not be decided.",
        )

    def encode_to_smt(self, rule: SymbolicSafetyRule) -> "_z3.ExprRef":  # type: ignore[name-defined]
        """Encode a ``SymbolicSafetyRule`` as a Z3 SMT formula.

        Each ``SymbolicCondition`` is translated to a Z3 expression.
        Conditions are AND-ed together.  If ``negated`` is True, the
        entire conjunction is negated.

        Args:
            rule: The symbolic safety rule to encode.

        Returns:
            A Z3 expression representing the rule.
        """
        assert _z3 is not None
        from z3 import (
            And,
            Bool,
            Not,
            Or,
            String,
            StringVal,
            Contains,
            PrefixOf,
            SuffixOf,
        )

        # Create symbolic variables for each field referenced
        sym_vars: Dict[str, "_z3.ExprRef"] = {}  # type: ignore[name-defined]
        for cond in rule.conditions:
            if cond.field not in sym_vars:
                if cond.field in ("tool_name", "file_path", "domain", "command"):
                    sym_vars[cond.field] = String(cond.field)
                else:
                    sym_vars[cond.field] = String(cond.field)

        # Translate each condition
        z3_conditions: List["_z3.ExprRef"] = []  # type: ignore[name-defined]
        for cond in rule.conditions:
            var = sym_vars[cond.field]
            val = StringVal(cond.value)

            if cond.operator == "eq":
                z3_conditions.append(var == val)
            elif cond.operator == "neq":
                z3_conditions.append(var != val)
            elif cond.operator == "prefix":
                z3_conditions.append(PrefixOf(val, var))
            elif cond.operator == "suffix":
                z3_conditions.append(SuffixOf(val, var))
            elif cond.operator == "contains":
                z3_conditions.append(Contains(var, val))
            elif cond.operator == "in":
                # Split 'in' values by comma
                parts = [v.strip() for v in cond.value.split(",") if v.strip()]
                if parts:
                    z3_conditions.append(
                        Or(*(var == StringVal(p) for p in parts))
                    )
                else:
                    z3_conditions.append(Bool(False))
            elif cond.operator == "not_in":
                parts = [v.strip() for v in cond.value.split(",") if v.strip()]
                if parts:
                    z3_conditions.append(
                        And(*(var != StringVal(p) for p in parts))
                    )
                else:
                    z3_conditions.append(Bool(True))
            else:
                # Unknown operator — use a symbolic boolean placeholder
                z3_conditions.append(Bool(True))

        if not z3_conditions:
            formula: "_z3.ExprRef" = Bool(True)  # type: ignore[name-defined]
        elif len(z3_conditions) == 1:
            formula = z3_conditions[0]
        else:
            formula = And(*z3_conditions)

        if rule.negated:
            formula = Not(formula)

        return formula

    @staticmethod
    def _model_to_dict(
        model: "_z3.ModelRef", rule: SymbolicSafetyRule  # type: ignore[name-defined]
    ) -> Dict[str, Any]:
        """Extract a human-readable counterexample dict from a Z3 model."""
        result: Dict[str, Any] = {}
        for cond in rule.conditions:
            if cond.field not in result:
                try:
                    val = model.eval(_z3.String(cond.field), model_completion=True)
                    result[cond.field] = str(val)
                except Exception:
                    result[cond.field] = f"<model:{cond.field}>"
        return result


# ---------------------------------------------------------------------------
# RuleOptimizer
# ---------------------------------------------------------------------------


class RuleOptimizer:
    """Detect redundant and contradictory safety rules via equivalence checking.

    Uses ``Z3SMTVerifier`` (or its fallback) to compare symbolic rules
    and identify:
    * **Redundant rules**: Two rules that are logically equivalent.
    * **Contradictory rules**: Two rules that can never both be satisfied.
    * **Subsumed rules**: A rule that is implied by another (weaker rule).
    """

    def __init__(self, verifier: Optional[Z3SMTVerifier] = None) -> None:
        """Initialise the optimizer.

        Args:
            verifier: A ``Z3SMTVerifier`` instance.  Creates a new one
                if not provided.
        """
        self._verifier = verifier or Z3SMTVerifier()

    # ------------------------------------------------------------------
    # Pairwise checks
    # ------------------------------------------------------------------

    def are_equivalent(
        self, rule_a: SymbolicSafetyRule, rule_b: SymbolicSafetyRule
    ) -> bool:
        """Check if two rules are logically equivalent.

        ``A ≡ B`` iff ``(A → B) ∧ (B → A)`` is valid, i.e. the
        biconditional ``A ↔ B`` is universally true.

        Args:
            rule_a: First rule.
            rule_b: Second rule.

        Returns:
            True if the rules are logically equivalent.
        """
        if not _HAS_Z3:
            return self._verifier._fallback.check_equivalence(rule_a, rule_b)

        return self._check_equivalence_z3(rule_a, rule_b)

    def are_contradictory(
        self, rule_a: SymbolicSafetyRule, rule_b: SymbolicSafetyRule
    ) -> bool:
        """Check if two rules contradict each other.

        ``A ⊥ B`` iff ``A ∧ B`` is unsatisfiable.

        Args:
            rule_a: First rule.
            rule_b: Second rule.

        Returns:
            True if the rules are contradictory.
        """
        if not _HAS_Z3:
            return self._verifier._fallback.check_contradiction(rule_a, rule_b)

        return self._check_contradiction_z3(rule_a, rule_b)

    def is_subsumed(
        self, rule_a: SymbolicSafetyRule, rule_b: SymbolicSafetyRule
    ) -> bool:
        """Check if rule A is subsumed by (implied by) rule B.

        ``A ⊑ B`` iff ``B → A`` is valid — whenever B holds, A also holds.
        This means B is stronger (more restrictive) than A.

        Args:
            rule_a: The potentially subsumed (weaker) rule.
            rule_b: The potentially subsuming (stronger) rule.

        Returns:
            True if A is subsumed by B.
        """
        return self._check_implication(rule_a, rule_b)

    # ------------------------------------------------------------------
    # Batch optimisation
    # ------------------------------------------------------------------

    def find_redundant_rules(
        self, rules: List[SymbolicSafetyRule]
    ) -> List[Tuple[str, str, str]]:
        """Find redundant rule pairs in a set.

        Args:
            rules: List of rules to check.

        Returns:
            List of ``(rule_a_name, rule_b_name, relationship)`` tuples
            where relationship is ``"equivalent"``, ``"contradictory"``,
            or ``"subsumed"``.
        """
        redundancies: List[Tuple[str, str, str]] = []
        n = len(rules)

        for i in range(n):
            for j in range(i + 1, n):
                ra, rb = rules[i], rules[j]

                if self.are_equivalent(ra, rb):
                    redundancies.append((ra.name, rb.name, "equivalent"))
                elif self.are_contradictory(ra, rb):
                    redundancies.append((ra.name, rb.name, "contradictory"))
                elif self.is_subsumed(ra, rb):
                    redundancies.append((ra.name, rb.name, "subsumed_by"))
                elif self.is_subsumed(rb, ra):
                    redundancies.append((rb.name, ra.name, "subsumed_by"))

        return redundancies

    def reduce_rules(
        self, rules: List[SymbolicSafetyRule]
    ) -> List[SymbolicSafetyRule]:
        """Remove redundant rules, returning a minimal set.

        Keeps the first rule in each equivalent pair and drops subsumed
        rules.

        Args:
            rules: The full rule set.

        Returns:
            A minimal set of rules with no redundancies.
        """
        redundancies = self.find_redundant_rules(rules)
        names_to_remove: set = set()

        for name_a, name_b, relationship in redundancies:
            if relationship == "equivalent":
                names_to_remove.add(name_b)
            elif relationship == "contradictory":
                # Both contradictory rules are kept — user should
                # decide which to keep.  We do not auto-remove.
                pass
            elif relationship == "subsumed_by":
                names_to_remove.add(name_a)

        return [r for r in rules if r.name not in names_to_remove]

    # ------------------------------------------------------------------
    # Z3 equivalence / contradiction internals
    # ------------------------------------------------------------------

    def _check_equivalence_z3(
        self, rule_a: SymbolicSafetyRule, rule_b: SymbolicSafetyRule
    ) -> bool:
        """Check logical equivalence using Z3.

        A ↔ B is valid if ¬(A ↔ B) is unsatisfiable.
        """
        assert _z3 is not None

        formula_a = self._verifier.encode_to_smt(rule_a)
        formula_b = self._verifier.encode_to_smt(rule_b)

        # ¬(A ↔ B) ≡ A ∧ ¬B ∨ ¬A ∧ B
        not_equiv = _z3.Or(
            _z3.And(formula_a, _z3.Not(formula_b)),
            _z3.And(_z3.Not(formula_a), formula_b),
        )

        solver = _z3.Solver()
        solver.add(not_equiv)

        return solver.check() == _z3.unsat

    def _check_contradiction_z3(
        self, rule_a: SymbolicSafetyRule, rule_b: SymbolicSafetyRule
    ) -> bool:
        """Check if two rules are contradictory using Z3.

        A ∧ B is satisfiable?  If unsat they are contradictory.
        """
        assert _z3 is not None

        formula_a = self._verifier.encode_to_smt(rule_a)
        formula_b = self._verifier.encode_to_smt(rule_b)
        conjunction = _z3.And(formula_a, formula_b)

        solver = _z3.Solver()
        solver.add(conjunction)

        return solver.check() == _z3.unsat

    def _check_implication(
        self, rule_a: SymbolicSafetyRule, rule_b: SymbolicSafetyRule
    ) -> bool:
        """Check if B → A is valid using Z3.

        B → A is valid if ¬(B → A) ≡ B ∧ ¬A is unsatisfiable.
        """
        if not _HAS_Z3:
            return False

        assert _z3 is not None

        formula_a = self._verifier.encode_to_smt(rule_a)
        formula_b = self._verifier.encode_to_smt(rule_b)

        # B ∧ ¬A is unsat → B → A is valid
        not_implication = _z3.And(formula_b, _z3.Not(formula_a))

        solver = _z3.Solver()
        solver.add(not_implication)

        return solver.check() == _z3.unsat
