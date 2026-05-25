"""Sandbox lifecycle orchestration — create, execute, terminate, and monitor."""

from __future__ import annotations

from dataclasses import dataclass, field
from datetime import datetime, timezone
from enum import Enum
from time import time
from typing import Sequence
from uuid import uuid4

from .docker_sandbox import DockerConfig, DockerSandbox
from .exceptions import (
    CodeRequest,
    ExecutionError,
    ExecutionResult,
    Language,
    SandboxError,
)
from .execution_engine import ExecutionEngine, ExecutionMetrics, ExecutionPolicy
from .filesystem_isolation import FilesystemConfig, FilesystemIsolation, MountPoint
from .network_policy import IsolationLevel, NetworkPolicy, NetworkPolicyManager
from .process_sandbox import ProcessConfig, ProcessSandbox
from .resource_limiter import ResourceLimiter, ResourceQuota
from .security_scanner import ScanConfig, SecurityPolicy, SecurityScanner


class SandboxType(str, Enum):
    """Supported sandbox runtime types."""

    PROCESS = "process"
    DOCKER = "docker"
    GVISOR = "gvisor"
    FIRECRACKER = "firecracker"
    REMOTE = "remote"


class SandboxStatus(str, Enum):
    """Lifecycle status of a sandbox instance."""

    CREATING = "creating"
    RUNNING = "running"
    IDLE = "idle"
    TERMINATED = "terminated"
    ERROR = "error"


@dataclass(frozen=True)
class SandboxConfig:
    """Complete configuration for a new sandbox instance."""

    sandbox_type: SandboxType = SandboxType.PROCESS
    timeout_seconds: int = 30
    max_memory_mb: int = 512
    max_cpu: int = 1
    network_policy: str = "air_gapped"
    read_only_root: bool = True
    allowed_packages: tuple[str, ...] = ()


@dataclass(frozen=True)
class SandboxInstance:
    """A running sandbox instance."""

    instance_id: str
    sandbox_type: SandboxType
    status: SandboxStatus
    created_at: float = field(default_factory=time)
    resource_usage: str = ""


@dataclass(frozen=True)
class SandboxMetrics:
    """Aggregate sandbox pool metrics."""

    active_instances: int = 0
    total_executions: int = 0
    avg_execution_time: float = 0.0


class SandboxManager:
    """Orchestrates sandbox lifecycle: creation, execution, termination, cleanup."""

    _instances: dict[str, SandboxInstance] = {}
    _engines: dict[str, ExecutionEngine] = {}
    _scan_config: ScanConfig = field(default_factory=lambda: ScanConfig(enabled=True))  # type: ignore[arg-type]

    @classmethod
    def create_sandbox(cls, config: SandboxConfig | None = None) -> SandboxInstance:
        """Create a new sandbox instance and return its descriptor."""
        cfg = config or SandboxConfig()
        instance_id = uuid4().hex[:16]
        engine = ExecutionEngine(
            scan_config=ScanConfig(enabled=True),
        )

        instance = SandboxInstance(
            instance_id=instance_id,
            sandbox_type=cfg.sandbox_type,
            status=SandboxStatus.CREATING,
        )

        cls._instances[instance_id] = instance
        cls._engines[instance_id] = engine

        # Transition to RUNNING
        running = SandboxInstance(
            instance_id=instance.instance_id,
            sandbox_type=instance.sandbox_type,
            status=SandboxStatus.RUNNING,
            created_at=instance.created_at,
        )
        cls._instances[instance_id] = running
        return running

    @classmethod
    def execute(
        cls,
        instance_id: str,
        code: str,
        language: str = "python",
    ) -> ExecutionResult:
        """Execute code within an existing sandbox instance."""
        instance = cls._instances.get(instance_id)
        if instance is None:
            raise SandboxError(f"Sandbox instance {instance_id} not found")
        if instance.status == SandboxStatus.TERMINATED:
            raise SandboxError(f"Sandbox instance {instance_id} is terminated")

        engine = cls._engines.get(instance_id)
        if engine is None:
            raise SandboxError(f"No engine for sandbox {instance_id}")

        lang_enum = Language(language) if language else Language.GENERIC
        request = CodeRequest(code=code, language=lang_enum)
        return engine.execute(request, sandbox_type=instance.sandbox_type.value)

    @classmethod
    def terminate(cls, instance_id: str) -> bool:
        """Terminate a sandbox instance and release its resources."""
        instance = cls._instances.get(instance_id)
        if instance is None:
            return False

        terminated = SandboxInstance(
            instance_id=instance.instance_id,
            sandbox_type=instance.sandbox_type,
            status=SandboxStatus.TERMINATED,
            created_at=instance.created_at,
        )
        cls._instances[instance_id] = terminated
        cls._engines.pop(instance_id, None)
        return True

    @classmethod
    def cleanup_stale(cls, max_age_seconds: int = 3600) -> int:
        """Terminate all sandbox instances older than max_age_seconds."""
        now = time()
        stale_ids = [
            iid
            for iid, inst in cls._instances.items()
            if inst.status
            in (SandboxStatus.RUNNING, SandboxStatus.IDLE, SandboxStatus.CREATING)
            and (now - inst.created_at) > max_age_seconds
        ]
        for iid in stale_ids:
            cls.terminate(iid)
        return len(stale_ids)

    @classmethod
    def get_instance(cls, instance_id: str) -> SandboxInstance | None:
        """Retrieve a sandbox instance by ID."""
        return cls._instances.get(instance_id)

    @classmethod
    def list_instances(cls) -> list[SandboxInstance]:
        """Return all sandbox instances."""
        return list(cls._instances.values())

    @classmethod
    def get_metrics(cls) -> SandboxMetrics:
        """Return aggregate pool metrics."""
        active = sum(
            1
            for inst in cls._instances.values()
            if inst.status == SandboxStatus.RUNNING
        )
        total_execs = sum(
            engine.execution_count for engine in cls._engines.values()
        )
        avg_time = 0.0
        engine_times = [
            engine.get_metrics().avg_duration for engine in cls._engines.values()
        ]
        if engine_times:
            avg_time = sum(engine_times) / len(engine_times)
        return SandboxMetrics(
            active_instances=active,
            total_executions=total_execs,
            avg_execution_time=avg_time,
        )

    @classmethod
    def clear_all(cls) -> None:
        """Remove all sandbox instances and engines."""
        cls._instances.clear()
        cls._engines.clear()
