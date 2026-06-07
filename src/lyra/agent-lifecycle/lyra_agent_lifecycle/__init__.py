"""lyra-agent-lifecycle — Dynamic agent spawn/retire/evolve lifecycle management.

Provides:
- Agent lifecycle state machine with hooks and graceful shutdown
- Agent spawner with factory pattern and health checks
- Agent retirement with knowledge extraction and state handoff
- Agent evolution tracking with breeding, lineages, and extinction
"""

from __future__ import annotations

from .evolution import (
    CapabilityProfile,
    EvolutionTracker,
    Lineage,
    PerformanceSnapshot,
)
from .lifecycle import (
    AgentLifecycleManager,
    AgentNotReadyError,
    AgentRecord,
    InvalidTransitionError,
    LifecycleError,
    LifecycleEvent,
    LifecycleHooks,
    LifecycleState,
    ShutdownTimeoutError,
    UpgradeError,
)
from .retirement import (
    AgentAlreadyRetiredError,
    AgentRetirement,
    HandoffError,
    KnowledgeBundle,
    KnowledgeExtractionError,
    KnowledgeExtractor,
    RetirementAuditEntry,
    RetirementConfig,
    RetirementError,
    StatePreservationError,
    StatePreserver,
)
from .spawner import (
    AgentFactory,
    AgentSpawner,
    HealthCheck,
    HealthCheckFailedError,
    HealthCheckResult,
    ResourceAllocationError,
    SpawnConfig,
    SpawnError,
    WarmupTimeoutError,
)

__version__ = "0.2.0"

__all__ = [
    # Lifecycle
    "LifecycleState",
    "LifecycleEvent",
    "LifecycleHooks",
    "AgentRecord",
    "AgentLifecycleManager",
    "LifecycleError",
    "InvalidTransitionError",
    "AgentNotReadyError",
    "ShutdownTimeoutError",
    "UpgradeError",
    # Spawner
    "SpawnConfig",
    "SpawnError",
    "ResourceAllocationError",
    "HealthCheck",
    "HealthCheckResult",
    "HealthCheckFailedError",
    "WarmupTimeoutError",
    "AgentFactory",
    "AgentSpawner",
    # Retirement
    "RetirementConfig",
    "KnowledgeBundle",
    "RetirementAuditEntry",
    "KnowledgeExtractor",
    "StatePreserver",
    "AgentRetirement",
    "RetirementError",
    "AgentAlreadyRetiredError",
    "KnowledgeExtractionError",
    "StatePreservationError",
    "HandoffError",
    # Evolution
    "CapabilityProfile",
    "PerformanceSnapshot",
    "Lineage",
    "EvolutionTracker",
]
