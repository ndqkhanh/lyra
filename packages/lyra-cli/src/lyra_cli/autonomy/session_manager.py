"""Session persistence with checkpointing for Lyra autonomy.

Supports saving and restoring full autonomy state as JSON, enabling
resume-after-restart.
"""

from __future__ import annotations

import json
import logging
from dataclasses import dataclass, field, asdict
from datetime import datetime, timezone
from pathlib import Path
from typing import Any

logger = logging.getLogger(__name__)


class CheckpointNotFoundError(Exception):
    """Raised when a requested checkpoint file does not exist."""


@dataclass(frozen=True)
class SessionCheckpoint:
    """Serialisable snapshot of the autonomy engine at a point in time."""

    session_id: str
    state: str  # serialised AutonomyState value
    context: dict[str, Any] = field(default_factory=dict)
    goal: str = ""
    created_at: str = ""  # ISO-8601 string

    def to_dict(self) -> dict[str, Any]:
        """Return a JSON-serialisable dictionary."""
        return asdict(self)

    @classmethod
    def from_dict(cls, data: dict[str, Any]) -> SessionCheckpoint:
        """Rehydrate from a dictionary (e.g. parsed from JSON)."""
        return cls(
            session_id=data["session_id"],
            state=data["state"],
            context=data.get("context", {}),
            goal=data.get("goal", ""),
            created_at=data.get("created_at", ""),
        )


@dataclass
class SessionManager:
    """Persists and restores autonomy session state.

    Args:
        checkpoint_dir: Directory where checkpoint JSON files live.
            Default: ``~/.lyra/checkpoints/``.
    """

    checkpoint_dir: Path = field(
        default_factory=lambda: Path.home() / ".lyra" / "checkpoints"
    )

    def __post_init__(self) -> None:
        self.checkpoint_dir.mkdir(parents=True, exist_ok=True)

    # ------------------------------------------------------------------
    # Public API
    # ------------------------------------------------------------------

    def save_checkpoint(self, checkpoint: SessionCheckpoint) -> Path:
        """Persist *checkpoint* to a JSON file and return its path.

        The file is named ``{session_id}-{timestamp}.json``.
        """
        timestamp = checkpoint.created_at or _now_iso()
        filename = f"{checkpoint.session_id}-{timestamp}.json"
        path = self.checkpoint_dir / filename
        path.write_text(json.dumps(checkpoint.to_dict(), indent=2))
        logger.info("checkpoint_saved: session=%s path=%s", checkpoint.session_id, path)
        return path

    def load_checkpoint(self, session_id: str) -> SessionCheckpoint:
        """Load the latest checkpoint for *session_id*.

        Raises:
            CheckpointNotFoundError: if no checkpoint file exists.
        """
        candidates = sorted(self.checkpoint_dir.glob(f"{session_id}-*.json"))
        if not candidates:
            raise CheckpointNotFoundError(
                f"No checkpoint found for session {session_id!r}"
            )
        latest = candidates[-1]
        data = json.loads(latest.read_text())
        logger.info("checkpoint_loaded: session=%s path=%s", session_id, latest)
        return SessionCheckpoint.from_dict(data)

    def list_checkpoints(self, session_id: str | None = None) -> list[SessionCheckpoint]:
        """List all stored checkpoints, optionally filtered by *session_id*."""
        pattern = f"{session_id}-*.json" if session_id else "*.json"
        checkpoints: list[SessionCheckpoint] = []
        for path in sorted(self.checkpoint_dir.glob(pattern)):
            checkpoints.append(
                SessionCheckpoint.from_dict(json.loads(path.read_text()))
            )
        return checkpoints

    def delete_checkpoint(self, session_id: str) -> int:
        """Remove all checkpoint files for *session_id*. Returns count deleted."""
        count = 0
        for path in self.checkpoint_dir.glob(f"{session_id}-*.json"):
            path.unlink()
            count += 1
        logger.info("checkpoint_deleted: session=%s count=%d", session_id, count)
        return count

    def checkpoint_exists(self, session_id: str) -> bool:
        """Return True if at least one checkpoint exists for *session_id*."""
        return any(self.checkpoint_dir.glob(f"{session_id}-*.json"))


def _now_iso() -> str:
    """Return current UTC time as ISO-8601 string suitable for filenames."""
    return datetime.now(timezone.utc).strftime("%Y%m%dT%H%M%SZ")
