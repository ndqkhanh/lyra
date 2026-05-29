"""Adapter layer — bridges existing agent systems to the unified AgentProtocol.

Each adapter wraps one of the 5 existing agent hierarchies:
  - LegacyAgentAdapter: src/agents/base.py Agent ABC
  - CoreLoopAdapter: lyra-core/agent/loop.py AgentLoop
  - SwarmAgentAdapter: lyra-agent-swarm discipline agents
  - PentestAgentAdapter: lyra-pentest agents
  - OrchestrationAdapter: lyra-orchestration AgentCoordinator

Adapters implement AgentProtocol by delegating to the wrapped system.
This lets us migrate incrementally — new agents use AgentProtocol directly,
old agents are wrapped.
"""

from __future__ import annotations

import asyncio
import logging
import time
from collections.abc import AsyncIterator
from typing import Any

from lyra_core.protocol import (
    AgentHealth,
    AgentIdentity,
    AgentLifecycle,
    AgentMode,
    AgentProtocol,
    AgentState,
    Task,
)

logger = logging.getLogger(__name__)


# ── Base Adapter ────────────────────────────────────────────────────────────


class BaseAgentAdapter:
    """Shared adapter logic. Subclasses override the wrapping."""

    def __init__(self, identity: AgentIdentity) -> None:
        self._identity = identity
        self._lifecycle = AgentLifecycle.REGISTERED
        self._health = AgentHealth.UNKNOWN
        self._state_since = time.time()
        self._modes: list[AgentMode] = []

    @property
    def identity(self) -> AgentIdentity:
        return self._identity

    @property
    def state(self) -> AgentState:
        return AgentState(
            lifecycle=self._lifecycle,
            health=self._health,
            since=self._state_since,
        )

    @property
    def mode_stack(self) -> tuple[AgentMode, ...]:
        return tuple(self._modes)

    def push_mode(self, mode: AgentMode) -> None:
        self._modes.append(mode)
        asyncio.create_task(mode.on_enter(self))

    def pop_mode(self) -> AgentMode:
        if not self._modes:
            raise IndexError("Mode stack is empty")
        mode = self._modes.pop()
        asyncio.create_task(mode.on_exit(self))
        return mode

    def supports(self, capability: str) -> bool:
        return capability in self._identity.capabilities

    def _set_healthy(self) -> None:
        self._health = AgentHealth.HEALTHY
        self._state_since = time.time()

    def _set_degraded(self) -> None:
        self._health = AgentHealth.DEGRADED
        self._state_since = time.time()

    def _set_unhealthy(self) -> None:
        self._health = AgentHealth.UNHEALTHY
        self._state_since = time.time()


# ── Legacy Agent Adapter ────────────────────────────────────────────────────


class LegacyAgentAdapter(BaseAgentAdapter, AgentProtocol):
    """Wraps an agent from src/agents/base.py Agent ABC.

    The legacy Agent ABC provides:
      - process_task() → str
      - capabilities property
      - memory system (STM, LTM, retriever, consolidator)
    """

    def __init__(self, identity: AgentIdentity, legacy_agent: Any) -> None:
        super().__init__(identity)
        self._wrapped = legacy_agent

    async def initialize(self) -> None:
        self._lifecycle = AgentLifecycle.INITIALIZING
        try:
            if hasattr(self._wrapped, "initialize"):
                await self._wrapped.initialize()
            self._set_healthy()
            self._lifecycle = AgentLifecycle.READY
        except Exception:
            self._set_unhealthy()
            self._lifecycle = AgentLifecycle.DEGRADED
            raise

    async def run(self, task: Task) -> AsyncIterator[str]:
        self._lifecycle = AgentLifecycle.ACTIVE
        try:
            if hasattr(self._wrapped, "process_task"):
                result = await self._wrapped.process_task(task.instruction)
                yield str(result)
            else:
                yield f"[LegacyAgentAdapter] {self._identity.agent_id}: no process_task method"
        except Exception as exc:
            self._set_degraded()
            yield f"Error: {exc}"
        finally:
            self._lifecycle = AgentLifecycle.IDLE

    async def shutdown(self) -> None:
        self._lifecycle = AgentLifecycle.STOPPING
        if hasattr(self._wrapped, "shutdown"):
            await self._wrapped.shutdown()
        self._lifecycle = AgentLifecycle.TERMINATED

    async def snapshot(self) -> dict[str, Any]:
        caps = list(self._identity.capabilities)
        return {
            "adapter": "LegacyAgentAdapter",
            "agent_id": self._identity.agent_id,
            "capabilities": caps,
            "wrapped_type": type(self._wrapped).__name__,
        }


# ── Core Loop Adapter ───────────────────────────────────────────────────────


class CoreLoopAdapter(BaseAgentAdapter, AgentProtocol):
    """Wraps a lyra-core AgentLoop as an AgentProtocol.

    AgentLoop.run_conversation() is synchronous/single-turn. The adapter
    calls it per task and yields the final result.
    """

    def __init__(self, identity: AgentIdentity, agent_loop: Any) -> None:
        super().__init__(identity)
        self._wrapped = agent_loop

    async def initialize(self) -> None:
        self._lifecycle = AgentLifecycle.INITIALIZING
        self._set_healthy()
        self._lifecycle = AgentLifecycle.READY

    async def run(self, task: Task) -> AsyncIterator[str]:
        self._lifecycle = AgentLifecycle.ACTIVE
        try:
            if hasattr(self._wrapped, "run_conversation"):
                result = self._wrapped.run_conversation(task.instruction)
                yield str(result)
            else:
                yield f"[CoreLoopAdapter] {self._identity.agent_id}: no run_conversation"
        except Exception as exc:
            self._set_degraded()
            yield f"Error: {exc}"
        finally:
            self._lifecycle = AgentLifecycle.IDLE

    async def shutdown(self) -> None:
        self._lifecycle = AgentLifecycle.TERMINATED

    async def snapshot(self) -> dict[str, Any]:
        return {
            "adapter": "CoreLoopAdapter",
            "agent_id": self._identity.agent_id,
        }


