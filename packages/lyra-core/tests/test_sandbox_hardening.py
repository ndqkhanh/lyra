"""Hardening tests for BashBlocklist sandbox — command blocking, patterns, fail-closed."""

from __future__ import annotations

import pytest
from lyra_core.sandbox import (
    BashBlocklist,
    SandboxDecision,
    requires_nl_description,
    sandbox_mode,
)

# ── SandboxDecision ─────────────────────────────────────────────────────


class TestSandboxDecision:
    def test_default_allowed(self):
        d = SandboxDecision()
        assert d.allowed is True
        assert d.reason == ""
        assert d.blocked_command == ""

    def test_blocked_decision(self):
        d = SandboxDecision(allowed=False, reason="blocked: curl", blocked_command="curl")
        assert d.allowed is False
        assert "curl" in d.reason

    def test_is_frozen(self):
        d = SandboxDecision(allowed=True)
        with pytest.raises(Exception):
            d.allowed = False


# ── BashBlocklist ───────────────────────────────────────────────────────


class TestBashBlocklistConstruction:
    def test_default_blocklist_blocks_curl(self):
        bl = BashBlocklist()
        decision = bl.check("curl https://example.com")
        assert decision.allowed is False
        assert "curl" in decision.blocked_command

    def test_default_blocklist_blocks_wget(self):
        bl = BashBlocklist()
        decision = bl.check("wget https://example.com/file")
        assert decision.allowed is False

    def test_default_blocklist_blocks_ssh(self):
        bl = BashBlocklist()
        decision = bl.check("ssh user@host")
        assert decision.allowed is False

    def test_safe_command_allowed(self):
        bl = BashBlocklist()
        decision = bl.check("ls -la")
        assert decision.allowed is True

    def test_empty_command_allowed(self):
        bl = BashBlocklist()
        decision = bl.check("")
        assert decision.allowed is True

    def test_whitespace_command_allowed(self):
        bl = BashBlocklist()
        decision = bl.check("   ")
        assert decision.allowed is True


class TestBashBlocklistPatterns:
    def test_blocks_fork_bomb_pattern(self):
        bl = BashBlocklist()
        decision = bl.check(":(){ :|:& };:")
        assert decision.allowed is False

    def test_blocks_rm_rf_root(self):
        bl = BashBlocklist()
        decision = bl.check("rm -rf /")
        assert decision.allowed is False
        assert "rm -rf /" in decision.blocked_command

    def test_blocks_chmod_r_root(self):
        bl = BashBlocklist()
        decision = bl.check("chmod -R /")
        assert decision.allowed is False

    def test_blocks_chown_r_root(self):
        bl = BashBlocklist()
        decision = bl.check("chown -R /")
        assert decision.allowed is False

    def test_safe_rm_not_blocked(self):
        bl = BashBlocklist()
        decision = bl.check("rm file.txt")
        assert decision.allowed is True


class TestBashBlocklistSudo:
    def test_blocks_curl_under_sudo(self):
        bl = BashBlocklist()
        decision = bl.check("sudo curl https://evil.com")
        assert decision.allowed is False

    def test_blocks_ssh_under_sudo(self):
        bl = BashBlocklist()
        decision = bl.check("sudo ssh user@host")
        assert decision.allowed is False


class TestBashBlocklistCustom:
    def test_add_blocked_command(self):
        bl = BashBlocklist()
        bl.add_blocked("python3")
        decision = bl.check("python3 -c 'print(1)'")
        assert decision.allowed is False

    def test_remove_blocked_command(self):
        bl = BashBlocklist()
        bl.remove_blocked("curl")
        decision = bl.check("curl https://example.com")
        assert decision.allowed is True

    def test_custom_blocked_commands_in_constructor(self):
        bl = BashBlocklist(blocked_commands=["custom-cmd"])
        decision = bl.check("custom-cmd --flag")
        assert decision.allowed is False

    def test_custom_blocked_patterns_in_constructor(self):
        bl = BashBlocklist(blocked_patterns=["dangerous_pattern"])
        decision = bl.check("some command with dangerous_pattern inside")
        assert decision.allowed is False

    def test_blocked_commands_property(self):
        bl = BashBlocklist()
        cmds = bl.blocked_commands
        assert "curl" in cmds
        assert "wget" in cmds

    def test_add_blocked_case_insensitive(self):
        bl = BashBlocklist()
        bl.add_blocked("MYCMD")
        decision = bl.check("mycmd --flag")
        assert decision.allowed is False


