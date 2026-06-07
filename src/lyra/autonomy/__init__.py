"""Autonomy module — continuous unattended operation with crash recovery.

Provides the continuous-operation loop that lets Lyra sessions run
without a terminal attached, managed by the supervisor daemon.

Includes self-calibrating effort regulation (SAAS-style over-search
mitigation), the AutonomousAgent wrapper with daemon mode, health
monitoring, self-diagnosis, sleep/wake cycling, resource quotas,
and continuous health monitoring.
"""

from lyra.autonomy.continuous_monitor import (
    AlertKind,
    AlertSeverity,
    ContinuousMonitor,
    MetricsSnapshot,
    MonitorAlert,
    MonitorConfig,
)
from lyra.autonomy.effort_regulator import (
    Budget,
    EffortLevel,
    EffortProfile,
    EffortRegulator,
    SessionState,
    TaskHistoryEntry,
)
from lyra.autonomy.guardrails import (
    AgentQuotaConfig,
    QuotaExceededAction,
    QuotaGovernor,
    QuotaKind,
    QuotaLimit,
    QuotaUsage,
    ResetPolicy,
)
from lyra.autonomy.loop import (
    AutonomousAgent,
    AutonomyLoop,
    HealthReport,
    HealthStatus,
    Issue,
    LoopState,
    RunMode,
)
from lyra.autonomy.recovery import CrashRecovery, RecoveryAction
from lyra.autonomy.sleep_wake import (
    DreamPhase,
    SleepMode,
    SleepPolicy,
    SleepReason,
    SleepWakeScheduler,
    WakePolicy,
    WakeReason,
    WakeTrigger,
)

__all__ = [
    "AgentQuotaConfig",
    "AlertKind",
    "AlertSeverity",
    "AutonomousAgent",
    "AutonomyLoop",
    "Budget",
    "ContinuousMonitor",
    "CrashRecovery",
    "DreamPhase",
    "EffortLevel",
    "EffortProfile",
    "EffortRegulator",
    "HealthReport",
    "HealthStatus",
    "Issue",
    "LoopState",
    "MetricsSnapshot",
    "MonitorAlert",
    "MonitorConfig",
    "QuotaExceededAction",
    "QuotaGovernor",
    "QuotaKind",
    "QuotaLimit",
    "QuotaUsage",
    "RecoveryAction",
    "ResetPolicy",
    "RunMode",
    "SessionState",
    "SleepMode",
    "SleepPolicy",
    "SleepReason",
    "SleepWakeScheduler",
    "TaskHistoryEntry",
    "WakePolicy",
    "WakeReason",
    "WakeTrigger",
]
