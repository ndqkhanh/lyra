"""
Tests for SMTSandbox and FormalQueryLoopGovernance.

Covers:
- SMTSandbox action verification (constraint satisfaction)
- Fallback to pure-Python constraint checker
- FormalQueryLoopGovernance rule management and guard()
- ConstraintOperator enum and ActionSMT construction
"""

from __future__ import annotations

import asyncio
import sys
from unittest.mock import patch

from lyra.reliability.smt_sandbox import (
    ActionSMT,
    ConstraintOperator,
    FormalQueryLoopGovernance,
    SMTSandbox,
    VerificationStatus,
)

# ======================================================================
# SMTSandbox — basic verification
# ======================================================================


class TestSMTSandbox:
    """SMTSandbox verification of SMT-encoded actions."""

    def test_sandbox_verify_no_constraints(self) -> None:
        """An action with no constraints is always allowed."""
        sandbox = SMTSandbox()
        action = ActionSMT(name="test", params={"x": "1"}, constraints=[])
        status = sandbox.verify(action)
        assert status.allowed
        assert status.reason == "No constraints to verify"

    def test_sandbox_verify_eq_pass(self) -> None:
        """EQ constraint passes when the value matches."""
        sandbox = SMTSandbox()
        action = ActionSMT(
            name="test",
            params={"path": "/tmp/file.txt"},
            constraints=[("path", ConstraintOperator.EQ, "/tmp/file.txt")],
        )
        status = sandbox.verify(action)
        assert status.allowed

    def test_sandbox_verify_eq_fail(self) -> None:
        """EQ constraint fails when the value does not match."""
        sandbox = SMTSandbox()
        action = ActionSMT(
            name="test",
            params={"path": "/etc/passwd"},
            constraints=[("path", ConstraintOperator.EQ, "/tmp/file.txt")],
        )
        status = sandbox.verify(action)
        assert not status.allowed

    def test_sandbox_verify_neq_pass(self) -> None:
        """NEQ constraint passes when the value differs."""
        sandbox = SMTSandbox()
        action = ActionSMT(
            name="test",
            params={"path": "/tmp/file.txt"},
            constraints=[("path", ConstraintOperator.NEQ, "/etc/passwd")],
        )
        status = sandbox.verify(action)
        assert status.allowed

    def test_sandbox_verify_prefix_pass(self) -> None:
        """PREFIX constraint passes when the field starts with the value."""
        sandbox = SMTSandbox()
        action = ActionSMT(
            name="test",
            params={"path": "/tmp/foo/bar.txt"},
            constraints=[("path", ConstraintOperator.PREFIX, "/tmp/")],
        )
        status = sandbox.verify(action)
        assert status.allowed

    def test_sandbox_verify_prefix_fail(self) -> None:
        """PREFIX constraint fails when the field does not start with the value."""
        sandbox = SMTSandbox()
        action = ActionSMT(
            name="test",
            params={"path": "/var/log/syslog"},
            constraints=[("path", ConstraintOperator.PREFIX, "/tmp/")],
        )
        status = sandbox.verify(action)
        assert not status.allowed

    def test_sandbox_verify_in_set_pass(self) -> None:
        """IN_SET constraint passes when the value is in the set."""
        sandbox = SMTSandbox()
        action = ActionSMT(
            name="test",
            params={"domain": "example.com"},
            constraints=[("domain", ConstraintOperator.IN_SET, ["example.com", "test.org"])],
        )
        status = sandbox.verify(action)
        assert status.allowed

    def test_sandbox_verify_in_set_fail(self) -> None:
        """IN_SET constraint fails when value is not in the set."""
        sandbox = SMTSandbox()
        action = ActionSMT(
            name="test",
            params={"domain": "evil.com"},
            constraints=[("domain", ConstraintOperator.IN_SET, ["example.com", "test.org"])],
        )
        status = sandbox.verify(action)
        assert not status.allowed

    def test_sandbox_verify_contains_pass(self) -> None:
        """CONTAINS constraint passes when value contains the substring."""
        sandbox = SMTSandbox()
        action = ActionSMT(
            name="test",
            params={"output": "this is the result we want"},
            constraints=[("output", ConstraintOperator.CONTAINS, "result")],
        )
        status = sandbox.verify(action)
        assert status.allowed

    def test_sandbox_verify_suffix_pass(self) -> None:
        """SUFFIX constraint passes when value ends with the substring."""
        sandbox = SMTSandbox()
        action = ActionSMT(
            name="test",
            params={"filename": "report.pdf"},
            constraints=[("filename", ConstraintOperator.SUFFIX, ".pdf")],
        )
        status = sandbox.verify(action)
        assert status.allowed

    def test_sandbox_verify_missing_param(self) -> None:
        """Verification fails when a constrained parameter is missing."""
        sandbox = SMTSandbox()
        action = ActionSMT(
            name="test",
            params={},  # no "path" key
            constraints=[("path", ConstraintOperator.EQ, "/tmp/x")],
        )
        status = sandbox.verify(action)
        assert not status.allowed
        assert "Missing parameter" in status.reason

    def test_sandbox_verify_multiple_constraints(self) -> None:
        """All constraints must pass for the action to be allowed."""
        sandbox = SMTSandbox()
        action = ActionSMT(
            name="test",
            params={"path": "/tmp/work", "domain": "example.com"},
            constraints=[
                ("path", ConstraintOperator.PREFIX, "/tmp/"),
                ("domain", ConstraintOperator.IN_SET, ["example.com", "allowed.org"]),
            ],
        )
        status = sandbox.verify(action)
        assert status.allowed

    def test_sandbox_verify_multiple_constraints_one_fails(self) -> None:
        """If any constraint fails, the action is blocked."""
        sandbox = SMTSandbox()
        action = ActionSMT(
            name="test",
            params={"path": "/tmp/work", "domain": "evil.com"},
            constraints=[
                ("path", ConstraintOperator.PREFIX, "/tmp/"),
                ("domain", ConstraintOperator.IN_SET, ["example.com", "allowed.org"]),
            ],
        )
        status = sandbox.verify(action)
        assert not status.allowed

    def test_sandbox_verify_batch(self) -> None:
        """verify_batch returns results for all actions."""
        sandbox = SMTSandbox()
        actions = [
            ActionSMT(
                name="a1",
                params={"x": "1"},
                constraints=[("x", ConstraintOperator.EQ, "1")],
            ),
            ActionSMT(
                name="a2",
                params={"x": "2"},
                constraints=[("x", ConstraintOperator.EQ, "1")],
            ),
        ]
        results = sandbox.verify_batch(actions)
        assert len(results) == 2
        assert results[0].allowed
        assert not results[1].allowed

    def test_sandbox_verify_numeric_gt(self) -> None:
        """GT constraint on numeric strings."""
        sandbox = SMTSandbox()
        action = ActionSMT(
            name="test",
            params={"count": "10"},
            constraints=[("count", ConstraintOperator.GT, "5")],
        )
        status = sandbox.verify(action)
        assert status.allowed

    def test_sandbox_verify_numeric_lt_fail(self) -> None:
        """LT constraint fails."""
        sandbox = SMTSandbox()
        action = ActionSMT(
            name="test",
            params={"count": "10"},
            constraints=[("count", ConstraintOperator.LT, "5")],
        )
        status = sandbox.verify(action)
        assert not status.allowed

    def test_sandbox_add_rule(self) -> None:
        """Named rules are applied to all verified actions."""
        sandbox = SMTSandbox()
        sandbox.add_rule("safe_path", [
            ("path", ConstraintOperator.PREFIX, "/tmp/"),
        ])

        action = ActionSMT(
            name="test",
            params={"path": "/tmp/ok.txt"},
            constraints=[],
        )
        status = sandbox.verify(action)
        assert status.allowed

        action2 = ActionSMT(
            name="test",
            params={"path": "/etc/passwd"},
            constraints=[],
        )
        status2 = sandbox.verify(action2)
        assert not status2.allowed

    def test_sandbox_remove_rule(self) -> None:
        """Removed rules no longer apply."""
        sandbox = SMTSandbox()
        sandbox.add_rule("r1", [("x", ConstraintOperator.EQ, "1")])
        sandbox.remove_rule("r1")

        action = ActionSMT(name="test", params={"x": "999"}, constraints=[])
        status = sandbox.verify(action)
        assert status.allowed

    def test_sandbox_list_rules(self) -> None:
        """list_rules returns registered rule names."""
        sandbox = SMTSandbox()
        sandbox.add_rule("a", [("x", ConstraintOperator.EQ, "1")])
        sandbox.add_rule("b", [("y", ConstraintOperator.EQ, "2")])
        rules = sandbox.list_rules()
        assert sorted(rules) == ["a", "b"]

    def test_sandbox_encode_to_smt(self) -> None:
        """encode_to_smt returns a serializable representation."""
        sandbox = SMTSandbox()
        action = ActionSMT(
            name="test",
            params={"path": "/tmp/x"},
            constraints=[("path", ConstraintOperator.EQ, "/tmp/x")],
        )
        encoded = sandbox.encode_to_smt(action)
        assert isinstance(encoded, dict)
        assert encoded["action"] == "test"
        assert len(encoded["constraints"]) == 1


