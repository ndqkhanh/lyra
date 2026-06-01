"""Integration tests for hooks — verifies real hook execution behavior.

Tests actual command-based hook execution via subprocess calls.
Replaces prior smoke tests. Each test exercises the real HookManager.
"""

from lyra_hooks.manager import HookManager
from lyra_hooks.models import HookSpec, HookType


class TestHookExecution:
    """Verify hooks ACTUALLY execute commands via subprocess."""

    def test_pre_tool_hook_executes_real_command(self):
        """A PreToolUse hook runs a real subprocess and returns result."""
        mgr = HookManager()

        spec = HookSpec(
            name="echo-pre-check",
            hook_type=HookType.PRE_TOOL_USE,
            command="echo 'pre-tool-check' && exit 0",
        )
        mgr.register(spec)

        results = mgr.run_pre_tool(tool_name="Write",
                                    tool_input={"path": "/tmp/test.txt"})
        assert len(results) == 1
        assert results[0].success
        assert results[0].exit_code == 0
        assert "pre-tool-check" in results[0].stdout

    def test_hook_with_failure_returns_nonzero_exit(self):
        """A hook that fails returns success=False."""
        mgr = HookManager()

        spec = HookSpec(
            name="failing-check",
            hook_type=HookType.PRE_TOOL_USE,
            command="echo 'failed' && exit 1",
        )
        mgr.register(spec)

        results = mgr.run_pre_tool(tool_name="Write",
                                    tool_input={"path": "/tmp/test.txt"})
        assert not results[0].success
        assert results[0].exit_code == 1
        assert "failed" in results[0].stdout

    def test_post_tool_hook_executes_after_tool(self):
        """A PostToolUse hook runs after tool completes."""
        mgr = HookManager()

        spec = HookSpec(
            name="audit-post",
            hook_type=HookType.POST_TOOL_USE,
            command="echo 'post-tool-audit' && exit 0",
        )
        mgr.register(spec)

        results = mgr.run_post_tool(tool_name="Bash",
                                     tool_result={"output": "hello"})
        assert results[0].success
        assert "post-tool-audit" in results[0].stdout

    def test_multiple_hooks_execute_in_order(self):
        """Multiple PRE_TOOL_USE hooks execute sequentially."""
        mgr = HookManager()

        mgr.register(HookSpec(name="first", hook_type=HookType.PRE_TOOL_USE,
                               command="echo 'first' && exit 0"))
        mgr.register(HookSpec(name="second", hook_type=HookType.PRE_TOOL_USE,
                               command="echo 'second' && exit 0"))

        results = mgr.run_pre_tool(tool_name="Read",
                                    tool_input={"path": "/tmp/test"})
        assert len(results) == 2
        assert results[0].success
        assert results[1].success
        assert "first" in results[0].stdout
        assert "second" in results[1].stdout

    def test_hook_timeout_returns_failure(self):
        """A hook exceeding timeout returns success=False."""
        mgr = HookManager()

        spec = HookSpec(
            name="slow-hook",
            hook_type=HookType.PRE_TOOL_USE,
            command="sleep 10",
            timeout_seconds=1,
        )
        mgr.register(spec)

        results = mgr.run_pre_tool(tool_name="Write",
                                    tool_input={"path": "/tmp/test.txt"})
        assert not results[0].success
        assert "Timeout" in results[0].stderr

    def test_stop_hook_executes_on_session_end(self):
        """A Stop hook runs when the session ends."""
        mgr = HookManager()

        mgr.register(HookSpec(name="cleanup", hook_type=HookType.STOP,
                               command="echo 'cleanup-done' && exit 0"))

        results = mgr.run_stop()
        assert results[0].success
        assert "cleanup-done" in results[0].stdout


class TestHookRegistration:
    """Hook registration and lifecycle."""

    def test_register_and_unregister(self):
        mgr = HookManager()
        spec = HookSpec(name="test", hook_type=HookType.PRE_TOOL_USE,
                         command="true")
        mgr.register(spec)
        assert mgr.unregister("test") is True
        assert mgr.unregister("test") is False

    def test_unregistered_hook_does_not_execute(self):
        """After unregister, hook should not execute."""
        mgr = HookManager()
        spec = HookSpec(name="test", hook_type=HookType.PRE_TOOL_USE,
                         command="true")
        mgr.register(spec)
        mgr.unregister("test")

        results = mgr.run_pre_tool(tool_name="Read", tool_input={})
        assert len(results) == 0

    def test_matcher_filters_tool_name(self):
        """Hook with matcher only fires for matching tool names."""
        mgr = HookManager()

        mgr.register(HookSpec(name="write-only", hook_type=HookType.PRE_TOOL_USE,
                               command="echo 'write-hook' && exit 0",
                               matcher="Write"))

        # Should match
        results = mgr.run_pre_tool(tool_name="Write", tool_input={})
        assert len(results) == 1
        assert "write-hook" in results[0].stdout

        # Should NOT match
        results = mgr.run_pre_tool(tool_name="Read", tool_input={})
        assert len(results) == 0
