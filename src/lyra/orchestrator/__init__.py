"""
Orchestrator Module - Multi-Agent Orchestrator-Worker system.

Provides a framework for decomposing complex queries into sub-tasks,
dispatching them to parallel worker agents, collecting artifacts,
and synthesizing final results with configurable effort scaling.
"""

from lyra.orchestrator.artifact import Artifact, CompressionLevel, compress_artifact, decompress_artifact
from lyra.orchestrator.orchestrator import (
    OrchestratorAgent,
    OrchestrationResult,
    SubTask,
    determine_effort_level,
)
from lyra.orchestrator.worker_pool import WorkerConfig, WorkerPool, WorkerSession

__all__ = [
    # Artifact types
    "Artifact",
    "CompressionLevel",
    "compress_artifact",
    "decompress_artifact",
    # Worker pool
    "WorkerPool",
    "WorkerConfig",
    "WorkerSession",
    # Orchestrator
    "OrchestratorAgent",
    "OrchestrationResult",
    "SubTask",
    "determine_effort_level",
]

__version__ = "1.0.0"
