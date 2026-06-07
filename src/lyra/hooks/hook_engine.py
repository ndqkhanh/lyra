"""
Hook execution engine v2 (Interceptor Pipeline).

Features
--------
- Sequential pre-hook execution (can BLOCK / ASK_USER)
- Parallel post-hook execution (fire-and-forget)
- Priority-ordered hook dispatch
- Built-in security, validation, and observability handlers
- Full backward compatibility with v1 ``fire()`` / ``fire_sync()``
"""

from __future__ import annotations

import asyncio
import logging
from collections.abc import Callable, Coroutine
from datetime import datetime
from typing import Any

from .handlers import CommandGuard, CostTracker, SecretsScanner
from .hook import Hook, HookAction, HookContext, HookResult, HookType
from .hook_registry import HookRegistry

logger = logging.getLogger(__name__)

# Priority levels (higher number = runs first)
PRIORITY_SECURITY = 1000
PRIORITY_VALIDATION = 900
PRIORITY_OBSERVABILITY = 800
PRIORITY_CUSTOM_BASE = 500


class HookEngine:
    """
    Hook Engine v2: interceptor pipeline for Lyra agent operations.

    Usage::

        engine = HookEngine()

        # Manual registration
        async def my_handler(ctx: HookContext) -> HookResult:
            return HookResult.allow("my_handler")

        engine.register(HookType.PRE_TOOL_USE, my_handler, priority=700)

        # Pre-hooks run sequentially (any hook can BLOCK)
        result = await engine.execute_pre_hooks(context)

        # Post-hooks run in parallel (fire-and-forget)
        await engine.execute_post_hooks(context)
    """

    def __init__(
        self,
        registry: HookRegistry | None = None,
        auto_register_builtins: bool = True,
    ):
        """
        Args:
            registry: An existing HookRegistry (creates a new one if None).
            auto_register_builtins: If True (default), registers the built-in
                SecretsScanner, CommandGuard, and CostTracker handlers.
        """
        self.registry = registry or HookRegistry()
        self.execution_history: list[dict[str, Any]] = []

        if auto_register_builtins:
            self._register_builtins()

    # ------------------------------------------------------------------
    # Registration (v2)
    # ------------------------------------------------------------------

    def register(
        self,
        hook_type: HookType,
        handler: Callable[[HookContext], HookResult | Coroutine[Any, Any, HookResult]],
        priority: int = PRIORITY_CUSTOM_BASE,
        hook_id: str | None = None,
        description: str = "",
        tool_filter: str | None = None,
        file_pattern: str | None = None,
    ) -> str:
        """
        Register a hook handler.

        Args:
            hook_type: The lifecycle point to hook into.
            handler: A sync or async callable that receives ``HookContext``
                and returns ``HookResult``.
            priority: Execution priority (higher = earlier).  Convention:
                p0=1000 (security), p1=900 (validation), p2=800 (observability),
                p3+ custom <= PRIORITY_CUSTOM_BASE (500).
            hook_id: Optional explicit ID.  Auto-generated from the type and
                handler name if omitted.
            description: Human-readable description.
            tool_filter: Optional tool name pattern (``fnmatch``).
            file_pattern: Optional file path pattern (``fnmatch``).

        Returns:
            The ``hook_id`` assigned to this hook.
        """
        hid = hook_id or f"{hook_type.value}_{handler.__name__}_{id(handler)}"
        hook = Hook(
            hook_id=hid,
            hook_type=hook_type,
            handler=handler,
            description=description,
            tool_filter=tool_filter,
            file_pattern=file_pattern,
            priority=priority,
        )

        try:
            self.registry.register(hook)
        except ValueError:
            # Registration already exists; treat as no-op.
            pass

        return hid

    # ------------------------------------------------------------------
    # Execution (v2)
    # ------------------------------------------------------------------

    async def execute_pre_hooks(self, context: HookContext) -> HookResult:
        """
        Execute pre-hooks sequentially.

        Each hook runs in order of descending priority.  If any hook returns
        ``BLOCK`` or ``ASK_USER`` the pipeline stops immediately and the
        terminating result is returned.

        If a hook returns ``MODIFY`` the context is replaced and subsequent
        hooks see the new context.
        """
        hooks = self._get_matching(context)

        for hook in hooks:
            result = await self._execute(hook, context)

            self._record(hook, result)

            if result.action == HookAction.BLOCK:
                logger.info(
                    "Pre-hook chain blocked by %s: %s",
                    hook.hook_id, result.reason,
                )
                return result

            if result.action == HookAction.ASK_USER:
                logger.info(
                    "Pre-hook chain deferred by %s: %s",
                    hook.hook_id, result.reason,
                )
                return result

            if result.action == HookAction.MODIFY and result.modified_context:
                context = result.modified_context

        # No hook blocked; return ALLOW with the (possibly modified) context
        return HookResult(
            action=HookAction.ALLOW,
            modified_context=context,
            hook_name="HookEngine",
            reason="All pre-hooks passed",
        )

    async def execute_post_hooks(
        self,
        context: HookContext,
        *,
        timeout: float = 10.0,
    ) -> list[HookResult]:
        """
        Execute post-hooks in parallel (fire-and-forget).

        Each hook runs in a separate task.  A single timeout applies to all
        hooks collectively.

        Args:
            context: Current hook context.
            timeout: Max wall-clock seconds to wait for all hooks.

        Returns:
            List of HookResult from each executed hook.
        """
        hooks = self._get_matching(context)

        if not hooks:
            return []

        async def _run(hook: Hook) -> HookResult:
            result = await self._execute(hook, context)
            self._record(hook, result)
            return result

        tasks = [asyncio.create_task(_run(h)) for h in hooks]
        done, pending = await asyncio.wait(tasks, timeout=timeout)

        results: list[HookResult] = []
        for task in done:
            try:
                results.append(task.result())
            except Exception as e:
                logger.error("Post-hook task failed: %s", e)

        # Cancel remaining
        for task in pending:
            task.cancel()

        return results

    # ------------------------------------------------------------------
    # Backward-compatible v1 API
    # ------------------------------------------------------------------

    async def fire(
        self,
        hook_type: HookType,
        tool_name: str | None = None,
        tool_args: dict[str, Any] | None = None,
        tool_result: Any | None = None,
        session_id: str | None = None,
        metadata: dict[str, Any] | None = None,
    ) -> list[HookResult]:
        """v1-compatible hook execution.

        Pre-hooks run sequentially; post-hooks run in parallel.
        Returns a list containing a single HookResult for pre-hooks,
        or a list of HookResults for post-hooks.
        """
        context = HookContext(
            hook_type=hook_type,
            tool_name=tool_name,
            tool_args=tool_args,
            tool_input=tool_args,
            tool_result=tool_result,
            session_id=session_id,
            metadata=metadata or {},
        )

        if hook_type in (
            HookType.PRE_TOOL_USE,
            HookType.PRE_MODEL_CALL,
            HookType.SESSION_START,
        ):
            result = await self.execute_pre_hooks(context)
            return [result]

        results = await self.execute_post_hooks(context)
        return results

    def fire_sync(
        self,
        hook_type: HookType,
        tool_name: str | None = None,
        tool_args: dict[str, Any] | None = None,
        tool_result: Any | None = None,
        session_id: str | None = None,
        metadata: dict[str, Any] | None = None,
    ) -> list[HookResult]:
        """Synchronous v1-compatible hook execution."""
        return asyncio.run(
            self.fire(
                hook_type=hook_type,
                tool_name=tool_name,
                tool_args=tool_args,
                tool_result=tool_result,
                session_id=session_id,
                metadata=metadata,
            )
        )

    # ------------------------------------------------------------------
    # History / statistics
    # ------------------------------------------------------------------

    def get_execution_history(
        self,
        hook_type: HookType | None = None,
        limit: int = 100,
    ) -> list[dict[str, Any]]:
        """Return execution history, optionally filtered by hook type."""
        history = self.execution_history
        if hook_type:
            history = [h for h in history if h["hook_type"] == hook_type.value]
        return history[-limit:]

    def clear_history(self) -> None:
        """Reset execution history."""
        self.execution_history.clear()

    def get_statistics(self) -> dict[str, Any]:
        """Return aggregated hook execution statistics."""
        total = len(self.execution_history)
        successful = sum(1 for h in self.execution_history if h.get("success", False))
        by_type: dict[str, dict[str, int]] = {}
        for rec in self.execution_history:
            ht = rec["hook_type"]
            if ht not in by_type:
                by_type[ht] = {"total": 0, "successful": 0, "blocked": 0}
            by_type[ht]["total"] += 1
            if rec.get("success"):
                by_type[ht]["successful"] += 1
            if rec.get("action") in ("block", "ask_user"):
                by_type[ht]["blocked"] += 1

        return {
            "total_executions": total,
            "successful": successful,
            "failed": total - successful,
            "success_rate": successful / total if total > 0 else 0.0,
            "by_type": by_type,
            "registry_stats": self.registry.get_statistics(),
        }

    # ------------------------------------------------------------------
    # Internals
    # ------------------------------------------------------------------

    def _register_builtins(self) -> None:
        """Register built-in handlers at their respective priorities."""
        scanner = SecretsScanner()
        self.register(
            HookType.POST_TOOL_USE,
            scanner,
            priority=PRIORITY_SECURITY,
            hook_id="builtin.secrets_scanner.post_tool_use",
            description="Block detected secrets in tool output",
        )
        self.register(
            HookType.POST_MODEL_CALL,
            scanner,
            priority=PRIORITY_SECURITY,
            hook_id="builtin.secrets_scanner.post_model_call",
            description="Block detected secrets in model output",
        )

        guard = CommandGuard()
        self.register(
            HookType.PRE_TOOL_USE,
            guard,
            priority=PRIORITY_VALIDATION,
            hook_id="builtin.command_guard.pre_tool_use",
            description="Block dangerous bash commands",
            tool_filter="Bash",
        )

        tracker = CostTracker()
        self.register(
            HookType.POST_MODEL_CALL,
            tracker,
            priority=PRIORITY_OBSERVABILITY,
            hook_id="builtin.cost_tracker.post_model_call",
            description="Track token usage for model calls",
        )
        self.register(
            HookType.POST_TOOL_USE,
            tracker,
            priority=PRIORITY_OBSERVABILITY,
            hook_id="builtin.cost_tracker.post_tool_use",
            description="Track token usage in tool context",
        )

        logger.debug("Registered %d built-in hook handlers", 5)

    def _get_matching(self, context: HookContext) -> list[Hook]:
        """Return hooks matching *context*, sorted by priority descending."""
        return self.registry.find_matching_hooks(context)

    async def _execute(
        self, hook: Hook, context: HookContext
    ) -> HookResult:
        """Execute a single hook handler with sync/async support."""
        try:
            if asyncio.iscoroutinefunction(hook.handler):
                return await hook.handler(context)
            loop = asyncio.get_event_loop()
            return await loop.run_in_executor(None, hook.handler, context)
        except Exception as e:
            logger.exception("Hook %s raised an exception", hook.hook_id)
            return HookResult(
                action=HookAction.BLOCK,
                reason=f"Hook {hook.hook_id} raised: {e}",
                hook_name=hook.hook_id,
            )

    def _record(self, hook: Hook, result: HookResult) -> None:
        """Append to execution history."""
        self.execution_history.append({
            "hook_id": hook.hook_id,
            "hook_type": hook.hook_type.value,
            "action": result.action.value,
            "success": result.success,
            "reason": result.reason,
            "timestamp": str(datetime.now()),
        })
