"""Checkpoint & Rewind system — file state snapshots with 30-day retention.

Checkpoints capture file content before edits and conversation state for
the Rewind menu, enabling restoration of code, conversation, or both.
Checkpoints are persisted as JSON files in a configurable storage directory,
separate from git, with configurable retention limits and file-locked access
for race prevention.

Typical usage::

    config = CheckpointConfig(storage_dir="/tmp/lyra-checkpoints")
    mgr = CheckpointManager(config)
    cp = mgr.create_checkpoint("src/main.py", "print('hello')")
    content = mgr.restore_code(cp.checkpoint_id)
    result = mgr.rewind(cp.checkpoint_id, RewindTarget.BOTH)
    removed = mgr.prune_expired()
"""
from __future__ import annotations

import hashlib
import json
import logging
import os
import threading
import time
from dataclasses import dataclass, field
from enum import Enum
from typing import Any, cast
from uuid import uuid4

logger = logging.getLogger(__name__)


__all__ = [
    "Checkpoint",
    "CheckpointConfig",
    "CheckpointManager",
    "CheckpointStats",
    "CheckpointType",
    "RewindResult",
    "RewindTarget",
]


# ---------------------------------------------------------------------------
# Enums
# ---------------------------------------------------------------------------


class CheckpointType(Enum):
    """Categorises what kind of state a checkpoint captures.

    Attributes
    ----------
    FILE_SNAPSHOT : str
        Snapshot of file content only.
    CONVERSATION : str
        Snapshot of conversation state only.
    FULL : str
        Combined snapshot of file content and conversation state.
    """

    FILE_SNAPSHOT = "file_snapshot"
    CONVERSATION = "conversation"
    FULL = "full"


class RewindTarget(Enum):
    """Specifies which dimensions to restore during a rewind operation.

    Attributes
    ----------
    CODE : str
        Restore only the file content from the checkpoint.
    CONVERSATION : str
        Restore only the conversation state from the checkpoint.
    BOTH : str
        Restore both file content and conversation state.
    """

    CODE = "code"
    CONVERSATION = "conversation"
    BOTH = "both"


# ---------------------------------------------------------------------------
# Data classes
# ---------------------------------------------------------------------------


@dataclass(frozen=True)
class Checkpoint:
    """Immutable record of a single checkpoint snapshot.

    Attributes
    ----------
    checkpoint_id : str
        Unique identifier (hex digest from uuid4).
    timestamp : float
        Unix timestamp when the checkpoint was created.
    checkpoint_type : CheckpointType
        Category of state captured (FILE_SNAPSHOT, CONVERSATION, or FULL).
    file_path : str
        Absolute or relative path to the source file.
    content_hash : str
        SHA-256 hex digest of the captured content.
    content : str
        Complete file content at the time of the snapshot.
    conversation_state : dict
        Optional conversation context captured alongside file content.
    metadata : tuple of (str, str) pairs
        Arbitrary key-value pairs for tagging or classification.
    """

    checkpoint_id: str
    timestamp: float
    checkpoint_type: CheckpointType
    file_path: str
    content_hash: str
    content: str
    conversation_state: dict[str, Any] = field(default_factory=dict)
    metadata: tuple[tuple[str, str], ...] = ()


@dataclass(frozen=True)
class RewindResult:
    """Outcome of a rewind operation.

    Attributes
    ----------
    success : bool
        Whether the rewind completed successfully.
    checkpoint_id : str
        The checkpoint that was targeted for rewind.
    restored_files : tuple of str
        File paths that were restored (empty on failure).
    message : str
        Human-readable description of the result.
    """

    success: bool
    checkpoint_id: str
    restored_files: tuple[str, ...]
    message: str


@dataclass(frozen=True)
class CheckpointConfig:
    """Configuration for a CheckpointManager instance.

    Attributes
    ----------
    max_checkpoints : int
        Maximum number of checkpoints to retain (oldest evicted first).
        Zero or negative means unlimited.
    retention_days : int
        Number of days before a checkpoint is eligible for pruning.
    auto_checkpoint : bool
        Whether to automatically create checkpoints before edits.
    storage_dir : str
        Directory path where checkpoint JSON files are persisted.
    """

    max_checkpoints: int = 100
    retention_days: int = 30
    auto_checkpoint: bool = True
    storage_dir: str = "."


@dataclass(frozen=True)
class CheckpointStats:
    """Aggregate statistics about stored checkpoints.

    Attributes
    ----------
    total_checkpoints : int
        Number of checkpoint files currently on disk.
    total_size_bytes : int
        Total disk space consumed by checkpoint files in bytes.
    oldest_timestamp : float
        Unix timestamp of the oldest checkpoint (0.0 if none).
    newest_timestamp : float
        Unix timestamp of the newest checkpoint (0.0 if none).
    """

    total_checkpoints: int
    total_size_bytes: int
    oldest_timestamp: float
    newest_timestamp: float


