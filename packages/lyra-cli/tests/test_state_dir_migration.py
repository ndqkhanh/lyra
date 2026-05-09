"""Phase 0 — v1 state-directory migration primitive (``.opencoding`` source).

This file pins the behavioural contract of the low-level primitive
``migrate_state(old, new, *, marker_name=...)`` living in
``lyra_core.migrations.state_v1``. It abstracts over the *source brand*
(v1.6 ``.opencoding`` or v1.7 ``.open-harness``) by taking the marker
name as a keyword-only argument.

This test fixes the v1.6 origin path (``.opencoding`` -> caller's target)
and asserts the primitive writes ``MIGRATED_FROM_OPENCODING``. The v1.7
origin path (``.open-harness``) is covered in
``test_state_dir_migration_v2.py``.

Contract:

- On a fresh dir with nothing at ``old`` it is a no-op that returns
  ``False`` (nothing to do) and does not create anything at ``new``.
- When ``old`` has content, it copies recursively to ``new`` and writes
  the marker file into ``new`` so we can recognise a migrated state dir.
- It never deletes ``old`` — data must stay recoverable.
- It is idempotent: calling it again after a successful migration must
  NOT overwrite files that already exist at ``new``.

lyra-legacy-aware: this file intentionally references the legacy
``.opencoding`` and ``.open-harness`` directory names to exercise the
migration primitive.
"""
from __future__ import annotations

from pathlib import Path

import pytest


def _import_migrate():
    try:
        from lyra_core.migrations.state_v1 import migrate_state
    except ModuleNotFoundError as exc:
        pytest.fail(
            f"lyra_core.migrations.state_v1.migrate_state must exist ({exc})"
        )
    return migrate_state


def test_migrate_state_is_noop_when_old_missing(tmp_path: Path) -> None:
    migrate_state = _import_migrate()
    old = tmp_path / ".opencoding"
    new = tmp_path / ".open-harness"
    assert not old.exists()
    result = migrate_state(old, new)
    assert result is False
    assert not new.exists(), "must not create the new dir when there's nothing to migrate"


def test_migrate_state_copies_files_and_writes_marker(tmp_path: Path) -> None:
    migrate_state = _import_migrate()
    old = tmp_path / ".opencoding"
    (old / "sessions").mkdir(parents=True)
    (old / "policy.yaml").write_text("version: 1\n")
    (old / "sessions" / "2026-04-23.jsonl").write_text("{}\n")
    (old / "plans").mkdir()
    (old / "plans" / "first.md").write_text("# first plan\n")

    new = tmp_path / ".open-harness"
    result = migrate_state(old, new)
    assert result is True

    assert (new / "policy.yaml").read_text() == "version: 1\n"
    assert (new / "sessions" / "2026-04-23.jsonl").read_text() == "{}\n"
    assert (new / "plans" / "first.md").read_text() == "# first plan\n"
    assert (new / "MIGRATED_FROM_OPENCODING").is_file(), "missing migration marker"

    # Old dir must be untouched.
    assert (old / "policy.yaml").is_file()
    assert (old / "sessions" / "2026-04-23.jsonl").is_file()


def test_migrate_state_is_idempotent(tmp_path: Path) -> None:
    migrate_state = _import_migrate()
    old = tmp_path / ".opencoding"
    old.mkdir()
    (old / "policy.yaml").write_text("original\n")
    new = tmp_path / ".open-harness"

    # First migration populates `new`.
    assert migrate_state(old, new) is True

    # Now a user edits the new policy.
    (new / "policy.yaml").write_text("user-edited\n")

    # Second call must not clobber user's edits.
    result = migrate_state(old, new)
    assert result is False
    assert (new / "policy.yaml").read_text() == "user-edited\n"


def test_migrate_state_preserves_subdirectories_with_mixed_content(tmp_path: Path) -> None:
    migrate_state = _import_migrate()
    old = tmp_path / ".opencoding"
    (old / "sessions" / "nested" / "deep").mkdir(parents=True)
    (old / "sessions" / "nested" / "deep" / "x.jsonl").write_text("x\n")
    (old / "hir.jsonl").write_text("event-1\n")

    new = tmp_path / ".open-harness"
    assert migrate_state(old, new) is True
    assert (new / "sessions" / "nested" / "deep" / "x.jsonl").read_text() == "x\n"
    assert (new / "hir.jsonl").read_text() == "event-1\n"
