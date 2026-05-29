"""Tests for the rollback_manager module."""

from __future__ import annotations

import os
import tempfile

import pytest
from lyra_meta_editor import (
    BackupRecord,
    RollbackError,
    RollbackManager,
    RollbackResult,
)


@pytest.fixture
def manager() -> RollbackManager:
    """Create a RollbackManager with a temp dir."""
    tmpdir = tempfile.mkdtemp()
    old_dir = RollbackManager.BACKUP_DIR
    RollbackManager.BACKUP_DIR = tmpdir
    m = RollbackManager()
    yield m
    RollbackManager.BACKUP_DIR = old_dir
    # Cleanup
    import shutil
    shutil.rmtree(tmpdir, ignore_errors=True)


@pytest.fixture
def temp_file() -> str:
    """Create a temporary file for backup testing."""
    with tempfile.NamedTemporaryFile(mode="w", suffix=".py", delete=False) as f:
        f.write("original content")
        path = f.name
    yield path
    if os.path.isfile(path):
        os.unlink(path)


class TestBackupRecord:
    """Tests for BackupRecord."""

    def test_creation(self) -> None:
        rec = BackupRecord(
            backup_id="abc123",
            file_path="/a.py",
            backup_path="/tmp/bak",
            created_at=1000.0,
            content_hash="deadbeef",
        )
        assert rec.backup_id == "abc123"
        assert rec.content_hash == "deadbeef"

    def test_immutable(self) -> None:
        rec = BackupRecord("id", "/a.py", "/tmp/bak", 1.0, "hash")
        with pytest.raises(AttributeError):
            rec.backup_id = "new"  # type: ignore[misc]


class TestRollbackResult:
    """Tests for RollbackResult."""

    def test_creation(self) -> None:
        rec = BackupRecord("id", "/a.py", "/tmp/bak", 1.0, "hash")
        result = RollbackResult(
            backup=rec,
            success=True,
            restored_content="restored",
            verification_hash="vhash",
        )
        assert result.success is True
        assert result.restored_content == "restored"