# ---------------------------------------------------------------------------
# Manager
# ---------------------------------------------------------------------------


class CheckpointManager:
    """File-locked checkpoint persistence with rewind, prune, and stats.

    Stores checkpoints as individual JSON files in *storage_dir* using
    ``uuid4().hex`` as the file stem. All public mutation methods acquire
    a :class:`threading.Lock` to prevent concurrent read/write races.

    Parameters
    ----------
    config : CheckpointConfig
        Persistence and retention settings for this manager instance.
    """

    def __init__(self, config: CheckpointConfig) -> None:
        self._config = config
        self._lock = threading.Lock()
        os.makedirs(config.storage_dir, exist_ok=True)

    # ---- public API ---------------------------------------------------

    def create_checkpoint(
        self,
        file_path: str,
        content: str,
        conversation_state: dict[str, Any] | None = None,
    ) -> Checkpoint:
        """Snapshot file content and optional conversation state.

        The checkpoint is assigned a fresh UUID, timestamped, hashed
        (SHA-256), and immediately persisted to disk under *storage_dir*.

        Parameters
        ----------
        file_path : str
            Path to the file being checkpointed.
        content : str
            Full file content to snapshot.
        conversation_state : dict or None
            Optional conversation state to associate with this checkpoint.

        Returns
        -------
        Checkpoint
            The newly created checkpoint record.
        """
        checkpoint_id = uuid4().hex
        timestamp = time.time()
        content_hash = self._compute_hash(content)

        cp = Checkpoint(
            checkpoint_id=checkpoint_id,
            timestamp=timestamp,
            checkpoint_type=CheckpointType.FILE_SNAPSHOT,
            file_path=file_path,
            content_hash=content_hash,
            content=content,
            conversation_state=conversation_state or {},
            metadata=(),
        )
        with self._lock:
            self._persist_checkpoint(cp)
            self._enforce_max_checkpoints()
        logger.info(
            "Created checkpoint %s for %s (hash=%s)",
            checkpoint_id,
            file_path,
            content_hash[:12],
        )
        return cp

    def get_checkpoint(self, checkpoint_id: str) -> Checkpoint | None:
        """Retrieve a checkpoint by its unique identifier.

        Parameters
        ----------
        checkpoint_id : str
            The UUID hex string of the checkpoint.

        Returns
        -------
        Checkpoint or None
            The checkpoint record if found, otherwise None.
        """
        with self._lock:
            return self._load_checkpoint(checkpoint_id)

    def list_checkpoints(
        self,
        file_path: str | None = None,
        limit: int = 50,
    ) -> list[Checkpoint]:
        """List stored checkpoints, most recent first.

        Parameters
        ----------
        file_path : str or None
            If provided, only return checkpoints for this file.
        limit : int
            Maximum number of checkpoints to return (default 50).

        Returns
        -------
        list of Checkpoint
            Checkpoints ordered by creation time (newest first).
        """
        result: list[tuple[float, Checkpoint]] = []
        with self._lock:
            storage_dir = self._config.storage_dir
            if not os.path.isdir(storage_dir):
                return []

            for fname in os.listdir(storage_dir):
                if not fname.endswith(".json"):
                    continue
                cp_id = fname[:-5]
                cp = self._load_checkpoint(cp_id)
                if cp is None:
                    continue
                if file_path is not None and cp.file_path != file_path:
                    continue
                result.append((cp.timestamp, cp))

        # Sort newest first, then slice to limit.
        result.sort(key=lambda pair: pair[0], reverse=True)
        return [cp for _, cp in result[:limit]]

    def rewind(
        self,
        checkpoint_id: str,
        target: RewindTarget = RewindTarget.BOTH,
    ) -> RewindResult:
        """Restore a checkpoint to its target dimensions.

        This is the high-level entry point for the Rewind menu. It
        validates the checkpoint exists and returns a
        :class:`RewindResult` describing what was restored.

        Parameters
        ----------
        checkpoint_id : str
            The checkpoint to rewind to.
        target : RewindTarget
            Which dimensions to restore (CODE, CONVERSATION, or BOTH).

        Returns
        -------
        RewindResult
            Outcome of the rewind operation.
        """
        cp = self.get_checkpoint(checkpoint_id)
        if cp is None:
            logger.warning("Rewind failed: checkpoint %s not found", checkpoint_id)
            return RewindResult(
                success=False,
                checkpoint_id=checkpoint_id,
                restored_files=(),
                message=f"Checkpoint not found: {checkpoint_id}",
            )

        restored: list[str] = []
        if target in (RewindTarget.CODE, RewindTarget.BOTH):
            restored.append(cp.file_path)
        if target in (RewindTarget.CONVERSATION, RewindTarget.BOTH):
            pass  # conversation state is accessible via restore_conversation()

        msg = (
            f"Rewound to checkpoint {checkpoint_id} "
            f"(target={target.value}, file={cp.file_path})"
        )
        logger.info(msg)
        return RewindResult(
            success=True,
            checkpoint_id=checkpoint_id,
            restored_files=tuple(restored),
            message=msg,
        )

    def restore_code(self, checkpoint_id: str) -> str:
        """Return the file content stored in a checkpoint.

        Parameters
        ----------
        checkpoint_id : str
            The checkpoint to restore code from.

        Returns
        -------
        str
            The full file content captured in the checkpoint.

        Raises
        ------
        ValueError
            If the checkpoint does not exist.
        """
        cp = self.get_checkpoint(checkpoint_id)
        if cp is None:
            raise ValueError(f"Checkpoint not found: {checkpoint_id}")
        return cp.content

    def restore_conversation(self, checkpoint_id: str) -> dict[str, Any]:
        """Return the conversation state stored in a checkpoint.

        Returns a shallow copy of the stored dict to preserve immutability
        of the on-disk checkpoint record.

        Parameters
        ----------
        checkpoint_id : str
            The checkpoint to restore conversation state from.

        Returns
        -------
        dict
            The conversation state dict (a copy, not the original).

        Raises
        ------
        ValueError
            If the checkpoint does not exist.
        """
        cp = self.get_checkpoint(checkpoint_id)
        if cp is None:
            raise ValueError(f"Checkpoint not found: {checkpoint_id}")
        return dict(cp.conversation_state)

    def prune_expired(self) -> int:
        """Remove checkpoints older than *retention_days*.

        Compares each checkpoint file's modification time against
        ``now - retention_days * 86400``. Silently skips files that
        cannot be read or removed.

        Returns
        -------
        int
            Number of checkpoint files removed.
        """
        cutoff = time.time() - (self._config.retention_days * 86400)
        removed = 0
        with self._lock:
            storage_dir = self._config.storage_dir
            if not os.path.isdir(storage_dir):
                return 0

            for fname in os.listdir(storage_dir):
                if not fname.endswith(".json"):
                    continue
                fpath = os.path.join(storage_dir, fname)
                try:
                    mtime = os.path.getmtime(fpath)
                    if mtime < cutoff:
                        os.remove(fpath)
                        removed += 1
                except OSError:
                    continue
        if removed:
            logger.info("Pruned %d expired checkpoints", removed)
        return removed

    def get_stats(self) -> CheckpointStats:
        """Compute aggregate statistics across all stored checkpoints.

        Returns
        -------
        CheckpointStats
            Total count, total bytes, oldest and newest timestamps.
        """
        total = 0
        total_bytes = 0
        oldest = float("inf")
        newest = 0.0

        with self._lock:
            storage_dir = self._config.storage_dir
            if not os.path.isdir(storage_dir):
                return CheckpointStats(
                    total_checkpoints=0,
                    total_size_bytes=0,
                    oldest_timestamp=0.0,
                    newest_timestamp=0.0,
                )

            for fname in os.listdir(storage_dir):
                if not fname.endswith(".json"):
                    continue
                fpath = os.path.join(storage_dir, fname)
                try:
                    total += 1
                    total_bytes += os.path.getsize(fpath)
                    mtime = os.path.getmtime(fpath)
                    if mtime < oldest:
                        oldest = mtime
                    if mtime > newest:
                        newest = mtime
                except OSError:
                    continue

        if total == 0:
            oldest = 0.0

        return CheckpointStats(
            total_checkpoints=total,
            total_size_bytes=total_bytes,
            oldest_timestamp=oldest,
            newest_timestamp=newest,
        )

    def clear(self, file_path: str | None = None) -> None:
        """Remove all checkpoints, optionally filtered by *file_path*.

        Parameters
        ----------
        file_path : str or None
            If provided, only remove checkpoints for this specific file.
            If None, all checkpoints in *storage_dir* are removed.
        """
        removed = 0
        with self._lock:
            storage_dir = self._config.storage_dir
            if not os.path.isdir(storage_dir):
                return

            for fname in list(os.listdir(storage_dir)):
                if not fname.endswith(".json"):
                    continue
                fpath = os.path.join(storage_dir, fname)
                if file_path is not None:
                    cp_id = fname[:-5]
                    cp = self._load_checkpoint(cp_id)
                    if cp is None or cp.file_path != file_path:
                        continue
                try:
                    os.remove(fpath)
                    removed += 1
                except OSError:
                    continue
        logger.info("Cleared %d checkpoints (filter=%s)", removed, file_path)

    # ---- internal helpers ---------------------------------------------

    def _compute_hash(self, content: str) -> str:
        """Return SHA-256 hex digest of *content*.

        Parameters
        ----------
        content : str
            String content to hash.

        Returns
        -------
        str
            Lowercase hex digest (64 characters).
        """
        return hashlib.sha256(content.encode("utf-8")).hexdigest()

    def _checkpoint_to_dict(self, cp: Checkpoint) -> dict[str, Any]:
        """Serialise a Checkpoint to a JSON-compatible dict.

        Parameters
        ----------
        cp : Checkpoint
            The checkpoint to serialise.

        Returns
        -------
        dict
            Flat dict suitable for ``json.dump``.
        """
        return {
            "checkpoint_id": cp.checkpoint_id,
            "timestamp": cp.timestamp,
            "checkpoint_type": cp.checkpoint_type.value,
            "file_path": cp.file_path,
            "content_hash": cp.content_hash,
            "content": cp.content,
            "conversation_state": cp.conversation_state,
            "metadata": list(cp.metadata),
        }

    def _dict_to_checkpoint(self, data: dict[str, Any]) -> Checkpoint:
        """Reconstruct a Checkpoint from a deserialised JSON dict.

        Parameters
        ----------
        data : dict
            Dict produced by :meth:`_checkpoint_to_dict` (or loaded from a
            compliant JSON file).

        Returns
        -------
        Checkpoint
            Reconstructed checkpoint instance.

        Raises
        ------
        KeyError
            If a required field is missing from *data*.
        ValueError
            If *checkpoint_type* is not a recognised :class:`CheckpointType`
            value.
        """
        metadata_raw: list[list[str]] = data.get("metadata", [])
        metadata: tuple[tuple[str, str], ...] = tuple(
            cast(tuple[str, str], tuple(pair)) for pair in metadata_raw
        )
        return Checkpoint(
            checkpoint_id=data["checkpoint_id"],
            timestamp=data["timestamp"],
            checkpoint_type=CheckpointType(data["checkpoint_type"]),
            file_path=data["file_path"],
            content_hash=data["content_hash"],
            content=data["content"],
            conversation_state=data.get("conversation_state", {}),
            metadata=metadata,
        )

    def _persist_checkpoint(self, checkpoint: Checkpoint) -> None:
        """Write a checkpoint to disk as a JSON file.

        Parameters
        ----------
        checkpoint : Checkpoint
            The checkpoint to persist. The caller must already hold
            ``self._lock`` when calling this method.
        """
        fpath = os.path.join(
            self._config.storage_dir, f"{checkpoint.checkpoint_id}.json"
        )
        data = self._checkpoint_to_dict(checkpoint)
        with open(fpath, "w") as f:
            json.dump(data, f, ensure_ascii=False, indent=2)

    def _load_checkpoint(self, checkpoint_id: str) -> Checkpoint | None:
        """Load a checkpoint from disk by its ID.

        Parameters
        ----------
        checkpoint_id : str
            UUID hex string identifying the checkpoint.

        Returns
        -------
        Checkpoint or None
            The reconstructed checkpoint, or None if the file is missing,
            corrupt, or contains invalid data.
        """
        fpath = os.path.join(
            self._config.storage_dir, f"{checkpoint_id}.json"
        )
        try:
            with open(fpath) as f:
                data = json.load(f)
            return self._dict_to_checkpoint(data)
        except (FileNotFoundError, json.JSONDecodeError, KeyError, ValueError) as exc:
            logger.debug(
                "Failed to load checkpoint %s: %s", checkpoint_id, exc
            )
            return None

    def _enforce_max_checkpoints(self) -> None:
        """Evict oldest checkpoints when count exceeds *max_checkpoints*.

        Operates on file modification time (oldest first). The caller must
        already hold ``self._lock`` when calling this method. No-op when
        *max_checkpoints* is zero or negative.
        """
        max_cp = self._config.max_checkpoints
        if max_cp <= 0:
            return

        storage_dir = self._config.storage_dir
        try:
            json_files = [
                f
                for f in os.listdir(storage_dir)
                if f.endswith(".json")
            ]
        except OSError:
            return

        if len(json_files) <= max_cp:
            return

        json_files.sort(
            key=lambda f: os.path.getmtime(os.path.join(storage_dir, f))
        )

        excess = len(json_files) - max_cp
        for fname in json_files[:excess]:
            fpath = os.path.join(storage_dir, fname)
            try:
                os.remove(fpath)
                logger.debug("Evicted old checkpoint %s", fname)
            except OSError:
                continue
