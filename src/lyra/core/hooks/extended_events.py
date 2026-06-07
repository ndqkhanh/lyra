"""
ExtendedEvents — expand the HookType enum from 6 to 25+ hook events.

Provides fine-grained hook points for every phase of the agent lifecycle:

    PRE / POST phases for:
        - Tool use (already in HookType)
        - Model call (already in HookType)
        - Session start/end (already in HookType)
        - Agent creation, destruction, delegation
        - Skill loading, execution, unloading
        - Memory read, write, consolidate
        - Research pipeline stages
        - Error handling
        - Permission checking
        - Worktree operations
        - State transitions
        - Configuration changes
        - Fleet coordination

Also provides an ExtendedEventEmitter for triggering these events.
"""

from __future__ import annotations

import logging
import time
import uuid
from dataclasses import dataclass, field
from enum import Enum
from typing import Any, Callable

logger = logging.getLogger(__name__)


# =============================================================================
# ExtendedHookType — 25+ hook events
# =============================================================================


class ExtendedHookType(str, Enum):
    """Extended hook events covering the full agent lifecycle.

    Naming convention: {PHASE}_{STAGE} where PHASE is PRE or POST
    and STAGE describes the lifecycle point.
    """

    # --- Core (inherited from HookType) ---
    PRE_TOOL_USE = "pre_tool_use"
    POST_TOOL_USE = "post_tool_use"
    PRE_MODEL_CALL = "pre_model_call"
    POST_MODEL_CALL = "post_model_call"
    SESSION_START = "session_start"
    SESSION_END = "session_end"

    # --- Agent lifecycle ---
    PRE_AGENT_CREATE = "pre_agent_create"
    POST_AGENT_CREATE = "post_agent_create"
    PRE_AGENT_DESTROY = "pre_agent_destroy"
    POST_AGENT_DESTROY = "post_agent_destroy"
    PRE_AGENT_DELEGATE = "pre_agent_delegate"
    POST_AGENT_DELEGATE = "post_agent_delegate"
    PRE_AGENT_RESUME = "pre_agent_resume"
    POST_AGENT_RESUME = "post_agent_resume"

    # --- Skills ---
    PRE_SKILL_LOAD = "pre_skill_load"
    POST_SKILL_LOAD = "post_skill_load"
    PRE_SKILL_EXECUTE = "pre_skill_execute"
    POST_SKILL_EXECUTE = "post_skill_execute"
    PRE_SKILL_UNLOAD = "pre_skill_unload"
    POST_SKILL_UNLOAD = "post_skill_unload"

    # --- Memory ---
    PRE_MEMORY_READ = "pre_memory_read"
    POST_MEMORY_READ = "post_memory_read"
    PRE_MEMORY_WRITE = "pre_memory_write"
    POST_MEMORY_WRITE = "post_memory_write"
    PRE_MEMORY_CONSOLIDATE = "pre_memory_consolidate"
    POST_MEMORY_CONSOLIDATE = "post_memory_consolidate"
    PRE_MEMORY_DREAM = "pre_memory_dream"
    POST_MEMORY_DREAM = "post_memory_dream"

    # --- Research pipeline ---
    PRE_RESEARCH_QUERY = "pre_research_query"
    POST_RESEARCH_QUERY = "post_research_query"
    PRE_RESEARCH_SYNTHESIS = "pre_research_synthesis"
    POST_RESEARCH_SYNTHESIS = "post_research_synthesis"
    PRE_ADVERSARIAL_CHECK = "pre_adversarial_check"
    POST_ADVERSARIAL_CHECK = "post_adversarial_check"

    # --- Errors ---
    ON_ERROR = "on_error"
    ON_RECOVERY = "on_recovery"
    ON_RETRY = "on_retry"
    ON_CIRCUIT_BREAK = "on_circuit_break"
    ON_CIRCUIT_RESET = "on_circuit_reset"

    # --- Permissions ---
    PRE_PERMISSION_CHECK = "pre_permission_check"
    POST_PERMISSION_CHECK = "post_permission_check"
    PRE_PERMISSION_GRANT = "pre_permission_grant"
    POST_PERMISSION_GRANT = "post_permission_grant"

    # --- Worktree ---
    PRE_WORKTREE_CREATE = "pre_worktree_create"
    POST_WORKTREE_CREATE = "post_worktree_create"
    PRE_WORKTREE_DESTROY = "pre_worktree_destroy"
    POST_WORKTREE_DESTROY = "post_worktree_destroy"

    # --- State transitions ---
    ON_STATE_CHANGE = "on_state_change"
    PRE_STATE_SAVE = "pre_state_save"
    POST_STATE_SAVE = "post_state_save"
    PRE_STATE_LOAD = "pre_state_load"
    POST_STATE_LOAD = "post_state_load"

    # --- Configuration ---
    PRE_CONFIG_CHANGE = "pre_config_change"
    POST_CONFIG_CHANGE = "post_config_change"
    PRE_CONFIG_RELOAD = "pre_config_reload"
    POST_CONFIG_RELOAD = "post_config_reload"

    # --- Fleet coordination ---
    PRE_FLEET_SYNC = "pre_fleet_sync"
    POST_FLEET_SYNC = "post_fleet_sync"
    PRE_FLEET_ELECTION = "pre_fleet_election"
    POST_FLEET_ELECTION = "post_fleet_election"

    # --- Transport ---
    PRE_TRANSPORT_CONNECT = "pre_transport_connect"
    POST_TRANSPORT_CONNECT = "post_transport_connect"
    PRE_TRANSPORT_DISCONNECT = "pre_transport_disconnect"
    POST_TRANSPORT_DISCONNECT = "post_transport_disconnect"

    # --- System ---
    ON_BOOT = "on_boot"
    ON_SHUTDOWN = "on_shutdown"
    ON_HEALTH_CHECK = "on_health_check"
    ON_IDLE = "on_idle"
    ON_BUSY = "on_busy"