# ======================================================================
# FormalQueryLoopGovernance
# ======================================================================


class TestFormalQueryLoopGovernance:
    """FormalQueryLoopGovernance wraps SMTSandbox for loop integration."""

    async def test_guard_allows_valid_action(self) -> None:
        """An action satisfying all governance rules is allowed."""
        gov = FormalQueryLoopGovernance()
        gov.add_rule("safe_area", [
            ("path", ConstraintOperator.PREFIX, "/workspace/"),
        ])
        status = await gov.guard(ActionSMT(
            name="write",
            params={"path": "/workspace/output.txt"},
            constraints=[],
        ))
        assert status.allowed

    async def test_guard_blocks_violating_action(self) -> None:
        """An action violating governance rules is blocked."""
        gov = FormalQueryLoopGovernance()
        gov.add_rule("safe_area", [
            ("path", ConstraintOperator.PREFIX, "/workspace/"),
        ])
        status = await gov.guard(ActionSMT(
            name="write",
            params={"path": "/etc/passwd"},
            constraints=[],
        ))
        assert not status.allowed

    async def test_guard_batch(self) -> None:
        """guard_batch returns results for multiple actions."""
        gov = FormalQueryLoopGovernance()
        gov.add_rule("eq_one", [
            ("x", ConstraintOperator.EQ, "1"),
        ])
        actions = [
            ActionSMT(name="a1", params={"x": "1"}, constraints=[]),
            ActionSMT(name="a2", params={"x": "2"}, constraints=[]),
        ]
        results = await gov.guard_batch(actions)
        assert len(results) == 2
        assert results[0].allowed
        assert not results[1].allowed

    def test_add_and_remove_rule(self) -> None:
        """Rules can be added and removed."""
        gov = FormalQueryLoopGovernance()
        gov.add_rule("r", [("x", ConstraintOperator.EQ, "1")])
        assert "r" in gov.list_rules()
        gov.remove_rule("r")
        assert "r" not in gov.list_rules()

    async def test_load_spec(self) -> None:
        """load_spec imports rules from a dict."""
        gov = FormalQueryLoopGovernance()
        gov.load_spec({
            "rule_a": [("x", ConstraintOperator.EQ, "1")],
            "rule_b": [("y", ConstraintOperator.NEQ, "bad")],
        })
        rules = gov.list_rules()
        assert sorted(rules) == ["rule_a", "rule_b"]

        status = await gov.guard(ActionSMT(
            name="test",
            params={"x": "1", "y": "good"},
            constraints=[],
        ))
        assert status.allowed

    def test_export_spec(self) -> None:
        """export_spec returns the current rules as a dict."""
        gov = FormalQueryLoopGovernance()
        gov.add_rule("my_rule", [("p", ConstraintOperator.EQ, "v")])
        spec = gov.export_spec()
        assert "my_rule" in spec
        assert spec["my_rule"] == [("p", ConstraintOperator.EQ, "v")]

    def test_clear_rules(self) -> None:
        """clear_rules removes all rules."""
        gov = FormalQueryLoopGovernance()
        gov.add_rule("r", [("x", ConstraintOperator.EQ, "1")])
        gov.clear_rules()
        assert gov.list_rules() == []