class TestRollbackManager:
    """Tests for RollbackManager."""

    @pytest.mark.asyncio
    async def test_create_backup(self, manager: RollbackManager, temp_file: str) -> None:
        content = "original content"
        record = await manager.create_backup(temp_file, content)
        assert os.path.isfile(record.backup_path)
        assert record.file_path == temp_file
        assert record.content_hash != ""

    @pytest.mark.asyncio
    async def test_create_backup_writes_correct_content(
        self, manager: RollbackManager, temp_file: str
    ) -> None:
        content = "test data"
        record = await manager.create_backup(temp_file, content)
        with open(record.backup_path) as f:
            assert f.read() == content

    @pytest.mark.asyncio
    async def test_list_backups_empty(self, manager: RollbackManager) -> None:
        backups = await manager.list_backups()
        assert backups == ()

    @pytest.mark.asyncio
    async def test_list_backups_after_create(
        self, manager: RollbackManager, temp_file: str
    ) -> None:
        await manager.create_backup(temp_file, "content")
        backups = await manager.list_backups()
        assert len(backups) == 1

    @pytest.mark.asyncio
    async def test_list_backups_filter_by_path(
        self, manager: RollbackManager, temp_file: str
    ) -> None:
        await manager.create_backup(temp_file, "content")
        # Create another file too
        other = temp_file + ".other"
        try:
            await manager.create_backup(other, "other content")
            file_backups = await manager.list_backups(file_path=temp_file)
            assert len(file_backups) == 1
            assert file_backups[0].file_path == temp_file
        finally:
            if os.path.isfile(other):
                os.unlink(other)

    @pytest.mark.asyncio
    async def test_restore_backup(
        self, manager: RollbackManager, temp_file: str
    ) -> None:
        # Write initial content
        with open(temp_file, "w") as f:
            f.write("original content")
        record = await manager.create_backup(temp_file, "original content")
        # Modify file
        with open(temp_file, "w") as f:
            f.write("modified content")
        # Restore
        result = await manager.restore_backup(record.backup_id)
        assert result.success is True
        with open(temp_file) as f:
            assert f.read() == "original content"

    @pytest.mark.asyncio
    async def test_restore_backup_not_found(self, manager: RollbackManager) -> None:
        with pytest.raises(RollbackError, match="not found"):
            await manager.restore_backup("nonexistent_id")

    @pytest.mark.asyncio
    async def test_restore_backup_tampered(
        self, manager: RollbackManager, temp_file: str
    ) -> None:
        content = "original content"
        record = await manager.create_backup(temp_file, content)
        # Tamper with backup file
        with open(record.backup_path, "w") as f:
            f.write("tampered content")
        result = await manager.restore_backup(record.backup_id)
        assert result.success is False
        assert result.verification_hash != record.content_hash

    @pytest.mark.asyncio
    async def test_prune_backups(
        self, manager: RollbackManager, temp_file: str
    ) -> None:
        await manager.create_backup(temp_file, "content")
        # Prune with 0 age to remove everything
        pruned = await manager.prune_backups(max_age_hours=0.0)
        assert pruned >= 1
        backups = await manager.list_backups()
        assert len(backups) == 0

    @pytest.mark.asyncio
    async def test_prune_backups_no_old(self, manager: RollbackManager, temp_file: str) -> None:
        await manager.create_backup(temp_file, "content")
        pruned = await manager.prune_backups(max_age_hours=72.0)
        assert pruned == 0

    @pytest.mark.asyncio
    async def test_multiple_backups_same_file(
        self, manager: RollbackManager, temp_file: str
    ) -> None:
        rec1 = await manager.create_backup(temp_file, "v1")
        rec2 = await manager.create_backup(temp_file, "v2")
        assert rec1.backup_id != rec2.backup_id
        backups = await manager.list_backups(file_path=temp_file)
        assert len(backups) == 2

    @pytest.mark.asyncio
    async def test_content_hash_integrity(
        self, manager: RollbackManager, temp_file: str
    ) -> None:
        content = "exact content"
        record = await manager.create_backup(temp_file, content)
        import hashlib
        expected = hashlib.sha256(content.encode()).hexdigest()
        assert record.content_hash == expected

    @pytest.mark.asyncio
    async def test_create_backup_invalid_dir(
        self, manager: RollbackManager
    ) -> None:
        """Backup for a deeply nested relative path should still succeed
        since it writes to BACKUP_DIR, not to the original file path."""
        record = await manager.create_backup("some/deep/nested/file.py", "content")
        assert os.path.isfile(record.backup_path)
        assert record.file_path == "some/deep/nested/file.py"

    @pytest.mark.asyncio
    async def test_backup_metadata_created(
        self, manager: RollbackManager, temp_file: str
    ) -> None:
        record = await manager.create_backup(temp_file, "content")
        meta_path = os.path.join(
            RollbackManager.BACKUP_DIR,
            os.path.basename(record.backup_path) + ".meta",
        )
        assert os.path.isfile(meta_path)

    def test_rollback_manager_creates_dir(self) -> None:
        tmpdir = tempfile.mkdtemp()
        old = RollbackManager.BACKUP_DIR
        try:
            new_dir = os.path.join(tmpdir, "subdir", "rollbacks")
            RollbackManager.BACKUP_DIR = new_dir
            RollbackManager()
            assert os.path.isdir(new_dir)
        finally:
            RollbackManager.BACKUP_DIR = old
            import shutil
            shutil.rmtree(tmpdir, ignore_errors=True)

    @pytest.mark.asyncio
    async def test_list_backups_after_prune(
        self, manager: RollbackManager, temp_file: str
    ) -> None:
        await manager.create_backup(temp_file, "x")
        await manager.prune_backups(max_age_hours=0.0)
        backups = await manager.list_backups()
        assert len(backups) == 0

    @pytest.mark.asyncio
    async def test_backup_record_hashable(
        self, manager: RollbackManager, temp_file: str
    ) -> None:
        record = await manager.create_backup(temp_file, "content")
        _ = {record: True}

    @pytest.mark.asyncio
    async def test_multiple_restores(
        self, manager: RollbackManager, temp_file: str
    ) -> None:
        with open(temp_file, "w") as f:
            f.write("original")
        record = await manager.create_backup(temp_file, "original")
        for _ in range(3):
            with open(temp_file, "w") as f:
                f.write("modified")
            result = await manager.restore_backup(record.backup_id)
            assert result.success is True
            with open(temp_file) as f:
                assert f.read() == "original"
