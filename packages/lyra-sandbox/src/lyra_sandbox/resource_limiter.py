"""Resource constraint enforcement for sandboxed processes."""

from __future__ import annotations

import os
import platform
from dataclasses import dataclass, field
from enum import Enum

from .exceptions import ResourceLimitError


class ResourcePolicy(str, Enum):
    """How resource limits are enforced."""

    HARD_LIMIT = "hard_limit"
    SOFT_LIMIT = "soft_limit"
    MONITOR_ONLY = "monitor_only"


@dataclass(frozen=True)
class ResourceQuota:
    """Resource limits to impose on a sandbox instance."""

    cpu_shares: int = 1024
    memory_limit_bytes: int = 512 * 1024 * 1024  # 512 MB
    disk_limit_bytes: int = 1024 * 1024 * 1024  # 1 GB
    max_pids: int = 256
    max_open_files: int = 1024
    network_bandwidth: int = 1_000_000  # 1 Mbps


@dataclass(frozen=True)
class QuotaStatus:
    """Current resource consumption relative to a quota."""

    quota: ResourceQuota
    current: ResourceUsage
    within_limits: bool
    exceeded_resources: tuple[str, ...] = field(default_factory=tuple)


@dataclass(frozen=True)
class ResourceUsage:
    """Point-in-time resource consumption."""

    cpu_percent: float = 0.0
    memory_bytes: int = 0
    disk_bytes: int = 0
    pids: int = 0
    open_fds: int = 0
    rx_bytes: int = 0
    tx_bytes: int = 0


class ResourceLimiter:
    """Enforces CPU, memory, disk, and process limits on sandboxes."""

    _system = platform.system()

    @classmethod
    def apply_limits(cls, process_id: int, quota: ResourceQuota) -> bool:
        """Apply resource limits to a process using platform-native mechanisms."""
        if cls._system == "Linux":
            return cls._apply_cgroups(process_id, quota)
        return cls._apply_ulimit(process_id, quota)

    @classmethod
    def get_current_usage(cls) -> ResourceUsage:
        """Return a snapshot of current resource usage for the calling process."""
        try:
            import resource

            usage = resource.getrusage(resource.RUSAGE_SELF)
            return ResourceUsage(
                cpu_percent=usage.ru_utime + usage.ru_stime,
                memory_bytes=usage.ru_maxrss * 1024 if cls._system == "Linux" else usage.ru_maxrss,
            )
        except (ImportError, AttributeError):
            return ResourceUsage()

    @classmethod
    def check_within_limits(cls, usage: ResourceUsage, quota: ResourceQuota) -> QuotaStatus:
        """Compare actual usage against quota and report which resources are exceeded."""
        exceeded: list[str] = []
        if usage.memory_bytes > quota.memory_limit_bytes:
            exceeded.append("memory")
        if usage.disk_bytes > quota.disk_limit_bytes:
            exceeded.append("disk")
        if usage.pids > quota.max_pids:
            exceeded.append("pids")
        return QuotaStatus(
            quota=quota,
            current=usage,
            within_limits=len(exceeded) == 0,
            exceeded_resources=tuple(exceeded),
        )

    @classmethod
    def _apply_cgroups(cls, process_id: int, quota: ResourceQuota) -> bool:
        """Apply limits via cgroups v1 or v2."""
        cgroup_path = f"/sys/fs/cgroup/lyra-sandbox-{process_id}"
        try:
            os.makedirs(cgroup_path, exist_ok=True)
            # cgroup v2 unified
            memory_max = os.path.join(cgroup_path, "memory.max")
            cpu_max = os.path.join(cgroup_path, "cpu.max")
            pids_max = os.path.join(cgroup_path, "pids.max")
            if os.path.exists(memory_max):
                with open(memory_max, "w") as f:
                    f.write(str(quota.memory_limit_bytes))
            if os.path.exists(cpu_max):
                with open(cpu_max, "w") as f:
                    f.write(f"{quota.cpu_shares} 100000")
            if os.path.exists(pids_max):
                with open(pids_max, "w") as f:
                    f.write(str(quota.max_pids))
            cgroup_procs = os.path.join(cgroup_path, "cgroup.procs")
            if os.path.exists(cgroup_procs):
                with open(cgroup_procs, "w") as f:
                    f.write(str(process_id))
            return True
        except (OSError, PermissionError):
            return False

    @classmethod
    def _apply_ulimit(cls, process_id: int, quota: ResourceQuota) -> bool:
        """Apply limits via ulimit / resource module (macOS/BSD fallback)."""
        try:
            import resource

            resource.setrlimit(resource.RLIMIT_NOFILE, (quota.max_open_files, quota.max_open_files))
            return True
        except (ImportError, ValueError, resource.error):
            return False