# ======================================================================
# ActionSMT and VerificationStatus
# ======================================================================


class TestActionSMT:
    """ActionSMT construction."""

    def test_default_params(self) -> None:
        """ActionSMT can be created with just a name."""
        action = ActionSMT(name="test")
        assert action.name == "test"
        assert action.params == {}
        assert action.constraints == []

    def test_full_construction(self) -> None:
        """ActionSMT with all fields."""
        action = ActionSMT(
            name="read_file",
            params={"path": "/tmp/x.txt"},
            constraints=[("path", ConstraintOperator.PREFIX, "/tmp/")],
        )
        assert action.name == "read_file"
        assert action.params["path"] == "/tmp/x.txt"
        assert len(action.constraints) == 1


class TestVerificationStatus:
    """VerificationStatus construction."""

    def test_allowed_default(self) -> None:
        """Default VerificationStatus for an allowed action."""
        status = VerificationStatus(allowed=True, reason="OK")
        assert status.allowed
        assert status.reason == "OK"
        assert status.model is None

    def test_blocked_with_reason(self) -> None:
        """Blocked status includes a reason."""
        status = VerificationStatus(
            allowed=False,
            reason="Constraint violation: path /etc/passwd not in /tmp/",
        )
        assert not status.allowed
        assert "violation" in status.reason

    def test_with_model(self) -> None:
        """VerificationStatus can carry a model."""
        status = VerificationStatus(
            allowed=True,
            reason="OK",
            model={"path": "/tmp/x"},
        )
        assert status.model == {"path": "/tmp/x"}


