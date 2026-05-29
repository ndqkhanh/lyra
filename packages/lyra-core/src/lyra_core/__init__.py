"""Lyra core kernel.

Public surface:
    - Agent Protocol v1.0 (``protocol``) — unified agent interface
    - Event Bus (``events``) — unified pub/sub with JSONL persistence
    - Agent Watchdog (``watchdog``) — lifecycle × health monitoring
    - Agent Adapters (``adapters.agent_adapters``) — legacy system bridges
    - TDD state machine (``tdd.state``)
    - LyraMode + resolve_lyra_decision (``permissions``)
    - Shipped hooks (``hooks``)
    - Native tools (``tools.builtin``)
    - HIR event emitter (``observability.hir``)
    - Event-Sourced Agent Loop 2.0 (``agent.event_sourced_loop``)

Re-exports lyra_harness_core primitives under ``lyra_core.core`` for ergonomic
imports downstream.
"""
from __future__ import annotations

# ── Phase 1: Adapters ──────────────────────────────────────────────────
from lyra_core.adapters.agent_adapters import (
    AdapterRegistry,
    BaseAgentAdapter,
    CoreLoopAdapter,
    LegacyAgentAdapter,
    PentestAgentAdapter,
    SwarmAgentAdapter,
    get_adapter_registry,
)

# ── Phase 5: Adversarial Review & Convergence ──────────────────────────
from lyra_core.adversarial import (
    AdversarialReview,
    ConvergenceCheck,
    ConvergenceResult,
    ConvergenceStatus,
    ResumableWorkflow,
    ReviewFinding,
    ReviewRole,
    ReviewSession,
    ReviewVerdict,
    Severity,
    WorkflowCheckpoint,
    WorkflowStatus,
    WorkflowStep,
)

# ── Existing exports ───────────────────────────────────────────────────
from lyra_core.agent.agi_plugin import AGILoopPlugin
from lyra_core.agent.event_sourced_loop import (
    EventLog,
    EventSourcedAgentLoop,
    EventType,
    MultiStreamExecutor,
    RuntimeHarnessAdaptor,
    SpeculativePlanner,
    StepEvent,
)
from lyra_core.agent.health import (
    AgentHealthMonitor,
    AnomalyDetector,
    AnomalyRecord,
    AnomalyType,
    HealthSignal,
    HealthStatus,
    HealthTrend,
    MonitorConfig,
    PlaybookStatus,
    PlaybookStep,
    RecoveryPlaybook,
    RecoveryResult,
    SignalSeverity,
    SignalSource,
)

# ── Phase 10: Integrated Agent ──────────────────────────────────────────
from lyra_core.agent.integrated import (
    AgentConfig,
    AgentSafetyContext,
    AgentStatus,
    HaltReason,
    HaltResumeController,
    IntegratedAgent,
)
from lyra_core.agent.safety_hooks import SafetyHookPlugin
from lyra_core.agi_orchestrator import (
    AGIOrchestrator,
    AGIPhase,
    PlanStatus,
)
from lyra_core.auto_fanout import AutoFanoutCompressor, FanoutResult

# ── Phase 6: Streaming Backpressure & Circuit Breaker ─────────────────
from lyra_core.backpressure import (
    AdaptiveThrottler,
    BackpressureConfig,
    BackpressureRegulator,
    BackpressureState,
    CircuitBreaker,
    CircuitBreakerConfig,
    CircuitState,
    ThrottleConfig,
    TokenBucket,
    Watermark,
)
from lyra_core.breakthrough import BreakthroughIntegration, breakthrough_available
from lyra_core.canary import CanaryTokenGuard, ScanResult, ScanSeverity

# ── Phase 4: Collective Intelligence ───────────────────────────────────
from lyra_core.collective import (
    CollectiveState,
    ConsensusLevel,
    DeadEndEntry,
    DeadEndRegistry,
    DiscussionForum,
    DiscussionThread,
    ForumPost,
    Hypothesis,
    HypothesisTeam,
    MetaImprovementLoop,
    NoiseGate,
    PostKind,
    ReorganizationPlan,
    ReorganizationTrigger,
    SelfReorganization,
    TeamFormationReason,
)

