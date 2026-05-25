"""Agent spawner with factory pattern, resource pre-allocation, warm-up, and health checks."""

from __future__ import annotations

import asyncio
import logging
import time
from collections.abc import Callable, Awaitable
from dataclasses import dataclass, field
from typing import Any
from uuid import uuid4

from .lifecycle import AgentLifecycleManager, AgentRecord, LifecycleState

logger = logging.getLogger(__name__)


# ---------------------------------------------------------------------------
# Custom exceptions
# ---------------------------------------------------------------------------


class SpawnError(Exception):
    """Base exception for spawn errors."""


class ResourceAllocationError(SpawnError):
    """Raised when resource pre-allocation fails."""


class HealthCheckFailedError(SpawnError):
    """Raised when a spawned agent fails its initial health check."""


class WarmupTimeoutError(SpawnError):
    """Raised when agent warm-up times out."""


# ---------------------------------------------------------------------------
# Helpers
# ---------------------------------------------------------------------------


def _new_id() -> str:
    return uuid4().hex[:12]


def _now() -> float:
    return time.monotonic()


# ---------------------------------------------------------------------------
# Dataclass models
# ---------------------------------------------------------------------------


@dataclass
class SpawnConfig:
    """Configuration for spawning an agent.

    Attributes:
        agent_type: Type of agent to spawn.
        capabilities: Initial capabilities.
        resource_limits: CPU/memory/token constraints.
        warmup_timeout: Maximum seconds for warm-up.
        health_check_required: Whether health check must pass.
        max_retries: How many times to retry spawning on failure.
        labels: Key-value labels for discovery.
        metadata: Additional configuration.
    """

    agent_type: str = "worker"
    capabilities: list[str] = field(default_factory=lambda: ["general"])
    resource_limits: dict[str, float] = field(default_factory=dict)
    warmup_timeout: float = 30.0
    health_check_required: bool = True
    max_retries: int = 3
    labels: dict[str, str] = field(default_factory=dict)
    metadata: dict[str, Any] = field(default_factory=dict)

    def __post_init__(self) -> None:
        if not self.capabilities:
            raise SpawnError("Agent must have at least one capability")
        if self.warmup_timeout <= 0:
            raise SpawnError("warmup_timeout must be positive")


@dataclass
class HealthCheckResult:
    """Result of a health check on an agent.

    Attributes:
        passed: Whether the check passed.
        agent_id: The agent checked.
        checks: Per-check results.
        latency_ms: How long the check took.
        details: Detailed output.
    """

    passed: bool = False
    agent_id: str = ""
    checks: dict[str, bool] = field(default_factory=dict)
    latency_ms: float = 0.0
    details: dict[str, Any] = field(default_factory=dict)

    @property
    def passed_count(self) -> int:
        return sum(1 for v in self.checks.values() if v)

    @property
    def total_checks(self) -> int:
        return len(self.checks)


# ---------------------------------------------------------------------------
# Health Check
# ---------------------------------------------------------------------------


class HealthCheck:
    """Runs health checks against spawned agents.

    Checks can be registered as async callables that return a boolean.
    """

    def __init__(self) -> None:
        self._checks: dict[str, Callable[[str], Awaitable[bool]]] = {}

    def register_check(self, name: str, check_fn: Callable[[str], Awaitable[bool]]) -> None:
        """Register a named health check function."""
        self._checks[name] = check_fn

    def remove_check(self, name: str) -> None:
        """Remove a registered health check."""
        self._checks.pop(name, None)

    async def run_checks(self, agent_id: str) -> HealthCheckResult:
        """Run all registered health checks against an agent."""
        if not self._checks:
            return HealthCheckResult(
                passed=True,
                agent_id=agent_id,
                checks={},
                latency_ms=0.0,
            )

        start = _now()
        results: dict[str, bool] = {}
        details: dict[str, Any] = {}

        for name, fn in self._checks.items():
            try:
                results[name] = await fn(agent_id)
            except Exception as e:
                results[name] = False
                details[name] = str(e)
                logger.warning("Health check '%s' failed with error: %s", name, e)

        elapsed = (_now() - start) * 1000
        passed = all(results.values())

        return HealthCheckResult(
            passed=passed,
            agent_id=agent_id,
            checks=results,
            latency_ms=elapsed,
            details=details,
        )


# ---------------------------------------------------------------------------
# Agent Factory
# ---------------------------------------------------------------------------


