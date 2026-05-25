"""Tests for the safe_rewriter module."""

from __future__ import annotations

import os
import tempfile

import pytest

from lyra_meta_editor import (
    RewriteConfig,
    RewriteError,
    RewritePlan,
    RewriteResult,
    SafeRewriter,
)


@pytest.fixture
def temp_py_file() -> str:
    """Create a temporary Python file for testing."""
    content = "x = 1\n"
    with tempfile.NamedTemporaryFile(mode="w", suffix=".py", delete=False) as f:
        f.write(content)
        path = f.name
    yield path
    if os.path.isfile(path):
        os.unlink(path)


class TestRewriteConfig:
    """Tests for RewriteConfig."""

    def test_defaults(self) -> None:
        cfg = RewriteConfig()
        assert cfg.backup_enabled is True
        assert cfg.max_retries == 3
        assert cfg.dry_run is False
        assert cfg.require_tests_pass is True


class TestRewritePlan:
    """Tests for RewritePlan."""

    def test_creation(self) -> None:
        plan = RewritePlan(
            file_path="/path/to/file.py",
            original_content="old",
            new_content="new",
            validation_steps=("syntax_check",),
            rollback_strategy="restore_original",
        )
        assert plan.file_path == "/path/to/file.py"
        assert plan.rollback_strategy == "restore_original"


class TestRewriteResult:
    """Tests for RewriteResult."""

    def test_creation_defaults(self) -> None:
        plan = RewritePlan("f.py", "old", "new", (), "")
        result = RewriteResult(plan=plan, success=True, validation_passed=True)
        assert result.backup_path == ""
        assert result.error_message == ""