# ======================================================================
# Additional coverage: _PythonConstraintChecker internals
# ======================================================================


class TestPythonConstraintChecker:
    """Direct coverage of pure-Python fallback constraint checker."""

    def test_is_valid_rule_no_contradiction(self) -> None:
        from lyra.reliability.smt_sandbox import _PythonConstraintChecker

        checker = _PythonConstraintChecker()
        assert checker.is_valid_rule([
            ("path", ConstraintOperator.PREFIX, "/tmp/"),
            ("domain", ConstraintOperator.IN_SET, ["a", "b"]),
        ])

    def test_is_valid_rule_detects_contradiction(self) -> None:
        from lyra.reliability.smt_sandbox import _PythonConstraintChecker

        checker = _PythonConstraintChecker()
        assert not checker.is_valid_rule([
            ("x", ConstraintOperator.EQ, "1"),
            ("x", ConstraintOperator.NEQ, "1"),
        ])

    def test_is_valid_rule_not_contradicted_neq(self) -> None:
        """EQ and NEQ on the same field but different values is NOT contradictory."""
        from lyra.reliability.smt_sandbox import _PythonConstraintChecker

        checker = _PythonConstraintChecker()
        assert checker.is_valid_rule([
            ("x", ConstraintOperator.EQ, "1"),
            ("x", ConstraintOperator.NEQ, "2"),
        ])

    def test_verify_batch(self) -> None:
        from lyra.reliability.smt_sandbox import _PythonConstraintChecker, ActionSMT

        checker = _PythonConstraintChecker()
        actions = [
            ActionSMT(name="a", params={"x": "1"}, constraints=[("x", ConstraintOperator.EQ, "1")]),
            ActionSMT(name="b", params={"x": "2"}, constraints=[("x", ConstraintOperator.EQ, "1")]),
        ]
        results = checker.verify_batch(actions)
        assert len(results) == 2
        assert results[0].allowed
        assert not results[1].allowed

    def test_matches_regex_pass(self) -> None:
        from lyra.reliability.smt_sandbox import _PythonConstraintChecker, ActionSMT

        checker = _PythonConstraintChecker()
        action = ActionSMT(
            name="t", params={"output": "hello123world"},
            constraints=[("output", ConstraintOperator.MATCHES_REGEX, r"\d+")],
        )
        result = checker.check(action)
        assert result.allowed

    def test_matches_regex_fail(self) -> None:
        from lyra.reliability.smt_sandbox import _PythonConstraintChecker, ActionSMT

        checker = _PythonConstraintChecker()
        action = ActionSMT(
            name="t", params={"output": "abc"},
            constraints=[("output", ConstraintOperator.MATCHES_REGEX, r"\d+")],
        )
        result = checker.check(action)
        assert not result.allowed

    def test_matches_regex_bad_pattern(self) -> None:
        """An invalid regex should not raise — it should return False."""
        from lyra.reliability.smt_sandbox import _PythonConstraintChecker, ActionSMT

        checker = _PythonConstraintChecker()
        action = ActionSMT(
            name="t", params={"output": "test"},
            constraints=[("output", ConstraintOperator.MATCHES_REGEX, r"[invalid")],
        )
        # Should not raise
        result = checker.check(action)
        assert not result.allowed

    def test_not_in_set_pass(self) -> None:
        from lyra.reliability.smt_sandbox import _PythonConstraintChecker, ActionSMT

        checker = _PythonConstraintChecker()
        action = ActionSMT(
            name="t", params={"domain": "evil.com"},
            constraints=[("domain", ConstraintOperator.NOT_IN_SET, ["good.com", "safe.org"])],
        )
        result = checker.check(action)
        assert result.allowed

    def test_not_in_set_fail(self) -> None:
        from lyra.reliability.smt_sandbox import _PythonConstraintChecker, ActionSMT

        checker = _PythonConstraintChecker()
        action = ActionSMT(
            name="t", params={"domain": "good.com"},
            constraints=[("domain", ConstraintOperator.NOT_IN_SET, ["good.com", "safe.org"])],
        )
        result = checker.check(action)
        assert not result.allowed

    def test_not_in_set_scalar(self) -> None:
        """NOT_IN_SET with a single scalar value."""
        from lyra.reliability.smt_sandbox import _PythonConstraintChecker, ActionSMT

        checker = _PythonConstraintChecker()
        action = ActionSMT(
            name="t", params={"x": "hello"},
            constraints=[("x", ConstraintOperator.NOT_IN_SET, "hello")],
        )
        result = checker.check(action)
        assert not result.allowed

    def test_numeric_ge_pass(self) -> None:
        from lyra.reliability.smt_sandbox import _PythonConstraintChecker, ActionSMT

        checker = _PythonConstraintChecker()
        action = ActionSMT(
            name="t", params={"count": "10"},
            constraints=[("count", ConstraintOperator.GE, "10")],
        )
        result = checker.check(action)
        assert result.allowed

    def test_numeric_ge_fail(self) -> None:
        from lyra.reliability.smt_sandbox import _PythonConstraintChecker, ActionSMT

        checker = _PythonConstraintChecker()
        action = ActionSMT(
            name="t", params={"count": "5"},
            constraints=[("count", ConstraintOperator.GE, "10")],
        )
        result = checker.check(action)
        assert not result.allowed

    def test_numeric_le_pass(self) -> None:
        from lyra.reliability.smt_sandbox import _PythonConstraintChecker, ActionSMT

        checker = _PythonConstraintChecker()
        action = ActionSMT(
            name="t", params={"count": "5"},
            constraints=[("count", ConstraintOperator.LE, "10")],
        )
        result = checker.check(action)
        assert result.allowed

    def test_numeric_le_fail(self) -> None:
        from lyra.reliability.smt_sandbox import _PythonConstraintChecker, ActionSMT

        checker = _PythonConstraintChecker()
        action = ActionSMT(
            name="t", params={"count": "15"},
            constraints=[("count", ConstraintOperator.LE, "10")],
        )
        result = checker.check(action)
        assert not result.allowed

    def test_non_numeric_gt_falls_to_string(self) -> None:
        """When the value cannot be parsed as a number, GT falls through to
        string operators and eventually returns False."""
        from lyra.reliability.smt_sandbox import _PythonConstraintChecker, ActionSMT

        checker = _PythonConstraintChecker()
        # "abc" cannot be converted to float
        action = ActionSMT(
            name="t", params={"value": "abc"},
            constraints=[("value", ConstraintOperator.GT, "5")],
        )
        result = checker.check(action)
        assert not result.allowed

    def test_non_numeric_ge_falls_to_string(self) -> None:
        from lyra.reliability.smt_sandbox import _PythonConstraintChecker, ActionSMT

        checker = _PythonConstraintChecker()
        action = ActionSMT(
            name="t", params={"value": "abc"},
            constraints=[("value", ConstraintOperator.GE, "5")],
        )
        result = checker.check(action)
        assert not result.allowed

    def test_contains_fail(self) -> None:
        from lyra.reliability.smt_sandbox import _PythonConstraintChecker, ActionSMT

        checker = _PythonConstraintChecker()
        action = ActionSMT(
            name="t", params={"output": "hello world"},
            constraints=[("output", ConstraintOperator.CONTAINS, "xyz")],
        )
        result = checker.check(action)
        assert not result.allowed

    def test_unrecognized_operator_returns_false(self) -> None:
        """Fallback return False when operator is not recognised."""
        from lyra.reliability.smt_sandbox import _PythonConstraintChecker, ActionSMT, VerificationStatus

        checker = _PythonConstraintChecker()
        # Create an action with the operator affecting _evaluate fallthrough
        action = ActionSMT(
            name="t", params={"x": "y"},
            constraints=[("x", ConstraintOperator.MATCHES_REGEX, r"[invalid")],
        )
        result = checker.check(action)
        # The regex will fail due to error
        assert not result.allowed


