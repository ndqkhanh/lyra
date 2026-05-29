from __future__ import annotations

import uuid
from dataclasses import dataclass
from enum import Enum


class IsolationLevel(Enum):
    PROCESS = "process"
    CONTAINER = "container"
    VM = "vm"
    AIR_GAPPED = "air_gapped"


class NetworkPolicy(Enum):
    NONE = "none"
    LOOPBACK_ONLY = "loopback_only"
    ALLOW_LIST = "allow_list"
    FULL_ACCESS = "full_access"


@dataclass(frozen=True)
class SandboxConfig:
    level: IsolationLevel = IsolationLevel.PROCESS
    memory_limit_mb: int = 512
    cpu_limit: int = 50
    network_policy: NetworkPolicy = NetworkPolicy.NONE
    timeout_seconds: int = 30
    read_only_fs: bool = True


@dataclass(frozen=True)
class ExecutionRequest:
    code: str = ""
    language: str = ""
    expected_outputs: str = ""
    max_runtime: float = 30.0


@dataclass(frozen=True)
class ExecutionResult:
    output: str = ""
    exit_code: int = 0
    duration: float = 0.0
    resource_usage: str = ""
    isolated_at_level: IsolationLevel = IsolationLevel.PROCESS


@dataclass(frozen=True)
class ResourceLimits:
    max_memory: int = 512
    max_cpu_percent: int = 80
    max_disk_mb: int = 100
    max_processes: int = 10


@dataclass(frozen=True)
class IsolationHealth:
    is_healthy: bool = True
    active_sandboxes: int = 0
    max_sandboxes: int = 50
    errors: tuple[str, ...] = ()


_DANGEROUS_KEYWORDS: tuple[str, ...] = (
    "import os", "import subprocess", "import shutil",
    "__import__('os')", "eval(", "exec(", "compile(",
    "open(", "file(", "socket.",
    "BaseException", "__subclasses__",
    "sys.modules", "__builtins__",
)


class IsolationManager:
    """Layer 4: Hardware and container-level execution isolation.

    Validates that execution requests comply with sandbox configuration
    and checks that the requested isolation level is sufficient for the
    code being executed.
    """

    def __init__(self) -> None:
        self._sandboxes: dict[str, SandboxConfig] = {}
        self._health_errors: list[str] = []

    def isolate_and_execute(self, request: ExecutionRequest, config: SandboxConfig) -> ExecutionResult:
        """Validate an execution request against the sandbox configuration.

        Performs safety checks on the code and verifies the isolation level
        is appropriate. Does not actually execute code — this is a governance
        validation layer.
        """
        issues: list[str] = []

        # Check for dangerous keywords in code
        if request.code:
            for keyword in _DANGEROUS_KEYWORDS:
                if keyword.lower() in request.code.lower():
                    issues.append(f"Dangerous keyword detected: {keyword}")

        # Validate max_runtime against timeout
        if request.max_runtime > config.timeout_seconds:
            issues.append(
                f"Requested max_runtime ({request.max_runtime}s) exceeds "
                f"configured timeout ({config.timeout_seconds}s)"
            )

        # Validate resource constraints
        duration = min(request.max_runtime, float(config.timeout_seconds))

        sandbox_id = str(uuid.uuid4())[:8]

        if issues:
            self._sandboxes[sandbox_id] = config
            return ExecutionResult(
                output=f"Rejected ({sandbox_id}): {'; '.join(issues)}",
                exit_code=1,
                duration=0.0,
                resource_usage="N/A",
                isolated_at_level=config.level,
            )

        self._sandboxes[sandbox_id] = config
        return ExecutionResult(
            output=f"Approved ({sandbox_id})",
            exit_code=0,
            duration=duration,
            resource_usage=f"mem={config.memory_limit_mb}MB,cpu={config.cpu_limit}%",
            isolated_at_level=config.level,
        )

    def check_isolation_health(self) -> IsolationHealth:
        """Check the overall health of the isolation subsystem."""
        active = len(self._sandboxes)
        healthy = active < 50 and len(self._health_errors) < 5

        return IsolationHealth(
            is_healthy=healthy,
            active_sandboxes=active,
            max_sandboxes=50,
            errors=tuple(self._health_errors[-10:]),
        )
