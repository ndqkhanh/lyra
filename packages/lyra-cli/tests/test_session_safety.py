"""Post-review safety hardening for v1.7.5 (Wave-C follow-up).

The Wave-C reviewer flagged three SHOULD-FIX classes:

1. **Path traversal** — ``SessionsStore.fork`` / ``rename`` /
   ``export_to`` and ``InteractiveSession._session_dir`` /
   ``resume_session`` accepted any string as a session id. A forged
   id like ``../../../../etc`` could escape the sessions root.
2. **Non-atomic persistence** — ``meta.json`` and the truncated
   ``turns.jsonl`` were written via direct ``write_text``; a crash
   mid-write left a half-truncated file.
3. **Config-store DoS** — ``Config.load`` ran ``yaml.safe_load`` on
   the whole file with no size cap, so a runaway ``~/.lyra/config.yaml``
   could starve memory at REPL boot.

These tests pin the new contracts so future refactors can't quietly
regress the security/integrity surface.
"""
from __future__ import annotations

import os
from pathlib import Path

import pytest

from lyra_cli.interactive.config_store import (
    MAX_CONFIG_BYTES,
    Config,
)
from lyra_cli.interactive.session import InteractiveSession
from lyra_cli.interactive.sessions_store import (
    InvalidSessionId,
    SessionsStore,
    _atomic_write_text,
    _validate_session_id,
)


# --- Path-traversal rejection ----------------------------------------


@pytest.mark.parametrize(
    "bad_id",
    [
        "..",
        ".",
        "../etc",
        "..\\windows",
        "foo/bar",
        "foo\\bar",
        "with:colon",
        "",
        "spaces are nope",
        "tab\there",
        "newline\nhere",
        "null\x00byte",
    ],
)
def test_validate_session_id_rejects_unsafe(bad_id: str) -> None:
    with pytest.raises(InvalidSessionId):
        _validate_session_id(bad_id)


@pytest.mark.parametrize(
    "good_id",
    [
        "sess-20260424123059-1234",
        "alpha",
        "ALPHA-123",
        "with.dots.and-dashes_42",
        "x",
    ],
)
def test_validate_session_id_accepts_safe(good_id: str) -> None:
    assert _validate_session_id(good_id) == good_id


def test_sessions_store_fork_refuses_traversal(tmp_path: Path) -> None:
    root = tmp_path / "sessions"
    src = root / "alpha"
    src.mkdir(parents=True)
    (src / "turns.jsonl").write_text('{"line":"hi","mode":"plan","turn":0}\n', "utf-8")
    store = SessionsStore(root)

    with pytest.raises(InvalidSessionId):
        store.fork("alpha", new_id="../escape")
    with pytest.raises(InvalidSessionId):
        store.fork("../alpha", new_id="beta")
    # No file should have been created outside the root.
    assert not (root.parent / "escape").exists()


def test_sessions_store_rename_refuses_traversal(tmp_path: Path) -> None:
    root = tmp_path / "sessions"
    (root / "alpha").mkdir(parents=True)
    store = SessionsStore(root)

    with pytest.raises(InvalidSessionId):
        store.rename("../alpha", new_name="x")


def test_sessions_store_export_refuses_traversal(tmp_path: Path) -> None:
    root = tmp_path / "sessions"
    (root / "alpha").mkdir(parents=True)
    (root / "alpha" / "turns.jsonl").write_text("", "utf-8")
    store = SessionsStore(root)

    with pytest.raises(InvalidSessionId):
        store.export_to("../alpha", path=tmp_path / "out.md", fmt="md")


def test_resume_session_refuses_traversal(tmp_path: Path) -> None:
    root = tmp_path / "sessions"
    root.mkdir()
    # Even if the path "exists" via traversal, validation must short-circuit.
    sneaky = "../sneaky"
    out = InteractiveSession.resume_session(
        session_id=sneaky,
        sessions_root=root,
        repo_root=tmp_path,
    )
    assert out is None


def test_session_dir_returns_none_for_invalid_id(tmp_path: Path) -> None:
    s = InteractiveSession(
        repo_root=tmp_path,
        sessions_root=tmp_path / "sessions",
        session_id="../escape",
    )
    # Persistence quietly disables itself when the id is unsafe so the
    # REPL keeps running rather than crashing on every dispatch.
    assert s._session_dir() is None


# --- Atomic writes ---------------------------------------------------


def test_atomic_write_text_replaces_existing_file(tmp_path: Path) -> None:
    target = tmp_path / "nested" / "out.txt"
    _atomic_write_text(target, "first")
    assert target.read_text("utf-8") == "first"
    _atomic_write_text(target, "second")
    assert target.read_text("utf-8") == "second"


def test_atomic_write_text_leaves_no_tempfiles(tmp_path: Path) -> None:
    target = tmp_path / "a.txt"
    _atomic_write_text(target, "payload")
    siblings = sorted(p.name for p in tmp_path.iterdir())
    # The temp prefix is always ``<target>.``; assert nothing leaked.
    leaked = [n for n in siblings if n != "a.txt" and n.startswith("a.txt.")]
    assert leaked == []


def test_sessions_store_meta_write_is_atomic(tmp_path: Path) -> None:
    root = tmp_path / "sessions"
    src = root / "alpha"
    src.mkdir(parents=True)
    (src / "turns.jsonl").write_text("{}\n", "utf-8")
    store = SessionsStore(root)
    store.fork("alpha", new_id="beta")
    store.rename("beta", new_name="renamed")
    # Confirm meta.json round-trips cleanly (no partial writes leaked).
    import json as _json

    meta = _json.loads((root / "beta" / "meta.json").read_text("utf-8"))
    assert meta["name"] == "renamed"
    assert meta["forked_from"] == "alpha"


# --- Config-store size cap ------------------------------------------


def test_config_load_refuses_oversized_file(tmp_path: Path) -> None:
    cfg_path = tmp_path / "config.yaml"
    huge = "x" * (MAX_CONFIG_BYTES + 1)
    cfg_path.write_text(f"theme: {huge}\n", encoding="utf-8")
    cfg = Config.load(cfg_path)
    # Must NOT block boot; must NOT load the runaway value.
    assert cfg.get("theme") is None


def test_config_load_accepts_normal_file(tmp_path: Path) -> None:
    cfg_path = tmp_path / "config.yaml"
    cfg_path.write_text("theme: aurora\nvim: on\n", encoding="utf-8")
    cfg = Config.load(cfg_path)
    assert cfg.get("theme") == "aurora"
    assert cfg.get("vim") == "on"


def test_config_save_is_atomic(tmp_path: Path) -> None:
    cfg_path = tmp_path / "config.yaml"
    cfg = Config(path=cfg_path)
    cfg.set("theme", "midnight")
    cfg.save()
    assert "theme: midnight" in cfg_path.read_text("utf-8")
    # No leaked tempfiles.
    leaked = [
        n for n in os.listdir(tmp_path)
        if n != "config.yaml" and n.startswith("config.yaml.")
    ]
    assert leaked == []
