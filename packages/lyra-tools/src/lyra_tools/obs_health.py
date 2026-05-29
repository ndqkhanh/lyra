"""Observability tool implementations — health checks, system status.

Provides a health endpoint that aggregates system state across multiple
dimensions: CPU, memory, disk, Python runtime, git status, and time.
"""
from __future__ import annotations

import os
import platform
import sys
import time as _time
from pathlib import Path
from typing import Any


def obs_health(
    repo_root: str = ".",
) -> dict[str, Any]:
    """Return system health status across key dimensions."""

    now = _time.time()

    # Python runtime info
    runtime = {
        "python_version": sys.version.split()[0],
        "implementation": platform.python_implementation(),
        "platform": platform.platform(),
        "hostname": platform.node(),
    }

    # Disk usage on the repo root
    disk: dict[str, Any] = {"path": str(Path(repo_root).resolve())}
    try:
        stat = os.statvfs(disk["path"])
        disk["total_gb"] = round((stat.f_frsize * stat.f_blocks) / (1024**3), 1)
        disk["free_gb"] = round((stat.f_frsize * stat.f_bavail) / (1024**3), 1)
        disk["used_percent"] = round(
            ((stat.f_blocks - stat.f_bfree) / stat.f_blocks) * 100, 1
        ) if stat.f_blocks > 0 else 0.0
    except OSError:
        disk["error"] = "unable to read disk stats"

    # Memory (psutil optional, graceful fallback)
    memory: dict[str, Any] = {"source": "unavailable"}
    try:
        import psutil
        mem = psutil.virtual_memory()
        memory = {
            "total_gb": round(mem.total / (1024**3), 1),
            "available_gb": round(mem.available / (1024**3), 1),
            "used_percent": round(mem.percent, 1),
            "source": "psutil",
        }
    except ImportError:
        memory = {"note": "install psutil for memory stats", "source": "unavailable"}

    # CPU load
    cpu: dict[str, Any] = {"source": "unavailable"}
    try:
        import psutil
        cpu = {
            "percent": round(psutil.cpu_percent(interval=0.1), 1),
            "logical_cores": psutil.cpu_count(logical=True),
            "physical_cores": psutil.cpu_count(logical=False),
            "source": "psutil",
        }
    except ImportError:
        cpu = {"note": "install psutil for CPU stats", "source": "unavailable"}

    # Git context (non-blocking, quick check)
    git_context: dict[str, Any] = {"repository": "unknown"}
    try:
        import subprocess
        r = subprocess.run(
            ["git", "rev-parse", "--show-toplevel"],
            cwd=repo_root,
            capture_output=True,
            text=True,
            timeout=3,
        )
        if r.returncode == 0:
            git_context["repository"] = r.stdout.strip()
            # Current branch
            br = subprocess.run(
                ["git", "branch", "--show-current"],
                cwd=repo_root,
                capture_output=True,
                text=True,
                timeout=2,
            )
            git_context["branch"] = br.stdout.strip() if br.returncode == 0 else "detached"
            # Uncommitted changes
            st = subprocess.run(
                ["git", "status", "--porcelain"],
                cwd=repo_root,
                capture_output=True,
                text=True,
                timeout=3,
            )
            git_context["uncommitted_files"] = len(
                [line for line in st.stdout.split("\n") if line.strip()]
            )
        else:
            git_context["repository"] = "not-a-git-repo"
    except Exception:
        git_context = {"repository": "unable-to-determine"}

    # Uptime (process)
    try:
        import psutil
        proc = psutil.Process()
        uptime_seconds = now - proc.create_time()
    except ImportError:
        uptime_seconds = None

    # Composite health check
    issues: list[str] = []
    if disk.get("used_percent", 0) > 90:
        issues.append(f"disk usage critical: {disk['used_percent']}%")
    if memory.get("used_percent", 0) > 90:
        issues.append(f"memory usage critical: {memory['used_percent']}%")
    if git_context.get("uncommitted_files", 0) > 50:
        issues.append(f"many uncommitted files: {git_context['uncommitted_files']}")

    return {
        "status": "unhealthy" if len(issues) > 2 else "healthy" if len(issues) == 0 else "degraded",
        "timestamp": now,
        "issues": issues,
        "runtime": runtime,
        "disk": disk,
        "memory": memory,
        "cpu": cpu,
        "git": git_context,
        "uptime_seconds": round(uptime_seconds, 0) if uptime_seconds else None,
    }


__all__ = ["obs_health"]
