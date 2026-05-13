"""OS-level agent process scanner.

Reads running processes via psutil (preferred) or ``ps aux`` fallback.
Identifies Claude Code / subagent processes by command pattern.
"""
from __future__ import annotations

import re
import subprocess
import time
from dataclasses import dataclass


_AGENT_PATTERNS: tuple[str, ...] = (
    r"\bclaude\b",
    r"claude-code",
    r"node.*claude",
    r"python.*lyra",
)
_COMPILED = [re.compile(p) for p in _AGENT_PATTERNS]


@dataclass(frozen=True)
class RawProcess:
    """Minimal OS-level process snapshot."""
    pid: int
    command: str
    cwd: str
    cpu_pct: float
    rss_mb: float
    started_at: float  # Unix timestamp (best-effort)


def _matches_agent(command: str) -> bool:
    return any(pat.search(command) for pat in _COMPILED)


def _scan_via_psutil() -> list[RawProcess]:
    import psutil  # type: ignore[import-untyped]

    out: list[RawProcess] = []
    for proc in psutil.process_iter(["pid", "cmdline", "cwd", "cpu_percent", "memory_info", "create_time"]):
        try:
            info = proc.info
            cmd = " ".join(info.get("cmdline") or [])
            if not cmd or not _matches_agent(cmd):
                continue
            cwd = info.get("cwd") or ""
            rss = (info.get("memory_info") or type("M", (), {"rss": 0})()).rss / 1024 / 1024
            out.append(
                RawProcess(
                    pid=info["pid"],
                    command=cmd,
                    cwd=cwd,
                    cpu_pct=info.get("cpu_percent") or 0.0,
                    rss_mb=rss,
                    started_at=info.get("create_time") or 0.0,
                )
            )
        except (psutil.NoSuchProcess, psutil.AccessDenied):
            continue
    return out


def _scan_via_ps() -> list[RawProcess]:
    try:
        result = subprocess.run(
            ["ps", "aux"],
            capture_output=True,
            text=True,
            timeout=5,
        )
    except (OSError, subprocess.TimeoutExpired):
        return []
    out: list[RawProcess] = []
    for line in result.stdout.splitlines()[1:]:
        parts = line.split(None, 10)
        if len(parts) < 11:
            continue
        cmd = parts[10]
        if not _matches_agent(cmd):
            continue
        try:
            pid = int(parts[1])
            cpu = float(parts[2])
            rss_kb = float(parts[5])
        except ValueError:
            continue
        out.append(
            RawProcess(
                pid=pid,
                command=cmd,
                cwd="",
                cpu_pct=cpu,
                rss_mb=rss_kb / 1024,
                started_at=0.0,
            )
        )
    return out


def scan_agent_processes() -> list[RawProcess]:
    """Return all detected agent processes. Prefers psutil; falls back to ps."""
    try:
        import psutil  # noqa: F401
        return _scan_via_psutil()
    except ImportError:
        return _scan_via_ps()