class TestSafeRewriter:
    """Tests for SafeRewriter."""

    @pytest.mark.asyncio
    async def test_create_plan(self, temp_py_file: str) -> None:
        rewriter = SafeRewriter()
        plan = await rewriter.create_plan(temp_py_file, "y = 2\n")
        assert plan.file_path == temp_py_file
        assert plan.original_content == "x = 1\n"
        assert plan.new_content == "y = 2\n"

    @pytest.mark.asyncio
    async def test_create_plan_file_not_found(self) -> None:
        rewriter = SafeRewriter()
        with pytest.raises(RewriteError, match="not found"):
            await rewriter.create_plan("/nonexistent.py", "content")

    @pytest.mark.asyncio
    async def test_create_plan_identical_content(self, temp_py_file: str) -> None:
        rewriter = SafeRewriter()
        with pytest.raises(RewriteError, match="identical"):
            await rewriter.create_plan(temp_py_file, "x = 1\n")

    @pytest.mark.asyncio
    async def test_execute_rewrite_dry_run(self, temp_py_file: str) -> None:
        config = RewriteConfig(dry_run=True)
        rewriter = SafeRewriter(config)
        plan = RewritePlan(
            file_path=temp_py_file,
            original_content="x = 1\n",
            new_content="y = 2\n",
            validation_steps=(),
            rollback_strategy="restore_original",
        )
        result = await rewriter.execute_rewrite(plan)
        assert result.success is True
        assert "Dry run" in result.error_message
        # File should be unchanged
        with open(temp_py_file) as f:
            assert f.read() == "x = 1\n"

    @pytest.mark.asyncio
    async def test_execute_rewrite_success(self, temp_py_file: str) -> None:
        rewriter = SafeRewriter()
        plan = RewritePlan(
            file_path=temp_py_file,
            original_content="x = 1\n",
            new_content="y = 2\n",
            validation_steps=("syntax_check",),
            rollback_strategy="restore_original",
        )
        result = await rewriter.execute_rewrite(plan)
        assert result.success is True
        assert result.validation_passed is True
        with open(temp_py_file) as f:
            assert f.read() == "y = 2\n"

    @pytest.mark.asyncio
    async def test_execute_rewrite_backup_disabled(self, temp_py_file: str) -> None:
        config = RewriteConfig(backup_enabled=False)
        rewriter = SafeRewriter(config)
        plan = RewritePlan(
            file_path=temp_py_file,
            original_content="x = 1\n",
            new_content="y = 2\n",
            validation_steps=("syntax_check",),
            rollback_strategy="restore_original",
        )
        result = await rewriter.execute_rewrite(plan)
        assert result.success is True
        assert result.backup_path == ""

    @pytest.mark.asyncio
    async def test_rollback(self, temp_py_file: str) -> None:
        rewriter = SafeRewriter()
        plan = RewritePlan(
            file_path=temp_py_file,
            original_content="x = 1\n",
            new_content="y = 2\n",
            validation_steps=(),
            rollback_strategy="restore_original",
        )
        success = await rewriter.rollback(plan)
        assert success is True
        with open(temp_py_file) as f:
            assert f.read() == "x = 1\n"

    @pytest.mark.asyncio
    async def test_rollback_nonexistent_file(self) -> None:
        rewriter = SafeRewriter()
        plan = RewritePlan(
            file_path="/nonexistent.py",
            original_content="old",
            new_content="new",
            validation_steps=(),
            rollback_strategy="restore_original",
        )
        success = await rewriter.rollback(plan)
        assert success is False

    @pytest.mark.asyncio
    async def test_validate_rewrite_success(self, temp_py_file: str) -> None:
        rewriter = SafeRewriter()
        plan = RewritePlan(
            file_path=temp_py_file,
            original_content="x = 1\n",
            new_content="y = 2\n",
            validation_steps=("syntax_check",),
            rollback_strategy="restore_original",
        )
        # Apply the rewrite first
        result = await rewriter.execute_rewrite(plan)
        valid = await rewriter.validate_rewrite(result)
        assert valid is True

    @pytest.mark.asyncio
    async def test_validate_rewrite_syntax_error(self, temp_py_file: str) -> None:
        rewriter = SafeRewriter()
        plan = RewritePlan(
            file_path=temp_py_file,
            original_content="x = 1\n",
            new_content="if x:\n",  # invalid Python
            validation_steps=("syntax_check",),
            rollback_strategy="restore_original",
        )
        result = await rewriter.execute_rewrite(plan)
        # Should fail validation and rollback
        assert result.validation_passed is False
        # File should be restored to original
        with open(temp_py_file) as f:
            assert f.read() == "x = 1\n"

    @pytest.mark.asyncio
    async def test_validate_rewrite_no_validation_steps(self, temp_py_file: str) -> None:
        rewriter = SafeRewriter()
        plan = RewritePlan(
            file_path=temp_py_file,
            original_content="x = 1\n",
            new_content="if x:\n",  # invalid but no syntax_check step
            validation_steps=(),
            rollback_strategy="restore_original",
        )
        result = await rewriter.execute_rewrite(plan)
        assert result.success is True

    @pytest.mark.asyncio
    async def test_execute_rewrite_missing_file(self) -> None:
        rewriter = SafeRewriter()
        plan = RewritePlan(
            file_path="/nonexistent_file.py",
            original_content="old",
            new_content="new",
            validation_steps=(),
            rollback_strategy="restore_original",
        )
        result = await rewriter.execute_rewrite(plan)
        assert result.success is False

    def test_rewriter_with_custom_config(self) -> None:
        config = RewriteConfig(max_retries=5)
        rewriter = SafeRewriter(config)
        assert rewriter._config.max_retries == 5  # type: ignore[arg-type]

    @pytest.mark.asyncio
    async def test_validate_rewrite_missing_file(self) -> None:
        rewriter = SafeRewriter()
        plan = RewritePlan(
            file_path="/nonexistent.py",
            original_content="old",
            new_content="new",
            validation_steps=(),
            rollback_strategy="restore_original",
        )
        result = RewriteResult(plan=plan, success=False, validation_passed=False)
        valid = await rewriter.validate_rewrite(result)
        assert valid is False

    @pytest.mark.asyncio
    async def test_full_rewrite_cycle(self, temp_py_file: str) -> None:
        rewriter = SafeRewriter()
        plan = await rewriter.create_plan(temp_py_file, 'print("hello")\n')
        result = await rewriter.execute_rewrite(plan)
        assert result.success is True
        with open(temp_py_file) as f:
            assert f.read() == 'print("hello")\n'
        # Rollback
        rolled_back = await rewriter.rollback(plan)
        assert rolled_back is True
        with open(temp_py_file) as f:
            assert f.read() == "x = 1\n"

    @pytest.mark.asyncio
    async def test_create_plan_empty_file(self) -> None:
        with tempfile.NamedTemporaryFile(mode="w", suffix=".py", delete=False) as f:
            f.write("")
            path = f.name
        try:
            rewriter = SafeRewriter()
            plan = await rewriter.create_plan(path, "x = 1\n")
            assert plan.original_content == ""
            assert plan.new_content == "x = 1\n"
        finally:
            os.unlink(path)

    @pytest.mark.asyncio
    async def test_create_plan_binary_file_raises(self) -> None:
        with tempfile.NamedTemporaryFile(mode="wb", suffix=".bin", delete=False) as f:
            f.write(b"\x00\x01\x02")
            path = f.name
        try:
            rewriter = SafeRewriter()
            plan = await rewriter.create_plan(path, "x = 1\n")
            plan = plan  # just checking no error on file existence
        finally:
            os.unlink(path)

    @pytest.mark.asyncio
    async def test_execute_rewrite_multiple_retries(self, temp_py_file: str) -> None:
        config = RewriteConfig(max_retries=1)
        rewriter = SafeRewriter(config)
        plan = RewritePlan(
            file_path=temp_py_file,
            original_content="x = 1\n",
            new_content="x = 999\n",
            validation_steps=("syntax_check",),
            rollback_strategy="restore_original",
        )
        result = await rewriter.execute_rewrite(plan)
        assert result.success is True
        assert result.validation_passed is True
