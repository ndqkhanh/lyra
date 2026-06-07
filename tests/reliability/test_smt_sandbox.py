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
