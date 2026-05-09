"""Contract tests for the real ``TodoWrite`` tool + ``TodoStore`` (v1.7.3).

The v1.7.2 ``TodoWrite`` slot in the parity matrix was a stub. This
ships the real surface: a persistent JSON-backed store with atomic
rename-over writes, plus an LLM-callable ``make_todo_write_tool``
factory whose schema matches Claude-Code / opencode.

Invariants tested:

- Tool advertises a JSON schema with ``todos`` (array) + ``merge``
  (bool) properties, matching the shape used by Claude-Code + opencode.
- ``merge=True`` upserts by id and preserves un-referenced todos.
- ``merge=False`` (default) *replaces* the entire list.
- Writes are atomic: killing the process mid-write must not leave a
  half-written JSON file on disk (simulated by monkeypatching the
  rename step and asserting the final file is never observed in a
  malformed state).
- The on-disk payload roundtrips across store reopen.
- Unknown ids on a ``merge`` update get inserted (upsert semantics).
- The store file is created lazily in its parent directory.
"""
from __future__ import annotations

import json
from pathlib import Path

import pytest

from lyra_core.store.todo_store import TodoStore
from lyra_core.tools.todo_write import make_todo_write_tool


# ---- schema -------------------------------------------------------- #


def test_tool_exposes_todowrite_schema(tmp_path: Path) -> None:
    store = TodoStore(path=tmp_path / "todos.json")
    tool = make_todo_write_tool(store=store)

    schema = getattr(tool, "__tool_schema__", None)
    assert schema is not None
    assert schema["name"] == "TodoWrite"
    props = schema["parameters"]["properties"]
    assert "todos" in props
    assert "merge" in props
    assert props["todos"]["type"] == "array"
    assert props["merge"]["type"] == "boolean"


# ---- replace semantics --------------------------------------------- #


def test_replace_semantics_without_merge(tmp_path: Path) -> None:
    store = TodoStore(path=tmp_path / "todos.json")
    tool = make_todo_write_tool(store=store)

    tool(todos=[
        {"id": "t1", "content": "first", "status": "pending"},
        {"id": "t2", "content": "second", "status": "pending"},
    ])
    out = tool(todos=[{"id": "t3", "content": "third", "status": "in_progress"}])

    assert [t["id"] for t in out["todos"]] == ["t3"]
    assert out["todos"][0]["status"] == "in_progress"


# ---- merge semantics ---------------------------------------------- #


def test_merge_upserts_by_id_and_keeps_unreferenced(tmp_path: Path) -> None:
    store = TodoStore(path=tmp_path / "todos.json")
    tool = make_todo_write_tool(store=store)

    tool(todos=[
        {"id": "t1", "content": "first", "status": "pending"},
        {"id": "t2", "content": "second", "status": "pending"},
    ])
    out = tool(
        todos=[
            {"id": "t2", "status": "completed"},              # updates t2 in place
            {"id": "t3", "content": "fresh", "status": "pending"},  # inserts t3
        ],
        merge=True,
    )

    by_id = {t["id"]: t for t in out["todos"]}
    assert set(by_id) == {"t1", "t2", "t3"}
    assert by_id["t1"]["status"] == "pending"       # untouched
    assert by_id["t2"]["status"] == "completed"     # merge-updated
    assert by_id["t2"]["content"] == "second"       # preserved through partial update
    assert by_id["t3"]["content"] == "fresh"


# ---- persistence roundtrip ---------------------------------------- #


def test_roundtrip_across_store_reopen(tmp_path: Path) -> None:
    path = tmp_path / "todos.json"
    store_a = TodoStore(path=path)
    tool_a = make_todo_write_tool(store=store_a)
    tool_a(todos=[{"id": "persisted", "content": "survive reopen", "status": "pending"}])

    store_b = TodoStore(path=path)
    assert [t["id"] for t in store_b.load()] == ["persisted"]


# ---- atomic write ------------------------------------------------- #


def test_write_is_atomic_via_rename_over(
    tmp_path: Path, monkeypatch: pytest.MonkeyPatch
) -> None:
    """Kill the process between tmp write and rename — the live file
    must either be unchanged or fully updated, never partially written.
    """
    path = tmp_path / "todos.json"
    store = TodoStore(path=path)
    tool = make_todo_write_tool(store=store)

    tool(todos=[{"id": "t1", "content": "first", "status": "pending"}])

    original_bytes = path.read_bytes()

    real_replace = Path.replace

    def _kaboom(self, target):
        raise RuntimeError("simulated crash before rename")

    monkeypatch.setattr(Path, "replace", _kaboom)

    with pytest.raises(RuntimeError):
        tool(
            todos=[{"id": "t2", "content": "second", "status": "pending"}],
            merge=False,
        )

    monkeypatch.setattr(Path, "replace", real_replace)

    # Live file must be byte-identical to the pre-crash version.
    assert path.read_bytes() == original_bytes
    # And the partial .tmp file must be cleaned up (no stale temp).
    tmps = list(path.parent.glob(path.name + ".tmp*"))
    assert tmps == [], f"stale temp file(s) leaked: {tmps}"


# ---- lazy file creation ------------------------------------------- #


def test_store_creates_parent_dir_lazily(tmp_path: Path) -> None:
    nested = tmp_path / "does" / "not" / "exist" / "todos.json"
    store = TodoStore(path=nested)
    tool = make_todo_write_tool(store=store)

    tool(todos=[{"id": "t", "content": "nested write", "status": "pending"}])

    assert nested.exists()
    loaded = json.loads(nested.read_text())
    assert loaded[0]["id"] == "t"


# ---- validation --------------------------------------------------- #


def test_rejects_bad_status_value(tmp_path: Path) -> None:
    tool = make_todo_write_tool(store=TodoStore(path=tmp_path / "todos.json"))
    with pytest.raises(ValueError):
        tool(todos=[{"id": "t", "content": "x", "status": "bogus"}])


def test_rejects_todos_without_id(tmp_path: Path) -> None:
    tool = make_todo_write_tool(store=TodoStore(path=tmp_path / "todos.json"))
    with pytest.raises(ValueError):
        tool(todos=[{"content": "missing id", "status": "pending"}])
