"""
Tests for P2: Deterministic Tool-Call Gating (Breakthrough #3).

Covers:
- Policy dataclass immutability and defaults
- ToolGate.generate_policy() returns a valid Policy
- All 4 GateDecision types: ALLOW, ALLOW_WITH_SANDBOX, ASK_USER, BLOCK
- Deterministic enforcement (no LLM in validation path)
- Hook handler integration via __call__
"""

from __future__ import annotations

import pytest

from src.hooks.hook import HookAction, HookContext, HookResult, HookType
from src.safety.policy import GateDecision, Policy
from src.safety.tool_gate import ToolGate


# ======================================================================
# Policy tests
# ======================================================================


class TestPolicy:
    """Policy dataclass — immutability and default values."""

    def test_default_policy(self) -> None:
        """A default Policy should include essential tools."""
        policy = Policy()
        assert len(policy.allowed_tools) == 0
        assert policy.allowed_paths == ["**"]
        assert policy.allowed_domains == ["*"]
        assert policy.max_tokens_per_call == 0
        assert policy.requires_approval_for == []

    def test_custom_policy(self) -> None:
        """A custom Policy should store the provided values."""
        policy = Policy(
            allowed_tools=["Read", "Bash"],
            allowed_paths=["src/**"],
            allowed_domains=["*.example.com"],
            max_tokens_per_call=2048,
            requires_approval_for=["Bash"],
        )
        assert policy.allowed_tools == ["Read", "Bash"]
        assert policy.allowed_paths == ["src/**"]
        assert policy.allowed_domains == ["*.example.com"]
        assert policy.max_tokens_per_call == 2048
        assert policy.requires_approval_for == ["Bash"]

    def test_policy_is_frozen(self) -> None:
        """Policy instances must be immutable (frozen dataclass)."""
        policy = Policy(allowed_tools=["Read"])
        with pytest.raises(AttributeError):
            policy.allowed_tools = ["Write"]  # type: ignore[misc]


# ======================================================================
# ToolGate — generate_policy
# ======================================================================


class TestToolGateGeneratePolicy:
    """ToolGate.generate_policy() — Phase 1: LLM-assisted generation."""

    def test_generate_policy_returns_policy(self) -> None:
        """generate_policy should always return a Policy instance."""
        gate = ToolGate()
        policy = gate.generate_policy("Read configuration files")
        assert isinstance(policy, Policy)

    def test_generate_policy_with_configured_default(self) -> None:
        """Default policy should include common tools."""
        gate = ToolGate()
        policy = gate.generate_policy("")
        assert "Read" in policy.allowed_tools
        assert "Bash" in policy.allowed_tools
        assert "Write" in policy.allowed_tools
        assert "Edit" in policy.allowed_tools
        assert "WebSearch" in policy.allowed_tools

    def test_generate_policy_custom_default(self) -> None:
        """A ToolGate constructed with a custom policy should return it."""
        custom = Policy(allowed_tools=["Read"], requires_approval_for=["Bash"])
        gate = ToolGate(policy=custom)
        result = gate.generate_policy("")
        assert result.allowed_tools == ["Read"]
        assert result.requires_approval_for == ["Bash"]


# ======================================================================
# ToolGate — validate (deterministic enforcement)
# ======================================================================


