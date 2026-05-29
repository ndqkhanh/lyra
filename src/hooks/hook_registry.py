"""
Hook registry for managing registered hooks.
"""

from typing import Any

from .hook import Hook, HookContext, HookType


class HookRegistry:
    """
    Registry for managing hooks.

    Stores and retrieves hooks by type and priority.
    """

    def __init__(self):
        """Initialize hook registry."""
        self.hooks: dict[str, Hook] = {}
        self._hooks_by_type: dict[HookType, list[Hook]] = {
            hook_type: [] for hook_type in HookType
        }

    def register(self, hook: Hook) -> None:
        """
        Register a hook.

        Args:
            hook: Hook to register
        """
        if hook.hook_id in self.hooks:
            raise ValueError(f"Hook {hook.hook_id} already registered")

        self.hooks[hook.hook_id] = hook
        self._hooks_by_type[hook.hook_type].append(hook)

        # Sort by priority (higher first)
        self._hooks_by_type[hook.hook_type].sort(
            key=lambda h: h.priority, reverse=True
        )

    def unregister(self, hook_id: str) -> bool:
        """
        Unregister a hook.

        Args:
            hook_id: Hook ID to unregister

        Returns:
            True if unregistered, False if not found
        """
        if hook_id not in self.hooks:
            return False

        hook = self.hooks[hook_id]
        del self.hooks[hook_id]
        self._hooks_by_type[hook.hook_type].remove(hook)
        return True

    def get(self, hook_id: str) -> Hook | None:
        """
        Get a hook by ID.

        Args:
            hook_id: Hook ID

        Returns:
            Hook if found, None otherwise
        """
        return self.hooks.get(hook_id)

    def find_matching_hooks(self, context: HookContext) -> list[Hook]:
        """
        Find all hooks that match the given context.

        Args:
            context: Hook context

        Returns:
            List of matching hooks, sorted by priority
        """
        hooks = self._hooks_by_type.get(context.hook_type, [])
        return [hook for hook in hooks if hook.matches(context)]

    def list_hooks(
        self,
        hook_type: HookType | None = None,
        enabled_only: bool = False,
    ) -> list[Hook]:
        """
        List registered hooks.

        Args:
            hook_type: Filter by hook type
            enabled_only: Only return enabled hooks

        Returns:
            List of hooks
        """
        if hook_type:
            hooks = self._hooks_by_type.get(hook_type, [])
        else:
            hooks = list(self.hooks.values())

        if enabled_only:
            hooks = [h for h in hooks if h.enabled]

        return hooks

    def enable(self, hook_id: str) -> bool:
        """
        Enable a hook.

        Args:
            hook_id: Hook ID

        Returns:
            True if enabled, False if not found
        """
        hook = self.hooks.get(hook_id)
        if hook:
            hook.enabled = True
            return True
        return False

    def disable(self, hook_id: str) -> bool:
        """
        Disable a hook.

        Args:
            hook_id: Hook ID

        Returns:
            True if disabled, False if not found
        """
        hook = self.hooks.get(hook_id)
        if hook:
            hook.enabled = False
            return True
        return False

    def clear(self) -> None:
        """Clear all hooks."""
        self.hooks.clear()
        for hook_type in HookType:
            self._hooks_by_type[hook_type].clear()

    def get_statistics(self) -> dict[str, Any]:
        """
        Get registry statistics.

        Returns:
            Statistics dictionary
        """
        return {
            "total_hooks": len(self.hooks),
            "by_type": {
                hook_type.value: len(hooks)
                for hook_type, hooks in self._hooks_by_type.items()
            },
            "enabled": sum(1 for h in self.hooks.values() if h.enabled),
            "disabled": sum(1 for h in self.hooks.values() if not h.enabled),
        }
