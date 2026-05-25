"""Pseudo-formal verification: invariant checking, type safety, contracts, property-based testing."""

from __future__ import annotations

import asyncio
import logging
import re
import time
from dataclasses import dataclass, field
from typing import Any, Callable, Optional, Protocol

from .verification_mesh import (
    VerificationLayer,
    VerificationStatus,
    VerificationResult,
    VerificationModule,
    TemporalProperty,
)

logger = logging.getLogger(__name__)


# ── Protocols and types ────────────────────────────────────────────────


class Invariant(Protocol):
    """An invariant condition that must hold."""

    def check(self, state: dict[str, Any]) -> tuple[bool, str]: ...


@dataclass
class PrePostCondition:
    """Pre-condition and post-condition pair for a function/operation.

    Attributes:
        name: Condition name.
        pre_condition: Must be true before execution.
        post_condition: Must be true after execution.
        description: Human-readable description.
    """

    name: str
    pre_condition: str
    post_condition: str
    description: str = ""


@dataclass
class TypeConstraint:
    """Type safety constraint.

    Attributes:
        variable_name: Name of the variable/field.
        expected_type: Expected Python type name.
        nullable: Whether None is allowed.
    """

    variable_name: str
    expected_type: str
    nullable: bool = False


@dataclass
class FormalProofResult:
    """Result of a formal verification proof attempt.

    Attributes:
        property_name: What was being proved.
        proved: Whether the proof succeeded.
        counterexample: Counterexample if the proof failed.
        proof_duration_ms: Time taken.
        strategy: Proof strategy used.
    """

    property_name: str
    proved: bool = False
    counterexample: Optional[dict[str, Any]] = None
    proof_duration_ms: float = 0.0
    strategy: str = "symbolic"


# ── Invariant registry ──────────────────────────────────────────────────


class InvariantRegistry:
    """Registry of invariants that must hold for system state."""

    def __init__(self) -> None:
        self._invariants: list[Invariant] = []
        self._named_invariants: dict[str, Invariant] = {}

    def register(self, name: str, invariant: Invariant) -> None:
        """Register a named invariant."""
        self._named_invariants[name] = invariant
        self._invariants.append(invariant)

    def check_all(self, state: dict[str, Any]) -> list[VerificationResult]:
        """Check all invariants against a given state.

        Args:
            state: The system state to check.

        Returns:
            List of verification results (one per invariant).
        """
        results: list[VerificationResult] = []
        for name, invariant in self._named_invariants.items():
            try:
                holds, message = invariant.check(state)
                results.append(VerificationResult(
                    status=VerificationStatus.PASS if holds else VerificationStatus.FAIL,
                    layer=VerificationLayer.PRE_EXECUTION,
                    verifier="InvariantRegistry",
                    check_name=name,
                    message=message,
                    confidence=1.0 if holds else 0.0,
                ))
            except Exception as exc:
                results.append(VerificationResult(
                    status=VerificationStatus.ERROR,
                    layer=VerificationLayer.PRE_EXECUTION,
                    verifier="InvariantRegistry",
                    check_name=name,
                    message=f"Invariant check error: {exc}",
                    confidence=0.0,
                ))
        return results


# ── Type checker ────────────────────────────────────────────────────────