class TestToolGateValidate:
    """ToolGate.validate() — Phase 2: pure deterministic enforcement.

    No LLM calls happen in this path.  All checks are pattern matching,
    string comparison, and simple logic.
    """

    def setup_method(self) -> None:
        self.gate = ToolGate()
        self.policy = Policy(
            allowed_tools=["Read", "Bash", "Write", "Edit", "WebSearch"],
            allowed_paths=["src/**", "docs/**"],
            allowed_domains=["*"],
            max_tokens_per_call=4096,
            requires_approval_for=["Bash"],
        )

    # -- ALLOW ---------------------------------------------------------

    def test_allow_allowed_tool(self) -> None:
        """A tool on the allowlist with no special conditions is ALLOW."""
        decision = self.gate.validate(
            {"name": "Read", "args": {"file_path": "src/main.py"}},
            self.policy,
        )
        assert decision == GateDecision.ALLOW

    def test_allow_websearch(self) -> None:
        """WebSearch without approval requirement is ALLOW."""
        decision = self.gate.validate(
            {"name": "WebSearch", "args": {"query": "python"}},
            self.policy,
        )
        assert decision == GateDecision.ALLOW

    def test_allow_allowed_path_not_matching_allowlist_default(self) -> None:
        """When allowed_paths is ['**'], any path is ALLOW."""
        permissive = Policy(
            allowed_tools=["Read"],
            allowed_paths=["**"],
        )
        decision = self.gate.validate(
            {"name": "Read", "args": {"file_path": "/any/path/at/all.py"}},
            permissive,
        )
        assert decision == GateDecision.ALLOW

    # -- ALLOW_WITH_SANDBOX --------------------------------------------
    #
    # These tests use a policy that does NOT require approval for Bash,
    # so the sandbox check is reached.

    def _sandbox_policy(self) -> Policy:
        return Policy(
            allowed_tools=["Read", "Bash", "Write", "Edit", "WebSearch"],
            allowed_paths=["src/**", "docs/**"],
            allowed_domains=["*"],
            max_tokens_per_call=4096,
            requires_approval_for=[],
        )

    def test_allow_with_sandbox_dangerous_rm(self) -> None:
        """Bash 'rm -rf /tmp/foo' triggers ALLOW_WITH_SANDBOX."""
        decision = self.gate.validate(
            {"name": "Bash", "args": {"command": "rm -rf /tmp/foo"}},
            self._sandbox_policy(),
        )
        assert decision == GateDecision.ALLOW_WITH_SANDBOX

    def test_allow_with_sandbox_dangerous_sudo(self) -> None:
        """Bash 'sudo something' triggers ALLOW_WITH_SANDBOX."""
        decision = self.gate.validate(
            {"name": "Bash", "args": {"command": "sudo apt update"}},
            self._sandbox_policy(),
        )
        assert decision == GateDecision.ALLOW_WITH_SANDBOX

    def test_allow_with_sandbox_dangerous_chmod(self) -> None:
        """Bash 'chmod 755 file' triggers ALLOW_WITH_SANDBOX."""
        decision = self.gate.validate(
            {"name": "Bash", "args": {"command": "chmod 755 file.sh"}},
            self._sandbox_policy(),
        )
        assert decision == GateDecision.ALLOW_WITH_SANDBOX

    def test_allow_with_sandbox_dangerous_dd(self) -> None:
        """Bash 'dd if=... of=...' triggers ALLOW_WITH_SANDBOX."""
        decision = self.gate.validate(
            {"name": "Bash", "args": {"command": "dd if=/dev/zero of=file bs=1M count=1"}},
            self._sandbox_policy(),
        )
        assert decision == GateDecision.ALLOW_WITH_SANDBOX

    def test_allow_safe_bash_is_not_sandboxed(self) -> None:
        """Bash 'ls -la' (no dangerous prefix) is ALLOW, not sandboxed."""
        decision = self.gate.validate(
            {"name": "Bash", "args": {"command": "ls -la"}},
            self._sandbox_policy(),
        )
        assert decision == GateDecision.ALLOW

    # -- ASK_USER ------------------------------------------------------

    def test_ask_user_when_tool_requires_approval(self) -> None:
        """Bash is in requires_approval_for → ASK_USER."""
        decision = self.gate.validate(
            {"name": "Bash", "args": {"command": "ls -la"}},
            self.policy,
        )
        assert decision == GateDecision.ASK_USER

    def test_ask_user_approval_check_before_sandbox_check(self) -> None:
        """ASK_USER takes priority over ALLOW_WITH_SANDBOX."""
        decision = self.gate.validate(
            {"name": "Bash", "args": {"command": "rm -rf /tmp"}},
            self.policy,
        )
        # Bash requires approval regardless of command content
        assert decision == GateDecision.ASK_USER

    # -- BLOCK ---------------------------------------------------------

    def test_block_unknown_tool(self) -> None:
        """A tool not in allowed_tools is BLOCK."""
        decision = self.gate.validate(
            {"name": "DangerousTool", "args": {}},
            self.policy,
        )
        assert decision == GateDecision.BLOCK

    def test_block_path_outside_allowlist(self) -> None:
        """A file path not matching allowed_paths is BLOCK."""
        policy = Policy(
            allowed_tools=["Read"],
            allowed_paths=["src/**"],
        )
        decision = self.gate.validate(
            {"name": "Read", "args": {"file_path": "/etc/passwd"}},
            policy,
        )
        assert decision == GateDecision.BLOCK

    def test_block_path_with_no_pattern_match(self) -> None:
        """A path outside any allowed pattern is BLOCK."""
        policy = Policy(
            allowed_tools=["Write"],
            allowed_paths=["safe_dir/**"],
        )
        decision = self.gate.validate(
            {"name": "Write", "args": {"file_path": "outside_dir/secret.txt"}},
            policy,
        )
        assert decision == GateDecision.BLOCK

    def test_block_empty_allowed_tools(self) -> None:
        """When allowed_tools is empty, every tool is BLOCK."""
        restrictive = Policy(allowed_tools=[])
        decision = self.gate.validate(
            {"name": "Read", "args": {}},
            restrictive,
        )
        assert decision == GateDecision.BLOCK


