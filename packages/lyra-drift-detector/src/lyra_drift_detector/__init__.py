"""Lyra Drift Detector — Multi-signal drift detection for continuous adaptation.

Detects five categories of drift across agent execution:
- Performance drift (latency, error rate, throughput)
- Context drift (topic shift, intent change)
- Distribution drift (KS test, KL divergence, MMD)
- Reward drift (RL reward signal changes)
- Concept drift (semantic shift over time)

Provides individual signal monitors, alert management, and automatic
adaptation triggers for detected drift.
"""

from __future__ import annotations

# ── Automatic adaptation ──────────────────────────────────────────────
from .adaptation import (
    AdaptationAction,
    AdaptationCheckpoint,
    AdaptationEngine,
    AdaptationRecord,
    AdaptationStatus,
    AdaptationStrategy,
    ModelRetrainStrategy,
    ResourceScaleStrategy,
    StrategySwitchStrategy,
    ThresholdRecalibrationStrategy,
)

# ── Alert management ──────────────────────────────────────────────────
from .alerts import (
    Alert,
    AlertManager,
    AlertRule,
    AlertSeverity,
    AlertState,
    AlertThrottleState,
    CallbackNotificationHandler,
    EscalationLevel,
    EscalationPolicy,
    LogNotificationHandler,
    NotificationHandler,
)

# ── Core drift detection ──────────────────────────────────────────────
from .drift_detector import (
    # Detectors
    BaseDriftDetector,
    ConceptDriftDetector,
    ContextDriftDetector,
    DetectionMethod,
    DistributionDriftDetector,
    # Orchestrator
    DriftOrchestrator,
    DriftReport,
    DriftSeverity,
    # Data classes
    DriftSignal,
    # Enums
    DriftType,
    PerformanceDriftDetector,
    RewardDriftDetector,
    _compute_severity,
    _kl_divergence,
    # Statistical utilities
    _ks_test,
    _mmd,
)

# ── Exceptions ────────────────────────────────────────────────────────
from .exceptions import (
    AdaptationError,
    AlertThrottledError,
    DriftDetectorError,
    InsufficientDataError,
    InvalidConfigurationError,
    MonitorNotInitializedError,
    RollbackError,
)

# ── Signal monitors ───────────────────────────────────────────────────
from .monitors import (
    BaseMonitor,
    ContextMonitor,
    DistributionMonitor,
    MonitorConfig,
    MonitorRegistry,
    MonitorState,
    PerformanceMonitor,
    RewardMonitor,
    SignalCallback,
)

__all__ = [
    # Core
    "DriftType",
    "DetectionMethod",
    "DriftSeverity",
    "DriftSignal",
    "DriftReport",
    "_ks_test",
    "_kl_divergence",
    "_mmd",
    "_compute_severity",
    "BaseDriftDetector",
    "PerformanceDriftDetector",
    "ContextDriftDetector",
    "DistributionDriftDetector",
    "RewardDriftDetector",
    "ConceptDriftDetector",
    "DriftOrchestrator",
    # Monitors
    "MonitorConfig",
    "MonitorState",
    "SignalCallback",
    "BaseMonitor",
    "PerformanceMonitor",
    "ContextMonitor",
    "DistributionMonitor",
    "RewardMonitor",
    "MonitorRegistry",
    # Alerts
    "AlertSeverity",
    "AlertState",
    "EscalationLevel",
    "AlertRule",
    "Alert",
    "AlertThrottleState",
    "AlertManager",
    "NotificationHandler",
    "LogNotificationHandler",
    "CallbackNotificationHandler",
    "EscalationPolicy",
    # Adaptation
    "AdaptationAction",
    "AdaptationStatus",
    "AdaptationCheckpoint",
    "AdaptationRecord",
    "AdaptationStrategy",
    "ThresholdRecalibrationStrategy",
    "ModelRetrainStrategy",
    "StrategySwitchStrategy",
    "ResourceScaleStrategy",
    "AdaptationEngine",
    # Exceptions
    "DriftDetectorError",
    "MonitorNotInitializedError",
    "AlertThrottledError",
    "InsufficientDataError",
    "AdaptationError",
    "RollbackError",
    "InvalidConfigurationError",
]
