"""Auto-memory tests (v3.7 L37-6)."""
from __future__ import annotations

import pytest
from pathlib import Path

from lyra_core.memory.auto_memory import (
    AutoMemory,
    MemoryEntry,
    MemoryKind,
    project_slug,
)


def test_project_slug_normalises() -> None:
    assert project_slug("My Project") == "my-project"
    assert project_slug("/abs/path/proj") == "abs-path-proj"
    assert project_slug("") == "default"


def test_save_then_round_trip(tmp_path: Path) -> None:
    am = AutoMemory(root=tmp_path, project="proj-a")
    am.save(kind=MemoryKind.PROJECT, title="build", body="make ci runs full suite")
    fresh = AutoMemory(root=tmp_path, project="proj-a")
    assert len(fresh) == 1
    entries = fresh.by_kind(MemoryKind.PROJECT)
    assert entries[0].title == "build"


def test_save_persists_md_digest(tmp_path: Path) -> None:
    am = AutoMemory(root=tmp_path, project="proj-a")
    am.save(kind=MemoryKind.USER, title="role",
            body="user is a senior backend engineer")
    md = am.md_path.read_text(encoding="utf-8")
    assert "## role" in md
    assert "senior backend engineer" in md


def test_save_appends_jsonl(tmp_path: Path) -> None:
    am = AutoMemory(root=tmp_path, project="proj-a")
    am.save(kind=MemoryKind.PROJECT, title="t1", body="b1")
    am.save(kind=MemoryKind.PROJECT, title="t2", body="b2")
    lines = am.jsonl_path.read_text(encoding="utf-8").strip().splitlines()
    assert len(lines) == 2


def test_forget_tombstones_keeps_audit(tmp_path: Path) -> None:
    am = AutoMemory(root=tmp_path, project="proj-a")
    e = am.save(kind=MemoryKind.PROJECT, title="x", body="y")
    am.forget(e.entry_id)
    # by_kind excludes tombstones.
    assert am.by_kind(MemoryKind.PROJECT) == ()
    # all(include_deleted=True) keeps the audit row.
    all_entries = am.all(include_deleted=True)
    assert any(x.deleted for x in all_entries)
    # The MD file is rewritten without the forgotten entry.
    assert "## x" not in am.md_path.read_text(encoding="utf-8")


def test_forget_unknown_id_raises(tmp_path: Path) -> None:
    am = AutoMemory(root=tmp_path, project="proj-a")
    with pytest.raises(KeyError):
        am.forget("missing")


def test_retrieve_token_overlap_picks_relevant(tmp_path: Path) -> None:
    am = AutoMemory(root=tmp_path, project="proj-a")
    am.save(kind=MemoryKind.PROJECT, title="build command",
            body="make ci runs lint typecheck and pytest tests")
    am.save(kind=MemoryKind.PROJECT, title="vacation policy",
            body="annual leave is unlimited")
    out = am.retrieve("how do I run the build tests?", top_n=2)
    assert out
    assert "build" in out[0].title


def test_retrieve_empty_query_returns_nothing(tmp_path: Path) -> None:
    am = AutoMemory(root=tmp_path, project="proj-a")
    am.save(kind=MemoryKind.PROJECT, title="x", body="y")
    assert am.retrieve("", top_n=5) == ()


def test_session_start_digest_lists_recent(tmp_path: Path) -> None:
    am = AutoMemory(root=tmp_path, project="proj-a")
    am.save(kind=MemoryKind.USER, title="role", body="senior engineer")
    am.save(kind=MemoryKind.PROJECT, title="build", body="make ci")
    digest = am.session_start_digest()
    assert "Auto-memory for proj-a" in digest
    assert "role" in digest
    assert "build" in digest


def test_session_start_digest_empty_when_no_entries(tmp_path: Path) -> None:
    am = AutoMemory(root=tmp_path, project="proj-a")
    assert am.session_start_digest() == ""


def test_two_projects_isolated_under_same_root(tmp_path: Path) -> None:
    a = AutoMemory(root=tmp_path, project="proj-a")
    b = AutoMemory(root=tmp_path, project="proj-b")
    a.save(kind=MemoryKind.PROJECT, title="A-only", body="...")
    b.save(kind=MemoryKind.PROJECT, title="B-only", body="...")
    assert {e.title for e in a.all()} == {"A-only"}
    assert {e.title for e in b.all()} == {"B-only"}


def test_append_only_invariant_persists_old_entries(tmp_path: Path) -> None:
    """Past entries never mutate even when forgotten. The JSONL keeps both rows."""
    am = AutoMemory(root=tmp_path, project="proj-a")
    e = am.save(kind=MemoryKind.PROJECT, title="x", body="original body")
    am.forget(e.entry_id)
    lines = am.jsonl_path.read_text(encoding="utf-8").strip().splitlines()
    # Two rows: original + tombstone.
    assert len(lines) == 2
    import json as _json
    rows = [_json.loads(line) for line in lines]
    # Original survives unmodified.
    assert rows[0]["body"] == "original body"
    assert not rows[0]["deleted"]
    # Tombstone preserves identity but flags deleted.
    assert rows[1]["entry_id"] == rows[0]["entry_id"]
    assert rows[1]["deleted"]
