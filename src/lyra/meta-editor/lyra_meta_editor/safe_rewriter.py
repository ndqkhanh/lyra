"""Safe code rewrite with validation and rollback."""

from __future__ import annotations

import os
import shutil
import tempfile
import time
from dataclasses import dataclass
from typing import ClassVar

from .exceptions import RewriteError


@dataclass(frozen=True)
class RewriteConfig:
    """Configuration governing safe rewrite behaviour."""

    backup_enabled: bool = True
    max_retries: int = 3
    dry_run: bool = False
    require_tests_pass: bool = True


@dataclass(frozen=True)
class RewritePlan:
    """A planned rewrite operation with validation steps."""

    file_path: str
    original_content: str
    new_content: str
    validation_steps: tuple[str, ...]
    rollback_strategy: str


@dataclass(frozen=True)
class RewriteResult:
    """Result of executing a RewritePlan."""

    plan: RewritePlan
    success: bool
    validation_passed: bool
    backup_path: str = ""
    error_message: str = ""


class SafeRewriter:
    """Safe code rewrite with validation and rollback."""

    BACKUP_DIR: ClassVar[str] = tempfile.gettempdir()

    def __init__(self, config: RewriteConfig = RewriteConfig()) -> None:
        self._config = config

    async def create_plan(self, file_path: str, new_content: str) -> RewritePlan:
        """Create a rewrite plan for the given file."""
        if not os.path.isfile(file_path):
            raise RewriteError(f"File not found: {file_path}")
        try:
            with open(file_path) as f:
                original = f.read()
        except OSError as e:
            raise RewriteError(f"Cannot read {file_path}: {e}") from e
        if original == new_content:
            raise RewriteError("New content is identical to original")
        return RewritePlan(
            file_path=file_path,
            original_content=original,
            new_content=new_content,
            validation_steps=("syntax_check", "content_changed"),
            rollback_strategy="restore_original",
        )

    async def execute_rewrite(self, plan: RewritePlan) -> RewriteResult:
        """Execute a rewrite plan with backup and retry logic."""
        if self._config.dry_run:
            return RewriteResult(
                plan=plan,
                success=True,
                validation_passed=True,
                error_message="Dry run -- no changes written",
            )

        backup_path = ""
        if self._config.backup_enabled:
            backup_path = os.path.join(
                SafeRewriter.BACKUP_DIR,
                f".lyra_backup_{int(time.time())}_{os.path.basename(plan.file_path)}",
            )
            try:
                with open(backup_path, "w") as f:
                    f.write(plan.original_content)
            except OSError as e:
                return RewriteResult(
                    plan=plan,
                    success=False,
                    validation_passed=False,
                    error_message=f"Backup failed: {e}",
                )

        for attempt in range(self._config.max_retries):
            try:
                with open(plan.file_path, "w") as f:
                    f.write(plan.new_content)
                break
            except OSError as e:
                if attempt == self._config.max_retries - 1:
                    self._restore_backup(backup_path, plan.file_path)
                    return RewriteResult(
                        plan=plan,
                        success=False,
                        validation_passed=False,
                        backup_path=backup_path,
                        error_message=(
                            f"Write failed after {self._config.max_retries} "
                            f"attempts: {e}"
                        ),
                    )

        validation_passed = await self.validate_rewrite(
            RewriteResult(
                plan=plan,
                success=True,
                validation_passed=True,
                backup_path=backup_path,
            )
        )

        if not validation_passed and backup_path:
            self._restore_backup(backup_path, plan.file_path)

        return RewriteResult(
            plan=plan,
            success=validation_passed,
            validation_passed=validation_passed,
            backup_path=backup_path,
            error_message=(
                "" if validation_passed
                else "Validation failed -- rewrite rolled back"
            ),
        )

    async def rollback(self, plan: RewritePlan) -> bool:
        """Restore original content for a given plan."""
        try:
            with open(plan.file_path, "w") as f:
                f.write(plan.original_content)
            return True
        except OSError:
            return False

    async def validate_rewrite(self, result: RewriteResult) -> bool:
        """Validate that a rewrite was applied correctly."""
        if not os.path.isfile(result.plan.file_path):
            return False
        try:
            with open(result.plan.file_path) as f:
                content = f.read()
        except OSError:
            return False
        if content == result.plan.original_content:
            return False
        if "syntax_check" in result.plan.validation_steps:
            try:
                compile(content, result.plan.file_path, "exec")
            except SyntaxError:
                return False
        return True

    @staticmethod
    def _restore_backup(backup_path: str, file_path: str) -> None:
        if backup_path and os.path.isfile(backup_path):
            try:
                shutil.copy2(backup_path, file_path)
            except OSError:
                pass
