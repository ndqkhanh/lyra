"""
Session Manager — manages session lifecycle (create, checkpoint, branch, restore).

Git-native design: sessions are stored as versioned state files in git,
enabling branching timelines and semantic search across session history.
"""

from __future__ import annotations

import json
import os
import time
import uuid
from pathlib import Path
from typing import Any

from .models import Checkpoint, SessionConfig, SessionState, SessionStatus

logger = __import__("logging").getLogger(__name__)


class SessionManager:
    """Manages session lifecycle with git-native versioning."""

    def __init__(self, base_dir: str | Path = ".lyra/sessions") -> None:
        self._base_dir = Path(base_dir)
        self._base_dir.mkdir(parents=True, exist_ok=True)
        self._active: dict[str, SessionState] = {}
        self._load_sessions()

    def create(self, config: SessionConfig | None = None, parent_id: str = "") -> SessionState:
        session_id = uuid.uuid4().hex[:12]
        state = SessionState(
            id=session_id,
            config=config or SessionConfig(),
            parent_session_id=parent_id,
            branch_name=f"lyra/session-{session_id}",
        )
        self._active[session_id] = state
        self._save(state)
        return state

    def checkpoint(self, session_id: str, name: str = "", metadata: dict[str, Any] | None = None) -> Checkpoint:
        state = self._active.get(session_id)
        if not state:
            raise KeyError(f"Session not found: {session_id}")

        cp = Checkpoint(
            id=uuid.uuid4().hex[:8],
            session_id=session_id,
            name=name or f"checkpoint-{len(state.checkpoints) + 1}",
            metadata=metadata or {},
        )
        state.checkpoints.append(cp)
        state.updated_at = time.time()
        self._save(state)
        return cp

    def get(self, session_id: str) -> SessionState | None:
        return self._active.get(session_id)

    def list_sessions(self) -> list[dict[str, Any]]:
        return [
            {"id": s.id, "status": s.status.value, "config": s.config.provider,
             "checkpoints": len(s.checkpoints), "created_at": s.created_at}
            for s in self._active.values()
        ]

    def archive(self, session_id: str) -> bool:
        state = self._active.get(session_id)
        if not state:
            return False
        state.status = SessionStatus.ARCHIVED
        self._save(state)
        return True

    def _save(self, state: SessionState) -> None:
        path = self._base_dir / f"{state.id}.json"
        path.write_text(json.dumps({
            "id": state.id, "status": state.status.value,
            "config": {"provider": state.config.provider, "model": state.config.model,
                       "effort_level": state.config.effort_level},
            "checkpoints": [{"id": c.id, "name": c.name, "created_at": c.created_at}
                          for c in state.checkpoints],
            "created_at": state.created_at, "updated_at": state.updated_at,
            "parent_session_id": state.parent_session_id,
        }, indent=2))

    def _load_sessions(self) -> None:
        for path in self._base_dir.glob("*.json"):
            try:
                data = json.loads(path.read_text())
                state = SessionState(
                    id=data["id"],
                    status=SessionStatus(data.get("status", "active")),
                    config=SessionConfig(**data.get("config", {})),
                    created_at=data.get("created_at", 0),
                    parent_session_id=data.get("parent_session_id", ""),
                )
                self._active[state.id] = state
            except Exception:
                pass
