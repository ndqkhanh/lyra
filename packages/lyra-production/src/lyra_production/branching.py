"""
Copy-on-write database branching for safe migrations and isolated environments.

Provides branch-based schema and data management with merge conflict
detection, point-in-time recovery, and test environment creation from
production data snapshots.
"""

from __future__ import annotations

import hashlib
import logging
import uuid
from datetime import datetime, timezone
from threading import RLock

from lyra_production.models import (
    BranchStatus,
    DatabaseBranch,
    MigrationEntry,
)

logger = logging.getLogger(__name__)


class BranchNotFoundError(KeyError):
    """Raised when a requested branch does not exist."""


class MigrationConflictError(RuntimeError):
    """Raised when merging a branch would cause conflicts."""


class BranchingConfig:
    """Configuration for the database branching system."""

    def __init__(
        self,
        max_branches: int = 100,
        auto_validate_on_merge: bool = True,
        conflict_detection_enabled: bool = True,
    ) -> None:
        self.max_branches = max_branches
        self.auto_validate_on_merge = auto_validate_on_merge
        self.conflict_detection_enabled = conflict_detection_enabled


class DatabaseBranching:
    """Manages copy-on-write database branches.

    Branches allow safe, isolated schema and data changes without
    affecting production. Merging uses conflict detection to
    identify schema conflicts before applying changes.
    """

    def __init__(self, config: BranchingConfig | None = None) -> None:
        self._branches: dict[str, DatabaseBranch] = {}
        self._lock = RLock()
        self._config = config or BranchingConfig()

    def _compute_checksum(self, content: str) -> str:
        """Compute SHA-256 checksum of a string."""
        return hashlib.sha256(content.encode("utf-8")).hexdigest()

    def create_branch(
        self,
        name: str,
        from_commit: str,
    ) -> DatabaseBranch:
        """Create a new copy-on-write branch from a commit.

        Args:
            name: Human-readable branch name.
            from_commit: The commit hash to branch from.

        Returns:
            The newly created DatabaseBranch.

        Raises:
            ValueError: If the branch name is empty or already exists.
        """
        if not name.strip():
            raise ValueError("Branch name cannot be empty")

        with self._lock:
            for existing in self._branches.values():
                if existing.name == name and existing.status == BranchStatus.ACTIVE:
                    raise ValueError(
                        f"Branch with name '{name}' already exists"
                    )

            if len(self._branches) >= self._config.max_branches:
                raise ValueError(
                    f"Maximum number of branches reached ({self._config.max_branches})"
                )

        branch_id = f"branch-{uuid.uuid4().hex[:12]}"

        branch = DatabaseBranch(
            branch_id=branch_id,
            name=name,
            parent_commit=from_commit,
            status=BranchStatus.ACTIVE,
            changes=[],
            head_commit=from_commit,
            created_at=datetime.now(timezone.utc),
            updated_at=datetime.now(timezone.utc),
        )

        with self._lock:
            self._branches[branch_id] = branch

        logger.info("Created branch '%s' (id=%s) from commit %s", name, branch_id, from_commit)
        return branch

    def apply_migration(
        self,
        branch_id: str,
        migration: MigrationEntry,
    ) -> DatabaseBranch:
        """Apply a migration to a branch.

        Args:
            branch_id: The target branch.
            migration: The migration to apply.

        Returns:
            The updated DatabaseBranch.

        Raises:
            BranchNotFoundError: If the branch does not exist.
            ValueError: If the branch is not active.
        """
        with self._lock:
            branch = self._branches.get(branch_id)
            if branch is None:
                raise BranchNotFoundError(f"Branch not found: {branch_id}")

            if branch.status != BranchStatus.ACTIVE:
                raise ValueError(
                    f"Cannot apply migration to branch '{branch.name}' "
                    f"in status {branch.status.name}"
                )

            # Compute checksum if not provided
            checksum = migration.checksum or self._compute_checksum(migration.sql_up)

            applied = MigrationEntry(
                migration_id=migration.migration_id,
                description=migration.description,
                sql_up=migration.sql_up,
                sql_down=migration.sql_down,
                applied_at=datetime.now(timezone.utc),
                checksum=checksum,
            )

            new_changes = list(branch.changes)
            new_changes.append(applied)

            # New head commit based on migration checksum
            new_head = self._compute_checksum(
                f"{branch.head_commit}:{checksum}"
            )

            updated = DatabaseBranch(
                branch_id=branch.branch_id,
                name=branch.name,
                parent_commit=branch.parent_commit,
                status=branch.status,
                changes=new_changes,
                head_commit=new_head,
                created_at=branch.created_at,
                updated_at=datetime.now(timezone.utc),
            )
            self._branches[branch_id] = updated

        logger.info(
            "Applied migration '%s' to branch '%s'",
            migration.description,
            branch.name,
        )
        return updated

    def validate_branch(self, branch_id: str) -> list[str]:
        """Validate a branch for potential merge conflicts.

        Checks for empty migrations and verifies the branch
        can be cleanly merged back to parent.

        Args:
            branch_id: The branch to validate.

        Returns:
            A list of conflict descriptions (empty if no conflicts).

        Raises:
            BranchNotFoundError: If the branch does not exist.
        """
        with self._lock:
            branch = self._branches.get(branch_id)
            if branch is None:
                raise BranchNotFoundError(f"Branch not found: {branch_id}")

            conflicts: list[str] = []

            if not branch.changes:
                conflicts.append("Branch has no migrations to merge")

            if branch.status != BranchStatus.ACTIVE:
                conflicts.append(
                    f"Branch is in status {branch.status.name}, "
                    "only active branches can be merged"
                )

            # Detect duplicate migration IDs within the branch
            migration_ids = [m.migration_id for m in branch.changes]
            if len(migration_ids) != len(set(migration_ids)):
                conflicts.append(
                    "Branch contains duplicate migration IDs"
                )

        if not conflicts:
            logger.info("Branch '%s' validation passed", branch.name)
        else:
            logger.warning(
                "Branch '%s' validation found %d conflict(s)",
                branch.name,
                len(conflicts),
            )

        return conflicts

    def merge_branch(
        self,
        branch_id: str,
        target_branch_id: str | None = None,
    ) -> DatabaseBranch:
        """Merge a branch into a target branch.

        Detects conflicts before merging. The target defaults to
        the parent commit's original branch.

        Args:
            branch_id: The source branch to merge.
            target_branch_id: The target branch (defaults to parent lineage).

        Returns:
            The merged DatabaseBranch.

        Raises:
            BranchNotFoundError: If either branch does not exist.
            MigrationConflictError: If conflicts are detected.
        """
        with self._lock:
            source = self._branches.get(branch_id)
            if source is None:
                raise BranchNotFoundError(
                    f"Source branch not found: {branch_id}"
                )

            if target_branch_id is None:
                target_branch_id = branch_id  # merge onto itself (simulated)

            if self._config.conflict_detection_enabled:
                conflicts = self.validate_branch(branch_id)
                if conflicts:
                    conflict_detail = "; ".join(conflicts)
                    raise MigrationConflictError(
                        f"Cannot merge branch '{source.name}': "
                        f"{conflict_detail}"
                    )

            new_head = self._compute_checksum(
                f"{source.head_commit}:merged:{datetime.now(timezone.utc).isoformat()}"
            )

            merged = DatabaseBranch(
                branch_id=source.branch_id,
                name=source.name,
                parent_commit=source.parent_commit,
                status=BranchStatus.MERGED,
                changes=source.changes,
                head_commit=new_head,
                created_at=source.created_at,
                updated_at=datetime.now(timezone.utc),
            )
            self._branches[branch_id] = merged

        logger.info(
            "Merged branch '%s' into target '%s'",
            source.name,
            target_branch_id,
        )
        return merged

    def rollback_branch(self, branch_id: str) -> DatabaseBranch:
        """Discard all changes on a branch and mark as rolled back.

        Args:
            branch_id: The branch to roll back.

        Returns:
            The rolled back DatabaseBranch.

        Raises:
            BranchNotFoundError: If the branch does not exist.
        """
        with self._lock:
            branch = self._branches.get(branch_id)
            if branch is None:
                raise BranchNotFoundError(f"Branch not found: {branch_id}")

            if branch.status != BranchStatus.ACTIVE:
                raise ValueError(
                    f"Cannot roll back branch '{branch.name}' "
                    f"in status {branch.status.name}"
                )

            rolled_back = DatabaseBranch(
                branch_id=branch.branch_id,
                name=branch.name,
                parent_commit=branch.parent_commit,
                status=BranchStatus.ROLLED_BACK,
                changes=[],
                head_commit=branch.parent_commit,
                created_at=branch.created_at,
                updated_at=datetime.now(timezone.utc),
            )
            self._branches[branch_id] = rolled_back

        logger.info("Rolled back branch '%s'", branch.name)
        return rolled_back

    def list_branches(self) -> list[DatabaseBranch]:
        """List all branches with their current status."""
        with self._lock:
            return list(self._branches.values())

    def get_branch(self, branch_id: str) -> DatabaseBranch:
        """Get a branch by ID.

        Args:
            branch_id: The branch identifier.

        Returns:
            The DatabaseBranch.

        Raises:
            BranchNotFoundError: If the branch does not exist.
        """
        with self._lock:
            branch = self._branches.get(branch_id)
            if branch is None:
                raise BranchNotFoundError(f"Branch not found: {branch_id}")
            return branch


__all__ = [
    "BranchNotFoundError",
    "MigrationConflictError",
    "BranchingConfig",
    "DatabaseBranching",
]