class TestBashBlocklistEdgeCases:
    def test_command_with_pipe_and_blocked(self):
        bl = BashBlocklist()
        # curl at start of pipe should be blocked
        decision = bl.check("curl https://example.com | grep data")
        assert decision.allowed is False

    def test_command_with_redirect_not_blocked(self):
        bl = BashBlocklist()
        decision = bl.check("echo hello > file.txt")
        assert decision.allowed is True

    def test_shell_builtin_not_blocked(self):
        bl = BashBlocklist()
        decision = bl.check("cd /tmp")
        assert decision.allowed is True

    def test_echo_with_redirect_not_blocked(self):
        bl = BashBlocklist()
        decision = bl.check("echo 'test' > output.txt")
        assert decision.allowed is True


# ── requires_nl_description ─────────────────────────────────────────────


class TestRequiresNLDescription:
    def test_pipe_triggers_description(self):
        assert requires_nl_description("cat file | grep pattern") is True

    def test_semicolon_triggers_description(self):
        assert requires_nl_description("cmd1; cmd2") is True

    def test_and_and_triggers_description(self):
        assert requires_nl_description("make && make install") is True

    def test_or_or_triggers_description(self):
        assert requires_nl_description("cmd1 || cmd2") is True

    def test_command_substitution_triggers_description(self):
        assert requires_nl_description("echo $(whoami)") is True

    def test_backticks_trigger_description(self):
        assert requires_nl_description("echo `whoami`") is True

    def test_long_command_triggers_description(self):
        assert requires_nl_description("x" * 201) is True

    def test_short_simple_command_no_description(self):
        assert requires_nl_description("ls -la") is False

    def test_empty_no_description(self):
        assert requires_nl_description("") is False


# ── sandbox_mode ────────────────────────────────────────────────────────


class TestSandboxMode:
    def test_default_is_warn(self):
        import os
        old = os.environ.pop("LYRA_SANDBOX_MODE", None)
        try:
            assert sandbox_mode() == "warn"
        finally:
            if old is not None:
                os.environ["LYRA_SANDBOX_MODE"] = old

    def test_strict_via_env(self):
        import os
        old = os.environ.get("LYRA_SANDBOX_MODE")
        os.environ["LYRA_SANDBOX_MODE"] = "strict"
        try:
            assert sandbox_mode() == "strict"
        finally:
            if old is not None:
                os.environ["LYRA_SANDBOX_MODE"] = old
            else:
                os.environ.pop("LYRA_SANDBOX_MODE", None)

    def test_off_via_env(self):
        import os
        old = os.environ.get("LYRA_SANDBOX_MODE")
        os.environ["LYRA_SANDBOX_MODE"] = "off"
        try:
            assert sandbox_mode() == "off"
        finally:
            if old is not None:
                os.environ["LYRA_SANDBOX_MODE"] = old
            else:
                os.environ.pop("LYRA_SANDBOX_MODE", None)

    def test_on_alias_for_strict(self):
        import os
        old = os.environ.get("LYRA_SANDBOX_MODE")
        os.environ["LYRA_SANDBOX_MODE"] = "on"
        try:
            assert sandbox_mode() == "strict"
        finally:
            if old is not None:
                os.environ["LYRA_SANDBOX_MODE"] = old
            else:
                os.environ.pop("LYRA_SANDBOX_MODE", None)

    def test_disabled_alias_for_off(self):
        import os
        old = os.environ.get("LYRA_SANDBOX_MODE")
        os.environ["LYRA_SANDBOX_MODE"] = "disabled"
        try:
            assert sandbox_mode() == "off"
        finally:
            if old is not None:
                os.environ["LYRA_SANDBOX_MODE"] = old
            else:
                os.environ.pop("LYRA_SANDBOX_MODE", None)

    def test_unknown_value_defaults_to_warn(self):
        import os
        old = os.environ.get("LYRA_SANDBOX_MODE")
        os.environ["LYRA_SANDBOX_MODE"] = "garbage_value"
        try:
            assert sandbox_mode() == "warn"
        finally:
            if old is not None:
                os.environ["LYRA_SANDBOX_MODE"] = old
            else:
                os.environ.pop("LYRA_SANDBOX_MODE", None)
