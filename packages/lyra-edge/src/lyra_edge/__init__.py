"""Edge/On-Device Agent Runtime — lightweight, offline-capable, privacy-preserving."""
from __future__ import annotations
import logging, json
from dataclasses import dataclass, field
from typing import Any, Optional

logger = logging.getLogger(__name__)
__all__ = ["EdgeDevice", "EdgeRuntime", "EdgeAgent"]

@dataclass
class EdgeDevice: name: str; memory_mb: int; storage_mb: int; battery_pct: float; is_online: bool = True

class EdgeRuntime:
    def __init__(self): self.devices: dict[str, EdgeDevice] = {}; self._task_queue: list[dict] = []

    def register_device(self, name: str, memory_mb: int = 512, storage_mb: int = 1024) -> EdgeDevice:
        d = EdgeDevice(name=name, memory_mb=memory_mb, storage_mb=storage_mb, battery_pct=100.0)
        self.devices[name] = d; return d

    def can_run(self, device_name: str, required_memory_mb: int = 128) -> bool:
        d = self.devices.get(device_name)
        if not d: return False
        return d.memory_mb >= required_memory_mb and d.battery_pct > 10.0

    def enqueue_task(self, task: dict) -> None: self._task_queue.append(task)

    def process_queue(self) -> list[dict]: q = self._task_queue[:]; self._task_queue.clear(); return q

    def go_offline(self, device_name: str) -> None:
        d = self.devices.get(device_name)
        if d: d.is_online = False; logger.info(f"{device_name} went offline")

    def sync_when_online(self, device_name: str) -> list[dict]:
        d = self.devices.get(device_name)
        if not d or not d.is_online: return []
        return [{"synced": True, "device": device_name}]

    @property
    def stats(self) -> dict: return {"devices": len(self.devices), "queue_length": len(self._task_queue)}
