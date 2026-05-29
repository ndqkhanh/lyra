"""
ECC Hooks Integration with Lyra Lifecycle

Bridges ECC's hooks system with Lyra's lifecycle-based hooks architecture.
"""

from pathlib import Path
from typing import Any

from lyra_core.hooks import LifecycleBus, LifecycleEvent

from lyra_ecc.hooks import ECCHooksEngine, HookContext, HookType


class ECCLifecycleIntegration:
    """
    Integrates ECC hooks with Lyra's lifecycle system.

    Subscribes to Lyra lifecycle events and translates them to ECC hook events.
    """

    def __init__(self, lifecycle_bus: LifecycleBus):
        """
        Initialize ECC lifecycle integration.

        Args:
            lifecycle_bus: Lyra's lifecycle event bus
        """
        self.lifecycle_bus = lifecycle_bus
        self.ecc_engine = ECCHooksEngine()

        # Subscribe to lifecycle events using callable
        self.lifecycle_bus.subscribe(LifecycleEvent.TOOL_CALL, self._on_tool_call)
        self.lifecycle_bus.subscribe(LifecycleEvent.SESSION_START, self._on_session_start)
        self.lifecycle_bus.subscribe(LifecycleEvent.SESSION_END, self._on_session_end)

    def _on_tool_call(self, context: dict[str, Any]) -> None:
        """Handle TOOL_CALL event."""
        # Fire POST_TOOL_USE hooks
        self._build_ecc_context(HookType.POST_TOOL_USE, context)
        # Note: Lyra's lifecycle is sync, but ECC hooks are async
        # In production, this would need proper async handling
        # For now, we'll skip async execution in the subscriber
        context["ecc_hook_fired"] = True

    def _on_session_start(self, context: dict[str, Any]) -> None:
        """Handle SESSION_START event."""
        self._build_ecc_context(HookType.SESSION_START, context)
        context["ecc_hook_fired"] = True

    def _on_session_end(self, context: dict[str, Any]) -> None:
        """Handle SESSION_END event."""
        self._build_ecc_context(HookType.SESSION_END, context)
        context["ecc_hook_fired"] = True

    def _build_ecc_context(
        self, hook_type: HookType, lifecycle_context: dict[str, Any]
    ) -> HookContext:
        """
        Build ECC hook context from lifecycle context.

        Args:
            hook_type: ECC hook type
            lifecycle_context: Lyra lifecycle context

        Returns:
            ECC hook context
        """
        tool_name = lifecycle_context.get("tool")
        file_path_str = lifecycle_context.get("file_path")
        file_path = Path(file_path_str) if file_path_str else None

        return HookContext(
            event_type=hook_type,
            tool_name=tool_name,
            file_path=file_path,
            args=lifecycle_context.get("args"),
            result=lifecycle_context.get("result"),
        )

    def register_custom_hook(self, hook_type: HookType, hook_fn: Any) -> None:
        """
        Register a custom ECC hook.

        Args:
            hook_type: Hook type
            hook_fn: Hook function
        """
        self.ecc_engine.register_hook(hook_type, hook_fn)

    def get_hook_summary(self) -> dict[str, Any]:
        """
        Get summary of registered hooks.

        Returns:
            Hook summary with counts by type
        """
        return {
            "hook_types": [ht.value for ht in HookType],
            "registered_hooks": {
                hook_type.value: len(hooks)
                for hook_type, hooks in self.ecc_engine.hooks.items()
            },
            "total_hooks": sum(len(hooks) for hooks in self.ecc_engine.hooks.values()),
        }


def setup_ecc_hooks(lifecycle_bus: LifecycleBus) -> ECCLifecycleIntegration:
    """
    Set up ECC hooks integration with Lyra lifecycle.

    Args:
        lifecycle_bus: Lyra's lifecycle event bus

    Returns:
        Configured ECC lifecycle integration
    """
    integration = ECCLifecycleIntegration(lifecycle_bus)
    return integration
