"""Escape-hatch audit log for ``--no-tdd`` usage.

Every invocation that skips the TDD gate emits a JSONL record. ``summary()``
produces counts the ``lyra retro`` command surfaces in the report.
"""
from __future__ import annotations

import json
from dataclasses import asdict, dataclass, field
from datetime import datetime, timezone
from pathlib import Path


@dataclass
class EscapeHatchEntry:
    session_id: str
    reason: str
    user: str
    tool: str
    ts: str = field(default_factory=lambda: datetime.now(timezone.utc).isoformat())


@dataclass
class EscapeHatchSummary:
    total: int
    by_user: dict[str, int]
    by_tool: dict[str, int]


class EscapeHatchAudit:
    def __init__(self, log_path: Path) -> None:
        self.log_path = Path(log_path)
        self.log_path.parent.mkdir(parents=True, exist_ok=True)

    def record(
        self,
        *,
        session_id: str,
        reason: str,
        user: str,
        tool: str,
    ) -> EscapeHatchEntry:
        entry = EscapeHatchEntry(
            session_id=session_id, reason=reason, user=user, tool=tool
        )
        with self.log_path.open("a", encoding="utf-8") as f:
            f.write(json.dumps(asdict(entry)) + "\n")
        return entry

    def entries(self) -> list[EscapeHatchEntry]:
        if not self.log_path.exists():
            return []
        out: list[EscapeHatchEntry] = []
        for line in self.log_path.read_text(encoding="utf-8").splitlines():
            if not line.strip():
                continue
            try:
                obj = json.loads(line)
            except json.JSONDecodeError:
                continue
            out.append(
                EscapeHatchEntry(
                    session_id=obj.get("session_id", ""),
                    reason=obj.get("reason", ""),
                    user=obj.get("user", ""),
                    tool=obj.get("tool", ""),
                    ts=obj.get("ts", ""),
                )
            )
        return out

    def summary(self) -> EscapeHatchSummary:
        by_user: dict[str, int] = {}
        by_tool: dict[str, int] = {}
        entries = self.entries()
        for e in entries:
            by_user[e.user] = by_user.get(e.user, 0) + 1
            by_tool[e.tool] = by_tool.get(e.tool, 0) + 1
        return EscapeHatchSummary(total=len(entries), by_user=by_user, by_tool=by_tool)