class AgentFactory:
    """Factory pattern for creating agent instances.

    Supports registering agent constructors by type and spawning
    agents with pre-configured templates.
    """

    def __init__(self) -> None:
        self._constructors: dict[str, Callable[[SpawnConfig], Awaitable[str]]] = {}
        self._templates: dict[str, SpawnConfig] = {}
        self._spawn_count: dict[str, int] = {}

    def register_constructor(
        self,
        agent_type: str,
        constructor: Callable[[SpawnConfig], Awaitable[str]],
    ) -> None:
        """Register a constructor function for an agent type."""
        self._constructors[agent_type] = constructor

    def register_template(self, name: str, config: SpawnConfig) -> None:
        """Register a spawn configuration template."""
        self._templates[name] = config

    def get_template(self, name: str) -> SpawnConfig | None:
        """Get a template by name."""
        return self._templates.get(name)

    async def build(self, config: SpawnConfig) -> str:
        """Build (instantiate) an agent from config. Returns agent ID."""
        agent_type = config.agent_type
        constructor = self._constructors.get(agent_type)

        if constructor is None:
            raise SpawnError(f"No constructor registered for agent type: {agent_type}")

        agent_id = await constructor(config)
        self._spawn_count[agent_type] = self._spawn_count.get(agent_type, 0) + 1
        logger.debug("Factory built agent %s of type %s", agent_id, agent_type)
        return agent_id

    async def build_from_template(self, template_name: str) -> str:
        """Build an agent from a pre-registered template."""
        config = self._templates.get(template_name)
        if config is None:
            raise SpawnError(f"Template not found: {template_name}")
        return await self.build(config)

    @property
    def template_names(self) -> list[str]:
        return list(self._templates.keys())

    @property
    def supported_types(self) -> list[str]:
        return list(self._constructors.keys())

    def snapshot(self) -> dict[str, Any]:
        return {
            "types": self.supported_types,
            "templates": self.template_names,
            "spawn_counts": dict(self._spawn_count),
        }


# ---------------------------------------------------------------------------
# Agent Spawner
# ---------------------------------------------------------------------------