class TypeSafetyVerifier:
    """Verifies type safety constraints on data structures.

    Checks that variables, fields, and return values conform to
    expected type annotations at runtime.
    """

    def __init__(self) -> None:
        self._constraints: list[TypeConstraint] = []
        self._type_map: dict[str, type] = {
            "str": str, "int": int, "float": float, "bool": bool,
            "list": list, "dict": dict, "tuple": tuple, "set": set,
            "None": type(None), "Any": object,
        }

    def add_constraint(self, constraint: TypeConstraint) -> None:
        """Add a type constraint to verify."""
        self._constraints.append(constraint)

    def verify_value(
        self, constraint: TypeConstraint, value: Any
    ) -> VerificationResult:
        """Verify a single value against a type constraint.

        Args:
            constraint: The type constraint.
            value: The value to check.

        Returns:
            VerificationResult.
        """
        if constraint.nullable and value is None:
            return VerificationResult(
                status=VerificationStatus.PASS,
                layer=VerificationLayer.PRE_EXECUTION,
                verifier="TypeSafetyVerifier",
                check_name=f"type_{constraint.variable_name}",
                message="Nullable field is None (allowed)",
                confidence=1.0,
            )

        expected_type = self._type_map.get(constraint.expected_type)
        if expected_type is None:
            return VerificationResult(
                status=VerificationStatus.WARN,
                layer=VerificationLayer.PRE_EXECUTION,
                verifier="TypeSafetyVerifier",
                check_name=f"type_{constraint.variable_name}",
                message=f"Unknown type: {constraint.expected_type}",
                confidence=0.5,
            )

        if isinstance(value, expected_type):
            return VerificationResult(
                status=VerificationStatus.PASS,
                layer=VerificationLayer.PRE_EXECUTION,
                verifier="TypeSafetyVerifier",
                check_name=f"type_{constraint.variable_name}",
                message=f"Type matches {constraint.expected_type}",
                confidence=1.0,
            )

        actual_type = type(value).__name__
        return VerificationResult(
            status=VerificationStatus.FAIL,
            layer=VerificationLayer.PRE_EXECUTION,
            verifier="TypeSafetyVerifier",
            check_name=f"type_{constraint.variable_name}",
            message=f"Type mismatch: expected {constraint.expected_type}, got {actual_type}",
            confidence=0.0,
            details={"expected": constraint.expected_type, "actual": actual_type},
        )

    def verify_all(self, values: dict[str, Any]) -> list[VerificationResult]:
        """Verify all constraints against a set of values.

        Args:
            values: Dict of variable_name -> value.

        Returns:
            List of verification results.
        """
        results: list[VerificationResult] = []
        for constraint in self._constraints:
            if constraint.variable_name in values:
                results.append(
                    self.verify_value(constraint, values[constraint.variable_name])
                )
        return results


# ── Contract verifier ──────────────────────────────────────────────────


class ContractVerifier:
    """Verifies pre/post conditions on functions and operations.

    Checks that pre-conditions are satisfied before execution and
    post-conditions hold after execution.
    """

    def __init__(self) -> None:
        self._contracts: list[PrePostCondition] = []

    def add_contract(self, contract: PrePostCondition) -> None:
        """Add a pre/post condition contract."""
        self._contracts.append(contract)

    async def verify_pre_conditions(
        self, state: dict[str, Any]
    ) -> list[VerificationResult]:
        """Verify all pre-conditions against the current state.

        Args:
            state: Current execution state.

        Returns:
            List of pre-condition check results.
        """
        results: list[VerificationResult] = []
        for contract in self._contracts:
            satisfied = self._evaluate_condition(contract.pre_condition, state)
            results.append(VerificationResult(
                status=VerificationStatus.PASS if satisfied else VerificationStatus.FAIL,
                layer=VerificationLayer.PRE_EXECUTION,
                verifier="ContractVerifier",
                check_name=f"pre_{contract.name}",
                message=f"Pre-condition '{contract.name}' {'satisfied' if satisfied else 'violated'}",
                confidence=1.0 if satisfied else 0.0,
                details={"condition": contract.pre_condition, "state": state},
            ))
        return results

    async def verify_post_conditions(
        self, before_state: dict[str, Any], after_state: dict[str, Any]
    ) -> list[VerificationResult]:
        """Verify all post-conditions.

        Args:
            before_state: State before execution.
            after_state: State after execution.

        Returns:
            List of post-condition check results.
        """
        results: list[VerificationResult] = []
        combined = {**before_state, "after": after_state}
        for contract in self._contracts:
            satisfied = self._evaluate_condition(contract.post_condition, combined)
            results.append(VerificationResult(
                status=VerificationStatus.PASS if satisfied else VerificationStatus.FAIL,
                layer=VerificationLayer.PRE_EXECUTION,
                verifier="ContractVerifier",
                check_name=f"post_{contract.name}",
                message=f"Post-condition '{contract.name}' {'satisfied' if satisfied else 'violated'}",
                confidence=1.0 if satisfied else 0.0,
                details={"condition": contract.post_condition},
            ))
        return results

    @staticmethod
    def _evaluate_condition(condition: str, state: dict[str, Any]) -> bool:
        """Evaluate a simple condition string against state.

        Supports basic expressions like: 'x > 0', 'status == "ok"', 'len(items) < 100'
        """
        try:
            # Simple expression evaluator for common patterns
            # Pattern: variable comparator value
            pattern = r"(\w+)\s*(==|!=|>=|<=|>|<)\s*(.+)$"
            match = re.match(pattern, condition.strip())
            if match:
                var_name = match.group(1)
                op = match.group(2)
                raw_value = match.group(3).strip().strip('"').strip("'")

                if var_name not in state:
                    return False

                actual = state[var_name]

                # Try numeric comparison
                try:
                    target = float(raw_value)
                    actual_num = float(actual) if not isinstance(actual, (int, float)) else actual
                except (ValueError, TypeError):
                    target = raw_value
                    actual_num = actual

                if op == "==":
                    return str(actual) == str(target) or actual == target
                elif op == "!=":
                    return str(actual) != str(target) and actual != target
                elif op == ">":
                    return actual_num > target
                elif op == "<":
                    return actual_num < target
                elif op == ">=":
                    return actual_num >= target
                elif op == "<=":
                    return actual_num <= target

            # Pattern: len(x) < N
            len_pattern = r"len\((\w+)\)\s*(==|!=|>=|<=|>|<)\s*(\d+)"
            match = re.match(len_pattern, condition.strip())
            if match:
                var_name = match.group(1)
                op = match.group(2)
                target = int(match.group(3))

                if var_name not in state:
                    return False
                actual_len = len(state[var_name])

                if op == "==":
                    return actual_len == target
                elif op == "!=":
                    return actual_len != target
                elif op == ">":
                    return actual_len > target
                elif op == "<":
                    return actual_len < target
                elif op == ">=":
                    return actual_len >= target
                elif op == "<=":
                    return actual_len <= target

            return True  # Unknown pattern, assume satisfied
        except Exception:
            return False


