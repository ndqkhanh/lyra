"""Backup and rollback management."""

from __future__ import annotations

import hashlib
import json
import os
import tempfile
import time
import uuid
from dataclasses import dataclass
from typing import ClassVar

from .exceptions import RollbackError


@dataclass(frozen=True)
class BackupRecord:
    """Metadata about a single backup."""

    backup_id: str
    file_path: str
    backup_path: str
    created_at: float
    content_hash: str


@dataclass(frozen=True)
class RollbackResult:
    """Result of a rollback operation."""

    backup: BackupRecord
    success: bool
    restored_content: str
    verification_hash: str


class RollbackManager:
    """Backup and rollback management for safe code rewrites."""

    BACKUP_DIR: ClassVar[str] = os.path.join(tempfile.gettempdir(), "lyra_rollbacks")

    def __init__(self) -> None:
        os.makedirs(RollbackManager.BACKUP_DIR, exist_ok=True)

    @staticmethod
    def _metadata_path(backup_path: str) -> str:
        return backup_path + ".meta"

    async def create_backup(self, file_path: str, content: str) -> BackupRecord:
        """Create a backup of the given file content."""
        backup_id = str(uuid.uuid4())
        content_hash = hashlib.sha256(content.encode()).hexdigest()
        timestamp = time.time()
        backup_path = os.path.join(
            RollbackManager.BACKUP_DIR,
            f"{backup_id}_{os.path.basename(file_path)}",
        )
        try:
            with open(backup_path, "w") as f:
                f.write(content)
            metadata = {
                "backup_id": backup_id,
                "file_path": file_path,
                "backup_path": backup_path,
                "created_at": timestamp,
                "content_hash": content_hash,
            }
            with open(RollbackManager._metadata_path(backup_path), "w") as f:
                json.dump(metadata, f)
        except OSError as e:
            raise RollbackError(f"Failed to create backup: {e}") from e
        return BackupRecord(
            backup_id=backup_id,
            file_path=file_path,
            backup_path=backup_path,
            created_at=timestamp,
            content_hash=content_hash,
        )

    async def restore_backup(self, backup_id: str) -> RollbackResult:
        """Restore a file from its backup by backup ID."""
        records = await self.list_backups()
        matching = [r for r in records if r.backup_id == backup_id]
        if not matching:
            raise RollbackError(f"Backup not found: {backup_id}")
        record = matching[0]
        if not os.path.isfile(record.backup_path):
            raise RollbackError(f"Backup file missing: {record.backup_path}")
        try:
            with open(record.backup_path) as f:
                restored_content = f.read()
        except OSError as e:
            raise RollbackError(f"Failed to read backup: {e}") from e
        verification_hash = hashlib.sha256(restored_content.encode()).hexdigest()
        success = verification_hash == record.content_hash
        if success:
            try:
                with open(record.file_path, "w") as f:
                    f.write(restored_content)
            except OSError as e:
                raise RollbackError(f"Failed to restore file: {e}") from e
        return RollbackResult(
            backup=record,
            success=success,
            restored_content=restored_content,
            verification_hash=verification_hash,
        )

    async def list_backups(self, file_path: str = "") -> tuple[BackupRecord, ...]:
        """List all backups, optionally filtered by original file path."""
        records: list[BackupRecord] = []
        if not os.path.isdir(RollbackManager.BACKUP_DIR):
            return ()
        for fn in os.listdir(RollbackManager.BACKUP_DIR):
            full = os.path.join(RollbackManager.BACKUP_DIR, fn)
            if not os.path.isfile(full) or fn.endswith(".meta"):
                continue
            meta_path = RollbackManager._metadata_path(full)
            if os.path.isfile(meta_path):
                try:
                    with open(meta_path) as f:
                        meta = json.load(f)
                    record = BackupRecord(
                        backup_id=meta["backup_id"],
                        file_path=meta["file_path"],
                        backup_path=meta["backup_path"],
                        created_at=meta["created_at"],
                        content_hash=meta["content_hash"],
                    )
                    if not file_path or record.file_path == file_path:
                        records.append(record)
                    continue
                except (OSError, json.JSONDecodeError, KeyError):
                    pass
            try:
                with open(full) as f:
                    content = f.read()
                content_hash = hashlib.sha256(content.encode()).hexdigest()
                parts = fn.split("_", 1)
                backup_id = parts[0]
                fpath = parts[1] if len(parts) > 1 else ""
                created_at = os.path.getmtime(full)
                record = BackupRecord(
                    backup_id=backup_id,
                    file_path=fpath,
                    backup_path=full,
                    created_at=created_at,
                    content_hash=content_hash,
                )
                if not file_path or record.file_path == file_path:
                    records.append(record)
            except (OSError, IndexError):
                continue
        records.sort(key=lambda r: r.created_at, reverse=True)
        return tuple(records)

    async def prune_backups(self, max_age_hours: float = 72.0) -> int:
        """Remove backups older than the specified age."""
        if not os.path.isdir(RollbackManager.BACKUP_DIR):
            return 0
        now = time.time()
        max_age_sec = max_age_hours * 3600
        pruned = 0
        for fn in os.listdir(RollbackManager.BACKUP_DIR):
            full = os.path.join(RollbackManager.BACKUP_DIR, fn)
            if os.path.isfile(full) and (now - os.path.getmtime(full)) > max_age_sec:
                try:
                    os.remove(full)
                    meta = full + ".meta"
                    if os.path.isfile(meta):
                        os.remove(meta)
                    pruned += 1
                except OSError:
                    continue
        return pruned