# ── Phase 3: Command Queue & Three-Surface Protocol ─────────────────────
from lyra_core.command_queue import (
    Command,
    CommandGroup,
    CommandGroupStatus,
    CommandPriority,
    CommandQueue,
    CommandStatus,
    SurfaceKind,
    SurfaceMessage,
    ThreeSurfaceProtocol,
)

# ── Phase 2: Containment Hierarchy ─────────────────────────────────────
from lyra_core.containment import (
    ConfigNode,
    ConfigTree,
    ModeStack,
    Project,
    ProjectRegistry,
    ProjectStatus,
    Team,
    TeamMembership,
    TopologyKind,
    TopologyTree,
    get_project_registry,
)

# ── Phase 9: Continuous Evaluation ──────────────────────────────────────
from lyra_core.evaluation import (
    AgentScore,
    BenchmarkRecord,
    BenchmarkStore,
    EvalPipeline,
    EvalTrigger,
    LeaderboardEngine,
    PipelineConfig,
    PipelineRun,
    RankingView,
    RunComparison,
)

# ── Phase 1: Unified Event Bus ─────────────────────────────────────────
from lyra_core.events import (
    Event,
    EventBus,
    EventCategory,
    EventMetrics,
    ProjectEventBus,
    Subscription,
)

# ── Phase 7: Experience & Learning Engine ──────────────────────────────
from lyra_core.experience import (
    AntiPattern,
    AntiPatternRegistry,
    DistillationResult,
    DistilledSkill,
    ExperienceExtractor,
    ExperienceRecord,
    ExtractedPattern,
    ImprovementCycle,
    LearningLoop,
    LoopConfig,
    LoopState,
    MatchResult,
    PatternType,
    SkillCandidate,
    SkillDistiller,
)

# ── Phase 1: Unified Agent Protocol ────────────────────────────────────
from lyra_core.protocol import (
    AgentFactory,
    AgentHealth,
    AgentIdentity,
    AgentLifecycle,
    AgentMode,
    AgentProtocol,
    AgentState,
    ItemKind,
    ItemStatus,
    Task,
    TaskResult,
    WorkstreamItem,
)

# ── Phase 8: Safety Governance ───────────────────────────────────────────
from lyra_core.safety import (
    ComplianceFramework,
    ComplianceMapper,
    OverrideRequest,
    OverrideWorkflow,
    PolicyEngine,
    PolicyRule,
    PolicyVerdict,
    SafetyPolicy,
)
from lyra_core.stagnation import StagnationDetector, StagnationResult
from lyra_core.two_circuit import (
    CircuitMode,
    ColdPathResult,
    HotPathConfig,
    ImprovementStatus,
    TwoCircuitBridge,
)

# ── Phase 1: Agent Watchdog ────────────────────────────────────────────
from lyra_core.watchdog import (
    AgentWatchdog,
    CrashRecord,
    WatchdogConfig,
    WatchdogStatus,
)

__version__ = "0.18.0"  # Phase 15: remove dead cron/triggers.py (zero production usage)