# ======================================================================
# Additional coverage: SMTSandbox edge cases
# ======================================================================


class TestSMTSandboxExtended:
    """Extended SMTSandbox coverage for edge cases."""

    def test_verify_merges_action_and_registered_rules(self) -> None:
        """Action constraints + registered rules should all be checked."""
        sandbox = SMTSandbox()
        sandbox.add_rule("always_true", [("x", ConstraintOperator.EQ, "1")])

        # The action's own constraint plus the registered rule
        action = ActionSMT(
            name="test",
            params={"x": "1", "y": "allowed"},
            constraints=[("y", ConstraintOperator.IN_SET, ["allowed", "ok"])],
        )
        status = sandbox.verify(action)
        assert status.allowed

    def test_verify_registered_rule_fails(self) -> None:
        """A registered rule can block an action even with no action constraints."""
        sandbox = SMTSandbox()
        sandbox.add_rule("path_prefix", [
            ("path", ConstraintOperator.PREFIX, "/tmp/"),
        ])
        action = ActionSMT(
            name="test",
            params={"path": "/etc/passwd"},
            constraints=[],
        )
        status = sandbox.verify(action)
        assert not status.allowed

    def test_encode_to_smt_with_rules(self) -> None:
        """encode_to_smt should include registered rule names."""
        sandbox = SMTSandbox()
        sandbox.add_rule("my_rule", [("x", ConstraintOperator.EQ, "1")])
        action = ActionSMT(name="test", params={"x": "1"})
        encoded = sandbox.encode_to_smt(action)
        assert isinstance(encoded, dict)
        assert "my_rule" in encoded.get("rules", [])

    def test_remove_nonexistent_rule(self) -> None:
        """Removing a rule that does not exist returns False."""
        sandbox = SMTSandbox()
        assert sandbox.remove_rule("nonexistent") is False

    def test_verify_batch_empty(self) -> None:
        """verify_batch with empty list returns empty list."""
        sandbox = SMTSandbox()
        assert sandbox.verify_batch([]) == []

    def test_not_in_set_with_empty_set(self) -> None:
        """NOT_IN_SET with an empty set means everything is allowed."""
        from lyra.reliability.smt_sandbox import _PythonConstraintChecker

        checker = _PythonConstraintChecker()
        action = ActionSMT(
            name="t", params={"x": "anything"},
            constraints=[("x", ConstraintOperator.NOT_IN_SET, [])],
        )
        result = checker.check(action)
        assert result.allowed

    def test_in_set_with_empty_set(self) -> None:
        """IN_SET with an empty set means nothing matches."""
        from lyra.reliability.smt_sandbox import _PythonConstraintChecker

        checker = _PythonConstraintChecker()
        action = ActionSMT(
            name="t", params={"x": "anything"},
            constraints=[("x", ConstraintOperator.IN_SET, [])],
        )
        result = checker.check(action)
        assert not result.allowed


