"""Observability primitives — HIR emitter, OTel export, EventBus, live display."""
from __future__ import annotations

from .context_gauge import (
    AgentDAG,
    ContextGauge,
    DAGEdge,
    DAGNode,
    SkillEntry,
    SkillPanel,
)
from .event_bus import (
    AnyEvent,
    CostThreshold,
    CronJobFired,
    DaemonIteration,
    EventBus,
    LLMCallFinished,
    LLMCallStarted,
    LLMTokenChunk,
    PermissionDecision,
    ProcessStateWriter,
    SkillActivated,
    StopHookFired,
    SubagentFinished,
    SubagentSpawned,
    ToolCallBlocked,
    ToolCallFinished,
    ToolCallStarted,
    get_event_bus,
    reset_event_bus,
)
from .hir import HIREmitter, HIREvent, HIREventKind
from .live_display import (
    AgentRow,
    DisplayState,
    EventEntry,
    LiveDisplay,
    build_layout,
    render_agent_table,
    render_event_log,
    render_header,
    render_stats,
)
from .otel_export import (
    Collector,
    InMemoryCollector,
    OpenTelemetryCollector,
    OTLPExporter,
)
from .process_tree import AgentLifecycleState, AgentNode, ProcessTree
from .telemetry_bridge import TelemetryBridge

__all__ = [
    # HIR
    "HIREmitter",
    "HIREvent",
    "HIREventKind",
    # OTel
    "Collector",
    "InMemoryCollector",
    "OpenTelemetryCollector",
    "OTLPExporter",
    "TelemetryBridge",
    # EventBus
    "EventBus",
    "get_event_bus",
    "reset_event_bus",
    "ProcessStateWriter",
    "AnyEvent",
    # Event dataclasses
    "LLMCallStarted",
    "LLMTokenChunk",
    "LLMCallFinished",
    "ToolCallStarted",
    "ToolCallFinished",
    "ToolCallBlocked",
    "SubagentSpawned",
    "SubagentFinished",
    "StopHookFired",
    "PermissionDecision",
    "CostThreshold",
    "CronJobFired",
    "DaemonIteration",
    "SkillActivated",
    # Live display
    "LiveDisplay",
    "DisplayState",
    "AgentRow",
    "EventEntry",
    "build_layout",
    "render_header",
    "render_agent_table",
    "render_event_log",
    "render_stats",
    # Process tree
    "ProcessTree",
    "AgentLifecycleState",
    "AgentNode",
    # Context gauge / skill panel / DAG
    "ContextGauge",
    "SkillPanel",
    "SkillEntry",
    "AgentDAG",
    "DAGNode",
    "DAGEdge",
]
