"""InterruptQueue — ordered list of agents blocked on permission requests."""
from __future__ import annotations

import json
import time
from dataclasses import dataclass
from typing import Optional


@dataclass
class PendingInterrupt:
    """A single pending permission request."""
    interrupt_id: str
    session_id: str
    tool_name: str
    action_preview: str
    severity: str    # "low" | "medium" | "high" | "critical"
    queued_at: float
    resolved_at: Optional[float] = None

    @property
    def wait_s(self) -> float:
        return time.time() - self.queued_at

    @property
    def is_resolved(self) -> bool:
        return self.resolved_at is not None


class InterruptQueue:
    """Thread-safe ordered queue of pending permission requests."""

    def __init__(self) -> None:
        self._items: dict[str, PendingInterrupt] = {}

    def push(
        self,
        interrupt_id: str,
        session_id: str,
        tool_name: str,
        payload_json: str = "{}",
    ) -> None:
        try:
            payload = json.loads(payload_json)
        except Exception:
            payload = {}
        severity = _infer_severity(tool_name, payload)
        action_preview = _action_preview(tool_name, payload)
        self._items[interrupt_id] = PendingInterrupt(
            interrupt_id=interrupt_id,
            session_id=session_id,
            tool_name=tool_name,
            action_preview=action_preview,
            severity=severity,
            queued_at=time.time(),
        )

    def resolve(self, interrupt_id: str) -> None:
        if interrupt_id in self._items:
            self._items[interrupt_id].resolved_at = time.time()

    def get_pending(self) -> list[PendingInterrupt]:
        """Return unresolved interrupts sorted by severity then wait time."""
        pending = [i for i in self._items.values() if not i.is_resolved]
        severity_rank = {"critical": 0, "high": 1, "medium": 2, "low": 3}
        return sorted(pending, key=lambda i: (severity_rank.get(i.severity, 9), -i.wait_s))

    def pending_count(self) -> int:
        return len(self.get_pending())

    def clear_resolved(self) -> None:
        self._items = {k: v for k, v in self._items.items() if not v.is_resolved}


_CRITICAL_PATTERNS = ("rm -rf", "drop table", "delete from", "truncate", "format", "/etc/")
_HIGH_PATTERNS = ("rm ", "mv /", "chmod 777", "sudo", "git push --force")


def _infer_severity(tool_name: str, payload: dict) -> str:
    args = payload.get("args") or payload.get("tool_input") or {}
    cmd = str(args).lower()
    if any(p in cmd for p in _CRITICAL_PATTERNS):
        return "critical"
    if any(p in cmd for p in _HIGH_PATTERNS):
        return "high"
    if tool_name in ("Bash", "Edit", "Write"):
        return "medium"
    return "low"


def _action_preview(tool_name: str, payload: dict, max_len: int = 60) -> str:
    args = payload.get("args") or payload.get("tool_input") or {}
    if isinstance(args, dict):
        cmd = args.get("command") or args.get("path") or str(args)
    else:
        cmd = str(args)
    preview = f"{tool_name}: {str(cmd)[:max_len]}"
    return preview
