"""Lyra Sandbox — Phase 4.3: Swarm & Safety.

Secure code execution across process-level, Docker, and gVisor sandboxes
with resource limiting, network isolation, filesystem protection, and
pre-execution security scanning.
"""

from __future__ import annotations

from .docker_sandbox import ContainerStatus, DockerConfig, DockerSandbox, SecurityProfile
from .exceptions import (
    CodeRequest,
    ContainerError,
    ExecutionError,
    ExecutionResult,
    FilesystemError,
    ImageError,
    Language,
    NetworkError,
    ResourceLimitError,
    ResourceUsage,
    SandboxError,
    SecurityScanError,
    TimeoutError,
)
from .execution_engine import ExecutionEngine, ExecutionMetrics, ExecutionPolicy
from .filesystem_isolation import (
    AccessMode,
    AllowedPaths,
    FilesystemConfig,
    FilesystemIsolation,
    FilesystemPolicy,
    MountPoint,
    MountType,
)
from .image_manager import (
    BASH_RESTRICTED,
    EMPTY_BOX,
    ImageBuildStatus,
    ImageConfig,
    ImageManager,
    NODE_SAFE,
    PYTHON_SAFE,
    SandboxImage,
)
from .network_policy import (
    AIR_GAPPED,
    DEVELOPMENT,
    LOOPBACK_ONLY,
    UNRESTRICTED,
    DefaultPolicy,
    IsolationLevel,
    NetworkAction,
    NetworkDirection,
    NetworkPolicy,
    NetworkPolicyManager,
    NetworkRule,
)
from .process_sandbox import ProcessConfig, ProcessResult, ProcessSandbox
from .resource_limiter import (
    QuotaStatus,
    ResourceLimiter,
    ResourcePolicy,
    ResourceQuota,
    ResourceUsage as LimiterResourceUsage,
)
from .sandbox_manager import (
    SandboxConfig,
    SandboxInstance,
    SandboxManager,
    SandboxMetrics,
    SandboxStatus,
    SandboxType,
)
from .security_scanner import (
    FindingSeverity,
    ScanConfig,
    ScanResult,
    SecurityFinding,
    SecurityPolicy as ScannerSecurityPolicy,
    SecurityScanner,
)

__version__ = "0.1.0"

__all__ = [
    "SandboxError",
    "ContainerError",
    "ExecutionError",
    "ResourceLimitError",
    "NetworkError",
    "FilesystemError",
    "ImageError",
    "SecurityScanError",
    "TimeoutError",
    "CodeRequest",
    "ExecutionResult",
    "ResourceUsage",
    "Language",
    "SandboxType",
    "SandboxStatus",
    "SandboxConfig",
    "SandboxInstance",
    "SandboxManager",
    "SandboxMetrics",
    "DockerConfig",
    "DockerSandbox",
    "ContainerStatus",
    "SecurityProfile",
    "ProcessConfig",
    "ProcessResult",
    "ProcessSandbox",
    "ExecutionEngine",
    "ExecutionMetrics",
    "ExecutionPolicy",
    "ResourceLimiter",
    "ResourceQuota",
    "QuotaStatus",
    "ResourcePolicy",
    "LimiterResourceUsage",
    "NetworkRule",
    "NetworkDirection",
    "NetworkAction",
    "NetworkPolicy",
    "DefaultPolicy",
    "IsolationLevel",
    "NetworkPolicyManager",
    "AIR_GAPPED",
    "LOOPBACK_ONLY",
    "DEVELOPMENT",
    "UNRESTRICTED",
    "MountPoint",
    "MountType",
    "FilesystemConfig",
    "FilesystemIsolation",
    "FilesystemPolicy",
    "AllowedPaths",
    "AccessMode",
    "SandboxImage",
    "ImageConfig",
    "ImageManager",
    "ImageBuildStatus",
    "PYTHON_SAFE",
    "NODE_SAFE",
    "BASH_RESTRICTED",
    "EMPTY_BOX",
    "ScanResult",
    "SecurityFinding",
    "FindingSeverity",
    "ScanConfig",
    "ScannerSecurityPolicy",
    "SecurityScanner",
]
