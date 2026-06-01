"""Persistent checkpoint manager for workflow state persistence.

Extends DynamicWorkflowEngine's checkpoint system with disk-backed
persistence, allowing long-running workflows to survive process
restarts.
"""

from __future__ import annotations

import json
import os
import time
import uuid
from dataclasses import dataclass, field
from typing import Any


@dataclass
class CheckpointRecord:
    """Serializable checkpoint snapshot."""

    checkpoint_id: str
    workflow_id: str
    step_id: str
    completed_step_ids: list[str] = field(default_factory=list)
    failed_step_ids: list[str] = field(default_factory=list)
    variables: dict[str, Any] = field(default_factory=dict)
    created_at: float = field(default_factory=time.time)
    metadata: dict[str, str] = field(default_factory=dict)


class PersistentCheckpointManager:
    """Disk-backed checkpoint manager for workflow persistence.

    Saves and restores workflow checkpoints to a directory, enabling
    multi-day workflow runs that survive process restarts.

    Usage::

        mgr = PersistentCheckpointManager("/tmp/lyra-checkpoints")
        record = mgr.save("wf-1", "step-3", completed=["step-1","step-2"])
        restored = mgr.load("wf-1")
        mgr.prune(max_age_s=86400 * 7)
    """

    def __init__(self, base_dir: str) -> None:
        self.base_dir = base_dir
        self._records: dict[str, CheckpointRecord] = {}

    @property
    def checkpoint_dir(self) -> str:
        return os.path.join(self.base_dir, "checkpoints")

    def ensure_dir(self) -> str:
        os.makedirs(self.checkpoint_dir, exist_ok=True)
        return self.checkpoint_dir

    def save(
        self,
        workflow_id: str,
        step_id: str,
        *,
        completed: list[str] | None = None,
        failed: list[str] | None = None,
        variables: dict[str, Any] | None = None,
        metadata: dict[str, str] | None = None,
    ) -> CheckpointRecord:
        """Persist a checkpoint to disk."""
        self.ensure_dir()

        record = CheckpointRecord(
            checkpoint_id=f"ckpt_{uuid.uuid4().hex[:12]}",
            workflow_id=workflow_id,
            step_id=step_id,
            completed_step_ids=list(completed or []),
            failed_step_ids=list(failed or []),
            variables=dict(variables or {}),
            metadata=dict(metadata or {}),
        )
        self._records[workflow_id] = record
        self._write(record)
        return record

    def load(self, workflow_id: str) -> CheckpointRecord | None:
        """Load the latest checkpoint for a workflow."""
        if workflow_id in self._records:
            return self._records[workflow_id]
        return self._read(workflow_id)

    def delete(self, workflow_id: str) -> bool:
        """Delete a workflow's checkpoint."""
        self._records.pop(workflow_id, None)
        path = self._path_for(workflow_id)
        if os.path.exists(path):
            os.remove(path)
            return True
        return False

    def list_workflows(self) -> list[str]:
        """List all workflow IDs with checkpoints."""
        self.ensure_dir()
        ids: list[str] = []
        for fname in os.listdir(self.checkpoint_dir):
            if fname.endswith(".json"):
                ids.append(fname[:-5])
        return sorted(ids)

    def prune(self, *, max_age_s: float = 86400 * 7) -> int:
        """Remove checkpoints older than max_age_s. Returns count removed."""
        cutoff = time.time() - max_age_s
        removed = 0
        for wf_id in self.list_workflows():
            record = self._read(wf_id)
            if record is not None and record.created_at < cutoff:
                self.delete(wf_id)
                removed += 1
        return removed

    def count(self) -> int:
        return len(self._records)

    # ── Internal ──────────────────────────────────────────────────────

    def _path_for(self, workflow_id: str) -> str:
        return os.path.join(self.checkpoint_dir, f"{workflow_id}.json")

    def _write(self, record: CheckpointRecord) -> None:
        path = self._path_for(record.workflow_id)
        data = {
            "checkpoint_id": record.checkpoint_id,
            "workflow_id": record.workflow_id,
            "step_id": record.step_id,
            "completed_step_ids": record.completed_step_ids,
            "failed_step_ids": record.failed_step_ids,
            "variables": record.variables,
            "created_at": record.created_at,
            "metadata": record.metadata,
        }
        with open(path, "w") as f:
            json.dump(data, f, indent=2)

    def _read(self, workflow_id: str) -> CheckpointRecord | None:
        path = self._path_for(workflow_id)
        if not os.path.exists(path):
            return None
        with open(path) as f:
            data = json.load(f)
        record = CheckpointRecord(
            checkpoint_id=data["checkpoint_id"],
            workflow_id=data["workflow_id"],
            step_id=data["step_id"],
            completed_step_ids=data.get("completed_step_ids", []),
            failed_step_ids=data.get("failed_step_ids", []),
            variables=data.get("variables", {}),
            created_at=data.get("created_at", 0.0),
            metadata=data.get("metadata", {}),
        )
        self._records[workflow_id] = record
        return record
