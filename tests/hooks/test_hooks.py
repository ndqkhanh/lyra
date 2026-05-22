"""
Tests for hooks system.
"""

import pytest

from src.hooks import (
    Hook,
    HookType,
    HookContext,
    HookResult,
    HookRegistry,
    HookEngine,
)


class TestHookContext:
    """Tests for HookContext class."""

    def test_context_creation(self):
        """Test creating a hook context."""
        context = HookContext(
            hook_type=HookType.PRE_TOOL_USE,
            tool_name="Edit",
            tool_args={"file_path": "test.py"},
            session_id="test-session",
        )

        assert context.hook_type == HookType.PRE_TOOL_USE
        assert context.tool_name == "Edit"
        assert context.tool_args["file_path"] == "test.py"
        assert context.session_id == "test-session"


class TestHookResult:
    """Tests for HookResult class."""

    def test_ok_result(self):
        """Test creating successful result."""
        result = HookResult.ok()
        assert result.success
        assert result.error is None

    def test_ok_with_modifications(self):
        """Test successful result with modifications."""
        result = HookResult.ok(modified_args={"key": "value"})
        assert result.success
        assert result.modified_args == {"key": "value"}

    def test_error_result(self):
        """Test creating error result."""
        result = HookResult.fail("Something went wrong")
        assert not result.success
        assert result.error == "Something went wrong"


class TestHook:
    """Tests for Hook class."""

    def test_hook_creation(self):
        """Test creating a hook."""
        def handler(context: HookContext) -> HookResult:
            return HookResult.ok()

        hook = Hook(
            hook_id="test-hook",
            hook_type=HookType.POST_TOOL_USE,
            handler=handler,
            description="Test hook",
            tool_filter="Edit",
            file_pattern="**/*.py",
            priority=10,
        )

        assert hook.hook_id == "test-hook"
        assert hook.hook_type == HookType.POST_TOOL_USE
        assert hook.priority == 10
        assert hook.enabled

    def test_hook_matches_type(self):
        """Test hook matching by type."""
        def handler(context: HookContext) -> HookResult:
            return HookResult.ok()

        hook = Hook(
            hook_id="test-hook",
            hook_type=HookType.POST_TOOL_USE,
            handler=handler,
            description="Test hook",
        )

        context = HookContext(hook_type=HookType.POST_TOOL_USE)
        assert hook.matches(context)

        context = HookContext(hook_type=HookType.PRE_TOOL_USE)
        assert not hook.matches(context)

    def test_hook_matches_tool(self):
        """Test hook matching by tool name."""
        def handler(context: HookContext) -> HookResult:
            return HookResult.ok()

        hook = Hook(
            hook_id="test-hook",
            hook_type=HookType.POST_TOOL_USE,
            handler=handler,
            description="Test hook",
            tool_filter="Edit",
        )

        context = HookContext(
            hook_type=HookType.POST_TOOL_USE,
            tool_name="Edit",
        )
        assert hook.matches(context)

        context = HookContext(
            hook_type=HookType.POST_TOOL_USE,
            tool_name="Write",
        )
        assert not hook.matches(context)

    def test_hook_matches_file_pattern(self):
        """Test hook matching by file pattern."""
        def handler(context: HookContext) -> HookResult:
            return HookResult.ok()

        hook = Hook(
            hook_id="test-hook",
            hook_type=HookType.POST_TOOL_USE,
            handler=handler,
            description="Test hook",
            file_pattern="**/*.py",
        )

        context = HookContext(
            hook_type=HookType.POST_TOOL_USE,
            tool_args={"file_path": "src/test.py"},
        )
        assert hook.matches(context)

        context = HookContext(
            hook_type=HookType.POST_TOOL_USE,
            tool_args={"file_path": "src/test.js"},
        )
        assert not hook.matches(context)

    def test_hook_disabled(self):
        """Test disabled hook doesn't match."""
        def handler(context: HookContext) -> HookResult:
            return HookResult.ok()

        hook = Hook(
            hook_id="test-hook",
            hook_type=HookType.POST_TOOL_USE,
            handler=handler,
            description="Test hook",
            enabled=False,
        )

        context = HookContext(hook_type=HookType.POST_TOOL_USE)
        assert not hook.matches(context)