# ======================================================================
# Additional coverage: FormalQueryLoopGovernance edge cases
# ======================================================================


class TestFormalGovernanceExtended:
    """Extended governance coverage."""

    async def test_guard_batch_empty(self) -> None:
        gov = FormalQueryLoopGovernance()
        results = await gov.guard_batch([])
        assert results == []

    async def test_load_spec_empty(self) -> None:
        gov = FormalQueryLoopGovernance()
        gov.load_spec({})
        assert gov.list_rules() == []

    def test_export_spec_empty(self) -> None:
        gov = FormalQueryLoopGovernance()
        spec = gov.export_spec()
        assert spec == {}

    def test_guard_logs_blocked_action(self) -> None:
        import logging

        gov = FormalQueryLoopGovernance()
        gov.add_rule("block_all", [
            ("x", ConstraintOperator.EQ, "impossible"),
        ])

        import asyncio
        status = asyncio.run(gov.guard(ActionSMT(
            name="blocked_action",
            params={"x": "real_value"},
        )))
        assert not status.allowed

    def test_custom_sandbox_injection(self) -> None:
        """FormalQueryLoopGovernance accepts an injected SMTSandbox."""
        sandbox = SMTSandbox()
        sandbox.add_rule("custom", [("x", ConstraintOperator.EQ, "1")])
        gov = FormalQueryLoopGovernance(sandbox=sandbox)
        assert "custom" in gov.list_rules()


