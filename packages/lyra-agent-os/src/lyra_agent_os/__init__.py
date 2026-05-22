"""Agent Operating System — process lifecycle, resource allocation, system services."""
from __future__ import annotations
import logging, time, uuid
from dataclasses import dataclass, field
from enum import Enum, auto
from typing import Any, Optional

logger = logging.getLogger(__name__)
__all__ = ["ProcessState", "AgentProcess", "AgentOS"]

class ProcessState(Enum):
    CREATED = auto(); RUNNING = auto(); PAUSED = auto(); TERMINATED = auto()

@dataclass
class AgentProcess:
    pid: str; name: str; state: ProcessState; memory_mb: float = 0.0; cpu_pct: float = 0.0; created_at: float = 0.0

class AgentOS:
    def __init__(self, total_memory_mb: float = 1024):
        self.processes: dict[str, AgentProcess] = {}
        self.total_memory = total_memory_mb
        self.used_memory = 0.0

    def spawn(self, name: str, memory_mb: float = 64.0) -> Optional[AgentProcess]:
        if self.used_memory + memory_mb > self.total_memory: return None
        pid = str(uuid.uuid4())[:8]
        proc = AgentProcess(pid=pid, name=name, state=ProcessState.RUNNING, memory_mb=memory_mb, created_at=time.time())
        self.processes[pid] = proc
        self.used_memory += memory_mb
        return proc

    def pause(self, pid: str) -> bool:
        proc = self.processes.get(pid)
        if not proc or proc.state != ProcessState.RUNNING: return False
        proc.state = ProcessState.PAUSED; return True

    def resume(self, pid: str) -> bool:
        proc = self.processes.get(pid)
        if not proc or proc.state != ProcessState.PAUSED: return False
        proc.state = ProcessState.RUNNING; return True

    def kill(self, pid: str) -> bool:
        proc = self.processes.get(pid)
        if not proc: return False
        proc.state = ProcessState.TERMINATED
        self.used_memory = max(0, self.used_memory - proc.memory_mb)
        return True

    @property
    def stats(self) -> dict[str, Any]:
        return {"processes": len(self.processes), "running": sum(1 for p in self.processes.values() if p.state == ProcessState.RUNNING), "memory_used": self.used_memory, "memory_total": self.total_memory, "memory_pct": (self.used_memory / self.total_memory) * 100}
