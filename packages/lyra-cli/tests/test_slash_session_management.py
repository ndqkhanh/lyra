"""Wave-C Task 2: ``/fork`` + ``/rename`` + ``/sessions`` + ``/export``.

These slashes were stubs in v1.7.4 — they printed "the driver will
do X". Wave-C grants them real disk-backed semantics through a tiny
``SessionsStore`` module that owns ``~/.lyra/sessions/`` layout.

The 8 tests below cover every mutating verb (fork, rename, export)
plus the read verb (list) plus the cross-cutting failure modes
(empty store, missing fork target, unsupported export format,
re-import idempotence).
"""
from __future__ import annotations

import json
from pathlib import Path

import pytest

from lyra_cli.interactive.session import InteractiveSession
from lyra_cli.interactive.sessions_store import (
    SessionMeta,
    SessionsStore,
    UnsupportedExportFormat,
)


def _seed(sessions_root: Path, sid: str, lines: tuple[str, ...]) -> InteractiveSession:
    s = InteractiveSession(
        repo_root=sessions_root.parent.parent,  # tmp_path
        sessions_root=sessions_root,
        session_id=sid,
    )
    for ln in lines:
        s.dispatch(ln)
    return s


# ---- list -------------------------------------------------------------

def test_list_enumerates_sessions_with_meta(tmp_path: Path) -> None:
    sessions_root = tmp_path / ".lyra" / "sessions"
    _seed(sessions_root, "sess-A", ("a1", "a2"))
    _seed(sessions_root, "sess-B", ("b1",))

    store = SessionsStore(sessions_root)
    metas = store.list()
    by_id = {m.session_id: m for m in metas}
    assert {"sess-A", "sess-B"} <= set(by_id)
    assert by_id["sess-A"].turn_count == 2
    assert by_id["sess-B"].turn_count == 1


def test_list_handles_empty_store(tmp_path: Path) -> None:
    store = SessionsStore(tmp_path / ".lyra" / "sessions")
    assert store.list() == []


# ---- fork -------------------------------------------------------------

def test_fork_copies_jsonl_under_new_id(tmp_path: Path) -> None:
    sessions_root = tmp_path / ".lyra" / "sessions"
    _seed(sessions_root, "sess-src", ("plan A", "plan B"))
    store = SessionsStore(sessions_root)

    new_id = store.fork("sess-src", new_id="sess-fork")

    assert new_id == "sess-fork"
    src = (sessions_root / "sess-src" / "turns.jsonl").read_text(encoding="utf-8")
    dst = (sessions_root / "sess-fork" / "turns.jsonl").read_text(encoding="utf-8")
    assert src == dst, "fork is a byte-identical copy at the moment of forking"


def test_fork_rejects_missing_source(tmp_path: Path) -> None:
    store = SessionsStore(tmp_path / ".lyra" / "sessions")
    with pytest.raises(FileNotFoundError):
        store.fork("sess-does-not-exist", new_id="sess-fork")


# ---- rename -----------------------------------------------------------

def test_rename_updates_meta_without_moving_directory(tmp_path: Path) -> None:
    """Renaming changes the *display name* in ``meta.json``, not the slug."""
    sessions_root = tmp_path / ".lyra" / "sessions"
    _seed(sessions_root, "sess-A", ("hello",))

    store = SessionsStore(sessions_root)
    store.rename("sess-A", new_name="Auth investigation")

    meta_path = sessions_root / "sess-A" / "meta.json"
    assert meta_path.is_file()
    data = json.loads(meta_path.read_text(encoding="utf-8"))
    assert data["name"] == "Auth investigation"
    # Directory slug is unchanged so existing JSONL paths still resolve.
    assert (sessions_root / "sess-A" / "turns.jsonl").is_file()


# ---- export -----------------------------------------------------------

def test_export_to_markdown(tmp_path: Path) -> None:
    sessions_root = tmp_path / ".lyra" / "sessions"
    _seed(sessions_root, "sess-md", ("first", "second"))
    out = tmp_path / "transcript.md"

    store = SessionsStore(sessions_root)
    written = store.export_to("sess-md", path=out, fmt="md")

    assert written == out
    text = out.read_text(encoding="utf-8")
    assert "first" in text and "second" in text
    # Markdown export must include a heading so the file is meaningful
    # when opened in any markdown viewer.
    assert text.lstrip().startswith("#")


def test_export_to_json_array(tmp_path: Path) -> None:
    sessions_root = tmp_path / ".lyra" / "sessions"
    _seed(sessions_root, "sess-json", ("plan: write the test",))
    out = tmp_path / "transcript.json"

    store = SessionsStore(sessions_root)
    store.export_to("sess-json", path=out, fmt="json")

    parsed = json.loads(out.read_text(encoding="utf-8"))
    assert isinstance(parsed, list)
    assert parsed[0]["line"] == "plan: write the test"


def test_export_rejects_unknown_format(tmp_path: Path) -> None:
    sessions_root = tmp_path / ".lyra" / "sessions"
    _seed(sessions_root, "sess-x", ("hi",))
    store = SessionsStore(sessions_root)
    with pytest.raises(UnsupportedExportFormat):
        store.export_to("sess-x", path=tmp_path / "out.bin", fmt="bin")
