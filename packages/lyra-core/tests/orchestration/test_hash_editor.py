"""Tests for the Phase 2.4a Hash-Anchored Editor."""
from __future__ import annotations

import pytest
from lyra_core.orchestration.hash_editor import (
    ContentAnchor,
    EditResult,
    EditStatus,
    HashAnchoredEdit,
    HashAnchoredEditor,
)

ORIGINAL_CODE = "def old_function():\n    return 'old'"


class TestHashAnchoredEditor:
    def test_anchor_returns_content_anchor(self):
        editor = HashAnchoredEditor()
        anchor = editor.anchor("src/app.py", ORIGINAL_CODE, 10, 12)
        assert anchor.anchor_id.startswith("ca-")
        assert anchor.file_path == "src/app.py"

    def test_anchor_stored_in_registry(self):
        editor = HashAnchoredEditor()
        anchor = editor.anchor("src/app.py", ORIGINAL_CODE, 10, 12)
        assert anchor.anchor_id in editor._registry
        assert editor.anchor_count == 1

    def test_apply_with_matching_content(self):
        editor = HashAnchoredEditor()
        anchor = editor.anchor("src/app.py", ORIGINAL_CODE, 10, 12)
        result = editor.apply(
            anchor,
            "def new_function():\n    return 'new'",
            description="Replace old function",
            current_content=ORIGINAL_CODE,
        )
        assert result.success
        assert "def new_function" in result.result_content

    def test_apply_with_hash_mismatch(self):
        editor = HashAnchoredEditor()
        anchor = editor.anchor("src/app.py", ORIGINAL_CODE, 10, 12)
        result = editor.apply(
            anchor,
            "replacement",
            current_content="different content entirely",
        )
        assert not result.success
        assert result.conflict_reason is not None
        assert "hash mismatch" in result.conflict_reason.lower()

    def test_apply_without_verification_succeeds(self):
        editor = HashAnchoredEditor()
        anchor = editor.anchor("src/app.py", ORIGINAL_CODE, 10, 12)
        result = editor.apply(anchor, "replacement")
        assert result.success

    def test_apply_creates_rollback_anchor(self):
        editor = HashAnchoredEditor()
        anchor = editor.anchor("src/app.py", ORIGINAL_CODE, 10, 12)
        result = editor.apply(
            anchor,
            "new content",
            current_content=ORIGINAL_CODE,
        )
        assert result.edit.rollback_anchor is not None

    def test_rollback_returns_anchor(self):
        editor = HashAnchoredEditor()
        anchor = editor.anchor("src/app.py", ORIGINAL_CODE, 10, 12)
        result = editor.apply(
            anchor,
            "new content",
            current_content=ORIGINAL_CODE,
        )
        rollback = editor.rollback(result.edit.edit_id)
        assert rollback is not None
        assert rollback.content_hash == anchor.content_hash

    def test_verify_edit_matches_hash(self):
        editor = HashAnchoredEditor()
        anchor = editor.anchor("src/app.py", ORIGINAL_CODE, 10, 12)
        result = editor.apply(
            anchor,
            "def verified():\n    pass",
            current_content=ORIGINAL_CODE,
        )
        status = editor.verify_edit(result.edit.edit_id, "def verified():\n    pass")
        assert status == EditStatus.VERIFIED

    def test_verify_edit_rejects_mismatch(self):
        editor = HashAnchoredEditor()
        anchor = editor.anchor("src/app.py", ORIGINAL_CODE, 10, 12)
        result = editor.apply(
            anchor,
            "def expected():\n    pass",
            current_content=ORIGINAL_CODE,
        )
        status = editor.verify_edit(result.edit.edit_id, "different content")
        assert status == EditStatus.REJECTED

    def test_verify_nonexistent_edit_returns_pending(self):
        editor = HashAnchoredEditor()
        assert editor.verify_edit("nonexistent", "content") == EditStatus.PENDING

    def test_edit_history_accumulates(self):
        editor = HashAnchoredEditor()
        anchor = editor.anchor("src/a.py", "content a", 1, 1)
        editor.apply(anchor, "new a")
        editor.apply(anchor, "newer a")
        assert editor.edit_count == 2

    def test_first_try_rate_no_conflicts(self):
        editor = HashAnchoredEditor()
        for i in range(5):
            content = f"line {i}"
            anchor = editor.anchor("src/app.py", content, i, i)
            editor.apply(anchor, f"new {i}", current_content=content)
        assert editor.get_first_try_rate() == 1.0

    def test_first_try_rate_with_conflicts(self):
        editor = HashAnchoredEditor()
        anchor = editor.anchor("src/app.py", "expected", 1, 1)
        editor.apply(anchor, "replacement", current_content="expected")
        editor.apply(anchor, "replacement", current_content="wrong content")
        assert editor.get_first_try_rate() == 0.5

    def test_conflict_rate_zero_initially(self):
        editor = HashAnchoredEditor()
        assert editor.get_conflict_rate() == 0.0

    def test_conflict_rate_with_conflicts(self):
        editor = HashAnchoredEditor()
        anchor = editor.anchor("src/app.py", "expected", 1, 1)
        editor.apply(anchor, "replacement", current_content="expected")
        editor.apply(anchor, "replacement", current_content="wrong")
        assert editor.get_conflict_rate() == 0.5

    def test_clear_history(self):
        editor = HashAnchoredEditor()
        anchor = editor.anchor("src/a.py", "content", 1, 1)
        editor.apply(anchor, "new")
        editor.clear_history()
        assert editor.edit_count == 0

    def test_default_end_line_equals_start_line(self):
        editor = HashAnchoredEditor()
        anchor = editor.anchor("src/app.py", "content", 42)
        assert anchor.end_line == 42


class TestContentAnchor:
    def test_frozen_dataclass(self):
        anchor = ContentAnchor(
            anchor_id="ca-001",
            file_path="test.py",
            start_line=1,
            end_line=10,
            content_hash="abc123",
            content_preview="test content",
            created_at=1000.0,
        )
        with pytest.raises(Exception):
            anchor.file_path = "other.py"  # type: ignore[misc]


class TestEditResult:
    def test_success_result_properties(self):
        result = EditResult(
            result_id="er-001",
            edit=HashAnchoredEdit(
                edit_id="he-001",
                anchor=ContentAnchor(
                    anchor_id="ca-001",
                    file_path="test.py",
                    start_line=1,
                    end_line=1,
                    content_hash="abc",
                    content_preview="test",
                    created_at=1000.0,
                ),
                replacement_text="new",
                description="test edit",
                status=EditStatus.APPLIED,
                applied_at=1000.0,
                verified_hash="def456",
                rollback_anchor=None,
            ),
            success=True,
            conflict_reason=None,
            result_content="new",
            result_hash="def456",
            first_try=True,
        )
        assert result.success
        assert result.first_try
        assert result.conflict_reason is None