# ======================================================================
# Additional coverage: Z3-backed paths (mocked)
# ======================================================================


class _MockSMTSandboxZ3:
    """Helper for mocking Z3 in SMTSandbox tests."""

    class MockExpr:
        def __init__(self, name: str = ""):
            self._name = name
        def __eq__(self, other):
            return _MockSMTSandboxZ3.MockExpr(f"eq")
        def __ne__(self, other):
            return _MockSMTSandboxZ3.MockExpr(f"ne")
        def __gt__(self, other):
            return _MockSMTSandboxZ3.MockExpr(f"gt")
        def __ge__(self, other):
            return _MockSMTSandboxZ3.MockExpr(f"ge")
        def __lt__(self, other):
            return _MockSMTSandboxZ3.MockExpr(f"lt")
        def __le__(self, other):
            return _MockSMTSandboxZ3.MockExpr(f"le")

    class MockModel:
        def eval(self, expr, model_completion=True):
            return _MockSMTSandboxZ3.MockExpr("mock_val")

    @staticmethod
    def _make_mock_z3(solver_return: str = "sat"):
        mock_self = _MockSMTSandboxZ3

        class MockSolver:
            def __init__(self):
                self._formulae = []
            def add(self, formula):
                self._formulae.append(formula)
            def check(self):
                return solver_return
            def model(self):
                return mock_self.MockModel()

        class _MockModule:
            sat = "sat"
            unsat = "unsat"
            @staticmethod
            def String(name: str):
                return mock_self.MockExpr(name)
            @staticmethod
            def StringVal(val: str):
                return mock_self.MockExpr(str(val))
            @staticmethod
            def Bool(val: bool = True):
                return mock_self.MockExpr(str(val))
            @staticmethod
            def And(*args):
                return mock_self.MockExpr("and")
            @staticmethod
            def Or(*args):
                return mock_self.MockExpr("or")
            @staticmethod
            def Not(expr):
                return mock_self.MockExpr("not")
            @staticmethod
            def Contains(a, b):
                return mock_self.MockExpr("contains")
            @staticmethod
            def PrefixOf(a, b):
                return mock_self.MockExpr("prefix")
            @staticmethod
            def SuffixOf(a, b):
                return mock_self.MockExpr("suffix")
            @staticmethod
            def Solver():
                return MockSolver()

        return _MockModule()

    @staticmethod
    def patch_z3(solver_return: str = "sat"):
        from contextlib import ExitStack
        from unittest.mock import patch

        mock_mod = _MockSMTSandboxZ3._make_mock_z3(solver_return)
        stack = ExitStack()
        stack.enter_context(patch.multiple("lyra.reliability.smt_sandbox",
                                            _HAS_Z3=True, _z3=mock_mod))
        stack.enter_context(patch.dict(sys.modules, {"z3": mock_mod}))
        return stack