class TestHookRegistry:
    """Tests for HookRegistry class."""

    def test_registry_creation(self):
        """Test creating a registry."""
        registry = HookRegistry()
        assert len(registry.hooks) == 0

    def test_register_hook(self):
        """Test registering a hook."""
        def handler(context: HookContext) -> HookResult:
            return HookResult.ok()

        registry = HookRegistry()
        hook = Hook(
            hook_id="test-hook",
            hook_type=HookType.POST_TOOL_USE,
            handler=handler,
            description="Test hook",
        )

        registry.register(hook)
        assert len(registry.hooks) == 1
        assert "test-hook" in registry.hooks

    def test_register_duplicate_fails(self):
        """Test registering duplicate hook fails."""
        def handler(context: HookContext) -> HookResult:
            return HookResult.ok()

        registry = HookRegistry()
        hook = Hook(
            hook_id="test-hook",
            hook_type=HookType.POST_TOOL_USE,
            handler=handler,
            description="Test hook",
        )

        registry.register(hook)
        with pytest.raises(ValueError):
            registry.register(hook)

    def test_unregister_hook(self):
        """Test unregistering a hook."""
        def handler(context: HookContext) -> HookResult:
            return HookResult.ok()

        registry = HookRegistry()
        hook = Hook(
            hook_id="test-hook",
            hook_type=HookType.POST_TOOL_USE,
            handler=handler,
            description="Test hook",
        )

        registry.register(hook)
        assert registry.unregister("test-hook")
        assert len(registry.hooks) == 0
        assert not registry.unregister("nonexistent")

    def test_get_hook(self):
        """Test getting a hook."""
        def handler(context: HookContext) -> HookResult:
            return HookResult.ok()

        registry = HookRegistry()
        hook = Hook(
            hook_id="test-hook",
            hook_type=HookType.POST_TOOL_USE,
            handler=handler,
            description="Test hook",
        )

        registry.register(hook)
        retrieved = registry.get("test-hook")
        assert retrieved is not None
        assert retrieved.hook_id == "test-hook"
        assert registry.get("nonexistent") is None

    def test_find_matching_hooks(self):
        """Test finding matching hooks."""
        def handler(context: HookContext) -> HookResult:
            return HookResult.ok()

        registry = HookRegistry()

        # Register multiple hooks
        hook1 = Hook(
            hook_id="hook1",
            hook_type=HookType.POST_TOOL_USE,
            handler=handler,
            description="Hook 1",
            tool_filter="Edit",
            priority=10,
        )
        hook2 = Hook(
            hook_id="hook2",
            hook_type=HookType.POST_TOOL_USE,
            handler=handler,
            description="Hook 2",
            tool_filter="Write",
            priority=5,
        )

        registry.register(hook1)
        registry.register(hook2)

        # Find hooks for Edit
        context = HookContext(
            hook_type=HookType.POST_TOOL_USE,
            tool_name="Edit",
        )
        matches = registry.find_matching_hooks(context)
        assert len(matches) == 1
        assert matches[0].hook_id == "hook1"

    def test_priority_ordering(self):
        """Test hooks are ordered by priority."""
        def handler(context: HookContext) -> HookResult:
            return HookResult.ok()

        registry = HookRegistry()

        # Register hooks with different priorities
        hook1 = Hook(
            hook_id="hook1",
            hook_type=HookType.POST_TOOL_USE,
            handler=handler,
            description="Hook 1",
            priority=5,
        )
        hook2 = Hook(
            hook_id="hook2",
            hook_type=HookType.POST_TOOL_USE,
            handler=handler,
            description="Hook 2",
            priority=10,
        )

        registry.register(hook1)
        registry.register(hook2)

        context = HookContext(hook_type=HookType.POST_TOOL_USE)
        matches = registry.find_matching_hooks(context)

        # Higher priority should come first
        assert matches[0].hook_id == "hook2"
        assert matches[1].hook_id == "hook1"

    def test_enable_disable(self):
        """Test enabling and disabling hooks."""
        def handler(context: HookContext) -> HookResult:
            return HookResult.ok()

        registry = HookRegistry()
        hook = Hook(
            hook_id="test-hook",
            hook_type=HookType.POST_TOOL_USE,
            handler=handler,
            description="Test hook",
        )

        registry.register(hook)
        assert registry.disable("test-hook")
        assert not hook.enabled

        assert registry.enable("test-hook")
        assert hook.enabled

    def test_list_hooks(self):
        """Test listing hooks."""
        def handler(context: HookContext) -> HookResult:
            return HookResult.ok()

        registry = HookRegistry()

        hook1 = Hook(
            hook_id="hook1",
            hook_type=HookType.POST_TOOL_USE,
            handler=handler,
            description="Hook 1",
        )
        hook2 = Hook(
            hook_id="hook2",
            hook_type=HookType.PRE_TOOL_USE,
            handler=handler,
            description="Hook 2",
            enabled=False,
        )

        registry.register(hook1)
        registry.register(hook2)

        # List all
        all_hooks = registry.list_hooks()
        assert len(all_hooks) == 2

        # Filter by type
        post_hooks = registry.list_hooks(hook_type=HookType.POST_TOOL_USE)
        assert len(post_hooks) == 1

        # Filter by enabled
        enabled_hooks = registry.list_hooks(enabled_only=True)
        assert len(enabled_hooks) == 1

    def test_clear(self):
        """Test clearing registry."""
        def handler(context: HookContext) -> HookResult:
            return HookResult.ok()

        registry = HookRegistry()
        hook = Hook(
            hook_id="test-hook",
            hook_type=HookType.POST_TOOL_USE,
            handler=handler,
            description="Test hook",
        )

        registry.register(hook)
        registry.clear()
        assert len(registry.hooks) == 0

    def test_get_statistics(self):
        """Test getting statistics."""
        def handler(context: HookContext) -> HookResult:
            return HookResult.ok()

        registry = HookRegistry()

        hook1 = Hook(
            hook_id="hook1",
            hook_type=HookType.POST_TOOL_USE,
            handler=handler,
            description="Hook 1",
        )
        hook2 = Hook(
            hook_id="hook2",
            hook_type=HookType.PRE_TOOL_USE,
            handler=handler,
            description="Hook 2",
            enabled=False,
        )

        registry.register(hook1)
        registry.register(hook2)

        stats = registry.get_statistics()
        assert stats["total_hooks"] == 2
        assert stats["enabled"] == 1
        assert stats["disabled"] == 1