# ── Swarm Agent Adapter ─────────────────────────────────────────────────────


class SwarmAgentAdapter(BaseAgentAdapter, AgentProtocol):
    """Wraps a lyra-agent-swarm discipline agent."""

    def __init__(self, identity: AgentIdentity, discipline_agent: Any) -> None:
        super().__init__(identity)
        self._wrapped = discipline_agent

    async def initialize(self) -> None:
        self._lifecycle = AgentLifecycle.INITIALIZING
        self._set_healthy()
        self._lifecycle = AgentLifecycle.READY

    async def run(self, task: Task) -> AsyncIterator[str]:
        self._lifecycle = AgentLifecycle.ACTIVE
        try:
            if hasattr(self._wrapped, "execute"):
                result = await self._wrapped.execute(task.instruction)
                yield str(result)
            else:
                yield f"[SwarmAgentAdapter] {self._identity.agent_id}: no execute method"
        except Exception as exc:
            self._set_degraded()
            yield f"Error: {exc}"
        finally:
            self._lifecycle = AgentLifecycle.IDLE

    async def shutdown(self) -> None:
        self._lifecycle = AgentLifecycle.TERMINATED

    async def snapshot(self) -> dict[str, Any]:
        return {
            "adapter": "SwarmAgentAdapter",
            "agent_id": self._identity.agent_id,
            "discipline": getattr(self._wrapped, "discipline", "unknown"),
        }


# ── Pentest Agent Adapter ───────────────────────────────────────────────────


class PentestAgentAdapter(BaseAgentAdapter, AgentProtocol):
    """Wraps a lyra-pentest agent (ARTEMIS framework)."""

    def __init__(self, identity: AgentIdentity, pentest_agent: Any) -> None:
        super().__init__(identity)
        self._wrapped = pentest_agent

    async def initialize(self) -> None:
        self._lifecycle = AgentLifecycle.INITIALIZING
        self._set_healthy()
        self._lifecycle = AgentLifecycle.READY

    async def run(self, task: Task) -> AsyncIterator[str]:
        self._lifecycle = AgentLifecycle.ACTIVE
        try:
            if hasattr(self._wrapped, "run"):
                result = await self._wrapped.run(task.instruction)
                yield str(result)
            else:
                yield f"[PentestAgentAdapter] {self._identity.agent_id}: no run method"
        except Exception as exc:
            self._set_degraded()
            yield f"Error: {exc}"
        finally:
            self._lifecycle = AgentLifecycle.IDLE

    async def shutdown(self) -> None:
        self._lifecycle = AgentLifecycle.TERMINATED

    async def snapshot(self) -> dict[str, Any]:
        return {
            "adapter": "PentestAgentAdapter",
            "agent_id": self._identity.agent_id,
            "phase": getattr(self._wrapped, "phase", "unknown"),
        }


# ── Adapter Registry ────────────────────────────────────────────────────────


class AdapterRegistry:
    """Registry of available adapters for wrapping legacy agent systems.

    Usage:
        registry = AdapterRegistry()
        wrapped = registry.wrap(legacy_agent, identity)
        # wrapped is now an AgentProtocol
    """

    def __init__(self) -> None:
        self._adapters: dict[str, type[BaseAgentAdapter]] = {
            "legacy": LegacyAgentAdapter,
            "core_loop": CoreLoopAdapter,
            "swarm": SwarmAgentAdapter,
            "pentest": PentestAgentAdapter,
        }

    def register(self, name: str, adapter_cls: type[BaseAgentAdapter]) -> None:
        """Register a new adapter type."""
        self._adapters[name] = adapter_cls

    def wrap(
        self,
        wrapped_agent: Any,
        identity: AgentIdentity,
        adapter_type: str | None = None,
    ) -> AgentProtocol:
        """Wrap a legacy agent in the appropriate adapter.

        If adapter_type is None, auto-detect based on the agent's module.
        """
        if adapter_type is None:
            adapter_type = self._detect_type(wrapped_agent)
        if adapter_type not in self._adapters:
            raise ValueError(
                f"Unknown adapter type: {adapter_type}. "
                f"Available: {list(self._adapters)}"
            )
        adapter_cls = self._adapters[adapter_type]
        return adapter_cls(identity, wrapped_agent)

    def _detect_type(self, agent: Any) -> str:
        """Auto-detect which adapter to use based on the agent's module path."""
        module = type(agent).__module__

        if "lyra_agent_swarm" in module or "discipline" in module:
            return "swarm"
        if "lyra_pentest" in module or "artemis" in module.lower():
            return "pentest"
        if "lyra_core" in module and hasattr(agent, "run_conversation"):
            return "core_loop"
        return "legacy"


# ── Singleton ───────────────────────────────────────────────────────────────

_adapter_registry: AdapterRegistry | None = None


def get_adapter_registry() -> AdapterRegistry:
    global _adapter_registry
    if _adapter_registry is None:
        _adapter_registry = AdapterRegistry()
    return _adapter_registry