# ======================================================================
# ToolGate — hook handler integration
# ======================================================================


class TestToolGateHookHandler:
    """ToolGate.__call__() — integration with the Hook Engine."""

    def setup_method(self) -> None:
        self.gate = ToolGate()

    def _make_context(
        self,
        tool_name: str = "Read",
        tool_args: dict | None = None,
        hook_type: HookType = HookType.PRE_TOOL_USE,
    ) -> HookContext:
        return HookContext(
            hook_type=hook_type,
            tool_name=tool_name,
            tool_args=tool_args or {},
            tool_input=tool_args or {},
        )

    def test_ignores_non_pre_tool_use(self) -> None:
        """The handler returns ALLOW for non-PRE_TOOL_USE hook types."""
        ctx = self._make_context(hook_type=HookType.POST_TOOL_USE)
        result = self.gate(ctx)
        assert result.action == HookAction.ALLOW

    def test_allow_tool(self) -> None:
        """A permitted tool call returns ALLOW."""
        ctx = self._make_context(tool_name="Read", tool_args={"file_path": "src/main.py"})
        result = self.gate(ctx)
        assert result.action == HookAction.ALLOW

    def test_block_unknown_tool_via_hook(self) -> None:
        """An unregistered tool returns BLOCK."""
        ctx = self._make_context(tool_name="UnknownTool")
        result = self.gate(ctx)
        assert result.action == HookAction.BLOCK
        assert "blocked per policy" in result.reason

    def test_ask_user_for_bash(self) -> None:
        """Bash is in the default requires_approval_for → ASK_USER."""
        ctx = self._make_context(tool_name="Bash", tool_args={"command": "ls"})
        result = self.gate(ctx)
        assert result.action == HookAction.ASK_USER
        assert "requires user approval" in result.reason

    def test_allow_with_sandbox_for_dangerous_bash(self) -> None:
        """Bash with a dangerous command triggers MODIFY (sandbox)."""
        # Override the default to not require approval for Bash
        custom_policy = Policy(
            allowed_tools=["Read", "Bash", "Write", "Edit"],
            requires_approval_for=[],
        )
        gate = ToolGate(policy=custom_policy)
        ctx = self._make_context(tool_name="Bash", tool_args={"command": "rm -rf /tmp"})
        result = gate(ctx)
        assert result.action == HookAction.MODIFY
        assert result.modified_context is not None
        assert result.modified_context.metadata.get("sandbox_required") is True

    def test_hook_result_has_hook_name(self) -> None:
        """All hook results should carry 'ToolGate' as the hook_name."""
        ctx = self._make_context(tool_name="Read")
        result = self.gate(ctx)
        assert result.hook_name == "ToolGate"


# ======================================================================
# Deterministic enforcement guarantee
# ======================================================================


class TestDeterministicEnforcement:
    """Verify that validation is purely deterministic (no LLM)."""

    def test_repeatable_block(self) -> None:
        """Same inputs always produce the same BLOCK."""
        gate = ToolGate()
        policy = Policy(allowed_tools=["Read"], allowed_paths=["src/**"])
        call = {"name": "Read", "args": {"file_path": "/etc/passwd"}}

        results = [gate.validate(call, policy) for _ in range(10)]
        assert all(r == GateDecision.BLOCK for r in results)

    def test_repeatable_allow(self) -> None:
        """Same inputs always produce the same ALLOW."""
        gate = ToolGate()
        policy = Policy(allowed_tools=["Read"], allowed_paths=["src/**"])
        call = {"name": "Read", "args": {"file_path": "src/main.py"}}

        results = [gate.validate(call, policy) for _ in range(10)]
        assert all(r == GateDecision.ALLOW for r in results)

    def test_no_llm_imports(self) -> None:
        """The validate method should not import any LLM-related module."""
        import inspect

        source = inspect.getsource(ToolGate.validate)

        # Simple text-based check — any import statement mentioning "llm"
        # or "ai" in the validate source is forbidden.
        forbidden = ("llm", "anthropic", "openai")
        for line in source.splitlines():
            stripped = line.strip()
            if stripped.startswith("import ") or stripped.startswith("from "):
                for keyword in forbidden:
                    if keyword in stripped.lower():
                        pytest.fail(
                            f"LLM-related import/statement found in validate(): "
                            f"{stripped!r}"
                        )
