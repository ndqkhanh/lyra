"""lyra-colony — Self-organizing agent colony runtime with emergent coordination.

Provides:
- Colony manager with agent spawning, monitoring, retirement
- Agent specification system with role definitions and resource limits
- Priority-queue scheduler with affinity-based assignment and load balancing
- Inter-agent communication (pub/sub, broadcast, request-reply)
- Colony observability with metrics, alerting, and audit logging
"""

from __future__ import annotations

from .agent_spec import (
    AgentRole,
    AgentRoleKind,
    AgentSpec,
    CapabilityConflictError,
    InvalidSpecError,
    LifecycleHooks,
    ResourceLimitExceededError,
    ResourceLimits,
    SkillLevel,
    SkillRequirement,
)
from .colony import (
    AgentColony,
    AgentNotFoundError,
    ColonyConfig,
    ColonyError,
    ColonyHealth,
    ColonyOverCapacityError,
    ColonyState,
    SpawnFailedError,
)
from .communication import (
    Channel,
    ChannelNotFoundError,
    CommunicationError,
    Message,
    MessageBus,
    MessageDeliveryError,
    MessageDeliveryReceipt,
    MessagePriority,
    Protocol,
    SubscriptionError,
)
from .monitoring import (
    AgentStatus,
    Alert,
    AlertRule,
    AlertSeverity,
    AlertThresholdExceededError,
    AuditEntry,
    ColonyMonitor,
    MetricsSnapshot,
    MonitoringError,
)
from .scheduler import (
    ColonyScheduler,
    DeadlineExceededError,
    DuplicateTaskError,
    NoAvailableAgentError,
    SchedulerMetrics,
    SchedulingError,
    SchedulingStrategy,
    Task,
    TaskAssignment,
    TaskState,
)

__version__ = "0.2.0"

__all__ = [
    # Agent Spec
    "AgentRole",
    "AgentRoleKind",
    "AgentSpec",
    "SkillLevel",
    "SkillRequirement",
    "ResourceLimits",
    "LifecycleHooks",
    "InvalidSpecError",
    "CapabilityConflictError",
    "ResourceLimitExceededError",
    # Colony
    "AgentColony",
    "ColonyConfig",
    "ColonyState",
    "ColonyHealth",
    "ColonyError",
    "AgentNotFoundError",
    "ColonyOverCapacityError",
    "SpawnFailedError",
    # Communication
    "Message",
    "MessagePriority",
    "MessageDeliveryReceipt",
    "Protocol",
    "Channel",
    "MessageBus",
    "CommunicationError",
    "ChannelNotFoundError",
    "MessageDeliveryError",
    "SubscriptionError",
    # Monitoring
    "AgentStatus",
    "MetricsSnapshot",
    "Alert",
    "AlertSeverity",
    "AlertRule",
    "AuditEntry",
    "ColonyMonitor",
    "MonitoringError",
    "AlertThresholdExceededError",
    # Scheduler
    "Task",
    "TaskState",
    "TaskAssignment",
    "ColonyScheduler",
    "SchedulingStrategy",
    "SchedulerMetrics",
    "SchedulingError",
    "NoAvailableAgentError",
    "DeadlineExceededError",
    "DuplicateTaskError",
]