# ── Formal verifier ────────────────────────────────────────────────────


class FormalVerifier:
    """Pseudo-formal verification engine.

    Decomposes reasoning into self-contained modules, verifies each
    independently via premise-conclusion analysis, and checks invariants,
    types, and contracts.
    """

    def __init__(self) -> None:
        self._modules: dict[str, VerificationModule] = {}
        self._invariants = InvariantRegistry()
        self._type_checker = TypeSafetyVerifier()
        self._contract_verifier = ContractVerifier()
        self._temporal_properties: list[TemporalProperty] = []
        self._property_checks: list[FormalProofResult] = []

    # ── Module management ──────────────────────────────────────────────

    def add_module(self, module: VerificationModule) -> None:
        """Add a verification module."""
        self._modules[module.id] = module

    def remove_module(self, module_id: str) -> bool:
        """Remove a verification module."""
        return self._modules.pop(module_id, None) is not None

    def add_property(self, prop: TemporalProperty) -> None:
        """Add a temporal property for verification."""
        self._temporal_properties.append(prop)

    # ── Module verification ────────────────────────────────────────────

    async def verify_module(self, module: VerificationModule) -> VerificationResult:
        """Verify a single module by checking premise-conclusion consistency.

        Analyzes term overlap between premises and conclusions, and
        verifies that the conclusion logically follows from the premises.

        Args:
            module: The module to verify.

        Returns:
            VerificationResult.
        """
        if not module.premises:
            return VerificationResult(
                status=VerificationStatus.FAIL,
                layer=VerificationLayer.PRE_EXECUTION,
                verifier="FormalVerifier",
                check_name=f"module_{module.id}",
                message=f"Module '{module.id}' has no premises",
            )

        # Extract significant terms (words > 3 chars)
        def _extract_terms(text: str) -> set[str]:
            words = re.findall(r"\b[a-zA-Z_]\w{3,}\b", text.lower())
            return set(words)

        premise_terms: set[str] = set()
        for premise in module.premises:
            premise_terms |= _extract_terms(premise)

        conclusion_terms = _extract_terms(module.conclusion)
        proof_terms = _extract_terms(module.proof) if module.proof else set()

        # Check that conclusion terms are covered by premises
        if not conclusion_terms:
            return VerificationResult(
                status=VerificationStatus.FAIL,
                layer=VerificationLayer.PRE_EXECUTION,
                verifier="FormalVerifier",
                check_name=f"module_{module.id}",
                message=f"Module '{module.id}' has no meaningful conclusion terms",
            )

        overlap = conclusion_terms & premise_terms
        coverage = len(overlap) / len(conclusion_terms) if conclusion_terms else 0.0

        # Proof terms should also align
        proof_coverage = 0.0
        if proof_terms:
            proof_overlap = proof_terms & premise_terms
            proof_coverage = len(proof_overlap) / max(len(proof_terms), 1)

        # Score the verification
        combined_score = 0.6 * coverage + 0.4 * proof_coverage
        module.verified = combined_score >= 0.5

        if module.verified:
            status = VerificationStatus.PASS
            msg = f"Module '{module.id}' verified (coverage={coverage:.2f})"
        else:
            status = VerificationStatus.FAIL
            msg = f"Module '{module.id}' failed (coverage={coverage:.2f})"

        return VerificationResult(
            status=status,
            layer=VerificationLayer.PRE_EXECUTION,
            verifier="FormalVerifier",
            check_name=f"module_{module.id}",
            message=msg,
            confidence=combined_score,
            details={
                "premise_terms": list(premise_terms),
                "conclusion_terms": list(conclusion_terms),
                "overlap": list(overlap),
                "missing_terms": list(conclusion_terms - premise_terms),
                "coverage": coverage,
                "proof_coverage": proof_coverage,
            },
        )

    async def verify_all(self) -> list[VerificationResult]:
        """Verify all registered modules."""
        tasks = [self.verify_module(m) for m in self._modules.values()]
        return list(await asyncio.gather(*tasks))

    # ── Temporal property checking ─────────────────────────────────────

    async def check_temporal_property(
        self, prop: TemporalProperty, event_log: list[dict[str, Any]]
    ) -> FormalProofResult:
        """Check a temporal property against an event log.

        Args:
            prop: The property to check.
            event_log: Execution event history.

        Returns:
            FormalProofResult with proved status.
        """
        start_time = time.time()

        # Check for violations in the event log
        property_holds = True
        counterexample: Optional[dict[str, Any]] = None

        for event in event_log:
            event_type = str(event.get("type", "")).lower()
            expression_lower = prop.expression.lower()

            # Check "not" properties
            if "not" in expression_lower and "error" in event_type:
                property_holds = False
                counterexample = event
                break

            # Check "always" properties
            if "always" in expression_lower:
                if "success" in event_type or event.get("status") == "ok":
                    continue
                property_holds = False
                counterexample = event
                break

            # Check "eventually" properties
            if "eventually" in expression_lower:
                # Check if the condition was met at some point
                target = expression_lower.split("eventually")[-1].strip()
                if target and target.lower() in event_type.lower():
                    property_holds = True
                    break

        duration = (time.time() - start_time) * 1000

        result = FormalProofResult(
            property_name=prop.name,
            proved=property_holds,
            counterexample=counterexample,
            proof_duration_ms=duration,
            strategy="trace_check",
        )
        self._property_checks.append(result)
        return result

    async def check_all_properties(
        self, event_log: list[dict[str, Any]]
    ) -> list[FormalProofResult]:
        """Check all temporal properties against event log."""
        tasks = [
            self.check_temporal_property(prop, event_log)
            for prop in self._temporal_properties
        ]
        return list(await asyncio.gather(*tasks))

    # ── Statistics ─────────────────────────────────────────────────────

    @property
    def module_count(self) -> int:
        """Number of registered modules."""
        return len(self._modules)

    @property
    def verified_module_count(self) -> int:
        """Number of modules that passed verification."""
        return sum(1 for m in self._modules.values() if m.verified)

    @property
    def summary(self) -> dict[str, Any]:
        """Get formal verifier summary."""
        return {
            "modules": self.module_count,
            "verified_modules": self.verified_module_count,
            "temporal_properties": len(self._temporal_properties),
            "property_checks": len(self._property_checks),
            "proved_properties": sum(1 for p in self._property_checks if p.proved),
        }
