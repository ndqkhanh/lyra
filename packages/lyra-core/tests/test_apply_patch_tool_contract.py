"""Contract tests for ``apply_patch`` (Anthropic v4 envelope parity).

The tool must:

1. Parse the ``*** Begin Patch`` / ``*** End Patch`` envelope and the
   ``*** Add / Delete / Update File:`` verbs.
2. Apply the ops to files under ``repo_root`` without escaping the root.
3. Return a structured dict with parsed ops and lists of touched files.
4. Reject malformed envelopes with a clear error dict (no exceptions
   propagate to the AgentLoop — it records the result verbatim).
"""
from __future__ import annotations

from pathlib import Path

import pytest

from lyra_core.tools.apply_patch import (
    ApplyPatchError,
    make_apply_patch_tool,
    parse_patch,
)


def test_parse_add_file_op() -> None:
    patch = (
        "*** Begin Patch\n"
        "*** Add File: hello.py\n"
        "+print('hi')\n"
        "*** End Patch\n"
    )
    ops = parse_patch(patch)
    assert len(ops) == 1
    assert ops[0].action == "add"
    assert ops[0].path == "hello.py"
    assert ops[0].new_text.strip() == "print('hi')"


def test_parse_update_file_op_with_old_and_new_blocks() -> None:
    patch = (
        "*** Begin Patch\n"
        "*** Update File: src/foo.py\n"
        "- old = 1\n"
        "+ new = 1\n"
        "*** End Patch\n"
    )
    ops = parse_patch(patch)
    assert len(ops) == 1
    assert ops[0].action == "update"
    assert "old = 1" in ops[0].old_text
    assert "new = 1" in ops[0].new_text


def test_missing_envelope_raises() -> None:
    with pytest.raises(ApplyPatchError):
        parse_patch("+ hello\n")


def test_add_then_update_then_delete_applies_all(tmp_path: Path) -> None:
    (tmp_path / "old.py").write_text("a = 1\n", encoding="utf-8")
    (tmp_path / "doomed.py").write_text("# bye\n", encoding="utf-8")

    tool = make_apply_patch_tool(repo_root=tmp_path)
    patch = (
        "*** Begin Patch\n"
        "*** Add File: new.py\n"
        "+print('hi')\n"
        "*** Update File: old.py\n"
        "- a = 1\n"
        "+ a = 2\n"
        "*** Delete File: doomed.py\n"
        "*** End Patch\n"
    )

    result = tool(patch=patch)
    assert result["ok"], result
    assert "new.py" in result["files_written"]
    assert "old.py" in result["files_written"]
    assert "doomed.py" in result["files_deleted"]

    assert (tmp_path / "new.py").read_text(encoding="utf-8").strip() == "print('hi')"
    assert (tmp_path / "old.py").read_text(encoding="utf-8").strip() == "a = 2"
    assert not (tmp_path / "doomed.py").exists()


def test_path_escape_is_rejected(tmp_path: Path) -> None:
    """Refuse any path that would escape repo_root."""
    tool = make_apply_patch_tool(repo_root=tmp_path)
    patch = (
        "*** Begin Patch\n"
        "*** Add File: ../escaped.txt\n"
        "+pwned\n"
        "*** End Patch\n"
    )
    result = tool(patch=patch)
    assert result["ok"] is False
    assert "outside repo_root" in result["error"].lower() or "refusing" in result["error"].lower()


def test_update_missing_old_block_returns_error_dict(tmp_path: Path) -> None:
    (tmp_path / "file.py").write_text("something else\n", encoding="utf-8")
    tool = make_apply_patch_tool(repo_root=tmp_path)
    patch = (
        "*** Begin Patch\n"
        "*** Update File: file.py\n"
        "- never here\n"
        "+ replacement\n"
        "*** End Patch\n"
    )
    result = tool(patch=patch)
    assert result["ok"] is False
    assert "old block" in result["error"].lower()


def test_tool_schema_is_present() -> None:
    tool = make_apply_patch_tool(repo_root=Path.cwd())
    schema = getattr(tool, "__tool_schema__", None)
    assert schema is not None
    assert schema["name"] == "apply_patch"
    assert "patch" in schema["parameters"]["required"]
