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

# ── Core drift detection ──────────────────────────────────────────────
from .drift_detector import (
    # Enums
    DriftType,
    DetectionMethod,
    DriftSeverity,
    # Data classes
    DriftSignal,
    DriftReport,
    # Statistical utilities
    _ks_test,
    _kl_divergence,
    _mmd,
    _compute_severity,
    # Detectors
    BaseDriftDetector,
    PerformanceDriftDetector,
    ContextDriftDetector,
    DistributionDriftDetector,
    RewardDriftDetector,
    ConceptDriftDetector,
    # Orchestrator
    DriftOrchestrator,
)

# ── Signal monitors ───────────────────────────────────────────────────
from .monitors import (
    MonitorConfig,
    MonitorState,
    SignalCallback,
    BaseMonitor,
    PerformanceMonitor,
    ContextMonitor,
    DistributionMonitor,
    RewardMonitor,
    MonitorRegistry,
)

# ── Alert management ──────────────────────────────────────────────────
from .alerts import (
    AlertSeverity,
    AlertState,
    EscalationLevel,
    AlertRule,
    Alert,
    AlertThrottleState,
    AlertManager,
    NotificationHandler,
    LogNotificationHandler,
    CallbackNotificationHandler,
    EscalationPolicy,
)

# ── Automatic adaptation ──────────────────────────────────────────────
from .adaptation import (
    AdaptationAction,
    AdaptationStatus,
    AdaptationCheckpoint,
    AdaptationRecord,
    AdaptationStrategy,
    ThresholdRecalibrationStrategy,
    ModelRetrainStrategy,
    StrategySwitchStrategy,
    ResourceScaleStrategy,
    AdaptationEngine,
)

# ── Exceptions ────────────────────────────────────────────────────────
from .exceptions import (
    DriftDetectorError,
    MonitorNotInitializedError,
    AlertThrottledError,
    InsufficientDataError,
    AdaptationError,
    RollbackError,
    InvalidConfigurationError,
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