class TestHookEngine:
    """Tests for HookEngine class."""

    def test_engine_creation(self):
        """Test creating a hook engine."""
        engine = HookEngine()
        assert engine.registry is not None

    @pytest.mark.asyncio
    async def test_fire_hook(self):
        """Test firing a hook."""
        executed = []

        def handler(context: HookContext) -> HookResult:
            executed.append(context.hook_type)
            return HookResult.ok()

        engine = HookEngine()
        hook = Hook(
            hook_id="test-hook",
            hook_type=HookType.POST_TOOL_USE,
            handler=handler,
            description="Test hook",
        )

        engine.registry.register(hook)

        results = await engine.fire(
            hook_type=HookType.POST_TOOL_USE,
            tool_name="Edit",
        )

        assert len(results) == 1
        assert results[0].success
        assert len(executed) == 1

    @pytest.mark.asyncio
    async def test_fire_multiple_hooks(self):
        """Test firing multiple hooks."""
        executed = []

        def handler1(context: HookContext) -> HookResult:
            executed.append("hook1")
            return HookResult.ok()

        def handler2(context: HookContext) -> HookResult:
            executed.append("hook2")
            return HookResult.ok()

        engine = HookEngine()

        hook1 = Hook(
            hook_id="hook1",
            hook_type=HookType.POST_TOOL_USE,
            handler=handler1,
            description="Hook 1",
            priority=10,
        )
        hook2 = Hook(
            hook_id="hook2",
            hook_type=HookType.POST_TOOL_USE,
            handler=handler2,
            description="Hook 2",
            priority=5,
        )

        engine.registry.register(hook1)
        engine.registry.register(hook2)

        results = await engine.fire(hook_type=HookType.POST_TOOL_USE)

        assert len(results) == 2
        # Higher priority executes first
        assert executed == ["hook1", "hook2"]

    @pytest.mark.asyncio
    async def test_hook_error_handling(self):
        """Test hook error handling."""
        def failing_handler(context: HookContext) -> HookResult:
            raise ValueError("Hook failed")

        engine = HookEngine()
        hook = Hook(
            hook_id="failing-hook",
            hook_type=HookType.POST_TOOL_USE,
            handler=failing_handler,
            description="Failing hook",
        )

        engine.registry.register(hook)

        results = await engine.fire(hook_type=HookType.POST_TOOL_USE)

        assert len(results) == 1
        assert not results[0].success
        assert "Hook execution failed" in results[0].error

    def test_fire_sync(self):
        """Test synchronous hook firing."""
        executed = []

        def handler(context: HookContext) -> HookResult:
            executed.append(True)
            return HookResult.ok()

        engine = HookEngine()
        hook = Hook(
            hook_id="test-hook",
            hook_type=HookType.SESSION_START,
            handler=handler,
            description="Test hook",
        )

        engine.registry.register(hook)

        results = engine.fire_sync(hook_type=HookType.SESSION_START)

        assert len(results) == 1
        assert results[0].success
        assert len(executed) == 1

    @pytest.mark.asyncio
    async def test_execution_history(self):
        """Test execution history tracking."""
        def handler(context: HookContext) -> HookResult:
            return HookResult.ok()

        engine = HookEngine()
        hook = Hook(
            hook_id="test-hook",
            hook_type=HookType.POST_TOOL_USE,
            handler=handler,
            description="Test hook",
        )

        engine.registry.register(hook)

        await engine.fire(hook_type=HookType.POST_TOOL_USE)

        history = engine.get_execution_history()
        assert len(history) == 1
        assert history[0]["hook_id"] == "test-hook"
        assert history[0]["success"]

    @pytest.mark.asyncio
    async def test_get_statistics(self):
        """Test getting execution statistics."""
        def handler(context: HookContext) -> HookResult:
            return HookResult.ok()

        engine = HookEngine()
        hook = Hook(
            hook_id="test-hook",
            hook_type=HookType.POST_TOOL_USE,
            handler=handler,
            description="Test hook",
        )

        engine.registry.register(hook)

        await engine.fire(hook_type=HookType.POST_TOOL_USE)
        await engine.fire(hook_type=HookType.POST_TOOL_USE)

        stats = engine.get_statistics()
        assert stats["total_executions"] == 2
        assert stats["successful"] == 2
        assert stats["success_rate"] == 1.0


if __name__ == "__main__":
    pytest.main([__file__, "-v"])
