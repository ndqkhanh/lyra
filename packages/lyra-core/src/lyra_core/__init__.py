"""Lyra core kernel.

Public surface:
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
from lyra_core.agent.safety_hooks import SafetyHookPlugin
from lyra_core.agi_orchestrator import (
    AGIOrchestrator,
    AGIPhase,
    PlanStatus,
)
from lyra_core.auto_fanout import AutoFanoutCompressor, FanoutResult
from lyra_core.breakthrough import BreakthroughIntegration, breakthrough_available
from lyra_core.canary import CanaryTokenGuard, ScanResult, ScanSeverity
from lyra_core.stagnation import StagnationDetector, StagnationResult
from lyra_core.two_circuit import (
    CircuitMode,
    ColdPathResult,
    HotPathConfig,
    ImprovementStatus,
    TwoCircuitBridge,
)

__version__ = "0.3.0"

__all__ = [
    "__version__",
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