# =============================================================================
# Event data
# =============================================================================


@dataclass
class ExtendedEvent:
    """A single extended event with payload.

    Attributes:
        event_id: Unique event identifier.
        hook_type: The extended hook type.
        source: Source component (e.g., "agent", "memory", "research").
        payload: Event-specific data.
        timestamp: When the event was created.
        metadata: Additional metadata.
    """

    event_id: str = ""
    hook_type: ExtendedHookType = ExtendedHookType.ON_BOOT
    source: str = ""
    payload: dict[str, Any] = field(default_factory=dict)
    timestamp: float = 0.0
    metadata: dict[str, Any] = field(default_factory=dict)

    def __post_init__(self) -> None:
        if not self.event_id:
            self.event_id = str(uuid.uuid4())
        if not self.timestamp:
            self.timestamp = time.time()


# =============================================================================
# ExtendedEventEmitter
# =============================================================================


class ExtendedEventEmitter:
    """Emits extended lifecycle events and dispatches to registered listeners.

    Each ExtendedHookType can have multiple listeners.  Listeners are
    called synchronously in registration order.  PRE-phase listeners
    return events that may be modified; POST-phase listeners are
    fire-and-forget.

    Attributes:
        strict: If True, raise on listener errors.  If False, log and
            continue.
    """

    def __init__(self, strict: bool = False) -> None:
        self.strict = strict
        self._listeners: dict[ExtendedHookType, list[Callable[[ExtendedEvent], ExtendedEvent | None]]] = {}

    # ------------------------------------------------------------------
    # Registration
    # ------------------------------------------------------------------

    def on(
        self,
        hook_type: ExtendedHookType,
        listener: Callable[[ExtendedEvent], ExtendedEvent | None],
    ) -> None:
        """Register a listener for an extended hook type.

        Args:
            hook_type: The hook type to listen for.
            listener: Callable that receives an ExtendedEvent and may
                return a (possibly modified) ExtendedEvent, or None.
        """
        self._listeners.setdefault(hook_type, []).append(listener)

    def off(
        self,
        hook_type: ExtendedHookType,
        listener: Callable | None = None,
    ) -> int:
        """Unregister a listener.

        Args:
            hook_type: The hook type.
            listener: Specific listener to remove, or None to remove all.

        Returns:
            Number of listeners removed.
        """
        if listener is None:
            count = len(self._listeners.get(hook_type, []))
            self._listeners.pop(hook_type, None)
            return count

        listeners = self._listeners.get(hook_type, [])
        before = len(listeners)
        self._listeners[hook_type] = [l for l in listeners if l is not listener]
        return before - len(self._listeners[hook_type])

    def has_listeners(self, hook_type: ExtendedHookType) -> bool:
        """Check if a hook type has registered listeners."""
        return bool(self._listeners.get(hook_type))

    def listener_count(self, hook_type: ExtendedHookType | None = None) -> int:
        """Count registered listeners.

        Args:
            hook_type: Optional filter by hook type.

        Returns:
            Number of listeners.
        """
        if hook_type:
            return len(self._listeners.get(hook_type, []))
        return sum(len(ll) for ll in self._listeners.values())

    # ------------------------------------------------------------------
    # Emission
    # ------------------------------------------------------------------

    def emit(
        self,
        hook_type: ExtendedHookType,
        source: str = "",
        payload: dict[str, Any] | None = None,
        metadata: dict[str, Any] | None = None,
    ) -> ExtendedEvent:
        """Emit an extended event and notify registered listeners.

        Args:
            hook_type: The hook type to emit.
            source: Source component name.
            payload: Event payload data.
            metadata: Additional metadata.

        Returns:
            The (possibly modified) ExtendedEvent.
        """
        event = ExtendedEvent(
            hook_type=hook_type,
            source=source,
            payload=payload or {},
            metadata=metadata or {},
        )

        listeners = self._listeners.get(hook_type, [])
        if not listeners:
            return event

        for listener in listeners:
            try:
                result = listener(event)
                if result is not None:
                    event = result
            except Exception as e:
                if self.strict:
                    raise
                logger.warning(
                    "ExtendedEventEmitter: listener error for %s: %s",
                    hook_type.value, e,
                )

        return event

    def emit_pre(self, *args: Any, **kwargs: Any) -> ExtendedEvent:
        """Alias for emit()."""
        return self.emit(*args, **kwargs)

    def emit_post(self, *args: Any, **kwargs: Any) -> ExtendedEvent:
        """Emit a post-phase event (fire-and-forget, no return)."""
        event = ExtendedEvent(
            hook_type=kwargs.get("hook_type", ExtendedHookType.POST_TOOL_USE),
            source=kwargs.get("source", ""),
            payload=kwargs.get("payload", {}),
            metadata=kwargs.get("metadata", {}),
        )

        listeners = self._listeners.get(event.hook_type, [])
        for listener in listeners:
            try:
                listener(event)
            except Exception as e:
                if self.strict:
                    raise
                logger.warning(
                    "ExtendedEventEmitter: post-listener error for %s: %s",
                    event.hook_type.value, e,
                )

        return event

    # ------------------------------------------------------------------
    # Event categories
    # ------------------------------------------------------------------

    def emit_agent_event(
        self,
        stage: str,
        agent_id: str,
        action: str,
        extra: dict[str, Any] | None = None,
    ) -> ExtendedEvent:
        """Emit an agent lifecycle event.

        Args:
            stage: "pre" or "post".
            agent_id: The agent's ID.
            action: The action (create, destroy, delegate, resume).
            extra: Additional payload data.

        Returns:
            The emitted event.
        """
        type_map: dict[str, ExtendedHookType] = {
            "pre_create": ExtendedHookType.PRE_AGENT_CREATE,
            "post_create": ExtendedHookType.POST_AGENT_CREATE,
            "pre_destroy": ExtendedHookType.PRE_AGENT_DESTROY,
            "post_destroy": ExtendedHookType.POST_AGENT_DESTROY,
            "pre_delegate": ExtendedHookType.PRE_AGENT_DELEGATE,
            "post_delegate": ExtendedHookType.POST_AGENT_DELEGATE,
            "pre_resume": ExtendedHookType.PRE_AGENT_RESUME,
            "post_resume": ExtendedHookType.POST_AGENT_RESUME,
        }
        key = f"{stage}_{action}"
        hook_type = type_map.get(key)
        if hook_type is None:
            logger.warning("ExtendedEventEmitter: unknown agent event '%s'", key)
            return ExtendedEvent()

        return self.emit(
            hook_type=hook_type,
            source=f"agent:{agent_id}",
            payload={"agent_id": agent_id, "action": action, **(extra or {})},
        )

    def emit_memory_event(
        self,
        stage: str,
        action: str,
        memory_id: str = "",
        extra: dict[str, Any] | None = None,
    ) -> ExtendedEvent:
        """Emit a memory lifecycle event.

        Args:
            stage: "pre" or "post".
            action: "read", "write", "consolidate", "dream".
            memory_id: The memory ID.
            extra: Additional payload data.

        Returns:
            The emitted event.
        """
        type_map: dict[str, ExtendedHookType] = {
            "pre_read": ExtendedHookType.PRE_MEMORY_READ,
            "post_read": ExtendedHookType.POST_MEMORY_READ,
            "pre_write": ExtendedHookType.PRE_MEMORY_WRITE,
            "post_write": ExtendedHookType.POST_MEMORY_WRITE,
            "pre_consolidate": ExtendedHookType.PRE_MEMORY_CONSOLIDATE,
            "post_consolidate": ExtendedHookType.POST_MEMORY_CONSOLIDATE,
            "pre_dream": ExtendedHookType.PRE_MEMORY_DREAM,
            "post_dream": ExtendedHookType.POST_MEMORY_DREAM,
        }
        key = f"{stage}_{action}"
        hook_type = type_map.get(key)
        if hook_type is None:
            logger.warning("ExtendedEventEmitter: unknown memory event '%s'", key)
            return ExtendedEvent()

        return self.emit(
            hook_type=hook_type,
            source="memory",
            payload={"memory_id": memory_id, "action": action, **(extra or {})},
        )

    def emit_skill_event(
        self,
        stage: str,
        action: str,
        skill_name: str = "",
        extra: dict[str, Any] | None = None,
    ) -> ExtendedEvent:
        """Emit a skill lifecycle event.

        Args:
            stage: "pre" or "post".
            action: "load", "execute", "unload".
            skill_name: The skill name.
            extra: Additional payload data.

        Returns:
            The emitted event.
        """
        type_map: dict[str, ExtendedHookType] = {
            "pre_load": ExtendedHookType.PRE_SKILL_LOAD,
            "post_load": ExtendedHookType.POST_SKILL_LOAD,
            "pre_execute": ExtendedHookType.PRE_SKILL_EXECUTE,
            "post_execute": ExtendedHookType.POST_SKILL_EXECUTE,
            "pre_unload": ExtendedHookType.PRE_SKILL_UNLOAD,
            "post_unload": ExtendedHookType.POST_SKILL_UNLOAD,
        }
        key = f"{stage}_{action}"
        hook_type = type_map.get(key)
        if hook_type is None:
            logger.warning("ExtendedEventEmitter: unknown skill event '%s'", key)
            return ExtendedEvent()

        return self.emit(
            hook_type=hook_type,
            source=f"skill:{skill_name}",
            payload={"skill_name": skill_name, "action": action, **(extra or {})},
        )

    def emit_error_event(
        self,
        error_type: str,
        error_message: str,
        source: str = "",
        extra: dict[str, Any] | None = None,
    ) -> ExtendedEvent:
        """Emit an error lifecycle event.

        Args:
            error_type: Type of error (error, recovery, retry, circuit_break,
                circuit_reset).
            error_message: Error description.
            source: Error source component.
            extra: Additional payload data.

        Returns:
            The emitted event.
        """
        type_map: dict[str, ExtendedHookType] = {
            "error": ExtendedHookType.ON_ERROR,
            "recovery": ExtendedHookType.ON_RECOVERY,
            "retry": ExtendedHookType.ON_RETRY,
            "circuit_break": ExtendedHookType.ON_CIRCUIT_BREAK,
            "circuit_reset": ExtendedHookType.ON_CIRCUIT_RESET,
        }
        hook_type = type_map.get(error_type)
        if hook_type is None:
            logger.warning("ExtendedEventEmitter: unknown error type '%s'", error_type)
            return ExtendedEvent()

        return self.emit(
            hook_type=hook_type,
            source=source,
            payload={"error": error_message, **(extra or {})},
        )

    def emit_permission_event(
        self,
        stage: str,
        action: str,
        agent_id: str = "",
        permission: str = "",
        extra: dict[str, Any] | None = None,
    ) -> ExtendedEvent:
        """Emit a permission lifecycle event.

        Args:
            stage: "pre" or "post".
            action: "check" or "grant".
            agent_id: The agent requesting the action.
            permission: The permission being checked.
            extra: Additional payload data.

        Returns:
            The emitted event.
        """
        type_map: dict[str, ExtendedHookType] = {
            "pre_check": ExtendedHookType.PRE_PERMISSION_CHECK,
            "post_check": ExtendedHookType.POST_PERMISSION_CHECK,
            "pre_grant": ExtendedHookType.PRE_PERMISSION_GRANT,
            "post_grant": ExtendedHookType.POST_PERMISSION_GRANT,
        }
        key = f"{stage}_{action}"
        hook_type = type_map.get(key)
        if hook_type is None:
            logger.warning("ExtendedEventEmitter: unknown permission event '%s'", key)
            return ExtendedEvent()

        return self.emit(
            hook_type=hook_type,
            source=f"agent:{agent_id}" if agent_id else "permissions",
            payload={
                "agent_id": agent_id,
                "permission": permission,
                **(extra or {}),
            },
        )

    # ------------------------------------------------------------------
    # Listeners for common use cases
    # ------------------------------------------------------------------

    @staticmethod
    def logging_listener(level: str = "info") -> Callable[[ExtendedEvent], None]:
        """Create a listener that logs events.

        Args:
            level: Log level (debug, info, warning).

        Returns:
            A listener callable.
        """

        def _listener(event: ExtendedEvent) -> None:
            level_map = {
                "debug": logger.debug,
                "info": logger.info,
                "warning": logger.warning,
            }
            log_fn = level_map.get(level, logger.info)
            log_fn(
                "ExtendedEvent: %s from %s [%s]",
                event.hook_type.value, event.source, event.event_id[:8],
            )

        return _listener

    @staticmethod
    def metrics_collector() -> Callable[[ExtendedEvent], None]:
        """Create a listener that collects event metrics.

        Returns:
            A listener callable that accumulates counts.
        """
        counts: dict[str, int] = {}

        def _listener(event: ExtendedEvent) -> None:
            key = event.hook_type.value
            counts[key] = counts.get(key, 0) + 1

        # Attach a stats method to the callable
        def get_counts() -> dict[str, int]:
            return dict(counts)

        setattr(_listener, "get_counts", get_counts)
        return _listener

    # ------------------------------------------------------------------
    # Statistics
    # ------------------------------------------------------------------

    def get_statistics(self) -> dict[str, Any]:
        """Return emitter statistics."""
        return {
            "registered_hook_types": len(self._listeners),
            "total_listeners": sum(len(ll) for ll in self._listeners.values()),
            "listeners_by_type": {
                k.value: len(v) for k, v in self._listeners.items()
            },
            "strict_mode": self.strict,
        }