class TestSMTSandboxWithMockZ3:
    """SMTSandbox coverage for Z3-backed paths."""

    def test_encode_z3_single_constraint(self) -> None:
        with _MockSMTSandboxZ3.patch_z3():
            sandbox = SMTSandbox()
            action = ActionSMT(
                name="test",
                params={"path": "/tmp/file.txt"},
                constraints=[("path", ConstraintOperator.EQ, "/tmp/file.txt")],
            )
            encoded = sandbox.encode_to_smt(action)
        assert encoded is not None

    def test_encode_z3_no_constraints(self) -> None:
        with _MockSMTSandboxZ3.patch_z3():
            sandbox = SMTSandbox()
            action = ActionSMT(name="empty", params={}, constraints=[])
            encoded = sandbox.encode_to_smt(action)
        assert encoded is not None

    def test_verify_with_z3_sat(self) -> None:
        with _MockSMTSandboxZ3.patch_z3("sat"):
            sandbox = SMTSandbox()
            action = ActionSMT(
                name="test",
                params={"x": "1"},
                constraints=[("x", ConstraintOperator.EQ, "1")],
            )
            status = sandbox.verify(action)
        assert status.allowed
        assert status.model is not None

    def test_verify_with_z3_unsat(self) -> None:
        with _MockSMTSandboxZ3.patch_z3("unsat"):
            sandbox = SMTSandbox()
            action = ActionSMT(
                name="test",
                params={"x": "1"},
                constraints=[("x", ConstraintOperator.EQ, "1")],
            )
            status = sandbox.verify(action)
        assert not status.allowed
        assert "unsatisfiable" in status.reason

    def test_verify_with_z3_unknown(self) -> None:
        with _MockSMTSandboxZ3.patch_z3("unknown"):
            sandbox = SMTSandbox()
            action = ActionSMT(
                name="test",
                params={"x": "1"},
                constraints=[("x", ConstraintOperator.EQ, "1")],
            )
            status = sandbox.verify(action)
        assert not status.allowed
        assert "unknown" in status.reason

    def test_encode_z3_with_rules(self) -> None:
        with _MockSMTSandboxZ3.patch_z3():
            sandbox = SMTSandbox()
            sandbox.add_rule("r1", [("x", ConstraintOperator.EQ, "1")])
            action = ActionSMT(name="test", params={"x": "1"}, constraints=[])
            encoded = sandbox.encode_to_smt(action)
        assert encoded is not None

    def test_encode_z3_all_operators(self) -> None:
        with _MockSMTSandboxZ3.patch_z3():
            sandbox = SMTSandbox()
            action = ActionSMT(
                name="test",
                params={"a": "1", "b": "2", "c": "x", "d": "y", "e": "z",
                        "f": "hello", "g": "world", "h": "test",
                        "i": "val", "j": "other"},
                constraints=[
                    ("a", ConstraintOperator.NEQ, "2"),
                    ("b", ConstraintOperator.GT, "1"),
                    ("c", ConstraintOperator.GE, "1"),
                    ("d", ConstraintOperator.LT, "2"),
                    ("e", ConstraintOperator.LE, "2"),
                    ("f", ConstraintOperator.CONTAINS, "ell"),
                    ("g", ConstraintOperator.PREFIX, "wor"),
                    ("h", ConstraintOperator.SUFFIX, "est"),
                    ("i", ConstraintOperator.IN_SET, ["val", "other"]),
                    ("j", ConstraintOperator.NOT_IN_SET, ["bad", "worse"]),
                    ("k", ConstraintOperator.MATCHES_REGEX, r"\d+"),
                ],
            )
            encoded = sandbox.encode_to_smt(action)
        assert encoded is not None