__all__ = [
    "__version__",
    # Phase 1: Protocol
    "AgentProtocol",
    "AgentFactory",
    "AgentIdentity",
    "AgentState",
    "AgentLifecycle",
    "AgentHealth",
    "AgentMode",
    "Task",
    "TaskResult",
    "WorkstreamItem",
    "ItemKind",
    "ItemStatus",
    # Phase 1: Events
    "EventBus",
    "Event",
    "EventCategory",
    "Subscription",
    "ProjectEventBus",
    "EventMetrics",
    # Phase 1: Watchdog
    "AgentWatchdog",
    "WatchdogConfig",
    "WatchdogStatus",
    "CrashRecord",
    # Phase 1: Adapters
    "AdapterRegistry",
    "BaseAgentAdapter",
    "LegacyAgentAdapter",
    "CoreLoopAdapter",
    "SwarmAgentAdapter",
    "PentestAgentAdapter",
    "get_adapter_registry",
    # Phase 2: Containment
    "Project",
    "ProjectStatus",
    "ProjectRegistry",
    "Team",
    "TeamMembership",
    "TopologyTree",
    "TopologyKind",
    "ConfigTree",
    "ConfigNode",
    "ModeStack",
    "get_project_registry",
    # Phase 3: Command Queue
    "CommandQueue",
    "Command",
    "CommandStatus",
    "CommandPriority",
    "CommandGroup",
    "CommandGroupStatus",
    "ThreeSurfaceProtocol",
    "SurfaceMessage",
    "SurfaceKind",
    # Phase 4: Collective
    "CollectiveState",
    "DiscussionForum",
    "DiscussionThread",
    "ForumPost",
    "PostKind",
    "ConsensusLevel",
    "Hypothesis",
    "HypothesisTeam",
    "TeamFormationReason",
    "DeadEndRegistry",
    "DeadEndEntry",
    "NoiseGate",
    "MetaImprovementLoop",
    "SelfReorganization",
    "ReorganizationPlan",
    "ReorganizationTrigger",
    # Phase 5: Adversarial
    "AdversarialReview",
    "ReviewFinding",
    "ReviewRole",
    "ReviewVerdict",
    "Severity",
    "ConvergenceCheck",
    "ConvergenceResult",
    "ConvergenceStatus",
    "ReviewSession",
    "ResumableWorkflow",
    "WorkflowStep",
    "WorkflowCheckpoint",
    "WorkflowStatus",
    # Phase 6: Backpressure
    "AdaptiveThrottler",
    "BackpressureConfig",
    "BackpressureRegulator",
    "BackpressureState",
    "CircuitBreaker",
    "CircuitBreakerConfig",
    "CircuitState",
    "ThrottleConfig",
    "TokenBucket",
    "Watermark",
    # Phase 10: Integrated Agent
    "AgentConfig",
    "AgentSafetyContext",
    "AgentStatus",
    "HaltReason",
    "HaltResumeController",
    "IntegratedAgent",
    # Phase 11: Agent Health
    "AgentHealthMonitor",
    "AnomalyDetector",
    "AnomalyRecord",
    "AnomalyType",
    "HealthSignal",
    "HealthStatus",
    "HealthTrend",
    "MonitorConfig",
    "PlaybookStatus",
    "PlaybookStep",
    "RecoveryPlaybook",
    "RecoveryResult",
    "SignalSeverity",
    "SignalSource",
    # Phase 9: Continuous Evaluation
    "AgentScore",
    "BenchmarkRecord",
    "BenchmarkStore",
    "EvalPipeline",
    "EvalTrigger",
    "LeaderboardEngine",
    "PipelineConfig",
    "PipelineRun",
    "RankingView",
    "RunComparison",
    # Phase 8: Safety Governance
    "ComplianceFramework",
    "ComplianceMapper",
    "OverrideRequest",
    "OverrideWorkflow",
    "PolicyEngine",
    "PolicyRule",
    "PolicyVerdict",
    "SafetyPolicy",
    # Phase 7: Experience
    "AntiPattern",
    "AntiPatternRegistry",
    "DistillationResult",
    "DistilledSkill",
    "ExperienceExtractor",
    "ExperienceRecord",
    "ExtractedPattern",
    "ImprovementCycle",
    "LearningLoop",
    "LoopConfig",
    "LoopState",
    "MatchResult",
    "PatternType",
    "SkillCandidate",
    "SkillDistiller",
    # Existing
    "EventSourcedAgentLoop",
    "EventLog",
    "StepEvent",
    "EventType",
    "MultiStreamExecutor",
    "SpeculativePlanner",
    "RuntimeHarnessAdaptor",
    "AGIOrchestrator",
    "AGIPhase",
    "PlanStatus",
    "AGILoopPlugin",
    "SafetyHookPlugin",
    "BreakthroughIntegration",
    "breakthrough_available",
    "AutoFanoutCompressor",
    "FanoutResult",
    "CanaryTokenGuard",
    "ScanResult",
    "ScanSeverity",
    "StagnationDetector",
    "StagnationResult",
    "CircuitMode",
    "ColdPathResult",
    "HotPathConfig",
    "ImprovementStatus",
    "TwoCircuitBridge",
]