class AgentSpawner:
    """Orchestrates agent spawning with resource pre-allocation, warm-up, and health checks.

    Workflow:
    1. Validate configuration
    2. Pre-allocate resources
    3. Build agent via factory
    4. Run warm-up phase
    5. Execute health checks
    6. Register with lifecycle manager
    """

    def __init__(
        self,
        lifecycle: AgentLifecycleManager,
        *,
        health_check: HealthCheck | None = None,
        factory: AgentFactory | None = None,
    ) -> None:
        self._lifecycle = lifecycle
        self._health_check = health_check or HealthCheck()
        self._factory = factory or AgentFactory()
        self._warmup_functions: dict[str, Callable[[str], Awaitable[None]]] = {}
        self._allocated_resources: dict[str, dict[str, float]] = {}

    # ------------------------------------------------------------------
    # Warm-up registration
    # ------------------------------------------------------------------

    def register_warmup(
        self,
        agent_type: str,
        warmup_fn: Callable[[str], Awaitable[None]],
    ) -> None:
        """Register a warm-up function for an agent type."""
        self._warmup_functions[agent_type] = warmup_fn

    # ------------------------------------------------------------------
    # Resource pre-allocation
    # ------------------------------------------------------------------

    async def _pre_allocate(self, agent_id: str, limits: dict[str, float]) -> bool:
        """Pre-allocate resources for an agent. Returns True on success."""
        try:
            self._allocated_resources[agent_id] = dict(limits)
            logger.debug("Pre-allocated resources for %s: %s", agent_id, limits)
            return True
        except Exception:
            raise ResourceAllocationError(f"Failed to allocate resources for {agent_id}")

    def _release_resources(self, agent_id: str) -> None:
        """Release allocated resources for an agent."""
        self._allocated_resources.pop(agent_id, None)

    # ------------------------------------------------------------------
    # Spawn
    # ------------------------------------------------------------------

    async def spawn(
        self,
        config: SpawnConfig,
        *,
        agent_id: str | None = None,
    ) -> AgentRecord:
        """Spawn a new agent with full lifecycle integration.

        Returns the AgentRecord of the spawned agent.
        """
        aid = agent_id or f"{config.agent_type}-{_new_id()}"
        attempts = 0

        while attempts <= config.max_retries:
            try:
                return await self._spawn_attempt(aid, config)
            except Exception as e:
                attempts += 1
                logger.warning("Spawn attempt %d/%d failed for %s: %s", attempts, config.max_retries + 1, aid, e)
                if attempts > config.max_retries:
                    raise SpawnError(f"Failed to spawn agent {aid} after {config.max_retries + 1} attempts") from e

                # Clean up partial state
                self._release_resources(aid)
                self._lifecycle.unregister_agent(aid)
                await asyncio.sleep(1.0 * attempts)

        raise SpawnError(f"Failed to spawn agent {aid}")

    async def _spawn_attempt(self, agent_id: str, config: SpawnConfig) -> AgentRecord:
        """Single spawn attempt."""
        # 1. Pre-allocate resources
        await self._pre_allocate(agent_id, config.resource_limits)

        # 2. Register with lifecycle manager (skip if already registered from retry)
        if self._lifecycle.get_state(agent_id) is None:
            self._lifecycle.register_agent(agent_id, version="1.0.0")
        logger.debug("Registered %s with lifecycle manager", agent_id)

        # 3. Build via factory
        try:
            built_id = await self._factory.build(config)
        except Exception:
            self._release_resources(agent_id)
            self._lifecycle.unregister_agent(agent_id)
            raise

        # 4. Mark as ready
        await self._lifecycle.mark_ready(agent_id, reason="spawned")

        # 5. Warm-up
        await self._warmup(agent_id, config)

        # 6. Health check
        if config.health_check_required:
            await self._run_health_check(agent_id)

        # 7. Activate
        await self._lifecycle.activate(agent_id, reason="spawn_complete")

        record = self._lifecycle._get_record(agent_id)  # type: ignore[attr-defined]
        logger.info("Spawned agent %s successfully", agent_id)
        return record

    async def spawn_from_template(
        self,
        template_name: str,
        *,
        agent_id: str | None = None,
    ) -> AgentRecord:
        """Spawn an agent from a factory template."""
        config = self._factory.get_template(template_name)
        if config is None:
            raise SpawnError(f"Template not found: {template_name}")
        return await self.spawn(config, agent_id=agent_id)

    # ------------------------------------------------------------------
    # Warm-up
    # ------------------------------------------------------------------

    async def _warmup(self, agent_id: str, config: SpawnConfig) -> None:
        """Run the warm-up phase for an agent."""
        warmup_fn = self._warmup_functions.get(config.agent_type)
        if warmup_fn is None:
            logger.debug("No warm-up registered for agent type %s", config.agent_type)
            return

        try:
            await asyncio.wait_for(
                warmup_fn(agent_id),
                timeout=config.warmup_timeout,
            )
            logger.debug("Warm-up complete for %s", agent_id)
        except asyncio.TimeoutError:
            raise WarmupTimeoutError(
                f"Warm-up timed out for {agent_id} ({config.warmup_timeout}s)"
            )

    # ------------------------------------------------------------------
    # Health check
    # ------------------------------------------------------------------

    async def _run_health_check(self, agent_id: str) -> HealthCheckResult:
        """Run health checks and raise if they fail."""
        result = await self._health_check.run_checks(agent_id)
        if not result.passed:
            raise HealthCheckFailedError(
                f"Health check failed for {agent_id}: {result.passed_count}/{result.total_checks} passed"
            )
        logger.debug("Health check passed for %s", agent_id)
        return result

    # ------------------------------------------------------------------
    # Queries
    # ------------------------------------------------------------------

    def get_allocated_resources(self, agent_id: str) -> dict[str, float]:
        """Get currently allocated resources for an agent."""
        return dict(self._allocated_resources.get(agent_id, {}))

    def get_total_allocation(self) -> dict[str, float]:
        """Get total resource allocation across all agents."""
        totals: dict[str, float] = {}
        for resources in self._allocated_resources.values():
            for k, v in resources.items():
                totals[k] = totals.get(k, 0.0) + v
        return totals

    async def health_check_now(self, agent_id: str) -> HealthCheckResult:
        """Run an ad-hoc health check on an agent."""
        return await self._health_check.run_checks(agent_id)

    def snapshot(self) -> dict[str, Any]:
        """Return current state snapshot."""
        return {
            "factory": self._factory.snapshot(),
            "allocated_agents": len(self._allocated_resources),
            "total_resources": self.get_total_allocation(),
            "warmup_types": list(self._warmup_functions.keys()),
        }
