"""
Checkpoint-based recovery for agent sessions.

Provides CheckpointManager for saving, restoring, and listing agent
state checkpoints at step boundaries.
"""

from __future__ import annotations

import json
import logging
from dataclasses import dataclass, field
from datetime import datetime, timezone
from pathlib import Path
from typing import Any

logger = logging.getLogger(__name__)


class CheckpointError(Exception):
    """Base exception for checkpoint operations."""


class CheckpointSaveError(CheckpointError):
    """Raised when saving a checkpoint fails."""


class CheckpointRestoreError(CheckpointError):
    """Raised when restoring a checkpoint fails."""


@dataclass
class Checkpoint:
    """A single checkpoint record."""

    agent_id: str
    timestamp: datetime
    state: dict[str, Any]


@dataclass
class CheckpointManager:
    """Persists and restores agent state at step boundaries.

    Each checkpoint is stored as a JSON file under *checkpoints_dir*,
    named ``{agent_id}.{timestamp}.checkpoint.json``.

    Usage::

        mgr = CheckpointManager(base_dir=Path("/tmp/checkpoints"))
        mgr.save("agent-1", {"step": 3, "context": {...}})
        state = mgr.restore("agent-1")
        checkpoints = mgr.list_checkpoints()
    """

    base_dir: Path
    _checkpoints: dict[str, list[Checkpoint]] = field(default_factory=dict, init=False, repr=False)

    def __post_init__(self) -> None:
        self.base_dir.mkdir(parents=True, exist_ok=True)
        self._load_index()

    # ------------------------------------------------------------------
    # Public API
    # ------------------------------------------------------------------

    def save(self, agent_id: str, state_dict: dict[str, Any]) -> Checkpoint:
        """Persist a checkpoint for *agent_id*.

        Parameters
        ----------
        agent_id:
            Unique agent identifier.
        state_dict:
            Arbitrary JSON-serialisable state to persist.

        Returns
        -------
        The newly created Checkpoint.

        Raises
        ------
        CheckpointSaveError
            If serialisation or disk write fails.
        """
        now = datetime.now(timezone.utc)
        filename = f"{agent_id}.{now.isoformat(timespec='seconds').replace(':', '-')}.checkpoint.json"
        path = self.base_dir / filename

        payload = {
            "agent_id": agent_id,
            "timestamp": now.isoformat(timespec="seconds"),
            "state": state_dict,
        }

        try:
            with open(path, "w") as f:
                json.dump(payload, f, indent=2)
        except (OSError, ValueError) as exc:
            raise CheckpointSaveError(
                f"Failed to save checkpoint for agent '{agent_id}': {exc}"
            ) from exc

        cp = Checkpoint(agent_id=agent_id, timestamp=now, state=state_dict)
        self._checkpoints.setdefault(agent_id, []).append(cp)
        logger.debug("Checkpoint saved for agent '%s' at %s", agent_id, now.isoformat())
        return cp

    def restore(self, agent_id: str) -> dict[str, Any]:
        """Restore the *latest* checkpoint for *agent_id*.

        Parameters
        ----------
        agent_id:
            Agent whose checkpoint to restore.

        Returns
        -------
        The state dict from the most recent checkpoint.

        Raises
        ------
        CheckpointRestoreError
            If no checkpoint exists for the agent.
        """
        checkpoints = self._checkpoints.get(agent_id)
        if not checkpoints:
            raise CheckpointRestoreError(f"No checkpoints found for agent '{agent_id}'")

        latest = max(checkpoints, key=lambda cp: cp.timestamp)
        return latest.state

    def list_checkpoints(self) -> list[Checkpoint]:
        """Return all known checkpoints across all agents."""
        all_cps: list[Checkpoint] = []
        for cps in self._checkpoints.values():
            all_cps.extend(cps)
        return sorted(all_cps, key=lambda cp: cp.timestamp, reverse=True)

    # ------------------------------------------------------------------
    # Internal helpers
    # ------------------------------------------------------------------

    def _load_index(self) -> None:
        """Scan *base_dir* and rebuild the in-memory index."""
        if not self.base_dir.is_dir():
            return

        for child in sorted(self.base_dir.iterdir()):
            if child.suffix != ".json" or not child.name.endswith(".checkpoint.json"):
                continue
            try:
                with open(child) as f:
                    payload = json.load(f)
                agent_id = payload.get("agent_id", "unknown")
                ts_str = payload.get("timestamp", "")
                timestamp = datetime.fromisoformat(ts_str) if ts_str else datetime.now(timezone.utc)
                state = payload.get("state", {})
                cp = Checkpoint(agent_id=agent_id, timestamp=timestamp, state=state)
                self._checkpoints.setdefault(agent_id, []).append(cp)
            except (OSError, json.JSONDecodeError, ValueError) as exc:
                logger.warning("Skipping corrupt checkpoint file '%s': %s", child.name, exc)
