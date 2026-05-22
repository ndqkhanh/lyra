"""
Hook execution engine.
"""

import asyncio
from typing import Any, Dict, List, Optional

from .hook import Hook, HookType, HookContext, HookResult
from .hook_registry import HookRegistry


class HookEngine:
    """
    Engine for executing hooks.

    Manages hook execution, error handling, and result aggregation.
    """

    def __init__(self, registry: Optional[HookRegistry] = None):
        """
        Initialize hook engine.

        Args:
            registry: Hook registry (creates new if not provided)
        """
        self.registry = registry or HookRegistry()
        self.execution_history: List[Dict[str, Any]] = []

    async def fire(
        self,
        hook_type: HookType,
        tool_name: Optional[str] = None,
        tool_args: Optional[Dict[str, Any]] = None,
        tool_result: Optional[Any] = None,
        session_id: Optional[str] = None,
        metadata: Optional[Dict[str, Any]] = None,
    ) -> List[HookResult]:
        """
        Fire hooks for a given event.

        Args:
            hook_type: Type of hook to fire
            tool_name: Name of tool (for tool-related hooks)
            tool_args: Tool arguments (for tool-related hooks)
            tool_result: Tool result (for PostToolUse hooks)
            session_id: Session ID
            metadata: Additional metadata

        Returns:
            List of hook results
        """
        # Create context
        context = HookContext(
            hook_type=hook_type,
            tool_name=tool_name,
            tool_args=tool_args,
            tool_result=tool_result,
            session_id=session_id,
            metadata=metadata or {},
        )

        # Find matching hooks
        hooks = self.registry.find_matching_hooks(context)

        # Execute hooks
        results = []
        for hook in hooks:
            try:
                result = await self._execute_hook(hook, context)
                results.append(result)

                # Record execution
                self.execution_history.append({
                    "hook_id": hook.hook_id,
                    "hook_type": hook_type.value,
                    "tool_name": tool_name,
                    "success": result.success,
                    "timestamp": context.timestamp,
                })

                # Stop on first failure if critical
                if not result.success and hook.metadata.get("critical", False):
                    break

            except Exception as e:
                error_result = HookResult.fail(f"Hook execution failed: {str(e)}")
                results.append(error_result)

                self.execution_history.append({
                    "hook_id": hook.hook_id,
                    "hook_type": hook_type.value,
                    "tool_name": tool_name,
                    "success": False,
                    "error": str(e),
                    "timestamp": context.timestamp,
                })

        return results

    async def _execute_hook(self, hook: Hook, context: HookContext) -> HookResult:
        """
        Execute a single hook.

        Args:
            hook: Hook to execute
            context: Hook context

        Returns:
            Hook result
        """
        # Check if handler is async
        if asyncio.iscoroutinefunction(hook.handler):
            return await hook.handler(context)
        else:
            # Run sync handler in executor
            loop = asyncio.get_event_loop()
            return await loop.run_in_executor(None, hook.handler, context)

    def fire_sync(
        self,
        hook_type: HookType,
        tool_name: Optional[str] = None,
        tool_args: Optional[Dict[str, Any]] = None,
        tool_result: Optional[Any] = None,
        session_id: Optional[str] = None,
        metadata: Optional[Dict[str, Any]] = None,
    ) -> List[HookResult]:
        """
        Fire hooks synchronously.

        Args:
            hook_type: Type of hook to fire
            tool_name: Name of tool
            tool_args: Tool arguments
            tool_result: Tool result
            session_id: Session ID
            metadata: Additional metadata

        Returns:
            List of hook results
        """
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

    def get_execution_history(
        self,
        hook_type: Optional[HookType] = None,
        limit: int = 100,
    ) -> List[Dict[str, Any]]:
        """
        Get hook execution history.

        Args:
            hook_type: Filter by hook type
            limit: Maximum number of entries

        Returns:
            List of execution records
        """
        history = self.execution_history

        if hook_type:
            history = [
                h for h in history
                if h["hook_type"] == hook_type.value
            ]

        return history[-limit:]

    def clear_history(self) -> None:
        """Clear execution history."""
        self.execution_history.clear()

    def get_statistics(self) -> Dict[str, Any]:
        """
        Get execution statistics.

        Returns:
            Statistics dictionary
        """
        total = len(self.execution_history)
        successful = sum(1 for h in self.execution_history if h["success"])

        by_type = {}
        for record in self.execution_history:
            hook_type = record["hook_type"]
            if hook_type not in by_type:
                by_type[hook_type] = {"total": 0, "successful": 0}
            by_type[hook_type]["total"] += 1
            if record["success"]:
                by_type[hook_type]["successful"] += 1

        return {
            "total_executions": total,
            "successful": successful,
            "failed": total - successful,
            "success_rate": successful / total if total > 0 else 0.0,
            "by_type": by_type,
            "registry_stats": self.registry.get_statistics(),
        }
